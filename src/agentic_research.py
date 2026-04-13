from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any

from .config import Settings
from .models import Contact
from .openrouter_client import OpenRouterClient
from .providers import HunterProvider, SerperProvider, WebsiteResearchProvider


logger = logging.getLogger(__name__)


# Classification signals from scoring module
OWNER_TITLE_HINTS = {
    "owner",
    "founder",
    "ceo",
    "president",
    "principal",
    "partner",
}

RA_HINTS = {
    "wealth",
    "insurance",
    "broker",
    "fractional cfo",
    "cfo",
    "eos",
    "cepa",
    "banker",
    "advisor",
    "advisory",
    "consultant",
}

FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
    "protonmail.com",
    "mail.com",
    "yandex.com",
    "qq.com",
}

MAX_QUERIES_BY_DEPTH = {
    "minimal": 3,
    "standard": 6,
    "deep": 9,
}

MAX_PAGE_EVIDENCE_BY_DEPTH = {
    "minimal": 0,
    "standard": 1,
    "deep": 2,
}


@dataclass
class ResearchResult:
    """Result of agentic research on a contact/company."""

    contact: Contact
    success: bool
    sources_used: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # Metrics
    serper_queries_used: int = 0
    websites_scraped: int = 0
    emails_found: int = 0
    activity_log: list[dict[str, str]] = field(default_factory=list)


