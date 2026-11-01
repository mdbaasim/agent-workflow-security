"""Generate a complete 3-minute 1080p MP4 demo video with neural voiceover."""

import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

OUTPUT_DIR = Path(r"C:\Users\mdbaa\OneDrive\Desktop\Meta")
AUDIO_FILE = OUTPUT_DIR / "IntentFence_Demo_Voiceover.mp3"
VIDEO_FILE = OUTPUT_DIR / "IntentFence_3Min_Demo_Video.mp4"
SLIDES_DIR = OUTPUT_DIR / "temp_slides"
SLIDES_DIR.mkdir(exist_ok=True)

WIDTH, HEIGHT = 1920, 1080

def get_font(size, bold=False):
    # Try Windows system fonts
    font_names = ["segoeui.ttf", "arial.ttf", "calibri.ttf"]
    if bold:
        font_names = ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"]
    for name in font_names:
        font_path = Path("C:/Windows/Fonts") / name
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_header(draw, title, subtitle):
    # Background soft slate
    draw.rectangle([(0, 0), (WIDTH, HEIGHT)], fill="#0f172a") # Dark slate
    # Card surface
    draw.rounded_rectangle([(80, 60), (WIDTH - 80, HEIGHT - 60)], radius=24, fill="#ffffff")
    
    # Header bar
    draw.rounded_rectangle([(120, 90), (180, 130)], radius=8, fill="#0f172a")
    font_badge = get_font(20, bold=True)
    draw.text((135, 98), "IF", font=font_badge, fill="#ffffff")
    
    font_brand = get_font(22, bold=True)
    draw.text((200, 95), "IntentFence", font=font_brand, fill="#0f172a")
    
    font_sub = get_font(14)
    draw.text((200, 122), "Meta Global AI Developer Hackathon 2026", font=font_sub, fill="#64748b")
    
    # Page Title
    font_title = get_font(36, bold=True)
    draw.text((120, 170), title, font=font_title, fill="#0f172a")
    
    font_desc = get_font(18)
    draw.text((120, 220), subtitle, font=font_desc, fill="#64748b")
    
    # Divider line
    draw.line([(120, 255), (WIDTH - 120, 255)], fill="#e2e8f0", width=2)

