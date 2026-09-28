---
title: Tarski Canonical Taxonomy of Learning Capabilities
taxonomy_version: "3.1"
taxonomy_schema_version: "1.0"
supersedes: "3.0"
status: stable_review_draft
construct_count: 137
domain_count: 10
canonical_format: markdown
canonical_bytes: "UTF-8, no BOM, LF line endings, Unicode NFC, single trailing LF"
generated_docx: Tarski_Canonical_Taxonomy_of_Learning_Capabilities_Draft_3_1.docx
date: "2026-09-26"
---

# Tarski Canonical Taxonomy of Learning Capabilities

Draft 3.1 · Stable review draft · A reasoning specification for learning in an AI-augmented environment

> **LOCKED DESIGN MAXIM** Reason broadly. Report selectively. Preserve everything underneath.

**Status.** This is a working specification for DRE reasoning and learning evaluation, not a validated psychometric instrument and not a fixed teacher-facing dashboard. Draft 3.1 is a narrow contract revision of Draft 3: it adds stable identifiers, controlled vocabularies and contract rules, and fixes references. No construct has been added, removed, renamed or reworded. The Markdown file is the canonical form; the Word file is generated from it.

# Contents

| **Section** | **Purpose** |
| --- | --- |
| **PART I · DRE Reasoning Architecture** | Why the taxonomy exists; how the DRE traverses, routes, compares and synthesises evidence; how teacher reporting remains selective. |
| **1. Purpose and design decisions** | Search space vs report; coverage vs communication; capabilities rather than traits. |
| **2. Required multi-pass DRE process** | Anti-shortcut rule; coverage traversal; evidence routing; longitudinal comparison; significance synthesis. |
| **3. Episode evidence model** | Coverage states; judgement; evidence; confidence; confounds; primary-home rule; canonical DRE evidence rules; observation layer; contract rules. |
| **4. Developmental trajectory** | Change, comparability, stability, retention, transfer, independence and responsiveness to learning. |
| **5. Teacher-facing reporting** | 3–6 findings by significance; drill-down underneath; dashboard postponed. |
| **PART II · Canonical Taxonomy** | The internal coverage spine and detailed constructs. |
| **6. Taxonomy boundaries and era tags** | How nearby domains differ; F / A+ / AI. |
| **Controlled vocabularies** | Machine-readable identifiers for coverage states, judgements, trajectory states, passes and era tags. |
| **D01–D10. Ten internal domains (§7–§16)** | Agency; metacognition; knowledge coherence; conceptual/mechanistic understanding; transfer; reasoning/logic/systems; evidence; creativity; execution; AI orchestration. |
| **Appendices** | Routing examples; evidence exemplars; longitudinal record; proposed teacher report; AI-era differentiation; Draft 3 change note; Draft 3.1 change note. |

# PART I · DRE Reasoning Architecture

## 1. Purpose and design decisions

**The taxonomy is the DRE's search landscape, not the teacher's report.** Its job is to make important learning phenomena hard to omit. The DRE should inspect the provenance broadly, test competing interpretations, and only then surface the few findings a teacher needs to notice.

> **DO NOT CONFLATE THESE** Coverage completeness asks whether the DRE walked the relevant learning landscape. Report completeness asks whether the teacher now knows what matters. The first should be broad. The second should be minimal.

| **Design decision** | **Meaning** |
| --- | --- |
| **Taxonomy ≠ report** | The taxonomy defines what the DRE must consider. It does not prescribe what a teacher must see. |
| **Capabilities ≠ personality traits** | The system evaluates demonstrated capability in context: “strong persistence was demonstrated in this episode”, not “this learner is persistent”. |
| **No evidence ≠ weakness** | No meaningful opportunity, not relevant, and insufficient evidence are valid outcomes. They must never become zero. |
| **Episode ≠ trajectory** | A single sitting describes behaviour in one context. Developmental claims require comparable evidence over time. |
| **Breadth inside, clarity outside** | The internal consideration file may be large; the teacher-facing findings layer should normally be short. |
| **UI must not freeze the ontology** | The ten internal domains are a coverage spine. They do not automatically become ten gauges. |

**The physician rule.** A good physician may consider many possibilities and still write a concise clinical impression. Likewise, a large taxonomy means many questions the DRE is not allowed to skip—not many rows on a teacher report.

## 2. Required multi-pass DRE process

> **ANTI-SHORTCUT RULE** The DRE may form provisional hypotheses early, but it must not finalise an interpretation because the first coherent story has appeared. No synthesis is final until coverage traversal, evidence routing, counter-evidence/confound checks and any available longitudinal comparison are complete.

| **Pass** | **Required action** |
| --- | --- |
| **Pass 0 · Evidence assembly** | Assemble provenance streams, student artifact(s), task context, relevant external evidence and prior comparable episodes. Mark capture gaps before interpretation. |
| **Pass 1 · Coverage traversal** | Walk the canonical domains and constructs. For each construct, record a coverage state. The purpose is to prove the landscape was considered, not to fill every cell. |
| **Pass 2 · Evidence routing** | Assign every material analytical observation a primary evidentiary home. Supporting context may be cited elsewhere, but the same observation must not independently move multiple constructs. |
| **Pass 3 · Episode evaluation** | For adequately evidenced constructs, weigh supportive evidence, concern evidence, alternative explanations and confounds; then form a bounded judgement with confidence. |
| **Pass 4 · Systems / reasoning integrity check** | Where the task involves complex reasoning, test whether the learner traced consequences deeply enough, maintained relevant constraints, considered interactions and avoided premature closure or local cognitive capture. |
| **Pass 5 · Longitudinal comparison** | Where comparable history exists, evaluate trajectory, task challenge, scaffolding, independence, retention, transfer and responsiveness to feedback. Do not compare raw results across incomparable conditions. |
| **Pass 6 · Significance synthesis** | Ask what a thoughtful teacher most needs to notice now. Developmental change may outrank absolute level; a decline from a strength may outrank a static weakness. |
| **Pass 7 · Teacher report + mentoring move** | Write a concise findings layer, identify a useful strength to leverage or next learning opportunity where appropriate, and preserve the deeper reasoning for drill-down and audit. |

**Coarse-to-fine implementation.** Pass 1 requires that every construct ends with a coverage state; it does not require full Pass 3 evaluation of every construct. An implementation may sweep coarse-to-fine: assess the ten domains for relevance and opportunity, populate construct coverage states with lightweight rules, retrieval or model calls, and reserve expensive reasoning for the subset of constructs that are genuinely in play. A domain-level screen may prioritise or accelerate the walk, but it must not silently assign all child constructs a state without a recorded basis for each. The anti-shortcut rule is unchanged—no synthesis is final until the walk is complete—but the walk may be cheap where the evidence makes it obviously so.

## 3. Episode evidence model

### 3.1 Coverage states: proving the walk

| **Coverage state** | **Meaning** |
| --- | --- |
| **Relevant evidence found** | Enough relevant evidence exists to support an episode judgement. |
| **Relevant but insufficient** | The construct was in play, but evidence is too thin, ambiguous or incomplete to judge fairly. |
| **No meaningful opportunity** | The episode did not provide a fair opportunity for the capability to appear. |
| **Not relevant to this episode** | The work was of the wrong kind for this construct. |
| **Considered, no material finding** | The DRE looked and found nothing educationally significant enough to carry forward. |

*These states are evidence that the DRE completed the walk. They are not automatically teacher-facing rows.*

### 3.2 Episode judgement

| **Judgement** | **Meaning** |
| --- | --- |
| **Concern** | Evidence materially indicates a weak, incomplete or unproductive pattern in this episode. |
| **Mixed / unstable** | Supportive and concerning evidence coexist, or the capability varies materially within the window. |
| **Supportive** | Evidence indicates effective use of the capability in this episode. |
| **Strong / consistent** | Multiple converging observations show a stable and effective pattern in this episode or across comparable episodes. |

**No forced score.** If a validated numeric measure later exists for a construct, it may be stored. Draft 3 does not invent numeric precision simply to make a dashboard look complete.

### 3.3 Primary-home evidence routing

> **PRIMARY-HOME RULE** Each material analytical observation has one primary construct home. It may provide supporting context elsewhere, but it does not independently move a second construct or domain. If one raw event genuinely contains several distinct behaviours, the DRE may decompose those behaviours explicitly rather than double-count the same claim.

### 3.4 Minimum internal finding record

