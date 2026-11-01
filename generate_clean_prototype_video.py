"""Capture clean 1920x1080 prototype screenshots and assemble video with ZERO added headers or footers."""

import time
import os
import subprocess
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import imageio_ffmpeg

OUTPUT_DIR = Path(r"C:\Users\mdbaa\OneDrive\Desktop\Meta")
AUDIO_FILE = OUTPUT_DIR / "IntentFence_Demo_Voiceover.mp3"
VIDEO_FILE = OUTPUT_DIR / "IntentFence_3Min_Demo_Video.mp4"
CLEAN_DIR = OUTPUT_DIR / "clean_prototype_frames"
CLEAN_DIR.mkdir(exist_ok=True)

def capture_clean_frames():
    print("Initializing headless Chrome with exact 1920x1080 viewport...")
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--force-device-scale-factor=1")

    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 1920,
        "height": 1080,
        "deviceScaleFactor": 1,
        "mobile": False
    })

    print("Opening prototype at http://127.0.0.1:8001...")
    driver.get("http://127.0.0.1:8001")
    time.sleep(2)

    # 1. Dashboard: Run live simulation to populate cards, timeline, and metrics
    print("Frame 1: Capturing Live Dashboard with active simulation...")
    try:
        driver.find_element(By.ID, "runBtn").click()
        time.sleep(4)
    except Exception as e:
        print("Error clicking runBtn:", e)

    f1 = CLEAN_DIR / "frame_1.png"
    driver.save_screenshot(str(f1))
    print("Saved:", f1)

    # 2. Protection: Two-Tier Objective Defense Architecture
    print("Frame 2: Capturing Protection view...")
    driver.execute_script("switchSection('protection');")
    time.sleep(1)
    f2 = CLEAN_DIR / "frame_2.png"
    driver.save_screenshot(str(f2))
    print("Saved:", f2)

    # 3. Decision Matrix Table
    print("Frame 3: Capturing Live Action Decision Table...")
    driver.execute_script("switchSection('dashboard');")
    time.sleep(0.5)
    driver.execute_script("window.scrollTo(0, 520);")
    time.sleep(1)
    f3 = CLEAN_DIR / "frame_3.png"
    driver.save_screenshot(str(f3))
    print("Saved:", f3)

    # 4. Developer Sandbox: Interception Tester & Python Adapter
    print("Frame 4: Capturing Developer Sandbox with active verdict...")
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)
    driver.execute_script("switchSection('developer');")
    time.sleep(1)
    try:
        driver.execute_script("fillSandboxPreset('blocked');")
        time.sleep(0.5)
        driver.find_element(By.ID, "sandboxTestBtn").click()
        time.sleep(1.5)
    except Exception as e:
        print("Error triggering sandbox test:", e)

    f4 = CLEAN_DIR / "frame_4.png"
    driver.save_screenshot(str(f4))
    print("Saved:", f4)

    # 5. Local Meta Llama 3.2 Security Analyst Report
    print("Frame 5: Capturing Local Meta Llama 3.2 Analysis Report...")
    driver.execute_script("switchSection('dashboard');")
    time.sleep(0.5)
    try:
        driver.find_element(By.ID, "aiBtn").click()
        time.sleep(10)
    except Exception as e:
        print("Error generating AI report:", e)
    driver.execute_script("window.scrollTo(0, 780);")
    time.sleep(1)
    f5 = CLEAN_DIR / "frame_5.png"
    driver.save_screenshot(str(f5))
    print("Saved:", f5)

    # 6. Audit & Compliance
    print("Frame 6: Capturing Audit Log & Telemetry Export...")
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)
    driver.execute_script("switchSection('audit');")
    time.sleep(2)
    f6 = CLEAN_DIR / "frame_6.png"
    driver.save_screenshot(str(f6))
    print("Saved:", f6)

    driver.quit()
    print("All pure prototype frames captured successfully!")

def assemble_clean_video():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Audio duration is 180.77s
    concat_file = CLEAN_DIR / "concat.txt"
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

    print("Encoding video using pure prototype UI alone...")
    subprocess.run(cmd, check=True)
    print(f"Clean prototype video generated at: {VIDEO_FILE}")

def main():
    capture_clean_frames()
    assemble_clean_video()

if __name__ == "__main__":
    main()