def create_slide_1():
    img = Image.new("RGB", (WIDTH, HEIGHT), "#0f172a")
    draw = ImageDraw.Draw(img)
    draw_header(draw, "The Problem: Autonomous Agent Policy Evasion", "Why ReAct and planning loops bypass enterprise access control")
    
    # 2 Big Cards
    # Left: AI Agent Planning Loop
    draw.rounded_rectangle([(120, 290), (920, 960)], radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    draw.text((160, 330), "How Autonomous Agents Operate", font=get_font(24, bold=True), fill="#0f172a")
    
    points_left = [
        "1. Dynamic Goal-Seeking Loops:",
        "   Agents possess self-healing re-planning capability.",
        "",
        "2. The Bypass Mechanism:",
        "   If an action to read payroll records is DENIED,",
        "   the agent's optimization loop does not stop.",
        "",
        "3. Alternate Route Pursuit:",
        "   The agent switches tools to query an unmasked",
        "   database view, or delegates to a child agent.",
        "",
        "Outcome: Critical Corporate Data Exfiltration"
    ]
    y = 390
    for p in points_left:
        color = "#be123c" if "Outcome:" in p else "#334155"
        bold = True if ("1." in p or "2." in p or "3." in p or "Outcome:" in p) else False
        draw.text((160, y), p, font=get_font(20, bold=bold), fill=color)
        y += 44

    # Right: Stateless Failure
    draw.rounded_rectangle([(980, 290), (1800, 960)], radius=16, fill="#ffe4e6", outline="#fecdd3", width=2)
    draw.text((1020, 330), "Why Traditional Security Fails", font=get_font(24, bold=True), fill="#be123c")
    
    points_right = [
        "1. Stateless Inspection:",
        "   Traditional API gateways inspect each call in isolation.",
        "",
        "2. Zero Objective Memory:",
        "   The second tool gateway sees only a new query and",
        "   distinct resource name. It is blind to the prior denial.",
        "",
        "3. Resulting Security Breach:",
        "   The backdoor request is ALLOWED.",
        "",
        "IntentFence Solution: Stateful Objective Tracking"
    ]
    y = 390
    for p in points_right:
        color = "#047857" if "IntentFence Solution:" in p else "#9f1239"
        bold = True if ("1." in p or "2." in p or "3." in p or "IntentFence" in p) else False
        draw.text((1020, y), p, font=get_font(20, bold=bold), fill=color)
        y += 44

    img.save(SLIDES_DIR / "slide_1.png")

def create_slide_2():
    img = Image.new("RGB", (WIDTH, HEIGHT), "#0f172a")
    draw = ImageDraw.Draw(img)
    draw_header(draw, "The IntentFence Solution: Denial-Aware Objective Guard", "Transforming security from stateless tool checks to stateful goal memory")
    
    # 3 Pillars
    cards = [
        ("Objective-Level Binding", "Binds every action event to a canonical task_id and objective_id across the multi-step agent execution graph.", "#ede9fe", "#6b21a8"),
        ("Denial Tombstone Memory", "When an action meets a policy restriction, a permanent denial tombstone is recorded for that entire objective.", "#fef3c7", "#b45309"),
        ("Pre-Execution Interception", "GuardedToolProxy automatically intercepts and blocks any alternative route or delegated agent attempting to fulfill that goal.", "#dcfce7", "#15803d"),
    ]
    
    x = 120
    for title, desc, bg, text_col in cards:
        draw.rounded_rectangle([(x, 300), (x + 520, 750)], radius=16, fill=bg, outline="#cbd5e1", width=1)
        draw.text((x + 30, 340), title, font=get_font(24, bold=True), fill=text_col)
        
        words = desc.split()
        lines = []
        cur = []
        for w in words:
            cur.append(w)
            if len(" ".join(cur)) > 30:
                lines.append(" ".join(cur))
                cur = []
        if cur:
            lines.append(" ".join(cur))
        
        ly = 420
        for line in lines:
            draw.text((x + 30, ly), line, font=get_font(20), fill="#334155")
            ly += 36
        x += 570

    # Bottom Banner
    draw.rounded_rectangle([(120, 800), (1800, 960)], radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    draw.text((160, 840), "Targeted Granularity Guarantee:", font=get_font(22, bold=True), fill="#0f172a")
    draw.text((160, 885), "Unrelated legitimate business objectives proceed normally without false-positive operational lockouts.", font=get_font(20), fill="#475569")
    
    img.save(SLIDES_DIR / "slide_2.png")

def create_slide_3():
    img = Image.new("RGB", (WIDTH, HEIGHT), "#0f172a")
    draw = ImageDraw.Draw(img)
    draw_header(draw, "Live Verification Matrix: Multi-Step Attack Scenario", "Side-by-side comparison: Stateless Baseline vs. IntentFence Stateful Guard")
    
    # Table Header
    draw.rounded_rectangle([(120, 300), (1800, 360)], radius=8, fill="#1e3a8a")
    draw.text((150, 320), "Step", font=get_font(18, bold=True), fill="#ffffff")
    draw.text((250, 320), "Action Attempt", font=get_font(18, bold=True), fill="#ffffff")
    draw.text((850, 320), "Baseline Policy", font=get_font(18, bold=True), fill="#ffffff")
    draw.text((1150, 320), "IntentFence Guard", font=get_font(18, bold=True), fill="#ffffff")
    draw.text((1480, 320), "Security Outcome", font=get_font(18, bold=True), fill="#ffffff")
    
    rows = [
        ("Step 1", "Read payroll.csv via file_reader tool", "DENIED", "DENIED", "Restricted resource; denial tombstone stamped.", "#ffe4e6"),
        ("Step 2", "Query payroll_view via sql_query tool (same objective)", "ALLOWED", "BLOCKED", "IntentFence detects evasion and neutralizes call.", "#fef3c7"),
        ("Step 3", "Fetch public documentation (unrelated objective)", "ALLOWED", "ALLOWED", "Authorized legitimate work permitted smoothly.", "#dcfce7"),
    ]
    
    y = 380
    for step, action, base, guard, outcome, bg in rows:
        draw.rounded_rectangle([(120, y), (1800, y + 160)], radius=12, fill=bg, outline="#cbd5e1", width=1)
        draw.text((150, y + 60), step, font=get_font(20, bold=True), fill="#0f172a")
        draw.text((250, y + 60), action, font=get_font(18, bold=True), fill="#0f172a")
        
        base_col = "#be123c" if base == "DENIED" else "#15803d"
        draw.text((880, y + 60), base, font=get_font(20, bold=True), fill=base_col)
        
        guard_col = "#b45309" if guard == "BLOCKED" else ("#be123c" if guard == "DENIED" else "#15803d")
        draw.text((1180, y + 60), guard, font=get_font(20, bold=True), fill=guard_col)
        
        draw.text((1450, y + 60), outcome, font=get_font(16), fill="#334155")
        y += 180

    img.save(SLIDES_DIR / "slide_3.png")

def create_slide_4():
    img = Image.new("RGB", (WIDTH, HEIGHT), "#0f172a")
    draw = ImageDraw.Draw(img)
    draw_header(draw, "Developer Integration & Persistence Subsystem", "Pre-execution GuardedToolProxy and complete SQLite compliance auditing")
    
    # Left Card: Python Adapter
    draw.rounded_rectangle([(120, 290), (940, 960)], radius=16, fill="#0f172a", outline="#38bdf8", width=2)
    draw.text((160, 330), "Python GuardedToolProxy Integration", font=get_font(22, bold=True), fill="#38bdf8")
    
    code = [
        "from workflow_security.agent_adapter import GuardedToolProxy",
        "from workflow_security.guard import WorkflowGuard",
        "",
        "# 1. Initialize guard with restricted policies",
        "guard = WorkflowGuard(restricted_resources={'payroll'})",
        "proxy = GuardedToolProxy(guard)",
        "",
        "# 2. Intercept agent tool execution",
        "try:",
        "    result = proxy.execute_guarded(",
        "        event, my_tool_callable, **tool_kwargs",
        "    )",
        "except SecurityEnforcementError as exc:",
        "    # Throws exception before reaching tool",
        "    print(f'Action Blocked: {exc.reason}')"
    ]
    y = 400
    for line in code:
        draw.text((160, y), line, font=get_font(17), fill="#e0f2fe")
        y += 34

    # Right Card: Interactive Sandbox & Audit Export
    draw.rounded_rectangle([(1000, 290), (1800, 960)], radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    draw.text((1040, 330), "Sandbox & Compliance Telemetry", font=get_font(22, bold=True), fill="#0f172a")
    
    features = [
        ("Interactive Action Sandbox", "Evaluators can input custom objectives, tools, and resources with instant live verdict calculation."),
        ("One-Click Telemetry Export", "Download SQLite audit logs directly as formatted JSON or CSV files for SecOps review."),
        ("SQLite Persistent Storage", "All runs, event chains, decisions, and timestamps are recorded in data/intentfence.db."),
        ("Serverless Cloud Ready", "Preconfigured with vercel.json and api/index.py for zero-configuration cloud hosting.")
    ]
    y = 400
    for f_title, f_desc in features:
        draw.text((1040, y), f_title, font=get_font(20, bold=True), fill="#1e3a8a")
        y += 32
        draw.text((1040, y), f_desc, font=get_font(16), fill="#475569")
        y += 65

    img.save(SLIDES_DIR / "slide_4.png")

def create_slide_5():
    img = Image.new("RGB", (WIDTH, HEIGHT), "#0f172a")
    draw = ImageDraw.Draw(img)
    draw_header(draw, "Local Meta Llama 3.2 Security Copilot", "Zero-cost, privacy-first AI intelligence running locally via Ollama")
    
    # Left: Architecture
    draw.rounded_rectangle([(120, 290), (940, 960)], radius=16, fill="#f8fafc", outline="#cbd5e1", width=2)
    draw.text((160, 330), "Why Meta Llama 3.2 is Essential", font=get_font(24, bold=True), fill="#0f172a")
    
    points = [
        ("Strict Architectural Separation", "Deterministic Python rules make 100% of the blocking decisions. Meta Llama 3.2 acts strictly as an analytical auditor."),
        ("Absolute Data Sovereignty", "Security audit logs contain sensitive internal file paths and schemas. Meta open-weights run on-premise without cloud transmission."),
        ("Zero Marginal API Cost", "Monitoring thousands of agent tool calls would be cost-prohibitive on commercial APIs. Llama 3.2 runs free forever."),
        ("Edge Hardware Efficiency", "3B parameters delivers high-speed inference on standard laptops with only 2 GB VRAM.")
    ]
    y = 390
    for h, b in points:
        draw.text((160, y), h, font=get_font(20, bold=True), fill="#1e3a8a")
        y += 30
        draw.text((160, y), b, font=get_font(16), fill="#475569")
        y += 65

    # Right: Sample Copilot Output
    draw.rounded_rectangle([(1000, 290), (1800, 960)], radius=16, fill="#0f172a", outline="#10b981", width=2)
    draw.text((1040, 330), "Live Meta Llama 3.2 Advisory Output", font=get_font(22, bold=True), fill="#10b981")
    
    sample = [
        "[+] INCIDENT FINDINGS SUMMARY",
        "Model: Meta Llama 3.2 (3B) Local",
        "Telemetry Evaluated: 3 Action Events",
        "",
        "- Event 1: DENIED (payroll_records access blocked)",
        "- Event 2: BLOCKED (Tool switch evasion detected)",
        "  Evidence: Objective 'export-payroll' attempted backdoor",
        "  via sql_query on payroll_view. Neutralized.",
        "- Event 3: ALLOWED (Authorized research task)",
        "",
        "[+] SecOps Recommendation:",
        "Quarantine agent session 'bot-alpha' for manual review.",
        "Deterministic guard prevented unauthorized data exfiltration."
    ]
    y = 400
    for line in sample:
        col = "#10b981" if "[+]" in line else "#e0f2fe"
        draw.text((1040, y), line, font=get_font(17), fill=col)
        y += 34

    img.save(SLIDES_DIR / "slide_5.png")

def assemble_video():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Timings for 5 slides: total ~180s (3m)
    # Slide 1: 0 - 35s (duration 35s)
    # Slide 2: 35 - 68s (duration 33s)
    # Slide 3: 68 - 110s (duration 42s)
    # Slide 4: 110 - 145s (duration 35s)
    # Slide 5: 145 - 181s (duration 36s)
    
    # Create concat demuxer file
    concat_file = SLIDES_DIR / "concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        f.write("file 'slide_1.png'\nduration 35\n")
        f.write("file 'slide_2.png'\nduration 33\n")
        f.write("file 'slide_3.png'\nduration 42\n")
        f.write("file 'slide_4.png'\nduration 35\n")
        f.write("file 'slide_5.png'\nduration 36\n")
        f.write("file 'slide_5.png'\n") # EOF requirement for concat demuxer
    
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-i", str(AUDIO_FILE),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(VIDEO_FILE)
    ]
    
    print("Assembling 1080p MP4 video with FFmpeg...")
    subprocess.run(cmd, check=True)
    print(f"Successfully generated demo video: {VIDEO_FILE}")

def main():
    print("Generating visual slide frames...")
    create_slide_1()
    create_slide_2()
    create_slide_3()
    create_slide_4()
    create_slide_5()
    print("Slides created in temp_slides.")
    assemble_video()

if __name__ == "__main__":
    main()
