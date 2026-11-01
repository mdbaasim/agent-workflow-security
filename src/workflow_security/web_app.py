"""IntentFence Web Application: Real-Time AI Agent Workflow Security Copilot.

Includes stateful event ingestion, Server-Sent Events (SSE) live streaming,
scenario playback controls, SQLite audit history, interactive developer sandbox,
and Meta Llama 3.2 local AI analysis.
"""

import asyncio
import csv
from datetime import datetime, timezone
import io
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from .ai_analyzer import DEFAULT_MODEL, analyze_workflow, get_available_local_models
from .correlator import detect_policy_evasion
from .db import clear_db, get_metrics, get_recent_events, init_db, record_run, save_evaluated_event
from .events import ActionEvent
from .guard import WorkflowGuard
from .policy import evaluate_action
from .simulator import load_scenario

logger = logging.getLogger("intentfence")

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "data" / "scenarios"
DEFAULT_SCENARIO_PATH = SCENARIOS_DIR / "alternative_route.json"

app = FastAPI(
    title="IntentFence",
    description="Real-Time AI Agent Workflow Security Copilot",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EventIngestBatch(BaseModel):
    events: list[ActionEvent]


class AIAnalysisRequest(BaseModel):
    model: str = Field(default=DEFAULT_MODEL)
    run_id: str | None = None


class SandboxActionRequest(BaseModel):
    objective_id: str = "export-payroll"
    agent_id: str = "bot-alpha"
    tool: str = "sql_query"
    action: str = "read"
    resource: str = "payroll_view"
    canonical_resource: str | None = None
    task_id: str = "interactive-sandbox"


class EngineState:
    """Stateful engine preserving active guard memory and broadcasting events in real time."""

    def __init__(self) -> None:
        init_db()
        self.restricted_resources = {"payroll_records"}
        self.guard = WorkflowGuard(self.restricted_resources)
        self.active_run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        self.active_scenario_name = DEFAULT_SCENARIO_PATH.name
        self.is_running_demo = False
        self.listeners: set[asyncio.Queue] = set()
        self.demo_task: asyncio.Task | None = None
        self.lock = asyncio.Lock()

    def reset_guard(self, restricted: set[str] | None = None) -> str:
        """Reset internal guard memory and generate a fresh run identifier."""
        if restricted is not None:
            self.restricted_resources = set(restricted)
        self.guard = WorkflowGuard(self.restricted_resources)
        now_iso = datetime.now(timezone.utc).isoformat()
        self.active_run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        record_run(self.active_run_id, self.active_scenario_name, now_iso)
        return self.active_run_id

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Deliver a structured telemetry message to all connected SSE clients."""
        payload = f"event: message\ndata: {json.dumps({'type': event_type, 'data': data})}\n\n"
        dead_queues = set()
        for q in list(self.listeners):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead_queues.add(q)
        self.listeners.difference_update(dead_queues)

    def evaluate_and_record(self, event: ActionEvent) -> dict[str, Any]:
        """Evaluate an individual event, apply guard logic, and commit to SQLite."""
        baseline = evaluate_action(event, self.restricted_resources)
        guarded = self.guard.evaluate(event)

        severity = "info"
        if guarded.status == "blocked":
            severity = "critical"
        elif guarded.status == "denied":
            severity = "warning"

        now_iso = datetime.now(timezone.utc).isoformat()
        record_dict = {
            "run_id": self.active_run_id,
            "step": event.step,
            "task_id": event.task_id,
            "objective_id": event.objective_id,
            "agent_id": event.agent_id,
            "parent_agent_id": event.parent_agent_id,
            "tool": event.tool,
            "action": event.action,
            "resource": event.resource,
            "canonical_resource": event.canonical_resource,
            "status": event.status,
            "baseline_status": baseline.status,
            "baseline_reason": baseline.reason,
            "guard_status": guarded.status,
            "guard_reason": guarded.reason,
            "severity": severity,
            "created_at": now_iso,
        }

        db_id = save_evaluated_event(record_dict)
        record_dict["id"] = db_id

        return record_dict


engine = EngineState()


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the Clean Top-Nav IntentFence web platform without sidebars."""
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/api/health")
async def health_check():
    """System health check and runtime capabilities."""
    models = get_available_local_models()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_run_id": engine.active_run_id,
        "active_scenario": engine.active_scenario_name,
        "restricted_resources": list(engine.restricted_resources),
        "denied_objectives_count": len(engine.guard.denied_objectives),
        "connected_sse_clients": len(engine.listeners),
        "demo_running": engine.is_running_demo,
        "ollama_available": len(models) > 0,
        "available_models": models,
    }


@app.get("/api/scenarios")
async def list_scenarios():
    """List all available JSON synthetic scenarios."""
    scenarios = []
    if SCENARIOS_DIR.exists():
        for file_path in sorted(SCENARIOS_DIR.glob("*.json")):
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    scenarios.append({
                        "id": file_path.name,
                        "name": data.get("scenario_name", file_path.stem),
                        "description": data.get("description", ""),
                        "event_count": len(data.get("events", [])),
                        "restricted_resources": data.get("restricted_resources", []),
                    })
            except Exception as e:
                logger.error(f"Error reading scenario {file_path}: {e}")
    return {"scenarios": scenarios}


