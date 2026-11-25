"""离线工具脚本。允许从仓库根以 ``python -m scripts.<name>`` 运行。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
