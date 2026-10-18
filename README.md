 AI-Agent Workflow Security

**Detecting potential policy evasion across autonomous AI-agent workflows.**

An experimental cybersecurity project exploring how to identify and prevent AI agents from pursuing restricted objectives through alternative tools, resources, or delegated agents after an access denial.

Overview:

AI agents can interact with APIs, read files, browse websites, and delegate tasks to other agents. Traditional security controls often evaluate individual actions independently, which can make it difficult to identify suspicious patterns across an entire workflow.

This project explores a denial-aware approach to AI-agent security. It records structured action events, applies deterministic resource policies, and correlates subsequent actions with previously denied objectives.

The goal is to investigate whether workflow-level detection can identify potential policy evasion that basic per-action checks may miss, while allowing legitimate tasks to continue.

**Project status:** Early research prototype. The current implementation uses synthetic scenarios and simple deterministic rules. It is not a production-ready security product.

Problem Statement:

Consider an AI agent that requests access to a restricted payroll resource and receives a denial.

Instead of stopping, the agent attempts to access equivalent information through another tool or delegates the task to another agent.

An individual action may appear reasonable when considered in isolation. However, the sequence of events may indicate an attempt to circumvent the original restriction.

This project investigates how security systems can correlate those events, preserve the history of denied objectives, and prevent subsequent actions associated with those objectives.

Core Objectives:

- Represent AI-agent actions as structured, validated events.
- Enforce explicit resource restrictions through deterministic policy checks.
- Track objectives that have previously received an access denial.
- Identify potential policy-evasion patterns across multiple actions.
- Distinguish restricted workflows from unrelated legitimate tasks.
- Evaluate workflow-aware enforcement against simpler security baselines.
- Build toward an explainable and reproducible AI-agent security framework.

## Current Features

### 1. Structured Event Schema

Uses Pydantic to validate action-event records containing fields such as:

- Task and objective identifiers
- Agent and parent-agent identifiers
- Tool and action names
- Resource identifiers
- Event sequence numbers
- Action status and denial reason

### 2. Deterministic Policy Engine

Applies explicit resource restrictions and returns an allow-or-deny decision.

The initial policy implementation uses a canonical resource name and a configured denylist. It is a demonstration policy rather than a complete identity-based authorization framework.

### 3. Workflow Correlation

Examines recorded events to identify tool switching or changes in the acting agent following a denial involving the same canonical resource.

The correlation engine produces structured alerts containing the relevant steps, agents, tools, and reasons.

### 4. Denial-Aware Workflow Guard

Maintains an in-memory record of previously denied objectives within a task.

Subsequent actions associated with a previously denied objective can be blocked, even when the requested alternative resource is not directly included in the initial resource denylist.

The current implementation uses an explicitly supplied objective identifier. A real integration would need to derive objective identity from a trusted task controller rather than allowing an agent to define it freely.

### 5. Synthetic Workflow Simulation

Includes a simulator for exploring the interaction between individual resource checks and workflow-level restrictions.

The simulation uses synthetic data and does not access real corporate systems, credentials, or sensitive resources.

### 6. Automated Tests

Uses pytest to test basic policy decisions, correlation behaviour, tool switching, delegated-agent activity, and objective-level blocking.

The test suite is intended to expand as additional threat scenarios and evaluation methods are implemented.

## Architecture

The current prototype is organised into separate modules:

```text
agent-workflow-security/
├── src/
│   └── workflow_security/
│       ├── __init__.py
│       ├── events.py
│       ├── policy.py
│       ├── correlator.py
│       ├── guard.py
│       └── simulator.py
├── tests/
│   └── test_workflow.py
├── data/
│   └── scenarios/
├── docs/
├── README.md
├── requirements.txt
└── .gitignore
```

### Component Responsibilities

| Component | Responsibility |
|---|---|
| `events.py` | Defines structured action events using Pydantic. |
| `policy.py` | Evaluates individual actions against configured resource restrictions. |
| `correlator.py` | Identifies suspicious relationships between recorded actions following a denial. |
| `guard.py` | Maintains denied-objective state and evaluates subsequent actions. |
| `simulator.py` | Runs controlled synthetic security scenarios. |
| `tests/test_workflow.py` | Validates the expected behaviour of the current components. |

## Technology Stack

- **Language:** Python
- **Data validation:** Pydantic
- **API framework planned:** FastAPI
- **Testing:** pytest
- **Version control:** Git and GitHub

FastAPI is included in the planned technology stack but is not yet integrated into the current prototype.

## Getting Started

### Prerequisites

- Python 3.10 or newer, with a version supported by the selected dependencies
- Git
- PowerShell on Windows, or an equivalent terminal
- Visual Studio Code or another Python-compatible editor

### 1. Clone the Repository

After the project has been published to GitHub, clone it using its repository URL:

```bash
git clone https://github.com/mdbaasim/agent-workflow-security.git
cd agent-workflow-security
```

The command above clones this repository to your local machine.

