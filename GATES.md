# AnimaFlux 阶段 Gate 清单（P0 → P12）

> 用途：让「每一阶段做对没有 / 做全没有」可验证。对应文档 §16F.4（阶段 Gate）与 §16F.8（Completion Definition）。
>
> 使用方式：
> 1. **开工前**：精读「开工前读」列出的章节，把该阶段要实现的 AD 逐条拆成 TODO。
> 2. **完工后**：对照「验收清单」逐条打勾。
> 3. **过 Gate**：带 ★ 的阶段（P3/P4/P7/P10）必须全勾 + `pytest tests/architecture/` 对应 invariant 绿，否则不进下一阶段。
> 4. 详细条目在每阶段开工时从对应 AD 章节补全（本文件是模板，不是最终穷举）。

---

## P0 — Project Skeleton
**开工前读**：§16A（Python Project Structure）、§16A.29（最终原则）

- [x] 建立 `src/animaflux/` 目录结构（§16A.2）
- [x] 依赖配置（dataclass/Protocol/Enum 优先，Pydantic 仅用于配置/LLM 输出）
- [x] 空包可 import、空 CLI 可运行（`python -m animaflux --version` → `animaflux 0.1.0`）
- [x] `pytest` 可跑（13 collected / 13 skipped / 0 fail）

## P1 — Core Contracts
**开工前读**：§3/§6/§9/§12/§13（各契约 AD）、§16A.3（Contracts Layer）

- [x] `contracts/` 层 Protocol / dataclass / Enum 齐备
- [x] Event / Influence / Capability / Process / State 契约对齐文档结构
- [x] 依赖方向：Default Plugin → Framework Contract（§16A.21）
- [x] Architecture Regression 测试文件可被 pytest 收集（13 skip 占位）

## P2 — Kernel
**开工前读**：§2（Kernel 边界）、§8/§10/§11（Hook/Scheduler/Plugin）、§9.7（Capability Registry）

- [x] Time / Random / Plugin Manager / Capability Registry / Namespace Registry / Event Routing / Scheduler
- [x] Kernel 不理解生命语义（Emotion/Memory/Goal…），只负责机制
- [x] RandomService 可复现（§22）

## P3 — State Runtime ★Gate
**开工前读**：§3/§6/§7/§14/§15（Owner/Influence/Resolver/State Store/Snapshot）、§16D.3

- [x] State Owner 规则：一个 Namespace 一个 Primary Owner
- [x] Influence Buffer + Resolution Round + Deferred Influence
- [x] Resolver 与 Owner 职责分离；到达顺序不影响业务结果（§7.6）
- [x] Working State / Copy-on-Write 快照
- [x] **invariant 激活：`test_owner_isolation`、`test_capability_immutability` 绿**

## P4 — SQLite Transaction ★Gate
**开工前读**：§16/§17/§18/§19/§20（Persistence/Transaction）、§16B（Schema）

- [x] Copy-on-Write：State 出新版本不覆盖（§16B.3）
- [x] Commit Journal 落盘（§16B.5）；Current Pointer 最后更新（§19.8）
- [x] Tick 失败 → Rollback，不留 committed version（§19.10 / Crash Recovery）
- [x] SQLite 后端 + InMemory 后端（§18.3）
- [x] **invariant 激活：`test_transaction_rollback` 绿**

## P5 — First Life Slice（Identity + Body + Emotion）
**开工前读**：§13N/§13B/§13D、Cross-cutting Developmental Context

- [x] Identity：Runtime Identity 与 Life Identity 分离（§13N.1）
- [x] Body：七个核心区域 + 多时间尺度（§13B）
- [x] Emotion：Episode/Mood 分离，多情绪共存（§13D）
- [x] 最小可运行 Life Loop 切片（能 step/advance）

## P6 — Perception & Appraisal
**开工前读**：§14A/§14B、§31/§32（Environment 输入）

- [x] Perception：Sensory Gate → Attention → Interpretation → PerceivedEvent
- [x] 客观 Event ≠ 主观 Perception；支持 Misperception（§14A.5）
- [x] Appraisal 只输出 AppraisalResult + Influence，不直接写 Emotion/Belief/Goal（§14B.9）

## P7 — Memory & Experience ★Gate
**开工前读**：§13F/§14C、§16B.12–16B.15（Memory Store）、Cross-cutting Experience

- [x] Memory Specialized Store（v0.1 唯一强制）
- [x] Memory 类型：Episodic/Semantic/Procedural/Autobiographical
- [x] Retrieval 预算化；Forgetting ≠ Delete；Reconsolidation 出新版本
- [x] Vector/Experience Index = Derived、可重建（非 source of truth）
- [x] **invariant 激活：`test_memory_versioning`、`test_knowledge_boundary` 绿**
- [x] 三条长期测试骨架就位（§16D.27）