@app.get("/api/events")
async def get_events(response: Response, run_id: str | None = None, limit: int = 100):
    """Retrieve recorded evaluated events and current aggregate metrics."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    events = get_recent_events(run_id=run_id, limit=limit)
    metrics = get_metrics(run_id=run_id)
    return {
        "run_id": run_id or engine.active_run_id,
        "metrics": metrics,
        "events": events,
    }


@app.post("/api/events")
async def ingest_events(payload: ActionEvent | EventIngestBatch):
    """Validate, evaluate, record, and stream incoming action events in real-time."""
    if isinstance(payload, EventIngestBatch):
        events_to_process = payload.events
    else:
        events_to_process = [payload]

    if not events_to_process:
        raise HTTPException(status_code=400, detail="No events provided.")

    processed = []
    async with engine.lock:
        for event in events_to_process:
            eval_record = engine.evaluate_and_record(event)
            processed.append(eval_record)
            await engine.broadcast("event_evaluated", eval_record)

        metrics = get_metrics(run_id=engine.active_run_id)
        await engine.broadcast("metrics_updated", metrics)

    return {
        "evaluated_count": len(processed),
        "events": processed,
        "metrics": get_metrics(run_id=engine.active_run_id),
    }


@app.post("/api/events/test")
async def evaluate_custom_action(payload: SandboxActionRequest):
    """Evaluate a custom user-defined action through the stateful guard and policy engine."""
    canonical = payload.canonical_resource or payload.resource
    existing_events = get_recent_events(run_id=engine.active_run_id, limit=500)
    step_num = len(existing_events) + 1

    event = ActionEvent(
        step=step_num,
        task_id=payload.task_id,
        objective_id=payload.objective_id,
        agent_id=payload.agent_id,
        tool=payload.tool,
        action=payload.action,
        resource=payload.resource,
        canonical_resource=canonical,
        status="requested",
    )
    async with engine.lock:
        eval_record = engine.evaluate_and_record(event)
        await engine.broadcast("event_evaluated", eval_record)
        metrics = get_metrics(run_id=engine.active_run_id)
        await engine.broadcast("metrics_updated", metrics)

    return {
        "record": eval_record,
        "metrics": metrics,
        "is_evasion": eval_record["baseline_status"] == "allowed" and eval_record["guard_status"] == "blocked",
    }


@app.get("/api/export/audit")
async def export_audit(format: str = "json", run_id: str | None = None):
    """Export persisted SQLite audit trail as downloadable JSON or CSV."""
    events = get_recent_events(run_id=run_id, limit=1000)
    if not events and run_id:
        events = get_recent_events(limit=1000)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if format.lower() == "csv":
        output = io.StringIO()
        fieldnames = [
            "id", "run_id", "step", "task_id", "objective_id", "agent_id",
            "parent_agent_id", "tool", "action", "resource", "canonical_resource",
            "baseline_status", "baseline_reason", "guard_status", "guard_reason",
            "severity", "created_at"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for ev in events:
            writer.writerow(ev)

        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="intentfence_audit_{timestamp_str}.csv"'
            }
        )
    else:
        json_content = json.dumps(events, indent=2)
        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="intentfence_audit_{timestamp_str}.json"'
            }
        )


@app.get("/api/evaluate")
async def evaluate_static_legacy():
    """Backward compatibility endpoint for static evaluation."""
    restricted, events = load_scenario(DEFAULT_SCENARIO_PATH)
    temp_guard = WorkflowGuard(restricted)
    baseline_decisions = [evaluate_action(e, restricted) for e in events]
    guard_decisions = [temp_guard.evaluate(e) for e in events]

    steps = [
        {
            "step": e.step,
            "objective": e.objective_id,
            "tool": e.tool,
            "action": e.action,
            "resource": e.resource,
            "canonical_resource": e.canonical_resource,
            "baseline_status": b.status.upper(),
            "baseline_reason": b.reason or "",
            "guard_status": g.status.upper(),
            "guard_reason": g.reason or "",
        }
        for e, b, g in zip(events, baseline_decisions, guard_decisions)
    ]
    caught = any(b.status == "allowed" and g.status == "blocked" for b, g in zip(baseline_decisions, guard_decisions))

    return {
        "scenario": DEFAULT_SCENARIO_PATH.name,
        "total_events": len(events),
        "baseline_allowed": sum(1 for b in baseline_decisions if b.status == "allowed"),
        "guard_blocked": sum(1 for g in guard_decisions if g.status == "blocked"),
        "caught_alternative": caught,
        "steps": steps,
    }


@app.get("/api/stream")
async def event_stream(request: Request):
    """Server-Sent Events (SSE) endpoint providing zero-refresh live telemetry."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    engine.listeners.add(queue)

    async def sse_generator():
        try:
            init_payload = {
                "type": "connected",
                "data": {
                    "run_id": engine.active_run_id,
                    "scenario": engine.active_scenario_name,
                    "metrics": get_metrics(run_id=engine.active_run_id),
                },
            }
            yield f"event: message\ndata: {json.dumps(init_payload)}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            engine.listeners.discard(queue)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/demo/run/{scenario_id}")
async def run_scenario_demo(scenario_id: str):
    """Run an automated scenario in the background, streaming events as they execute."""
    target_path = SCENARIOS_DIR / scenario_id
    if not target_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_id}' not found in {SCENARIOS_DIR}",
        )

    restricted_resources, events = load_scenario(target_path)

    async with engine.lock:
        if engine.demo_task and not engine.demo_task.done():
            engine.demo_task.cancel()

        engine.active_scenario_name = scenario_id
        run_id = engine.reset_guard(restricted_resources)
        engine.is_running_demo = True

    await engine.broadcast("demo_started", {
        "run_id": run_id,
        "scenario": scenario_id,
        "total_events": len(events),
        "restricted_resources": list(restricted_resources),
    })

    async def demo_worker():
        try:
            for event in events:
                await asyncio.sleep(0.4)
                async with engine.lock:
                    eval_record = engine.evaluate_and_record(event)
                await engine.broadcast("event_evaluated", eval_record)
                metrics = get_metrics(run_id=run_id)
                await engine.broadcast("metrics_updated", metrics)

            alerts = detect_policy_evasion(events)
            alert_dicts = [
                {
                    "step": a.step,
                    "alert_type": a.alert_type,
                    "agent_id": a.agent_id,
                    "tool": a.tool,
                    "canonical_resource": a.canonical_resource,
                    "reason": a.reason,
                }
                for a in alerts
            ]
            await engine.broadcast("demo_completed", {
                "run_id": run_id,
                "alerts": alert_dicts,
                "metrics": get_metrics(run_id=run_id),
            })
        except asyncio.CancelledError:
            await engine.broadcast("demo_stopped", {"run_id": run_id})
        finally:
            engine.is_running_demo = False

    engine.demo_task = asyncio.create_task(demo_worker())
    return {
        "status": "started",
        "scenario": target_path.name,
        "run_id": run_id,
        "total_events": len(events),
    }


