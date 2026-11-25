"""模型接入层：加载/冻结、hook 捕获与注入、RoPE、层映射 + V2 CF-RCT。"""

from .cf_rct import CFRCTMapper, CFRCTModule
from .layer_map import LayerMap
from .mock_backend import MockBackend, MockSpec
from .rope import apply_rope, de_rope, rotate_half

__all__ = [
    "LayerMap", "MockBackend", "MockSpec", "de_rope", "apply_rope", "rotate_half",
    "CFRCTMapper", "CFRCTModule",
]
