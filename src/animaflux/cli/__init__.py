"""AnimaFlux CLI（v5.9 §16C.29）。

命令：create / open / status / step / advance / observe / checkpoint / branch / replay / inspect。
默认用 SQLite 后端（--db）持久化，使 checkpoint / replay 跨进程可用。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from animaflux import __version__
from animaflux.api import AnimaFlux, CharacterBootstrap
from animaflux.contracts.environment import Observation
from animaflux.contracts.state import StateNamespace
from animaflux.persistence.sqlite import SqliteBackend
from animaflux.runtime.replay import ReplayEngine


def _namespace(value: str) -> StateNamespace:
    try:
        return StateNamespace(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"unknown namespace '{value}'")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="animaflux",
        description="AnimaFlux / 灵演 — An Open Runtime for Evolving Digital Life",
    )
    parser.add_argument("--version", action="version", version=f"animaflux {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default="animaflux.db", help="SQLite 后端路径（默认 animaflux.db）")

    p_create = sub.add_parser("create", parents=[common], help="创建数字生命")
    p_create.add_argument("--agent", default="life-1")
    p_create.add_argument("--name", default="小林")
    p_create.add_argument("--values", nargs="*", default=(), help="初始价值观（如 safety authenticity）")

    p_status = sub.add_parser("status", parents=[common], help="打印当前 Committed 状态摘要")
    p_status.add_argument("--agent", default="life-1")

    p_open = sub.add_parser("open", parents=[common], help="从持久化后端 RESTORE 生命（等价 status 语义）")
    p_open.add_argument("--agent", default="life-1")

    p_step = sub.add_parser("step", parents=[common], help="推进一个 Tick")
    p_step.add_argument("--agent", default="life-1")
    p_step.add_argument("--seconds", type=float, default=1.0)

    p_advance = sub.add_parser("advance", parents=[common], help="推进 World Time（无输入）")
    p_advance.add_argument("--agent", default="life-1")
    p_advance.add_argument("--seconds", type=float, default=1.0)

    p_observe = sub.add_parser("observe", parents=[common], help="注入一条 Observation（经 Perception→Appraisal）")
    p_observe.add_argument("--agent", default="life-1")
    p_observe.add_argument("--text", default="")

    p_ckpt = sub.add_parser("checkpoint", parents=[common], help="快照当前 Checkpoint")
    p_ckpt.add_argument("--agent", default="life-1")

    p_branch = sub.add_parser("branch", parents=[common], help="从当前 Checkpoint Fork 新 Branch")
    p_branch.add_argument("--agent", default="life-1")
    p_branch.add_argument("--name", default="branch")

    p_replay = sub.add_parser("replay", parents=[common], help="只读回放 Commit Journal")
    p_replay.add_argument("--agent", default="life-1")

    p_inspect = sub.add_parser("inspect", parents=[common], help="只读查看某个 State 当前版本")
    p_inspect.add_argument("--agent", default="life-1")
    p_inspect.add_argument("--namespace", type=_namespace, required=True)

    p_web = sub.add_parser("web", parents=[common], help="启动本地 Web Console（§39.21）")
    p_web.add_argument("--host", default="127.0.0.1")
    p_web.add_argument("--port", type=int, default=8000)
    p_web.add_argument("--open", action="store_true", help="启动后自动打开浏览器")

    return parser


def _open_life(db_path: str, agent_id: str):
    flux = AnimaFlux(SqliteBackend(db_path))
    return flux, flux.open(agent_id)


def _run_web(args) -> int:
    """启动 Web Console：`python -m uvicorn animaflux.web.asgi:app`（§39.21）。

    用 subprocess 启动，避免 CLI（冻结 Core）直接 import uvicorn（§Web Plan §2 的
    import-direction 契约）；uvicorn 属于 [web] optional extra，未安装时给出可读提示。
    """
    import os
    import subprocess
    import threading
    import time
    import webbrowser

    env = dict(os.environ)
    env.setdefault("ANIMAFLUX_DB", args.db)
    cmd = [
        sys.executable, "-m", "uvicorn", "animaflux.web.asgi:app",
        "--host", args.host, "--port", str(args.port),
    ]
    if args.open:
        def _open_later():
            time.sleep(1.5)
            webbrowser.open(f"http://{args.host}:{args.port}")
        threading.Thread(target=_open_later, daemon=True).start()
    try:
        return subprocess.call(cmd, env=env)
    except FileNotFoundError:
        print('错误：未安装 uvicorn。请先 `pip install "animaflux[web]"`。', file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    db_path = args.db

    if args.command == "web":
        return _run_web(args)

    if args.command == "create":
        flux = AnimaFlux(SqliteBackend(db_path))
        handle = flux.create_life(
            args.agent,
            bootstrap=CharacterBootstrap(primary_name=args.name, values=tuple(args.values)),
        )
        print(f"created agent_id={handle.agent_id} name={args.name}")
        return 0

    if args.command in ("open", "status"):
        flux = AnimaFlux(SqliteBackend(db_path))
        handle = flux.open(args.agent)
        if args.command == "open":
            print(f"restored agent_id={handle.agent_id}")
        print(f"world_time={handle.now().isoformat()}")
        for ns in sorted(handle._runtime.store.committed_namespaces(), key=lambda n: n.value):
            view = handle.inspect(ns)
            print(f"  {ns.value} v{view.version}")
        return 0

    flux, handle = _open_life(db_path, args.agent)

    if args.command == "step":
        tick_id = handle.step(args.seconds)
        print(f"stepped tick_id={tick_id} world_time={handle.now().isoformat()}")
        return 0

    if args.command == "advance":
        tick_id = handle.advance(args.seconds)
        print(f"advanced tick_id={tick_id} world_time={handle.now().isoformat()}")
        return 0

    if args.command == "observe":
        obs = Observation(
            observation_id="cli-observe",
            modality="communication",
            content=args.text,
            world_time=handle.now(),
            source_entity="human",
        )
        tick_id = handle.observe(obs)
        print(f"observed tick_id={tick_id}")
        return 0

    if args.command == "checkpoint":
        cp = handle.checkpoint()
        print(json.dumps({"checkpoint_id": cp.checkpoint_id, "version_map": cp.version_map}, ensure_ascii=False))
        return 0

    if args.command == "branch":
        branch = handle.branch(name=args.name)
        print(f"branched branch_id={branch.branch_id} from={args.agent}")
        return 0

    if args.command == "replay":
        engine = ReplayEngine(flux.backend)
        for tick in engine.replay_timeline(args.agent):
            print(f"{tick.tick_id} {tick.commit_id} time={tick.runtime_time_after} versions={sorted(tick.version_map)}")
        print(f"replayed {len(engine.replay_timeline(args.agent))} ticks (llm_calls={engine.llm_calls}, write_ops={engine.write_ops})")
        return 0

    if args.command == "inspect":
        view = handle.inspect(args.namespace)
        print(json.dumps(
            {"namespace": view.namespace.value, "version": view.version, "data": repr(view.data)},
            ensure_ascii=False,
        ))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
