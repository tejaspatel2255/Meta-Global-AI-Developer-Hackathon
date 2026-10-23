"""Pure step state machine, alarm rules, and alert lifecycle — docs/ARCHITECTURE.md §6.3, §6.4."""

from __future__ import annotations

from benchguard.contracts.enums import (
    AttrCategory,
    ErrorType,
    PredicateStatus,
    Role,
    StepStatus,
)
from benchguard.contracts.events import (
    AlertRaisedEvent,
    AlertResolvedEvent,
    AlertUpdatedEvent,
    Event,
    StepUpdatedEvent,
)
from benchguard.contracts.ir import Attribute, Procedure, Step
from benchguard.contracts.observation import Observation
from benchguard.contracts.state import Alert, PredicateResult, SessionState, StepState
from benchguard.engine.config import EngineConfig
from benchguard.engine.evaluator import evaluate_predicate
from benchguard.geometry.resolution import ResolvedScene

_ERROR_PRECEDENCE = [
    ErrorType.WRONG_ORDER,
    ErrorType.SKIPPED_STEP,
    ErrorType.REGRESSION,
    ErrorType.WRONG_POSITION,
    ErrorType.WRONG_ORIENTATION,
    ErrorType.WRONG_OBJECT,
    ErrorType.WRONG_STATE,
]


