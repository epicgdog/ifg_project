from __future__ import annotations

import csv
from pathlib import Path

from src.ingest import read_contacts


def _write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def test_apollo_style_headers(tmp_path):
    """Apollo-style 'Person First Name'/'Person Title' headers map correctly."""
    csv_path = tmp_path / "apollo.csv"
    _write_csv(
        csv_path,
        [
            "Person First Name",
            "Person Last Name",
            "Person Title",
            "Organization Name",
            "Email",
            "Organization Website",
        ],
        [
            [
                "Jake",
                "Morrison",
                "Owner",
                "Morrison Roofing",
                "jake@morrison.com",
                "morrison.com",
            ],
        ],
    )

    contacts = read_contacts([str(csv_path)])
    assert len(contacts) == 1
    c = contacts[0]
    assert c.first_name == "Jake"
    assert c.last_name == "Morrison"
    assert c.title == "Owner"
    assert c.company == "Morrison Roofing"
    assert c.email == "jake@morrison.com"
    assert c.website == "morrison.com"


def test_linkedin_style_headers(tmp_path):
    """LinkedIn-style headers (Full Name, Job Title, LinkedIn URL) map correctly."""
    csv_path = tmp_path / "linkedin.csv"
    _write_csv(
        csv_path,
        ["Full Name", "Job Title", "Company", "LinkedIn URL"],
        [["Angela Price", "Fractional CFO", "Price Advisory", "linkedin.com/in/ap"]],
    )

    contacts = read_contacts([str(csv_path)])
    assert len(contacts) == 1
    c = contacts[0]
    # full_name preserved, first/last derived from it
    assert c.full_name == "Angela Price"
    assert c.first_name == "Angela"
    assert c.last_name == "Price"
    assert c.title == "Fractional CFO"
    assert c.linkedin == "linkedin.com/in/ap"


def test_mixed_case_and_underscore_headers(tmp_path):
    """Header normalization handles mixed case and snake_case variants."""
    csv_path = tmp_path / "mixed.csv"
    _write_csv(
        csv_path,
        ["first_name", "LAST NAME", "Job_Title", "company name", "EMAIL"],
        [["Marco", "Diaz", "President", "Diaz Industrial", "m@diaz.com"]],
    )

    contacts = read_contacts([str(csv_path)])
    assert len(contacts) == 1
    c = contacts[0]
    assert c.first_name == "Marco"
    assert c.last_name == "Diaz"
    assert c.title == "President"
    assert c.company == "Diaz Industrial"
    assert c.email == "m@diaz.com"


def test_full_name_split_derives_first_and_last(tmp_path):
    """When only Full Name is present, first/last are split from it."""
    csv_path = tmp_path / "fullname.csv"
    _write_csv(
        csv_path,
        ["Name", "Title", "Company"],
        [
            ["Nora Patel", "CEPA Advisor", "Patel Exit"],
            ["Cher", "Singer", "Solo"],  # single-token full name
        ],
    )

    contacts = read_contacts([str(csv_path)])
    assert len(contacts) == 2

    assert contacts[0].full_name == "Nora Patel"
    assert contacts[0].first_name == "Nora"
    assert contacts[0].last_name == "Patel"

    # Single-token full name: first_name set, last_name empty.
    assert contacts[1].full_name == "Cher"
    assert contacts[1].first_name == "Cher"
    assert contacts[1].last_name == ""


def test_missing_email_is_empty_string(tmp_path):
    """Rows with no email column / empty email field ingest as empty strings."""
    csv_path = tmp_path / "no_email.csv"
    _write_csv(
        csv_path,
        ["First Name", "Last Name", "Title", "Company"],
        [["Rita", "Chen", "Founder", "Chen HVAC"]],
    )

    contacts = read_contacts([str(csv_path)])
    assert len(contacts) == 1
    c = contacts[0]
    # No crash; email defaults to empty string.
    assert c.email == ""
    assert c.first_name == "Rita"
