# Track 2 — Making the ForgeReach Pipeline Agentic

Status: **proposed, not implemented.** Ship the Vercel demo first (Track 1 is done). This document is the plan you asked for: how the current rule-based pipeline becomes an agent-driven one, what each agent does, and what it costs.

---

## Today's pipeline (rule-based)

```
CSV → classify (keyword scoring) → qualify (keyword scoring) → generate (single LLM call per contact, few-shot) → validate → export
```

Every stage except `generate` is deterministic keyword matching. `generate` is a single-shot prompt with no self-criticism or research. This is fast and cheap but leaves a lot of quality on the table — exactly the personalization gap flagged in GRADE.md.

## Target pipeline (agentic)

```
CSV → [Classifier Agent] → [Research Agent] → [Planner] → [Writer → Critic] loop → [Judge Agent] → export
                                                              ↑_______________|
                                                                 revise N times
```

Five distinct roles, each a small LLM call with a focused job. Total: 4–7 LLM calls per contact instead of 1. About $0.003–$0.006 per contact with DeepSeek — still cheap at 500/week (~$3).

---

## The five agents

### 1. Classifier Agent — replaces `src/scoring.py`

**Job**: Given a contact, decide audience (`owner` vs `referral_advocate`) and emit a 0–100 fit score with plain-English reasoning.

**Why upgrade**: Keyword matching misses obvious cases (a "VP of Commercial Lines" is a broker, but if the title reads "Commercial Lines Producer" the current code might miss it). It also can't weigh signals holistically — title + industry + employee count + website copy together paint a much clearer picture than any individual keyword.

**Implementation**:
- New `src/agents/classifier.py`
- Input: full `Contact` object
- Output: structured JSON `{audience, audience_reason, fit_score, fit_reason, confidence}`
- Model: DeepSeek-v3.2 with JSON mode, ~200 tokens out
- Fall back to existing `scoring.py` if LLM fails or confidence < 0.5

**Cost**: ~$0.0002 per contact

### 2. Research Agent — new capability

**Job**: Given a contact and their company, gather 3–5 concrete personalization hooks: recent news mentions, hiring signals, notable LinkedIn posts, press releases, or any other public signal. Return them as structured bullets.

**Why upgrade**: This is the #1 personalization lever that's missing today. Step-1 emails feel generic because they have nothing specific to reference. "I saw you're hiring 12 techs in Denver" lands 4–5× the response rate of "operator-led businesses in your space are creating real value right now."

**Implementation**:
- New `src/agents/researcher.py`
- Tools available to the agent:
  - `search_web(query)` — SerpAPI or Tavily (both have free tiers)
  - `linkedin_recent_posts(url)` — Apify LinkedIn Post Scraper actor (already have Apify wired)
  - `company_news(domain)` — Google News via SerpAPI
- Agent runs 2–4 tool calls, synthesizes findings into `ResearchBrief` with fields `hooks: list[str]`, `signals: list[str]`, `confidence: float`
- 30s timeout, parallel across contacts (respect Tavily/SerpAPI rate limits — 10 concurrent is safe)
- Cache per contact for 7 days in `.cache/research/`

**Cost**: ~$0.002 per contact (3–4 LLM calls + 2–3 tool calls)

### 3. Planner — lightweight, possibly not an agent

**Job**: Decide the message angle per contact: which hook from Research to lead with, which philosophy anchor from MASTER.md to ground the middle, which CTA style to use.

**Why upgrade**: Right now `messaging.py` feeds all hooks into the prompt and lets the writer pick. Explicitly picking first gives the Writer a much tighter brief and improves consistency.

