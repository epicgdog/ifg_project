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


def _apply_session_env(overrides: dict[str, str]) -> None:
    for key, value in overrides.items():
        cleaned = value.strip()
        if cleaned:
            os.environ[key] = cleaned


st.title("ForgeReach Prospecting and Outreach")
st.caption(
    "Run CSV processing, optional API discovery, qualification, and campaign export from one place"
)

with st.sidebar:
    st.header("Pipeline Mode")
    mode = st.radio(
        "Select run mode",
        options=[
            "CSV only",
            "API discovery only",
            "CSV + API merge",
        ],
        index=0,
    )

    st.header("Run Settings")
    dry_run = st.checkbox("Dry run (no LLM API calls)", value=True)
    enrich = st.checkbox("Enable enrichment (Apollo/Apify)", value=False)
    enrich_cache = st.checkbox("Enable enrichment cache", value=True)
    enrich_cache_ttl = st.number_input("Cache TTL (hours)", min_value=1, value=24)
    enrich_timeout = st.number_input("Enrichment timeout (sec)", min_value=10, value=60)
    enrich_retries = st.number_input("Enrichment retries", min_value=0, value=3)

    st.header("Profiles")
    voice_profile_path = st.text_input(
        "Voice profile path",
        value="data/voice_profile.json",
    )
    icp_profile_path = st.text_input(
        "ICP profile path",
        value="data/icp_profile.json",
    )
    min_qualification_score = st.slider(
        "Minimum qualification score",
        min_value=40,
        max_value=90,
        value=60,
    )

    st.header("Prospecting")
    referral_advocates_only = st.checkbox(
        "Referral advocates only",
        value=True,
        help="Audience B mode for trusted advisor sourcing",
    )
    state = st.text_input("State filter", value="CO")
    prospect_sources = st.multiselect(
        "Prospecting sources",
        options=["apollo", "hunter"],
        default=["apollo"],
    )
    prospect_limit = st.number_input("Prospect limit", min_value=1, value=25)
    hunter_domains_input = st.text_input(
        "Hunter domains (comma-separated)",
        value="",
    )

    with st.expander("API keys (session only)"):
        st.caption("Optional: overrides .env for this app session only")
        openrouter_key = st.text_input("OPENROUTER_API_KEY", type="password")
        apollo_key = st.text_input("APOLLO_API_KEY", type="password")
        hunter_key = st.text_input("HUNTER_API_KEY", type="password")
        apify_token = st.text_input("APIFY_API_TOKEN", type="password")
        apify_actor = st.text_input("APIFY_LINKEDIN_ACTOR_ID")

st.subheader("Configuration Health")
cfg1 = st.columns(4)
cfg1[0].metric(
    "OpenRouter", "Configured" if _env_ok("OPENROUTER_API_KEY") else "Missing"
)
cfg1[1].metric("Apollo", "Configured" if _env_ok("APOLLO_API_KEY") else "Missing")
cfg1[2].metric("Hunter", "Configured" if _env_ok("HUNTER_API_KEY") else "Missing")
cfg1[3].metric(
    "Apify",
    "Configured"
    if (_env_ok("APIFY_API_TOKEN") and _env_ok("APIFY_LINKEDIN_ACTOR_ID"))
    else "Missing",
)

cfg2 = st.columns(4)
cfg2[0].metric("Mode", mode)
cfg2[1].metric("RA Mode", "On" if referral_advocates_only else "Off")
cfg2[2].metric("State", state.upper() if state else "CO")
cfg2[3].metric("Dry Run", "On" if dry_run else "Off")

st.subheader("CSV Inputs")
uploaded_files = st.file_uploader(
    "Upload one or more CSV files",
    type=["csv"],
    accept_multiple_files=True,
)

use_sample_default = mode == "CSV only" and not uploaded_files
use_sample = st.checkbox(
    "Use sample file (data/sample_contacts.csv)",
    value=use_sample_default,
)

run_clicked = st.button("Run Campaign Build", type="primary")

if run_clicked:
    _apply_session_env(
        {
            "OPENROUTER_API_KEY": openrouter_key,
            "APOLLO_API_KEY": apollo_key,
            "HUNTER_API_KEY": hunter_key,
            "APIFY_API_TOKEN": apify_token,
            "APIFY_LINKEDIN_ACTOR_ID": apify_actor,
        }
    )

    input_paths: list[str] = []
    for uploaded in uploaded_files or []:
        input_paths.append(_save_uploaded_csv(uploaded))
    if use_sample:
        input_paths.append("data/sample_contacts.csv")

    prospect = mode in {"API discovery only", "CSV + API merge"}

    if mode == "CSV only" and not input_paths:
        st.error("Upload at least one CSV or enable sample file.")
    elif mode == "CSV + API merge" and not input_paths:
        st.error("CSV + API merge mode needs at least one CSV input.")
    elif not prospect_sources and prospect:
        st.error("Select at least one prospect source for API discovery.")
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
                    referral_advocates_only=referral_advocates_only,
                    state=state,
                )

                df = pd.read_csv(result.output_path)
                report = result.report.to_dict()

                st.success("Campaign build complete.")

                st.subheader("Executive Summary")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Contacts", report["total_contacts"])
                m2.metric(
                    "Enriched",
                    report["enriched_count"],
                    delta=_metric_delta(
                        report["enriched_count"], report["total_contacts"]
                    ),
                )
                m3.metric(
                    "Qualified",
                    report["qualified_count"],
                    delta=_metric_delta(
                        report["qualified_count"], report["total_contacts"]
                    ),
                )
                m4.metric("High Priority", report["high_priority_count"])

                m5, m6 = st.columns(2)
                m5.metric("Review Flagged", report["review_flagged_count"])
                m6.metric("Avg Fit Score", report["avg_fit_score"])

                st.subheader("Audience Split")
                if not df.empty and "audience" in df.columns:
                    st.bar_chart(df["audience"].value_counts().rename_axis("audience"))
                else:
                    st.info("No rows returned for this run.")

                st.subheader("Campaign Review")
                view_df = df.copy()

                if "audience" in view_df.columns and not view_df.empty:
                    selected_audiences = st.multiselect(
                        "Filter by audience",
                        options=sorted(view_df["audience"].dropna().unique().tolist()),
                        default=sorted(view_df["audience"].dropna().unique().tolist()),
                    )
                    if selected_audiences:
                        view_df = view_df[view_df["audience"].isin(selected_audiences)]

                only_qualified = st.checkbox("Only qualified targets", value=True)
                if only_qualified and "qualified" in view_df.columns:
                    view_df = view_df[view_df["qualified"] == "yes"]

                if view_df.empty:
                    st.warning("No contacts match current filters.")
                else:
                    preview_cols = [
                        "full_name",
                        "company",
                        "email",
                        "audience",
                        "fit_score",
                        "qualified",
                        "qualification_score",
                        "qualification_tier",
                        "review_flag",
                        "validation_passed",
                    ]
                    available_cols = [c for c in preview_cols if c in view_df.columns]
                    st.dataframe(view_df[available_cols], use_container_width=True)

                    st.subheader("Sequence Preview")
                    idx = st.selectbox(
                        "Select contact",
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
                campaign_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download campaign_ready.csv",
                    data=campaign_bytes,
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
