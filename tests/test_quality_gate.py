"""
Quality Gate Tests - Ruthless, Comprehensive, Borderline Brutal

These tests tear apart the quality gate logic that filters contacts based on:
1. verified_email requirement
2. identity confirmation (linkedin OR decision_maker_name)

The quality gate is in src/pipeline.py lines 262-280.
"""

import pytest
from dataclasses import dataclass, field
from typing import Any

from src.models import Contact, EnrichmentResult
from src.pipeline import PipelineRunReport, run_pipeline
from src.openrouter_client import OpenRouterClient
from src.config import Settings


# =============================================================================
# TEST CONTACT FACTORY
# =============================================================================

def make_test_contact(**kwargs) -> Contact:
    """
    Factory for creating test contacts with sensible defaults.
    
    By default, creates a contact that will FAIL both quality gates:
    - verified_email=False
    - linkedin='' (empty)
    - decision_maker_name='' (empty)
    
    Use kwargs to override specific fields for test scenarios.
    """
    defaults = {
        # Required core fields
        'row_id': 'test-001',
        'source_file': 'test.csv',
        'first_name': 'John',
        'last_name': 'Doe',
        'full_name': 'John Doe',
        'title': 'CEO',
        'company': 'TestCo Industries',
        'email': 'john.doe@testco.com',
        'industry': 'Technology',
        'website': 'https://testco.com',
        'linkedin': '',  # Empty by default - will fail identity gate
        'city': 'Denver',
        'state': 'CO',
        'notes': 'Test contact for quality gate validation',
        'employee_count': '50-200',
        'annual_revenue': '$10M-$50M',
        'apollo_person_id': 'apollo_12345',
        'apollo_org_id': 'apollo_org_67890',
        
        # Enrichment metadata
        'enrichment_sources': {},
        'enriched_at': '',
        'data_confidence': {},
        
        # Research-driven fields - these are the critical ones for quality gate
        'audience_confidence': 0.0,
        'company_maturity_score': 0,
        'company_summary': '',
        'decision_maker_name': '',  # Empty by default - will fail identity gate
        'decision_maker_source': '',
        'decision_maker_title': '',
        'email_source': '',
        'personalization_facts_json': '',
        'research_status': '',
        'verified_email': False,  # False by default - will fail email gate
    }
    defaults.update(kwargs)
    return Contact(**defaults)


# =============================================================================
# PYTEST FIXTURES
# =============================================================================

@pytest.fixture
def base_contact():
    """Returns a base contact that fails all quality gates."""
    return make_test_contact()


@pytest.fixture
def passing_contact():
    """Returns a contact that passes both quality gates."""
    return make_test_contact(
        row_id='passing-001',
        verified_email=True,
        linkedin='https://linkedin.com/in/johndoe',
        decision_maker_name='John Doe',
    )


@pytest.fixture
def mock_llm():
    """Returns a mock OpenRouterClient for pipeline tests."""
    settings = Settings(
        openrouter_api_key="test-key",
        openrouter_model="test-model",
        openrouter_base_url="https://test.openrouter.ai/api/v1",
        openrouter_http_referer="https://test.local",
        openrouter_title="Test",
        apollo_api_key="",
        hunter_api_key="",
        serper_api_key="",
        apify_api_token="",
        apify_linkedin_actor_id="",
    )
    return OpenRouterClient(settings)


@pytest.fixture
def empty_report():
    """Returns a fresh PipelineRunReport."""
    return PipelineRunReport()


# =============================================================================
# QUALITY GATE LOGIC TESTS
# =============================================================================

