import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--force-device-scale-factor=1")

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_window_size(1920, 1080)

    output_dir = r"C:\Users\mdbaa\OneDrive\Desktop\Meta\proto_shots"
    os.makedirs(output_dir, exist_ok=True)

    print("Navigating to http://127.0.0.1:8001...")
    driver.get("http://127.0.0.1:8001")
    time.sleep(2)

    # 1. Dashboard: Run live simulation
    print("Executing live simulation...")
    try:
        run_btn = driver.find_element(By.ID, "runBtn")
        run_btn.click()
        time.sleep(4)  # Wait for simulation events to process
    except Exception as e:
        print("Error clicking runBtn:", e)

    shot1 = os.path.join(output_dir, "shot1_dashboard_live.png")
    driver.save_screenshot(shot1)
    print("Saved:", shot1)

    # 2. Local AI Report (Meta Llama 3.2)
    print("Triggering Local AI Report...")
    try:
        ai_btn = driver.find_element(By.ID, "aiBtn")
        ai_btn.click()
        # Wait up to 10 seconds for report to generate
        time.sleep(10)
        # Scroll to bring the AI report and action table into view
        driver.execute_script("window.scrollTo(0, 480);")
        time.sleep(1)
    except Exception as e:
        print("Error triggering AI analysis:", e)

    shot2 = os.path.join(output_dir, "shot2_llama_report.png")
    driver.save_screenshot(shot2)
    print("Saved:", shot2)

    # 3. Developer Sandbox
    print("Switching to Developer Sandbox...")
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(0.5)
    driver.execute_script("switchSection('developer');")
    time.sleep(1)
    # Click Preset 2 (Tool Switch Evasion) and execute test
    try:
        driver.execute_script("fillSandboxPreset('blocked');")
        time.sleep(0.5)
        test_btn = driver.find_element(By.ID, "sandboxTestBtn")
        test_btn.click()
        time.sleep(1.5)
    except Exception as e:
        print("Error testing sandbox:", e)

    shot3 = os.path.join(output_dir, "shot3_developer_sandbox.png")
    driver.save_screenshot(shot3)
    print("Saved:", shot3)

    # 4. Protection & Policy Architecture
    print("Switching to Protection view...")
    driver.execute_script("switchSection('protection');")
    time.sleep(1)
    shot4 = os.path.join(output_dir, "shot4_protection.png")
    driver.save_screenshot(shot4)
    print("Saved:", shot4)

    # 5. Audit & Compliance
    print("Switching to Audit view...")
    driver.execute_script("switchSection('audit');")
    time.sleep(2)
    shot5 = os.path.join(output_dir, "shot5_audit_telemetry.png")
    driver.save_screenshot(shot5)
    print("Saved:", shot5)

    driver.quit()
    print("All prototype screenshots captured successfully!")

if __name__ == "__main__":
    main()
