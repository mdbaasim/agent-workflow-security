"""Script to generate IntentFence Project Documentation as a formatted DOCX file."""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    """Set background color of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tc_pr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner padding for table cells."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)

def create_document():
    doc = Document()
    
    # Page setup: 1-inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Base font styling
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Calibri'
    font.size = Pt(11)
    font.color.rgb = RGBColor(0x33, 0x41, 0x55) # Slate 700

    # Document Header / Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    run_title = title_p.add_run("IntentFence: AI Agent Workflow Security Copilot")
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A) # Slate 900

    subtitle_p = doc.add_paragraph()
    subtitle_p.paragraph_format.space_before = Pt(0)
    subtitle_p.paragraph_format.space_after = Pt(18)
    run_sub = subtitle_p.add_run("Meta Global AI Developer Hackathon 2026 | Technical Architecture & Operations Guide")
    run_sub.font.size = Pt(13)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(0x47, 0x55, 0x69) # Slate 600

    # Helper function for Section Headings (No # used)
    def add_heading_1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.size = Pt(15)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A) # Blue 900
        return p

    def add_heading_2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B) # Slate 800
        return p

    def add_bullet(text, bold_prefix=""):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        if bold_prefix:
            run_b = p.add_run(bold_prefix)
            run_b.bold = True
            run_b.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
        run_t = p.add_run(text)
        run_t.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
        return p

    def add_code_block(code_text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.left_indent = Inches(0.2)
        run = p.add_run(code_text)
        run.font.name = 'Consolas'
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
        return p

    # ----------------------------------------------------
    # SECTION 1: Problem Statement
    # ----------------------------------------------------
    add_heading_1("1. Problem Statement: Autonomous Agent Evasion")
    
    p = doc.add_paragraph()
    p.add_run(
        "Modern autonomous AI agents (such as ReAct loops, planning agents, and multi-agent systems) "
        "have become standard tools for enterprise automation. These agents do not follow rigid, hard-coded scripts; "
        "instead, they possess dynamic goal-seeking loops that continuously evaluate outcomes and replan if a step fails."
    )

    p2 = doc.add_paragraph()
    p2.add_run(
        "While this autonomy makes AI agents resilient against transient errors, it exposes a critical enterprise security "
        "vulnerability: Autonomous Policy Evasion. When an agent attempts an action that violates an access control policy "
        "and is denied, its optimization loop immediately searches for alternative tools or indirect paths to achieve the original objective."
    )

    add_heading_2("Why Traditional Access Controls Fail")
    add_bullet("Traditional access control gateways inspect each HTTP request or tool call independently. They evaluate whether the immediate caller has permission for the immediate endpoint, with zero awareness of previous requests.", "Stateless Tool-Centric Inspection: ")
    add_bullet("If an agent is denied permission to read 'payroll_records' via a restricted HR tool, the agent replans and issues a raw SQL query or reads an unmasked database view ('payroll_view'). Because the database tool sees a new query and distinct resource string, it permits the request.", "Tool Switching Evasion: ")
    add_bullet("An agent blocked on an action can delegate the prohibited sub-task to a child agent or worker agent. The worker agent begins with a clean context and bypasses single-agent restrictions.", "Delegated Agent Evasion: ")

    # ----------------------------------------------------
    # SECTION 2: The IntentFence Solution
    # ----------------------------------------------------
    add_heading_1("2. The IntentFence Solution: Denial-Aware Workflow Guard")
    
    p = doc.add_paragraph()
    p.add_run(
        "IntentFence introduces an objective-aware security layer that tracks agent actions across the lifecycle of an entire task. "
        "Rather than evaluating tool calls in isolation, IntentFence binds security boundaries to the business objective."
    )

    add_heading_2("Key Security Pillars")
    add_bullet("Every action event is stamped with a canonical task_id and objective_id in addition to the tool and resource names.", "Objective-Level Tracking: ")
    add_bullet("When any action under an objective encounters an access denial, IntentFence permanently records a denial tombstone for that objective_id.", "Denial Memory: ")
    add_bullet("Any subsequent action attempting to satisfy that denied objective is automatically blocked at the pre-execution boundary, regardless of which tool is used.", "Pre-Execution Boundary: ")
    add_bullet("The WorkflowCorrelator tracks execution graphs to detect specific evasion signatures such as rapid tool switching or delegating denied goals to child agents.", "Correlation Engine: ")
    add_bullet("Actions under separate, benign objectives continue uninterrupted, preventing false-positive operational lockouts.", "Targeted Granularity: ")
    add_bullet("All access decisions (Allow, Deny, Block) are enforced by 100% deterministic Python rules. A local Meta Llama 3.2 (3B) model runs via Ollama strictly as an explanatory copilot, summarizing violations for human SecOps teams without prompt-injection risk.", "Strict Deterministic Boundary: ")

    # ----------------------------------------------------
    # SECTION 3: Live Verification Matrix
    # ----------------------------------------------------
    add_heading_1("3. Verification Matrix: Baseline Policy vs. IntentFence Guard")

    p = doc.add_paragraph()
    p.add_run("The following table illustrates a multi-step sequence demonstrating how IntentFence blocks evasion while allowing legitimate work to proceed:")

    # Create Table
    table = doc.add_table(rows=4, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    headers = ["Step", "Action Attempt", "Baseline Policy", "IntentFence Guard", "Security Outcome"]
    widths = [Inches(0.6), Inches(1.8), Inches(1.1), Inches(1.2), Inches(1.8)]

    # Style Header Row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        hdr_cells[i].width = widths[i]
        set_cell_background(hdr_cells[i], "1E3A8A") # Navy Blue
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=100, right=100)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.bold = True
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            run.font.size = Pt(9.5)

    data = [
        ("Step 1", "Read restricted payroll records via file_reader", "DENIED", "DENIED", "Policy restriction enforced; objective marked denied."),
        ("Step 2", "Query payroll view via sql_query tool (same objective)", "ALLOWED", "BLOCKED", "IntentFence detects evasion and blocks pre-execution."),
        ("Step 3", "Read public handbook under separate objective", "ALLOWED", "ALLOWED", "Unrelated objective permitted without false-positive lockout.")
    ]

    for row_idx, row_data in enumerate(data, start=1):
        row_cells = table.rows[row_idx].cells
        bg_color = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, cell_value in enumerate(row_data):
            row_cells[col_idx].text = cell_value
            row_cells[col_idx].width = widths[col_idx]
            set_cell_background(row_cells[col_idx], bg_color)
            set_cell_margins(row_cells[col_idx], top=100, bottom=100, left=100, right=100)
            p = row_cells[col_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if col_idx != 0 else WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                run.font.size = Pt(9)
                if cell_value in ("BLOCKED", "DENIED"):
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0xBE, 0x12, 0x3C) # Rose 700
                elif cell_value == "ALLOWED":
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(0x04, 0x78, 0x57) # Emerald 700

    # ----------------------------------------------------
    # SECTION 4: How to Work on the Project
    # ----------------------------------------------------
    add_heading_1("4. How to Work on the Project")

    add_heading_2("4.1 Prerequisites and Environment")
    add_bullet("Python 3.10 or higher (tested and verified on Python 3.14).", "Python Version: ")
    add_bullet("Ollama running locally with Meta Llama 3.2 (3B) installed. Run 'ollama pull llama3.2:3b' to download the model.", "Local AI Copilot: ")
    add_bullet("Virtual environment in '.venv' with dependencies from requirements.txt (fastapi, uvicorn, pydantic, pytest, requests, python-docx).", "Dependencies: ")

    add_heading_2("4.2 Running the Automated Test Suite")
    p = doc.add_paragraph()
    p.add_run("IntentFence includes a comprehensive test suite covering the policy engine, guard memory, correlation engine, local AI integration, and the real-time SSE streaming adapter.")
    add_code_block("pytest")
    p = doc.add_paragraph()
    p.add_run("Result: 19 passed unit and integration tests executing in under 3 seconds.")

    add_heading_2("4.3 Starting the Real-Time Web Dashboard")
    p = doc.add_paragraph()
    p.add_run("The interactive dashboard provides a visual command center for evaluating AI agent runs in real time:")
    add_bullet("Start Ollama in a separate terminal: 'ollama serve'", "Step 1: ")
    add_bullet("Launch the dashboard runner from the project root: 'python run_dashboard.py'", "Step 2: ")
    add_bullet("Open your browser to: http://127.0.0.1:8001", "Step 3: ")

    add_heading_2("4.4 Web Dashboard Features")
    add_bullet("Centered pill navigation providing instant access to Dashboard, Developer, Protection, and Audit telemetry views.", "Top Navigation: ")
    add_bullet("Select between 5 preconfigured scenarios (Alternative Route, Tool Switch, Delegated Agent, Benign Workflow, Repeated Attempt).", "Scenario Selector: ")
    add_bullet("Watch events stream in real time via Server-Sent Events (SSE) with live status chips.", "Live Event Stream: ")
    add_bullet("Direct side-by-side verification table comparing stateless policy with the IntentFence Guard.", "Comparison Matrix: ")
    add_bullet("Automated post-run analysis powered by local Meta Llama 3.2 (3B), providing structured security findings.", "Meta Llama 3.2 Security Advisory: ")
    add_bullet("Live display of active blocked objectives, total events, and SQLite telemetry.", "System Metrics: ")

    add_heading_2("4.5 Using the GuardedToolProxy in Python Agent Code")
    p = doc.add_paragraph()
    p.add_run("Developers can integrate IntentFence into their own autonomous agents by wrapping tools with the GuardedToolProxy:")
    add_code_block(
        "from workflow_security.agent_adapter import GuardedToolProxy\n"
        "from workflow_security.guard import WorkflowGuard\n"
        "from workflow_security.events import ActionEvent\n\n"
        "# 1. Initialize guard and proxy\n"
        "guard = WorkflowGuard(restricted_resources=['payroll_records'])\n"
        "proxy = GuardedToolProxy(guard=guard)\n\n"
        "# 2. Register real tool callables\n"
        "def query_database(query: str):\n"
        "    return 'database_query_result'\n\n"
        "proxy.register_tool('sql_tool', query_database)\n\n"
        "# 3. Intercept execution\n"
        "event = ActionEvent(\n"
        "    task_id='task-01',\n"
        "    objective_id='export-payroll',\n"
        "    agent_id='agent-1',\n"
        "    tool='sql_tool',\n"
        "    resource='payroll_records',\n"
        "    status='REQUESTED'\n"
        ")\n\n"
        "# If the objective was previously denied, raises SecurityEnforcementError:\n"
        "result = proxy.execute(event, query='SELECT * FROM payroll')"
    )

    add_heading_2("4.6 SQLite Persistence and Audit Telemetry")
    p = doc.add_paragraph()
    p.add_run(
        "All simulation runs, event sequences, and security verdicts are persistently logged into "
        "data/intentfence.db using SQLite. SecOps teams can query this database for forensic auditing and compliance reporting."
    )

    # ----------------------------------------------------
    # SECTION 5: Repository Layout
    # ----------------------------------------------------
    add_heading_1("5. Repository File Reference")

    add_bullet("Pydantic schema definitions for ActionEvent and security models.", "src/workflow_security/events.py: ")
    add_bullet("Canonical resource normalization and deterministic policy restrictions.", "src/workflow_security/policy.py: ")
    add_bullet("Stateful objective-level denial memory and action enforcement.", "src/workflow_security/guard.py: ")
    add_bullet("Multi-event correlation engine detecting tool switches and delegation.", "src/workflow_security/correlator.py: ")
    add_bullet("Zero-cost local Ollama connector for Meta Llama 3.2 advisory reports.", "src/workflow_security/ai_analyzer.py: ")
    add_bullet("Runtime tool proxy for pre-execution enforcement in live agents.", "src/workflow_security/agent_adapter.py: ")
    add_bullet("SQLite schema and persistence functions.", "src/workflow_security/db.py: ")
    add_bullet("FastAPI server with Server-Sent Events and soft-pastel UI dashboard.", "src/workflow_security/web_app.py: ")
    add_bullet("Batch simulation engine for synthetic test scenarios.", "src/workflow_security/simulator.py: ")
    add_bullet("19 automated unit and integration tests.", "tests/: ")
    add_bullet("SQLite database and 5 JSON test scenarios.", "data/: ")
    add_bullet("Dashboard launcher script binding to port 8001.", "run_dashboard.py: ")

    # Save to file
    output_path = r"C:\Users\mdbaa\OneDrive\Desktop\Meta\IntentFence_Project_Documentation.docx"
    doc.save(output_path)
    print(f"Successfully generated DOCX at: {output_path}")

if __name__ == "__main__":
    create_document()
