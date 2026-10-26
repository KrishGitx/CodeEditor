"""
smart_engine - General-Purpose AI Problem-Solving and Recovery Architecture for DGX Studio.
"""

from smart_engine.actions import SmartAction, CommandRecord, SmartSafetyGuard, ActionRegistry
from smart_engine.session import RecoverySession
from smart_engine.prompt import (
    SMART_AI_SYSTEM_PROMPT,
    build_smart_prompt,
    parse_smart_response,
    validate_ai_plan_response
)
from smart_engine.engine import SmartEngine

__all__ = [
    "SmartEngine",
    "RecoverySession",
    "SmartAction",
    "CommandRecord",
    "SmartSafetyGuard",
    "ActionRegistry",
    "SMART_AI_SYSTEM_PROMPT",
    "build_smart_prompt",
    "parse_smart_response",
    "validate_ai_plan_response"
]
