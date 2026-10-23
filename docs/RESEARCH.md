# RESEARCH.md — Findings, critique, feasibility, risks

Research date: **2026-10-23** (pre-kickoff). Re-verify anything marked ⚠ on Day 1.
Type tags: **FACT** (read in a cited source) · **ASSUMPTION** (unverified; test) · **PROPOSAL** (our choice).

## 1. Sources consulted
| Ref | Source |
|---|---|
| M1 | Meta Model API docs — Models: https://dev.meta.ai/docs/models |
| M2 | Media segmentation: https://dev.meta.ai/docs/media-segmentation |
| M3 | Segmenting with prompts: https://dev.meta.ai/docs/sam/segmenting |
| M4 | SAM client libraries: https://dev.meta.ai/docs/sam/client-libraries |
| M5 | Pricing & rate limits: https://dev.meta.ai/docs/pricing-rate-limits |
| M6 | Structured output: https://dev.meta.ai/docs/structured-output |
| M7 | Image understanding (incl. grounding): https://dev.meta.ai/docs/image-understanding |
| M8 | Muse Code: https://dev.meta.ai/docs/muse-code · config: https://dev.meta.ai/docs/muse-code/configuration |
| H1 | Hackathon page: https://dev.meta.ai/events/global-hackathon (+ Cerebral Valley page) |
| L1 | Survey: *Building Egocentric Procedural AI Assistant* — arXiv 2511.13261 |
| L2 | *Explainable/Transparent Procedural Mistake Detection* — arXiv 2412.11927 |
| L3 | Review: *Vision-Based Mistake Analysis in Procedural Activities* — arXiv 2510.19292 |
| L4 | Loginova, *Language-Grounded Post-Completion Mistake Detection* (thesis, 2026) |
| L5 | *Unreasonable Effectiveness of VLMs for Zero-shot Procedural Mistake Detection* — arXiv 2606.21579 (**abstract/snippet only; not read in full**) |
| C1 | Retrocausal (CB Insights, dealroom, Novus Light), Drishti (Computer Automation, SP-Edge), Roboflow manual-assembly page |
| S1 | Secondary hackathon write-ups (Substack, Internshala, reconscribe.com) — used for dates/ideas only; **official page wins** |

