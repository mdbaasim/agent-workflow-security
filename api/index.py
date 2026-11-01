import os
import sys
from pathlib import Path

# Add src directory to sys.path so workflow_security imports cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Set VERCEL environment indicator
os.environ.setdefault("VERCEL", "1")

from workflow_security.web_app import app