@app.post("/api/demo/stop")
async def stop_demo():
    """Halt any ongoing synthetic playback immediately."""
    if engine.demo_task and not engine.demo_task.done():
        engine.demo_task.cancel()
        engine.is_running_demo = False
        await engine.broadcast("demo_stopped", {"status": "stopped"})
        return {"status": "stopped"}
    return {"status": "idle"}


@app.post("/api/demo/reset")
async def reset_demo():
    """Reset the guard state, clear the database, and notify clients."""
    if engine.demo_task and not engine.demo_task.done():
        engine.demo_task.cancel()
    clear_db()
    run_id = engine.reset_guard()
    metrics = get_metrics(run_id=run_id)
    await engine.broadcast("system_reset", {
        "run_id": run_id,
        "metrics": metrics,
    })
    return {"status": "reset", "run_id": run_id}


@app.post("/api/ai-analysis")
async def ai_analysis_endpoint(request_body: AIAnalysisRequest = AIAnalysisRequest()):
    """Explain recorded workflow evidence using local Meta Llama 3.2 or Qwen 3."""
    target_run_id = request_body.run_id or engine.active_run_id
    records = get_recent_events(run_id=target_run_id, limit=50)

    if not records:
        raise HTTPException(
            status_code=400,
            detail="No evaluated events found for this run. Run a scenario first.",
        )

    events = []
    baseline_decisions = []
    guard_decisions = []

    class DummyDecision:
        def __init__(self, status: str, reason: str):
            self.status = status
            self.reason = reason

    for r in records:
        event = ActionEvent(
            step=r["step"],
            task_id=r["task_id"],
            objective_id=r["objective_id"],
            agent_id=r["agent_id"],
            parent_agent_id=r.get("parent_agent_id"),
            tool=r["tool"],
            action=r["action"],
            resource=r["resource"],
            canonical_resource=r["canonical_resource"],
            status=r["raw_status"],
            reason=r.get("guard_reason"),
        )
        events.append(event)
        baseline_decisions.append(DummyDecision(r["baseline_status"], r["baseline_reason"]))
        guard_decisions.append(DummyDecision(r["guard_status"], r["guard_reason"]))

    try:
        report = analyze_workflow(
            events,
            baseline_decisions,
            guard_decisions,
            model=request_body.model,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {
        "report": report,
        "model": request_body.model,
        "run_id": target_run_id,
        "events_analyzed": len(events),
    }


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IntentFence - Autonomous Agent Security Platform</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --app-bg: #f8fafc;
  --card-bg: #ffffff;
  --text-main: #0f172a;
  --text-muted: #64748b;
  --text-dim: #94a3b8;
  --border-light: #f1f5f9;
  --border-subtle: #e2e8f0;
  
  --pastel-purple: #ede9fe;
  --pastel-purple-border: #ddd6fe;
  --pastel-purple-text: #6b21a8;

  --pastel-blue: #e0f2fe;
  --pastel-blue-border: #bae6fd;
  --pastel-blue-text: #0369a1;

  --pastel-green: #dcfce7;
  --pastel-green-border: #bbf7d0;
  --pastel-green-text: #15803d;

  --pastel-amber: #fef3c7;
  --pastel-amber-border: #fde68a;
  --pastel-amber-text: #b45309;

  --pastel-rose: #ffe4e6;
  --pastel-rose-border: #fecdd3;
  --pastel-rose-text: #be123c;

  --shadow-sm: 0 4px 12px rgba(15, 23, 42, 0.04);
  --shadow-md: 0 10px 30px rgba(15, 23, 42, 0.06);

  --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  width: 100%;
  min-height: 100vh;
  margin: 0;
  padding: 0;
  overflow-x: hidden;
  background-color: var(--app-bg);
  font-family: var(--font-sans);
  color: var(--text-main);
  -webkit-font-smoothing: antialiased;
}

/* App Main Content Surface - Full Viewport, No Sidebars */
.app-main {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 24px 36px;
  overflow-y: auto;
  gap: 22px;
}

/* Top Header Bar */
.main-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--border-subtle);
  min-height: 56px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  z-index: 2;
}

.brand-badge {
  background-color: #0f172a;
  color: #ffffff;
  padding: 6px 12px;
  border-radius: 8px;
  font-weight: 800;
  font-size: 14px;
  letter-spacing: -0.5px;
}

.brand-text-group {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.page-title {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.4px;
  color: var(--text-main);
}

.page-subtext {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

/* Centered Top Nav Container */
.center-nav-container {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
}

.top-nav-pills {
  display: inline-flex;
  align-items: center;
  background-color: #ffffff;
  border: 1px solid var(--border-subtle);
  border-radius: 30px;
  padding: 4px;
  gap: 4px;
  box-shadow: var(--shadow-sm);
}

.nav-pill-btn {
  background: transparent;
  color: var(--text-muted);
  border: none;
  border-radius: 24px;
  padding: 8px 22px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  outline: none;
  white-space: nowrap;
}

.nav-pill-btn:hover {
  color: var(--text-main);
}

.nav-pill-btn.active {
  background-color: #0f172a;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  z-index: 2;
}

.system-pill {
  background-color: #ffffff;
  border: 1px solid var(--border-subtle);
  border-radius: 24px;
  padding: 8px 18px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  box-shadow: var(--shadow-sm);
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #10b981;
}

.status-indicator.offline {
  background-color: #ef4444;
}

/* Tab Views */
.tab-view {
  display: none;
  flex-direction: column;
  gap: 22px;
}

.tab-view.active {
  display: flex;
}

/* Metrics Row */
.metrics-pill-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.metric-pill {
  background-color: #ffffff;
  border-radius: 16px;
  padding: 18px 20px;
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-pill-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-dim);
}

.metric-pill-val {
  font-size: 26px;
  font-weight: 800;
  font-family: var(--font-mono);
  color: var(--text-main);
}

/* Two Column Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 24px;
}

@media (max-width: 1200px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

/* Left Column */
.scenario-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-container-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-container-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.scenario-select-box {
  width: 100%;
  padding: 12px 16px;
  border-radius: 12px;
  background-color: #ffffff;
  border: 1px solid var(--border-subtle);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  box-shadow: var(--shadow-sm);
  outline: none;
  cursor: pointer;
}

/* Pastel Cards */
.pastel-card {
  border-radius: 16px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  box-shadow: var(--shadow-sm);
  border: 1px solid transparent;
  transition: transform 0.15s ease;
}

.pastel-card:hover {
  transform: translateY(-2px);
}

.pastel-card.purple {
  background-color: var(--pastel-purple);
  border-color: var(--pastel-purple-border);
}

.pastel-card.blue {
  background-color: var(--pastel-blue);
  border-color: var(--pastel-blue-border);
}

.pastel-card.green {
  background-color: var(--pastel-green);
  border-color: var(--pastel-green-border);
}

.pastel-card-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
}

