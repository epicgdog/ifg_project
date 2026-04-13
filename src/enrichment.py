from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings
from .models import Contact, EnrichmentResult
from .providers import ApolloProvider, ApifyLinkedInProvider


@dataclass
class EnrichmentConfig:
    """Configuration for enrichment operations."""

    enable_apollo: bool = True
    enable_apify: bool = True
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    timeout_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


class EnrichmentCache:
    """Simple file-based cache for enrichment results."""

    def __init__(self, cache_dir: Path | None = None, ttl_hours: int = 24):
        self.cache_dir = cache_dir or Path(".cache/enrichment")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600

    def _make_key(self, contact: Contact) -> str:
        """Create cache key from contact identifiers."""
        key_parts = [contact.email, contact.linkedin, contact.company]
        key_string = "|".join(filter(None, key_parts))
        if not key_string:
            key_string = f"{contact.row_id}|{contact.source_file}|{contact.full_name}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, contact: Contact) -> dict[str, Any] | None:
        """Get cached enrichment data if valid."""
        key = self._make_key(contact)
        cache_path = self._cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            # Check TTL
            cached_time = cached.get("cached_at", 0)
            if time.time() - cached_time > self.ttl_seconds:
                cache_path.unlink(missing_ok=True)
                return None

            return cached.get("data")
        except (json.JSONDecodeError, IOError):
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, contact: Contact, data: dict[str, Any]) -> None:
        """Cache enrichment data."""
        key = self._make_key(contact)
        cache_path = self._cache_path(key)

        cached = {
            "cached_at": time.time(),
            "data": data,
        }

        with open(cache_path, "w") as f:
            json.dump(cached, f, indent=2)

    def clear(self) -> None:
        """Clear all cached entries."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink(missing_ok=True)


class EnrichmentOrchestrator:
    """Orchestrates contact enrichment from multiple API sources."""

    MERGE_PRECEDENCE = [
        "apollo",  # Good for company and person data
        "apify",  # Most reliable for LinkedIn profile data
        "csv",  # Original input
    ]

    def __init__(self, settings: Settings, config: EnrichmentConfig | None = None):
        self.settings = settings
        self.config = config or EnrichmentConfig()
        self.cache = EnrichmentCache(ttl_hours=self.config.cache_ttl_hours)

        # Initialize providers
        self.apollo = ApolloProvider(settings)
        self.apify = ApifyLinkedInProvider(settings)

    def _with_retry(self, fn, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception:
                if attempt == self.config.max_retries - 1:
                    raise
                time.sleep(self.config.retry_delay_seconds * (attempt + 1))
        return None

    def _merge_data(
        self, original: Contact, enrichments: dict[str, dict[str, str]]
    ) -> tuple[Contact, list[str], list[str]]:
        """
        Merge enrichment data from multiple sources.
        Precedence: API verified > existing non-empty CSV > empty.
        """
        merged = Contact(**original.to_dict())
        fields_to_merge = [
            "title",
            "company",
            "email",
            "industry",
            "website",
            "linkedin",
            "city",
            "state",
            "employee_count",
            "annual_revenue",
            "apollo_person_id",
            "apollo_org_id",
        ]

        sources_applied = []
        fields_updated = []

        for source in self.MERGE_PRECEDENCE:
            if source not in enrichments:
                continue

            data = enrichments[source]
            sources_applied.append(source)

            for field in fields_to_merge:
                new_value = data.get(field, "").strip()
                if not new_value:
                    continue

                current_value = getattr(merged, field, "")

                # Apply merge rule
                if source in ("apollo", "apify"):
                    # API data overrides CSV if present
                    if new_value != current_value:
                        setattr(merged, field, new_value)
                        merged.enrichment_sources[field] = source
                        if field not in fields_updated:
                            fields_updated.append(field)
                elif source == "csv" and not current_value:
                    # Only use CSV to fill gaps
                    setattr(merged, field, new_value)

        # Mark enrichment timestamp
        if fields_updated:
            merged.enriched_at = time.strftime("%Y-%m-%dT%H:%M:%S")

        return merged, sources_applied, fields_updated

    def _score_source_confidence(self, source: str) -> float:
        if source == "apify":
            return 0.9
        if source == "apollo":
            return 0.85
        return 0.6

    def enrich(self, contact: Contact) -> EnrichmentResult:
        """
        Enrich a single contact from all configured sources.
        Returns enriched contact with provenance tracking.
        """
        errors = []
        enrichments = {"csv": {}}
        cached = False

        # Check cache first
        if self.config.cache_enabled:
            cached_data = self.cache.get(contact)
            if cached_data:
                for key, value in cached_data.items():
                    setattr(contact, key, value)
                return EnrichmentResult(
                    contact=contact,
                    sources_applied=["cache"],
                    fields_updated=list(cached_data.keys()),
                    errors=[],
                    cached=True,
                )

        # Apollo enrichment
        apollo_linkedin: str = ""
        if self.config.enable_apollo and self.apollo.enabled:
            try:
                apollo_data = self._with_retry(
                    self.apollo.enrich_contact,
                    contact,
                    self.config.timeout_seconds,
                )
                if apollo_data:
                    enrichments["apollo"] = apollo_data
                    apollo_linkedin = apollo_data.get("linkedin", "")
            except Exception as e:
                errors.append(f"apollo:{str(e)}")

        # Apify LinkedIn enrichment — use Apollo-found URL if CSV didn't have one
        linkedin_url = contact.linkedin or apollo_linkedin
        if self.config.enable_apify and self.apify.enabled and linkedin_url:
            try:
                apify_results = self._with_retry(
                    self.apify.scrape_profiles,
                    [linkedin_url],
                    self.config.timeout_seconds,
                )
                if apify_results:
                    enrichments["apify"] = apify_results[0]
            except Exception as e:
                errors.append(f"apify:{str(e)}")

        # Merge all sources
        merged_contact, sources_applied, fields_updated = self._merge_data(
            contact, enrichments
        )

        for field in fields_updated:
            source = merged_contact.enrichment_sources.get(field, "csv")
            merged_contact.data_confidence[field] = self._score_source_confidence(
                source
            )

        # Cache result
        if self.config.cache_enabled and fields_updated:
            cache_data = {
                field: getattr(merged_contact, field) for field in fields_updated
            }
            cache_data["enrichment_sources"] = merged_contact.enrichment_sources
            cache_data["enriched_at"] = merged_contact.enriched_at
            cache_data["data_confidence"] = merged_contact.data_confidence
            self.cache.set(contact, cache_data)

        return EnrichmentResult(
            contact=merged_contact,
            sources_applied=sources_applied,
            fields_updated=fields_updated,
            errors=errors,
            cached=cached,
        )

    def enrich_batch(self, contacts: list[Contact]) -> list[EnrichmentResult]:
        """Enrich multiple contacts efficiently."""
        results = []
        for contact in contacts:
            result = self.enrich(contact)
            results.append(result)
        return results
