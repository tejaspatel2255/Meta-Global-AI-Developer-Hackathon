# CONTRACTS.md — Schemas & API

Source of truth is code in `backend/benchguard/contracts/`; this file mirrors it (AGENTS R5). Change both, run `make schemas`. Contract changes need **both** humans' approval. `schema_version = 1`. All coordinates are **normalized** `[0,1]`, boxes `[x1,y1,x2,y2]` (top-left origin). All timestamps `t_ms` are session-relative integers (frame timestamps).

## 1. Enums
```python
class PredicateStatus(str, Enum): TRUE="TRUE"; FALSE="FALSE"; UNKNOWN="UNKNOWN"
class StepStatus(str, Enum): PENDING; ACTIVE; DONE; UNCERTAIN; PROBLEM
class ErrorType(str, Enum):
    WRONG_ORDER; SKIPPED_STEP; REGRESSION; WRONG_POSITION
    WRONG_ORIENTATION; WRONG_OBJECT; WRONG_STATE; MISSING_OBJECT; UNKNOWN_ERROR   # precedence = this order (MISSING_OBJECT only preflight/finish)
class Role(str, Enum): GOAL="goal"; INVARIANT="invariant"
class AttrCategory(str, Enum): ORIENTATION="orientation"; STATE="state"; IDENTITY="identity"
class TickTrigger(str, Enum): CHANGE="change"; MANUAL="manual"; HEARTBEAT="heartbeat"; PREFLIGHT="preflight"
class SessionStatus(str, Enum): CREATED; PREFLIGHT; RUNNING; PAUSED; PAUSED_BUDGET; FINISHED; ERROR
```

## 2. Procedure IR
### 2.1 Objects
```python
class Slot(BaseModel):            # k-th instance of the concept along an axis (deterministic Python mapping)
    axis: Literal["x","y"]; index: int; of: int          # index < of; left→right / top→bottom

class ObjectDef(BaseModel):
    id: str                       # snake_case, unique
    label: str                    # human-readable
    concept: str                  # SAM noun phrase: 1–4 words, no commas/and/or/not; lowercase
    expected_count: int | None    # for preflight (instances of the *concept*)
    slot: Slot | None = None
```
### 2.2 Predicates (discriminated union on `kind`)
```python
class PredBase(BaseModel): role: Role = Role.GOAL; note: str | None = None
class Present(PredBase):  kind: Literal["present"]; object_id: str; min_count: int = 1; max_count: int | None = None
class Absent(PredBase):   kind: Literal["absent"];  object_id: str
class Relation(PredBase): kind: Literal["relation"]; subject_id: str; relation: Literal["left_of","right_of","above","below","inside","overlaps","near"]; target_id: str; negate: bool = False
class OrderAlong(PredBase): kind: Literal["order_along"]; object_ids: list[str]; axis: Literal["x","y"]   # len ≥ 2, increasing
class Attribute(PredBase):
    kind: Literal["attribute"]; object_id: str
    attribute: str                       # e.g. "liquid_color", "led_polarity"
    question: str                        # closed-form question sent with the crop
    allowed: list[str]                   # goal values (non-empty)
    pending: list[str] = []              # benign "not yet" values (disjoint from allowed)
    category: AttrCategory               # drives ErrorType on evidence
    gate: "Predicate | None" = None      # evaluate only if gate TRUE (e.g. led inside breadboard); else UNKNOWN(GATED)
class Confirm(PredBase):  kind: Literal["confirm"]; prompt: str
Predicate = Annotated[Present | Absent | Relation | OrderAlong | Attribute | Confirm, Field(discriminator="kind")]
```
> Recursion: `Attribute.gate` may only hold a **non-recursive** predicate (Present/Absent/Relation/OrderAlong). When exporting JSON Schema for Spark structured output, **inline the gate as a flattened optional field set** (no `$ref` cycles — recursive schemas are rejected, `docs/META_API.md §5`).

