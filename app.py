from __future__ import annotations

import os
import tempfile
import json
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


def _parse_json_field(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _to_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


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
    master_persona_path = st.text_input(
        "MASTER persona path",
        value="MASTER.md",
    )
    use_master_persona = st.checkbox(
        "Use MASTER-based few-shot",
        value=True,
    )
    few_shot_k = st.slider(
        "Few-shot examples per step",
        min_value=1,
        max_value=5,
        value=3,
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
    min_fit_score_for_enrich = st.slider(
        "Min fit score for enrichment",
        min_value=0,
        max_value=90,
        value=65,
        help="Contacts below this score are skipped BEFORE enrichment to save API credits. Set to 0 to disable filtering.",
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
        openrouter_model = st.text_input(
            "OPENROUTER_MODEL",
            value=os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v3.2"),
        )
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
cfg3 = st.columns(3)
cfg3[0].metric("Model", os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v3.2"))
cfg3[1].metric("MASTER Few-shot", "On" if use_master_persona else "Off")
cfg3[2].metric("Few-shot k", str(few_shot_k))

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

st.subheader("Apollo Credit Estimator")
est_cols = st.columns(3)
estimated_discovery_calls = 0
if mode in {"API discovery only", "CSV + API merge"} and "apollo" in prospect_sources:
    estimated_discovery_calls = (int(prospect_limit) + 24) // 25
estimated_enrichment_calls = 0
if enrich:
    estimated_enrichment_calls = len(uploaded_files or []) * 25
est_cols[0].metric("Estimated discovery calls", estimated_discovery_calls)
est_cols[1].metric("Estimated enrich calls", estimated_enrichment_calls)
est_cols[2].metric(
    "Estimated total calls",
    estimated_discovery_calls + estimated_enrichment_calls,
)
st.caption(
    "Estimate only. Actual Apollo credit usage depends on plan billing rules, cache hits, and endpoint behavior."
)

run_clicked = st.button("Run Campaign Build", type="primary")

if run_clicked:
    _apply_session_env(
        {
            "OPENROUTER_API_KEY": openrouter_key,
            "OPENROUTER_MODEL": openrouter_model,
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
                    min_fit_score_for_enrich=min_fit_score_for_enrich,
                    prospect=prospect,
                    prospect_sources=prospect_sources,
                    prospect_limit=int(prospect_limit),
                    hunter_domains=[
                        d.strip() for d in hunter_domains_input.split(",") if d.strip()
                    ],
                    referral_advocates_only=referral_advocates_only,
                    state=state,
                    use_master_persona=use_master_persona,
                    master_persona_path=master_persona_path,
                    few_shot_k=few_shot_k,
                )

                df = pd.read_csv(result.output_path)
                report = result.report.to_dict()

                st.success("Campaign build complete.")

                st.subheader("Executive Summary")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Contacts", report["total_contacts"])
                m2.metric(
                    "Skipped (Low Fit)",
                    report["skipped_low_fit_count"],
                    delta=f"-{report['skipped_low_fit_count']}"
                    if report["skipped_low_fit_count"] > 0
                    else None,
                    delta_color="inverse",
                )
                m3.metric(
                    "Enriched",
                    report["enriched_count"],
                    delta=_metric_delta(
                        report["enriched_count"],
                        max(
                            1,
                            report["total_contacts"] - report["skipped_low_fit_count"],
                        ),
                    ),
                )
                m4.metric("High Priority", report["high_priority_count"])

                m5, m6, m7 = st.columns(3)
                m5.metric("Review Flagged", report["review_flagged_count"])
                m6.metric("Avg Fit Score", report["avg_fit_score"])
                m7.metric(
                    "Skipped (No LinkedIn)",
                    report.get("skipped_missing_linkedin_count", 0),
                )

                st.subheader("Channel Summary")
                ch1, ch2, ch3 = st.columns(3)
                ch1.metric("Owners", report.get("owner_count", 0))
                ch2.metric(
                    "Referral Advocates", report.get("referral_advocate_count", 0)
                )
                ch3.metric(
                    "Owner High Readiness",
                    report.get("owner_high_readiness_count", 0),
                )

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
                    # Contact Profile Viewer with navigation
                    st.subheader("Contact Profile Viewer")

                    # Navigation controls
                    nav_cols = st.columns([1, 3, 1])
                    current_idx = st.session_state.get("profile_idx", 0)
                    current_idx = max(0, min(current_idx, len(view_df) - 1))
                    st.session_state["profile_idx"] = current_idx

                    if nav_cols[0].button("← Previous", key="prev_contact"):
                        st.session_state["profile_idx"] = max(0, current_idx - 1)
                        current_idx = st.session_state["profile_idx"]
                        st.rerun()

                    nav_cols[1].markdown(
                        f"**Contact {current_idx + 1} of {len(view_df)}**"
                    )

                    if nav_cols[2].button("Next →", key="next_contact"):
                        st.session_state["profile_idx"] = min(
                            len(view_df) - 1, current_idx + 1
                        )
                        current_idx = st.session_state["profile_idx"]
                        st.rerun()

                    # Quick index selector
                    quick_idx = nav_cols[1].selectbox(
                        "Jump to contact",
                        options=range(len(view_df)),
                        index=current_idx,
                        format_func=lambda i: (
                            f"{view_df.iloc[i]['full_name']} ({view_df.iloc[i]['company']})"
                        ),
                        key="quick_contact_select",
                    )
                    if quick_idx != current_idx:
                        st.session_state["profile_idx"] = quick_idx
                        current_idx = quick_idx
                        st.rerun()

                    # Profile card
                    selected = view_df.iloc[current_idx]

                    profile_cols = st.columns([1, 1])

                    with profile_cols[0]:
                        st.markdown("### Profile")
                        st.markdown(f"**{selected.get('full_name', '')}**")
                        st.markdown(
                            f"**{selected.get('title', '')}** @ {selected.get('company', '')}"
                        )

                        contact_info = []
                        if selected.get("email"):
                            contact_info.append(f"📧 {selected.get('email')}")
                        if selected.get("linkedin"):
                            contact_info.append(
                                f"💼 [LinkedIn]({selected.get('linkedin')})"
                            )
                        if selected.get("website"):
                            contact_info.append(f"🌐 {selected.get('website')}")
                        if selected.get("city") and selected.get("state"):
                            contact_info.append(
                                f"📍 {selected.get('city')}, {selected.get('state')}"
                            )

                        if contact_info:
                            st.markdown("\n".join(contact_info))

                        st.divider()

                        # Badges
                        badge_cols = st.columns(2)
                        audience = selected.get("audience", "")
                        badge_cols[0].markdown(f"🎯 **Audience:** `{audience}`")
                        qualified = selected.get("qualified", "")
                        badge_cols[1].markdown(f"✅ **Qualified:** `{qualified}`")

                        # Matched signals as tags
                        matched = selected.get("matched_signals", "")
                        if matched:
                            st.caption("Matched Signals:")
                            signals = [
                                s.strip() for s in matched.split(";") if s.strip()
                            ]
                            signal_cols = st.columns(min(3, len(signals)))
                            for i, sig in enumerate(signals[:6]):
                                signal_cols[i % 3].markdown(f"🏷️ `{sig}`")

                        # Enrichment provenance
                        enriched_at = selected.get("enriched_at", "")
                        if enriched_at:
                            st.caption("Enrichment Sources:")
                            prov_cols = st.columns(2)
                            title_src = selected.get("title_source", "csv")
                            company_src = selected.get("company_source", "csv")
                            industry_src = selected.get("industry_source", "csv")
                            prov_cols[0].markdown(f"- Title: `{title_src}`")
                            prov_cols[0].markdown(f"- Company: `{company_src}`")
                            prov_cols[1].markdown(f"- Industry: `{industry_src}`")

                    with profile_cols[1]:
                        st.markdown("### Scores")

                        # Fit score with color
                        fit_score = _to_int(selected.get("fit_score", 0))
                        if fit_score >= 75:
                            fit_color = "🟢"
                        elif fit_score >= 55:
                            fit_color = "🟡"
                        else:
                            fit_color = "🔴"

                        st.metric("Fit Score", f"{fit_color} {fit_score}")

                        # Owner readiness
                        readiness_tier = selected.get("owner_readiness_tier", "n/a")
                        readiness_conf = selected.get("owner_readiness_confidence", 0)
                        if readiness_tier == "high":
                            readiness_icon = "🟢"
                        elif readiness_tier == "medium":
                            readiness_icon = "🟡"
                        else:
                            readiness_icon = "⚪"

                        st.metric(
                            "Owner Readiness",
                            f"{readiness_icon} {readiness_tier} ({readiness_conf:.2f})",
                        )

                        # Qualification score
                        qual_score = _to_int(selected.get("qualification_score", 0))
                        qual_tier = selected.get("qualification_tier", "low")
                        if qual_tier == "high":
                            qual_icon = "🟢"
                        elif qual_tier == "medium":
                            qual_icon = "🟡"
                        else:
                            qual_icon = "⚪"

                        st.metric(
                            "Qualification", f"{qual_icon} {qual_score} ({qual_tier})"
                        )

                        # Fit reason
                        fit_reason = selected.get("fit_reason", "")
                        if fit_reason:
                            with st.expander("Fit Reason"):
                                st.write(fit_reason)

                        # Qualification reason
                        qual_reason = selected.get("qualification_reason", "")
                        if qual_reason:
                            with st.expander("Qualification Reason"):
                                st.write(qual_reason)

                    # Score breakdown charts
                    st.markdown("### Score Breakdown")
                    chart_cols = st.columns(2)

                    fit_breakdown = _parse_json_field(
                        selected.get("fit_breakdown_json", "")
                    )
                    qual_breakdown = _parse_json_field(
                        selected.get("qualification_breakdown_json", "")
                    )

                    with chart_cols[0]:
                        fit_adjustments = fit_breakdown.get("adjustments", [])
                        if fit_adjustments:
                            fit_rows = [
                                {
                                    "rule": str(item.get("rule", "")),
                                    "delta": _to_int(item.get("delta", 0)),
                                    "evidence": ", ".join(
                                        [str(e) for e in item.get("evidence", [])]
                                    ),
                                }
                                for item in fit_adjustments
                            ]
                            cumulative = fit_breakdown.get("base", 40)
                            waterfall_points = [{"stage": "base", "score": cumulative}]
                            for row in fit_rows:
                                cumulative += row["delta"]
                                waterfall_points.append(
                                    {
                                        "stage": row["rule"],
                                        "score": max(0, min(100, cumulative)),
                                    }
                                )
                            waterfall_df = pd.DataFrame(waterfall_points).set_index(
                                "stage"
                            )
                            st.markdown("**Fit Score Waterfall**")
                            st.bar_chart(waterfall_df)

                    with chart_cols[1]:
                        qual_adjustments = qual_breakdown.get("adjustments", [])
                        if qual_adjustments:
                            qual_rows = [
                                {
                                    "rule": str(item.get("rule", "")),
                                    "delta": _to_int(item.get("delta", 0)),
                                }
                                for item in qual_adjustments
                            ]
                            qual_df = pd.DataFrame(qual_rows)
                            st.markdown("**Qualification Adjustments**")
                            st.dataframe(
                                qual_df, use_container_width=True, hide_index=True
                            )

                    # Email sequence preview (replaces old Score Inspector)
                    st.subheader("Email Sequence Preview")
                    seq_cols = st.columns(3)
                    with seq_cols[0]:
                        st.markdown("**Step 1**")
                        st.markdown(selected.get("email_step_1", ""))
                    with seq_cols[1]:
                        st.markdown("**Step 2**")
                        st.markdown(selected.get("email_step_2", ""))
                    with seq_cols[2]:
                        st.markdown("**Step 3**")
                        st.markdown(selected.get("email_step_3", ""))

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