.pastel-card-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
}

.pastel-card-meta {
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--text-dim);
}

/* White Box Containers */
.white-box {
  background-color: var(--card-bg);
  border-radius: 16px;
  padding: 24px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.action-btn-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-black {
  background-color: #0f172a;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  padding: 10px 20px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-black:hover:not(:disabled) {
  background-color: #1e293b;
  transform: translateY(-1px);
}

.btn-ghost {
  background-color: #f1f5f9;
  color: var(--text-main);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-ghost:hover:not(:disabled) {
  background-color: #e2e8f0;
}

button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* Timeline */
.timeline-card {
  background-color: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
}

.card-subtitle {
  font-size: 12px;
  color: var(--text-muted);
}

.timeline-track {
  display: flex;
  gap: 14px;
  overflow-x: auto;
  padding-bottom: 6px;
}

.step-card {
  min-width: 220px;
  background-color: #f8fafc;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: transform 0.2s ease;
}

.step-card:hover {
  transform: translateY(-2px);
  background-color: #ffffff;
  box-shadow: var(--shadow-sm);
}

.step-card.blocked {
  background-color: var(--pastel-amber);
  border-color: var(--pastel-amber-border);
}

.step-card.denied {
  background-color: var(--pastel-rose);
  border-color: var(--pastel-rose-border);
}

.step-card-num {
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
  color: var(--text-dim);
}

.step-card-tool {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.step-card-resource {
  font-size: 11px;
  font-family: var(--font-mono);
  color: #0284c7;
  word-break: break-all;
}

/* Audit Table */
.table-box {
  background-color: #ffffff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-subtle);
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  text-align: left;
}

th {
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-dim);
  letter-spacing: 0.6px;
  border-bottom: 1px solid var(--border-subtle);
}

td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-light);
  vertical-align: top;
}

tr:last-child td {
  border-bottom: none;
}

.status-tag {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-mono);
}

.tag-allowed {
  background-color: var(--pastel-green);
  color: var(--pastel-green-text);
}

.tag-denied {
  background-color: var(--pastel-rose);
  color: var(--pastel-rose-text);
}

.tag-blocked {
  background-color: var(--pastel-amber);
  color: var(--pastel-amber-text);
}

/* AI Report Area */
.ai-report-box {
  background-color: #f8fafc;
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
  padding: 20px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
  color: #334155;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.code-container {
  background-color: #0f172a;
  border-radius: 12px;
  padding: 20px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: #38bdf8;
  overflow-x: auto;
}

.bullet-group, .num-group {
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.5;
}
</style>
</head>
<body>

