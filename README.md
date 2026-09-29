<div align="center">

# AnimaFlux / 灵演

**An Open Runtime for Evolving Digital Life**

*让 AI 活着，而不只是回答。* · *Let AI live, not just answer.*

Python 3.10+ · v0.1.0 · 300 passed / 1 skipped

</div>

---

## 这是什么

AnimaFlux 不是把一长串角色 Prompt 包在 LLM 外面。它是一个**会演化的数字生命运行时**：生命拥有持续的状态，会把经历沉淀成记忆、让记忆反过来影响未来，关系会变化，目标与信念会演化，并最终形成自我与人生叙事。

```
Agent = LLM + State + Dynamics + Memory + Environment
```

核心边界：**AnimaFlux models the life, not the universe.**（模拟生命本身，而不是整个宇宙。）外部世界通过 Environment Adapter 接入，不实现完整城市 / 经济 / 战斗 / 物理模拟。

## 核心概念

### 13 个 Core State（已冻结）

| 分组 | State |
| --- | --- |
| 稳定自我 | Identity · Personality · Value · Self Model · Narrative |
| 活跃心智 | Emotion · Drive · Belief · Goal |
| 生命上下文 | Body · Memory · Relationship · World Model |

### 6 个 Cognitive Process（已冻结）

`Perception` · `Memory Retrieval` · `Appraisal` · `Decision-Planning` · `Communication` · `Reflection`

### 关键边界

- **自己的状态自己解释，别人的状态只能提出影响（Influence）。** 一个 State Namespace 恰好一个 Primary Owner；非 Owner 不能直接写 State。
- **跨模块读取走 Capability（immutable View），不碰内部实现。**
- **知识边界严格可测**：`Objective Reality ≠ Perception ≠ Memory ≠ Belief ≠ World Model ≠ Narrative`；「不知道」≠「不记得」。
- **LLM = Cognitive Capability，不是 Agent。** 代码 owns 规则 / 权限 / 状态所有权 / 事务 / Replay 正确性；LLM 只做复杂语义；**Deterministic First**，默认零 LLM 也能运行。
- **State 只新增版本、不覆盖（Copy-on-Write）**；Checkpoint 引用 Commit；Branch 不复制历史。
- **三种时间语义严格区分**：`RESTORE`（续命）/ `REPLAY`（只读重放，零 LLM 调用）/ `BRANCH`（从过去产生新未来）。

## 特性（v0.1）

- ✅ 13 Core State + 6 Cognitive Process 全落地
- ✅ 标准 Life Loop（Tick 12 步）
- ✅ SQLite + InMemory 双后端，Copy-on-Write + Commit Journal + Current Pointer
- ✅ Memory 作为唯一强制 Specialized Store（Episodic / Semantic / Procedural / Autobiographical）
- ✅ 精确重放 / 人生分支 / 恢复
- ✅ 公开 API（`AnimaFlux` / `LifeHandle`）+ CLI + 本地 Web Console
- ✅ 可选 LLM Provider（SiliconFlow，OpenAI-compatible；默认确定性模板）
- ✅ 300+ 测试，含 13 条 Architecture Regression

## 安装

需要 Python >= 3.10。

```bash
# 只装核心（CLI + Python API，仅依赖 pydantic）
pip install -e .

# 含 Web Console
pip install -e ".[web]"

# 含测试工具
pip install -e ".[dev]"
```

## 快速开始

### CLI

```bash
python -m animaflux --version                 # animaflux 0.1.0

python -m animaflux create --name 小林 --values growth care
python -m animaflux step --seconds 3600
python -m animaflux observe --text "你的第一次公开演讲下周举行"
python -m animaflux status                    # 当前 Committed 状态摘要
python -m animaflux inspect --namespace emotion
python -m animaflux checkpoint
python -m animaflux branch --name 平行人生
python -m animaflux replay                    # 只读回放 Commit Journal
```

### Python API