| **Field** | **What the DRE records** |
| --- | --- |
| **Construct** | The canonical capability being evaluated. |
| **Opportunity to observe** | Whether the task genuinely provided a fair test of the construct. |
| **Primary evidence** | Provenance-linked observations whose primary home is this construct. |
| **Counter-evidence** | Relevant observations pointing the other way. |
| **Coverage state** | One `COV.*` value: relevant / insufficient / no opportunity / not relevant / considered-no-material-finding. |
| **Judgement** | One `JDG.*` value: concern / mixed / supportive / strong—only when evidence is adequate. |
| **Confidence** | How strongly the evidence supports the judgement, independent of whether the judgement is positive or negative. |
| **Confounds / alternatives** | Plausible reasons the observed pattern may not reflect the learner’s underlying capability. |
| **Time window** | The episode, task or longitudinal interval to which the finding applies. |
| **Trajectory link** | Any prior comparable record used to infer change. |
| **Construct ID** | The immutable identifier of the construct, from this taxonomy (e.g. `D06.GLOBAL_RECHECK`). |
| **Taxonomy version** | The `taxonomy_version` of the taxonomy that produced the finding. |
| **Taxonomy SHA-256** | The full 64-hex SHA-256 of the canonical taxonomy file that produced the finding. |

### 3.5 Canonical DRE evidence rules

These rules are normative for taxonomy version 3.1. They restate upstream canonical Tarski evidence principles so that the DRE's evidentiary contract can be read in one place. Any future upstream change affecting them must be incorporated through a new taxonomy version rather than silently overriding this file.

- Tarski Telemetry records evidence; the DRE interprets it. TT evidence remains immutable. The DRE may construct derived views, normalised timelines, links and analytical observations, but it must not mutate or silently repair the original evidence or package. Every derivation must preserve its basis and pointers to the source evidence.
- **OBSERVED → DERIVED → INFERRED → EVALUATED** are distinct evidence grades and are never collapsed. Evidence grade and confidence are separate concepts. The grades are:

| **Evidence grade** | **Meaning** |
| --- | --- |
| **Observed** | A directly captured event. |
| **Derived** | A computation over observed evidence. |
| **Inferred** | An interpretation carrying confidence and links to the evidence that supports it. |
| **Evaluated** | An educational or reasoning judgement, produced for human review. |

- Exposure ≠ comprehension. Copy ≠ understanding. Semantic similarity ≠ influence. Temporal sequence ≠ causation.
- Concept knowledge ≠ connection knowledge ≠ transfer ≠ synthesis.
- AI assistance ≠ AI substitution.
- Silence in the telemetry ≠ inactivity. A capture gap ≠ misconduct. Missing evidence is never converted into certainty in either direction.
- An unexplained discontinuity is a neutral description with alternative explanations preserved, not an accusation.
- Every consequential finding is drillable to the evidence that supports it.

### 3.6 The analytical observation layer (outside this document)

This taxonomy defines constructs and how findings about them are stated. It does not define how raw telemetry becomes an analytical observation. That is a separate DRE reasoning layer—raw evidence → analytical observations → construct routing → findings → report—specified and versioned independently of both the telemetry sensor and this taxonomy, because the three change on different clocks.

An analytical observation carries evidence pointers, evidence grade, confidence, time window, alternative explanations and capture limitations before it is routed. Where one span of behaviour contains several distinct behaviours, decomposition into observations happens once, at the observation layer, before routing, and the decomposition is itself recorded; the primary-home rule then applies to the resulting observations.

Some constructs will rarely have a fair opportunity to appear in a naturalistic episode without a designed question, task or challenge. That is an opportunity-to-observe result, recorded as such; it is not a routing fault.

### 3.7 Contract rules

- Domain, construct and vocabulary identifiers are immutable once published. A change of meaning creates a new identifier; retired identifiers are listed, never recycled.
- Every stored finding carries `construct_id`, `taxonomy_version` and the full 64-hex SHA-256 of the canonical taxonomy file. Findings are never rewritten when the taxonomy changes; they continue to name the version that produced them.
- When a controlled-vocabulary value is persisted, its identifier (for example `JDG.SUPPORTIVE`) is authoritative; the human label is display text.
- A consumer that encounters an unknown identifier preserves it and its finding rather than discarding either.
- `taxonomy_version` tracks content; `taxonomy_schema_version` tracks the machine grammar of this file. Either may change without the other.
- The canonical file is UTF-8 without BOM, LF line endings, Unicode NFC, with a single trailing LF. Its SHA-256 is computed over exactly those bytes.

## 4. Developmental trajectory: learning as change

**Current level and developmental movement are different objects.** A learner who moves from weak to moderate capability may be showing a major educational gain. A learner who remains high and stable tells a different story; a learner who moves from high to moderate may require attention even though the absolute level remains respectable.

> **TRAJECTORY IS A CROSS-CUTTING AXIS** Do not create an eleventh “growth” domain. Every construct and domain may acquire a longitudinal history when comparable evidence exists. Change is evaluated across the taxonomy rather than beside it.

| **Longitudinal dimension** | **Question for the DRE** |
| --- | --- |
| **Current demonstrated capability** | What recent evidence supports now. |
| **Direction of change** | Improving, stable, declining, variable, discontinuous/uncertain, or not yet established. |
| **Magnitude of change** | How large the apparent movement is, but only when a defensible ordinal or numeric comparison exists. |
| **Rate of development** | How quickly the capability is changing across a meaningful interval. |
| **Stability** | Whether improvement is becoming reliable rather than appearing in one exceptional episode. |
| **Retention / reactivation** | Whether the capability still operates after time has passed and the original support is absent. |
| **Transfer over time** | Whether gains appear in new tasks, domains or representations. |
| **Increasing independence** | Whether similar or harder performance is achieved with less scaffolding or AI assistance. |
| **Challenge growth** | Whether the learner can sustain the capability as task complexity or ambiguity increases. |
| **Strategy development** | Whether useful learning strategies recur spontaneously in new settings. |
| **Responsiveness to feedback** | Whether feedback produces durable changes in understanding, strategy or behaviour. |
| **Developmental responsiveness** | A cautious higher-order inference, only after substantial evidence, about how effectively the learner improves previously weak capabilities when given feedback and opportunity. |

> **COMPARABILITY RULE** Do not call change merely because two values differ. Compare task difficulty, novelty, domain, scaffolding, AI assistance, time pressure, capture quality and opportunity to observe before attributing a trajectory.

| **Trajectory state** | **Meaning** |
| --- | --- |
| **Not yet established** | Too little comparable history to infer direction. |
| **Improving** | Comparable evidence supports sustained upward development. |
| **Stable** | Capability appears broadly maintained across comparable opportunities. |
| **Declining** | Comparable evidence supports a meaningful downward movement. |
| **Variable** | Performance changes materially across contexts without a stable direction yet. |
| **Discontinuous / uncertain** | Apparent movement exists, but missing evidence, context shift or non-comparability prevents a trustworthy trajectory claim. |

**Pass 5 with no comparable history.** Pass 5 always executes. If no comparable history exists, the episode-level longitudinal result is recorded as `TRJ.NOT_YET_ESTABLISHED`, with the comparability basis stated; any construct-level trajectory represented for that episode must likewise be `TRJ.NOT_YET_ESTABLISHED`. A skipped Pass 5 leaves no evidence that trajectory was considered; an executed Pass 5 that finds nothing to compare does.

**Unexplained discontinuity.** A major change in sophistication, content, structure or capability without an observable evidentiary bridge should be preserved as an unexplained discontinuity with alternative explanations, not converted into an accusation or a confident developmental story.

## 5. Teacher-facing reporting

> **REPORT PRINCIPLE** The report is a concise educational impression of the evidence, not a dump of the taxonomy. Internal reasoning may be exhaustive; external communication should be selective.

| **Significance question** | **What the DRE asks** |
| --- | --- |
| **Strength of evidence** | How well supported is the finding? |
| **Educational importance now** | Would a thoughtful teacher act differently if they knew this? |
| **Developmental change** | Is the learner improving, declining or showing a new capability? Change may outrank absolute level. |
| **Contradiction / instability** | Does this episode conflict with earlier patterns or vary sharply across conditions? |
| **Potential leverage** | Can an existing strength help the learner tackle a weaker or untested area? |
| **Actionability** | Is there a small next learning opportunity that would help the learner or clarify the evidence? |
| **Uniqueness** | Is the finding genuinely distinct, or merely the same observation appearing under another label? |

| **Teacher layer** | **What appears** |
| --- | --- |
| **Most important findings** | Usually 3–6 findings ranked by educational significance, each in plain language. |
| **Change that matters** | Any improvement, regression or newly stable capability important enough to alter interpretation. |
| **Strength to leverage** | A demonstrated capability that can support the learner’s next challenge. |
| **Important concern or instability** | Only when genuinely material; avoid turning every mixed signal into a warning. |
| **Important untested area** | Only when educationally relevant. Do not list the whole dark taxonomy. |
| **Next useful learning opportunity** | The smallest task, prompt or condition likely to improve learning or produce needed evidence. |
| **How the learner used AI** | A short plain-language summary when AI use was material to the episode. |
| **Drill-down** | Evidence, constructs, counter-evidence, confounds, comparable prior episodes and why any trajectory is trusted. |