### 2. Create a Virtual Environment

On Windows PowerShell:

```powershell
py -m venv .venv
```

Activate the environment if your system permits PowerShell script activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

If script activation is restricted, you can invoke the environment's Python executable directly instead.

### 3. Install Dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Run the Automated Tests

```powershell
$env:PYTHONPATH = "$PWD\src"

.\.venv\Scripts\python.exe -m pytest -q
```

The initial seven-test suite was designed to validate the prototype's basic policy and correlation behaviour. Run the current tests and inspect their results before relying on any previously observed test count.

### 5. Run the Simulator

```powershell
$env:PYTHONPATH = "$PWD\src"

.\.venv\Scripts\python.exe -m workflow_security.simulator
```

Review the output to inspect the simulated security decisions and workflow analysis.

## Research and Evaluation Plan

The next stage is to evaluate whether workflow-level correlation offers meaningful benefits over simpler security controls.

### Baselines

1. **Unprotected agent:** No additional protection beyond the simulated agent's normal behaviour.
2. **Per-action policy checks:** Every action is evaluated independently against the configured resource policy.
3. **Workflow-aware guard:** Individual policy checks are combined with denial-aware objective tracking.

### Planned Threat Scenarios

- Switching tools after an access denial
- Repeating a request with modified parameters
- Delegating a restricted request to another agent
- Using alternate paths or aliases for the same protected resource
- Splitting an operation across multiple actions
- Attempting to transfer restricted information through another channel
- Continuing an operation through legitimate alternative workflows

These scenarios will be implemented and validated incrementally. They are planned evaluation cases, not a claim that all of them are already detected.

### Planned Metrics

- Detection rate by scenario category
- False-positive and false-block rates
- Legitimate task-completion rate
- Number of actions between an evasive attempt and detection
- Additional enforcement latency

Evaluation will include benign retries and held-out scenario combinations. Results will be reported only after experiments have been run.

## Future Roadmap

### Phase 1: Core Security Logic
- Refine event validation and policy decisions.
- Improve objective tracking and event correlation.
- Expand the automated test suite.

### Phase 2: Evaluation
- Build repeatable attack and benign workflow scenarios.
- Compare per-action and workflow-aware baselines.
- Measure detection effectiveness and false positives.

### Phase 3: AI and Machine Learning
- Extract behavioural features from event sequences.
- Evaluate rule-based detection against a trained classifier.
- Test performance on held-out scenarios.
- Add AI-assisted explanations grounded in recorded evidence.

### Phase 4: Visualization and Integration
- Build an interactive event timeline and investigation dashboard.
- Expose a service API where appropriate.
- Integrate simulated agents and tools.
- Investigate integration with cloud infrastructure and enterprise identity systems.

### Phase 5: Deployment and Open Development
- Add reproducible deployment instructions.
- Introduce continuous integration and dependency checks.
- Document supported integrations and limitations.
- Evaluate whether the implementation is suitable for a broader open-source release.

## Security Design Principles

The project follows these intended design principles:

- **Independent enforcement:** AI-generated explanations must not override deterministic authorization rules.
- **Least privilege:** Actions should receive only the permissions required for their approved task.
- **Auditability:** Security decisions should be traceable to recorded events and policy outcomes.
- **Evidence-based alerts:** Detection should indicate potential policy evasion rather than claim certainty about an agent's intent.
- **Safe experimentation:** Initial scenarios use synthetic data and isolated simulations.
- **Reproducibility:** Tests and evaluation scenarios should be repeatable by other developers.

These principles describe the intended architecture. They do not imply that every production security requirement has already been implemented.

## Limitations

This is an early-stage research prototype.

- It does not yet connect to real AI-agent execution environments.
- Resource restrictions are basic and do not constitute comprehensive authorization.
- Objective tracking currently depends on identifiers supplied in the event records.
- The correlation engine uses straightforward rules rather than a trained ML model.
- Persistence, distributed coordination, enterprise identity integration, and production-grade monitoring are not yet implemented.
- No claims of production readiness or superiority over commercial systems have been established.

## Intended Audience

This project may be useful to developers, security engineers, researchers, and students interested in:

- AI-agent security
- Machine learning for behavioural analysis
- Enterprise authorization and access control
- Distributed systems and tool orchestration
- Explainable security monitoring
- Cloud and infrastructure security

## Contributing

Contributions and technical feedback are welcome as the prototype develops.

Potential areas for contribution include event modelling, testing, policy design, simulated threat scenarios, correlation algorithms, documentation, and evaluation methodology.

Any future contribution guidelines and licensing terms will be documented before the project is opened for external contributions.

## License

A license has not yet been selected. Until a license is added to the repository, reuse and redistribution permissions should not be assumed.

## Disclaimer

This project is for educational, research, and defensive cybersecurity purposes. All current demonstrations are synthetic. The implementation is experimental and should not be used to protect production systems without substantial additional engineering, testing, and security review.

---

**Built as a learning and research project exploring safer autonomous AI workflows.**
