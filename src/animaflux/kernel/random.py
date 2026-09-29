"""Kernel 随机服务（v5.9 §22.3 / §22.4）。

确定性核心：Plugin 业务随机性统一走 context.random，禁止全局随机源。
Random Stream 按 (runtime / branch / agent / domain) 稳定派生，互相隔离。
"""

from __future__ import annotations

import hashlib
import random as _random
from typing import Any, Sequence


class RandomStream:
    """一条独立随机流，由 root seed + stream_id 稳定派生。"""

    def __init__(self, rng: _random.Random) -> None:
        self._rng = rng

    def random(self) -> float:
        return self._rng.random()

    def uniform(self, a: float, b: float) -> float:
        return self._rng.uniform(a, b)

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def choice(self, seq: Sequence[Any]) -> Any:
        return self._rng.choice(seq)


class RandomService:
    """按需派生隔离的 Random Stream（§22.4）。"""

    def __init__(self, root_seed: int = 0) -> None:
        self._root_seed = root_seed
        self._streams: dict[str, RandomStream] = {}

    @property
    def root_seed(self) -> int:
        return self._root_seed

    def stream(self, *parts: str) -> RandomStream:
        key = "/".join(str(p) for p in parts)
        stream = self._streams.get(key)
        if stream is None:
            seed = self._derive_seed(self._root_seed, key)
            stream = RandomStream(_random.Random(seed))
            self._streams[key] = stream
        return stream

    @staticmethod
    def _derive_seed(root_seed: int, key: str) -> int:
        # 用稳定哈希派生，不依赖 PYTHONHASHSEED（跨进程可复现）
        digest = hashlib.sha256(f"{root_seed}:{key}".encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big")