<!-- Main App Surface -->
<main class="app-main">

  <!-- Header with Brand on Left, Center Pills, System Status on Right -->
  <header class="main-header">
    <div class="header-left">
      <div class="brand-badge">IF</div>
      <div class="brand-text-group">
        <h1 class="page-title" id="pageTitle">Dashboard</h1>
        <p class="page-subtext" id="pageSubtitle">Real-Time Autonomous Agent Workflow Security Copilot</p>
      </div>
    </div>

    <!-- Centered Navigation Pills -->
    <div class="center-nav-container">
      <nav class="top-nav-pills">
        <button class="nav-pill-btn active" id="topPill-dashboard" onclick="switchSection('dashboard')">
          Dashboard
        </button>
        <button class="nav-pill-btn" id="topPill-developer" onclick="switchSection('developer')">
          Developer
        </button>
        <button class="nav-pill-btn" id="topPill-protection" onclick="switchSection('protection')">
          Protection
        </button>
        <button class="nav-pill-btn" id="topPill-audit" onclick="switchSection('audit')">
          Audit
        </button>
      </nav>
    </div>

    <div class="header-right">
      <div class="system-pill">
        <span class="status-indicator" id="statusDot"></span>
        <span id="statusLabel">System Online</span>
      </div>
    </div>
  </header>

  <!-- SECTION 1: WORKFLOW SECURITY DASHBOARD -->
  <div class="tab-view active" id="view-dashboard">

    <!-- Metrics Row -->
    <section class="metrics-pill-row">
      <div class="metric-pill">
        <span class="metric-pill-label">Evaluated Actions</span>
        <span class="metric-pill-val" id="valTotal">0</span>
      </div>
      <div class="metric-pill">
        <span class="metric-pill-label">Baseline Allowed</span>
        <span class="metric-pill-val" style="color: var(--pastel-green-text);" id="valAllowed">0</span>
      </div>
      <div class="metric-pill">
        <span class="metric-pill-label">Policy Denials</span>
        <span class="metric-pill-val" style="color: var(--pastel-rose-text);" id="valDenied">0</span>
      </div>
      <div class="metric-pill">
        <span class="metric-pill-label">Guard Blocks</span>
        <span class="metric-pill-val" style="color: var(--pastel-amber-text);" id="valBlocked">0</span>
      </div>
      <div class="metric-pill">
        <span class="metric-pill-label">Bypass Neutralized</span>
        <span class="metric-pill-val" id="valCaught" style="font-size: 20px;">NONE</span>
      </div>
    </section>

    <!-- Main Two Column Grid -->
    <div class="dashboard-grid">

      <!-- Left Column: Scenario & Pastel Action Cards -->
      <div class="scenario-column">
        <div class="card-container-header">
          <span class="card-container-title">Security Scenarios</span>
        </div>

        <select id="scenarioSelect" class="scenario-select-box" onchange="onScenarioChange()">
          <option value="alternative_route.json">1. Alternative Route Bypass</option>
          <option value="tool_switch.json">2. Tool Switching Evasion</option>
          <option value="delegated_agent.json">3. Delegated Agent Activity</option>
          <option value="benign_workflow.json">4. Benign Authorized Tasks</option>
          <option value="repeated_attempt.json">5. Repeated Action Retries</option>
        </select>

        <!-- Pastel Card 1 -->
        <div class="pastel-card purple">
          <span class="pastel-card-title">Payroll Access Denial</span>
          <p class="pastel-card-desc">Evaluates agent attempt to read sensitive payroll data through canonical file restrictions.</p>
          <div class="pastel-card-meta">
            <span>Target: payroll_records</span>
            <span>Policy: Restricted</span>
          </div>
        </div>

        <!-- Pastel Card 2 -->
        <div class="pastel-card blue">
          <span class="pastel-card-title">Alternative Route Detection</span>
          <p class="pastel-card-desc">Tracks objective memory when agent switches tools or database views to reach prohibited assets.</p>
          <div class="pastel-card-meta">
            <span>State: Denial-Aware</span>
            <span>Action: Blocked</span>
          </div>
        </div>

        <!-- Pastel Card 3 -->
        <div class="pastel-card green">
          <span class="pastel-card-title">Legitimate Continuity</span>
          <p class="pastel-card-desc">Preserves valid unrelated workflows and authorized operations without broad false positives.</p>
          <div class="pastel-card-meta">
            <span>Status: Authorized</span>
            <span>Guard: Allowed</span>
          </div>
        </div>
      </div>

      <!-- Right Column: Controls, Timeline & Decision Table -->
      <div style="display: flex; flex-direction: column; gap: 20px;">

        <!-- Controls Bar -->
        <div class="white-box">
          <div class="action-row">
            <div class="action-btn-group">
              <button id="runBtn" class="btn-black" onclick="startScenarioDemo()">Execute Live Simulation</button>
              <button id="stopBtn" class="btn-ghost" onclick="stopDemo()" disabled>Stop</button>
              <button id="resetBtn" class="btn-ghost" onclick="resetDemo()">Reset State</button>
            </div>

            <div class="action-btn-group">
              <select id="modelSelect" class="scenario-select-box" style="width: auto;">
                <option value="llama3.2:3b">Meta Llama 3.2 (3B)</option>
                <option value="qwen3:latest">Qwen 3 (Latest)</option>
              </select>
              <button id="aiBtn" class="btn-black" onclick="requestAIAnalysis()">Generate Report</button>
            </div>
          </div>
        </div>

        <!-- Action Timeline Strip -->
        <div class="timeline-card">
          <div class="card-header-row">
            <span class="card-title">Workflow Execution Progression</span>
            <span class="card-subtitle" id="timelineCount">0 Actions Ingested</span>
          </div>
          <div class="timeline-track" id="timelineList">
            <div style="color: var(--text-dim); font-size: 13px; padding: 12px 0;">Execute simulation to view action sequence nodes.</div>
          </div>
        </div>

        <!-- Live Table -->
        <div class="table-box">
          <div class="card-header-row" style="margin-bottom: 16px;">
            <span class="card-title">Action Ingestion Audit Stream</span>
            <span class="card-subtitle">Continuous Real-Time Verification</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>Step</th>
                <th>Agent & Tool</th>
                <th>Target Resource</th>
                <th>Baseline</th>
                <th>Workflow Guard</th>
              </tr>
            </thead>
            <tbody id="eventsTableBody">
              <tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 24px;">No actions ingested yet.</td></tr>
            </tbody>
          </table>
        </div>

        <!-- Local AI Advisory Report Area -->
        <div class="white-box">
          <div class="card-header-row">
            <span class="card-title">Local Security Analyst Report</span>
            <span class="card-subtitle">Zero Cloud Transmission (Local Meta Llama 3.2)</span>
          </div>
          <pre class="ai-report-box" id="aiReportBox">Select "Generate Report" to request an analytical breakdown from the local open-weight model.</pre>
        </div>

      </div>

    </div>

  </div>

  <!-- SECTION 2: DEVELOPER SANDBOX (INTERACTIVE TESTER) -->
  <div class="tab-view" id="view-developer">
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">

      <!-- Sandbox Interactive Form (Left Column) -->
      <div class="white-box">
        <div class="card-header-row">
          <div>
            <span class="card-title">Interactive Security Sandbox</span>
            <div class="card-subtitle">Live Action Interception Tester for Evaluators</div>
          </div>
          <span class="brand-badge" style="background-color: #2563eb; font-size: 11px;">TEST ENGINE</span>
        </div>

        <div style="display: flex; flex-direction: column; gap: 14px;">
          <div>
            <label style="font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">Objective ID</label>
            <input type="text" id="sandboxObjective" class="scenario-select-box" style="margin-top: 4px;" value="export-payroll" />
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div>
              <label style="font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">Agent ID</label>
              <input type="text" id="sandboxAgent" class="scenario-select-box" style="margin-top: 4px;" value="bot-alpha" />
            </div>
            <div>
              <label style="font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">Tool Name</label>
              <input type="text" id="sandboxTool" class="scenario-select-box" style="margin-top: 4px;" value="sql_query" />
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div>
              <label style="font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">Target Resource</label>
              <input type="text" id="sandboxResource" class="scenario-select-box" style="margin-top: 4px;" value="payroll_view" />
            </div>
            <div>
              <label style="font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">Canonical Entity</label>
              <input type="text" id="sandboxCanonical" class="scenario-select-box" style="margin-top: 4px;" value="payroll_records" />
            </div>
          </div>

          <div>
            <label style="font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">Quick Fill Presets</label>
            <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;">
              <button type="button" class="btn-ghost" style="padding: 6px 12px; font-size: 11px;" onclick="fillSandboxPreset('denied')">Preset 1: Initial Denial</button>
              <button type="button" class="btn-ghost" style="padding: 6px 12px; font-size: 11px;" onclick="fillSandboxPreset('blocked')">Preset 2: Tool Switch Evasion</button>
              <button type="button" class="btn-ghost" style="padding: 6px 12px; font-size: 11px;" onclick="fillSandboxPreset('allowed')">Preset 3: Legitimate Work</button>
            </div>
          </div>

          <div style="margin-top: 6px;">
            <button id="sandboxTestBtn" class="btn-black" style="width: 100%; padding: 12px; justify-content: center;" onclick="executeSandboxTest()">
              Test Action Interception
            </button>
          </div>
        </div>
      </div>

      <!-- Real-Time Verdict Card (Right Column) -->
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div class="white-box" id="verdictBox" style="border-left: 4px solid #f59e0b;">
          <div class="card-header-row">
            <div>
              <span class="card-title">Real-Time Interception Verdict</span>
              <div class="card-subtitle">Stateful Pre-Execution Outcome</div>
            </div>
            <span id="verdictBadge" class="status-tag tag-blocked" style="font-size: 12px; padding: 6px 12px;">READY</span>
          </div>

          <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 8px;">
            <div style="background-color: #f8fafc; border-radius: 10px; padding: 14px; border: 1px solid var(--border-subtle);">
              <div style="font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">Verdict Summary</div>
              <div id="verdictTitle" style="font-size: 15px; font-weight: 800; color: var(--text-main); margin-top: 2px;">Awaiting Execution</div>
              <p id="verdictDetail" style="font-size: 12px; color: var(--text-muted); margin-top: 6px; line-height: 1.5;">Click "Test Action Interception" to submit this custom action to the IntentFence workflow guard.</p>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
              <div style="background-color: #f8fafc; border-radius: 8px; padding: 10px; border: 1px solid var(--border-subtle);">
                <span style="font-size: 10px; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">Baseline Policy</span>
                <div id="verdictBaseline" style="font-size: 13px; font-weight: 700; color: var(--text-main); margin-top: 2px;">--</div>
              </div>
              <div style="background-color: #f8fafc; border-radius: 8px; padding: 10px; border: 1px solid var(--border-subtle);">
                <span style="font-size: 10px; font-weight: 700; color: var(--text-dim); text-transform: uppercase;">IntentFence Guard</span>
                <div id="verdictGuard" style="font-size: 13px; font-weight: 700; color: var(--text-main); margin-top: 2px;">--</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Python Code Integration Snippet -->
        <div class="white-box">
          <div class="card-header-row">
            <span class="card-title">Runtime Python Adapter</span>
            <span class="card-subtitle">GuardedToolProxy Boundary</span>
          </div>
          <div class="code-container" style="max-height: 180px;">
