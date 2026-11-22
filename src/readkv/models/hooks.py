"""KV 捕获与注入接口。

为何是接口而不是实现：transformers 5.x 的 cache API 随版本变化，直接绑定
内部实现会让评测与 mapper 代码被上游升级击穿。这里定义清晰的契约，真实适配
放在 runner（实验脚本）中，按当次 pinned 版本实现。

契约：
    capture_teacher_cache(model, tokens, layer_map, ...) -> KVCache
        - 对文档做一次 prefill；按层取 K/V；keys 为 de-RoPE 后的内容空间张量。
    inject_and_generate(model, cache, query_tokens, ...) -> generation
        - 用映射后的 cache 初始化 student；query token 的 position offset 显式传入；
          首 token 取自 prefill logits，不在已推进 query/gold 的 cache 上生成。
    verify_zero_re_prefill(...) -> bool
        - 断言 student forward 未接收任何上下文 token。
"""

from __future__ import annotations

from typing import Any

from readkv.cache.cache import KVCache


def capture_teacher_cache(*args: Any, **kwargs: Any) -> KVCache:  # pragma: no cover
    raise NotImplementedError(
        "capture_teacher_cache must be implemented against the pinned transformers version; "
        "return a readkv.cache.KVCache with de-ROPed keys"
    )


def inject_and_generate(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover
    raise NotImplementedError(
        "inject_and_generate must be implemented against the pinned transformers version; "
        "use a fresh cache and take the first token from prefill logits"
    )


def verify_zero_re_prefill(*args: Any, **kwargs: Any) -> bool:  # pragma: no cover
    raise NotImplementedError("instrument the student forward to assert no context tokens enter")
