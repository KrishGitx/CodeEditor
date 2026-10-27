"""
smart_engine.prompt - System Prompt, Context Assembly & Response Contract Parser for DGX Studio.
"""

import json
import re
from typing import Dict, Any, Tuple, Optional, List
from smart_engine.actions import SmartSafetyGuard


SMART_AI_SYSTEM_PROMPT = """You are Smart AI, the general-purpose problem-solving and recovery engine inside DGX Studio.

Your responsibility is to understand a user's intended task, diagnose problems using available evidence, develop appropriate solutions, and guide the application through a safe, verifiable recovery process.

### 1. General Reasoning
- You are not a collection of predefined error handlers.
- Analyze each problem using its actual context. Do not assume that an error belongs to a known category simply because a familiar keyword appears.
- Do not rely on predefined recovery workflows for particular languages, file extensions, databases, compilers, tools, or technologies.
- Use only the verified tools, capabilities, environmental information, diagnostics, and evidence provided by DGX Studio.
- If relevant information is missing, determine whether it can be obtained through available diagnostics or whether you need to ask the user.
- Distinguish observed facts from hypotheses. Never present an unverified hypothesis as an established fact.

### 2. Concrete Resolution Over Speculation
- Understand what the user was attempting to accomplish, what failed, what the actual output indicates, and what conditions may have caused the failure.
- When an installation or configuration is required to resolve a missing runner or tool, emit concrete installation commands using package managers available on the system (e.g. winget on Windows, pip in Python).
- Do not stop at abstract diagnostic speculation. Every recovery plan must lead to concrete, executable installation or configuration steps that resolve the user's workflow failure.

### 3. Use Actual Capabilities
- Use only the tools, extensions, actions, and execution interfaces described in the supplied capability context.
- Never invent a tool, installation path, available version, successful command execution, or system capability.
- When information about the environment is unknown, identify what evidence is needed to resolve that uncertainty.
- Do not claim to have inspected a file, executed an action, or modified a project unless the application has supplied evidence that this occurred.

### 4. Plan Concrete Resolution Actions
- Every recovery plan MUST propose concrete, actionable steps to resolve the workflow failure.
- When resolving a missing runner, executable, compiler, or package:
  - You MUST emit concrete executable shell commands to install or configure the capability (e.g. `winget install SQLite.SQLite`, `pip install <package>`, `npm install -g <package>`).
  - Use the package managers verified in the environment (e.g. winget on Windows, pip in Python).
- Supported action types:
  - "command": Execute a single safe shell command (parameters: {"command": "<exact command>"}). One command per action. Do NOT combine multiple commands using '&&', ';', '|', or multi-line scripts.
  - "config": Update runtime environment or project configuration (parameters: {"env_var": "<key>", "value": "<val>"} or {"config_key": "<key>", "config_value": "<val>"}).
  - "extension": Manage a DGX extension (parameters: {"operation": "install"|"enable"|"reload", "extension_id": "<id>"}).
- DO NOT emit abstract, placeholder, or invented "diagnostic" check names (e.g. "discover_sql_runners" or "check_sqlite_runtime_and_executable").
- If you need to verify or probe a tool or runtime, use a real executable shell command via "command" (e.g., `<tool> --version`, `where <tool>`, or `python -c "<import_or_check>"`).
- CRITICAL: Never declare completion ("completion.verified": true) without actually installing or configuring the missing tool/runner that caused the failure. An inspection alone does NOT solve the failure.
- Propose at most 4 actions in a single batch.
- Each action must have a clear purpose, required parameters, expected result, and verification condition.
- Mark 'requires_approval: true' for any action that installs software, modifies system files, or changes configuration.
- Do not execute actions yourself or claim they have run. The application validates, requests approval when required, and executes your proposed actions.

### 5. Ask Questions Only When Necessary
- Ask the user for information when the answer materially affects the correct solution and cannot reasonably be obtained through available diagnostics.
- Each question must be specific to the current situation. Explain why the information is necessary.
- Generate choices dynamically from verified capabilities and relevant context. Offer free-text input when appropriate.
- Do not ask questions whose answers can already be determined from the available evidence.
- Do not provide arbitrary default choices or assume an answer when the user's decision is genuinely required.
- When the user responds, incorporate their answer into the existing recovery session and reassess the problem.

### 6. Treat Execution Results as New Evidence
- After each executed action, evaluate its actual output, exit status, and other relevant results.
- Determine whether the action succeeded, failed, partially succeeded, or left the problem unresolved.
- Update your diagnosis and recovery plan accordingly.
- Never assume an action succeeded solely because it was attempted.
- Do not keep repeating failed actions without analyzing why they failed.

### 7. Handle Limitations Honestly
- When evidence is insufficient, explain what remains unknown.
- When a required capability is unavailable, identify the limitation and determine whether a supported alternative exists.
- When a task is impossible within the available environment or safety constraints, explain the concrete reason and identify reasonable alternatives.
- Do not repeatedly return an unexplained generic failure response.
- Do not fabricate a successful outcome to satisfy the user.

### 8. Respect Safety and Policy Boundaries
- All proposed actions must pass through DGX Studio's application-side safety and permission checks.
- Never attempt to bypass those controls.
- The application, not the model, is responsible for enforcing action restrictions, approval requirements, execution budgets, and permissions.

### 9. Preserve Continuity
- Use the current recovery session's conversation history, diagnostics, previous plans, execution results, user answers, and remaining budget.
- Replanning must not erase prior evidence or reset limits.

### 10. Output Structured Decisions (JSON Only)
You MUST respond with valid JSON matching the DGX Studio Smart AI Response Contract.
Do not wrap your response in introductory text, markdown commentary, or explanations outside the JSON object.
"""


