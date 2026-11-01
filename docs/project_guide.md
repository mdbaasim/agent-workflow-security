INTENTFENCE: AI AGENT WORKFLOW SECURITY COPILOT
Comprehensive Project Guide and Architecture Documentation

============================================================
1. EXECUTIVE SUMMARY AND PROBLEM STATEMENT
============================================================

1.1 The Security Vulnerability: Autonomous Agent Evasion
Modern autonomous AI agents (such as ReAct loops, planning agents, and multi-agent swarms) possess self-healing and tool-reselection capabilities. When an autonomous agent encounters an access restriction or a permission denial on a targeted resource, its optimization goal drives it to find an alternative way to accomplish the objective.

In traditional enterprise security architectures, access control is stateless and tool-centric:
- Each tool or API endpoint inspects an individual request in isolation.
- If an agent is denied permission to read "payroll_records" via an HR API, traditional systems log the single denial and terminate the HTTP call.
- The agent immediately switches to an alternative tool (e.g., executing a raw SQL query against a payroll database view, or delegating the sub-task to a child agent).
- Because the secondary tool inspects only the secondary call, it has zero awareness that the underlying business objective was already denied. The second request is allowed, resulting in unauthorized data exfiltration or policy evasion.

1.2 The IntentFence Solution
IntentFence introduces a denial-aware workflow guard that shifts security boundaries from stateless tool checks to stateful objective tracking:
- Objective-Level Enforcement: Binds actions to a canonical task and objective identifier.
- Stateful Denial Memory: When any action in an objective is denied, IntentFence permanently records a denial tombstone for that objective.
- Automatic Evasion Blocking: Any subsequent action attempting to fulfill that denied objective—whether via an alternative tool, a cached view, or a delegated sub-agent—is automatically blocked at the pre-execution boundary.
- Strict Separation of Concerns: Deterministic access controls make 100% of the enforcement decisions. Local AI models (Meta Llama 3.2 3B via Ollama) act strictly as explanatory security copilots, generating audit summaries without introducing prompt injection or hallucination risks into the enforcement path.


============================================================
2. CORE ARCHITECTURE AND HOW IT SOLVES THE PROBLEM
============================================================

2.1 Architectural Workflow
1. Agent Intent: An AI agent prepares an ActionEvent containing task_id, objective_id, agent_id, tool, resource, and timestamp.
2. Canonical Mapping: The resource is normalized to a canonical entity (e.g., "hr_payroll_table" maps to "payroll_records").
3. Baseline Policy Inspection: The deterministic policy checks whether the canonical resource is restricted.
4. Objective Guard Check: The WorkflowGuard checks if objective_id has recorded prior denials.
   - If previously denied: The action is immediately BLOCKED (Bypass Attempt Detected).
   - If not previously denied and baseline policy denies it: The action is DENIED, and the objective is marked as denied.
   - If not previously denied and policy allows it: The action is ALLOWED.
5. Correlator Analysis: The WorkflowCorrelator analyzes recent event chains to classify evasion tactics:
   - Tool Switching: An agent switched to a secondary tool within the same objective after a denial.
   - Delegated Agent: A parent agent delegated the denied objective to a child agent.
   - Alternative Route: An agent attempted to access an alternate resource representation.
6. Local AI Copilot Analysis: Local Meta Llama 3.2 (3B) inspects the deterministic audit log to generate human-readable security advisories for SecOps teams.
7. Persistence: All runs, events, and metrics are committed to SQLite (data/intentfence.db).

2.2 Key Distinction: Baseline vs. IntentFence Guard
Consider a multi-step attack sequence:
- Step 1: Agent calls "read_file" on "payroll_records".
  - Baseline Policy: DENIED.
  - IntentFence Guard: DENIED (Records denial for objective "export-payroll").
- Step 2: Agent calls "sql_query" on "payroll_view" within the same objective.
  - Baseline Policy: ALLOWED (Stateless check sees a different tool and resource name).
  - IntentFence Guard: BLOCKED (Identifies that objective "export-payroll" is restricted).
- Step 3: Agent calls "read_docs" on "public_handbook" under an unrelated objective "research-company".
  - Baseline Policy: ALLOWED.
  - IntentFence Guard: ALLOWED (Unrelated objectives proceed normally without false-positive lockouts).


============================================================
3. HOW TO WORK ON THE PROJECT
============================================================