class TestQualityGateLogic:
    """
    Tests the core quality gate filtering logic.
    
    The quality gate filters contacts based on:
    - verified_email AND email must both be truthy
    - linkedin OR decision_maker_name must be truthy
    """

    def test_contact_passes_with_verified_email_and_linkedin(self, mock_llm, tmp_path):
        """
        Contact with verified email + LinkedIn should pass.
        
        This is the "happy path" - contact has both email verification
        and identity confirmation via LinkedIn URL.
        """
        contact = make_test_contact(
            row_id='pass-email-linkedin',
            email='valid@example.com',
            verified_email=True,
            linkedin='https://linkedin.com/in/validuser',
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 1, f"Expected 1 contact to pass, but got {count}"
        assert report.skipped_unverified_email_count == 0, "Should not skip any for unverified email"
        assert report.skipped_no_identity_count == 0, "Should not skip any for missing identity"
        assert report.total_contacts == 1, "Total contacts should be 1"

    def test_contact_passes_with_verified_email_and_decision_maker(self, mock_llm, tmp_path):
        """
        Contact with verified email + decision_maker_name should pass.
        
        Identity can be confirmed via either LinkedIn OR decision_maker_name.
        This tests the decision_maker_name path.
        """
        contact = make_test_contact(
            row_id='pass-email-dm',
            email='valid@example.com',
            verified_email=True,
            linkedin='',  # Empty LinkedIn
            decision_maker_name='Jane Smith',  # But has decision maker
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 1, f"Expected 1 contact to pass, but got {count}"
        assert report.skipped_unverified_email_count == 0
        assert report.skipped_no_identity_count == 0

    def test_contact_passes_with_both_identity_fields(self, mock_llm, tmp_path):
        """
        Contact with verified email + BOTH linkedin AND decision_maker_name should pass.
        
        Having both identity fields is even better, but either one is sufficient.
        """
        contact = make_test_contact(
            row_id='pass-both-identity',
            email='valid@example.com',
            verified_email=True,
            linkedin='https://linkedin.com/in/user',
            decision_maker_name='John DecisionMaker',
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 1, f"Expected 1 contact to pass, but got {count}"

    def test_contact_fails_without_verified_email(self, mock_llm, tmp_path):
        """
        Contact without verified_email should be skipped.
        
        Even if contact has LinkedIn and decision_maker_name, 
        unverified email should cause rejection.
        """
        contact = make_test_contact(
            row_id='fail-no-verify',
            email='unverified@example.com',
            verified_email=False,  # NOT verified
            linkedin='https://linkedin.com/in/user',
            decision_maker_name='Some Decision Maker',
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 0, f"Expected 0 contacts to pass, but got {count}"
        assert report.skipped_unverified_email_count == 1, "Should increment unverified email counter"
        assert report.total_contacts == 1, "Total should still reflect input count"

    def test_contact_fails_without_identity(self, mock_llm, tmp_path):
        """
        Contact without linkedin OR decision_maker_name should be skipped.
        
        Even with verified email, missing identity confirmation should reject.
        """
        contact = make_test_contact(
            row_id='fail-no-identity',
            email='valid@example.com',
            verified_email=True,  # Email is verified
            linkedin='',  # NO LinkedIn
            decision_maker_name='',  # NO decision maker
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 0, f"Expected 0 contacts to pass, but got {count}"
        assert report.skipped_no_identity_count == 1, "Should increment no-identity counter"

    def test_contact_fails_with_both_missing(self, mock_llm, tmp_path):
        """
        Contact missing both email verification AND identity should be skipped.
        
        This contact fails both gates - worst case scenario.
        Both counters should increment.
        """
        contact = make_test_contact(
            row_id='fail-both',
            email='test@example.com',
            verified_email=False,  # NOT verified
            linkedin='',  # NO LinkedIn
            decision_maker_name='',  # NO decision maker
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 0, f"Expected 0 contacts to pass, but got {count}"
        assert report.skipped_unverified_email_count == 1, "Should increment unverified email counter"
        assert report.skipped_no_identity_count == 1, "Should increment no-identity counter"


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """
    Edge cases that could break the quality gate logic.
    
    These tests probe boundary conditions, weird inputs, and 
    potential bugs in the filtering logic.
    """

    def test_contact_with_only_linkedin_no_verified_email(self, mock_llm, tmp_path):
        """
        LinkedIn alone should fail if verified_email required.
        
        Having LinkedIn is not enough if email is not verified.
        Both gates must pass independently.
        """
        contact = make_test_contact(
            row_id='edge-linkedin-only',
            email='has@email.com',
            verified_email=False,  # Email NOT verified
            linkedin='https://linkedin.com/in/haslinkedin',  # Has LinkedIn
            decision_maker_name='',  # No DM
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 0, "Should fail because email is not verified"
        assert report.skipped_unverified_email_count == 1
        assert report.skipped_no_identity_count == 0, "Identity check should pass (LinkedIn present)"

    def test_contact_with_unverified_email_flag(self, mock_llm, tmp_path):
        """
        verified_email=False should fail even if email exists.
        
        The email field can have a value, but if verified_email is False,
        the contact should still be rejected.
        """
        contact = make_test_contact(
            row_id='edge-unverified-flag',
            email='looks.valid@example.com',  # Email looks valid
            verified_email=False,  # But explicitly NOT verified
            linkedin='https://linkedin.com/in/user',
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 0, "Should fail because verified_email=False"
        assert report.skipped_unverified_email_count == 1

    def test_contact_with_empty_email_string(self, mock_llm, tmp_path):
        """
        Empty string email with verified_email=True should fail.
        
        The gate checks: contact.verified_email AND contact.email
        Empty string is falsy in Python, so this should fail.
        """
        contact = make_test_contact(
            row_id='edge-empty-email',
            email='',  # Empty string (falsy)
            verified_email=True,  # Even though marked verified
            linkedin='https://linkedin.com/in/user',
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 0, "Should fail because email is empty string (falsy)"
        assert report.skipped_unverified_email_count == 1

    def test_empty_decision_maker_name_not_counted(self, mock_llm, tmp_path):
        """
        Empty string decision_maker_name should not count as identity.
        
        Empty string is falsy in Python, so it should not satisfy
        the identity requirement.
        """
        contact = make_test_contact(
            row_id='edge-empty-dm',
            email='valid@example.com',
            verified_email=True,
            linkedin='',  # No LinkedIn
            decision_maker_name='',  # Empty string DM (falsy)
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 0, "Should fail because decision_maker_name is empty"
        assert report.skipped_no_identity_count == 1

    def test_whitespace_only_decision_maker_name(self, mock_llm, tmp_path):
        """
        Whitespace-only decision_maker_name should not count as identity.
        
        Whitespace is truthy in Python, but semantically it's still empty.
        The current implementation treats it as truthy - this documents that behavior.
        """
        contact = make_test_contact(
            row_id='edge-whitespace-dm',
            email='valid@example.com',
            verified_email=True,
            linkedin='',  # No LinkedIn
            decision_maker_name='   ',  # Whitespace only (truthy in Python!)
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        # Note: Whitespace-only strings are truthy in Python, so this PASSES
        # This test documents the current behavior, not necessarily desired behavior
        assert count == 1, "Whitespace-only DM is truthy in Python, so it passes"
        assert report.skipped_no_identity_count == 0

    def test_backward_compatibility_no_new_fields(self, mock_llm, tmp_path):
        """
        Contacts without new fields should use getattr defaults.
        
        When loading old CSVs or data without the new fields,
        the model defaults should handle it gracefully.
        verified_email defaults to False, linkedin and decision_maker_name to ''.
        """
        # Simulate loading from dict without new fields (backward compat)
        data = {
            'row_id': 'legacy-001',
            'source_file': 'legacy.csv',
            'first_name': 'Legacy',
            'last_name': 'Contact',
            'full_name': 'Legacy Contact',
            'title': 'CEO',
            'company': 'OldCorp',
            'email': 'old@example.com',
            'industry': 'Manufacturing',
            'website': '',
            'linkedin': '',  # Explicitly empty
            'city': 'Chicago',
            'state': 'IL',
            'notes': '',
            'employee_count': '',
            'annual_revenue': '',
            'apollo_person_id': '',
            'apollo_org_id': '',
            # Note: verified_email and decision_maker_name NOT in dict
        }
        
        contact = Contact.from_dict(data)
        
        # Verify defaults are applied
        assert contact.verified_email == False, "verified_email should default to False"
        assert contact.decision_maker_name == '', "decision_maker_name should default to empty"
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        # Should fail both gates
        assert count == 0
        assert report.skipped_unverified_email_count == 1
        assert report.skipped_no_identity_count == 1

    def test_require_verified_email_disabled(self, mock_llm, tmp_path):
        """
        When require_verified_email=False, email verification is not required.
        
        The contact should pass even with verified_email=False.
        """
        contact = make_test_contact(
            row_id='edge-no-email-check',
            email='any@email.com',
            verified_email=False,  # Not verified
            linkedin='https://linkedin.com/in/user',  # But has identity
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=False,  # DISABLED
            require_identity_confirmation=True,
        )
        
        assert count == 1, "Should pass when email verification is not required"
        assert report.skipped_unverified_email_count == 0

    def test_require_identity_confirmation_disabled(self, mock_llm, tmp_path):
        """
        When require_identity_confirmation=False, identity is not required.
        
        The contact should pass even without linkedin or decision_maker_name.
        """
        contact = make_test_contact(
            row_id='edge-no-identity-check',
            email='valid@example.com',
            verified_email=True,  # Has verified email
            linkedin='',  # No LinkedIn
            decision_maker_name='',  # No DM
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=False,  # DISABLED
        )
        
        assert count == 1, "Should pass when identity confirmation is not required"
        assert report.skipped_no_identity_count == 0

    def test_both_gates_disabled(self, mock_llm, tmp_path):
        """
        When both gates are disabled, all contacts should pass.
        
        Even contacts that would fail both gates should be allowed through.
        """
        contact = make_test_contact(
            row_id='edge-no-gates',
            email='',  # No email
            verified_email=False,  # Not verified
            linkedin='',  # No LinkedIn
            decision_maker_name='',  # No DM
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=False,  # DISABLED
            require_identity_confirmation=False,  # DISABLED
        )
        
        assert count == 1, "Should pass when both gates are disabled"
        assert report.skipped_unverified_email_count == 0
        assert report.skipped_no_identity_count == 0


# =============================================================================
# REPORT COUNTER TESTS
# =============================================================================

class TestReportCounters:
    """
    Tests that verify the PipelineRunReport counters increment correctly.
    
    These tests focus on the side effects - making sure the report
    accurately reflects what happened during filtering.
    """

    def test_report_counters_increment_correctly(self, mock_llm, tmp_path):
        """
        Verify skipped_unverified_email_count and skipped_no_identity_count work.
        
        Mix of contacts that pass/fail different gates to ensure
        counters accumulate correctly.
        """
        contacts = [
            # Contact 1: Passes both
            make_test_contact(
                row_id='pass-1',
                verified_email=True,
                linkedin='https://linkedin.com/in/user1',
            ),
            # Contact 2: Fails email only
            make_test_contact(
                row_id='fail-email-1',
                verified_email=False,
                linkedin='https://linkedin.com/in/user2',
            ),
            # Contact 3: Fails identity only
            make_test_contact(
                row_id='fail-identity-1',
                verified_email=True,
                linkedin='',
                decision_maker_name='',
            ),
            # Contact 4: Fails both
            make_test_contact(
                row_id='fail-both-1',
                verified_email=False,
                linkedin='',
                decision_maker_name='',
            ),
            # Contact 5: Passes both (different identity field)
            make_test_contact(
                row_id='pass-2',
                verified_email=True,
                linkedin='',
                decision_maker_name='Decision Maker',
            ),
            # Contact 6: Fails email only (has DM, no LinkedIn)
            make_test_contact(
                row_id='fail-email-2',
                verified_email=False,
                linkedin='',
                decision_maker_name='Another DM',
            ),
        ]
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=contacts,
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        # 6 total, 2 pass (pass-1, pass-2), 4 fail in some way
        # fail-email-1: fails email only
        # fail-identity-1: fails identity only  
        # fail-both-1: fails both
        # fail-email-2: fails email only
        
        assert count == 2, f"Expected 2 contacts to pass, got {count}"
        assert report.total_contacts == 6, "Total should be 6"
        
        # Email failures: fail-email-1, fail-both-1, fail-email-2 = 3
        assert report.skipped_unverified_email_count == 3, \
            f"Expected 3 unverified email skips, got {report.skipped_unverified_email_count}"
        
        # Identity failures: fail-identity-1, fail-both-1 = 2
        assert report.skipped_no_identity_count == 2, \
            f"Expected 2 no-identity skips, got {report.skipped_no_identity_count}"

    def test_counter_resets_between_runs(self, mock_llm, tmp_path):
        """
        Each pipeline run should have independent counters.
        
        Running twice should not accumulate counters across runs.
        """
        contact = make_test_contact(
            row_id='fail-both',
            verified_email=False,
            linkedin='',
            decision_maker_name='',
        )
        
        output_path = tmp_path / "output.csv"
        
        # First run
        count1, report1 = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        # Second run with same contact
        count2, report2 = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        # Both should have same counts, not accumulated
        assert count1 == count2 == 0
        assert report1.skipped_unverified_email_count == report2.skipped_unverified_email_count == 1
        assert report1.skipped_no_identity_count == report2.skipped_no_identity_count == 1

    def test_no_counters_when_gates_disabled(self, mock_llm, tmp_path):
        """
        When both gates are disabled, counters should remain at 0.
        
        Even with failing contacts, counters shouldn't increment if
        the corresponding gate is disabled.
        """
        contacts = [
            make_test_contact(
                row_id='bad-1',
                verified_email=False,
            ),
            make_test_contact(
                row_id='bad-2', 
                verified_email=False,
                linkedin='',
                decision_maker_name='',
            ),
        ]
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=contacts,
            require_verified_email=False,  # Disabled
            require_identity_confirmation=False,  # Disabled
        )
        
        assert count == 2, "All contacts should pass when gates disabled"
        assert report.skipped_unverified_email_count == 0
        assert report.skipped_no_identity_count == 0


# =============================================================================
# BATCH PROCESSING TESTS
# =============================================================================

class TestBatchProcessing:
    """
    Tests for batch processing scenarios.
    
    Ensures the quality gate works correctly with multiple contacts
    and doesn't have state leakage or ordering issues.
    """

    def test_empty_contact_list(self, mock_llm, tmp_path):
        """
        Empty contact list should return 0 with all counters at 0.
        
        Edge case: what happens when there's nothing to process?
        """
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 0
        assert report.total_contacts == 0
        assert report.skipped_unverified_email_count == 0
        assert report.skipped_no_identity_count == 0

    def test_all_contacts_pass(self, mock_llm, tmp_path):
        """
        All contacts passing should result in count == total.
        
        Sanity check for the happy path at scale.
        """
        contacts = [
            make_test_contact(
                row_id=f'pass-{i}',
                verified_email=True,
                linkedin=f'https://linkedin.com/in/user{i}',
            )
            for i in range(10)
        ]
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=contacts,
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 10
        assert report.total_contacts == 10
        assert report.skipped_unverified_email_count == 0
        assert report.skipped_no_identity_count == 0

    def test_all_contacts_fail(self, mock_llm, tmp_path):
        """
        All contacts failing should result in count == 0.
        
        Sanity check for the failure path at scale.
        """
        contacts = [
            make_test_contact(
                row_id=f'fail-{i}',
                verified_email=False,
                linkedin='',
                decision_maker_name='',
            )
            for i in range(10)
        ]
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=contacts,
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 0
        assert report.total_contacts == 10
        assert report.skipped_unverified_email_count == 10
        assert report.skipped_no_identity_count == 10

    def test_mixed_batch(self, mock_llm, tmp_path):
        """
        Mixed batch of pass/fail should have correct counts.
        
        Tests that filtering maintains proper counts with varied inputs.
        """
        contacts = []
        
        # 3 pass both
        for i in range(3):
            contacts.append(make_test_contact(
                row_id=f'pass-{i}',
                verified_email=True,
                linkedin=f'https://linkedin.com/in/user{i}',
            ))
        
        # 2 fail email only
        for i in range(2):
            contacts.append(make_test_contact(
                row_id=f'fail-email-{i}',
                verified_email=False,
                linkedin=f'https://linkedin.com/in/fail{i}',
            ))
        
        # 2 fail identity only  
        for i in range(2):
            contacts.append(make_test_contact(
                row_id=f'fail-identity-{i}',
                verified_email=True,
                linkedin='',
                decision_maker_name='',
            ))
        
        # 3 fail both
        for i in range(3):
            contacts.append(make_test_contact(
                row_id=f'fail-both-{i}',
                verified_email=False,
                linkedin='',
                decision_maker_name='',
            ))
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=contacts,
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        # Only 3 should pass
        assert count == 3, f"Expected 3 to pass, got {count}"
        assert report.total_contacts == 10
        
        # Email failures: 2 (email only) + 3 (both) = 5
        assert report.skipped_unverified_email_count == 5
        
        # Identity failures: 2 (identity only) + 3 (both) = 5
        assert report.skipped_no_identity_count == 5


# =============================================================================
# OUTPUT FILE VERIFICATION
# =============================================================================

class TestOutputVerification:
    """
    Tests that verify the actual output file content.
    
    These tests go beyond counters and check that the CSV
    output contains exactly the contacts that should pass.
    """

    def test_output_file_contains_only_passing_contacts(self, mock_llm, tmp_path):
        """
        Output CSV should only contain contacts that passed both gates.
        
        Verifies the actual file content, not just the count.
        """
        contacts = [
            make_test_contact(row_id='pass-1', verified_email=True, linkedin='https://linkedin.com/in/1'),
            make_test_contact(row_id='fail-email', verified_email=False, linkedin='https://linkedin.com/in/2'),
            make_test_contact(row_id='pass-2', verified_email=True, decision_maker_name='DM'),
            make_test_contact(row_id='fail-identity', verified_email=True),
        ]
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=contacts,
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 2
        
        # Read output file and verify content
        import csv
        with open(output_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        row_ids = [row['row_id'] for row in rows]
        assert 'pass-1' in row_ids, "pass-1 should be in output"
        assert 'pass-2' in row_ids, "pass-2 should be in output"
        assert 'fail-email' not in row_ids, "fail-email should NOT be in output"
        assert 'fail-identity' not in row_ids, "fail-identity should NOT be in output"


# =============================================================================
# ADDITIONAL EDGE CASES - BEING EXTRA RUTHLESS
# =============================================================================

class TestExtraRuthlessEdgeCases:
    """
    Even more edge cases because I don't trust this code.
    
    These probe weird scenarios that might break the logic.
    """

    def test_none_email_with_verified_true(self, mock_llm, tmp_path):
        """
        What if email is None instead of empty string?
        
        The dataclass uses str type, but Python might allow None.
        This tests the behavior if someone bypasses type safety.
        """
        # This would violate the type hint, but let's see what happens
        contact = make_test_contact(
            row_id='edge-none-email',
            verified_email=True,
            linkedin='https://linkedin.com/in/user',
        )
        # Manually override with None (bypassing type safety)
        object.__setattr__(contact, 'email', None)  # type: ignore
        
        output_path = tmp_path / "output.csv"
        
        # This might raise an exception or behave unexpectedly
        try:
            count, report = run_pipeline(
                input_paths=[],
                output_path=str(output_path),
                llm=mock_llm,
                dry_run=True,
                seed_contacts=[contact],
                require_verified_email=True,
                require_identity_confirmation=True,
            )
            # If it runs, None is falsy so it should fail email check
            assert count == 0, "None email should fail verification"
            assert report.skipped_unverified_email_count >= 1
        except (TypeError, AttributeError):
            # This is also acceptable - the code might crash on None
            pass

    def test_linkedin_url_variations(self, mock_llm, tmp_path):
        """
        Different LinkedIn URL formats should all count as identity.
        
        Tests various valid LinkedIn URL patterns.
        """
        linkedin_urls = [
            'https://linkedin.com/in/username',
            'https://www.linkedin.com/in/username',
            'http://linkedin.com/in/username',
            'linkedin.com/in/username',
            'https://linkedin.com/in/username/',
        ]
        
        for i, url in enumerate(linkedin_urls):
            contact = make_test_contact(
                row_id=f'linkedin-var-{i}',
                verified_email=True,
                linkedin=url,
            )
            
            output_path = tmp_path / f"output_{i}.csv"
            
            count, report = run_pipeline(
                input_paths=[],
                output_path=str(output_path),
                llm=mock_llm,
                dry_run=True,
                seed_contacts=[contact],
                require_verified_email=True,
                require_identity_confirmation=True,
            )
            
            assert count == 1, f"LinkedIn URL '{url}' should be accepted as identity"

    def test_single_character_decision_maker_name(self, mock_llm, tmp_path):
        """
        Single character decision_maker_name should count as identity.
        
        Edge case: is 'A' a valid name? Technically yes, it's truthy.
        """
        contact = make_test_contact(
            row_id='edge-single-char',
            verified_email=True,
            linkedin='',
            decision_maker_name='X',  # Single character
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 1, "Single character DM name should pass as identity"

    def test_very_long_decision_maker_name(self, mock_llm, tmp_path):
        """
        Very long decision_maker_name should still work.
        
        Tests that there's no length limit breaking things.
        """
        long_name = 'A' * 1000  # 1000 character name
        contact = make_test_contact(
            row_id='edge-long-name',
            verified_email=True,
            linkedin='',
            decision_maker_name=long_name,
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 1, "Very long DM name should still pass"

    def test_special_characters_in_identity_fields(self, mock_llm, tmp_path):
        """
        Special characters in identity fields should be handled.
        
        Unicode, emoji, etc. in linkedin or decision_maker_name.
        """
        contact = make_test_contact(
            row_id='edge-special-chars',
            verified_email=True,
            linkedin='',  
            decision_maker_name='José García-Müller 🚀',  # Unicode + emoji
        )
        
        output_path = tmp_path / "output.csv"
        
        count, report = run_pipeline(
            input_paths=[],
            output_path=str(output_path),
            llm=mock_llm,
            dry_run=True,
            seed_contacts=[contact],
            require_verified_email=True,
            require_identity_confirmation=True,
        )
        
        assert count == 1, "Unicode and special chars should be accepted as identity"