> **DASHBOARD POSTPONED** The internal domains do not entitle fixed dials. After enough real DRE reports exist, the persistent glance-space can be designed empirically from what teachers actually need. A future dashboard is a compression of findings—not the ontology.

# PART II · Canonical Taxonomy

## 6. Taxonomy boundaries and era tags

**The domains are deliberately overlapping in subject matter but distinct in the question they ask.** The boundary map below is intended to prevent the DRE from turning one observation into several apparently independent findings.

| **Internal domain** | **Distinctive question** |
| --- | --- |
| **Agency & Self-Direction** | Who chooses the goal, path and next move? |
| **Metacognition & Self-Regulation** | Does the learner understand and regulate their own learning process? |
| **Knowledge Integration & Coherence** | How is knowledge organised—what connects to what, and does the whole cohere? |
| **Conceptual & Mechanistic Understanding** | Does the learner understand how and why the thing works, and can they reconstruct it? |
| **Transfer & Application** | Can the knowledge or skill travel into a new context? |
| **Reasoning, Logic & Systems Thinking** | What follows from what, how far does the reasoning travel, and can the wider interacting system remain in view? |
| **Epistemic Judgement & Evidence** | Why should the learner believe the claim, and how strong is the evidence? |
| **Creativity, Synthesis & Range** | Can the learner generate, connect and reorganise ideas productively? |
| **Adaptive Persistence, Precision & Execution** | How accurately and intelligently does the learner carry the work through difficulty and revision? |
| **AI Orchestration & Cognitive Control** | Is AI being deliberately managed as a cognitive partner rather than becoming the cognitive driver? |

### 6.1 Era-relevance tags

| **Tag** | **Meaning** |
| --- | --- |
| **F · Foundational** | Important before AI and still important now. The capability itself is not reclassified merely because AI happens to be nearby. |
| **A+ · AI-amplified** | A pre-existing capability whose importance, frequency, observability or practical character changes materially when AI is in the loop. |
| **AI · AI-native** | A capability that only meaningfully exists because another intelligence can participate continuously in the learner’s cognitive process. |

### 6.2 Internal coverage spine

| **ID** | **Domain** | **Draft 3 section** | **Core question** |
| --- | --- | --- | --- |
| D01 | **Agency & Self-Direction** | §7 | Who chooses the goal, path and next move? |
| D02 | **Metacognition & Self-Regulation** | §8 | Does the learner understand and regulate their own learning process? |
| D03 | **Knowledge Integration & Coherence** | §9 | How is knowledge organised—what connects to what, and does the whole cohere? |
| D04 | **Conceptual & Mechanistic Understanding** | §10 | Does the learner understand how and why the thing works, and can they reconstruct it? |
| D05 | **Transfer & Application** | §11 | Can the knowledge or skill travel into a new context? |
| D06 | **Reasoning, Logic & Systems Thinking** | §12 | What follows from what, how far does the reasoning travel, and can the wider interacting system remain in view? |
| D07 | **Epistemic Judgement & Evidence** | §13 | Why should the learner believe the claim, and how strong is the evidence? |
| D08 | **Creativity, Synthesis & Range** | §14 | Can the learner generate, connect and reorganise ideas productively? |
| D09 | **Adaptive Persistence, Precision & Execution** | §15 | How accurately and intelligently does the learner carry the work through difficulty and revision? |
| D10 | **AI Orchestration & Cognitive Control** | §16 | Is AI being deliberately managed as a cognitive partner rather than becoming the cognitive driver? |

Identifiers `D01`–`D10` are the stable machine references for the ten domains. Prose sections §7–§16 present them in the same order. Any reference of the form “Domain N” elsewhere in this document uses these identifiers.

# Controlled Vocabularies

The values a finding may take are defined here with stable identifiers. The prose tables in Part I remain the readable explanation; this block is the machine-readable definition, and the two are checked against each other at build time. When a value is persisted, its identifier is authoritative and the label is display text.

## EGR — Evidence grades

### EGR.OBSERVED
**Label:** Observed
**Meaning:** A directly captured event.

### EGR.DERIVED
**Label:** Derived
**Meaning:** A computation over observed evidence.

### EGR.INFERRED
**Label:** Inferred
**Meaning:** An interpretation carrying confidence and links to the evidence that supports it.

### EGR.EVALUATED
**Label:** Evaluated
**Meaning:** An educational or reasoning judgement, produced for human review.

## COV — Coverage states

### COV.RELEVANT_FOUND
**Label:** Relevant evidence found
**Meaning:** Enough relevant evidence exists to support an episode judgement.

### COV.RELEVANT_INSUFFICIENT
**Label:** Relevant but insufficient
**Meaning:** The construct was in play, but evidence is too thin, ambiguous or incomplete to judge fairly.

### COV.NO_OPPORTUNITY
**Label:** No meaningful opportunity
**Meaning:** The episode did not provide a fair opportunity for the capability to appear.

### COV.NOT_RELEVANT
**Label:** Not relevant to this episode
**Meaning:** The work was of the wrong kind for this construct.

### COV.NO_MATERIAL_FINDING
**Label:** Considered, no material finding
**Meaning:** The DRE looked and found nothing educationally significant enough to carry forward.

## JDG — Episode judgements

### JDG.CONCERN
**Label:** Concern
**Meaning:** Evidence materially indicates a weak, incomplete or unproductive pattern in this episode.

### JDG.MIXED
**Label:** Mixed / unstable
**Meaning:** Supportive and concerning evidence coexist, or the capability varies materially within the window.

### JDG.SUPPORTIVE
**Label:** Supportive
**Meaning:** Evidence indicates effective use of the capability in this episode.

### JDG.STRONG
**Label:** Strong / consistent
**Meaning:** Multiple converging observations show a stable and effective pattern in this episode or across comparable episodes.

## TRJ — Trajectory states

### TRJ.NOT_YET_ESTABLISHED
**Label:** Not yet established
**Meaning:** Too little comparable history to infer direction.

### TRJ.IMPROVING
**Label:** Improving
**Meaning:** Comparable evidence supports sustained upward development.

### TRJ.STABLE
**Label:** Stable
**Meaning:** Capability appears broadly maintained across comparable opportunities.

### TRJ.DECLINING
**Label:** Declining
**Meaning:** Comparable evidence supports a meaningful downward movement.

### TRJ.VARIABLE
**Label:** Variable
**Meaning:** Performance changes materially across contexts without a stable direction yet.

### TRJ.DISCONTINUOUS
**Label:** Discontinuous / uncertain
**Meaning:** Apparent movement exists, but missing evidence, context shift or non-comparability prevents a trustworthy trajectory claim.

## PASS — DRE passes

### PASS.0_EVIDENCE_ASSEMBLY
**Label:** Pass 0 · Evidence assembly
**Meaning:** Assemble provenance streams, student artifact(s), task context, relevant external evidence and prior comparable episodes. Mark capture gaps before interpretation.

### PASS.1_COVERAGE_TRAVERSAL
**Label:** Pass 1 · Coverage traversal
**Meaning:** Walk the canonical domains and constructs. For each construct, record a coverage state. The purpose is to prove the landscape was considered, not to fill every cell.

### PASS.2_EVIDENCE_ROUTING
**Label:** Pass 2 · Evidence routing
**Meaning:** Assign every material analytical observation a primary evidentiary home. Supporting context may be cited elsewhere, but the same observation must not independently move multiple constructs.

### PASS.3_EPISODE_EVALUATION
**Label:** Pass 3 · Episode evaluation
**Meaning:** For adequately evidenced constructs, weigh supportive evidence, concern evidence, alternative explanations and confounds; then form a bounded judgement with confidence.

### PASS.4_REASONING_INTEGRITY
**Label:** Pass 4 · Systems / reasoning integrity check
**Meaning:** Where the task involves complex reasoning, test whether the learner traced consequences deeply enough, maintained relevant constraints, considered interactions and avoided premature closure or local cognitive capture.

### PASS.5_LONGITUDINAL_COMPARISON
**Label:** Pass 5 · Longitudinal comparison
**Meaning:** Where comparable history exists, evaluate trajectory, task challenge, scaffolding, independence, retention, transfer and responsiveness to feedback. Do not compare raw results across incomparable conditions.

### PASS.6_SIGNIFICANCE_SYNTHESIS
**Label:** Pass 6 · Significance synthesis
**Meaning:** Ask what a thoughtful teacher most needs to notice now. Developmental change may outrank absolute level; a decline from a strength may outrank a static weakness.