### 2.3 Steps & procedure
```python
class ErrorSignature(BaseModel):   # declared positive evidence of a specific wrong state
    error_type: ErrorType; when: list[Predicate]   # ALL must be TRUE; message_hint: str

class Step(BaseModel):
    id: str                        # "s1"…
    index: int
    instruction: str
    expects: list[Predicate]       # goals (must hold for DONE) + invariants (must keep holding)
    errors: list[ErrorSignature] = []
    depends_on: list[str] = []     # step ids; default = previous step
    persistent: bool = False       # re-check after DONE (regression, F-24)
    hints: dict[ErrorType, str] = {}   # optional step-specific wording

class Procedure(BaseModel):
    schema_version: int = 1; id: str; title: str
    source: dict                   # {"kind":"text"|"pdf", "sha256": str}
    objects: list[ObjectDef]; steps: list[Step]
    compile_meta: dict             # {"model","created_at","attempts","warnings":[…]}
```
### 2.4 Lint rules (pure, `compiler/lint.py`; violations ⇒ `LintError`)
ids unique & snake_case/`sN` · all referenced ids exist · concept legal (regex `^[a-z0-9][a-z0-9 \-]{0,38}$`, ≤ 4 words, no `, ; + / and or not`) · each step has ≥ 1 `goal` · `allowed` non-empty, `pending ∩ allowed = ∅` · `slot.index < slot.of` and all objects sharing a concept have consistent `of` · `depends_on` acyclic and refer to earlier steps · `order_along` ≥ 2 ids · attribute `gate` non-recursive · signatures non-empty `when`.

## 3. Perception & observation
```python
class Detection(BaseModel):
    concept: str; instance_id: int; box: Box; score: float | None
    mask_svg: str | None = None      # optional SVG path in normalized coords (size-capped)
class PerceptionRequest(BaseModel):
    concepts: list[str]              # unique; always includes "hand" when occlusion gating enabled
class AttributeQuery(BaseModel):
    query_id: str; object_id: str; attribute: str; question: str
    allowed_values: list[str]        # allowed ∪ pending ∪ (observable others); "unclear" added automatically
    box: Box                         # resolved instance box
class AttributeReading(BaseModel):
    query_id: str; value: str; confidence: float; evidence: str      # evidence ≤ 160 chars
class ModelError(BaseModel): model: str; kind: Literal["timeout","rate_limit","http","parse","budget"]; detail: str
class Observation(BaseModel):
    tick_id: int; t_ms: int; frame_id: str; trigger: TickTrigger; settled: bool
    detections: list[Detection]; readings: list[AttributeReading]
    latency_ms: dict[str,int]        # {"sam","spark","total"}
    n_calls: int; errors: list[ModelError]; models: dict[str,str]   # {"sam":"sam-3.1","spark":"muse-spark-1.3"}
```

## 4. Engine state & events
```python
class PredicateResult(BaseModel):
    step_id: str; index: int; status: PredicateStatus; confidence: float
    reason: str                      # e.g. "OK","OCCLUDED","GATED","SLOT_COUNT_MISMATCH","PENDING_VALUE","EVIDENCE","LOW_CONF"
    benign: bool = False
class StepState(BaseModel):
    step_id: str; status: StepStatus; satisfied_early: bool = False
    consec_true: int = 0; consec_evidence: int = 0; unknown_since_ms: int | None = None
    done_at_ms: int | None = None; done_source: Literal["engine","manual"] | None = None
class Alert(BaseModel):
    id: str; t_ms: int; step_id: str; related_step_id: str | None
    error_type: ErrorType; message: str; confidence: float
    evidence_frame_ids: list[str]; evidence_tick_ids: list[int]
    resolved_at_ms: int | None = None; resolution: str | None = None
class SessionState(BaseModel): ...   # steps, open alerts, counters, cooldowns; fully serialisable
```
### Events (WS server→client and `events.jsonl`; discriminated on `type`)
| `type` | Payload |
|---|---|
| `session.status` | `status: SessionStatus`, `detail?` |
| `preflight.result` | `PreflightResult` (below) |
| `observation.summary` | `tick_id, t_ms, trigger, settled, n_detections, latency_ms, degraded: bool` + overlay boxes for UI |
| `step.updated` | `StepState` + `last_results: list[PredicateResult]` |
| `alert.raised` / `alert.updated` / `alert.resolved` | `Alert` |
| `manual.applied` | `step_id, action, t_ms` |
| `session.finished` | `summary: {step_id: StepStatus|"INCOMPLETE"}`, `report_urls` |
| `error` | `code, message, fatal: bool` |
```python
class PreflightObject(BaseModel): object_id: str; concept: str; found: int; expected: int | None; ok: bool; suggestion: str | None
class PreflightResult(BaseModel):
    objects: list[PreflightObject]; blur_score: float; brightness: float
    quality_ok: bool; goal_true_at_start: list[str]      # step ids; non-empty ⇒ warning
    models_ok: dict[str,bool]
```
Every event also carries `seq: int` (monotonic per session) and `t_ms`.