def build_smart_prompt(session: Any, context: Optional[dict] = None) -> str:
    """
    Builds the complete query prompt sent to the AI backend.
    Assembles authoritative facts from diagnostic probes, failure details,
    prior execution history, user decisions, and execution budget.
    """
    ctx = (context or session.context or {}).copy()
    op = ctx.get("operation") or "Resolution"
    op_type = ctx.get("operationType") or ctx.get("operation_type") or "tool"
    lang = ctx.get("language") or ctx.get("languageId") or ""
    tool_name = ctx.get("toolName") or ctx.get("executable") or ""
    cur_os = ctx.get("operatingSystem") or sys.platform
    pms = ", ".join(ctx.get("availablePackageManagers", [])) or "standard system package managers"
    py_path = ctx.get("pythonExecutable") or sys.executable

    # Verified diagnostic facts
    facts = [
        f"- Target Operation: {op} ({op_type})",
        f"- Language / Ecosystem: {lang or 'general'}",
        f"- Operating System: {cur_os}",
        f"- Active Python: {py_path}",
        f"- Package Managers Detected: {pms}"
    ]
    if tool_name:
        facts.append(f"- Tool / Executable: {tool_name}")
    if ctx.get("installed_jdks"):
        facts.append(f"- Installed JDKs Detected: {ctx.get('installed_jdks')}")
    if ctx.get("available_extensions"):
        facts.append(f"- Available DGX Extensions: {ctx.get('available_extensions')}")
    if ctx.get("detectedMissingDependency"):
        facts.append(f"- Detected Missing Component: {ctx.get('detectedMissingDependency')}")

    facts_block = "\n".join(facts)

    # Failure Evidence
    evidence = []
    if ctx.get("filePath"):
        evidence.append(f"Target File: {ctx.get('filePath')}")
    if ctx.get("commandAttempted") or ctx.get("command"):
        evidence.append(f"Command Attempted: {ctx.get('commandAttempted') or ctx.get('command')}")
    if ctx.get("exitCode") is not None:
        evidence.append(f"Exit Code: {ctx.get('exitCode')}")
    if ctx.get("stdout"):
        evidence.append(f"Stdout:\n{ctx.get('stdout')}")
    if ctx.get("stderr") or ctx.get("errorMessage"):
        evidence.append(f"Stderr / Error:\n{ctx.get('stderr') or ctx.get('errorMessage')}")

    evidence_block = "\n".join(evidence) if evidence else "No diagnostic output captured."

    # User decisions
    user_dec_block = ""
    if session and session.user_decisions:
        user_dec_items = "\n".join([f"- {k}: {v}" for k, v in session.user_decisions.items()])
        user_dec_block = f"USER DECISIONS AND CLARIFICATIONS:\n{user_dec_items}\n\n"

    # Prior executed history
    history_str = ""
    if session and session.command_history:
        history_str = "\n\n".join([c.format_result() for c in session.command_history])
    else:
        history_str = "(No actions executed yet)"

    budget_remaining = session.commands_remaining if session else 10
    budget_total = session.maximum_commands if session else 10

    prompt = f"""{SMART_AI_SYSTEM_PROMPT}

================================================================================
RECOVERY SESSION CONTEXT
================================================================================
AUTHORITATIVE FACTS & DETECTED CAPABILITIES:
{facts_block}

FAILURE EVIDENCE:
{evidence_block}

{user_dec_block}PREVIOUS EXECUTED ACTIONS AND ACTUAL RESULTS:
{history_str}

ACTION EXECUTION BUDGET REMAINING:
{budget_remaining} / {budget_total} actions

================================================================================
RESPONSE CONTRACT (JSON ONLY, NO COMMENTARY OUTSIDE JSON):
================================================================================
{{
  "status": "awaiting_user_decision" | "planning" | "completed" | "cannot_resolve",
  "diagnosis": {{
    "summary": "<concise problem summary>",
    "root_cause": "<root cause supported by evidence>",
    "evidence": ["<evidence point 1>", "<evidence point 2>"]
  }},
  "decision_request": {{
    "needed": false,
    "question": "<question for user if clarification needed>",
    "why_necessary": "<why this information is necessary>",
    "choices": ["<choice 1>", "<choice 2>"],
    "allow_custom_answer": true,
    "resume_key": "<key_name>"
  }},
  "plan": {{
    "proposed_total_steps": 1,
    "actions": [
      {{
        "action_type": "command",
        "target": "{tool_name or 'tool'}",
        "purpose": "Verify {tool_name or 'tool'} version",
        "parameters": {{
          "command": "{tool_name or 'tool'} --version"
        }},
        "requires_approval": false,
        "expected_result": "Version printed",
        "failure_handling": "abort"
      }}
    ]
  }},
  "completion": {{
    "verified": false,
    "final_report": ""
  }},
  "blocker": {{
    "is_blocked": false,
    "reason": "",
    "recommended_alternatives": []
  }}
}}
"""
    return prompt


