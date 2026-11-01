"""Generate 3-minute 1080p demo video using actual prototype screenshots."""

import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

OUTPUT_DIR = Path(r"C:\Users\mdbaa\OneDrive\Desktop\Meta")
AUDIO_FILE = OUTPUT_DIR / "IntentFence_Demo_Voiceover.mp3"
VIDEO_FILE = OUTPUT_DIR / "IntentFence_3Min_Demo_Video.mp4"
SHOTS_DIR = OUTPUT_DIR / "proto_shots"
SLIDES_DIR = OUTPUT_DIR / "proto_slides"
SLIDES_DIR.mkdir(exist_ok=True)

WIDTH, HEIGHT = 1920, 1080

def get_font(size, bold=False):
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

def compose_prototype_frame(shot_filename, title, subtitle, bottom_highlight, view_tag):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "#090d16")
    draw = ImageDraw.Draw(canvas)

    # Top Navigation / Window Header Bar (height 68px)
    draw.rectangle([(0, 0), (WIDTH, 68)], fill="#0f172a")
    draw.line([(0, 68), (WIDTH, 68)], fill="#1e293b", width=2)

    # Brand badge
    draw.rounded_rectangle([(30, 14), (82, 54)], radius=8, fill="#2563eb")
    draw.text((42, 21), "IF", font=get_font(22, bold=True), fill="#ffffff")

    # Brand Title
    draw.text((96, 17), "IntentFence", font=get_font(20, bold=True), fill="#ffffff")
    draw.text((96, 41), "Meta Global AI Developer Hackathon 2026", font=get_font(12), fill="#94a3b8")

    # Center URL Pill
    pill_w = 480
    pill_x = (WIDTH - pill_w) // 2
    draw.rounded_rectangle([(pill_x, 14), (pill_x + pill_w, 54)], radius=20, fill="#1e293b", outline="#334155", width=1)
    
    # Online dot
    draw.ellipse([(pill_x + 20, 30), (pill_x + 30, 40)], fill="#10b981")
    draw.text((pill_x + 40, 24), "http://127.0.0.1:8001/ - IntentFence Live Prototype", font=get_font(13, bold=True), fill="#e2e8f0")

    # Right View Tag
    tag_w = 260
    tag_x = WIDTH - tag_w - 30
    draw.rounded_rectangle([(tag_x, 16), (tag_x + tag_w, 52)], radius=18, fill="#1e1e38", outline="#6366f1", width=1)
    draw.text((tag_x + 20, 24), view_tag, font=get_font(12, bold=True), fill="#a5b4fc")

    # Section Context Bar (height 44px)
    draw.rectangle([(0, 68), (WIDTH, 112)], fill="#131b2e")
    draw.text((32, 78), title, font=get_font(17, bold=True), fill="#38bdf8")
    draw.text((450, 80), subtitle, font=get_font(14), fill="#cbd5e1")

    # Load and place prototype screenshot
    shot_path = SHOTS_DIR / shot_filename
    if shot_path.exists():
        shot_img = Image.open(shot_path)
        # Target area: Y from 116 to 1024 (height 908px, width 1880px)
        target_w = 1880
        target_h = 908
        
        # Resize to fit target while preserving aspect ratio
        shot_img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        
        # Center horizontally and vertically within screenshot area
        paste_x = (WIDTH - shot_img.width) // 2
        paste_y = 116 + (target_h - shot_img.height) // 2
        
        # Border around prototype
        draw.rounded_rectangle([(paste_x - 4, paste_y - 4), (paste_x + shot_img.width + 4, paste_y + shot_img.height + 4)], radius=10, outline="#334155", width=2)
        canvas.paste(shot_img, (paste_x, paste_y))

    # Bottom Highlight Bar (height 52px)
    draw.rectangle([(0, HEIGHT - 52), (WIDTH, HEIGHT)], fill="#0b1120")
    draw.line([(0, HEIGHT - 52), (WIDTH, HEIGHT - 52)], fill="#1e293b", width=1)
    
    # Bottom text badge
    draw.rounded_rectangle([(30, HEIGHT - 42), (160, HEIGHT - 12)], radius=6, fill="#1e293b")
    draw.text((42, HEIGHT - 36), "CAPABILITY", font=get_font(11, bold=True), fill="#38bdf8")
    draw.text((176, HEIGHT - 37), bottom_highlight, font=get_font(14, bold=True), fill="#f8fafc")

    return canvas