def advance_session(
    proc: Procedure,
    state: SessionState,
    obs: Observation,
    scene: ResolvedScene,
    cfg: EngineConfig,
    confirmed_prompts: set[str] | None = None,
) -> tuple[SessionState, list[Event]]:
    """Advance the pure session state machine for one observation tick."""
    events: list[Event] = []
    seq = state.seq
    t_ms = obs.t_ms

    # Create mapping of current step states
    step_states: dict[str, StepState] = {s.step_id: s.model_copy() for s in state.steps}

    # Identify active step (lowest-index step not DONE)
    sorted_steps = sorted(proc.steps, key=lambda s: s.index)
    active_step: Step | None = None
    for step in sorted_steps:
        s_state = step_states.get(step.id)
        if s_state is not None and s_state.status != StepStatus.DONE:
            active_step = step
            break

    # 1. Evaluate predicates for all steps of interest:
    # - active step
    # - subsequent steps (for early satisfaction / WRONG_ORDER)
    # - persistent DONE steps (for REGRESSION)
    pred_results_by_step: dict[str, list[PredicateResult]] = {}
    candidate_alerts: list[Alert] = []

    for step in sorted_steps:
        s_state = step_states[step.id]
        is_active = active_step is not None and step.id == active_step.id
        is_future = active_step is not None and step.index > active_step.index
        is_persistent_done = s_state.status == StepStatus.DONE and step.persistent

        if not (is_active or is_future or is_persistent_done):
            continue

        results: list[PredicateResult] = []
        for idx, pred in enumerate(step.expects):
            res = evaluate_predicate(
                pred=pred,
                step_id=step.id,
                index=idx,
                obs=obs,
                scene=scene,
                cfg=cfg,
                confirmed_prompts=confirmed_prompts,
            )
            results.append(res)
        pred_results_by_step[step.id] = results

        # 2. Check alarm rules if scene is settled
        if obs.settled:
            alerts = _check_step_alarms(
                step=step,
                s_state=s_state,
                results=results,
                active_step=active_step,
                obs=obs,
                scene=scene,
                cfg=cfg,
                confirmed_prompts=confirmed_prompts,
            )
            candidate_alerts.extend(alerts)

    # 3. Check Order Error (A4) if active step is not satisfied
    if obs.settled and active_step is not None:
        order_alert = _check_order_alarms(
            active_step=active_step,
            sorted_steps=sorted_steps,
            step_states=step_states,
            pred_results=pred_results_by_step,
            obs=obs,
            cfg=cfg,
        )
        if order_alert is not None:
            candidate_alerts.append(order_alert)

    # 4. Filter candidate alerts by cooldown and precedence
    open_alerts = [a.model_copy() for a in state.open_alerts]
    cooldowns = dict(state.cooldowns)
    step_by_id = {s.id: s for s in proc.steps}

    # Reclassify existing WRONG_ORDER alerts to SKIPPED_STEP if threshold elapsed
    for a in open_alerts:
        if a.error_type == ErrorType.WRONG_ORDER and (t_ms - a.t_ms) >= cfg.skip_reclass_ms:
            # Verify active step goals are still not TRUE
            target_step = step_by_id.get(a.step_id)
            act_res = pred_results_by_step.get(a.step_id, [])
            act_goals_true = (
                bool(act_res)
                and target_step is not None
                and all(
                    r.status == PredicateStatus.TRUE
                    for r in act_res
                    if r.index < len(target_step.expects)
                    and target_step.expects[r.index].role == Role.GOAL
                )
            )
            if not act_goals_true:
                a.error_type = ErrorType.SKIPPED_STEP
                a.message = f"Step {a.step_id} skipped: proceeded with step {a.related_step_id}."
                seq += 1
                events.append(AlertUpdatedEvent(seq=seq, t_ms=t_ms, alert=a))

    # Raise new alerts that pass cooldown
    for candidate in sorted(candidate_alerts, key=lambda a: _error_priority(a.error_type)):
        cd_key = f"{candidate.step_id}:{candidate.error_type.value}"
        if t_ms < cooldowns.get(cd_key, 0):
            continue
        # Avoid duplicate open alerts for same (step_id, error_type) or already reclassified
        already_open = any(
            a.step_id == candidate.step_id
            and (
                a.error_type == candidate.error_type
                or (
                    candidate.error_type == ErrorType.WRONG_ORDER
                    and a.error_type == ErrorType.SKIPPED_STEP
                    and a.related_step_id == candidate.related_step_id
                )
            )
            for a in open_alerts
        )
        if not already_open:
            open_alerts.append(candidate)
            seq += 1
            events.append(AlertRaisedEvent(seq=seq, t_ms=t_ms, alert=candidate))
            # Put step into PROBLEM status
            target_st = step_states.get(candidate.step_id)
            if target_st and target_st.status != StepStatus.DONE:
                target_st.status = StepStatus.PROBLEM

    # 5. Advance active step state
    if active_step is not None:
        act_state = step_states[active_step.id]
        act_results = pred_results_by_step.get(active_step.id, [])
        goal_results = [
            r for idx, r in enumerate(act_results) if active_step.expects[idx].role == Role.GOAL
        ]

        all_goals_true = bool(
            goal_results and all(r.status == PredicateStatus.TRUE for r in goal_results)
        )
        any_unknown = any(r.status == PredicateStatus.UNKNOWN for r in act_results)

        if all_goals_true:
            if obs.settled:
                act_state.consec_true += 1
                if act_state.consec_true >= cfg.k_true:
                    act_state.status = StepStatus.DONE
                    act_state.done_at_ms = t_ms
                    act_state.done_source = "engine"
                    act_state.unknown_since_ms = None
            else:
                act_state.consec_true = 0
        else:
            act_state.consec_true = 0
            if obs.settled and any_unknown:
                if act_state.unknown_since_ms is None:
                    act_state.unknown_since_ms = t_ms
                elif (t_ms - act_state.unknown_since_ms) >= cfg.uncertain_after_ms:
                    if act_state.status != StepStatus.PROBLEM:
                        act_state.status = StepStatus.UNCERTAIN
            else:
                act_state.unknown_since_ms = None
                if act_state.status == StepStatus.UNCERTAIN:
                    act_state.status = StepStatus.ACTIVE

    # 6. Resolve alerts if evidence is gone or step is DONE
    surviving_alerts: list[Alert] = []
    for a in open_alerts:
        st = step_states.get(a.step_id)
        step_is_done = st is not None and st.status == StepStatus.DONE
        evidence_present = any(
            ca.step_id == a.step_id
            and (
                ca.error_type == a.error_type
                or (
                    a.error_type == ErrorType.SKIPPED_STEP
                    and ca.error_type == ErrorType.WRONG_ORDER
                    and a.related_step_id == ca.related_step_id
                )
            )
            for ca in candidate_alerts
        )

        if step_is_done or not evidence_present:
            a.resolved_at_ms = t_ms
            a.resolution = "STEP_COMPLETED" if step_is_done else "RESOLVED"
            cooldowns[f"{a.step_id}:{a.error_type.value}"] = t_ms + cfg.alert_cooldown_ms
            seq += 1
            events.append(AlertResolvedEvent(seq=seq, t_ms=t_ms, alert=a))
            if st and st.status == StepStatus.PROBLEM and not step_is_done:
                st.status = StepStatus.ACTIVE
        else:
            surviving_alerts.append(a)

    # 7. Check cascade of subsequent early-satisfied steps
    new_active_step: Step | None = None
    for step in sorted_steps:
        s_state = step_states[step.id]
        if s_state.status != StepStatus.DONE:
            if new_active_step is None:
                new_active_step = step
                if s_state.status == StepStatus.PENDING:
                    s_state.status = StepStatus.ACTIVE
            else:
                # Early satisfaction check for steps after new active
                f_results = pred_results_by_step.get(step.id, [])
                f_goals = [
                    r for idx, r in enumerate(f_results) if step.expects[idx].role == Role.GOAL
                ]
                s_state.satisfied_early = bool(
                    f_goals and all(r.status == PredicateStatus.TRUE for r in f_goals)
                )

    # 8. Emit StepUpdatedEvents
    for step in sorted_steps:
        st = step_states[step.id]
        res_list = pred_results_by_step.get(step.id, [])
        seq += 1
        events.append(
            StepUpdatedEvent(
                seq=seq,
                t_ms=t_ms,
                step=st,
                last_results=res_list,
            )
        )

    # Update session counters
    counters = dict(state.counters)
    counters["ticks"] = counters.get("ticks", 0) + 1

    new_state = SessionState(
        session_id=state.session_id,
        procedure_id=state.procedure_id,
        status=state.status,
        steps=list(step_states.values()),
        open_alerts=surviving_alerts,
        seq=seq,
        tick_id=obs.tick_id,
        n_calls=state.n_calls + obs.n_calls,
        cooldowns=cooldowns,
        counters=counters,
    )
    return new_state, events


