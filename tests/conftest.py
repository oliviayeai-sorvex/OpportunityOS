import sys
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "apps" / "control-plane" / "src"
sys.path.insert(0, str(SRC_PATH))
os.environ["REPOSITORY_BACKEND"] = "inmemory"
