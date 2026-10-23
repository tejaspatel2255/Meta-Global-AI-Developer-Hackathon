# META_API.md — Verified facts, recipes, pitfalls

**Rule (AGENTS R6):** only rely on rows marked **VERIFIED**. `DOCS` = read in official docs on 2026-10-23 but **not yet exercised live**. `UNVERIFIED` = do not rely; run the spike. When you verify something live, change the status, add date + your initials, and paste the evidence path (`fixtures/spike/…`).
Base URL `https://api.meta.ai/v1` · auth `Authorization: Bearer $MODEL_API_KEY` · OpenAI-compatible SDK works (`OpenAI(base_url=…, api_key=…)`). Docs root: https://dev.meta.ai/docs

## 1. Models we use
| Role | Model id | Endpoint | Mode |
|---|---|---|---|
| Localise (boxes+masks) | `sam-3.1` | Responses `POST /v1/responses` | Standard |
| Compile SOP, read attributes, (optional) polish text, (optional) export | `muse-spark-1.3` | Chat Completions `POST /v1/chat/completions` | Standard (**never** `-contributor`: 150 RPM and trains on content) |
| Optional hands-free commands | `muse-voice-transcribe-1.0` | `wss://api.meta.ai/v1/asr/realtime` | — |
| Dev tooling only | Muse Code (`muse`, `muse exec`) | CLI | — |
Not used: Muse Wonder (preview), Muse Image, Muse Spark Open/Glimmer.

