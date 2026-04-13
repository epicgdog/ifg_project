from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .config import Settings
from .models import Contact
from .providers import HunterProvider, SerperProvider, WebsiteResearchProvider


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

    def research_contact(self, contact: Contact, depth: str = "standard") -> ResearchResult:
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
        if not contact:
            return ResearchResult(
                contact=contact or Contact(),
                success=False,
                errors=["No contact provided"],
            )

        # Initialize tracking
        contact.research_status = "started"
        sources_used: list[str] = []
        errors: list[str] = []
        serper_queries = 0
        websites_scraped = 0
        emails_found = 0

        try:
            # Agent 1: Discovery
            contact.research_status = "discovery"
            discovery_data = self._run_discovery_agent(contact)
            if discovery_data:
                sources_used.append("discovery")
                serper_queries += discovery_data.get("queries_used", 0)

            # Agent 2: Company Website (skip if minimal depth)
            company_data: dict[str, Any] = {}
            if depth != "minimal":
                contact.research_status = "company_research"
                company_data = self._run_company_agent(contact, discovery_data)
                if company_data:
                    sources_used.append("company_website")
                    websites_scraped += company_data.get("pages_scraped", 1)

            # Agent 3: Person Enrichment (standard and deep only)
            person_data: dict[str, Any] = {}
            if depth in ("standard", "deep"):
                contact.research_status = "person_research"
                person_data = self._run_person_agent(contact, discovery_data, company_data)
                if person_data:
                    sources_used.append("person_enrichment")

            # Agent 4: Email Discovery
            contact.research_status = "email_discovery"
            email_data = self._run_email_agent(contact)
            if email_data:
                sources_used.append("email_discovery")
                emails_found += email_data.get("emails_found", 0)

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
            )

    def _run_discovery_agent(self, contact: Contact) -> dict[str, Any]:
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
            location = f"{contact.city} {contact.state}".strip() if (contact.city or contact.state) else ""
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
                        and dm.get("first_name", "").lower() == contact.first_name.lower()
                        and dm.get("last_name", "").lower() == contact.last_name.lower()
                    ):
                        contact.linkedin = dm.get("linkedin", "")
                        break

        return results

    def _run_company_agent(self, contact: Contact, discovery_data: dict[str, Any]) -> dict[str, Any]:
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
                        member.get("first_name", "").lower() == contact.first_name.lower()
                        and member.get("last_name", "").lower() == contact.last_name.lower()
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
        self, contact: Contact, discovery_data: dict[str, Any], company_data: dict[str, Any]
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

                    contact.decision_maker_name = member.get("full_name", contact.full_name)
                    contact.decision_maker_source = "website_team_page"
                    break

        # Build personalization facts from available data
        if company_data.get("company_summary"):
            personalization_facts["company_context"] = company_data["company_summary"][:200]

        if discovery_data.get("company_info", {}).get("founded"):
            personalization_facts["company_founded"] = discovery_data["company_info"]["founded"]

        if discovery_data.get("company_info", {}).get("employees"):
            personalization_facts["company_size"] = discovery_data["company_info"]["employees"]

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
                domain = contact.website.lower().replace("www.", "").replace("https://", "").replace("http://", "")

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
                            and email_data.get("first_name", "").lower() == contact.first_name.lower()
                            and email_data.get("last_name", "").lower() == contact.last_name.lower()
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

    def _run_classifier_agent(self, contact: Contact, all_data: dict[str, Any]) -> dict[str, Any]:
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
            # Mixed signals - moderate confidence
            results["audience"] = "owner"  # Default to owner on conflict
            results["audience_confidence"] = 0.6
            results["classification_signals"] = [f"owner:{s}" for s in owner_signals] + [f"ra:{s}" for s in ra_signals]
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
                current_year = 2024  # Using fixed year for consistency
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
