"""
smart_engine.actions - Generic Extensible Action Model & Safety Validation for DGX Studio.
Supports shell commands, environment/config updates, extension lifecycle actions,
and diagnostic inspection probes.
"""

import os
import re
import sys
import shutil
from typing import Dict, Any, Optional, Tuple, Callable


class SmartAction:
    """
    Represents a discrete, verifiable recovery action in DGX Studio.
    """
    def __init__(
        self,
        action_id: str,
        action_type: str = "command",
        target: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        purpose: str = "",
        requires_approval: bool = False,
        expected_result: str = "",
        failure_handling: str = "abort"
    ):
        self.action_id: str = action_id
        self.action_type: str = action_type or "command"
        self.target: str = target or ""
        self.parameters: Dict[str, Any] = parameters or {}
        self.purpose: str = purpose or f"Execute {self.action_type} on {self.target}"
        self.requires_approval: bool = requires_approval
        self.expected_result: str = expected_result
        self.failure_handling: str = failure_handling  # "abort" | "continue"
        
        self.status: str = "pending"  # "pending", "running", "succeeded", "failed", "skipped"
        self.approved: bool = not requires_approval
        self.start_time: Optional[float] = None
        self.completion_time: Optional[float] = None
        self.exit_code: Optional[int] = None
        self.stdout: str = ""
        self.stderr: str = ""
        self.result_data: Dict[str, Any] = {}

    @property
    def command(self) -> str:
        """Backward compatibility for shell commands."""
        return self.parameters.get("command", "")

    @property
    def command_id(self) -> str:
        """Backward compatibility for command identifier."""
        return self.action_id

    @property
    def duration(self) -> float:
        if self.start_time is not None and self.completion_time is not None:
            return round(self.completion_time - self.start_time, 3)
        return 0.0

    def format_result(self) -> str:
        """Returns structured human/AI readable execution summary."""
        dur = f"{self.duration}s" if self.duration > 0 else "0s"
        status_line = f"[{self.action_id}] Type: {self.action_type} | Target: {self.target} | Status: {self.status.upper()} (duration: {dur})"
        if self.action_type == "command":
            cmd = self.parameters.get("command", "")
            return f"{status_line}\nCommand: {cmd}\nExit Code: {self.exit_code}\nStdout: {self.stdout.strip()}\nStderr: {self.stderr.strip()}"
        else:
            return f"{status_line}\nParameters: {self.parameters}\nResult: {self.result_data or self.stdout or self.stderr}"

    def to_dict(self) -> Dict[str, Any]:
        """Dictionary representation for QML and JSON serialization."""
        return {
            "action_id": self.action_id,
            "actionId": self.action_id,
            "command_id": self.action_id,
            "commandId": self.action_id,
            "action_type": self.action_type,
            "actionType": self.action_type,
            "target": self.target,
            "parameters": self.parameters,
            "purpose": self.purpose,
            "requires_approval": self.requires_approval,
            "requiresApproval": self.requires_approval,
            "approved": self.approved,
            "expected_result": self.expected_result,
            "expectedResult": self.expected_result,
            "failure_handling": self.failure_handling,
            "failureHandling": self.failure_handling,
            "status": self.status,
            "exit_code": self.exit_code,
            "exitCode": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration": self.duration,
            "command": self.parameters.get("command", ""),
            "is_verification": bool("--version" in self.parameters.get("command", "") or "-v" in self.parameters.get("command", "") or "verify" in self.purpose.lower())
        }


# Backward-compatible alias for existing tests and QML bindings
CommandRecord = SmartAction