## 5. REST API (JSON; prefix `/api`)
| Method & path | Body → Response |
|---|---|
| `GET /health` | → `{status, version}` |
| `GET /models` | → `{sam: bool, spark: bool}` (live check; 404 → false) |
| `POST /procedures/compile` | `{sop_text: str(≤20000)}` → `{procedure, warnings[]}` or `422 {code, details}` |
| `POST /procedures/compile-pdf` *(S, F-21)* | multipart `file` → same |
| `PUT /procedures/{id}` | edited `Procedure` → validated+linted `Procedure` or `422` |
| `GET /procedures/{id}` | → `Procedure` |
| `POST /sessions` | `{procedure_id, source:{kind:"live"}|{kind:"clip", path, pace:"realtime"|"fast"}, config_overrides?}` → `{session_id, ws_url}` |
| `POST /sessions/{id}/preflight` | → `PreflightResult` (needs ≥ 1 frame) |
| `POST /sessions/{id}/start` · `/pause` · `/resume` · `/finish` | → `{status}` |
| `POST /sessions/{id}/check` | force tick (Check now) → `202` |
| `POST /sessions/{id}/manual` | `{step_id, action:"done"|"skip"|"confirm"}` → `{status}` |
| `GET /sessions/{id}` | → `{status, procedure_id, steps:[StepState], alerts:[Alert], counters}` |
| `GET /sessions/{id}/report?format=json|md|html` | → report |
| `GET /sessions/{id}/frames/{frame_id}.jpg` | → image |
Errors: `{ "error": {"code","message","details?"} }` with proper HTTP status. Never leak keys or stack traces.

## 6. WebSocket `/ws/sessions/{id}`
- **Client → server (binary):** `[uint32 BE header_len][header JSON UTF-8][JPEG bytes]`; header `{"type":"frame","t_ms":int,"w":int,"h":int}`. Frame rate 1 fps default; max 2 MB/frame.
- **Client → server (text JSON):** `{"type":"ping"}`, `{"type":"check"}` (same as REST check).
- **Server → client (text JSON):** events from §4, plus `{"type":"pong"}`.
- Resume: reconnecting with the same `session_id` within 60 s replays events with `seq > last_seq` (`?last_seq=N`).

## 7. Report schema (`report.json`)
`{session_id, procedure_id, started_at, finished_at, models, steps:[{step_id, instruction, status, done_at_ms, source, alerts:[Alert]}], alerts:[Alert], counters:{ticks, calls, degraded_ticks}, latency:{p50,p95}, caveats:[str]}`. `report.md` renders the same data. `caveats` always include "verified by camera heuristics; not safety-critical".

## 8. Example (Protocol B fragment, abridged)
```json
{"id":"tube_d","label":"Tube D","concept":"test tube","expected_count":5,"slot":{"axis":"x","index":3,"of":5}}
{"id":"s2","index":2,"instruction":"Transfer stock A (red) into tube D.",
 "expects":[
  {"kind":"attribute","object_id":"tube_d","attribute":"liquid_color","question":"What colour is the liquid?",
   "allowed":["red"],"pending":["clear"],"category":"state","role":"goal"},
  {"kind":"attribute","object_id":"tube_e","attribute":"liquid_color","question":"What colour is the liquid?",
   "allowed":["clear"],"pending":[],"category":"state","role":"invariant"}],
 "errors":[],"depends_on":["s1"],"persistent":false}
```
