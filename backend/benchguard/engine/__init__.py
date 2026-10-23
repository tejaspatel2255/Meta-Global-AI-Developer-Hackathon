"""Pure deterministic BenchGuard Engine — docs/ARCHITECTURE.md §6."""

from __future__ import annotations

from typing import Literal

from benchguard.contracts.enums import (
    PredicateStatus,
    SessionStatus,
    StepStatus,
    TickTrigger,
)
from benchguard.contracts.events import (
    AlertResolvedEvent,
    Event,
    ManualAppliedEvent,
    ObservationSummaryEvent,
    OverlayBox,
    SessionFinishedEvent,
    StepUpdatedEvent,
)
from benchguard.contracts.ir import (
    Attribute,
    Procedure,
)
from benchguard.contracts.observation import (
    AttributeQuery,
    Detection,
    Observation,
    PerceptionRequest,
)
from benchguard.contracts.state import (
    ManualAction,
    SessionState,
    StepState,
)
from benchguard.engine.config import EngineConfig
from benchguard.engine.evaluator import evaluate_predicate, make_query_id
from benchguard.engine.machine import advance_session
from benchguard.geometry.resolution import resolve_scene

_DEFAULT_CONFIG = EngineConfig()


def create_initial_state(proc: Procedure, session_id: str) -> SessionState:
    """Create a fresh SessionState for a procedure."""
    steps = []
    for idx, step in enumerate(sorted(proc.steps, key=lambda s: s.index)):
        initial_status = StepStatus.ACTIVE if idx == 0 else StepStatus.PENDING
        steps.append(
            StepState(
                step_id=step.id,
                status=initial_status,
                satisfied_early=False,
                consec_true=0,
                consec_evidence=0,
                unknown_since_ms=None,
                done_at_ms=None,
                done_source=None,
            )
        )
    return SessionState(
        session_id=session_id,
        procedure_id=proc.id,
        status=SessionStatus.RUNNING,
        steps=steps,
        open_alerts=[],
        seq=0,
        tick_id=0,
        n_calls=0,
        cooldowns={},
        counters={"ticks": 0},
    )


def plan(proc: Procedure, state: SessionState) -> PerceptionRequest:
    """Determine the unique concepts that SAM must detect this tick."""
    concepts: set[str] = {"hand"}
    step_states = {s.step_id: s for s in state.steps}

    # Map object id to concept
    obj_concepts = {obj.id: obj.concept for obj in proc.objects}

    for step in proc.steps:
        s_state = step_states.get(step.id)
        is_done = s_state is not None and s_state.status == StepStatus.DONE

        if not is_done or step.persistent:
            for pred in step.expects:
                _collect_predicate_concepts(pred, obj_concepts, concepts)
            for sig in step.errors:
                for pred in sig.when:
                    _collect_predicate_concepts(pred, obj_concepts, concepts)

    return PerceptionRequest(concepts=sorted(concepts))


def plan_attributes(
    proc: Procedure,
    state: SessionState,
    detections: list[Detection],
    settled: bool,
    cfg: EngineConfig | None = None,
) -> list[AttributeQuery]:
    """Cheap first attribute planning — docs/ARCHITECTURE.md §4."""
    if not settled:
        return []

    c = cfg or _DEFAULT_CONFIG
    scene = resolve_scene(
        objects=proc.objects,
        detections=detections,
        det_score_min=c.det_score_min,
        occlusion_overlap=c.occlusion_overlap,
    )

    # Find active step index
    step_states = {s.step_id: s for s in state.steps}
    sorted_steps = sorted(proc.steps, key=lambda s: s.index)
    active_idx = 0
    for idx, s in enumerate(sorted_steps):
        st = step_states.get(s.id)
        if st is not None and st.status != StepStatus.DONE:
            active_idx = idx
            break

    # Lookahead steps
    lookahead_steps = sorted_steps[active_idx : active_idx + 1 + c.attr_lookahead_steps]

    queries: list[AttributeQuery] = []
    dummy_obs = Observation(
        tick_id=0,
        t_ms=0,
        frame_id="",
        trigger=TickTrigger.CHANGE,
        settled=settled,
        detections=detections,
        readings=[],
        latency_ms={},
        n_calls=0,
        errors=[],
        models={},
    )

    for step in lookahead_steps:
        for idx, pred in enumerate(step.expects):
            if isinstance(pred, Attribute):
                resolved = scene.get(pred.object_id)
                if resolved and resolved.is_valid and resolved.box is not None:
                    # If gate exists, it must be TRUE
                    if pred.gate is not None:
                        gate_res = evaluate_predicate(
                            pred=pred.gate,
                            step_id=step.id,
                            index=idx,
                            obs=dummy_obs,
                            scene=scene,
                            cfg=c,
                        )
                        if gate_res.status != PredicateStatus.TRUE:
                            continue

                    qid = make_query_id(step.id, idx, pred.object_id, pred.attribute)
                    allowed_vals = sorted(list(set(pred.allowed + pred.pending + ["unclear"])))
                    queries.append(
                        AttributeQuery(
                            query_id=qid,
                            object_id=pred.object_id,
                            attribute=pred.attribute,
                            question=pred.question,
                            allowed_values=allowed_vals,
                            box=resolved.box,
                        )
                    )
    return queries


