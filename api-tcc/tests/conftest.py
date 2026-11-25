import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("YOLO_CONFIG_DIR", tempfile.gettempdir())
os.environ.setdefault(
    "PERMANENT_BLACKLIST_FILE",
    str(Path(tempfile.gettempdir()) / "api_tcc_test_blacklist.txt"),
)
os.environ.setdefault("GLOBAL_PERMANENT_BLACKLIST_ON_BURST", "False")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