from workflow_security.agent_adapter import GuardedToolProxy
from workflow_security.guard import WorkflowGuard

guard = WorkflowGuard(restricted_resources={"payroll_records"})
proxy = GuardedToolProxy(guard)

# Pre-execution tool call interception
result = proxy.execute_guarded(event, my_tool_callable, **kwargs)
          </div>
        </div>
      </div>

    </div>
  </div>

  <!-- SECTION 3: POLICY PROTECTION -->
  <div class="tab-view" id="view-protection">
    <div class="white-box">
      <div class="card-header-row">
        <span class="card-title">Policy & Objective Memory Architecture</span>
        <span class="card-subtitle">Two-Tier Defense Model</span>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px;">
        <div class="pastel-card purple">
          <span class="pastel-card-title">Tier 1: Canonical Resource Policy</span>
          <p class="pastel-card-desc">Maps file paths, database views, and API calls to canonical identities to stop alias-based evasion.</p>
        </div>
        <div class="pastel-card blue">
          <span class="pastel-card-title">Tier 2: Denial-Aware Objective Tracking</span>
          <p class="pastel-card-desc">Preserves state across operations. If an objective meets a denial, subsequent actions under that objective are blocked.</p>
        </div>
      </div>
    </div>
  </div>

  <!-- SECTION 4: AUDIT & EXPORT -->
  <div class="tab-view" id="view-audit">
    <div class="white-box">
      <div class="card-header-row" style="flex-wrap: wrap; gap: 12px;">
        <div>
          <span class="card-title">Audit Log & Compliance Subsystem</span>
          <div class="card-subtitle">SQLite Persistent Records (data/intentfence.db) &bull; <span id="auditRecordCount" style="font-weight: 700; color: var(--text-main);">0 Records Persisted</span></div>
        </div>
        <div class="action-btn-group">
          <button class="btn-black" onclick="exportAudit('json')">Export Telemetry (JSON)</button>
          <button class="btn-ghost" onclick="exportAudit('csv')">Export Telemetry (CSV)</button>
          <button id="refreshAuditBtn" class="btn-ghost" onclick="loadAuditTable()">Refresh Audit</button>
        </div>
      </div>

      <!-- Audit Records Table -->
      <div style="overflow-x: auto; margin-top: 8px;">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Run ID</th>
              <th>Objective</th>
              <th>Agent & Tool</th>
              <th>Resource</th>
              <th>Baseline</th>
              <th>IntentFence Guard</th>
            </tr>
          </thead>
          <tbody id="auditTableBody">
            <tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 24px;">Loading persisted audit records...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

</main>

<script>
const byId = (id) => document.getElementById(id);
let eventSource = null;
let recordedEvents = [];

function switchSection(sectionId) {
  const sections = ["dashboard", "developer", "protection", "audit"];
  const titles = {
    dashboard: "Dashboard",
    developer: "Developer",
    protection: "Protection",
    audit: "Audit"
  };
  const subtitles = {
    dashboard: "Real-Time Autonomous Agent Workflow Security Copilot",
    developer: "Interactive Pre-Execution Action Interception Tester",
    protection: "Two-Tier Objective Defense & Canonical Policies",
    audit: "SQLite Audit Persistence & Regulatory Export"
  };

  sections.forEach(s => {
    const v = byId("view-" + s);
    const topPill = byId("topPill-" + s);
    if (v) v.classList.remove("active");
    if (topPill) topPill.classList.remove("active");
  });

  const activeView = byId("view-" + sectionId);
  const activeTopPill = byId("topPill-" + sectionId);
  if (activeView) activeView.classList.add("active");
  if (activeTopPill) activeTopPill.classList.add("active");

  byId("pageTitle").textContent = titles[sectionId] || "Dashboard";
  byId("pageSubtitle").textContent = subtitles[sectionId] || "";

  if (sectionId === "audit") {
    loadAuditTable();
  }
}

