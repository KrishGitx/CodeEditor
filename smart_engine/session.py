"""
smart_engine.session - Authoritative RecoverySession state machine & budget management.
Maintains execution budgets, action history, batch promotion, and user decisions.
"""

import time
from typing import List, Dict, Any, Optional
from smart_engine.actions import SmartAction, CommandRecord


class RecoverySession:
    """
    Authoritative state tracker for a multi-step Smart Fix / Smart Recovery session.
    Maintains execution budgets, sequential IDs, batch promotion, and plan steps.
    """
    def __init__(
        self,
        session_id: str,
        context: dict,
        maximum_commands: int = 10
    ):
        self.session_id: str = session_id
        self.context: dict = context.copy() if context else {}
        self.maximum_commands: int = maximum_commands
        self.actual_commands_executed: int = 0
        self.next_command_index: int = 1
        
        self.command_history: List[SmartAction] = []
        self.active_batch: List[SmartAction] = []
        self.pending_queue: List[SmartAction] = []
        
        self.total_steps: int = 0
        self.last_displayed_total_steps: Optional[int] = None
        self.status: str = "initialized"
        
        self.final_report: Optional[str] = None
        self.final_diagnosis: Optional[dict] = None
        self.created_at: float = time.time()
        self.waiting_for_approval_cmd: Optional[SmartAction] = None
        
        self.decision_request: Optional[dict] = None
        self.user_decisions: Dict[str, Any] = {}

    @property
    def commands_remaining(self) -> int:
        return max(0, self.maximum_commands - self.actual_commands_executed)

    @property
    def completed_steps(self) -> int:
        return sum(1 for c in self.command_history if c.status == "succeeded")

    @property
    def failed_steps(self) -> int:
        return sum(1 for c in self.command_history if c.status == "failed")

    @property
    def pending_steps(self) -> int:
        return sum(1 for c in self.active_batch if c.status == "pending") + len(self.pending_queue)

    @property
    def planned_steps(self) -> int:
        return self.total_steps

    def generate_next_command_id(self) -> str:
        cid = f"CMD-{self.next_command_index:02d}"
        self.next_command_index += 1
        return cid

    def get_command_by_id(self, command_id: str) -> Optional[SmartAction]:
        for cmd in self.command_history:
            if cmd.action_id == command_id:
                return cmd
        for cmd in self.active_batch:
            if cmd.action_id == command_id:
                return cmd
        for cmd in self.pending_queue:
            if cmd.action_id == command_id:
                return cmd
        return None

    def format_total_steps_display(self) -> Optional[str]:
        if self.last_displayed_total_steps is None or self.last_displayed_total_steps != self.total_steps:
            self.last_displayed_total_steps = self.total_steps
            return f"TOTAL STEPS: {self.total_steps}"
        return None

    def accept_new_batch(self, validated_actions: List[dict], proposed_total: Optional[int] = None) -> List[SmartAction]:
        """
        Accepts actions from AI, assigns sequential IDs without reuse,
        places up to 4 actions in active_batch, and queues the rest in pending_queue.
        """
        new_records: List[SmartAction] = []
        for a in validated_actions:
            aid = self.generate_next_command_id()
            act_type = a.get("action_type") or a.get("actionType") or "command"
            cmd_text = a.get("command", "")
            params = a.get("parameters", {})
            if cmd_text and "command" not in params:
                params["command"] = cmd_text
                
            rec = SmartAction(
                action_id=aid,
                action_type=act_type,
                target=a.get("target", a.get("toolName", "system")),
                parameters=params,
                purpose=a.get("purpose", f"Run {cmd_text or act_type}"),
                requires_approval=bool(a.get("requires_approval") or a.get("requiresApproval")),
                expected_result=a.get("expected_result", a.get("expectedResult", "")),
                failure_handling=a.get("failure_handling", a.get("failureHandling", "abort"))
            )
            if len(self.active_batch) < 4:
                self.active_batch.append(rec)
            else:
                self.pending_queue.append(rec)
            new_records.append(rec)

        min_required = len(self.command_history) + len(self.active_batch) + len(self.pending_queue)
        if proposed_total is not None and isinstance(proposed_total, int) and proposed_total >= min_required:
            self.total_steps = proposed_total
        else:
            self.total_steps = max(self.total_steps, min_required)

        return new_records

    def promote_next_batch(self) -> List[SmartAction]:
        """Promotes queued actions to active_batch up to the 4-item batch limit."""
        promoted: List[SmartAction] = []
        while self.pending_queue and len(self.active_batch) < 4:
            rec = self.pending_queue.pop(0)
            self.active_batch.append(rec)
            promoted.append(rec)
        return promoted

    def replan(self, validated_actions: List[dict], proposed_total: Optional[int] = None) -> List[SmartAction]:
        """
        Replaces remaining active and pending actions with revised plan from AI
        while strictly preserving already executed actions and original budget.
        """
        self.active_batch.clear()
        self.pending_queue.clear()
        return self.accept_new_batch(validated_actions, proposed_total)

    def to_dict(self) -> Dict[str, Any]:
        """Full serialization for QML and tests."""
        total_steps_disp = self.format_total_steps_display()
        active_dicts = [c.to_dict() for c in self.active_batch]
        history_dicts = [c.to_dict() for c in self.command_history]
        pending_dicts = [c.to_dict() for c in self.pending_queue]

        waiting_cmd_dict = self.waiting_for_approval_cmd.to_dict() if self.waiting_for_approval_cmd else None

        return {
            "sessionId": self.session_id,
            "session_id": self.session_id,
            "status": self.status,
            "maximum_commands": self.maximum_commands,
            "maximumCommands": self.maximum_commands,
            "actual_commands_executed": self.actual_commands_executed,
            "actualCommandsExecuted": self.actual_commands_executed,
            "commands_remaining": self.commands_remaining,
            "commandsRemaining": self.commands_remaining,
            "total_steps": self.total_steps,
            "totalSteps": self.total_steps,
            "completed_steps": self.completed_steps,
            "completedSteps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "failedSteps": self.failed_steps,
            "pending_steps": self.pending_steps,
            "pendingSteps": self.pending_steps,
            "total_steps_display": total_steps_disp or (f"TOTAL STEPS: {self.total_steps}" if self.total_steps > 0 else ""),
            "totalStepsDisplay": total_steps_disp or (f"TOTAL STEPS: {self.total_steps}" if self.total_steps > 0 else ""),
            "active_batch": active_dicts,
            "activeBatch": active_dicts,
            "commands": active_dicts,
            "command_history": history_dicts,
            "commandHistory": history_dicts,
            "pending_queue": pending_dicts,
            "pendingQueue": pending_dicts,
            "waiting_for_approval_cmd": waiting_cmd_dict,
            "waitingForApprovalCommand": waiting_cmd_dict,
            "decision_request": self.decision_request,
            "decisionRequest": self.decision_request,
            "needs_user_decision": bool(self.decision_request is not None or self.status == "awaiting_user_decision"),
            "needsUserDecision": bool(self.decision_request is not None or self.status == "awaiting_user_decision"),
            "user_decisions": self.user_decisions,
            "userDecisions": self.user_decisions,
            "final_report": self.final_report or "",
            "finalReport": self.final_report or "",
            "final_diagnosis": self.final_diagnosis or {},
            "finalDiagnosis": self.final_diagnosis or {},
            "context": self.context
        }
