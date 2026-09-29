"""AnimaFlux Local Web Console（Web Plan v0.2）。

FastAPI + Vanilla JS 的本地可视化控制台。它是 Public API 的消费者，与 CLI / Demo 平级；
冻结核心对它 zero import fastapi / uvicorn（§Web Plan §2）。依赖方向：web → public API → core。
"""
