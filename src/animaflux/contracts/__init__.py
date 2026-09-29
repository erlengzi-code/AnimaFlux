"""契约层（P1）：Protocol / dataclass / Enum，定义跨插件边界。

依赖方向：Default Plugin → Framework Contract（§16A.21）。
"""

from animaflux.contracts.capability import CapabilityId, CapabilityRegistry
from animaflux.contracts.context import ExecutionContext, RandomService, RandomStream, RuntimeContext, TimeContext
from animaflux.contracts.event import Event
from animaflux.contracts.influence import Influence
from animaflux.contracts.persistence import CommitRecord, PersistenceBackend, StateVersionRecord
from animaflux.contracts.process import Process, ProcessResult
from animaflux.contracts.state import StateNamespace, StateOwner, StateResolutionResult

__all__ = [
    "CapabilityId",
    "CapabilityRegistry",
    "CommitRecord",
    "Event",
    "ExecutionContext",
    "Influence",
    "PersistenceBackend",
    "Process",
    "ProcessResult",
    "RandomService",
    "RandomStream",
    "RuntimeContext",
    "StateNamespace",
    "StateOwner",
    "StateResolutionResult",
    "StateVersionRecord",
    "TimeContext",
]
