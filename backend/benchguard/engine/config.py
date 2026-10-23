"""Injected configuration for the pure engine — docs/ARCHITECTURE.md §6.6."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EngineConfig:
    det_score_min: float = 0.5
    occlusion_overlap: float = 0.25
    k_true: int = 2
    k_false_evidence: int = 2
    k_false_absence: int = 3
    vlm_conf_min: float = 0.6
    alarm_conf_min: float = 0.7
    absence_conf: float = 0.7
    uncertain_after_ms: int = 6000
    skip_reclass_ms: int = 20000
    alert_cooldown_ms: int = 15000
    attr_lookahead_steps: int = 2
    rel_margin: float = 0.01
    call_budget: int = 400
    tick_deadline_ms: int = 10000
