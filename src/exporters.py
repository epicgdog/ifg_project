from __future__ import annotations

from pathlib import Path

import pandas as pd


def export_instantly_campaign(input_csv: str | Path, output_csv: str | Path) -> Path:
    df = pd.read_csv(input_csv)
    out = pd.DataFrame(
        {
            "First Name": df.get("first_name", ""),
            "Last Name": df.get("last_name", ""),
            "Email": df.get("email", ""),
            "Company": df.get("company", ""),
            "Subject 1": df.get("subject_1", ""),
            "Step 1": df.get("email_step_1", ""),
            "Subject 2": df.get("subject_2", ""),
            "Step 2": df.get("email_step_2", ""),
            "Subject 3": df.get("subject_3", ""),
            "Step 3": df.get("email_step_3", ""),
            "Qualified": df.get("qualified", ""),
            "Qualification Tier": df.get("qualification_tier", ""),
        }
    )

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return output_path
