from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.exporters import export_instantly_campaign
from src.ui_service import run_campaign_pipeline


load_dotenv()


st.set_page_config(
    page_title="ForgeReach Dashboard",
    page_icon=":email:",
    layout="wide",
)


def _env_ok(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _save_uploaded_csv(uploaded_file) -> str:
    temp_dir = Path(tempfile.mkdtemp(prefix="forgereach_upload_"))
    file_path = temp_dir / uploaded_file.name
    file_path.write_bytes(uploaded_file.getbuffer())
    return str(file_path)


def _metric_delta(value: int, total: int) -> str:
    if total <= 0:
        return "0%"
    return f"{round((value / total) * 100)}%"


st.title("ForgeReach Prospecting and Outreach")
st.caption(
    "AI-powered targeting and personalized founder-led outreach in Kory Mitchell's voice"
)

with st.sidebar:
    st.header("Run Settings")
    dry_run = st.checkbox("Dry run (no LLM API calls)", value=True)
    enrich = st.checkbox("Enable enrichment (Apollo/Apify)", value=False)
    enrich_cache = st.checkbox("Enable enrichment cache", value=True)
    enrich_cache_ttl = st.number_input("Cache TTL (hours)", min_value=1, value=24)
    enrich_timeout = st.number_input("Enrichment timeout (sec)", min_value=10, value=60)
    enrich_retries = st.number_input("Enrichment retries", min_value=0, value=3)
    voice_profile_path = st.text_input(
        "Voice profile path",
        value="data/voice_profile.json",
        help="Leave default unless you have a custom profile.",
    )
    icp_profile_path = st.text_input(
        "ICP profile path",
        value="data/icp_profile.json",
        help="Profile used to qualify targets.",
    )
    min_qualification_score = st.slider(
        "Minimum qualification score",
        min_value=40,
        max_value=90,
        value=60,
    )

    st.subheader("Prospecting (Phase 2)")
    prospect = st.checkbox("Enable API prospect discovery", value=False)
    prospect_sources = st.multiselect(
        "Prospecting sources",
        options=["apollo", "hunter"],
        default=["apollo"],
    )
    prospect_limit = st.number_input("Prospect limit", min_value=1, value=25)
    hunter_domains_input = st.text_input(
        "Hunter domains (comma-separated)",
        value="",
        help="Used when Hunter source is selected.",
    )

st.subheader("Configuration Health")
cfg_cols = st.columns(3)
cfg_cols[0].metric(
    "OpenRouter", "Configured" if _env_ok("OPENROUTER_API_KEY") else "Missing"
)
cfg_cols[1].metric("Apollo", "Configured" if _env_ok("APOLLO_API_KEY") else "Missing")
cfg_cols[2].metric(
    "Apify",
    "Configured"
    if (_env_ok("APIFY_API_TOKEN") and _env_ok("APIFY_LINKEDIN_ACTOR_ID"))
    else "Missing",
)
cfg_cols2 = st.columns(3)
cfg_cols2[0].metric("Hunter", "Configured" if _env_ok("HUNTER_API_KEY") else "Missing")
cfg_cols2[1].metric("Prospecting", "On" if prospect else "Off")
cfg_cols2[2].metric("Dry Run", "On" if dry_run else "Off")

st.subheader("Prospect Input")
uploaded = st.file_uploader(
    "Upload contacts CSV",
    type=["csv"],
    help="Use Apollo/LinkedIn/Hunter style exports.",
)

use_sample = st.checkbox(
    "Use sample file (data/sample_contacts.csv)", value=not bool(uploaded)
)

run_clicked = st.button("Run Campaign Build", type="primary")

if run_clicked:
    input_paths: list[str] = []
    if uploaded:
        input_paths.append(_save_uploaded_csv(uploaded))
    if use_sample:
        input_paths.append("data/sample_contacts.csv")

    if not input_paths:
        st.error("Please upload a CSV or enable sample file.")
    else:
        with st.spinner("Running pipeline..."):
            try:
                result = run_campaign_pipeline(
                    input_paths=input_paths,
                    dry_run=dry_run,
                    enrich=enrich,
                    enrich_cache=enrich_cache,
                    enrich_cache_ttl=int(enrich_cache_ttl),
                    enrich_timeout=int(enrich_timeout),
                    enrich_retries=int(enrich_retries),
                    voice_profile_path=voice_profile_path or None,
                    icp_profile_path=icp_profile_path,
                    min_qualification_score=min_qualification_score,
                    prospect=prospect,
                    prospect_sources=prospect_sources,
                    prospect_limit=int(prospect_limit),
                    hunter_domains=[
                        d.strip() for d in hunter_domains_input.split(",") if d.strip()
                    ],
                )

                df = pd.read_csv(result.output_path)
                report = result.report.to_dict()

                st.success("Campaign build complete.")

                st.subheader("Executive Summary")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Contacts", report["total_contacts"])
                c2.metric(
                    "Enriched",
                    report["enriched_count"],
                    delta=_metric_delta(
                        report["enriched_count"], report["total_contacts"]
                    ),
                )
                c3.metric(
                    "Qualified",
                    report["qualified_count"],
                    delta=_metric_delta(
                        report["qualified_count"], report["total_contacts"]
                    ),
                )
                c4.metric("High Priority", report["high_priority_count"])

                c5, c6 = st.columns(2)
                c5.metric("Review Flagged", report["review_flagged_count"])
                c6.metric("Avg Fit Score", report["avg_fit_score"])

                st.subheader("Audience Split")
                if "audience" in df.columns and not df.empty:
                    audience_counts = (
                        df["audience"].value_counts().rename_axis("audience")
                    )
                    st.bar_chart(audience_counts)

                st.subheader("Campaign Review")
                audience_filter = st.multiselect(
                    "Filter by audience",
                    options=sorted(df["audience"].dropna().unique().tolist())
                    if "audience" in df.columns
                    else [],
                    default=sorted(df["audience"].dropna().unique().tolist())
                    if "audience" in df.columns
                    else [],
                )

                view_df = df.copy()
                if audience_filter and "audience" in view_df.columns:
                    view_df = view_df[view_df["audience"].isin(audience_filter)]

                only_qualified = st.checkbox("Only qualified targets", value=True)
                if only_qualified and "qualified" in view_df.columns:
                    view_df = view_df[view_df["qualified"] == "yes"]

                st.dataframe(
                    view_df[
                        [
                            "full_name",
                            "company",
                            "audience",
                            "fit_score",
                            "qualified",
                            "qualification_score",
                            "qualification_tier",
                            "review_flag",
                            "validation_passed",
                        ]
                    ]
                    if not view_df.empty
                    else view_df,
                    use_container_width=True,
                )

                st.subheader("Sequence Preview")
                if not view_df.empty:
                    idx = st.selectbox(
                        "Select row",
                        options=view_df.index.tolist(),
                        format_func=lambda i: (
                            f"{view_df.loc[i, 'full_name']} - {view_df.loc[i, 'company']}"
                        ),
                    )
                    selected = view_df.loc[idx]
                    st.markdown(f"**Step 1**\n\n{selected.get('email_step_1', '')}")
                    st.markdown(f"**Step 2**\n\n{selected.get('email_step_2', '')}")
                    st.markdown(f"**Step 3**\n\n{selected.get('email_step_3', '')}")

                st.subheader("Download")
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download campaign_ready.csv",
                    data=csv_bytes,
                    file_name="campaign_ready.csv",
                    mime="text/csv",
                )

                instantly_path = result.output_path.parent / "instantly_campaign.csv"
                export_instantly_campaign(result.output_path, instantly_path)
                st.download_button(
                    label="Download instantly_campaign.csv",
                    data=instantly_path.read_bytes(),
                    file_name="instantly_campaign.csv",
                    mime="text/csv",
                )

                st.subheader("Run Report")
                st.json(report)

            except Exception as exc:
                st.error(f"Pipeline run failed: {exc}")