function initSSE() {
  if (eventSource) eventSource.close();
  eventSource = new EventSource("/api/stream");

  eventSource.onopen = () => {
    byId("statusDot").className = "status-indicator";
    byId("statusLabel").textContent = "System Online";
  };

  eventSource.onerror = () => {
    byId("statusDot").className = "status-indicator offline";
    byId("statusLabel").textContent = "Reconnecting";
  };

  eventSource.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      handleLiveMessage(msg);
    } catch (err) {
      console.warn("Telemetry stream error:", err);
    }
  };
}

function handleLiveMessage(msg) {
  if (msg.type === "connected") {
    updateMetrics(msg.data.metrics);
  } else if (msg.type === "event_evaluated") {
    addEvaluatedEvent(msg.data);
  } else if (msg.type === "metrics_updated") {
    updateMetrics(msg.data);
  } else if (msg.type === "demo_started") {
    recordedEvents = [];
    byId("eventsTableBody").innerHTML = "";
    byId("timelineList").innerHTML = "";
    byId("runBtn").disabled = true;
    byId("stopBtn").disabled = false;
  } else if (msg.type === "demo_completed") {
    byId("runBtn").disabled = false;
    byId("stopBtn").disabled = true;
  } else if (msg.type === "demo_stopped") {
    byId("runBtn").disabled = false;
    byId("stopBtn").disabled = true;
  } else if (msg.type === "system_reset") {
    recordedEvents = [];
    byId("eventsTableBody").innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 24px;">No actions ingested yet.</td></tr>';
    byId("timelineList").innerHTML = '<div style="color: var(--text-dim); font-size: 13px; padding: 12px 0;">Execute simulation to view action sequence nodes.</div>';
    byId("timelineCount").textContent = "0 Actions Ingested";
    byId("aiReportBox").textContent = 'Select "Generate Report" to request an analytical breakdown from the local open-weight model.';
    updateMetrics(msg.data.metrics);
    byId("runBtn").disabled = false;
    byId("stopBtn").disabled = true;
  }
}

function updateMetrics(m) {
  if (!m) return;
  byId("valTotal").textContent = m.total_events ?? 0;
  byId("valAllowed").textContent = m.baseline_allowed ?? 0;
  byId("valDenied").textContent = m.baseline_denied ?? 0;
  byId("valBlocked").textContent = m.guard_blocked ?? 0;

  const caught = m.caught_alternative;
  const caughtEl = byId("valCaught");
  if (caught) {
    caughtEl.textContent = "BLOCKED";
    caughtEl.style.color = "var(--pastel-amber-text)";
  } else {
    caughtEl.textContent = "NONE";
    caughtEl.style.color = "var(--text-dim)";
  }
}

