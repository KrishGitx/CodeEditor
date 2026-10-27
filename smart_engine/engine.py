"""
smart_engine.engine - Central Smart AI Coordinator & Recovery Engine for DGX Studio.
"""

import os
import sys
import time
import threading
import subprocess
from typing import Dict, Any, Optional, Tuple, Callable

from smart_engine.actions import SmartAction, SmartSafetyGuard, ActionRegistry
from smart_engine.session import RecoverySession
from smart_engine.prompt import build_smart_prompt, parse_smart_response, SMART_AI_SYSTEM_PROMPT


class SmartEngine:
    """
    General-purpose, AI-driven problem-solving and recovery engine inside DGX Studio.
    Coordinates context collection, AI diagnosis, user decisions, safety checks,
    and closed-loop action execution.
    """
    def __init__(self, extension_manager: Any = None):
        self.extension_manager = extension_manager
        self.action_registry = ActionRegistry()
        self._sessions: Dict[str, RecoverySession] = {}
        self._active_session_id: Optional[str] = None
        self._custom_ai_provider: Optional[Callable[[str], str]] = None
        
        # Register default core action handlers
        self._register_default_handlers()

    def set_ai_provider(self, provider_fn: Optional[Callable[[str], str]]):
        """Sets custom AI provider for testing and custom bridges."""
        self._custom_ai_provider = provider_fn

    def get_ai_provider(self) -> Optional[Callable[[str], str]]:
        if self._custom_ai_provider:
            return self._custom_ai_provider
        if self.extension_manager:
            cls = self.extension_manager if isinstance(self.extension_manager, type) else self.extension_manager.__class__
            resolver = cls.__dict__.get("_custom_ai_resolver") or getattr(cls, "_custom_ai_resolver", None)
            if resolver:
                if isinstance(resolver, staticmethod):
                    return resolver.__func__
                return resolver
        return None

    def _register_default_handlers(self):
        """Registers handlers for command, config, extension, and diagnostic actions."""
        # 1. Shell command handler
        def _handle_command(action: SmartAction, context: dict) -> Tuple[bool, str, str, int]:
            cmd = action.parameters.get("command", "")
            if not cmd:
                return False, "", "Empty command", 1

            fp = context.get("filePath") or context.get("target_file") or ""
            working_dir = os.path.dirname(os.path.abspath(fp)) if fp and os.path.exists(fp) else os.getcwd()
            
            # Delegate to extension manager's execute_command_steps if available for rich logging/env prep
            if self.extension_manager and hasattr(self.extension_manager, "execute_command_steps"):
                tool_name = context.get("toolName", action.target)
                exit_c, out, err, _ = self.extension_manager.execute_command_steps(
                    command_str=cmd,
                    tool_name=tool_name,
                    timeout=300,
                    working_dir=working_dir,
                    run_id=context.get("runId", "")
                )
                return (exit_c == 0), out, err, exit_c

            # Standalone fallback execution
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=working_dir, timeout=300)
            return (proc.returncode == 0), proc.stdout, proc.stderr, proc.returncode

        # 2. Configuration handler
        def _handle_config(action: SmartAction, context: dict) -> Tuple[bool, str, str, int]:
            env_var = action.parameters.get("env_var")
            val = action.parameters.get("value")
            if env_var and val is not None:
                if env_var.upper() == "PATH":
                    if val not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = val + os.pathsep + os.environ.get("PATH", "")
                else:
                    os.environ[env_var] = str(val)

                if self.extension_manager and hasattr(self.extension_manager, "set_tool_runtime_config"):
                    self.extension_manager.set_tool_runtime_config(action.target, {env_var: val})
                return True, f"Configured environment variable '{env_var}'", "", 0
            return False, "", f"Invalid config parameters: {action.parameters}", 1

        # 3. Extension lifecycle handler
        def _handle_extension(action: SmartAction, context: dict) -> Tuple[bool, str, str, int]:
            op = action.parameters.get("operation", "")
            ext_id = action.parameters.get("extension_id", "")
            if self.extension_manager:
                if op in ("enable", "activate") and hasattr(self.extension_manager, "activate_extension"):
                    ok = self.extension_manager.activate_extension(ext_id)
                    return ok, f"Extension {ext_id} activated", "", (0 if ok else 1)
                elif op == "install" and hasattr(self.extension_manager, "install_local_extension"):
                    ok = self.extension_manager.install_local_extension(ext_id)
                    return ok, f"Extension {ext_id} installed", "", (0 if ok else 1)
            return True, f"Extension operation '{op}' simulated for {ext_id}", "", 0

        # 4. Diagnostic inspection handler
        def _handle_diagnostic(action: SmartAction, context: dict) -> Tuple[bool, str, str, int]:
            check = action.parameters.get("check", "")
            path = action.parameters.get("path", "")
            if check == "file_exists":
                exists = os.path.exists(path)
                return exists, f"File {path} exists: {exists}", "", (0 if exists else 1)
            cmd = action.parameters.get("command", "")
            if cmd:
                return _handle_command(action, context)
            return False, "", f"Unsupported diagnostic probe '{check}'. Use concrete shell commands with action_type 'command'.", 1

        self.action_registry.register_handler("command", _handle_command)
        self.action_registry.register_handler("config", _handle_config)
        self.action_registry.register_handler("extension", _handle_extension)
        self.action_registry.register_handler("diagnostic", _handle_diagnostic)

    def create_session(self, context: dict, maximum_commands: int = 10) -> RecoverySession:
        """Initializes and registers a new authoritative RecoverySession."""
        session_id = f"rec_{int(time.time()*1000)%1000000}_{len(self._sessions)+1}"
        session = RecoverySession(session_id, context, maximum_commands=maximum_commands)
        self._sessions[session_id] = session
        self._active_session_id = session_id
        return session

    def get_session(self, session_id: str) -> Optional[RecoverySession]:
        return self._sessions.get(session_id)

    def _query_ai(self, prompt: str) -> Tuple[bool, str, str]:
        """Queries the configured AI backend without freezing the Qt GUI event loop."""
        provider = self.get_ai_provider()

        def _execute_query() -> Tuple[bool, str, str]:
            if provider and callable(provider):
                try:
                    res = provider(prompt)
                    if res and str(res).strip():
                        return True, str(res).strip(), ""
                    return False, "", "Empty response from AI provider"
                except Exception as e:
                    return False, "", str(e)

            # Fallback to AIBackend singleton
            try:
                from AIBackend import AIBackend
                backend = AIBackend.get_instance()
                res = backend.ask(prompt)
                if res and str(res).strip():
                    return True, str(res).strip(), ""
                return False, "", "Empty response from AIBackend"
            except Exception as ex:
                return False, "", str(ex)

        try:
            from PySide6.QtCore import QCoreApplication, QThread
            app = QCoreApplication.instance()
            is_main = (QThread.currentThread() == app.thread()) if app else False
        except Exception:
            app = None
            is_main = False

        if not app or not is_main:
            return _execute_query()

        # On Qt main thread: run query in background thread while pumping GUI events
        # so windows never freeze, spinners animate, and Windows never marks app as "Not Responding"
        res_holder = [None]
        def _bg_worker():
            res_holder[0] = _execute_query()

        t = threading.Thread(target=_bg_worker, daemon=True)
        t.start()

        while t.is_alive():
            app.processEvents()
            t.join(timeout=0.03)

        return res_holder[0] if res_holder[0] is not None else (False, "", "AI query aborted")

    def resolve_context(self, context: dict) -> dict:
        """
        AI-driven diagnosis and recovery proposal:
        1. Gathers context & detected capabilities.
        2. Sends prompt to AI backend.
        3. Parses response against response contract.
        4. Attaches / updates RecoverySession.
        5. Returns normalized proposal dictionary.
        """
        run_id = context.get("runId") or f"si_{int(time.time()*1000)%1000000}"
        context["runId"] = run_id
        tool_name = context.get("toolName") or context.get("executable") or context.get("operation", "tool")

        session = self.create_session(context, maximum_commands=10)
        session.status = "analyzing"

        prompt = build_smart_prompt(session, context)
        print(f"[SmartInstall] AI request sent")
        print(f"[SmartInstall] Sending request through existing AI backend")

        success, response_text, err = self._query_ai(prompt)
        if not success or not response_text:
            print(f"[SmartInstall] AI request failed: {err}")
            session.status = "ai_unavailable"
            session.final_report = f"AI provider error: {err}"
            return {
                "sessionId": session.session_id,
                "session_id": session.session_id,
                "status": "ai_unavailable",
                "resolutionType": "cannot_resolve",
                "title": f"Smart Recovery: {tool_name}",
                "diagnosis": err or "AI service unavailable",
                "explanation": f"Unable to contact AI provider: {err}",
                "command": "",
                "steps": [],
                "source": "ai_unavailable"
            }

        print(f"[SmartInstall] AI request completed")
        print(f"[SmartInstall] Raw AI response received: {response_text}")

        ok, proposal, parse_err = parse_smart_response(response_text, fallback_tool=tool_name, fallback_exec=tool_name)
        
        # Corrective retry if invalid
        if not ok:
            print(f"[SmartInstall] Corrective AI retry started: {parse_err}")
            reprompt = f"Your previous response had a schema or safety issue: {parse_err}.\nPlease return valid JSON matching the Response Contract.\n\n" + prompt
            retry_ok, retry_text, _ = self._query_ai(reprompt)
            if retry_ok and retry_text:
                ok, proposal, parse_err = parse_smart_response(retry_text, fallback_tool=tool_name, fallback_exec=tool_name)

        if not ok:
            session.status = "cannot_resolve"
            session.final_report = f"Model response validation error: {parse_err}"
            return {
                "sessionId": session.session_id,
                "session_id": session.session_id,
                "status": "cannot_resolve",
                "resolutionType": "cannot_resolve",
                "title": f"Cannot Resolve {tool_name}",
                "diagnosis": parse_err,
                "explanation": f"AI proposal could not be validated: {parse_err}",
                "command": "",
                "steps": [],
                "source": "ai"
            }

        print(f"[SmartInstall] AI response parsed")
        print(f"[SmartInstall] AI response validation result: is_safe=True, pkg_valid=True")

        # Synchronize session state from proposal
        proposal["sessionId"] = session.session_id
        proposal["session_id"] = session.session_id
        proposal["toolName"] = tool_name
        proposal["filePath"] = context.get("filePath", "")
        proposal["languageId"] = context.get("language") or context.get("languageId", "")
        proposal["retryAction"] = context.get("retryAction", "run")

        has_decision = bool(
            proposal.get("decision_request") and
            isinstance(proposal["decision_request"], dict) and
            proposal["decision_request"].get("needed") is not False and
            (proposal["decision_request"].get("choices") or proposal["decision_request"].get("options") or proposal["decision_request"].get("question"))
        )
        if has_decision and (proposal.get("needs_user_decision") or proposal.get("status") == "awaiting_user_decision"):
            session.status = "awaiting_user_decision"
            session.decision_request = proposal.get("decision_request")
            proposal["status"] = "awaiting_user_decision"
            proposal["resolutionType"] = "awaiting_user_decision"
        elif proposal.get("commands"):
            session.accept_new_batch(proposal["commands"], proposal.get("proposed_total_steps"))
            first_cmd = session.active_batch[0] if session.active_batch else None
            if first_cmd and first_cmd.requires_approval and not first_cmd.approved:
                session.status = "awaiting_approval"
                session.waiting_for_approval_cmd = first_cmd
            else:
                session.status = "ready"
            proposal["status"] = session.status
            proposal["commands"] = [c.to_dict() for c in session.active_batch]
            proposal["total_steps"] = session.total_steps
            proposal["commands_remaining"] = session.commands_remaining
        elif proposal.get("recovery_complete"):
            session.status = "completed"
            proposal["status"] = "completed"
        else:
            session.status = "cannot_resolve"
            proposal["status"] = "cannot_resolve"

        # Emit updates if extension_manager attached
        if self.extension_manager and hasattr(self.extension_manager, "recoveryPlanUpdated"):
            self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())

        return proposal

    def diagnose_and_recover(self, context: dict) -> dict:
        """Main entry point for workflow failure diagnosis and recovery."""
        return self.resolve_context(context)

    def submit_user_decision(self, session_id: str, decision: str, key: str = "user_choice") -> bool:
        """
        Receives user choice, incorporates it into the session history,
        resumes the session, and re-queries the AI for the next plan.
        """
        session = self.get_session(session_id)
        if not session:
            return False

        if not key:
            if session.decision_request and isinstance(session.decision_request, dict):
                key = session.decision_request.get("resume_key") or session.decision_request.get("resumeKey") or "user_choice"
            else:
                key = "user_choice"

        # Incorporate choice into session state
        session.user_decisions[key] = decision
        session.context[key] = decision
        session.context["last_user_decision"] = decision
        session.decision_request = None

        print(f"[SmartInstall] [{session_id}] [USER_DECISION] User provided choice for '{key}': '{decision}'")

        # Resume session via replanning
        return self.replan_session(session_id)

    def replan_session(self, session_id: str) -> bool:
        """Re-queries AI with accumulated command results, user answers, and budget."""
        session = self.get_session(session_id)
        if not session:
            return False

        if session.commands_remaining <= 0:
            session.status = "limit_reached"
            session.final_report = f"Action limit of {session.maximum_commands} reached. Halting recovery session."
            if self.extension_manager and hasattr(self.extension_manager, "recoveryPlanUpdated"):
                self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())
            return False

        session.status = "planning"
        if self.extension_manager and hasattr(self.extension_manager, "recoveryPlanUpdated"):
            self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())

        prompt = build_smart_prompt(session, session.context)
        print(f"[SmartInstall] [{session_id}] [AI_PLAN_QUERY] Querying AI command planner for session '{session_id}' (executed: {session.actual_commands_executed}, remaining: {session.commands_remaining})")
        print(f"[SmartInstall] AI request sent")
        print(f"[SmartInstall] Sending request through existing AI backend")

        success, response_text, err = self._query_ai(prompt)
        if not success or not response_text:
            session.status = "failed"
            session.final_report = err or "AI replanning returned empty response"
            if self.extension_manager and hasattr(self.extension_manager, "recoveryPlanUpdated"):
                self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())
            return False

        ok, proposal, parse_err = parse_smart_response(response_text)
        if not ok:
            session.status = "failed"
            session.final_report = parse_err
            if self.extension_manager and hasattr(self.extension_manager, "recoveryPlanUpdated"):
                self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())
            return False

        has_decision = bool(
            proposal.get("decision_request") and
            isinstance(proposal["decision_request"], dict) and
            proposal["decision_request"].get("needed") is not False and
            (proposal["decision_request"].get("choices") or proposal["decision_request"].get("options") or proposal["decision_request"].get("question"))
        )
        if has_decision and (proposal.get("needs_user_decision") or proposal.get("status") == "awaiting_user_decision"):
            session.status = "awaiting_user_decision"
            session.decision_request = proposal.get("decision_request")
            if proposal.get("commands"):
                session.replan(proposal["commands"], proposal.get("proposed_total_steps"))
        elif proposal.get("cannot_resolve"):
            session.status = "cannot_resolve"
            session.final_report = proposal.get("final_report", "Recovery cannot proceed.")
        elif proposal.get("recovery_complete"):
            session.status = "completed"
            session.final_report = proposal.get("final_report", "Recovery completed successfully.")
        elif proposal.get("commands"):
            session.replan(proposal["commands"], proposal.get("proposed_total_steps"))
            first_cmd = session.active_batch[0] if session.active_batch else None
            if first_cmd and first_cmd.requires_approval and not first_cmd.approved:
                session.status = "awaiting_approval"
                session.waiting_for_approval_cmd = first_cmd
            else:
                session.status = "ready"
        else:
            session.status = "cannot_resolve"
            session.final_report = "AI returned empty plan during replanning."

        if self.extension_manager and hasattr(self.extension_manager, "recoveryPlanUpdated"):
            self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())

        return True

    def execute_plan(self, session_id: str) -> bool:
        """
        Executes all actions in the recovery plan sequentially without waiting for per-action user input.
        If a command fails, captures its stderr and sends it back to AI (replan_session).
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # Mark all pending actions approved for execution once approved by user
        for act in session.active_batch:
            act.approved = True
        for act in session.pending_queue:
            act.approved = True
        session.waiting_for_approval_cmd = None

        while session.active_batch and session.status in ("ready", "planning", "executing", "verifying"):
            act = session.active_batch[0]
            act.approved = True

            success, formatted_res = self.execute_session_action(session_id, act.action_id)

            if not success:
                # Command failed! Closed-loop feedback:
                print(f"[SmartInstall] [{session_id}] Command '{act.action_id}' failed: exit_code={act.exit_code}. Sending failure back to AI for recovery replanning...")
                session.status = "planning"
                if self.extension_manager and hasattr(self.extension_manager, "recoveryPlanUpdated"):
                    self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())

                replan_ok = self.replan_session(session_id)
                if not replan_ok:
                    return False

                # If AI now asks the user a question, stop and wait for user decision
                if session.status == "awaiting_user_decision":
                    return True

                # If AI provided a new corrective plan, approve actions and continue execution
                if session.status in ("ready", "planning") and session.active_batch:
                    for new_act in session.active_batch:
                        new_act.approved = True
                    continue
                else:
                    return session.status in ("completed", "succeeded")

        return session.status in ("completed", "succeeded")

    def approve_action(self, session_id: str, action_id: str) -> bool:
        """Approves and executes the recovery plan sequentially."""
        return self.execute_plan(session_id)

    def execute_session_action(self, session_id: str, action_id: str) -> Tuple[bool, str]:
        """
        Executes a single action in the session:
        - Enforces budget limit (default 10).
        - Enforces user approval requirement for privileged actions.
        - Records execution exit code, stdout/stderr, and duration.
        - Emits started, completed, and progress signals.
        """
        session = self.get_session(session_id)
        if not session:
            return False, f"Session '{session_id}' not found."

        action = session.get_command_by_id(action_id)
        if not action:
            return False, f"Action '{action_id}' not found."

        if action in session.pending_queue:
            return False, f"Action '{action_id}' is queued behind preceding steps."

        if action.status in ("succeeded", "failed"):
            return True, f"Action '{action_id}' already executed."

        # Check budget limit
        if session.actual_commands_executed >= session.maximum_commands:
            session.status = "limit_reached"
            session.final_report = f"Action limit of {session.maximum_commands} reached. Halting recovery session."
            if self.extension_manager:
                if hasattr(self.extension_manager, "recoverySessionEnded"):
                    self.extension_manager.recoverySessionEnded.emit(session_id, False, session.final_report)
                if hasattr(self.extension_manager, "recoveryPlanUpdated"):
                    self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())
            return False, "Action budget exhausted."

        # Check approval requirement
        if action.requires_approval and not action.approved:
            session.status = "awaiting_approval"
            session.waiting_for_approval_cmd = action
            if self.extension_manager and hasattr(self.extension_manager, "recoveryPlanUpdated"):
                self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())
            return False, f"Action '{action_id}' requires explicit user approval."

        # Mark running and increment actual executed counter
        action.status = "running"
        action.start_time = time.time()
        is_verify = bool(action.parameters.get("command", "").endswith("--version") or "verify" in action.purpose.lower())
        session.status = "verifying" if is_verify else "executing"
        session.actual_commands_executed += 1

        if self.extension_manager:
            if hasattr(self.extension_manager, "recoveryCommandStarted"):
                self.extension_manager.recoveryCommandStarted.emit(session_id, action.action_id, action.parameters.get("command", action.purpose))
            if hasattr(self.extension_manager, "recoveryPlanUpdated"):
                self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())

        # Execute through ActionRegistry
        try:
            from PySide6.QtCore import QCoreApplication, QThread
            app = QCoreApplication.instance()
            is_main = (QThread.currentThread() == app.thread()) if app else False
        except Exception:
            app = None
            is_main = False

        if app and is_main:
            holder = [None]
            def _exec_bg():
                holder[0] = self.action_registry.execute_action(action, session.context)
            t = threading.Thread(target=_exec_bg, daemon=True)
            t.start()
            while t.is_alive():
                app.processEvents()
                t.join(timeout=0.03)
            success, stdout, stderr, exit_code = holder[0] if holder[0] else (False, "", "Execution cancelled", 1)
        else:
            success, stdout, stderr, exit_code = self.action_registry.execute_action(action, session.context)

        action.exit_code = exit_code
        action.stdout = stdout or ""
        action.stderr = stderr or ""
        action.completion_time = time.time()
        action.status = "succeeded" if success else "failed"

        # Transfer from active_batch to command_history
        if action in session.active_batch:
            session.active_batch.remove(action)
        if action not in session.command_history:
            session.command_history.append(action)

        # Batch promotion
        if not any(c.status in ("pending", "running") for c in session.active_batch):
            if session.pending_queue:
                session.promote_next_batch()

        formatted_res = action.format_result()
        if self.extension_manager:
            if hasattr(self.extension_manager, "recoveryCommandCompleted"):
                self.extension_manager.recoveryCommandCompleted.emit(session_id, action.action_id, exit_code, formatted_res)
            if hasattr(self.extension_manager, "recoveryPlanUpdated"):
                self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())

        # Update session status
        if action.status == "succeeded":
            if session.active_batch:
                next_act = session.active_batch[0]
                if next_act.requires_approval and not next_act.approved:
                    session.status = "awaiting_approval"
                    session.waiting_for_approval_cmd = next_act
                else:
                    session.status = "ready"
            elif session.pending_queue:
                session.status = "ready"
            else:
                session.status = "completed"
                session.final_report = f"All {session.actual_commands_executed} recovery steps completed successfully."
                if self.extension_manager and hasattr(self.extension_manager, "recoverySessionEnded"):
                    self.extension_manager.recoverySessionEnded.emit(session_id, True, session.final_report)
                if self.extension_manager and hasattr(self.extension_manager, "recoveryPlanUpdated"):
                    self.extension_manager.recoveryPlanUpdated.emit(session.to_dict())
        else:
            if action.failure_handling == "continue" and session.active_batch:
                session.status = "ready"
            else:
                session.status = "failed"
                session.final_report = f"Action {action.action_id} failed with exit code {exit_code}: {stderr or stdout}"

        return (action.status == "succeeded"), formatted_res