def parse_smart_response(
    response_text: str,
    fallback_tool: str = "",
    fallback_exec: str = ""
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Parses and validates AI response conforming to the DGX Studio Smart AI Response Contract.
    Robustly handles markdown fences, unescaped Windows backslashes, and schema normalization.
    """
    if not response_text or not str(response_text).strip():
        return False, {}, "AI returned an empty response."

    text = str(response_text).strip()
    if text.lower().startswith("chatgpt said:"):
        text = text[13:].strip()

    # Extract JSON candidate from text or markdown code fence
    json_cand = text
    if "```json" in text or "```" in text:
        m = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text, re.IGNORECASE)
        if m:
            json_cand = m.group(1).strip()
    elif "{" in text and "}" in text:
        m = re.search(r'(\{[\s\S]+\})', text)
        if m:
            json_cand = m.group(1).strip()

    data = None
    try:
        data = json.loads(json_cand)
    except Exception:
        try:
            # Repair unescaped backslashes in Windows file paths
            repaired = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', json_cand)
            data = json.loads(repaired)
        except Exception as ex:
            return False, {}, f"Invalid JSON format in AI response: {ex}"

    if not isinstance(data, dict):
        return False, {}, "AI response root must be a JSON object."

    # 1. Normalize decision request
    decision_req = data.get("decision_request") or data.get("decisionRequest")
    raw_needs = bool(data.get("needs_user_decision", data.get("needsUserDecision", False))) or data.get("status") == "awaiting_user_decision"

    is_decision_active = False
    if decision_req and isinstance(decision_req, dict):
        is_needed = decision_req.get("needed")
        q = str(decision_req.get("question") or "").strip()
        choices = decision_req.get("choices") or decision_req.get("options") or []
        if not isinstance(choices, list):
            choices = []
        if q.startswith("<question") or q.lower() in ("none", "null", "n/a", ""):
            q = ""

        # If needed is explicitly False, or if neither question nor choices are provided, disable decision request
        if is_needed is False or (not q and not choices):
            decision_req = None
            is_decision_active = False
        else:
            is_decision_active = True
            decision_req["question"] = q
            decision_req["choices"] = choices
            decision_req["options"] = choices
            if "why_necessary" in decision_req and "whyNecessary" not in decision_req:
                decision_req["whyNecessary"] = decision_req["why_necessary"]
            if "resume_key" in decision_req and "resumeKey" not in decision_req:
                decision_req["resumeKey"] = decision_req["resume_key"]
            if "allow_custom_answer" in decision_req and "allowCustomAnswer" not in decision_req:
                decision_req["allowCustomAnswer"] = decision_req["allow_custom_answer"]
    elif raw_needs or "question" in data or "choices" in data or "options" in data:
        q = str(data.get("question") or data.get("title") or "").strip()
        choices = data.get("choices", data.get("options", []))
        if not isinstance(choices, list):
            choices = []
        if q.startswith("<question") or q.lower() in ("none", "null", "n/a", ""):
            q = ""
        if q or choices:
            decision_req = {
                "question": q,
                "why_necessary": data.get("why_necessary", data.get("whyNecessary", data.get("explanation", data.get("diagnosis", "")))),
                "whyNecessary": data.get("why_necessary", data.get("whyNecessary", data.get("explanation", data.get("diagnosis", "")))),
                "choices": choices,
                "options": choices,
                "allow_custom_answer": bool(data.get("allow_custom_answer", data.get("allowCustomAnswer", True))),
                "allowCustomAnswer": bool(data.get("allow_custom_answer", data.get("allowCustomAnswer", True))),
                "resume_key": data.get("resume_key", data.get("resumeKey", "user_choice")),
                "resumeKey": data.get("resume_key", data.get("resumeKey", "user_choice")),
                "default_choice": data.get("default_choice", data.get("defaultChoice", ""))
            }
            is_decision_active = True
        else:
            decision_req = None
            is_decision_active = False
    else:
        decision_req = None
        is_decision_active = False

    needs_user_dec = is_decision_active

    # 2. Normalize actions / commands
    raw_actions = []
    plan_obj = data.get("plan") if isinstance(data.get("plan"), dict) else {}
    if "actions" in plan_obj and isinstance(plan_obj["actions"], list):
        raw_actions = plan_obj["actions"]
    elif "commands" in plan_obj and isinstance(plan_obj["commands"], list):
        raw_actions = plan_obj["commands"]
    elif "commands" in data and isinstance(data["commands"], list):
        raw_actions = data["commands"]
    elif "steps" in data and isinstance(data["steps"], list):
        raw_actions = [{"command": s} for s in data["steps"] if s]
    elif data.get("command"):
        raw_actions = [{"command": data.get("command")}]

    validated_actions = []
    for idx, item in enumerate(raw_actions):
        if isinstance(item, str):
            item = {"command": item}
        if not isinstance(item, dict):
            continue

        cmd_text = item.get("command") or item.get("parameters", {}).get("command", "")
        act_type = item.get("action_type") or item.get("actionType") or "command"
        
        # If shell command, validate safety
        if act_type == "command" and cmd_text:
            is_safe, reason = SmartSafetyGuard.validate_command_safety(cmd_text, fallback_tool)
            if not is_safe:
                return False, {}, f"Command safety check failed for '{cmd_text}': {reason}"

        cmd_lower = cmd_text.lower()
        is_install = any(k in cmd_lower for k in ("install", "add", "download", "setup", "upgrade"))
        req_approval = item.get("requires_approval", item.get("requiresApproval", is_install))

        params = item.get("parameters", {})
        if cmd_text and "command" not in params:
            params["command"] = cmd_text

        validated_actions.append({
            "action_type": act_type,
            "target": item.get("target", fallback_tool or "system"),
            "parameters": params,
            "command": cmd_text,
            "purpose": item.get("purpose", f"Run {cmd_text or act_type}"),
            "requires_approval": bool(req_approval),
            "expected_result": item.get("expected_result", item.get("expectedResult", "")),
            "failure_handling": item.get("failure_handling", item.get("failureHandling", "abort"))
        })

    # 3. Determine authoritative status
    status = data.get("status", "")
    if is_decision_active:
        status = "awaiting_user_decision"
    elif data.get("cannot_resolve") or data.get("blocker", {}).get("is_blocked"):
        status = "cannot_resolve"
    elif data.get("recovery_complete") or data.get("completion", {}).get("verified"):
        status = "completed"
    elif validated_actions:
        status = "ready"
    elif status == "awaiting_user_decision" and not is_decision_active:
        status = "ready" if validated_actions else "cannot_resolve"
    elif not status:
        status = "cannot_resolve"

    # Normalized proposal dictionary
    proposed_total = plan_obj.get("proposed_total_steps") or data.get("proposed_total_steps") or len(validated_actions)
    
    diag_summary = ""
    diag_obj = data.get("diagnosis")
    if isinstance(diag_obj, dict):
        diag_summary = diag_obj.get("summary") or diag_obj.get("root_cause") or ""
    elif isinstance(diag_obj, str):
        diag_summary = diag_obj
    else:
        diag_summary = data.get("explanation") or ""

    first_cmd = validated_actions[0]["command"] if validated_actions else data.get("command", "")
    v_cmd = data.get("verificationCommand") or data.get("verify") or f"{fallback_exec or fallback_tool} --version"

    normalized = {
        "status": status,
        "title": data.get("title") or (decision_req.get("question") if decision_req else f"Smart Fix: {fallback_tool or 'Workflow'}"),
        "diagnosis": diag_summary,
        "explanation": data.get("explanation") or diag_summary,
        "needs_user_decision": needs_user_dec,
        "needsUserDecision": needs_user_dec,
        "decision_request": decision_req,
        "decisionRequest": decision_req,
        "options": decision_req.get("choices", []) if decision_req else [],
        "choices": decision_req.get("choices", []) if decision_req else [],
        "commands": validated_actions,
        "actions": validated_actions,
        "proposed_total_steps": proposed_total,
        "command": first_cmd,
        "steps": [a["command"] for a in validated_actions if a.get("command")],
        "verificationCommand": v_cmd,
        "verifyCommand": v_cmd,
        "officialUrl": data.get("officialUrl") or data.get("official_url") or "",
        "cannot_resolve": (status == "cannot_resolve"),
        "recovery_complete": (status == "completed"),
        "final_report": data.get("final_report") or data.get("completion", {}).get("final_report", ""),
        "source": "ai",
        "resolutionType": "awaiting_user_decision" if needs_user_dec else ("single_command" if first_cmd else status)
    }

    return True, normalized, ""


# Backward-compatible validator function
def validate_ai_plan_response(
    response_raw: Any,
    extension_mgr: Any = None,
    tool_name: str = "",
    allow_oversized_split: bool = True
) -> Tuple[bool, dict, str]:
    """Preserves legacy validate_ai_plan_response contract for compatibility."""
    if isinstance(response_raw, dict):
        text = json.dumps(response_raw)
    else:
        text = str(response_raw)
    return parse_smart_response(text, fallback_tool=tool_name, fallback_exec=tool_name)