### PASS.7_REPORT
**Label:** Pass 7 · Teacher report + mentoring move
**Meaning:** Write a concise findings layer, identify a useful strength to leverage or next learning opportunity where appropriate, and preserve the deeper reasoning for drill-down and audit.

## ERA — Era-relevance tags

### ERA.F
**Label:** F · Foundational
**Meaning:** Important before AI and still important now. The capability itself is not reclassified merely because AI happens to be nearby.

### ERA.A_PLUS
**Label:** A+ · AI-amplified
**Meaning:** A pre-existing capability whose importance, frequency, observability or practical character changes materially when AI is in the loop.

### ERA.AI
**Label:** AI · AI-native
**Meaning:** A capability that only meaningfully exists because another intelligence can participate continuously in the learner’s cognitive process.

# D01 — Agency & Self-Direction
**Question:** Who chooses the goal, path and next move?

*Who is choosing the goal, path and next move?*

## D01.GOAL_AUTHORSHIP
**Name:** Goal authorship
**Era:** F
**Guidepost:** Defines what is to be learned or achieved rather than merely responding to the next prompt or task.

## D01.GOAL_REVISION
**Name:** Goal revision
**Era:** F
**Guidepost:** Revises the learning goal when new understanding shows that the original target was incomplete or poorly framed.

## D01.PROBLEM_FRAMING
**Name:** Problem framing
**Era:** F
**Guidepost:** Defines or reframes the problem so the work addresses the real learning need.

## D01.PATH_DESIGN
**Name:** Path design
**Era:** F
**Guidepost:** Chooses the sequence of topics, examples or sub-problems rather than passively following a default path.

## D01.INITIATIVE
**Name:** Initiative
**Era:** F
**Guidepost:** Introduces useful next steps, questions or investigations without waiting to be told.

## D01.INVESTIGATIVE_QUESTIONS
**Name:** Investigative question generation
**Era:** F
**Guidepost:** Generates the next useful question from the problem or a gap in understanding; distinct from interrogating one’s own explanation.

## D01.DIRECTION_MAINTENANCE
**Name:** Direction maintenance
**Era:** A+
**Guidepost:** Keeps the episode aligned to the learner’s objective despite attractive side paths or model-led drift.

## D01.SELECTIVE_UPTAKE
**Name:** Selective uptake
**Era:** A+
**Guidepost:** Accepts, modifies or rejects suggestions according to usefulness rather than automatically adopting them.

## D01.LEARNING_OWNERSHIP
**Name:** Learning ownership
**Era:** A+
**Guidepost:** Visibly shapes the developing understanding, framing and conclusions rather than merely adopting supplied wording.

## D01.INDEPENDENT_CONTINUATION
**Name:** Independent continuation
**Era:** F
**Guidepost:** Can continue reasoning or working without needing the AI to specify every next move.

# D02 — Metacognition & Self-Regulation
**Question:** Does the learner understand and regulate their own learning process?

## D02.PLANNING
**Name:** Planning
**Era:** F
**Guidepost:** Selects an approach, sequence or strategy before or during the task.

## D02.MONITORING_UNDERSTANDING
**Name:** Monitoring understanding
**Era:** F
**Guidepost:** Checks whether understanding is actually developing rather than equating exposure with learning.

## D02.CONFUSION_RECOGNITION
**Name:** Recognition of confusion
**Era:** F
**Guidepost:** Identifies what is unclear, missing or internally inconsistent with useful specificity.

## D02.SELF_QUESTIONING
**Name:** Self-questioning
**Era:** F
**Guidepost:** Interrogates one’s own current explanation, assumptions or certainty; distinct from generating the next investigative question.

## D02.KNOWLEDGE_CALIBRATION
**Name:** Calibration of own knowledge
**Era:** F
**Guidepost:** Distinguishes what is known, partly known, guessed or not understood.

## D02.STRATEGY_SELECTION
**Name:** Strategy selection
**Era:** F
**Guidepost:** Chooses a learning or problem-solving method suited to the current task.

## D02.STRATEGY_SWITCHING
**Name:** Strategy switching
**Era:** F
**Guidepost:** Changes approach when evidence shows that the current strategy is ineffective.

## D02.ERROR_DIAGNOSIS
**Name:** Error diagnosis
**Era:** F
**Guidepost:** Identifies why an error occurred, not only that it occurred.

## D02.FEEDBACK_UPTAKE
**Name:** Feedback uptake and adaptation
**Era:** F
**Guidepost:** Uses feedback to change understanding, strategy or behaviour rather than merely acknowledging it.

## D02.REFLECTION
**Name:** Reflection
**Era:** F
**Guidepost:** Reviews what was learned, what changed, and what approach worked or failed.

## D02.ATTENTION_ALLOCATION
**Name:** Attention and time allocation
**Era:** F
**Guidepost:** Allocates effort to the parts that matter for learning rather than being captured by low-value activity.

## D02.HELP_SEEKING
**Name:** Help-seeking judgement
**Era:** F
**Guidepost:** Recognises when external help is valuable and asks for the smallest useful assistance.

## D02.HUMAN_AI_METACOGNITION
**Name:** Collaborative human-AI metacognition
**Era:** AI
**Guidepost:** Monitors the joint human-AI cognitive system: what the learner should think, what the AI should do, and whether that division is helping learning.

# D03 — Knowledge Integration & Coherence
**Question:** How is knowledge organised—what connects to what, and does the whole cohere?
**Boundary:** This domain is about the structure of the learner’s knowledge: what connects to what, how concepts are organised, and whether the whole is coherent. It is not the same as reconstructing a mechanism (D04) or tracing consequences through a system (D06).

*Are facts becoming a connected, coherent mental model?*

## D03.FACT_TO_CONCEPT
**Name:** Fact-to-concept integration
**Era:** F
**Guidepost:** Places individual facts inside larger concepts rather than retaining them as isolated items.

## D03.RELATIONAL_UNDERSTANDING
**Name:** Relational understanding
**Era:** F
**Guidepost:** Understands how concepts relate to one another, not merely what each means separately.

## D03.SCHEMA_FORMATION
**Name:** Schema formation
**Era:** F
**Guidepost:** Builds an organised structure that can absorb and locate new knowledge.

## D03.HIERARCHICAL_ORGANISATION
**Name:** Hierarchical organisation
**Era:** F
**Guidepost:** Distinguishes governing principles, subordinate ideas, examples and exceptions.

## D03.CAUSAL_STRUCTURE
**Name:** Causal structure in the knowledge model
**Era:** F
**Guidepost:** Represents known causal relationships coherently when causation is part of the subject matter.

## D03.INTERNAL_COHERENCE
**Name:** Internal coherence
**Era:** F
**Guidepost:** Detects and resolves contradictions or incompatible pieces within the developing knowledge structure.

## D03.PRIOR_KNOWLEDGE_INTEGRATION
**Name:** Integration with prior knowledge
**Era:** F
**Guidepost:** Connects new learning to useful prior knowledge without forcing false analogies.

## D03.KNOWLEDGE_COMPRESSION
**Name:** Knowledge compression
**Era:** F
**Guidepost:** Compresses many details into a smaller set of explanatory rules, principles or operators.

## D03.DISTINCTION_MAKING
**Name:** Conceptual distinction-making
**Era:** F
**Guidepost:** Separates ideas that appear similar but perform different roles.

## D03.BOUNDARY_UNDERSTANDING
**Name:** Boundary understanding
**Era:** F
**Guidepost:** Understands where a concept applies, where it stops applying, and what exceptions matter.

## D03.HOLISTIC_RECONSTRUCTION
**Name:** Holistic reconstruction
**Era:** F
**Guidepost:** Can reconstruct the whole system from its important parts and explain how those parts fit together.

# D04 — Conceptual & Mechanistic Understanding
**Question:** Does the learner understand how and why the thing works, and can they reconstruct it?
**Boundary:** This domain asks whether the learner understands how and why something works and can reconstruct it. “Depth” here means depth of understanding; Draft 3 reserves “reasoning depth” for the length and integrity of inferential chains in D06.

*Can the learner explain what is happening underneath fluent descriptions?*

## D04.SURFACE_VS_DEEP_PROCESSING
**Name:** Surface vs deep processing
**Era:** F
**Guidepost:** Moves beyond reproduction of wording toward usable underlying understanding.

## D04.CONCEPTUAL_UNDERSTANDING
**Name:** Conceptual understanding
**Era:** F
**Guidepost:** Grasps the governing idea rather than only labels, definitions or procedures.

## D04.MECHANISTIC_UNDERSTANDING
**Name:** Mechanistic understanding
**Era:** F
**Guidepost:** Can explain how a process works through intermediate steps and interactions.

## D04.WHY_NOT_JUST_WHAT
**Name:** Why-not-just-what understanding
**Era:** F
**Guidepost:** Explains why a result or behaviour occurs, not only what occurs.