## P8 — Motivation & Social Cognition
**开工前读**：§13E/§13G/§13I/§13J、§14D/§14E

- [x] Drive（Need/Dive 分离）、Belief（Evidence-driven）、Goal（Hierarchy/Review）、Relationship（Directional）
- [x] Decision 四阶段（Framing/Candidate/Evaluation/Commit）
- [x] Communication：CommunicativeIntent ≠ Utterance；Disclosure Policy；LLM 无自主撒谎权限（§14E.7）

## P9 — Slow Self Development
**开工前读**：§13C/§13H/§13K/§13L/§13M、§14F

- [x] Personality（Bounded Change）、Value、World Model、Self Model、Narrative
- [x] Reflection：只产出 Proposal/Evidence，不直接改 Slow State（§14F.4）
- [x] Narrative 带 Provenance/Versioning

## P10 — Replay & Branch ★Gate
**开工前读**：§21/§22/§16C.13–16C.17

- [x] RESTORE / REPLAY / RESIMULATE-BRANCH 三种语义严格区分（§21）
- [x] Exact Replay：no LLM / no env / no new state/event/memory
- [x] Branch 共享 pre-fork 历史、独立 post-fork
- [x] **invariant 激活：`test_replay_exactness`、`test_branch_isolation` 绿**

## P11 — Public API / CLI / Official Demo
**开工前读**：§16C/§16E/§16B.43

- [x] `AnimaFlux` / `LifeHandle` 公开 API；`send_text()` 完整过 Cognition
- [x] CLI 可 create/step/advance/observe/checkpoint/restore/branch/replay
- [x] 官方 Demo：主线 A（阅历成长）+ 主线 B（关系转折/分支）
- [x] **invariant 激活：`test_llm_retry_reuse`、`test_external_action_idempotency` 绿**

## P12 — Hardening & v0.1 Release
**开工前读**：§16D（Testing Strategy 全量）、§20（Retention/GC）

- [x] 10 + 3 条 Architecture Regression 全部激活且绿
- [x] 迁移 / 插件替换 / Provider 替换测试齐备（§16D.21–16D.23）
- [x] 长期运行 / 性能 / Fuzz（§16D.33–16D.34）
- [x] v0.1 Release 判定（§16F.8 Completion Definition 全满足）

---

## Gate 总览

| Gate | 阶段 | 过 Gate 前置 |
|---|---|---|
| ★ | P3 | owner_isolation + capability_immutability 绿 |
| ★ | P4 | transaction_rollback 绿 |
| ★ | P7 | memory_versioning + knowledge_boundary 绿 |
| ★ | P10 | replay_exactness + branch_isolation 绿 |

---

## v0.1 Release 判定（§16F.8 Completion Definition）

- 13 Core State（Identity/Body/Personality/Emotion/Drive/Memory/Belief/Value/Goal/Relationship/WorldModel/SelfModel/Narrative）Owner 全部落地（Default Life 插件 12 个 + Memory Specialized Store）。
- 6 Core Cognitive Process（Perception/Appraisal/MemoryRetrieval/Decision/Communication/Reflection）落地，均为确定性优先、不直接写 State。
- Runtime Wiring（LifeRuntime + Resolver + Transaction Coordinator + Checkpoint/Replay/Branch/Restore）完成。
- Persistence：SQLite + InMemory 双后端，Copy-on-Write + Commit Journal + Current Pointer 最后更新。
- Public API（AnimaFlux / LifeHandle / send_text 完整 Cognition）、CLI、官方 Demo（主线 A + B）落地。
- Testing：Architecture Regression 13 条全部激活且绿；全量测试 `276 passed / 1 skipped`（唯一 skip = 真实 LLM live smoke，需 `ANIMAFLUX_SILICONFLOW_API_KEY` opt-in）。

v0.1 冻结架构已实现并验证，无新增概念子系统。后续 Real LLM Provider / Vector Retrieval / 前端展示属于 SHOULD/LATER（§16F.9）。

### v0.2 可选 LLM Provider（默认关闭，不改变 v0.1 确定性默认）

- `SiliconFlowProvider`（`llm/providers.py`，OpenAI-compatible，纯 stdlib urllib）实现 `LLMProvider` Protocol，作为可选 Cognitive Capability 接入 `send_text` 的 language realization（§15D.3）。
- 默认（未配置）仍走确定性模板（Deterministic First）；Provider 失败自动回退（§15D.23）；withhold/redirect/vague 等隐瞒类意图一律确定性模板，不经 LLM（§14E.5）。
- Exact Replay 仍零 LLM 调用（§21.2）。API Key 从环境变量 `ANIMAFLUX_SILICONFLOW_API_KEY` 读取，不硬编码。