class AgenticResearchOrchestrator:
    """
    Orchestrates multiple specialized agents to research contacts agentically.

    The pipeline coordinates five specialized agents:
    1. Discovery Agent: Uses Serper to find company/decision maker info
    2. Company Agent: Scrapes company websites for context
    3. Person Agent: Enriches person data and validates identity
    4. Email Agent: Finds and verifies email addresses
    5. Classifier Agent: Determines audience type and maturity scoring

    Each agent operates independently with error isolation - partial
    success is still considered success, with detailed tracking of
    what was discovered vs what failed.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the orchestrator with all required providers.

        Args:
            settings: Application settings containing API keys
        """
        self.settings = settings
        self.serper = SerperProvider(settings)
        self.website = WebsiteResearchProvider(settings)
        self.hunter = HunterProvider(settings)
        self.llm = OpenRouterClient(settings)
        self.research_model = (
            settings.openrouter_research_model or settings.openrouter_model
        )

    def research_contact(
        self, contact: Contact, depth: str = "standard"
    ) -> ResearchResult:
        """
        Main entry point for agentic research on a contact.

        Executes the full research pipeline with configurable depth:
        - "minimal": Discovery + basic classification only
        - "standard": Full pipeline with all agents
        - "deep": Extended search with multiple queries and thorough validation

        Args:
            contact: The contact to research
            depth: Research depth level ("minimal", "standard", "deep")

        Returns:
            ResearchResult with enriched contact and operation metrics
        """
        if contact is None:
            return ResearchResult(
                contact=Contact.from_dict({}),
                success=False,
                errors=["No contact provided"],
            )

        # Initialize tracking
        contact.research_status = "started"
        sources_used: list[str] = []
        errors: list[str] = []
        activity_log: list[dict[str, str]] = []
        serper_queries = 0
        websites_scraped = 0
        emails_found = 0

        try:
            # Agent 1: Discovery
            contact.research_status = "discovery"
            discovery_data = self._run_discovery_agent(contact, depth=depth)
            if discovery_data:
                sources_used.append("discovery")
                serper_queries += discovery_data.get("queries_used", 0)
                activity_log.append(
                    {
                        "source": "serper",
                        "message": (
                            f"Discovery complete for {contact.company or contact.full_name}: "
                            f"{discovery_data.get('queries_used', 0)} queries"
                        ),
                    }
                )
                for query in discovery_data.get("person_search_queries", [])[:8]:
                    activity_log.append(
                        {
                            "source": "serper",
                            "message": f"Query: {query}",
                        }
                    )
                for page in discovery_data.get("evidence_pages", [])[:4]:
                    url = str(page.get("url", "") or "").strip()
                    if url:
                        activity_log.append(
                            {
                                "source": "web",
                                "message": f"Fetched evidence page: {url}",
                            }
                        )

            # Agent 2: Company Website (skip if minimal depth)
            company_data: dict[str, Any] = {}
            if depth != "minimal":
                contact.research_status = "company_research"
                company_data = self._run_company_agent(contact, discovery_data)
                if company_data:
                    sources_used.append("company_website")
                    websites_scraped += company_data.get("pages_scraped", 1)
                    website = contact.website or discovery_data.get("website_found", "")
                    if website:
                        activity_log.append(
                            {
                                "source": "website",
                                "message": f"Scraped company site: {website}",
                            }
                        )

            # Agent 3: Person Enrichment (standard and deep only)
            person_data: dict[str, Any] = {}
            if depth in ("standard", "deep"):
                contact.research_status = "person_research"
                person_data = self._run_person_agent(
                    contact,
                    discovery_data,
                    company_data,
                    depth=depth,
                )
                if person_data:
                    sources_used.append("person_enrichment")
                    if person_data.get("identity_verified"):
                        activity_log.append(
                            {
                                "source": "person_agent",
                                "message": "Identity cross-reference validated",
                            }
                        )

            # Agent 4: Email Discovery
            contact.research_status = "email_discovery"
            email_data = self._run_email_agent(contact)
            if email_data:
                sources_used.append("email_discovery")
                emails_found += email_data.get("emails_found", 0)
                domain = email_data.get("domain_searched", "")
                if domain:
                    activity_log.append(
                        {
                            "source": "hunter",
                            "message": f"Domain searched for email: {domain}",
                        }
                    )
                if email_data.get("verified"):
                    activity_log.append(
                        {
                            "source": "hunter",
                            "message": "Verified email identified",
                        }
                    )
                elif email_data.get("pattern_match"):
                    activity_log.append(
                        {
                            "source": "email_inference",
                            "message": "Email inferred from domain pattern",
                        }
                    )

            # Agent 5: Classification
            contact.research_status = "classification"
            all_data = {
                "discovery": discovery_data,
                "company": company_data,
                "person": person_data,
                "email": email_data,
            }
            classification = self._run_classifier_agent(contact, all_data)
            if classification:
                sources_used.append("classification")
                activity_log.append(
                    {
                        "source": "classifier",
                        "message": (
                            f"Audience confidence {contact.audience_confidence:.2f}, "
                            f"maturity {contact.company_maturity_score}"
                        ),
                    }
                )

            # Final status
            contact.research_status = "complete"

            # Determine success: partial success is still success
            success = len(sources_used) >= 2 or "classification" in sources_used

            return ResearchResult(
                contact=contact,
                success=success,
                sources_used=sources_used,
                errors=errors,
                serper_queries_used=serper_queries,
                websites_scraped=websites_scraped,
                emails_found=emails_found,
                activity_log=activity_log,
            )

        except Exception as e:
            errors.append(f"Research pipeline error: {str(e)}")
            contact.research_status = "failed"
            return ResearchResult(
                contact=contact,
                success=False,
                sources_used=sources_used,
                errors=errors,
                serper_queries_used=serper_queries,
                websites_scraped=websites_scraped,
                emails_found=emails_found,
                activity_log=activity_log,
            )

    def _run_discovery_agent(
        self, contact: Contact, depth: str = "standard"
    ) -> dict[str, Any]:
        """
        Use Serper to find company and decision maker information.

        Searches for:
        - Company website if missing
        - Decision makers by title patterns
        - Company information from knowledge graph

        Args:
            contact: The contact to research

        Returns:
            Dictionary with structured findings and query metrics
        """
        results: dict[str, Any] = {
            "company_info": {},
            "decision_makers": [],
            "website_found": "",
            "queries_used": 0,
            "person_search_queries": [],
            "person_search_hits": [],
            "evidence_pages": [],
        }

        if not self.serper.enabled:
            return results

        company_name = contact.company.strip() if contact.company else ""
        if not company_name:
            return results

        # Query 1: Extract company info from knowledge graph
        company_info = self.serper.extract_company_info(company_name)
        if company_info:
            results["company_info"] = company_info
            results["queries_used"] += 1

            # Update contact if website was found and missing
            if company_info.get("website") and not contact.website:
                contact.website = company_info["website"]
                results["website_found"] = company_info["website"]

            # Update other fields if missing
            if company_info.get("description") and not contact.notes:
                contact.notes = company_info["description"]
            if company_info.get("industry") and not contact.industry:
                contact.industry = company_info["industry"]

        # Query 2: Search for company website if still missing
        if not contact.website and not results["website_found"]:
            location = (
                f"{contact.city} {contact.state}".strip()
                if (contact.city or contact.state)
                else ""
            )
            companies = self.serper.search_companies(
                industry=contact.industry or "company",
                location=location or "USA",
                num=10,
            )
            results["queries_used"] += 1

            # Find matching company
            for company in companies:
                if company_name.lower() in company.get("name", "").lower():
                    if company.get("website"):
                        contact.website = company["website"]
                        results["website_found"] = company["website"]
                        break

        # Query 3: Search for decision makers at the company
        decision_maker_titles = [
            "CEO",
            "Founder",
            "Owner",
            "President",
            "Managing Director",
            "Chief Executive",
        ]
        location = contact.state if contact.state else None

        decision_makers = self.serper.search_decision_makers(
            company_name=company_name,
            titles=decision_maker_titles,
            location=location,
        )
        if decision_makers:
            results["decision_makers"] = decision_makers
            results["queries_used"] += 1

            # If contact has no LinkedIn but we found one for them specifically
            if not contact.linkedin:
                for dm in decision_makers:
                    if (
                        contact.first_name
                        and contact.last_name
                        and dm.get("first_name", "").lower()
                        == contact.first_name.lower()
                        and dm.get("last_name", "").lower() == contact.last_name.lower()
                    ):
                        contact.linkedin = dm.get("linkedin", "")
                        break

        # Query 4+: Multi-query person research sweep (LLM planned)
        planned_queries = self._plan_person_search_queries(contact, depth=depth)
        if planned_queries:
            results["person_search_queries"] = planned_queries

        sweep_hits: list[dict[str, str]] = []
        seen_links: set[str] = set()
        for query in planned_queries:
            search_result = self.serper.search(query=query, num=8)
            results["queries_used"] += 1
            if not search_result:
                continue

            for item in search_result.get("organic", []):
                title = str(item.get("title") or "").strip()
                link = str(item.get("link") or "").strip()
                snippet = str(item.get("snippet") or "").strip()
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                sweep_hits.append(
                    {
                        "query": query,
                        "title": title,
                        "link": link,
                        "snippet": snippet,
                    }
                )

        results["person_search_hits"] = sweep_hits

        # Optional deepening: fetch top non-LinkedIn pages and extract stronger evidence.
        evidence_limit = MAX_PAGE_EVIDENCE_BY_DEPTH.get(depth, 2)
        if evidence_limit > 0 and sweep_hits:
            evidence_pages = self._collect_evidence_pages(
                sweep_hits, limit=evidence_limit
            )
            results["evidence_pages"] = evidence_pages

            # Upgrade company summary from evidence when missing.
            if evidence_pages and not (contact.company_summary or "").strip():
                snippets = []
                for page in evidence_pages[:2]:
                    snippet = str(page.get("summary", "") or "").strip()
                    if snippet:
                        snippets.append(snippet)
                if snippets:
                    contact.company_summary = " ".join(snippets)[:500]

        # Fill identity clues from search sweep
        linkedin_hits = [
            h for h in sweep_hits if "linkedin.com/in/" in h.get("link", "").lower()
        ]
        if linkedin_hits and not contact.linkedin:
            contact.linkedin = linkedin_hits[0]["link"]

        if linkedin_hits and not contact.decision_maker_name:
            first_title = linkedin_hits[0].get("title", "")
            guessed_name = first_title.split("-")[0].strip()
            if guessed_name and len(guessed_name) <= 120:
                contact.decision_maker_name = guessed_name
                contact.decision_maker_source = "serper_reasoned_search"

        if linkedin_hits and not contact.decision_maker_title:
            first_title = linkedin_hits[0].get("title", "")
            parts = [p.strip() for p in first_title.split("-") if p.strip()]
            if len(parts) >= 2:
                contact.decision_maker_title = parts[1][:120]

        return results

    def _run_company_agent(
        self, contact: Contact, discovery_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Scrape company website for context and team information.

        Extracts:
        - Company summary/description
        - Team/leadership page information
        - Any available emails from the website

        Args:
            contact: The contact being researched
            discovery_data: Data from the discovery agent

        Returns:
            Dictionary with company context and scraping metrics
        """
        results: dict[str, Any] = {
            "company_summary": "",
            "team_members": [],
            "has_team_page": False,
            "pages_scraped": 0,
            "emails_found_on_site": [],
        }

        website = contact.website or discovery_data.get("website_found", "")
        if not website:
            return results

        try:
            # Scrape main company page
            company_info = self.website.scrape_company_page(website)
            results["pages_scraped"] += 1

            if not company_info:
                return results

            # Extract company summary
            summary_parts = []
            if company_info.get("meta_description"):
                summary_parts.append(company_info["meta_description"])
            if company_info.get("about_content"):
                summary_parts.append(company_info["about_content"][:300])

            results["company_summary"] = " ".join(summary_parts)[:500].strip()
            if results["company_summary"]:
                contact.company_summary = results["company_summary"]

            # Extract team information
            team_members = company_info.get("team_members", [])
            results["team_members"] = team_members
            results["has_team_page"] = len(team_members) > 0

            # Look for decision maker match in team
            if contact.first_name and contact.last_name and team_members:
                for member in team_members:
                    if (
                        member.get("first_name", "").lower()
                        == contact.first_name.lower()
                        and member.get("last_name", "").lower()
                        == contact.last_name.lower()
                    ):
                        if member.get("title") and not contact.title:
                            contact.title = member["title"]
                        if member.get("full_name") and not contact.full_name:
                            contact.full_name = member["full_name"]
                        break

            return results

        except Exception:
            # Company agent failure is non-fatal
            return results

    def _run_person_agent(
        self,
        contact: Contact,
        discovery_data: dict[str, Any],
        company_data: dict[str, Any],
        depth: str = "standard",
    ) -> dict[str, Any]:
        """
        Enrich person data through cross-referencing and validation.

        Validates:
        - Decision maker identity against multiple sources
        - Extracts personalization facts for messaging
        - Cross-references LinkedIn, discovery, and website data

        Args:
            contact: The contact being researched
            discovery_data: Data from discovery agent
            company_data: Data from company agent

        Returns:
            Dictionary with person enrichment and personalization facts
        """
        results: dict[str, Any] = {
            "identity_verified": False,
            "personalization_facts": {},
            "title_validated": False,
            "data_sources": [],
        }

        personalization_facts: dict[str, Any] = {}

        person_search_hits = discovery_data.get("person_search_hits", [])
        evidence_pages = discovery_data.get("evidence_pages", [])

        # Cross-reference decision makers from discovery
        decision_makers = discovery_data.get("decision_makers", [])
        if decision_makers and contact.first_name and contact.last_name:
            for dm in decision_makers:
                if (
                    dm.get("first_name", "").lower() == contact.first_name.lower()
                    and dm.get("last_name", "").lower() == contact.last_name.lower()
                ):
                    results["identity_verified"] = True
                    results["data_sources"].append("discovery_match")

                    if dm.get("title"):
                        results["title_validated"] = True
                        if not contact.title:
                            contact.title = dm["title"]
                        personalization_facts["discovered_title"] = dm["title"]

                    if dm.get("linkedin"):
                        personalization_facts["linkedin_url"] = dm["linkedin"]
                        if not contact.linkedin:
                            contact.linkedin = dm["linkedin"]

                    break

        # Cross-reference with team data from website
        team_members = company_data.get("team_members", [])
        if team_members and contact.first_name and contact.last_name:
            for member in team_members:
                if (
                    member.get("first_name", "").lower() == contact.first_name.lower()
                    and member.get("last_name", "").lower() == contact.last_name.lower()
                ):
                    results["identity_verified"] = True
                    results["data_sources"].append("website_team")

                    if member.get("title"):
                        results["title_validated"] = True
                        contact.decision_maker_title = member["title"]
                        personalization_facts["team_title"] = member["title"]

                    contact.decision_maker_name = member.get(
                        "full_name", contact.full_name
                    )
                    contact.decision_maker_source = "website_team_page"
                    break

        # Build personalization facts from available data
        if company_data.get("company_summary"):
            personalization_facts["company_context"] = company_data["company_summary"][
                :200
            ]

        if discovery_data.get("company_info", {}).get("founded"):
            personalization_facts["company_founded"] = discovery_data["company_info"][
                "founded"
            ]

        if discovery_data.get("company_info", {}).get("employees"):
            personalization_facts["company_size"] = discovery_data["company_info"][
                "employees"
            ]

        # Build richer personalization facts from multi-query search sweep
        if person_search_hits:
            top_hits = person_search_hits[:12]
            personalization_facts["search_signals"] = [
                {
                    "title": h.get("title", "")[:180],
                    "snippet": h.get("snippet", "")[:220],
                    "url": h.get("link", ""),
                }
                for h in top_hits
            ]

            heuristic_hooks: list[str] = []
            for h in top_hits:
                title = (h.get("title", "") or "").strip()
                snippet = (h.get("snippet", "") or "").strip()
                text = f"{title} {snippet}".lower()
                if any(
                    kw in text
                    for kw in (
                        "podcast",
                        "interview",
                        "speaking",
                        "webinar",
                        "award",
                        "acquired",
                        "expansion",
                        "hiring",
                        "launched",
                    )
                ):
                    hook = title or snippet
                    if hook and hook not in heuristic_hooks:
                        heuristic_hooks.append(hook[:180])
                if len(heuristic_hooks) >= 5:
                    break

            if heuristic_hooks:
                personalization_facts["heuristic_personalization_hooks"] = (
                    heuristic_hooks
                )

            llm_facts = self._extract_personalization_facts_with_llm(
                contact,
                person_search_hits,
                company_data,
                depth=depth,
            )
            if llm_facts:
                personalization_facts["reasoned_personalization"] = llm_facts
                suggested_name = str(llm_facts.get("decision_maker_name") or "").strip()
                suggested_title = str(
                    llm_facts.get("decision_maker_title") or ""
                ).strip()
                if suggested_name and not contact.decision_maker_name:
                    contact.decision_maker_name = suggested_name[:120]
                    contact.decision_maker_source = "reasoning_model"
                if suggested_title and not contact.decision_maker_title:
                    contact.decision_maker_title = suggested_title[:120]

        # Include fetched-page evidence in personalization artifacts
        if evidence_pages:
            personalization_facts["source_evidence_pages"] = [
                {
                    "url": str(p.get("url", "")),
                    "title": str(p.get("title", ""))[:180],
                    "summary": str(p.get("summary", ""))[:260],
                }
                for p in evidence_pages
            ]

            page_level_facts = self._extract_page_level_personalization_facts(
                contact=contact,
                evidence_pages=evidence_pages,
                depth=depth,
            )
            if page_level_facts:
                personalization_facts["page_level_personalization"] = page_level_facts

                if not (contact.decision_maker_name or "").strip():
                    name = str(
                        page_level_facts.get("decision_maker_name") or ""
                    ).strip()
                    if name:
                        contact.decision_maker_name = name[:120]
                        contact.decision_maker_source = "reasoning_model_page_evidence"
                if not (contact.decision_maker_title or "").strip():
                    title = str(
                        page_level_facts.get("decision_maker_title") or ""
                    ).strip()
                    if title:
                        contact.decision_maker_title = title[:120]

        # Store personalization facts as JSON
        if personalization_facts:
            contact.personalization_facts_json = json.dumps(personalization_facts)
            results["personalization_facts"] = personalization_facts

        return results

    def _run_email_agent(self, contact: Contact) -> dict[str, Any]:
        """
        Find and verify email addresses for the contact.

        Attempts in order:
        1. Hunter domain search if domain available
        2. Pattern-based inference
        3. Email verification status tracking

        Args:
            contact: The contact to find email for

        Returns:
            Dictionary with email data and verification status
        """
        results: dict[str, Any] = {
            "emails_found": 0,
            "email_source": "",
            "verified": False,
            "domain_searched": "",
            "pattern_match": False,
        }

        # Skip if contact already has an email
        if contact.email and "@" in contact.email:
            results["emails_found"] = 1
            results["email_source"] = "existing"
            results["verified"] = True
            contact.verified_email = True
            contact.email_source = "existing_csv"
            return results

        # Extract domain from website
        domain = ""
        if contact.website:
            from urllib.parse import urlparse

            url = contact.website.strip()
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            try:
                parsed = urlparse(url)
                domain = parsed.netloc or parsed.path
                if domain.startswith("www."):
                    domain = domain[4:]
            except Exception:
                domain = (
                    contact.website.lower()
                    .replace("www.", "")
                    .replace("https://", "")
                    .replace("http://", "")
                )

        results["domain_searched"] = domain

        # Try Hunter domain search
        if domain and self.hunter.enabled:
            try:
                hunter_results = self.hunter.domain_search(domain, limit=10)
                if hunter_results:
                    # Look for matching name
                    for email_data in hunter_results:
                        if (
                            contact.first_name
                            and contact.last_name
                            and email_data.get("first_name", "").lower()
                            == contact.first_name.lower()
                            and email_data.get("last_name", "").lower()
                            == contact.last_name.lower()
                        ):
                            contact.email = email_data["email"]
                            contact.verified_email = True
                            contact.email_source = "hunter_verified"
                            results["emails_found"] = 1
                            results["email_source"] = "hunter"
                            results["verified"] = True
                            return results

                    # No name match, but we found emails at the domain
                    results["emails_found"] = len(hunter_results)

            except Exception:
                pass

        # Try pattern-based inference
        if domain and contact.first_name and contact.last_name:
            first = contact.first_name.lower()
            last = contact.last_name.lower()
            first_initial = first[0] if first else ""
            last_initial = last[0] if last else ""

            # Common email patterns
            patterns = [
                f"{first}.{last}@{domain}",
                f"{first}{last}@{domain}",
                f"{first}@{domain}",
                f"{first_initial}{last}@{domain}",
                f"{first}.{last_initial}@{domain}",
                f"{first}{last_initial}@{domain}",
                f"{last}@{domain}",
            ]

            results["pattern_candidates"] = patterns
            results["pattern_match"] = True

            # Store the most common pattern as unverified
            contact.email = patterns[0]  # first.last@domain
            contact.verified_email = False
            contact.email_source = "pattern_inferred"
            results["email_source"] = "pattern"
            results["emails_found"] = 1

        return results

    def _run_classifier_agent(
        self, contact: Contact, all_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Perform audience classification and company maturity scoring.

        Calculates:
        - audience_confidence: 0.0-1.0 based on signal strength
        - company_maturity_score: 0-100 based on business indicators

        Args:
            contact: The contact to classify
            all_data: Aggregated data from all previous agents

        Returns:
            Dictionary with classification results and scores
        """
        results: dict[str, Any] = {
            "audience": "",
            "audience_confidence": 0.0,
            "company_maturity_score": 0,
            "maturity_breakdown": {},
            "classification_signals": [],
        }

        # Build classification text from all available data
        title_text = (contact.title or "").lower()
        industry_text = (contact.industry or "").lower()
        notes_text = (contact.notes or "").lower()
        company_summary = (contact.company_summary or "").lower()

        combined_text = f"{title_text} {industry_text} {notes_text} {company_summary}"

        # Calculate audience confidence
        owner_signals = []
        ra_signals = []

        # Check for owner signals
        for hint in OWNER_TITLE_HINTS:
            if hint in title_text:
                owner_signals.append(hint)

        # Check for RA signals
        for hint in RA_HINTS:
            if hint in combined_text:
                ra_signals.append(hint)

        # Determine audience and confidence
        is_owner = bool(owner_signals)
        is_ra = bool(ra_signals)

        if is_owner and not is_ra:
            results["audience"] = "owner"
            results["audience_confidence"] = min(0.8 + (0.05 * len(owner_signals)), 1.0)
            results["classification_signals"] = [f"owner:{s}" for s in owner_signals]
        elif is_ra and not is_owner:
            results["audience"] = "referral_advocate"
            results["audience_confidence"] = min(0.8 + (0.05 * len(ra_signals)), 1.0)
            results["classification_signals"] = [f"ra:{s}" for s in ra_signals]
        elif is_owner and is_ra:
            # Mixed signals - route to referral_advocate (advisor signals dominate
            # when explicit advisor keywords like CFO, wealth, CEPA, EOS are present).
            results["audience"] = "referral_advocate"
            results["audience_confidence"] = 0.6
            results["classification_signals"] = [
                f"owner:{s}" for s in owner_signals
            ] + [f"ra:{s}" for s in ra_signals]
        else:
            # No clear signals - low confidence, default to owner
            results["audience"] = "owner"
            results["audience_confidence"] = 0.3
            results["classification_signals"] = ["no_clear_signals"]

        contact.audience_confidence = results["audience_confidence"]

        # Calculate company maturity score (0-100)
        maturity_score = 30  # Base score
        breakdown: dict[str, int] = {"base": 30}

        # Has website with real content
        if contact.website and len(company_summary) > 50:
            maturity_score += 15
            breakdown["website_content"] = 15

        # Employee count scoring
        employee_str = contact.employee_count or ""
        # Parse employee count from various formats
        emp_match = re.search(r"(\d+)", employee_str)
        if emp_match:
            emp_count = int(emp_match.group(1))
            if emp_count >= 50:
                maturity_score += 20
                breakdown["employee_count_50plus"] = 20
            elif emp_count >= 10:
                maturity_score += 10
                breakdown["employee_count_10plus"] = 10

        # Years in business / founded date
        discovery_data = all_data.get("discovery", {})
        company_info = discovery_data.get("company_info", {})
        founded = company_info.get("founded", "")

        if founded:
            year_match = re.search(r"(\d{4})", founded)
            if year_match:
                founded_year = int(year_match.group(1))
                current_year = datetime.now(timezone.utc).year
                years_in_business = current_year - founded_year

                if years_in_business >= 10:
                    maturity_score += 25
                    breakdown["years_in_business_10plus"] = 25
                elif years_in_business >= 5:
                    maturity_score += 15
                    breakdown["years_in_business_5plus"] = 15
                else:
                    maturity_score += 10
                    breakdown["years_in_business_any"] = 10

        # Leadership/team page present
        company_data = all_data.get("company", {})
        if company_data.get("has_team_page"):
            maturity_score += 10
            breakdown["team_page"] = 10

        # Professional email domain
        if contact.email and "@" in contact.email:
            domain = contact.email.split("@")[1].lower()
            if domain not in FREE_EMAIL_DOMAINS:
                maturity_score += 10
                breakdown["professional_email"] = 10

        results["company_maturity_score"] = min(100, maturity_score)
        results["maturity_breakdown"] = breakdown
        contact.company_maturity_score = results["company_maturity_score"]

        return results

    def research_batch(
        self, contacts: list[Contact], depth: str = "standard"
    ) -> list[ResearchResult]:
        """
        Research multiple contacts efficiently.

        Args:
            contacts: List of contacts to research
            depth: Research depth level for all contacts

        Returns:
            List of ResearchResult objects
        """
        results = []
        for contact in contacts:
            result = self.research_contact(contact, depth=depth)
            results.append(result)
        return results

    def _plan_person_search_queries(self, contact: Contact, depth: str) -> list[str]:
        company = (contact.company or "").strip()
        full_name = (
            (contact.full_name or "").strip()
            or f"{(contact.first_name or '').strip()} {(contact.last_name or '').strip()}".strip()
        )
        title = (contact.title or "").strip()
        location = " ".join([p for p in [contact.city, contact.state] if p]).strip()

        fallback_queries = [
            f'site:linkedin.com/in "{full_name}" "{company}"',
            f'"{full_name}" "{company}" {title}'.strip(),
            f'"{company}" leadership team {location}'.strip(),
            f'"{company}" "{full_name}" podcast OR interview OR webinar',
            f'"{company}" press release OR news OR expansion',
            f'"{company}" awards OR case study OR customer story',
            f'"{company}" "{title or "owner"}" "{location or "USA"}"',
        ]

        max_queries = MAX_QUERIES_BY_DEPTH.get(depth, 6)

        # If no LLM credentials, still run multi-query fallback sweep.
        if not self.settings.openrouter_api_key:
            return [q for q in fallback_queries if q][:max_queries]

        system_prompt = (
            "You generate high-yield Google queries for B2B personalization research. "
            "Return strict JSON only."
        )
        user_prompt = (
            "Create a compact set of search queries to learn actionable personalization "
            "signals about this person/company for outbound email. Focus on recent activity, "
            "initiatives, speaking/interviews, customer outcomes, and leadership priorities.\n\n"
            f"Person: {full_name or 'unknown'}\n"
            f"Title: {title or 'unknown'}\n"
            f"Company: {company or 'unknown'}\n"
            f"Location: {location or 'unknown'}\n"
            f"Max queries: {max_queries}\n\n"
            "Output format:\n"
            '{"queries": ["..."], "rationale": "one sentence"}'
        )

        llm_queries: list[str] = []
        try:
            raw = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                model=self.research_model,
            )
            parsed = self._safe_json_from_model(raw)
            candidate_queries = parsed.get("queries", [])
            if isinstance(candidate_queries, list):
                for q in candidate_queries:
                    q_text = str(q or "").strip()
                    if q_text:
                        llm_queries.append(q_text)
        except Exception as e:
            logger.debug("LLM query planning failed, using fallback queries: %s", e)

        merged: list[str] = []
        seen: set[str] = set()
        for q in llm_queries + fallback_queries:
            key = q.lower().strip()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(q)
            if len(merged) >= max_queries:
                break

        return merged

    def _extract_personalization_facts_with_llm(
        self,
        contact: Contact,
        person_search_hits: list[dict[str, str]],
        company_data: dict[str, Any],
        depth: str = "standard",
    ) -> dict[str, Any]:
        if not self.settings.openrouter_api_key or not person_search_hits:
            return {}

        max_hits = 8 if depth == "minimal" else 12 if depth == "standard" else 16
        compact_hits = []
        for h in person_search_hits[:max_hits]:
            compact_hits.append(
                {
                    "title": (h.get("title", "") or "")[:200],
                    "snippet": (h.get("snippet", "") or "")[:260],
                    "url": h.get("link", ""),
                }
            )

        system_prompt = (
            "You are a research analyst extracting trustworthy personalization facts for B2B outreach. "
            "Use only provided snippets. Avoid hallucinations. Return strict JSON only."
        )
        user_prompt = (
            "Given these search results, extract high-signal personalization hooks and inferred priorities.\n"
            f"Person: {(contact.full_name or '').strip()}\n"
            f"Title: {(contact.title or '').strip()}\n"
            f"Company: {(contact.company or '').strip()}\n"
            f"Company summary: {(company_data.get('company_summary') or '')[:300]}\n\n"
            f"Search hits JSON:\n{json.dumps(compact_hits)}\n\n"
            "Output JSON schema:\n"
            "{"
            '"decision_maker_name":"",'
            '"decision_maker_title":"",'
            '"top_personalization_hooks":[{"fact":"", "why_it_matters":"", "source_url":"", "confidence":0.0}],'
            '"likely_priorities":[""],'
            '"talking_points":[""]'
            "}"
        )

        try:
            raw = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                model=self.research_model,
            )
            parsed = self._safe_json_from_model(raw)
            if not isinstance(parsed, dict):
                return {}

            # Keep payload bounded and predictable.
            hooks = parsed.get("top_personalization_hooks", [])
            if isinstance(hooks, list):
                parsed["top_personalization_hooks"] = hooks[:5]
            priorities = parsed.get("likely_priorities", [])
            if isinstance(priorities, list):
                parsed["likely_priorities"] = [str(p)[:120] for p in priorities[:5]]
            points = parsed.get("talking_points", [])
            if isinstance(points, list):
                parsed["talking_points"] = [str(p)[:140] for p in points[:6]]
            return parsed
        except Exception as e:
            logger.debug("LLM personalization extraction failed: %s", e)
            return {}

    def _collect_evidence_pages(
        self, search_hits: list[dict[str, str]], limit: int = 3
    ) -> list[dict[str, str]]:
        pages: list[dict[str, str]] = []
        seen_domains: set[str] = set()
        for hit in search_hits:
            url = str(hit.get("link", "") or "").strip()
            if not url:
                continue
            lowered = url.lower()
            if "linkedin.com/" in lowered:
                continue
            if lowered.endswith(".pdf"):
                continue

            domain = ""
            try:
                from urllib.parse import urlparse

                domain = (urlparse(url).netloc or "").lower().strip()
            except Exception:
                domain = ""
            if domain.startswith("www."):
                domain = domain[4:]
            if domain and domain in seen_domains:
                continue

            page = self._fetch_page_summary(url)
            if not page:
                continue

            pages.append(page)
            if domain:
                seen_domains.add(domain)
            if len(pages) >= limit:
                break
        return pages

    def _fetch_page_summary(self, url: str) -> dict[str, str]:
        html = self.website._fetch_page(url)
        if not html:
            return {}

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        for tag in soup.find_all(["script", "style", "noscript", "svg", "form"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return {}

        summary = text[:900]
        return {
            "url": url,
            "title": title[:220],
            "summary": summary,
        }

    def _extract_page_level_personalization_facts(
        self,
        contact: Contact,
        evidence_pages: list[dict[str, str]],
        depth: str = "standard",
    ) -> dict[str, Any]:
        if not self.settings.openrouter_api_key or not evidence_pages:
            return {}

        max_pages = 1 if depth == "minimal" else 2 if depth == "standard" else 4
        compact_pages = [
            {
                "url": p.get("url", ""),
                "title": p.get("title", "")[:200],
                "summary": p.get("summary", "")[:1000],
            }
            for p in evidence_pages[:max_pages]
        ]

        system_prompt = (
            "You are a sales research analyst. Extract only grounded facts from page summaries. "
            "No guessing. Return strict JSON."
        )
        user_prompt = (
            f"Person: {(contact.full_name or '').strip()}\n"
            f"Title: {(contact.title or '').strip()}\n"
            f"Company: {(contact.company or '').strip()}\n"
            f"Evidence pages JSON:\n{json.dumps(compact_pages)}\n\n"
            "Output JSON schema:\n"
            "{"
            '"decision_maker_name":"",'
            '"decision_maker_title":"",'
            '"verified_facts":[{"fact":"", "source_url":"", "confidence":0.0}],'
            '"personalization_angles":[""],'
            '"do_not_claim":[""]'
            "}"
        )

        try:
            raw = self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                model=self.research_model,
            )
            parsed = self._safe_json_from_model(raw)
            if not isinstance(parsed, dict):
                return {}

            facts = parsed.get("verified_facts", [])
            if isinstance(facts, list):
                parsed["verified_facts"] = facts[:6]
            angles = parsed.get("personalization_angles", [])
            if isinstance(angles, list):
                parsed["personalization_angles"] = [str(a)[:140] for a in angles[:6]]
            dnc = parsed.get("do_not_claim", [])
            if isinstance(dnc, list):
                parsed["do_not_claim"] = [str(a)[:140] for a in dnc[:6]]

            return parsed
        except Exception as e:
            logger.debug("Page-level fact extraction failed: %s", e)
            return {}

    def _safe_json_from_model(self, raw: str) -> dict[str, Any]:
        text = (raw or "").strip()
        if not text:
            return {}

        # Strip fenced code blocks if present.
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z0-9_\-]*", "", text).strip()
            text = re.sub(r"```$", "", text).strip()

        # Try direct parse first.
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            return {}
        except Exception:
            pass

        # Fallback: parse first object-like block.
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(text[start : end + 1])
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {}
        return {}