function addEvaluatedEvent(event) {
  recordedEvents.push(event);
  byId("timelineCount").textContent = `${recordedEvents.length} Actions Ingested`;

  const tbody = byId("eventsTableBody");
  if (recordedEvents.length === 1) tbody.innerHTML = "";

  const tr = document.createElement("tr");

  const baselineTag = `<span class="status-tag tag-${event.baseline_status}">${event.baseline_status.toUpperCase()}</span>`;
  const guardTag = `<span class="status-tag tag-${event.guard_status}">${event.guard_status.toUpperCase()}</span>`;

  tr.innerHTML = `
    <td><strong style="font-family: var(--font-mono); font-size: 13px;">${event.step}</strong></td>
    <td>
      <div style="font-weight: 700; color: var(--text-main);">${escapeHtml(event.tool)}: ${escapeHtml(event.action)}</div>
      <div style="font-size: 11px; color: var(--text-dim); font-family: var(--font-mono);">Agent: ${escapeHtml(event.agent_id)}${event.parent_agent_id ? ' (' + escapeHtml(event.parent_agent_id) + ')' : ''}</div>
    </td>
    <td>
      <div style="font-family: var(--font-mono); color: #0284c7; font-size: 12px;">${escapeHtml(event.resource)}</div>
      <div style="font-size: 11px; color: var(--text-muted);">Obj: ${escapeHtml(event.objective_id)}</div>
    </td>
    <td>
      ${baselineTag}
      <div style="font-size: 11px; color: var(--text-dim); margin-top: 3px;">${escapeHtml(event.baseline_reason || '')}</div>
    </td>
    <td>
      ${guardTag}
      <div style="font-size: 11px; color: var(--text-dim); margin-top: 3px;">${escapeHtml(event.guard_reason || '')}</div>
    </td>
  `;
  tbody.appendChild(tr);

  const tl = byId("timelineList");
  if (recordedEvents.length === 1) tl.innerHTML = "";

  const stepCard = document.createElement("div");
  let stepClass = "step-card";
  if (event.guard_status === "blocked") stepClass += " blocked";
  else if (event.guard_status === "denied") stepClass += " denied";
  stepCard.className = stepClass;

  stepCard.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <span class="step-card-num">STEP ${event.step}</span>
      <span class="status-tag tag-${event.guard_status}">${event.guard_status.toUpperCase()}</span>
    </div>
    <div class="step-card-tool">${escapeHtml(event.tool)} (${escapeHtml(event.action)})</div>
    <div class="step-card-resource">${escapeHtml(event.resource)}</div>
  `;
  tl.appendChild(stepCard);
  tl.scrollLeft = tl.scrollWidth;
}

async function startScenarioDemo() {
  const scenario = byId("scenarioSelect").value;
  try {
    const res = await fetch(`/api/demo/run/${scenario}`, { method: "POST" });
    if (!res.ok) throw new Error(await res.text());
  } catch (err) {
    alert("Could not start demo: " + err.message);
  }
}

async function stopDemo() {
  try {
    await fetch("/api/demo/stop", { method: "POST" });
  } catch (err) {
    console.error(err);
  }
}

async function resetDemo() {
  try {
    await fetch("/api/demo/reset", { method: "POST" });
  } catch (err) {
    console.error(err);
  }
}

async function requestAIAnalysis() {
  const aiBtn = byId("aiBtn");
  const reportBox = byId("aiReportBox");
  const model = byId("modelSelect").value;

  aiBtn.disabled = true;
  aiBtn.textContent = "Analyzing...";
  reportBox.textContent = `Connecting to local Ollama (${model})...\nSynthesizing findings, evidence, and guard comparison...`;

  try {
    const res = await fetch("/api/ai-analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: model })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "AI analysis failed.");
    reportBox.textContent = data.report;
  } catch (err) {
    reportBox.textContent = `Analysis status:\n${err.message}\n\nNotice: Security decisions remain deterministic regardless of local model availability.`;
  } finally {
    aiBtn.disabled = false;
    aiBtn.textContent = "Generate Report";
  }
}

/* Developer Sandbox Functions */
function fillSandboxPreset(presetType) {
  if (presetType === "denied") {
    byId("sandboxObjective").value = "export-payroll";
    byId("sandboxAgent").value = "bot-alpha";
    byId("sandboxTool").value = "file_reader";
    byId("sandboxResource").value = "payroll.csv";
    byId("sandboxCanonical").value = "payroll_records";
  } else if (presetType === "blocked") {
    byId("sandboxObjective").value = "export-payroll";
    byId("sandboxAgent").value = "bot-alpha";
    byId("sandboxTool").value = "sql_query";
    byId("sandboxResource").value = "payroll_view";
    byId("sandboxCanonical").value = "payroll_view";
  } else if (presetType === "allowed") {
    byId("sandboxObjective").value = "read-handbook";
    byId("sandboxAgent").value = "bot-alpha";
    byId("sandboxTool").value = "web_fetcher";
    byId("sandboxResource").value = "https://docs.local/help.html";
    byId("sandboxCanonical").value = "public_help";
  }
}

async function executeSandboxTest() {
  const btn = byId("sandboxTestBtn");
  btn.disabled = true;

  const payload = {
    objective_id: byId("sandboxObjective").value.trim(),
    agent_id: byId("sandboxAgent").value.trim(),
    tool: byId("sandboxTool").value.trim(),
    action: "read",
    resource: byId("sandboxResource").value.trim(),
    canonical_resource: byId("sandboxCanonical").value.trim(),
    task_id: "interactive-sandbox"
  };

  try {
    const res = await fetch("/api/events/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Test failed");

    const record = data.record;
    const badge = byId("verdictBadge");
    const box = byId("verdictBox");
    const title = byId("verdictTitle");
    const detail = byId("verdictDetail");

    byId("verdictBaseline").textContent = record.baseline_status.toUpperCase() + (record.baseline_reason ? ` (${record.baseline_reason})` : "");
    byId("verdictGuard").textContent = record.guard_status.toUpperCase() + (record.guard_reason ? ` (${record.guard_reason})` : "");

    if (record.guard_status === "blocked") {
      badge.className = "status-tag tag-blocked";
      badge.textContent = "BLOCKED";
      box.style.borderLeftColor = "#f59e0b";
      title.textContent = "Bypass Evasion Neutralized";
      detail.textContent = `Action blocked pre-execution. Objective "${record.objective_id}" encountered previous denial. IntentFence prevented alternate tool execution.`;
    } else if (record.guard_status === "denied") {
      badge.className = "status-tag tag-denied";
      badge.textContent = "DENIED";
      box.style.borderLeftColor = "#f43f5e";
      title.textContent = "Policy Restriction Enforced";
      detail.textContent = `Target resource "${record.resource}" (Canonical: "${record.canonical_resource}") violates security policy. Objective marked as denied in guard memory.`;
    } else {
      badge.className = "status-tag tag-allowed";
      badge.textContent = "ALLOWED";
      box.style.borderLeftColor = "#10b981";
      title.textContent = "Action Authorized";
      detail.textContent = `Operation authorized. Unrelated objective "${record.objective_id}" executed without false-positive lockout.`;
    }

  } catch (err) {
    alert("Sandbox error: " + err.message);
  } finally {
    btn.disabled = false;
  }
}

/* Audit Table & Export Functions */
async function loadAuditTable() {
  const btn = byId("refreshAuditBtn");
  const countEl = byId("auditRecordCount");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Refreshing...";
  }
  const tbody = byId("auditTableBody");
  try {
    const res = await fetch(`/api/events?limit=100&_nocache=${Date.now()}`, { cache: "no-store" });
    const data = await res.json();
    const events = data.events || [];

    if (countEl) {
      countEl.textContent = `${events.length} Records Persisted`;
    }

    if (events.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-dim); padding: 24px;">No persisted audit records found in SQLite.</td></tr>';
      return;
    }

    tbody.innerHTML = events.map(e => `
      <tr>
        <td style="font-family: var(--font-mono); font-size: 11px;">${e.id}</td>
        <td style="font-family: var(--font-mono); font-size: 11px; color: var(--text-dim);">${escapeHtml(e.run_id)}</td>
        <td style="font-weight: 600;">${escapeHtml(e.objective_id)}</td>
        <td>
          <div style="font-weight: 700;">${escapeHtml(e.tool)}</div>
          <div style="font-size: 11px; color: var(--text-dim);">${escapeHtml(e.agent_id)}</div>
        </td>
        <td style="font-family: var(--font-mono); font-size: 11px; color: #0284c7;">${escapeHtml(e.resource)}</td>
        <td><span class="status-tag tag-${e.baseline_status}">${e.baseline_status.toUpperCase()}</span></td>
        <td><span class="status-tag tag-${e.guard_status}">${e.guard_status.toUpperCase()}</span></td>
      </tr>
    `).join("");

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="color: var(--pastel-rose-text); text-align: center; padding: 18px;">Failed to load audit records: ${escapeHtml(err.message)}</td></tr>`;
    if (countEl) countEl.textContent = "Error loading";
  } finally {
    if (btn) {
      btn.textContent = "Refreshed!";
      setTimeout(() => {
        btn.textContent = "Refresh Audit";
        btn.disabled = false;
      }, 700);
    }
  }
}

function exportAudit(fmt) {
  window.location.href = `/api/export/audit?format=${encodeURIComponent(fmt)}`;
}

function onScenarioChange() {
  resetDemo();
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

initSSE();
</script>
</body>
</html>
"""