## 2. Facts table
| # | Fact | Status | Source |
|---|---|---|---|
| 1 | `muse-spark-1.3` input: text, image, video, audio, PDF; output: text; context 1,048,576 tokens | DOCS | /docs/models |
| 2 | Audio on Spark 1.3 degraded — irrelevant (we use images) | DOCS | /docs/models |
| 3 | Images: public URL, base64 data URL, or `file_id`; ≤ 50 images/request; ≤ 50 MB inline; JPEG/PNG/WebP/GIF | DOCS | /docs/image-understanding |
| 4 | Only `user`-role messages may carry images | DOCS | /docs/image-understanding |
| 5 | Chat Completions image part: `{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,…"}}`; Responses image part: `{"type":"input_image","image_url":"…"}` | DOCS | /docs/image-understanding |
| 6 | Structured output: Chat Completions `response_format={"type":"json_schema","json_schema":{"name","schema"[,"strict"]}}`; decoding constrained; recursive schemas ⇒ HTTP 400; depth ≤ 10; ≤ 5 000 properties; `strict` default false (behaves same) | DOCS | /docs/structured-output |
| 7 | Responses API uses `text.format` (not `response_format`) — **exact JSON shape UNVERIFIED** ⇒ don't use for Spark | UNVERIFIED | /docs/structured-output |
| 8 | Spark perception grounding: normalized **0–1000** grid; prompts must name objects and demand one output shape; may emit 1001 → clamp | DOCS | /docs/image-understanding |
| 9 | SAM request: Responses API, `model:"sam-3.1"`, one user message with `input_text` (noun phrase) + `input_image` (`image_url`) or `input_video` (`video_url`/`file_id`) | DOCS | /docs/sam/segmenting |
| 10 | SAM: **one concept per request**; `"bus, bicycle"`, `;`, `+`, `and`, newline, 2nd text part ⇒ zero matches or one concept only; negation / OR / spatial phrases unreliable ("person on the left" partly honoured); commands/questions unreliable; plurals/case/punctuation ignored; keep short; attributes narrow predictably | DOCS | /docs/sam/segmenting |
| 11 | Absent concept ⇒ stream completes with empty `output_text` (**not** an error) | DOCS | /docs/sam/segmenting |
| 12 | SAM output = special-token text, one box + one mask per match: `<0f>0<\|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..\|><\|mask;x=0;y=0;data=…\|>`; `x2,y2` inclusive; `w,h` = image size | DOCS | /docs/sam/segmenting |
| 13 | `metadata.include_confidence="true"` (string!) adds `c=` to box/mask tokens; needs `meta-sam-parser` ≥ 0.0.6 (older parsers drop those lines) | DOCS | /docs/sam/segmenting, /docs/sam/client-libraries |
| 14 | `metadata.mask_encoding="one_bit"` ⇒ much smaller mask payloads; box/point prompts always return one_bit | DOCS | /docs/sam/segmenting |
| 15 | Box/point prompts exist (`<0f>1<\|box;…\|>`), same `w`/`h` rules; image prompts on frame 0 only | DOCS | /docs/sam/segmenting |
| 16 | `w`,`h` aspect ratio different from the media ⇒ HTTP 400 | DOCS | /docs/sam/segmenting |
| 17 | Streaming optional; non-streaming returns the same full result | DOCS | /docs/sam/segmenting |
| 18 | Video: MP4/MOV (H.264/H.265/MPEG-4; **not** WebM/VP9); ≤ 15 000 frames; ≤ 16 tracked objects; upload via `POST /v1/files` `purpose=user_data`; MP4 faststart recommended (`ffmpeg -c copy -movflags +faststart`) | DOCS | /docs/sam/segmenting |
| 19 | Python parser `meta-sam-parser` (import `meta_sam_parser`, Python ≥ 3.10, no deps): documented functions `build_object_prompt`, `decode_mask_to_raster`, `decode_mask_to_rle`, `decode_mask_to_svg_path`; stream/parse entry points "mirror the TypeScript contract" — **exact Python names UNVERIFIED** | UNVERIFIED | /docs/sam/client-libraries |
| 20 | Pricing: SAM $2.50 / 1 000 images; $0.20 / 1 000 video frames. Spark Standard $1.25/M in, $0.15/M cached, $4.25/M out. ~1,300–1,500 tokens per 1280-px image | DOCS | /docs/pricing-rate-limits |
| 21 | Rate limits per **team**: Spark Standard 3 000 RPM / 4 M TPM; SAM 3 000 RPM; Contributor Spark 150 RPM; 429 ⇒ exponential backoff + jitter, honour `Retry-After`; headers `x-ratelimit-remaining-*` on token-based responses | DOCS | /docs/pricing-rate-limits |
| 22 | Standard mode content not used for training; Contributor mode may be | DOCS | /docs/models |
| 23 | Errors: 400 invalid prompt/metadata; 404 `model_not_found` (also when team lacks access) | DOCS | /docs/sam/segmenting, /docs/error-handling |
| 24 | Reasoning-effort levels exist (`minimal`…`max`); **parameter name/shape UNVERIFIED** — read /docs/reasoning before use. Default to omitting it. | UNVERIFIED | /docs/models |
| 25 | PDF input to Spark via Files API (`input_file`); first 50 pages as images; details on /docs/file-handling | UNVERIFIED | /docs/image-understanding |
| 26 | Muse Code: `muse exec "<prompt>"` headless; reads `AGENTS.md` first (then `CLAUDE.md`); project memory `.agents/memory/`; default model `muse-spark-1.2`; Windows: PowerShell instead of Bash | DOCS | /docs/muse-code/configuration |
| 27 | Latency of SAM image call and Spark image call | UNVERIFIED | — (spike S1) |
| 28 | Quality of SAM on small parts (resistor, LED) and clear tubes | UNVERIFIED | — (spike S2) |
| 29 | Spark colour reading on tube crops; orientation reading | UNVERIFIED | — (spikes S3, S4) |

## 3. Recipes (adapted from official docs — verify in S1/S2, then update status)
### 3.1 SAM, one concept, one image (non-streaming)
```python
from openai import OpenAI
client = OpenAI(base_url="https://api.meta.ai/v1", api_key=os.environ["MODEL_API_KEY"])
resp = client.responses.create(
    model="sam-3.1",
    input=[{"type":"message","role":"user","content":[
        {"type":"input_text","text":"test tube"},
        {"type":"input_image","image_url":f"data:image/jpeg;base64,{b64}"}]}],
    metadata={"include_confidence":"true","mask_encoding":"one_bit"},
)
raw = resp.output_text          # special-token text; UNVERIFIED that non-streaming exposes output_text this way → check in S2
# parse with meta_sam_parser (entry point TBD in S2); convert px → normalized with w,h from tokens
```
Wrap in `meta_client/sam.py`: `async def segment(image_jpeg: bytes, concept: str) -> list[RawDetection]`. Unit-test the parser with **saved real outputs** in `fixtures/spike/sam_*.txt`.