class SmartSafetyGuard:
    """
    Validates proposed actions before execution:
    - Blocks destructive system commands
    - Rejects shell chaining, piping, compound scripts
    - Checks platform compatibility
    - Enforces discrete steps
    """
    @staticmethod
    def validate_command_safety(command: str, tool_name: str = "") -> Tuple[bool, str]:
        if not command or not command.strip():
            return False, "Installation command is empty."

        raw_cmd = command.strip()
        cmd_clean = raw_cmd.lower()

        # Reject conversational prose
        prose_prefixes = (
            "you ", "please ", "to install ", "download ", "first ", "we need to ",
            "make sure ", "ensure ", "run the following", "here is ", "note:", "tip:",
            "after ", "once ", "step 1", "step 2"
        )
        if any(cmd_clean.startswith(p) for p in prose_prefixes):
            return False, "Command rejected: Explanatory prose detected instead of executable command."

        # Blacklist destructive system operations
        destructive_patterns = [
            r"\brm\s+-[a-zA-Z]*r",
            r"\bdel\s+/[a-zA-Z]*f",
            r"\bformat\s+[a-zA-Z]:",
            r"\bmkfs\b",
            r"\bdd\s+if=",
            r"\bshutdown\b",
            r"\breboot\b",
            r":\(\)\s*\{\s*:\|:&\s*\};:",
            r">\s*/dev/sd",
            r"\bdrop\s+database\b",
            r"\bchmod\s+-[a-zA-Z]*R\s+777\s+/",
        ]
        for pat in destructive_patterns:
            if re.search(pat, cmd_clean):
                return False, "Command rejected: Destructive or unsafe system operation detected."

        # Reject platform mismatches
        is_windows = (sys.platform == "win32")
        is_darwin = (sys.platform == "darwin")
        is_linux = sys.platform.startswith("linux")

        if is_windows:
            unix_only = [r"\bbrew\b", r"\bapt\b", r"\bapt-get\b", r"\bpacman\b", r"\byum\b", r"\bdnf\b", r"\bsudo\b"]
            for mgr in unix_only:
                if re.search(mgr, cmd_clean):
                    return False, f"Command rejected: Platform mismatch. Unix tool ({mgr.strip(r'\\b')}) cannot run on Windows."
        elif is_darwin or is_linux:
            windows_only = [r"\bwinget\b", r"\bchoco\b", r"\bscoop\b"]
            for mgr in windows_only:
                if re.search(mgr, cmd_clean):
                    return False, f"Command rejected: Platform mismatch. Windows tool ({mgr.strip(r'\\b')}) cannot run on {sys.platform}."

        # Reject compound PowerShell scripts
        if re.search(r"\bpowershell(?:\.exe)?\b.*-(?:c|command)\b.*[;&|]", cmd_clean):
            return False, "Command rejected: Compound PowerShell script detected. Execute commands as individual steps."

        # Reject shell chaining / piping
        unquoted = re.sub(r'("[^"]*"|\'[^\']*\')', '', cmd_clean)
        if any(chain_op in unquoted for chain_op in ("&&", ";", "||", "|")):
            return False, "Command rejected: Shell chaining or piping detected. Execute commands as individual steps."

        # Reject single-ampersand backgrounding / chaining
        call_match = re.match(r"^\s*&\s*", raw_cmd)
        if call_match:
            remainder = raw_cmd[call_match.end():].strip().lower()
            if re.search(r"(?<!&)&(?!&)", remainder):
                return False, "Command rejected: Shell backgrounding or chaining (&) detected. Execute commands as individual steps."
        else:
            if re.search(r"(?<!&)&(?!&)", cmd_clean):
                return False, "Command rejected: Shell backgrounding or chaining (&) detected. Execute commands as individual steps."

        # Reject multi-line commands
        if "\n" in raw_cmd or "\r" in raw_cmd:
            return False, "Command rejected: Multi-line command detected. Execute commands as individual steps."

        # Reject command substitutions
        if re.search(r"\$\(.*?\)|`.*?`", raw_cmd):
            return False, "Command rejected: Command substitution detected. Execute commands as individual steps."

        # Reject encoded commands
        if any(enc in cmd_clean for enc in ("-encodedcommand", "-enc ")):
            return False, "Command rejected: Encoded command execution detected."

        # Reject output redirection
        if re.search(r"(?<![=<>])>{1,2}(?![=])", raw_cmd):
            return False, "Command rejected: Shell output redirection (>) detected. Execute commands as individual steps."

        return True, "Valid"

    @staticmethod
    def validate_action(action: SmartAction, tool_name: str = "") -> Tuple[bool, str]:
        """Validates any SmartAction based on its action_type."""
        if action.action_type == "command":
            cmd = action.parameters.get("command", "")
            if not cmd:
                return False, "Command action requires a non-empty 'command' parameter."
            return SmartSafetyGuard.validate_command_safety(cmd, tool_name)
        elif action.action_type == "config":
            if not action.parameters.get("env_var") and not action.parameters.get("config_key"):
                return False, "Config action requires 'env_var' or 'config_key' parameter."
            return True, "Valid config action"
        elif action.action_type == "extension":
            op = action.parameters.get("operation", "")
            ext_id = action.parameters.get("extension_id", "")
            if not op or not ext_id:
                return False, "Extension action requires 'operation' and 'extension_id' parameters."
            return True, "Valid extension action"
        elif action.action_type == "diagnostic":
            check = action.parameters.get("check", "")
            cmd = action.parameters.get("command", "")
            if check == "file_exists" and action.parameters.get("path"):
                return True, "Valid diagnostic file check"
            if cmd:
                return SmartSafetyGuard.validate_command_safety(cmd, tool_name)
            return False, f"Diagnostic probe '{check}' is not supported. Use concrete shell commands with action_type 'command' to inspect or verify tools."
        return False, f"Unsupported action type: '{action.action_type}'"


class ActionRegistry:
    """
    Registry for action executors. Allows DGX Studio extensions and core
    to register action handlers without modifying the SmartEngine core.
    """
    def __init__(self):
        self._handlers: Dict[str, Callable[[SmartAction, dict], Tuple[bool, str, str, int]]] = {}

    def register_handler(self, action_type: str, handler: Callable[[SmartAction, dict], Tuple[bool, str, str, int]]):
        self._handlers[action_type] = handler

    def execute_action(self, action: SmartAction, context: dict) -> Tuple[bool, str, str, int]:
        """
        Executes action through registered handler.
        Returns: (success: bool, stdout: str, stderr: str, exit_code: int)
        """
        handler = self._handlers.get(action.action_type)
        if not handler:
            return False, "", f"No handler registered for action type '{action.action_type}'", 1
        return handler(action, context)
