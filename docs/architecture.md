\# AI-Agent Workflow Security Architecture



\## Overview



This project is a research prototype that explores how to detect and prevent AI agents from bypassing access restrictions by switching tools, delegating tasks, or using alternative routes to reach restricted resources.



\## Architecture



```mermaid

flowchart TD

&#x20;   A\[AI Agent Action] --> B\[Action Event]

&#x20;   B --> C\[Policy Engine]

&#x20;   C --> D{Policy Decision}

&#x20;   D -->|Allowed| E\[Workflow Guard]

&#x20;   D -->|Denied| F\[Record Denial]

&#x20;   F --> G\[Workflow Correlator]

&#x20;   E --> H{Objective Previously Denied?}

&#x20;   H -->|No| I\[Allow Action]

&#x20;   H -->|Yes| J\[Block Action]

&#x20;   G --> K\[Detect Suspicious Sequences]

&#x20;   K --> L\[Security Alert]

&#x20;   I --> M\[Audit Trail]

&#x20;   J --> M

&#x20;   L --> M

```



\## Main Components



\### 1. Action Events

Represent tool calls and workflow activity with fields such as task ID, objective ID, agent ID, tool, resource, and action status.



\### 2. Policy Engine

Evaluates individual actions against configured resource restrictions.



\### 3. Workflow Guard

Tracks denied objectives and blocks subsequent actions associated with those objectives.



\### 4. Workflow Correlator

Examines sequences of events to identify possible policy evasion, including tool switching and delegation after a denial.



\### 5. Simulator and Tests

Demonstrate the prototype's behavior and verify key security scenarios.



\## Security Principle



A denied action should not automatically end the analysis. The system should examine subsequent actions within the same objective to detect attempts to reach restricted resources through alternative paths.



\## Current Limitations



\- The prototype uses simulated events rather than a live agent framework.

\- Policy decisions use simple resource restrictions.

\- Objective identity and trusted approval require stronger enforcement in a real deployment.

\- Detection rules are currently deterministic; machine-learning-assisted analysis is a future extension.



\## Research Direction



Future work includes stronger identity and approval controls, richer workflow correlation, integration with agent frameworks, and evaluation against realistic attack scenarios.