## D04.OWN_TERMS_REEXPRESSION
**Name:** Re-expression in own terms
**Era:** F
**Guidepost:** Reconstructs an idea in personally meaningful language, notation or representation.

## D04.TEACH_BACK
**Name:** Human explanation / teach-back
**Era:** F
**Guidepost:** Can explain the developing mental model clearly to another person, or to a future self on a blank page.

## D04.DERIVATION
**Name:** Derivation / reconstruction
**Era:** F
**Guidepost:** Can rebuild a result or process from underlying principles rather than merely recognise it.

## D04.INDEPENDENT_RECONSTRUCTION
**Name:** Independent reconstruction
**Era:** A+
**Guidepost:** After assistance is removed, can reconstruct the concept, process or representation without relying on the original AI explanation.

## D04.OPERATIONAL_COMPRESSION
**Name:** Operational compression
**Era:** F
**Guidepost:** Reduces a long explanation to a concise rule, operator or relationship that can actually be used.

## D04.PROBING_ROBUSTNESS
**Name:** Robustness under probing
**Era:** F
**Guidepost:** Understanding survives follow-up questions, changed wording and requests for explanation.

## D04.EXAMPLE_TO_PRINCIPLE
**Name:** Example-to-principle movement
**Era:** F
**Guidepost:** Extracts the general principle illustrated by a particular example.

## D04.PRINCIPLE_TO_EXAMPLE
**Name:** Principle-to-example movement
**Era:** F
**Guidepost:** Can generate or interpret examples that instantiate an abstract principle.

# D05 — Transfer & Application
**Question:** Can the knowledge or skill travel into a new context?

*Can knowledge and skill travel beyond the context in which they were learned?*

## D05.NEAR_TRANSFER
**Name:** Near transfer
**Era:** F
**Guidepost:** Applies a learned principle or skill to a closely related problem or context.

## D05.FAR_TRANSFER
**Name:** Far transfer
**Era:** F
**Guidepost:** Recognises and applies the same underlying structure in a substantially different context.

## D05.PROCEDURAL_TRANSFER
**Name:** Procedural transfer
**Era:** F
**Guidepost:** Carries a method or procedure successfully into a new task.

## D05.CONCEPTUAL_TRANSFER
**Name:** Conceptual transfer
**Era:** F
**Guidepost:** Uses an abstract idea outside the example or context in which it was learned.

## D05.CROSS_DOMAIN_TRANSFER
**Name:** Cross-domain transfer
**Era:** F
**Guidepost:** Imports a useful concept or structure from one field into another when the fit is genuine.

## D05.ANALOGICAL_TRANSFER
**Name:** Analogical transfer
**Era:** F
**Guidepost:** Uses structural analogy to solve or understand a new problem while respecting differences.

## D05.SPONTANEOUS_TRANSFER
**Name:** Spontaneous transfer
**Era:** F
**Guidepost:** Transfers knowledge without being explicitly prompted to do so.

## D05.ADAPTIVE_APPLICATION
**Name:** Adaptive application
**Era:** F
**Guidepost:** Modifies a learned method when the new context has different constraints.

## D05.REAL_WORLD_APPLICATION
**Name:** Real-world application
**Era:** F
**Guidepost:** Connects learning to authentic decisions, systems or problems beyond the instructional setting.

## D05.TRANSFER_FEEDBACK
**Name:** Transfer feedback
**Era:** F
**Guidepost:** Uses success or failure in a new context to refine the original understanding.

# D06 — Reasoning, Logic & Systems Thinking
**Question:** What follows from what, how far does the reasoning travel, and can the wider interacting system remain in view?
**Boundary:** Knowledge Integration asks how the learner’s knowledge is organised. Conceptual & Mechanistic Understanding asks how and why a process works. This domain asks what the learner can derive from that knowledge: whether the inferential chain is sound, whether consequences are followed far enough, and whether interacting constraints remain visible while attention is local.

| **Reasoning dimension** | **Core question** |
| --- | --- |
| **Vertical reasoning** | How far can a justified chain of inference or consequence be carried before the learner stops? |
| **Horizontal reasoning** | How many relevant interacting factors, constraints or alternative pathways can remain active while the learner reasons? |
| **Temporal horizon** | How far downstream in time are delayed, cumulative or path-dependent consequences traced? |
| **Whole-problem retention** | Can the learner work deeply on one part without losing the goals, constraints and interactions of the larger system? |

> **KEY FAILURE MODES** Premature closure: the first plausible answer ends the reasoning too early. Local cognitive capture: the current subproblem, optimisation target or AI reply becomes so salient that important parts of the wider system effectively disappear.

## D06.ARGUMENT_STRUCTURE
**Name:** Argument structure
**Family:** Logical structure
**Era:** F
**Guidepost:** Identifies premises, inferences and conclusions and keeps them logically distinct.

## D06.DEDUCTIVE_VALIDITY
**Name:** Deductive validity
**Family:** Logical structure
**Era:** F
**Guidepost:** Recognises whether a conclusion follows necessarily from stated premises.

## D06.INDUCTIVE_STRENGTH
**Name:** Inductive strength
**Family:** Logical structure
**Era:** F
**Guidepost:** Judges whether evidence makes a conclusion more plausible without pretending it proves it.

## D06.NECESSARY_SUFFICIENT
**Name:** Necessary vs sufficient conditions
**Family:** Logical structure
**Era:** F
**Guidepost:** Distinguishes what must be true from what would be enough to make something true.

## D06.ASSUMPTION_DETECTION
**Name:** Assumption detection
**Family:** Logical structure
**Era:** F
**Guidepost:** Identifies unstated premises or conditions on which an argument depends.

## D06.CONSISTENCY_CONTRADICTION
**Name:** Consistency and contradiction
**Family:** Logical structure
**Era:** F
**Guidepost:** Detects when claims cannot all be true together or when reasoning shifts standards midstream.

## D06.FALLACY_DETECTION
**Name:** Fallacy detection
**Family:** Logical structure
**Era:** F
**Guidepost:** Recognises recurring invalid or misleading forms such as false dichotomy, circularity, equivocation, straw man, ad hominem and inappropriate appeal to authority.

## D06.COUNTEREXAMPLE_GENERATION
**Name:** Counterexample generation
**Family:** Logical structure
**Era:** F
**Guidepost:** Tests general claims by looking for cases that would invalidate or sharply qualify them.

## D06.SCOPE_GENERALISATION
**Name:** Scope and generalisation
**Family:** Logical structure
**Era:** F
**Guidepost:** Avoids moving illegitimately from some to all, from one context to another, or from a narrow sample to a broad claim.

## D06.BURDEN_OF_PROOF
**Name:** Burden of proof
**Family:** Logical structure
**Era:** F
**Guidepost:** Recognises who needs to supply evidence and avoids treating absence of disproof as proof.

## D06.CHAIN_INTEGRITY
**Name:** Chain integrity
**Family:** Reasoning span
**Era:** F
**Guidepost:** Maintains justified links across a multi-step argument rather than allowing hidden leaps to enter as the chain grows.

## D06.INFERENTIAL_DEPTH
**Name:** Inferential depth · vertical reasoning
**Family:** Reasoning span
**Era:** F
**Guidepost:** Sustains a meaningful chain of reasoning through several dependent steps instead of stopping at the first plausible consequence.

## D06.CONSEQUENCE_TRACING
**Name:** Consequence tracing
**Family:** Reasoning span
**Era:** F
**Guidepost:** Follows the downstream consequences of a proposal or assumption, including second- and higher-order effects where relevant.

## D06.TEMPORAL_HORIZON
**Name:** Temporal horizon
**Family:** Reasoning span
**Era:** F
**Guidepost:** Looks beyond immediate effects to delayed, cumulative or path-dependent consequences.

## D06.BRANCHING_REASONING
**Name:** Branching reasoning
**Family:** Reasoning span
**Era:** F
**Guidepost:** Keeps more than one plausible downstream pathway alive long enough to compare them rather than forcing a single linear story too early.

## D06.ALTERNATIVE_HYPOTHESES
**Name:** Alternative hypotheses
**Family:** Reasoning span
**Era:** F
**Guidepost:** Generates and tests competing explanations before settling on a preferred account.

## D06.STOPPING_DISCIPLINE
**Name:** Stopping discipline
**Family:** Reasoning span
**Era:** F
**Guidepost:** Stops when the important consequences have been examined—not merely when the first workable answer appears, and not after endless low-value elaboration.

## D06.CAUSAL_REASONING
**Name:** Causal reasoning
**Family:** Systems interaction
**Era:** F
**Guidepost:** Distinguishes causal claims from correlation and looks for mechanisms, confounders and directionality.