```python
from datetime import datetime
from animaflux.api import AnimaFlux, CharacterBootstrap

flux = AnimaFlux()
handle = flux.create_life(
    "my-life",
    bootstrap=CharacterBootstrap(primary_name="小林", values=("growth", "care")),
    start_time=datetime(2000, 1, 1),
)

handle.observe_text("You have an exciting opportunity: give your first talk in one week.")
for _ in range(6):
    handle.advance(86400.0)
    handle.act()

handle.checkpoint()
```

`send_text()` 完整经过 Cognition，不等价于 `llm.chat()`。

### Web Console（数字生命观察舱）

```bash
python -m animaflux web --open
# 或 Windows 下双击 start_web.bat
```

打开 http://127.0.0.1:8000 —— 五大视图：**Life / Talk / Timeline / Mind / Branches**。

### 官方 Demo

```bash
python -m animaflux.demo
```

- **主线 A**：多日成长年 —— 演讲 → 阅历增长（self-efficacy）
- **主线 B**：关系转折 + 人生分支
- **主线 C**：同一世界，四条生命，四种死法

## 测试

```bash
pytest
# 300 passed, 1 skipped（唯一 skip = 真实 LLM 在线 smoke，需 ANIMAFLUX_SILICONFLOW_API_KEY opt-in）
```

- 分层：Unit / Contract / Integration / Replay-Branch / Scenario-Life
- **13 条 Architecture Regression**：Owner isolation · Capability immutability · Transaction rollback · Replay exactness · Branch isolation · Knowledge boundary · LLM retry reuse · External action idempotency · Memory versioning · Development Context …
- 长期保留测试：Same Age / Different Experience · Different Age / Same Experience · Experience ≠ Competence ≠ Self-Efficacy

## 架构与文档

| 文档 | 内容 |
| --- | --- |
| [设计规范·持续维护版](AnimaFlux_设计规范_持续维护版_FINAL.md) | 速查摘要（接手速读） |
| [技术架构设计规范 v5.9](AnimaFlux_技术架构设计规范_v5.9_FINAL.md) | 完整技术细节（权威） |
| [Gate 清单](GATES.md) | P0–P12 阶段验收 |
| [追溯映射](TRACEABILITY.md) | AD → 模块 → 契约测试 |
| [功能测试报告](FUNCTIONAL_TEST_REPORT.md) | 20 个端到端「生命切片」场景 |
| [Web Plan](AnimaFlux_WEB_PLAN_v0.2_FINAL.md) | Web Console 设计 |

## 路线图

P0–P12 已完成，**v0.1 达成**（FROZEN FOR IMPLEMENTATION）。硬 Gate：P3 / P4 / P7 / P10。

```
P0 Project Skeleton        P6 Perception & Appraisal
P1 Core Contracts          P7 Memory & Experience      ★Gate
P2 Kernel                  P8 Motivation & Social
P3 State Runtime    ★Gate  P9 Slow Self Development
P4 SQLite Transaction ★Gate P10 Replay & Branch         ★Gate
P5 First Life Slice        P11 Public API / CLI / Demo
                           P12 Hardening & v0.1 Release
```

## 目录结构

```
src/animaflux/
├── contracts/            # 框架契约（Protocol / dataclass / Enum）
├── kernel/               # 机制内核（Time / Random / Plugin / Scheduler）
├── runtime/              # 生命周期（Resolver / Transaction / Replay / Branch）
├── state/                # 版本化状态存储
├── plugins/
│   ├── default_life/         # 12 个 Core State Owner
│   └── default_cognition/    # 6 个 Cognitive Process
├── memory/               # 唯一强制 Specialized Store
├── persistence/          # SQLite + InMemory 双后端
├── llm/                  # 可选 Provider / Call Strategy
├── environment/          # Environment Adapter / Scenario
├── web/                  # 本地 Web Console
└── cli/                  # 命令行
```

## License

[MIT](LICENSE) © 2026 erlengzi-code