def step(
    proc: Procedure,
    state: SessionState,
    obs: Observation,
    cfg: EngineConfig | None = None,
    confirmed_prompts: set[str] | None = None,
) -> tuple[SessionState, list[Event]]:
    """Advance engine by one observation tick."""
    c = cfg or _DEFAULT_CONFIG
    scene = resolve_scene(
        objects=proc.objects,
        detections=obs.detections,
        det_score_min=c.det_score_min,
        occlusion_overlap=c.occlusion_overlap,
    )

    # 1. Observation summary event
    seq = state.seq + 1
    overlays = [OverlayBox(concept=d.concept, box=d.box, score=d.score) for d in scene.detections]
    summary_event = ObservationSummaryEvent(
        seq=seq,
        t_ms=obs.t_ms,
        tick_id=obs.tick_id,
        trigger=obs.trigger.value,
        settled=obs.settled,
        n_detections=len(scene.detections),
        latency_ms=obs.latency_ms,
        degraded=bool(obs.errors),
        overlay=overlays,
    )

    interim_state = state.model_copy(update={"seq": seq})
    advanced_state, step_events = advance_session(
        proc=proc,
        state=interim_state,
        obs=obs,
        scene=scene,
        cfg=c,
        confirmed_prompts=confirmed_prompts,
    )

    return advanced_state, [summary_event, *step_events]


def manual(
    proc: Procedure,
    state: SessionState,
    action: ManualAction,
    t_ms: int,
) -> tuple[SessionState, list[Event]]:
    """Apply manual intervention to a step."""
    seq = state.seq + 1
    events: list[Event] = [
        ManualAppliedEvent(
            seq=seq,
            t_ms=t_ms,
            step_id=action.step_id,
            action=action.action,
        )
    ]

    step_states = {s.step_id: s.model_copy() for s in state.steps}
    target = step_states.get(action.step_id)
    if target is None:
        return state, events

    open_alerts = [a.model_copy() for a in state.open_alerts]
    surviving_alerts = []

    if action.action in {"done", "skip"}:
        target.status = StepStatus.DONE
        target.done_at_ms = t_ms
        target.done_source = "manual"
        target.unknown_since_ms = None

        # Resolve open alerts for this step
        for a in open_alerts:
            if a.step_id == action.step_id:
                a.resolved_at_ms = t_ms
                a.resolution = "MANUAL_DONE"
                seq += 1
                events.append(AlertResolvedEvent(seq=seq, t_ms=t_ms, alert=a))
            else:
                surviving_alerts.append(a)

        # Advance next step to ACTIVE
        sorted_steps = sorted(proc.steps, key=lambda s: s.index)
        for s in sorted_steps:
            st = step_states[s.id]
            if st.status != StepStatus.DONE:
                st.status = StepStatus.ACTIVE
                break

    for step in proc.steps:
        st = step_states[step.id]
        seq += 1
        events.append(
            StepUpdatedEvent(
                seq=seq,
                t_ms=t_ms,
                step=st,
                last_results=[],
            )
        )

    new_state = state.model_copy(
        update={
            "steps": list(step_states.values()),
            "open_alerts": surviving_alerts,
            "seq": seq,
        }
    )
    return new_state, events


def finish(
    proc: Procedure,
    state: SessionState,
    t_ms: int,
) -> tuple[SessionState, list[Event]]:
    """Mark session as finished and generate summary event."""
    seq = state.seq + 1
    summary: dict[str, StepStatus | Literal["INCOMPLETE"]] = {}
    for st in state.steps:
        summary[st.step_id] = st.status if st.status == StepStatus.DONE else "INCOMPLETE"

    finish_event = SessionFinishedEvent(
        seq=seq,
        t_ms=t_ms,
        summary=summary,
        report_urls={
            "json": f"/api/sessions/{state.session_id}/report?format=json",
            "md": f"/api/sessions/{state.session_id}/report?format=md",
        },
    )

    new_state = state.model_copy(
        update={
            "status": SessionStatus.FINISHED,
            "seq": seq,
        }
    )
    return new_state, [finish_event]


def _collect_predicate_concepts(
    pred: object,
    obj_concepts: dict[str, str],
    concepts: set[str],
) -> None:
    if hasattr(pred, "object_id"):
        oid = getattr(pred, "object_id")
        if oid in obj_concepts:
            concepts.add(obj_concepts[oid])
    if hasattr(pred, "subject_id"):
        sid = getattr(pred, "subject_id")
        if sid in obj_concepts:
            concepts.add(obj_concepts[sid])
    if hasattr(pred, "target_id"):
        tid = getattr(pred, "target_id")
        if tid in obj_concepts:
            concepts.add(obj_concepts[tid])
    if hasattr(pred, "object_ids"):
        oids = getattr(pred, "object_ids")
        for oid in oids:
            if oid in obj_concepts:
                concepts.add(obj_concepts[oid])
