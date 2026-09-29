"""StateReadCapability（v5.9 §9.2「要数据用 Capability」）。

跨模块只读访问某个 Namespace 的当前稳定版本，返回 frozen StateView（§9.15）。
要改变别人，必须走 Influence，不能通过这里（§9.2）。
"""

from __future__ import annotations

from animaflux.contracts.state import StateNamespace
from animaflux.state.state_store import StateStore
from animaflux.state.views import StateView


class StateReadCapability:
    """只读能力：把 StateStore 的当前版本包装成不可变 View 供其它模块读取。"""

    def __init__(self, store: StateStore) -> None:
        self._store = store

    def get_state(self, namespace: StateNamespace) -> StateView:
        version = self._store.read_version(namespace)
        return StateView(
            namespace=version.namespace,
            version=version.version,
            data=version.state,
        )
