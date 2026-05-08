"""把 examples/ 加入 sys.path, 让 test_stock_dashboard 可以 import examples 里的模块。"""
import sys
from pathlib import Path

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))