## D06.REASONING_BREADTH
**Name:** Reasoning breadth · horizontal reasoning
**Family:** Systems interaction
**Era:** F
**Guidepost:** Keeps multiple relevant factors, constraints or interacting pathways in view while reasoning about the system.

## D06.TRADEOFF_REASONING
**Name:** Interaction and trade-off reasoning
**Family:** Systems interaction
**Era:** F
**Guidepost:** Recognises that improving one variable may alter or damage another and evaluates coupled objectives rather than optimising one dimension in isolation.

## D06.FEEDBACK_LOOP_REASONING
**Name:** Feedback-loop reasoning
**Family:** Systems interaction
**Era:** F
**Guidepost:** Recognises when consequences feed back to alter earlier conditions, incentives or system behaviour.

## D06.SYSTEMS_BOUNDARY
**Name:** Systems boundary awareness
**Family:** Systems interaction
**Era:** F
**Guidepost:** Notices which variables are inside the working model, which have been omitted, and whether the chosen boundary hides important effects.

## D06.WHOLE_PROBLEM_RETENTION
**Name:** Whole-problem retention · active context maintenance
**Family:** Systems interaction
**Era:** F
**Guidepost:** While working locally, keeps salient goals, constraints and prior conclusions cognitively available—internally or through deliberate external scaffolding.

## D06.COGNITIVE_CAPTURE_RESISTANCE
**Name:** Resistance to local cognitive capture
**Family:** Systems interaction
**Era:** A+
**Guidepost:** Avoids allowing the current subproblem, AI reply or optimisation target to make the wider system disappear from consideration.

## D06.GLOBAL_RECHECK
**Name:** Global re-check after local optimisation
**Family:** Systems interaction
**Era:** F
**Guidepost:** After improving one component, deliberately tests whether the change harms other objectives or violates earlier constraints.

# D07 — Epistemic Judgement & Evidence
**Question:** Why should the learner believe the claim, and how strong is the evidence?

*Is belief proportional to the quality of the evidence?*

## D07.EVIDENCE_RELEVANCE
**Name:** Evidence relevance
**Era:** F
**Guidepost:** Asks whether the evidence actually bears on the claim being considered.

## D07.EVIDENCE_STRENGTH
**Name:** Evidence strength
**Era:** F
**Guidepost:** Distinguishes stronger from weaker evidence rather than treating all supporting material as equivalent.

## D07.SOURCE_QUALITY
**Name:** Source quality
**Era:** F
**Guidepost:** Evaluates competence, incentives, methodology and reliability of information sources.

## D07.SAMPLING_REPRESENTATIVENESS
**Name:** Sampling and representativeness
**Era:** F
**Guidepost:** Judges whether observations or samples justify claims about the wider population or situation.

## D07.MEASUREMENT_QUALITY
**Name:** Measurement quality
**Era:** F
**Guidepost:** Asks whether the measurement, operationalisation or data-generation process actually captures the thing claimed.

## D07.PROVENANCE_AWARENESS
**Name:** Provenance awareness
**Era:** A+
**Guidepost:** Tracks where claims, numbers, quotations or ideas came from and how they reached the learner.

## D07.TRIANGULATION
**Name:** Independence and triangulation
**Era:** F
**Guidepost:** Recognises when apparently multiple sources are not independent and seeks genuinely independent confirmation where needed.

## D07.FACT_INFERENCE_OPINION
**Name:** Fact / inference / opinion distinction
**Era:** F
**Guidepost:** Separates direct observations and established facts from interpretations, inferences and preferences.

## D07.UNCERTAINTY_HYGIENE
**Name:** Uncertainty hygiene
**Era:** F
**Guidepost:** Represents uncertainty explicitly instead of turning incomplete evidence into false certainty.

## D07.CONFIDENCE_CALIBRATION
**Name:** Confidence calibration
**Era:** F
**Guidepost:** Matches confidence to evidential strength and revises confidence when evidence changes.

## D07.VERIFICATION_JUDGEMENT
**Name:** Verification judgement
**Era:** A+
**Guidepost:** Decides whether a claim needs checking, what standard of evidence is appropriate, and when verification is sufficient.

## D07.FALSIFIABILITY
**Name:** Falsifiability and testability
**Era:** F
**Guidepost:** Identifies what observations could count against a claim and prefers claims that can be meaningfully tested when appropriate.

## D07.MISSING_EVIDENCE
**Name:** Missing-evidence recognition
**Era:** F
**Guidepost:** Notices what would need to be known before a confident conclusion could be justified.

## D07.BELIEF_UPDATING
**Name:** Belief updating
**Era:** F
**Guidepost:** Changes or qualifies a conclusion when better evidence appears.

## D07.FLUENT_WRONGNESS_RESISTANCE
**Name:** Resistance to fluent wrongness
**Era:** AI
**Guidepost:** Does not confuse confident, polished or AI-generated language with truth.

# D08 — Creativity, Synthesis & Range
**Question:** Can the learner generate, connect and reorganise ideas productively?

## D08.DIVERGENT_THINKING
**Name:** Divergent thinking
**Era:** F
**Guidepost:** Generates meaningfully different possibilities rather than cosmetic variants of the same idea.

## D08.EXPLORATION_BREADTH
**Name:** Breadth of exploration
**Era:** F
**Guidepost:** Looks beyond the first obvious path before narrowing.

## D08.ORIGINALITY
**Name:** Originality
**Era:** F
**Guidepost:** Introduces useful ideas, framings or questions not simply supplied by the task or AI.

## D08.INTEGRATIVE_SYNTHESIS
**Name:** Integrative synthesis
**Era:** F
**Guidepost:** Combines separate ideas into a coherent structure that is more useful than the parts alone.

## D08.JOINING_DISTANT_IDEAS
**Name:** Joining distant ideas
**Era:** F
**Guidepost:** Recognises meaningful connections between initially disparate domains or concepts.

## D08.ANALOGICAL_INVENTION
**Name:** Analogical invention
**Era:** F
**Guidepost:** Creates analogies or metaphors that genuinely illuminate structure rather than merely decorate.

## D08.HYPOTHESIS_GENERATION
**Name:** Hypothesis generation
**Era:** F
**Guidepost:** Generates plausible candidate explanations or models that can then be tested.

## D08.PERSPECTIVE_SHIFTING
**Name:** Perspective shifting
**Era:** F
**Guidepost:** Re-examines a problem from different roles, scales, assumptions or viewpoints.

## D08.RECOMBINATION
**Name:** Recombination
**Era:** F
**Guidepost:** Uses known components in a novel arrangement suited to the problem.

## D08.REPRESENTATION_INVENTION
**Name:** Representation invention
**Era:** F
**Guidepost:** Creates a notation, diagram, table, model or other representation that improves thinking.

## D08.IDEA_ELABORATION
**Name:** Idea elaboration
**Era:** F
**Guidepost:** Develops a promising idea beyond its first rough form.

## D08.IDEA_EVALUATION
**Name:** Idea evaluation and refinement
**Era:** F
**Guidepost:** Discriminates among generated ideas and improves the most promising ones.

# D09 — Adaptive Persistence, Precision & Execution
**Question:** How accurately and intelligently does the learner carry the work through difficulty and revision?

*Does the learner carry the work through difficulty accurately and intelligently?*

## D09.PERSISTENCE
**Name:** Persistence
**Era:** F
**Guidepost:** Continues working when understanding or execution does not come immediately.

## D09.PRODUCTIVE_STRUGGLE
**Name:** Productive struggle
**Era:** F
**Guidepost:** Engages with effortful thinking rather than immediately bypassing the difficulty; AI makes avoidance easier but the capability itself is foundational.

## D09.FRUSTRATION_TOLERANCE
**Name:** Frustration tolerance
**Era:** F
**Guidepost:** Maintains useful engagement despite temporary confusion, error or tool friction.

## D09.ADAPTIVE_PERSISTENCE
**Name:** Adaptive persistence
**Era:** F
**Guidepost:** Persists while changing strategy when the current approach is not working.

## D09.STALL_RECOVERY
**Name:** Recovery after stall
**Era:** F
**Guidepost:** Recognises a dead end and resumes progress using a different route.

## D09.FLEXIBILITY
**Name:** Flexibility
**Era:** F
**Guidepost:** Can abandon an attractive but ineffective approach when evidence warrants it.

## D09.ACCURACY
**Name:** Accuracy
**Era:** F
**Guidepost:** Produces results that are substantively correct for the task.

## D09.PRECISION
**Name:** Precision
**Era:** F
**Guidepost:** Uses terminology, notation, units, distinctions and claims with appropriate exactness.

## D09.ATTENTION_TO_CONSEQUENTIAL_DETAIL
**Name:** Attention to consequential detail
**Era:** F
**Guidepost:** Notices small errors when they affect meaning, validity or reproducibility.