## 2. Verified facts that shape the design
| # | Claim | Type | Src | Impact |
|---|---|---|---|---|
| 1 | Muse Spark 1.3 (`muse-spark-1.3`) accepts text, image, video, audio, **PDF**; returns text; 1,048,576-token context; recommended for new work | FACT | M1 | Resolves PDF's "does Spark take images?" → **yes**. PDF SOP ingestion plausible (spike S5). |
| 2 | Muse Spark supports JSON-schema constrained decoding (`response_format` on Chat Completions; `text.format` on Responses); no recursive schemas; depth ≤ 10 | FACT | M6 | Compiler/attribute outputs are schema-guaranteed; we still validate. |
| 3 | Muse Spark does perception grounding (points/boxes on a 0–1000 grid) | FACT | M7 | Fallback localiser if SAM latency is bad. |
| 4 | SAM 3.1 id `sam-3.1`; image or video input; text noun-phrase **or** box/point prompts; returns boxes + pixel masks | FACT | M1,M3 | Core localiser. |
| 5 | SAM: **one concept per request**; commas/“and”/negation/boolean fail; attributes narrow ("red square"); formatting ignored; absent concept → zero matches (not an error) | FACT | M3 | Fan-out per unique concept; concept phrases must be short noun phrases; calibration needed (preflight). |
| 6 | SAM output is special-token text; Python parser `meta-sam-parser` (≥0.0.6 for confidence) decodes it; `metadata.include_confidence="true"`, `metadata.mask_encoding="one_bit"` supported | FACT | M3,M4 | Use parser; ⚠ exact Python entry-point names unverified (spike S2). |
| 7 | SAM video = uploaded/URL **file** (MP4/MOV; H.264/H.265/MPEG-4; ≤15 000 frames; ≤16 tracked objects); no live stream | FACT | M3 | "Tracking" in live mode = repeated per-snapshot segmentation. Video tracking only for recorded-clip review (F-33). |
| 8 | Pricing: SAM $2.50/1 000 images, $0.20/1 000 video frames; Spark Standard $1.25/M in, $4.25/M out; ~1.3–1.5 k tokens per 1280 px image | FACT | M5,M7 | Cost is negligible (≈ $0.40 per 160-call session); latency, not cost, is the constraint. |
| 9 | Rate limits are per **team**: Spark Standard 3 000 RPM/4 M TPM; SAM 3 000 RPM; Contributor Spark 150 RPM | FACT | M5 | Both devs + eval runs share limits → announce eval runs; Standard mode only. |
| 10 | Standard mode: content **not** used for training; Contributor mode: used for training | FACT | M1,M5 | Camera frames ⇒ Standard only (privacy). |
| 11 | Muse Code is a terminal/CI coding agent (headless `muse exec`), **not** a hosted runtime model; reads `AGENTS.md` first, then `CLAUDE.md`; project memory in `.agents/memory/` | FACT | M8 | Original "Muse Code generates the exported script at runtime" is a poor fit → use Spark API for export; use Muse Code as dev tool; `AGENTS.md` is the shared source. |
| 12 | Muse Voice Transcribe: realtime WS + file endpoint; $0.18/h | FACT | M1,M5 | Optional hands-free commands (F-30). |
| 13 | Hackathon: Oct 26 12:00 PM ET → Nov 4 9:00 PM ET; Indie track = "individual builders and students", judged on creativity, technical ambition, whether it works; Startup = "technical execution… holds up in production"; Official Rules published Oct 26 | FACT | H1 | Recommend Indie. Verify team rules. |
| 14 | Application deadline Oct 25 11:59 PM ET (≈ Oct 26 09:29 IST) or earlier if 20 000 spots fill; approvals by Oct 26 9 AM ET | FACT | H1 | **If you haven't applied, do it now; confirm Tejas applied too.** |
| 15 | Kickoff ≈ Oct 26 21:30 IST (secondary source) | ASSUMPTION ⚠ | S1 | Day 1 is a short evening in IST. |
| 16 | Submission deadline Nov 4 9 PM ET. US DST ends Nov 1 ⇒ ET = UTC−5 ⇒ **07:30 IST Nov 5**; Internshala lists 06:30 IST (assumes EDT) | FACT/⚠ | H1,S1 | Plan to submit ≤ Nov 4 20:00 IST; treat 06:30 IST as hard limit. |
| 17 | Hackathon asks for “Push the Frontier” (software, robotics, manufacturing, science, physical systems) and “Build for Your World” | FACT | H1 | BenchGuard fits both. |
| 18 | Procedural mistake detection (PMD): survey reports egocentric/VLM models near chance on CaptainCook4D and "current models cannot be directly applied" without task-specific work; thesis argues reliable detection needs structured, interpretable mechanisms over black-box VLM judgment | FACT | L1,L4 | Structure-first architecture (state machine + closed predicates + VLM on narrow questions). |
| 19 | Counter-evidence: a 2026 paper's title claims VLMs are "unreasonably effective" zero-shot at PMD | FACT (title only) / ⚠ | L5 | Literature is mixed → we hedge with structure and **measure**; read L5 on Day 1 for prompt ideas. |
| 20 | Datasets define error types incl. omission, addition, modification, slip, correction; IndustReal ties mistake detection to assembly **state progression** | FACT | L3 | Our taxonomy and "state-based verification" align with prior work. |
| 21 | Retrocausal sells camera-based step verification with audible/visual alerts for assembly; Drishti: station cameras, "short training phase" | FACT | C1 | Real market exists; incumbents are factory-station products. Our gap is an **ASSUMPTION** (zero-training, non-factory). |

## 3. Why structure-first (design rationale)
1. Free-form "did the user do it right?" VLM judgment is the weakest link in the literature (rows 18–19). We never ask it.
2. We convert the SOP into **closed-vocabulary predicates** (present/absent/relation/order/attribute) and let a **pure-Python engine** evaluate them from detections + narrow VLM readings.
3. We alarm only on **positive evidence of a specific wrong state** (`docs/ARCHITECTURE.md §6`). "Not done yet" ≠ "error".
4. Every verdict stores evidence → debuggable, honest evaluation.

## 4. Critique of the original proposal (what we changed and why)
| # | Original claim / plan | Problem | Resolution |
|---|---|---|---|
| 1 | "SAM 3.1 … tracks the objects" live at 1–2 fps | Hosted SAM is request/response on an image or a **file**; no live stream; one concept per request | Event-based snapshot segmentation, fan-out per concept; overlay shows last verified masks. Video tracking only offline (F-33). |
| 2 | "Warns … **before** they happen" | System sees only what already occurred | Reword to "as they happen". Add preflight as the only "before". |
| 3 | Muse Spark "decides done/uncertain/problem" | Free-form VLM judgment is unreliable (rows 18–19) and non-deterministic | Spark reads *attributes*; **engine decides**. |
| 4 | Muse Code "generates exported checklist or script" | Muse Code is a CLI dev agent, not a runtime API | Export via Spark API + Python templates; Muse Code is our **development** agent (declare honestly). |
| 5 | "Open-weights model via Baseten/Modal/Fireworks for cheap text" | Extra moving part, little value (Spark text is ~$1.25/M) | Won't. |
| 6 | Pipetting-robot script export | Hardware-adjacent, unverifiable | Won't; export = JSON/MD/HTML (+ optional validated procedure-as-code, F-32). |
| 7 | Protocol B: "multi-step transfer order" | Transfer **actions** and volumes are hard to recognise | State-based verification: design the protocol so each error leaves a **colour signature**; volume = non-goal. |
| 8 | Protocol A: orientation errors | LED legs hide under the breadboard; polarity unreadable from a webcam `[ASSUMPTION]` | Feasibility gate G0; fallback to wrong-position/wrong-object; use distractor parts. |
| 9 | "Caught 17 of 20; 2 false alarms; warning in ~2 s" (example) | Speculative; n=10/class gives wide intervals; 2 s unmeasured | Report Wilson 95 % CIs; define "caught"; measure latency (S1) before promising anything. |
| 10 | Tune on clips, then report on clips | Test-set leakage | **Freeze-before-test**: dev clips for tuning; tag `eval-freeze-v1`; headline = frozen v1; v2 reported separately with caveat. |
| 11 | Parse "step N skipped" | Absence ≠ evidence; false alarms | Skip only via lookahead evidence or at Finish (INCOMPLETE). |
| 12 | Roles by function for a solo/team | Two devs need independent streams | `docs/COLLABORATION.md`: contract-first workstreams with mocks/fixtures. |
| 13 | 10 full days | Kickoff is evening IST ⇒ ~9 effective days; two protocols + 40+ clips + UI is tight | Gates, cut ladder, overlap phases, Day-9 freeze. |
| 14 | PDF "Track: decide" | Startup track needs production proof we can't show | Indie recommended. |

