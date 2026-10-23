"""Session runner orchestrating perception, engine, persistence, and event streams.

Implements docs/ARCHITECTURE.md §4 and docs/CONTRACTS.md §4-6.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from benchguard.contracts.enums import SessionStatus, TickTrigger
from benchguard.contracts.events import (
    AlertRaisedEvent,
    Event,
    PreflightObject,
    PreflightResult,
    PreflightResultEvent,
    SessionStatusEvent,
)
from benchguard.contracts.ir import Procedure
from benchguard.contracts.observation import (
    AttributeQuery,
    AttributeReading,
    Detection,
    Observation,
)
from benchguard.contracts.state import ManualAction, SessionState
from benchguard.engine import (
    create_initial_state,
    plan,
    plan_attributes,
)
from benchguard.engine import (
    finish as engine_finish,
)
from benchguard.engine import (
    manual as engine_manual,
)
from benchguard.engine import (
    step as engine_step,
)
from benchguard.engine.config import EngineConfig
from benchguard.engine.evaluator import evaluate_predicate
from benchguard.geometry.resolution import resolve_scene


@dataclass(frozen=True)
class StoredFrame:
    """Frame retained in ring buffer."""

    frame_id: str
    t_ms: int
    jpeg_bytes: bytes
    width: int
    height: int


@dataclass(frozen=True)
class _PendingTick:
    """Queued tick parameters for trigger coalescence."""

    trigger: TickTrigger
    frame_id: str
    t_ms: int
    settled: bool


@runtime_checkable
class PerceptionHandler(Protocol):
    """Protocol for perception layer decoupling (WS-P)."""

    async def detect(
        self,
        frame_bytes: bytes,
        concepts: list[str],
    ) -> tuple[list[Detection], int]:
        """Run SAM detection across unique concepts. Returns (detections, latency_ms)."""
        ...

    async def read_attributes(
        self,
        frame_bytes: bytes,
        queries: list[AttributeQuery],
    ) -> tuple[list[AttributeReading], int]:
        """Run Spark VLM queries on unoccluded crops. Returns (readings, latency_ms)."""
        ...


class SessionRunner:
    """Manages an active verification session against a Procedure."""

    def __init__(
        self,
        procedure: Procedure,
        *,
        session_id: str | None = None,
        config: EngineConfig | None = None,
        data_dir: Path | str = "data/sessions",
        clock: Callable[[], int] | None = None,
    ) -> None:
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.procedure = procedure
        self.config = config or EngineConfig()
        self.data_dir = Path(data_dir) / self.session_id
        self._clock = clock or self._default_clock

        self.created_at_ms = self._clock()
        self.started_at_ms: int | None = None
        self.finished_at_ms: int | None = None

        self.state: SessionState = create_initial_state(self.procedure, self.session_id)
        self.state = self.state.model_copy(update={"status": SessionStatus.CREATED})
        self.status: SessionStatus = SessionStatus.CREATED

        self._frames: deque[StoredFrame] = deque(maxlen=5)
        self._frame_index: dict[str, StoredFrame] = {}

        self._events: list[Event] = []
        self._observations: list[Observation] = []
        self._subscribers: set[asyncio.Queue[Event]] = set()

        self._tick_lock = asyncio.Lock()
        self._pending_tick: _PendingTick | None = None

        self._init_storage()

    @staticmethod
    def _default_clock() -> int:
        return int(time.time() * 1000)

    def _init_storage(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "frames").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "evidence").mkdir(parents=True, exist_ok=True)

        proc_path = self.data_dir / "procedure.json"
        if not proc_path.exists():
            proc_path.write_text(
                self.procedure.model_dump_json(indent=2),
                encoding="utf-8",
            )

    # -------------------------------------------------------------------------
    # Frame Management
    # -------------------------------------------------------------------------

    def feed_frame(
        self,
        jpeg_bytes: bytes,
        t_ms: int | None = None,
        width: int = 1280,
        height: int = 720,
        frame_id: str | None = None,
    ) -> str:
        """Feed a new frame into the session's ring buffer."""
        actual_t_ms = self._clock() if t_ms is None else t_ms
        actual_frame_id = frame_id or f"f_{len(self._frame_index) + 1:05d}_{actual_t_ms}"

        stored = StoredFrame(
            frame_id=actual_frame_id,
            t_ms=actual_t_ms,
            jpeg_bytes=jpeg_bytes,
            width=width,
            height=height,
        )
        self._frames.append(stored)
        self._frame_index[actual_frame_id] = stored
        return actual_frame_id

    def get_frame(self, frame_id: str) -> StoredFrame | None:
        """Retrieve stored frame by ID from memory or disk."""
        if frame_id in self._frame_index:
            return self._frame_index[frame_id]

        disk_path = self.data_dir / "frames" / f"{frame_id}.jpg"
        if disk_path.exists():
            jpeg_bytes = disk_path.read_bytes()
            stored = StoredFrame(
                frame_id=frame_id,
                t_ms=0,
                jpeg_bytes=jpeg_bytes,
                width=1280,
                height=720,
            )
            self._frame_index[frame_id] = stored
            return stored

        evidence_path = self.data_dir / "evidence" / f"{frame_id}.jpg"
        if evidence_path.exists():
            jpeg_bytes = evidence_path.read_bytes()
            stored = StoredFrame(
                frame_id=frame_id,
                t_ms=0,
                jpeg_bytes=jpeg_bytes,
                width=1280,
                height=720,
            )
            self._frame_index[frame_id] = stored
            return stored

        return None

    def _save_evidence_frame(self, frame_id: str) -> None:
        stored = self._frame_index.get(frame_id)
        if stored:
            out_path = self.data_dir / "evidence" / f"{frame_id}.jpg"
            if not out_path.exists():
                out_path.write_bytes(stored.jpeg_bytes)

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def start(self, t_ms: int | None = None) -> list[Event]:
        """Start or transition session from CREATED/PAUSED to RUNNING."""
        now = self._clock() if t_ms is None else t_ms
        self.started_at_ms = now
        self.status = SessionStatus.RUNNING
        self.state = self.state.model_copy(update={"status": SessionStatus.RUNNING})

        event = SessionStatusEvent(
            seq=self._next_seq(),
            t_ms=now,
            status=SessionStatus.RUNNING,
        )
        self._record_and_broadcast([event])
        return [event]

    def pause(self, t_ms: int | None = None) -> list[Event]:
        """Pause active session."""
        now = self._clock() if t_ms is None else t_ms
        self.status = SessionStatus.PAUSED
        self.state = self.state.model_copy(update={"status": SessionStatus.PAUSED})

        event = SessionStatusEvent(
            seq=self._next_seq(),
            t_ms=now,
            status=SessionStatus.PAUSED,
        )
        self._record_and_broadcast([event])
        return [event]

    def resume(self, t_ms: int | None = None) -> list[Event]:
        """Resume paused session."""
        now = self._clock() if t_ms is None else t_ms
        self.status = SessionStatus.RUNNING
        self.state = self.state.model_copy(update={"status": SessionStatus.RUNNING})

        event = SessionStatusEvent(
            seq=self._next_seq(),
            t_ms=now,
            status=SessionStatus.RUNNING,
        )
        self._record_and_broadcast([event])
        return [event]

    def manual(self, action: ManualAction, t_ms: int | None = None) -> list[Event]:
        """Apply a manual action to a step."""
        now = self._clock() if t_ms is None else t_ms
        new_state, events = engine_manual(self.procedure, self.state, action, now)
        self.state = new_state
        self._record_and_broadcast(events)
        return events

    def finish(self, t_ms: int | None = None) -> list[Event]:
        """Finish session and mark complete."""
        now = self._clock() if t_ms is None else t_ms
        self.finished_at_ms = now
        self.status = SessionStatus.FINISHED

        new_state, events = engine_finish(self.procedure, self.state, now)
        self.state = new_state
        self._record_and_broadcast(events)
        return events

    # -------------------------------------------------------------------------
    # Preflight Check
    # -------------------------------------------------------------------------

    def run_preflight(
        self,
        frame_bytes: bytes,
        detections: list[Detection],
        *,
        blur_score: float = 120.0,
        brightness: float = 110.0,
        models_ok: dict[str, bool] | None = None,
        t_ms: int | None = None,
    ) -> PreflightResult:
        """Evaluate preflight readiness and detect initial false goals."""
        now = self._clock() if t_ms is None else t_ms
        quality_ok = blur_score >= 50.0 and (30.0 <= brightness <= 230.0)

        # Count objects by concept
        counts_by_concept: dict[str, int] = {}
        for d in detections:
            counts_by_concept[d.concept] = counts_by_concept.get(d.concept, 0) + 1

        preflight_objs: list[PreflightObject] = []
        for obj in self.procedure.objects:
            found = counts_by_concept.get(obj.concept, 0)
            expected = obj.expected_count
            ok = (expected is None and found > 0) or (expected is not None and found == expected)
            suggestion = (
                None if ok else f"Expected {expected or '≥1'} {obj.concept}, found {found}."
            )
            preflight_objs.append(
                PreflightObject(
                    object_id=obj.id,
                    concept=obj.concept,
                    found=found,
                    expected=expected,
                    ok=ok,
                    suggestion=suggestion,
                )
            )

        # Run scene resolution and evaluate goals on preflight frame
        scene = resolve_scene(
            self.procedure.objects,
            detections,
            det_score_min=self.config.det_score_min,
            occlusion_overlap=self.config.occlusion_overlap,
        )

        dummy_obs = Observation(
            tick_id=0,
            t_ms=now,
            frame_id="preflight",
            trigger=TickTrigger.MANUAL,
            settled=True,
            detections=detections,
            readings=[],
            latency_ms={"total": 0},
            n_calls=0,
            errors=[],
            models={"sam": "sam-3.1", "spark": "muse-spark-1.3"},
        )

        goal_true_at_start: list[str] = []
        for step in self.procedure.steps:
            for p_idx, pred in enumerate(step.expects):
                res = evaluate_predicate(
                    pred=pred,
                    step_id=step.id,
                    index=p_idx,
                    obs=dummy_obs,
                    scene=scene,
                    cfg=self.config,
                )
                if res.status.value == "TRUE":
                    goal_true_at_start.append(step.id)
                    break

        result = PreflightResult(
            objects=preflight_objs,
            blur_score=blur_score,
            brightness=brightness,
            quality_ok=quality_ok and all(po.ok for po in preflight_objs),
            goal_true_at_start=goal_true_at_start,
            models_ok=models_ok or {"sam": True, "spark": True},
        )

        event = PreflightResultEvent(
            seq=self._next_seq(),
            t_ms=now,
            result=result,
        )
        self._record_and_broadcast([event])
        return result

    # -------------------------------------------------------------------------
    # Verification Ticks & Coalescence
    # -------------------------------------------------------------------------

    async def process_observation(
        self,
        obs: Observation,
    ) -> tuple[SessionState, list[Event]]:
        """Process an externally-constructed Observation directly."""
        async with self._tick_lock:
            return self._execute_engine_step(obs)

    async def trigger_tick(
        self,
        trigger: TickTrigger,
        *,
        frame_id: str | None = None,
        t_ms: int | None = None,
        perception: PerceptionHandler | None = None,
        settled: bool = True,
    ) -> tuple[SessionState, list[Event]]:
        """Trigger a verification tick with single-tick lock & coalescence."""
        now = self._clock() if t_ms is None else t_ms

        # Pick latest frame if not specified
        if frame_id is None:
            if not self._frames:
                raise ValueError("Cannot trigger tick: no frames fed to session")
            frame_id = self._frames[-1].frame_id

        # Coalescence: if a tick is running, register pending tick and return
        if self._tick_lock.locked():
            self._pending_tick = _PendingTick(
                trigger=trigger,
                frame_id=frame_id,
                t_ms=now,
                settled=settled,
            )
            return self.state, []

        async with self._tick_lock:
            # Execute primary tick
            state, events = await self._run_tick_pipeline(
                trigger=trigger,
                frame_id=frame_id,
                t_ms=now,
                perception=perception,
                settled=settled,
            )

            # Process coalesced tick if one arrived during execution
            while self._pending_tick is not None:
                pending = self._pending_tick
                self._pending_tick = None
                state, pending_events = await self._run_tick_pipeline(
                    trigger=pending.trigger,
                    frame_id=pending.frame_id,
                    t_ms=pending.t_ms,
                    perception=perception,
                    settled=pending.settled,
                )
                events.extend(pending_events)

            return state, events

    async def _run_tick_pipeline(
        self,
        trigger: TickTrigger,
        frame_id: str,
        t_ms: int,
        perception: PerceptionHandler | None,
        settled: bool,
    ) -> tuple[SessionState, list[Event]]:
        frame = self._frame_index.get(frame_id)
        if frame is None:
            raise KeyError(f"Frame {frame_id} not found in runner buffer")

        latency_ms: dict[str, int] = {}
        detections: list[Detection] = []
        readings: list[AttributeReading] = []
        n_calls = 0

        if perception is not None:
            # 1. Plan concepts from active step
            req = plan(self.procedure, self.state)
            if req.concepts:
                t0 = time.perf_counter()
                dets, det_lat = await perception.detect(frame.jpeg_bytes, req.concepts)
                detections.extend(dets)
                latency_ms["sam"] = det_lat or int((time.perf_counter() - t0) * 1000)
                n_calls += len(req.concepts)

            # 2. Plan attributes (cheap first: only settled + unoccluded + present)
            queries = plan_attributes(self.procedure, self.state, detections, settled)
            if queries:
                t1 = time.perf_counter()
                reads, read_lat = await perception.read_attributes(frame.jpeg_bytes, queries)
                readings.extend(reads)
                latency_ms["spark"] = read_lat or int((time.perf_counter() - t1) * 1000)
                n_calls += 1

        latency_ms["total"] = sum(latency_ms.values())

        obs = Observation(
            tick_id=self.state.tick_id + 1,
            t_ms=t_ms,
            frame_id=frame_id,
            trigger=trigger,
            settled=settled,
            detections=detections,
            readings=readings,
            latency_ms=latency_ms,
            n_calls=n_calls,
            errors=[],
            models={"sam": "sam-3.1", "spark": "muse-spark-1.3"},
        )

        return self._execute_engine_step(obs)

    def _execute_engine_step(self, obs: Observation) -> tuple[SessionState, list[Event]]:
        new_state, events = engine_step(self.procedure, self.state, obs, self.config)
        self.state = new_state
        self._observations.append(obs)
        self._record_observation(obs)
        self._record_and_broadcast(events)

        # Check for alert evidence and save frame
        for ev in events:
            if isinstance(ev, AlertRaisedEvent):
                for fid in ev.alert.evidence_frame_ids:
                    self._save_evidence_frame(fid)

        return self.state, events

    # -------------------------------------------------------------------------
    # Pub/Sub Event Stream & Persistence
    # -------------------------------------------------------------------------

    def _next_seq(self) -> int:
        seq = self.state.seq + 1
        self.state = self.state.model_copy(update={"seq": seq})
        return seq

    def subscribe(self) -> asyncio.Queue[Event]:
        """Subscribe to real-time event queue."""
        q: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[Event]) -> None:
        """Unsubscribe from event queue."""
        self._subscribers.discard(q)

    def _record_and_broadcast(self, events: list[Event]) -> None:
        if not events:
            return

        events_file = self.data_dir / "events.jsonl"
        with events_file.open("a", encoding="utf-8") as f:
            for ev in events:
                self._events.append(ev)
                f.write(ev.model_dump_json() + "\n")
                for q in self._subscribers:
                    q.put_nowait(ev)

    def _record_observation(self, obs: Observation) -> None:
        obs_file = self.data_dir / "observations.jsonl"
        with obs_file.open("a", encoding="utf-8") as f:
            f.write(obs.model_dump_json() + "\n")

    def get_events(self, since_seq: int = 0) -> list[Event]:
        """Get past events starting after sequence number `since_seq`."""
        return [e for e in self._events if e.seq > since_seq]

    def get_observations(self) -> list[Observation]:
        """Get all recorded observations."""
        return list(self._observations)
