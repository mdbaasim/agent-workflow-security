"""Capture native 4K (3840x2160) prototype frames and encode 4K UHD demo video."""

import time
import subprocess
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import imageio_ffmpeg

OUTPUT_DIR = Path(r"C:\Users\mdbaa\OneDrive\Desktop\Meta")
AUDIO_FILE = OUTPUT_DIR / "IntentFence_Demo_Voiceover.mp3"
VIDEO_FILE = OUTPUT_DIR / "IntentFence_3Min_Demo_Video.mp4"
FRAMES_4K_DIR = OUTPUT_DIR / "frames_4k"
FRAMES_4K_DIR.mkdir(exist_ok=True)

def capture_4k_frames():
    print("Launching Chrome in native 4K HiDPI mode (3840x2160)...")
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=3840,2160")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opts)
    # Configure 2x scale on 1920x1080 CSS viewport to render crisp 3840x2160 output
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 1920,
        "height": 1080,
        "deviceScaleFactor": 2,
        "mobile": False
    })

    print("Opening prototype at http://127.0.0.1:8001...")
    driver.get("http://127.0.0.1:8001")
    time.sleep(2)

    # 1. Dashboard: Run live simulation
    print("Frame 1: Capturing Live Dashboard in 4K...")
    try:
        driver.find_element(By.ID, "runBtn").click()
        time.sleep(4)
    except Exception as e:
        print("Error clicking runBtn:", e)

    f1 = FRAMES_4K_DIR / "frame_1.png"
    driver.save_screenshot(str(f1))
    print("Saved:", f1)

    # 2. Protection: Two-Tier Objective Defense Architecture
    print("Frame 2: Capturing Protection Architecture in 4K...")
    driver.execute_script("switchSection('protection');")
    time.sleep(1)
    f2 = FRAMES_4K_DIR / "frame_2.png"
    driver.save_screenshot(str(f2))
    print("Saved:", f2)

    # 3. Decision Matrix Table
    print("Frame 3: Capturing Live Action Decision Table in 4K...")
    driver.execute_script("switchSection('dashboard');")
    time.sleep(0.5)
    driver.execute_script("window.scrollTo(0, 520);")
    time.sleep(1)
    f3 = FRAMES_4K_DIR / "frame_3.png"
    driver.save_screenshot(str(f3))
    print("Saved:", f3)

    # 4. Developer Sandbox: Interception Tester & Python Adapter
    print("Frame 4: Capturing Developer Sandbox in 4K...")
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

    f4 = FRAMES_4K_DIR / "frame_4.png"
    driver.save_screenshot(str(f4))
    print("Saved:", f4)

    # 5. Local Meta Llama 3.2 Security Analyst Report
    print("Frame 5: Capturing Local Meta Llama 3.2 Report in 4K...")
    driver.execute_script("switchSection('dashboard');")
    time.sleep(0.5)
    try:
        driver.find_element(By.ID, "aiBtn").click()
        time.sleep(10)
    except Exception as e:
        print("Error generating AI report:", e)
    driver.execute_script("window.scrollTo(0, 780);")
    time.sleep(1)
    f5 = FRAMES_4K_DIR / "frame_5.png"
    driver.save_screenshot(str(f5))
    print("Saved:", f5)

    # 6. Audit & Compliance
    print("Frame 6: Capturing Audit Log in 4K...")
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)
    driver.execute_script("switchSection('audit');")
    time.sleep(2)
    f6 = FRAMES_4K_DIR / "frame_6.png"
    driver.save_screenshot(str(f6))
    print("Saved:", f6)

    driver.quit()
    print("All 4K prototype frames captured successfully!")

def assemble_4k_video():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    concat_file = FRAMES_4K_DIR / "concat.txt"
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
        "-crf", "18",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", "00:03:00.00",
        str(VIDEO_FILE)
    ]

    print("Encoding 4K Ultra HD (3840x2160) video...")
    subprocess.run(cmd, check=True)
    print(f"4K video generated successfully at: {VIDEO_FILE}")

def main():
    capture_4k_frames()
    assemble_4k_video()

if __name__ == "__main__":
    main()