def _check_step_alarms(
    step: Step,
    s_state: StepState,
    results: list[PredicateResult],
    active_step: Step | None,
    obs: Observation,
    scene: ResolvedScene,
    cfg: EngineConfig,
    confirmed_prompts: set[str] | None,
) -> list[Alert]:
    alerts: list[Alert] = []
    t_ms = obs.t_ms

    for idx, (pred, res) in enumerate(zip(step.expects, results, strict=False)):
        # Rule A1: Attribute evidence
        if (
            isinstance(pred, Attribute)
            and res.status == PredicateStatus.FALSE
            and not res.benign
            and res.reason == "EVIDENCE"
            and res.confidence >= cfg.alarm_conf_min
        ):
            err_type = _attr_category_to_error(pred.category)
            alerts.append(
                Alert(
                    id=f"alert-{t_ms}-{step.id}-{err_type.value}",
                    t_ms=t_ms,
                    step_id=step.id,
                    error_type=err_type,
                    message=f"Incorrect {pred.category.value} for {pred.object_id} in {step.id}.",
                    confidence=res.confidence,
                    evidence_frame_ids=[obs.frame_id],
                    evidence_tick_ids=[obs.tick_id],
                )
            )

        # Rule A2: Invariant geometry error
        if (
            pred.role == Role.INVARIANT
            and res.status == PredicateStatus.FALSE
            and res.confidence >= cfg.alarm_conf_min
        ):
            alerts.append(
                Alert(
                    id=f"alert-{t_ms}-{step.id}-wrong_position",
                    t_ms=t_ms,
                    step_id=step.id,
                    error_type=ErrorType.WRONG_POSITION,
                    message=f"Position invariant violated for {step.id}.",
                    confidence=res.confidence,
                    evidence_frame_ids=[obs.frame_id],
                    evidence_tick_ids=[obs.tick_id],
                )
            )

        # Rule A5: Regression for persistent DONE step
        if s_state.status == StepStatus.DONE and step.persistent:
            if res.status == PredicateStatus.FALSE and res.confidence >= cfg.alarm_conf_min:
                alerts.append(
                    Alert(
                        id=f"alert-{t_ms}-{step.id}-regression",
                        t_ms=t_ms,
                        step_id=step.id,
                        error_type=ErrorType.REGRESSION,
                        message=f"Regression detected on completed step {step.id}.",
                        confidence=res.confidence,
                        evidence_frame_ids=[obs.frame_id],
                        evidence_tick_ids=[obs.tick_id],
                    )
                )

    # Rule A3: Signature errors
    for sig in step.errors:
        sig_results = [
            evaluate_predicate(
                pred=p,
                step_id=f"{step.id}.error",
                index=i,
                obs=obs,
                scene=scene,
                cfg=cfg,
                confirmed_prompts=confirmed_prompts,
            )
            for i, p in enumerate(sig.when)
        ]
        all_true = all(
            r.status == PredicateStatus.TRUE and r.confidence >= cfg.alarm_conf_min
            for r in sig_results
        )
        if all_true:
            min_c = min(r.confidence for r in sig_results)
            msg = sig.message_hint or f"Error signature detected on {step.id}."
            alerts.append(
                Alert(
                    id=f"alert-{t_ms}-{step.id}-{sig.error_type.value}",
                    t_ms=t_ms,
                    step_id=step.id,
                    error_type=sig.error_type,
                    message=msg,
                    confidence=min_c,
                    evidence_frame_ids=[obs.frame_id],
                    evidence_tick_ids=[obs.tick_id],
                )
            )

    return alerts