**Implementation**:
- New `src/agents/planner.py` OR just a deterministic function that scores hooks against audience (won't know until we measure)
- Input: `Contact`, `ClassifiedContact`, `ResearchBrief`
- Output: `MessageBrief {lead_hook, philosophy_anchor, cta_type, tone_tilt}`

**Cost**: ~$0.0001 per contact (one short call) or $0 if deterministic

### 4. Writer → Critic loop — replaces single-shot generation in `src/messaging.py`

**Job**: Writer drafts the 3-step sequence. Critic evaluates against rubric (voice match, personalization depth, taboo phrases, CTA specificity). If Critic scores < 8/10 on any axis, Writer revises with the Critic's notes. Max 3 rounds.

**Why upgrade**: Today the sequence is whatever the model generates first. Self-criticism catches weak openings, generic middles, and flabby CTAs before they reach the validator. This is the single highest-quality-per-dollar improvement in agentic LLM patterns.

**Implementation**:
- New `src/agents/writer.py` and `src/agents/critic.py`
- Writer prompt: existing `build_sequence_prompt` + `MessageBrief`
- Critic rubric: 5 axes × 10-point scale (voice, specificity, CTA clarity, conciseness, taboo-free), plus pass/fail gate on validators
- Loop stops when all axes ≥ 8 OR max 3 iterations reached
- Log each iteration for offline evaluation

**Cost**: ~$0.001–$0.003 per contact (avg 1.5 Writer passes + 1.5 Critic passes)

### 5. Judge Agent — optional, for highest-value contacts

**Job**: When fit_score ≥ 85 (tier "high"), generate **3 variants** from Writer and have Judge pick the best one with reasoning.

**Why upgrade**: Top-tier contacts deserve the best of multiple attempts. For the other 80% of contacts, a single Writer→Critic pass is plenty.

**Implementation**:
- New `src/agents/judge.py`
- Only triggered in pipeline for contacts with `qualification_tier == "high"`
- Generates 3 Writer variants in parallel
- Judge ranks and returns the winner + runner-up (log runner-up for A/B data later)

**Cost**: ~$0.004 per high-tier contact. If 20% of contacts are high tier, average marginal cost is $0.0008.

---

## Architecture considerations

### State machine

Replace the current loop in `src/pipeline.py:run_pipeline` with a stage-based executor:

```python
class ContactState:
    contact: Contact
    classification: ClassifiedContact | None = None
    research: ResearchBrief | None = None
    brief: MessageBrief | None = None
    draft: GeneratedSequence | None = None
    critic_feedback: list[CriticNote] = []
    judge_choice: int | None = None
    status: Literal["pending", "classified", "researched", ..., "done", "failed"]
```

Each agent advances the state by one step. This makes retries, resumes, and partial-run debugging trivial.

### Orchestration: framework vs. hand-rolled

**Recommendation: hand-rolled.** The pipeline is linear; LangGraph/CrewAI buy you very little and add a dependency. Write a 50-line `AgentOrchestrator` in `src/agents/orchestrator.py` that runs stages in order with per-stage timeouts and a single retry.

Use LangGraph only if the flow becomes genuinely branching (e.g., Judge says "none of these are good, send back to Research"). That's a YAGNI call for now.

### Cost management

- DeepSeek-v3.2 is ~40× cheaper than Claude Sonnet and 10× cheaper than GPT-4o for this workload. Keep using it.
- Total cost per contact end-to-end: ~$0.003–$0.006. 500 contacts/week = $1.50–$3/week.
- Add per-run budget caps in `.env` (`MAX_LLM_DOLLARS_PER_RUN=5`).

### Parallelism

Research is IO-bound (tool calls), Classifier/Writer/Critic/Judge are LLM-bound. Both parallelize well. The existing `ThreadPoolExecutor(max_workers=10)` extends naturally — just ensure each agent respects the global budget.

### Observability

Each contact's full agent trace should be saved to `out/runs/<run_id>/traces/<row_id>.json`. This is how you'll debug failures and A/B test variants later. Surface a "View trace" link in the dashboard for each contact.

---

## Migration strategy

Don't rewrite the pipeline in one PR. Ladder it in:

| Phase | Scope | Impact |
|---|---|---|
| 2a | Ship Classifier Agent behind an `--agentic-classify` flag. Compare to keyword on 50 contacts; measure accuracy and cost. | Low risk. Validates LLM vs keyword gap. |
| 2b | Ship Research Agent, wire it into the existing `messaging.py` as an optional context block. Keep single-shot generation. | Medium impact. Personalization quality goes up materially. |
| 2c | Replace single-shot generation with Writer→Critic loop. | High impact. This is the biggest quality lever. |
| 2d | Add Judge for high-tier contacts. | Low marginal gain; defer unless 2a–2c show ceiling. |
| 2e | Retire keyword `scoring.py` fallback once Classifier confidence is proven. | Cleanup. |

Each phase is a week of work, independently shippable, and measurable on sample contacts before rolling out.

---

## What I'd do differently if we were starting from scratch

You don't need to — the current pipeline is the right scaffold. Agents slot in as drop-in replacements for specific stages. The validators, CSV export, scheduling, and UI all stay the same. The only piece that fundamentally changes shape is `src/messaging.py` → `src/agents/*`.

---

## Open questions before implementing

1. **Research API budget**: SerpAPI free tier is 100 queries/month, Tavily is 1,000/month. 500 contacts/week × 2 queries each = 4,000/month. We'd need paid tier (~$50/mo for SerpAPI, Tavily has $30/mo). Acceptable?
2. **Human-in-the-loop gate**: Should Judge's output go to a human review queue before sending, or auto-approve at tier == high? (I'd start with review-required for the first 200, then relax.)
3. **Trace retention**: Keep traces forever for learning, or 30-day TTL? Storage is cheap; disclosure is the question.

Let me know when you want Phase 2a kicked off.