def generate_all_prototype_slides():
    print("Composing slide frames from live prototype captures...")

    # Frame 1: Dashboard Overview (0 to 35s)
    f1 = compose_prototype_frame(
        "shot1_dashboard_live.png",
        "1. THE CHALLENGE & AGENT PLATFORM",
        "Autonomous AI agent replanning loops & tool-switching policy evasion",
        "Demonstrates real-time telemetry ingestion and detection of unauthorized agent route switching.",
        "LIVE SOC DASHBOARD"
    )
    f1.save(SLIDES_DIR / "frame_1.png")

    # Frame 2: Protection Architecture (35 to 68s)
    f2 = compose_prototype_frame(
        "shot4_protection.png",
        "2. TWO-TIER OBJECTIVE DEFENSE",
        "Replacing stateless inspection with denial-aware workflow guards & tombstones",
        "Objective memory persists across tool calls, child agents, and aliased resource views.",
        "OBJECTIVE MEMORY GUARD"
    )
    f2.save(SLIDES_DIR / "frame_2.png")

    # Frame 3: Decision Table & Verification Scenarios (68 to 110s)
    f3 = compose_prototype_frame(
        "shot1_table_view.png",
        "3. LIVE VERIFICATION MATRIX",
        "Step-by-step pre-execution boundary evaluation vs. traditional baseline",
        "5/5 benchmark verified: baseline allows tool switch; IntentFence blocks pre-execution.",
        "STEP AUDIT STREAM"
    )
    f3.save(SLIDES_DIR / "frame_3.png")

    # Frame 4: Developer Sandbox & Adapter (110 to 145s)
    f4 = compose_prototype_frame(
        "shot3_developer_sandbox.png",
        "4. DEVELOPER SECURITY SANDBOX",
        "Interactive pre-execution action interception tester & GuardedToolProxy adapter",
        "Drop-in CrewAI, LangChain, and AutoGen adapter with instant verdict payloads.",
        "DEVELOPER SANDBOX"
    )
    f4.save(SLIDES_DIR / "frame_4.png")

    # Frame 5: Meta Llama 3.2 Local Copilot (145 to 168s)
    f5 = compose_prototype_frame(
        "shot2_llama_report.png",
        "5. LOCAL META LLAMA 3.2 COPILOT",
        "Zero-cloud-transmission security analyst powered by open-weight Meta Llama 3.2 (3B)",
        "Synthesizes raw action traces into root-cause incident reports and SecOps remediation.",
        "META LLAMA 3.2 ANALYST"
    )
    f5.save(SLIDES_DIR / "frame_5.png")

    # Frame 6: SQLite Audit & Telemetry Export (168 to 181s)
    f6 = compose_prototype_frame(
        "shot5_audit_telemetry.png",
        "6. AUDIT COMPLIANCE & EXPORT",
        "SQLite persistent records with zero-dependency JSON & CSV telemetry export",
        "Complete tamper-evident audit trail for enterprise regulatory compliance and SOC integration.",
        "COMPLIANCE TELEMETRY"
    )
    f6.save(SLIDES_DIR / "frame_6.png")

    print("All 6 prototype slides composed successfully in proto_slides.")

def assemble_video():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Exact audio duration: 180.77s
    # Frame 1: 0 to 35s (duration 35)
    # Frame 2: 35 to 68s (duration 33)
    # Frame 3: 68 to 110s (duration 42)
    # Frame 4: 110 to 145s (duration 35)
    # Frame 5: 145 to 168s (duration 23)
    # Frame 6: 168 to 181s (duration 13)
    
    concat_file = SLIDES_DIR / "concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        f.write("file 'frame_1.png'\nduration 35\n")
        f.write("file 'frame_2.png'\nduration 33\n")
        f.write("file 'frame_3.png'\nduration 42\n")
        f.write("file 'frame_4.png'\nduration 35\n")
        f.write("file 'frame_5.png'\nduration 23\n")
        f.write("file 'frame_6.png'\nduration 13\n")
        f.write("file 'frame_6.png'\n")

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

    print("Encoding 1080p video with actual prototype UI and voiceover...")
    subprocess.run(cmd, check=True)
    print(f"Video created successfully at: {VIDEO_FILE}")

def main():
    generate_all_prototype_slides()
    assemble_video()

if __name__ == "__main__":
    main()