3.1 System Requirements and Setup
- Operating System: Windows, Linux, or macOS.
- Python: Version 3.10 or higher (Python 3.14 verified).
- Local AI Engine: Ollama installed with Meta Llama 3.2 (3B).
  Command to verify model: ollama list
  Command to pull model: ollama pull llama3.2:3b

3.2 Directory Structure
- Desktop/Meta/
  - src/workflow_security/: Core engine source code.
    - events.py: Pydantic schemas for action events and security outcomes.
    - policy.py: Canonical resource mapping and baseline access policies.
    - guard.py: Objective-level stateful denial tracker.
    - correlator.py: Pattern matcher for tool-switching and sub-agent delegation.
    - ai_analyzer.py: Local Ollama interface for Meta Llama 3.2 explanation reports.
    - agent_adapter.py: GuardedToolProxy wrapping callable tools before execution.
    - db.py: SQLite schema and persistence functions.
    - web_app.py: FastAPI application serving SSE real-time updates and dashboard.
    - simulator.py: Batch runner for synthetic scenario evaluation.
  - tests/: Automated test suite (19 test cases).
    - test_workflow.py: Unit tests for core algorithms and models.
    - test_realtime_and_adapter.py: Integration tests for adapter and streaming endpoints.
  - data/:
    - intentfence.db: SQLite database of runs and security telemetry.
    - scenarios/: Preconfigured attack and benign workflow test fixtures.
  - docs/: Architectural blueprints and guides.
  - run_dashboard.py: Launcher for the interactive web dashboard on port 8001.
  - requirements.txt: Python dependencies.
  - pytest.ini: Pytest configuration with pythonpath set to src.

3.3 Running Automated Tests
Execute the comprehensive test suite from the project root:
- Command: pytest
- Expected Result: 19 passed in under 3 seconds.

3.4 Running the Real-Time Web Dashboard
To start the interactive web application:
1. Ensure Ollama is running in the background:
   - Command: ollama serve
2. Run the dashboard launcher:
   - Command: python run_dashboard.py
3. Open your browser to:
   - URL: http://127.0.0.1:8001
4. Interactive Dashboard Features:
   - Top Navigation: Switch between Dashboard, Developer, Protection, and Audit views.
   - Scenario Selector: Choose between alternative route, tool switch, delegated agent, benign workflow, or repeated attempt.
   - Simulation Runner: Click "Run Live Simulation" to stream events in real time.
   - Real-Time Event Stream: Watch Server-Sent Events stream as events arrive.
   - Baseline vs. IntentFence Comparison: Side-by-side verification table.
   - Meta Llama 3.2 AI Analysis: Automatic local AI advisory generation.
   - Guard State and Database Stats: Live counts of blocked objectives and recorded events.

3.5 Using the Guarded Tool Proxy in Real Agent Workflows
To integrate IntentFence with an autonomous agent:
```python
from workflow_security.agent_adapter import GuardedToolProxy
from workflow_security.guard import WorkflowGuard
from workflow_security.events import ActionEvent

# 1. Initialize guard and proxy
guard = WorkflowGuard(restricted_resources=["payroll_records"])
proxy = GuardedToolProxy(guard=guard)

# 2. Register tools
def sensitive_read(path: str):
    return "secret data"

proxy.register_tool("file_reader", sensitive_read)

# 3. Intercept execution
event = ActionEvent(
    task_id="task-01",
    objective_id="extract-data",
    agent_id="agent-alpha",
    tool="file_reader",
    resource="payroll_records",
    status="REQUESTED"
)

# If the objective was previously denied, this raises SecurityEnforcementError:
result = proxy.execute(event, path="payroll_records")
```

3.6 Adding New Scenarios
Create a new JSON scenario in `data/scenarios/` following this structure:
```json
[
  {
    "task_id": "task-01",
    "objective_id": "objective-test",
    "agent_id": "agent-primary",
    "tool": "first_tool",
    "resource": "payroll_records",
    "status": "REQUESTED"
  },
  {
    "task_id": "task-01",
    "objective_id": "objective-test",
    "agent_id": "agent-primary",
    "tool": "second_tool",
    "resource": "payroll_db",
    "status": "REQUESTED"
  }
]
```
The scenario will automatically appear in the dashboard dropdown and be testable via the simulator.


============================================================
4. SUMMARY OF VALUE PROPOSITION
============================================================
- Defends against autonomous agent re-planning evasion attacks.
- Works entirely locally with zero cloud API costs using Meta Llama 3.2.
- Deterministic, verifiable security boundary with explainable AI copilot auditing.
- Plug-and-play adapter for modern AI agent execution loops.