### 3.2 Spark, batched crops → JSON (Chat Completions)
```python
schema = {"name":"Readings","schema":{"type":"object","properties":{"readings":{"type":"array","items":{
  "type":"object","properties":{"query_id":{"type":"string"},
    "value":{"type":"string","enum":[...closed set + "unclear"...]},   # enum per query: use one schema per distinct value-set, or free string + validate
    "confidence":{"type":"number"},"evidence":{"type":"string"}},
  "required":["query_id","value","confidence","evidence"]}}},"required":["readings"]}}
resp = client.chat.completions.create(
    model="muse-spark-1.3",
    messages=[{"role":"user","content":[
        {"type":"text","text":PROMPT_WITH_QUERIES},
        {"type":"image_url","image_url":{"url":data_url_crop_1}}, ...]}],
    response_format={"type":"json_schema","json_schema":schema},
)
data = json.loads(resp.choices[0].message.content)   # then Pydantic-validate; clamp confidence to [0,1]
```
Prompt rules: list crops as "Image 1 = query q1 …"; ask exactly one question per crop; give the closed set; **no procedure/step context**; say "answer `unclear` if you cannot tell"; ask for ≤ 12-word evidence.

### 3.3 Spark, SOP → IR (Chat Completions)
System: compiler rules (`docs/ARCHITECTURE.md §8`); user: SOP inside `<sop>…</sop>`; `response_format=json_schema` of the **flattened** IR (no recursion). Validate → lint → retry ≤ 3 with lint messages.

## 4. Pitfalls checklist (read before writing perception code)
- Fan out **per unique concept**; never send "tube, hand".
- Don't ask SAM for "red LED not on breadboard" / "leftmost tube" — segment the plain concept, filter in Python.
- Tokens are **pixel** coords with `w,h`; convert to normalized with those exact `w,h`; never resize between request and parsing without tracking.
- Send the same image to every SAM call in a tick (consistency) and keep the JPEG bytes for the evidence frame.
- `include_confidence` must be the **string** `"true"`.
- Zero matches ≠ error. 400 = our bug (don't retry unchanged).
- Per-team limits: announce eval runs; cap concurrency (`perception.max_parallel_sam`).
- Log request **summaries** (model, n_images, bytes, latency), never base64.
- Never log or commit `MODEL_API_KEY`; cassette files must not contain headers.

## 5. Spike verification table (fill in Phase 0)
| Spike | What | Evidence file | Status | Date/by |
|---|---|---|---|---|
| S1 | Latency p50/p95: SAM image, Spark 1-crop, Spark 5-crop (n ≥ 20 each) | `fixtures/spike/latency.json` | ☐ | |
| S2 | SAM: parse output; detect `breadboard`, `resistor`, `led`, `capacitor`, `jumper wire`, `test tube`, `hand` on real frames; confidence distribution | `fixtures/spike/sam_*` | ☐ | |
| S3 | Spark colour reading on ≥ 30 tube crops (6 colours) — accuracy | `fixtures/spike/colour.json` | ☐ | |
| S4 | Spark orientation reading (LED polarity / battery lead colour on rail) on ≥ 20 crops — accuracy | `fixtures/spike/orient.json` | ☐ | |
| S5 | Spark PDF input (`input_file`) → text/IR; or mark Won't | `fixtures/spike/pdf.md` | ☐ | |
| S6 | Browser `getUserMedia` 1280×720 → WS binary frames on both dev machines; phone via HTTPS tunnel optional | `docs/STATUS.md` note | ☐ | |
| S7 | (Could) SAM video on a recorded clip, track IDs | `fixtures/spike/video.txt` | ☐ | |