## 5. Feasibility assessment (honest)
| Capability | Confidence | Why / what would change it |
|---|---|---|
| SOP → structured IR with Spark | **High** | Constrained decoding; closed vocab; we lint + human review. |
| Presence/count of distinct objects via SAM (tubes, LED, wires) | **Med-High** | Open-vocab; small parts on breadboard may need concept tuning → preflight. |
| Tube liquid colour from SAM-box crops via Spark | **Med-High** | Good lighting + separable colours (red/blue/yellow/purple/green/clear). Spike S3. |
| Wrong-component (distractor) detection | **Med-High** | Distinct parts; concept presence inside breadboard box. |
| Wrong-order detection | **Med** | Depends on timely settled ticks catching intermediate states; protocol discipline (pause 2 s after each action). |
| LED / battery polarity from a webcam | **Low-Med** | Gate G0 (≥ 80 % on 20 calibration crops) else drop. |
| Time-to-warning ≤ 6 s p95 | **Unknown** | Hosted latency unmeasured; S1 decides. |
| Zero false alarms | **Not promised** | Reduced via positive evidence, debounce, occlusion gating; **measured** and reported. |
| Whole plan (2 protocols, eval, UI) in ~9 days by 2 students | **Med-Low** | ≈ 14.5 person-days of work vs ≈ 17 available; requires the cut ladder. |

## 6. Risk register
| ID | Risk | L | I | Mitigation | Fallback / trigger |
|---|---|---|---|---|---|
| R-01 | SAM or Spark latency too high for "live" feel | M | H | Event-based ticks, parallel fan-out, small crops, 1 tick in flight | Reframe as "verify at settle" (≤ 10 s); amber "checking…" state |
| R-02 | SAM misses small parts / concept phrase sensitivity | M | H | Preflight calibration, concept edit UI, attribute-narrowed phrases, fixed camera + lighting | Larger parts / closer camera; Spark grounding as fallback localiser |
| R-03 | Orientation unreadable | H | M | Gate G0; marker sticker on LED rim (disclosed); close-up crop | Replace with wrong-position error |
| R-04 | VLM colour misreads under glare | M | M | Diffuse light, matte rack, crops, `unclear` option → UNKNOWN | Stronger-contrast dyes |
| R-05 | False alarms annoy users | M | H | Positive-evidence rule, K-tick debounce, hand-occlusion gating, cooldown | Raise thresholds via ADR before freeze |
| R-06 | Test-set leakage / over-tuning | M | H | Dev/test split, freeze tag, report v1 headline | Record small fresh confirmation set |
| R-07 | Shared rate limits (per team) hit during eval | M | M | Announce eval runs, concurrency cap, cassettes for engine tests | Stagger runs |
| R-08 | Model/API outage or behaviour drift mid-hackathon | L | H | Cassettes, backup demo video recorded by Day 8, pinned model ids | Replay mode demo |
| R-09 | Scope creep | H | H | Phase gates, cut ladder, AGENTS R1/R2 | — |
| R-10 | Rules disallow something (team size, models, pre-kickoff docs) | M | M | Read Official Rules Day 1; docs committed post-kickoff | Adjust via ADR |
| R-11 | Two developers conflicting edits | M | M | Directory ownership, contract-first, short PRs | — |
| R-12 | Kickoff evening IST shortens Day 1 | H | L | Day 1 = accounts + smoke calls only | — |
| R-13 | Camera/OS differences (Windows laptop webcams, HTTPS for phone) | M | M | Spike S6 on both machines | Laptop webcam only |

## 7. Differentiation (claims we can defend)
D1–D6 in `PRD.md §7`. We do **not** claim to beat commercial systems on accuracy, nor that incumbents require training for every deployment (only that Drishti's article mentions a training phase).

## 8. Reading list for Day 1 (≈ 45 min total, split)
Prit: M3, M4, M6 · Tejas: M7, M5, L5 · Both: Official Rules, Waiver.