## D09.CONSISTENCY
**Name:** Consistency
**Era:** F
**Guidepost:** Maintains compatible notation, definitions, assumptions and standards across the work.

## D09.REVISION_QUALITY
**Name:** Revision quality
**Era:** F
**Guidepost:** Improves the underlying reasoning or representation rather than merely making surface changes.

## D09.FOLLOW_THROUGH
**Name:** Follow-through
**Era:** F
**Guidepost:** Carries an investigation or correction through to a stable resolution.

## D09.TOOL_FRICTION
**Name:** Tool-friction management
**Era:** A+
**Guidepost:** Recognises when interaction with software or AI is consuming learning time and changes workflow appropriately.

# D10 — AI Orchestration & Cognitive Control
**Question:** Is AI being deliberately managed as a cognitive partner rather than becoming the cognitive driver?

*Is AI amplifying the learner’s cognition rather than substituting for it?*

## D10.HUMAN_AI_AGENCY
**Name:** Human-AI agency & pacing
**Era:** AI
**Guidepost:** The learner remains the cognitive decision-maker and determines when to advance, pause, rewind, reroute or stop the model.

## D10.AI_ROLE_ASSIGNMENT
**Name:** AI role assignment
**Era:** AI
**Guidepost:** Deliberately assigns the AI roles such as explainer, challenger, verifier, brainstormer, tutor or production assistant.

## D10.COGNITIVE_DELEGATION
**Name:** Cognitive delegation
**Era:** AI
**Guidepost:** Chooses which work to delegate to AI and which work must remain with the learner.

## D10.COGNITIVE_RETENTION
**Name:** Cognitive retention / no-outsourcing
**Era:** AI
**Guidepost:** Protects the very cognitive operation that the learner is supposed to acquire or practise.

## D10.AI_ABSTENTION
**Name:** Knowing when not to use AI
**Era:** AI
**Guidepost:** Recognises when withholding AI assistance is educationally or epistemically preferable.

## D10.AI_TRUST_CALIBRATION
**Name:** Calibration of trust in AI
**Era:** AI
**Guidepost:** Adjusts trust according to task, evidence, model behaviour and stakes rather than fluency.

## D10.AI_VERIFICATION
**Name:** AI verification execution
**Era:** AI
**Guidepost:** Carries out proportionate checks on AI output using independent sources, calculation, tests, tools or a genuinely independent model when warranted.

## D10.PROMPT_COMPOSITION
**Name:** Prompt / brief composition
**Era:** AI
**Guidepost:** Gives the AI context, constraints, role and success criteria sufficient for the intended cognitive job.

## D10.REPRESENTATION_NEGOTIATION
**Name:** Representation negotiation
**Era:** AI
**Guidepost:** Changes the form of AI output until it supports the learner’s own understanding and reasoning.

## D10.ASSISTANCE_REGULATION
**Name:** Assistance regulation
**Era:** AI
**Guidepost:** Controls pace, granularity, hint level and completeness of AI help.

## D10.MULTI_AI_ORCHESTRATION
**Name:** Multi-AI orchestration
**Era:** AI
**Guidepost:** Uses multiple models or tools for distinct purposes such as contrast, challenge or independent checking rather than roulette.

## D10.CONTEXT_MANAGEMENT
**Name:** Context management
**Era:** AI
**Guidepost:** Keeps tasks, evidence, files and conversational contexts organised so the AI is operating on the right problem.

## D10.AI_OPPORTUNITY_JUDGEMENT
**Name:** AI opportunity judgement
**Era:** AI
**Guidepost:** Recognises when AI enables a qualitatively new line of inquiry, synthesis or project rather than merely faster completion.

## D10.AUTHORSHIP_TRANSPARENCY
**Name:** Authorship transparency
**Era:** AI
**Guidepost:** Can distinguish what originated with the learner, what came from AI, and what was transformed collaboratively.

## D10.DATA_PRIVACY_JUDGEMENT
**Name:** Data and privacy judgement
**Era:** AI
**Guidepost:** Understands what information is being captured, transmitted or stored and acts appropriately.

## D10.FINAL_HUMAN_JUDGEMENT
**Name:** Final human judgement
**Era:** AI
**Guidepost:** Retains responsibility for the final intellectual decision rather than treating model output as authority.

# 17. AI-era differentiation

A capable learner in a typical 1950 classroom could already demonstrate knowledge, logic, persistence, precision, curiosity, synthesis, transfer and metacognition. AI does not replace those capabilities. It adds a new class of capability: managing another intelligence as part of one’s own cognitive system.

| **Distinctively AI-era capability** | **Defining question** |
| --- | --- |
| **Human-AI agency & pacing** | Who is cognitively driving the episode? |
| **Collaborative human-AI metacognition** | Is the learner monitoring the effectiveness of the joint human-AI system? |
| **AI role assignment** | Is the model being used deliberately as explainer, challenger, verifier, brainstormer or production assistant? |
| **Cognitive delegation** | Which thinking is deliberately given to the AI, and which is kept? |
| **Cognitive retention / no-outsourcing** | Is the learner protecting the cognitive operation they are meant to acquire? |
| **Knowing when not to use AI** | Can the learner deliberately withhold AI when effort itself is educationally valuable? |
| **Assistance regulation** | Can the learner control pace, granularity, completeness and timing of AI help? |
| **Calibration of trust in AI** | Does trust track evidence, stakes and model behaviour rather than fluency? |
| **Representation negotiation** | Can the learner reshape AI output into a form that supports their own cognition? |
| **Multi-AI orchestration** | Can different models or tools be assigned distinct purposes rather than used as roulette? |
| **AI opportunity judgement** | Can the learner recognise qualitatively new inquiry made possible by AI? |
| **Authorship transparency** | Can the learner distinguish human-originated, AI-originated and jointly transformed contributions? |

**What should I think?**
**What should the machine think?**
**How should we combine the two?**
**And am I becoming more capable as a result?**

# Appendix A · Evidence-routing examples

| **Observed behaviour** | **Primary home** | **Secondary use** |
| --- | --- | --- |
| **Learner ignores the tail of a long AI answer and deliberately returns to the first section.** | Human-AI agency & pacing (D10) | Direction maintenance and metacognition may use it as context, but it is not independently counted there. |
| **Learner compresses “E(x) looks up row x” into a usable operator.** | Operational compression (D04) | May support knowledge coherence, but the primary claim is about usable reconstruction. |
| **Learner asks “Why a Token ID if the token already has a vector?”** | Investigative question generation (D01) | May later reveal distinction-making or assumption detection; the question itself primarily evidences learner-generated inquiry. |
| **Learner refuses a correct but unnecessary sentence because it clutters their own notes.** | Selective uptake (D01) | May support learning ownership; it does not independently prove cognitive retention or authorship transparency. |
| **Learner uses a second model specifically to challenge the first model’s conclusion.** | Multi-AI orchestration (D10) | May contribute to verification context, but the orchestration behaviour has one primary home. |
| **Learner optimises one subsystem, then explicitly re-checks earlier constraints and finds a trade-off elsewhere.** | Global re-check after local optimisation (D06) | May support whole-problem retention, but the re-check is the primary analytical claim. |
| **Learner spends a long period solving a local issue while previously stated constraints disappear from reasoning.** | Resistance to local cognitive capture (D06) — concern | May also explain a poor final solution, but it should not independently depress several other constructs. |

# Appendix B · Seed evidence exemplars