def _check_order_alarms(
    active_step: Step,
    sorted_steps: list[Step],
    step_states: dict[str, StepState],
    pred_results: dict[str, list[PredicateResult]],
    obs: Observation,
    cfg: EngineConfig,
) -> Alert | None:
    """Rule A4: Check if a subsequent step is satisfied while active is not DONE."""
    t_ms = obs.t_ms
    for step in sorted_steps:
        if step.index <= active_step.index:
            continue
        st = step_states[step.id]
        if st.status == StepStatus.DONE:
            continue
        results = pred_results.get(step.id, [])
        goal_results = [r for idx, r in enumerate(results) if step.expects[idx].role == Role.GOAL]
        if goal_results and all(
            r.status == PredicateStatus.TRUE and r.confidence >= cfg.alarm_conf_min
            for r in goal_results
        ):
            min_c = min(r.confidence for r in goal_results)
            msg = f"Wrong order: Step {step.id} executed before {active_step.id} is complete."
            return Alert(
                id=f"alert-{t_ms}-{active_step.id}-wrong_order",
                t_ms=t_ms,
                step_id=active_step.id,
                related_step_id=step.id,
                error_type=ErrorType.WRONG_ORDER,
                message=msg,
                confidence=min_c,
                evidence_frame_ids=[obs.frame_id],
                evidence_tick_ids=[obs.tick_id],
            )
    return None


def _attr_category_to_error(cat: AttrCategory) -> ErrorType:
    if cat == AttrCategory.ORIENTATION:
        return ErrorType.WRONG_ORIENTATION
    if cat == AttrCategory.IDENTITY:
        return ErrorType.WRONG_OBJECT
    return ErrorType.WRONG_STATE


def _error_priority(err: ErrorType) -> int:
    try:
        return _ERROR_PRECEDENCE.index(err)
    except ValueError:
        return 999
