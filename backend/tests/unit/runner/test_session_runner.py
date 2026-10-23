"""Unit tests for SessionRunner (Phase 4 / WS-E)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from benchguard.contracts.boxes import Box
from benchguard.contracts.enums import SessionStatus, StepStatus, TickTrigger
from benchguard.contracts.events import (
    SessionFinishedEvent,
    SessionStatusEvent,
    StepUpdatedEvent,
)
from benchguard.contracts.ir import (
    ObjectDef,
    Present,
    Procedure,
    Step,
)
from benchguard.contracts.observation import (
    AttributeQuery,
    AttributeReading,
    Detection,
)
from benchguard.contracts.state import ManualAction
from benchguard.runner.session_runner import PerceptionHandler, SessionRunner


def _make_test_procedure() -> Procedure:
    """Minimal 2-step procedure for runner tests."""
    return Procedure(
        id="test_proc",
        title="Test Procedure",
        source={"type": "text", "hash": "test1234"},
        objects=[
            ObjectDef(id="breadboard", label="Breadboard", concept="breadboard", expected_count=1),
            ObjectDef(id="led", label="Red LED", concept="red led", expected_count=1),
        ],
        steps=[
            Step(
                id="s1",
                index=1,
                instruction="Place the breadboard.",
                expects=[
                    Present(object_id="breadboard"),
                ],
            ),
            Step(
                id="s2",
                index=2,
                instruction="Insert the red LED.",
                expects=[
                    Present(object_id="led"),
                ],
                depends_on=["s1"],
            ),
        ],
    )


class MockPerception(PerceptionHandler):
    """Deterministic mock perception handler for runner testing."""

    def __init__(
        self,
        detections: list[Detection] | None = None,
        readings: list[AttributeReading] | None = None,
        delay_s: float = 0.0,
    ) -> None:
        self.detections = detections or []
        self.readings = readings or []
        self.delay_s = delay_s
        self.detect_calls: list[list[str]] = []
        self.read_calls: list[list[AttributeQuery]] = []

    async def detect(
        self,
        frame_bytes: bytes,
        concepts: list[str],
    ) -> tuple[list[Detection], int]:
        self.detect_calls.append(concepts)
        if self.delay_s > 0:
            await asyncio.sleep(self.delay_s)
        return self.detections, 15

    async def read_attributes(
        self,
        frame_bytes: bytes,
        queries: list[AttributeQuery],
    ) -> tuple[list[AttributeReading], int]:
        self.read_calls.append(queries)
        if self.delay_s > 0:
            await asyncio.sleep(self.delay_s)
        return self.readings, 20


@pytest.mark.asyncio
async def test_session_runner_init_and_storage(tmp_path: Path) -> None:
    proc = _make_test_procedure()
    clock_ms = 1000

    runner = SessionRunner(
        procedure=proc,
        session_id="sess_001",
        data_dir=tmp_path,
        clock=lambda: clock_ms,
    )

    assert runner.session_id == "sess_001"
    assert runner.status == SessionStatus.CREATED
    assert runner.created_at_ms == 1000
    assert runner.state.status == SessionStatus.CREATED
    assert len(runner.state.steps) == 2
    assert runner.state.steps[0].status == StepStatus.ACTIVE
    assert runner.state.steps[1].status == StepStatus.PENDING

    # Verify disk files
    sess_dir = tmp_path / "sess_001"
    assert sess_dir.exists()
    assert (sess_dir / "procedure.json").exists()
    assert (sess_dir / "frames").is_dir()
    assert (sess_dir / "evidence").is_dir()


@pytest.mark.asyncio
async def test_feed_frame_ring_buffer(tmp_path: Path) -> None:
    proc = _make_test_procedure()
    runner = SessionRunner(procedure=proc, session_id="sess_002", data_dir=tmp_path)

    frame_ids = []
    for i in range(7):
        fid = runner.feed_frame(
            jpeg_bytes=f"fake_jpeg_{i}".encode(),
            t_ms=1000 + i * 100,
            frame_id=f"frame_{i:03d}",
        )
        frame_ids.append(fid)

    # Ring buffer keeps only the last 5
    assert len(runner._frames) == 5
    assert runner._frames[0].frame_id == "frame_002"
    assert runner._frames[-1].frame_id == "frame_006"

    # get_frame retrieves stored frame
    f = runner.get_frame("frame_006")
    assert f is not None
    assert f.jpeg_bytes == b"fake_jpeg_6"


@pytest.mark.asyncio
async def test_lifecycle_transitions(tmp_path: Path) -> None:
    proc = _make_test_procedure()
    runner = SessionRunner(procedure=proc, session_id="sess_003", data_dir=tmp_path)

    events_q = runner.subscribe()

    # 1. Start
    ev_start = runner.start(t_ms=2000)
    assert runner.status == SessionStatus.RUNNING
    assert runner.started_at_ms == 2000
    assert len(ev_start) == 1
    assert isinstance(ev_start[0], SessionStatusEvent)
    assert ev_start[0].status == SessionStatus.RUNNING

    # 2. Pause
    ev_pause = runner.pause(t_ms=2500)
    assert runner.status == SessionStatus.PAUSED
    assert ev_pause[0].status == SessionStatus.PAUSED

    # 3. Resume
    ev_resume = runner.resume(t_ms=3000)
    assert runner.status == SessionStatus.RUNNING
    assert ev_resume[0].status == SessionStatus.RUNNING

    # 4. Manual Done on step 1
    ev_manual = runner.manual(ManualAction(step_id="s1", action="done"), t_ms=3500)
    assert any(isinstance(e, StepUpdatedEvent) and e.step.step_id == "s1" for e in ev_manual)
    assert runner.state.steps[0].status == StepStatus.DONE
    assert runner.state.steps[1].status == StepStatus.ACTIVE

    # 5. Finish
    ev_finish = runner.finish(t_ms=4000)
    assert runner.status == SessionStatus.FINISHED
    assert runner.finished_at_ms == 4000
    assert any(isinstance(e, SessionFinishedEvent) for e in ev_finish)

    # Verify event queue received all events
    received_events = []
    while not events_q.empty():
        received_events.append(events_q.get_nowait())
    assert len(received_events) >= 5

    # Verify reconnect catch-up (get_events since_seq)
    all_events = runner.get_events(since_seq=0)
    assert len(all_events) == len(received_events)
    recent = runner.get_events(since_seq=all_events[-2].seq)
    assert len(recent) == 1


@pytest.mark.asyncio
async def test_preflight_check(tmp_path: Path) -> None:
    proc = _make_test_procedure()
    runner = SessionRunner(procedure=proc, session_id="sess_004", data_dir=tmp_path)

    # 1. Missing breadboard
    res_bad = runner.run_preflight(
        frame_bytes=b"dummy",
        detections=[],
        blur_score=100.0,
        brightness=120.0,
        t_ms=1000,
    )
    assert not res_bad.quality_ok
    assert any(obj.object_id == "breadboard" and not obj.ok for obj in res_bad.objects)

    # 2. Breadboard present
    res_good = runner.run_preflight(
        frame_bytes=b"dummy",
        detections=[
            Detection(
                concept="breadboard",
                instance_id=1,
                box=Box(x1=0.1, y1=0.1, x2=0.9, y2=0.9),
                score=0.95,
            )
        ],
        blur_score=120.0,
        brightness=130.0,
        t_ms=1100,
    )
    # breadboard ok, led ok because expected is None or found == 0 when expected=1 is not ok
    bb_obj = next(o for o in res_good.objects if o.object_id == "breadboard")
    assert bb_obj.ok
    assert "s1" in res_good.goal_true_at_start  # breadboard present at start is caught!


@pytest.mark.asyncio
async def test_trigger_tick_with_mock_perception(tmp_path: Path) -> None:
    proc = _make_test_procedure()
    runner = SessionRunner(procedure=proc, session_id="sess_005", data_dir=tmp_path)
    runner.start(t_ms=1000)

    # Feed a frame
    runner.feed_frame(b"jpeg_data", t_ms=1000, frame_id="f001")

    # Mock perception returns the breadboard
    mock_perc = MockPerception(
        detections=[
            Detection(
                concept="breadboard",
                instance_id=1,
                box=Box(x1=0.2, y1=0.2, x2=0.8, y2=0.8),
                score=0.92,
            )
        ]
    )

    # Tick 1: breadboard present once
    state1, evs1 = await runner.trigger_tick(
        trigger=TickTrigger.CHANGE,
        frame_id="f001",
        t_ms=1100,
        perception=mock_perc,
        settled=True,
    )
    assert state1.steps[0].consec_true == 1
    assert state1.steps[0].status == StepStatus.ACTIVE

    # Tick 2: breadboard present twice (k_true=2) -> step 1 becomes DONE!
    runner.feed_frame(b"jpeg_data_2", t_ms=1800, frame_id="f002")
    state2, evs2 = await runner.trigger_tick(
        trigger=TickTrigger.HEARTBEAT,
        frame_id="f002",
        t_ms=1900,
        perception=mock_perc,
        settled=True,
    )
    assert state2.steps[0].status == StepStatus.DONE
    assert state2.steps[1].status == StepStatus.ACTIVE

    # Check persistence files
    assert (tmp_path / "sess_005" / "observations.jsonl").exists()
    assert (tmp_path / "sess_005" / "events.jsonl").exists()

    obs_lines = (tmp_path / "sess_005" / "observations.jsonl").read_text().strip().splitlines()
    assert len(obs_lines) == 2


@pytest.mark.asyncio
async def test_tick_coalescence_under_lock(tmp_path: Path) -> None:
    proc = _make_test_procedure()
    runner = SessionRunner(procedure=proc, session_id="sess_006", data_dir=tmp_path)
    runner.start(t_ms=1000)

    runner.feed_frame(b"frame_1", t_ms=1000, frame_id="f1")
    runner.feed_frame(b"frame_2", t_ms=1100, frame_id="f2")

    # Perception with 100ms artificial delay
    slow_perc = MockPerception(
        detections=[
            Detection(
                concept="breadboard",
                instance_id=1,
                box=Box(x1=0.2, y1=0.2, x2=0.8, y2=0.8),
                score=0.9,
            )
        ],
        delay_s=0.1,
    )

    # Launch tick 1 as background task
    t1_task = asyncio.create_task(
        runner.trigger_tick(
            trigger=TickTrigger.CHANGE,
            frame_id="f1",
            t_ms=1000,
            perception=slow_perc,
        )
    )

    # Give t1 a moment to acquire the tick lock
    await asyncio.sleep(0.02)
    assert runner._tick_lock.locked()

    # Trigger second and third ticks while tick 1 is running -> they coalesce
    t2_state, t2_evs = await runner.trigger_tick(
        trigger=TickTrigger.CHANGE,
        frame_id="f1",
        t_ms=1050,
        perception=slow_perc,
    )
    # Returns immediately with empty events because tick was queued/coalesced
    assert t2_evs == []
    assert runner._pending_tick is not None

    # Third trigger coalesces into the pending slot
    t3_state, t3_evs = await runner.trigger_tick(
        trigger=TickTrigger.MANUAL,
        frame_id="f2",
        t_ms=1080,
        perception=slow_perc,
    )
    assert t3_evs == []
    assert runner._pending_tick.trigger == TickTrigger.MANUAL
    assert runner._pending_tick.frame_id == "f2"

    # Await completion of the task chain
    await t1_task

    # The pending tick should have been processed automatically by the lock loop
    assert runner._pending_tick is None
    assert runner.state.tick_id == 2
