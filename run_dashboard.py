"""Launcher script for IntentFence web dashboard on port 8001."""

import os
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

import uvicorn

if __name__ == "__main__":
    print("============================================================")
    print("[-] Starting IntentFence Real-Time Security Copilot")
    print("    URL: http://127.0.0.1:8001")
    print("    Local AI: Meta Llama 3.2 (3B) / Qwen 3 via local Ollama")
    print("============================================================")
    uvicorn.run(
        "workflow_security.web_app:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
        log_level="info",
    )
