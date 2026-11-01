IntentFence: AI Agent Workflow Security Copilot
Meta Global AI Developer Hackathon 2026

Live Cloud Demo: https://agent-workflow-security.vercel.app

IntentFence is a denial-aware cybersecurity copilot designed to detect and block autonomous AI agents from evading access restrictions by switching tools, views, or delegating tasks after a sensitive operation is denied.

============================================================
Key Distinction: Stateless Policy vs. Objective-Aware Guard
============================================================

1. Baseline Stateless Policy:
- Evaluates each action in complete isolation.
- Vulnerability: When an agent is denied access to a restricted resource (e.g., "payroll_records" via file_read), the agent immediately replans and calls a different tool (e.g., sql_query on "payroll_view"). The baseline check allows the second call because the tool and raw string differ, enabling unauthorized bypass.

2. IntentFence Objective-Aware Guard:
- Binds actions to a stateful task and business objective.
- Protection: When an action under an objective is denied, IntentFence permanently records a denial tombstone. Any subsequent action attempting to satisfy that same objective—whether through an alternative tool, alternative resource alias, or delegated sub-agent—is automatically blocked at the pre-execution boundary.
- Granularity: Unrelated business objectives are unaffected and continue executing without false-positive lockouts.

============================================================
Live Comparison Example
============================================================

Scenario: data/scenarios/alternative_route.json

| Step | Action Attempt | Baseline Policy | IntentFence Guard | Security Outcome |
|---|---|---|---|---|
| Step 1 | Read restricted payroll records | DENIED | DENIED | Policy restriction enforced; objective marked denied |
| Step 2 | Execute SQL view on payroll within same objective | ALLOWED | BLOCKED | IntentFence blocks tool-switch evasion |
| Step 3 | Read public documentation under separate objective | ALLOWED | ALLOWED | Unrelated objective permitted normally |

============================================================
Current Platform Features
============================================================

- Objective-Level Enforcement: Tracks agent actions across multi-step execution graphs.
- Correlation Engine: Automatically detects tool-switching and delegated child-agent evasions.
- Guarded Tool Proxy: Intercepts callable tools before execution, raising SecurityEnforcementError on blocked objectives.
- Interactive Security Sandbox: Evaluators and hackathon judges can enter custom objective IDs, agent IDs, and tools to test live pre-execution interception.
- One-Click Audit Export: Download complete SQLite telemetry directly as formatted JSON or CSV files from the web UI.
- Zero-Cost Local AI Copilot: Uses Meta Llama 3.2 (3B) via Ollama to generate structured SecOps advisory explanations. Enforcement logic remains strictly deterministic.
- Interactive Pastel Dashboard: Real-time telemetry streaming via Server-Sent Events (SSE) on port 8001.
- SQLite Persistence: Complete audit trails stored in data/intentfence.db (automatically adapts to /tmp on serverless hosts).
- Five Scenarios Included: Alternative route, tool switch, delegated agent, benign workflow, and repeated attempt.
- Cloud Serverless Ready: Native Vercel deployment support via vercel.json and api/index.py.

============================================================
Project Structure
============================================================

- api/
  - index.py: Vercel serverless entrypoint for cloud deployment.
- vercel.json: Vercel deployment configuration.
- src/workflow_security/
  - events.py: Pydantic schemas for action events and security outcomes.
  - policy.py: Canonical resource mapping and baseline access policies.
  - guard.py: Objective-level stateful denial tracker.
  - correlator.py: Pattern matcher for tool-switching and delegation evasion.
  - ai_analyzer.py: Local Ollama interface for Meta Llama 3.2 (3B).
  - agent_adapter.py: GuardedToolProxy wrapping tools for runtime enforcement.
  - db.py: SQLite schema and persistence functions (with cloud serverless fallback).
  - web_app.py: FastAPI web application with SSE streaming, sandbox tester, and audit export.
  - simulator.py: Batch runner for synthetic scenario evaluation.
- tests/
  - test_workflow.py: Unit tests for core algorithms and models.
  - test_realtime_and_adapter.py: Integration tests for adapter, sandbox, export, and streaming endpoints.
- data/
  - intentfence.db: SQLite database of runs and security telemetry.
  - scenarios/: 5 preconfigured attack and benign workflow test fixtures.
- docs/
  - architecture.md: Full architectural specification.
  - project_guide.md: Comprehensive how-to-work guide.
- run_dashboard.py: Launcher for the interactive web dashboard on port 8001.
- requirements.txt: Python package dependencies.
- pytest.ini: Pytest configuration with pythonpath set to src.

============================================================
How to Work on the Project Locally
============================================================

1. Prerequisites:
- Python 3.10+ (tested on Python 3.14).
- Ollama running locally with Meta Llama 3.2 (3B):
  - Start daemon: ollama serve
  - Pull model: ollama pull llama3.2:3b

2. Running Automated Tests:
- Command: pytest
- Result: 20 passed in under 3 seconds.

3. Running the Web Dashboard:
- Command: python run_dashboard.py
- Open browser: http://127.0.0.1:8001
- Available features:
  - Top navigation bar (Dashboard, Developer Sandbox, Protection, Audit).
  - Scenario dropdown selector.
  - Live Server-Sent Events simulation stream.
  - Interactive Security Sandbox to test custom actions live.
  - One-Click Telemetry Export (JSON and CSV).
  - Real-time Meta Llama 3.2 copilot security advisory.

4. Using the Guarded Tool Proxy in Code:
```python
from workflow_security.agent_adapter import GuardedToolProxy
from workflow_security.guard import WorkflowGuard
from workflow_security.events import ActionEvent

guard = WorkflowGuard(restricted_resources=["payroll_records"])
proxy = GuardedToolProxy(guard=guard)

def my_file_tool(path: str):
    return f"reading {path}"

proxy.register_tool("file_reader", my_file_tool)

event = ActionEvent(
    task_id="task-01",
    objective_id="export-payroll",
    agent_id="agent-1",
    tool="file_reader",
    resource="payroll_records",
    status="REQUESTED"
)

result = proxy.execute(event, path="payroll_records")
```

============================================================
Deploying to Vercel
============================================================

IntentFence is preconfigured for zero-configuration deployment to Vercel:

1. Import Repository:
- Go to https://vercel.com/new
- Select your GitHub repository: mdbaasim/agent-workflow-security

2. Deployment Settings:
- Framework Preset: Other
- Root Directory: ./
- Build Command: (leave empty)
- Output Directory: (leave empty)

3. Automatic Configuration:
- Vercel automatically detects vercel.json and builds api/index.py with @vercel/python.
- The SQLite persistence layer automatically detects the VERCEL environment variable and writes to /tmp/intentfence.db to comply with serverless storage requirements.

============================================================
License and Disclaimer
============================================================
Developed for the Meta Global AI Developer Hackathon 2026.
Educational and research prototype demonstrating defense-in-depth against autonomous agent evasion attacks.