| **Domain** | **Direction** | **Illustrative trace** |
| --- | --- | --- |
| **Agency & Self-Direction** | Supportive | Learner sets a goal, rejects an attractive side path and generates the next investigative question independently. |
| **Agency & Self-Direction** | Concern | Learner repeatedly follows the model’s suggested sequence despite an earlier stated learning goal and does not reassert direction. |
| **Metacognition & Self-Regulation** | Supportive | Learner notices that pace is too fast, names the gap and changes strategy before continuing. |
| **Metacognition & Self-Regulation** | Concern | Learner repeatedly claims understanding but cannot identify what is confusing after failed reconstruction. |
| **Knowledge Integration & Coherence** | Supportive | Learner links several facts into a governing structure and correctly places a new fact within it. |
| **Knowledge Integration & Coherence** | Concern | Learner accumulates correct facts but cannot explain how they relate or resolve a contradiction between them. |
| **Conceptual & Mechanistic Understanding** | Supportive | Learner reconstructs the mechanism on a blank page after the AI explanation is removed. |
| **Conceptual & Mechanistic Understanding** | Concern | Learner can repeat the explanation but cannot explain an intermediate step or adapt it to a changed example. |
| **Transfer & Application** | Supportive | Learner independently recognises the same underlying principle in a new domain and adjusts it for different constraints. |
| **Transfer & Application** | Concern | After explicit prompting, learner still treats a closely analogous problem as unrelated and rebuilds from scratch. |
| **Reasoning, Logic & Systems Thinking** | Supportive | Learner traces a proposal through several consequences, checks interactions and revisits the whole system after local optimisation. |
| **Reasoning, Logic & Systems Thinking** | Concern | Learner stops at the first attractive effect, ignores second-order consequences and loses earlier constraints while optimising one variable. |
| **Epistemic Judgement & Evidence** | Supportive | Learner asks what evidence would distinguish competing explanations and adjusts confidence after a stronger source appears. |
| **Epistemic Judgement & Evidence** | Concern | Learner treats fluent model output as confirmation and does not notice that multiple cited sources derive from the same underlying claim. |
| **Creativity, Synthesis & Range** | Supportive | Learner joins initially distant ideas into a useful new framework and then tests whether the analogy genuinely holds. |
| **Creativity, Synthesis & Range** | Concern | Learner produces many variants but they are cosmetic restatements and no idea is developed or evaluated. |
| **Adaptive Persistence, Precision & Execution** | Supportive | Learner stays with a hard point, changes strategy after a stall, corrects notation and carries the revision through consistently. |
| **Adaptive Persistence, Precision & Execution** | Concern | Learner repeats the same failed move, then bypasses the hard part with a generated answer without resolving the underlying error. |
| **AI Orchestration & Cognitive Control** | Supportive | Learner deliberately controls pace, assigns the AI a narrow role, keeps the learning-critical step for themselves and verifies a consequential claim. |
| **AI Orchestration & Cognitive Control** | Concern | Learner accepts the model’s framing, sequence and answer with little independent judgement while the AI performs the very skill being learned. |

# Appendix C · Longitudinal comparison record

| **Field** | **Longitudinal record** |
| --- | --- |
| **Current state** | What recent comparable evidence supports. |
| **Reference period** | Which earlier episode(s) or period provide the comparison. |
| **Comparability** | Task difficulty, novelty, domain, support, AI assistance, capture quality and opportunity-to-observe comparison. |
| **Direction** | Improving / stable / declining / variable / discontinuous-uncertain / not established. |
| **Magnitude / rate** | Only where the measurement basis justifies it. |
| **Stability** | Whether the pattern repeats across several comparable opportunities. |
| **Retention** | Whether the capability survives after time and removal of the original support. |
| **Transfer** | Whether the change appears in new tasks or domains. |
| **Independence** | Whether equivalent or harder performance occurs with less scaffolding. |
| **Challenge** | Whether the capability survives greater complexity, ambiguity or cognitive load. |
| **Feedback responsiveness** | Whether earlier feedback can be linked to durable later change. |
| **Confidence in trajectory** | How strongly the available history supports the developmental claim. |
| **Unexplained discontinuities** | Any major change without an observable evidentiary bridge, with alternative explanations preserved. |
| **Episode-level result** | When no comparable history exists, the episode-level longitudinal result is `TRJ.NOT_YET_ESTABLISHED`, with the comparability basis recorded; construct-level entries for that episode carry the same state. |

# Appendix D · Proposed teacher report shape (not a fixed UI)

> **REPORT PRINCIPLE** The teacher sees the few findings that matter. The taxonomy, coverage states and full reasoning remain available underneath.

## Most important findings

3–6 plain-language findings, ordered by educational significance rather than by domain number or raw score.

## Change that matters

Any important improvement, regression, newly stable capability or unexplained discontinuity, with confidence in the comparison.

## Strength to leverage

One demonstrated capability that can be used to support the learner’s next challenge.

## Next useful learning opportunity

A small task, prompt or condition that could improve learning or provide a fair opportunity to test an important unobserved capability.

## How the learner used AI

A short paragraph when AI use materially shaped the learning: who led, what was delegated, what was retained, how trust was calibrated.

## Drill-down available underneath

For any finding: construct, provenance, counter-evidence, confounds, opportunity, prior comparable episodes and why the trajectory is trusted.

# Appendix E · Foundational vs AI-era learning

**The point of the era tags is not to declare older capabilities obsolete.** Logic, evidence evaluation, transfer, coherent knowledge, persistence and metacognition remain central. The AI era adds a second intelligence to the learner’s environment and therefore creates new demands around cognitive delegation, trust, pacing, no-outsourcing, orchestration and authorship.

> **AI CHANGES THE LEARNING PROBLEM** The learner must now decide not only what to think, but what the machine should think, how the two should be combined, and whether using the machine is actually making the learner more capable.

# Appendix F · What Draft 3 changes from Draft 2

| **Draft 3 change** | **Why it matters** |
| --- | --- |
| **Reasoning depth becomes explicit** | Draft 3 adds inferential depth / vertical reasoning, chain integrity, consequence tracing, temporal horizon, branching reasoning and stopping discipline. |
| **Systems breadth becomes explicit** | Draft 3 adds horizontal reasoning, interaction/trade-off reasoning, feedback loops, systems boundary awareness and global re-check after local optimisation. |
| **Whole-problem retention becomes explicit** | The learner’s ability to keep salient goals, constraints and prior conclusions active while working locally is now a canonical construct; external scaffolding counts when deliberately used. |
| **Local cognitive capture is named** | Draft 3 treats tunnel vision on the current subproblem or AI reply as a distinctive failure mode, not merely “poor working memory”. |
| **Depth terminology is clarified** | The former “Depth & Mechanistic Understanding” domain is renamed “Conceptual & Mechanistic Understanding” so “reasoning depth” can refer unambiguously to inferential chain depth. |
| **The anti-shortcut rule is strengthened** | The DRE may not finalise the first coherent story; explicit coverage traversal and reasoning-integrity checks precede synthesis. |
| **Trajectory is strengthened** | Change remains a cross-cutting axis and now explicitly includes developmental responsiveness, challenge growth, independence, stability, retention and unexplained discontinuities. |
| **Report / reasoning separation is reinforced** | The taxonomy is internal search space; the teacher report is a selective synthesis; any dashboard remains a future compression of real findings. |

**Reason broadly. Report selectively. Preserve everything underneath.**

# Appendix G · What Draft 3.1 changes from Draft 3

Draft 3.1 is a contract revision. No construct was added, removed, renamed or reworded; no guidepost or era tag was changed; no domain was reordered.

| **Draft 3.1 change** | **Why it matters** |
| --- | --- |
| **Stable domain identifiers `D01`–`D10`** | Draft 3 referred to domains by document section number, which collided with the 1–10 coverage spine: a reference to the tenth section could be misread as the tenth domain. All such references now use `D01`–`D10`. |
| **Immutable construct identifiers** | Each of the 137 constructs has an identifier of the form `Dnn.UPPER_SNAKE`. Findings reference the identifier, so later wording changes do not orphan stored findings. |
| **Controlled vocabularies with identifiers** | Evidence grades, coverage states, judgements, trajectory states, passes and era tags are defined as machine-readable values (`EGR.*`, `COV.*`, `JDG.*`, `TRJ.*`, `PASS.*`, `ERA.*`). A persisted value's identifier is authoritative; the label is display text. |
| **Canonical DRE evidence rules (§3.5)** | The evidentiary contract is restated in one place, normative for this version, so the DRE builder need not read the upstream control documents to learn it. TT evidence is immutable; the DRE builds derived views around it without mutating it. |
| **Analytical observation layer named (§3.6)** | The bridge from raw telemetry to analytical observations is declared a separate, independently versioned DRE layer; decomposition happens once, before routing. |
| **Contract rules (§3.7)** | Identifier immutability, finding provenance (`construct_id`, `taxonomy_version`, file SHA-256), unknown-identifier handling, separate schema version, canonical bytes. |
| **Coarse-to-fine Pass 1 (§2)** | Every construct still ends Pass 1 with a coverage state, but the walk may be cheap where evidence makes it obviously so; a domain-level screen may not silently assign child states. |
| **Pass 5 with no history (§4)** | Pass 5 always executes; with no comparable history the episode-level result is `TRJ.NOT_YET_ESTABLISHED`. Appendix C gains an episode-level row. |
| **Minimum finding record (§3.4)** | Gains `Construct ID`, `Taxonomy version` and `Taxonomy SHA-256`; coverage state and judgement rows reference `COV.*` and `JDG.*`. |
| **Stale count removed (§1)** | The physician rule no longer cites a fixed construct count that had fallen out of date; the current count is 137 and is declared in the file header. |
| **Canonical Markdown form** | The `.md` file is the canonical taxonomy; the `.docx` is generated from it and checked against it. `taxonomy_schema_version` tracks the file grammar independently of content. |
| **Contents table** | Gains a row for the controlled vocabularies; the domains row now shows `D01–D10`. |

**Reason broadly. Report selectively. Preserve everything underneath.**
