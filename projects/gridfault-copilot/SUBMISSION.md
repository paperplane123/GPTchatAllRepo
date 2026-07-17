# OpenAI Build Week submission package

Status: **working draft — not yet submitted**

## Category

**Work & Productivity**

GridFault Copilot helps distribution-grid control-room and engineering teams turn incomplete fault evidence into an explainable section ranking, an explicit diagnosability decision, and the next-best observation.

## Project title

**GridFault Copilot — Know When a Grid Fault Can Actually Be Diagnosed**

## One-line pitch

An explainable AI copilot that ranks likely distribution-grid fault sections, admits when evidence is insufficient, and recommends the next measurement that will reduce uncertainty fastest.

## Project description

Distribution-grid fault tools are usually optimized to produce an answer. In real control rooms, the more important question is often whether the available evidence supports any reliable answer at all.

GridFault Copilot combines radial topology, voltage deviation, zero-sequence current, estimated fault resistance, protection events, and telemetry coverage. It produces:

1. a ranked list of likely fault sections;
2. fault-type assessment and confidence;
3. a first-class **diagnosable / ambiguous** decision;
4. an evidence trace an operator can inspect;
5. the next-best observation, such as a downstream current trace or switch-state verification;
6. an optional GPT-5.6 operator brief generated through the OpenAI Responses API.

The MVP includes three interactive cases: a clear grounded event, a high-resistance weak fault, and an ambiguous event with sparse telemetry. Users can change every measurement and immediately see the section ranking, confidence, diagnosability, evidence, topology coloring, and recommendation update.

The current scoring engine is deliberately transparent and physics-inspired rather than presented as a trained production model. This makes the demo honest and testable. The production path is to replace or augment the baseline with a graph foundation model while preserving the same diagnosability and evidence interfaces.

## How GPT-5.6 is used

When `OPENAI_API_KEY` is configured, the local Python server sends the compact diagnostic JSON to the OpenAI Responses API using `gpt-5.6`. GPT-5.6 converts structured evidence into a concise control-room brief with four sections: assessment, evidence, uncertainty, and recommended next action.

The server instruction explicitly prohibits invented readings, breaker states, certainty, or autonomous switching commands. The API key stays server-side. Without a key, the project remains fully runnable and returns a deterministic local brief.

## How Codex accelerated the build

Codex/ChatGPT was used to:

- turn a distribution-grid research concept into a judgeable product flow;
- design the diagnosability-first interaction model;
- implement the zero-dependency responsive frontend;
- implement the explainable scoring and topology visualization;
- build the server-side Responses API adapter and local fallback;
- draft safety boundaries, setup documentation, and the submission narrative;
- organize the project inside the public repository.

Before submission, add the Codex `/feedback` Session ID containing the majority of the core implementation:

```text
CODEX_SESSION_ID=TODO
```

## Three-minute demo script

### 0:00–0:20 — The problem

“Most fault-location systems always output a location. Grid operators need a system that can also say: the current evidence is not sufficient, and here is the next observation that would make it sufficient.”

### 0:20–0:55 — Clear event

Open **Clear grounded feeder event** and click **Run diagnosability analysis**.

Show:

- the topology highlighting the most likely section;
- a high-confidence single-phase-to-ground assessment;
- the diagnosable badge;
- the ranked section probabilities;
- the evidence trace.

### 0:55–1:35 — High-resistance weak fault

Switch to **High-resistance weak fault**.

Explain that the zero-sequence signal and voltage deviation are weaker, fault resistance is high, and no protection event is available. Show how confidence decreases and the next-best observation changes to a more sensitive zero-sequence measurement.

### 1:35–2:10 — Ambiguous sparse telemetry

Switch to **Sparse telemetry ambiguity**.

Show the amber ambiguous state. Increase telemetry coverage and rerun. Explain that diagnosability is treated as an output, not an afterthought.

### 2:10–2:40 — GPT-5.6 brief

Click **Generate operator brief** with `OPENAI_API_KEY` configured.

Show GPT-5.6 translating the compact diagnostic JSON into a concise operator brief while preserving uncertainty and the human-authorization boundary.

### 2:40–3:00 — Impact and close

“GridFault Copilot is not an autonomous protection device. It is an uncertainty-aware decision-support interface. The same pattern can be used wherever industrial AI must know when not to guess.”

## Judge testing instructions

```bash
git clone https://github.com/paperplane123/GPTchatAllRepo.git
cd GPTchatAllRepo/projects/gridfault-copilot
python server.py
```

Open `http://127.0.0.1:8787`.

Optional GPT-5.6 mode:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-5.6"
python server.py
```

## Submission checklist

- [x] Public repository
- [x] Runnable project
- [x] README with setup and architecture
- [x] Sample scenarios embedded in the UI
- [x] GPT-5.6 Responses API integration
- [x] No-key local fallback
- [x] Safety and scope statement
- [ ] Verify participant eligibility under the official rules
- [ ] Claim free Codex credits before the Resources-tab deadline
- [ ] Run the project locally and capture final screenshots
- [ ] Record and publish a public YouTube video under three minutes
- [ ] Add the video URL
- [ ] Add the Codex `/feedback` Session ID
- [ ] Add an open-source license at repository or project level
- [ ] Create a stable demo URL or provide local test instructions
- [ ] Complete and submit the Devpost form before July 21, 2026 at 5:00 PM PT

## Links to fill before submission

```text
REPOSITORY=https://github.com/paperplane123/GPTchatAllRepo/tree/build-week/gridfault-copilot/projects/gridfault-copilot
DEMO_URL=TODO
VIDEO_URL=TODO
CODEX_SESSION_ID=TODO
```
