# AnimaFlux / 灵演 — 开发约束（项目级）

> 本文件是**硬约束**，每次开发自动加载。完整技术细节以
> `AnimaFlux_技术架构设计规范_v5.9_FINAL.md` 为准；`AnimaFlux_设计规范_持续维护版_FINAL.md` 是速查摘要。

## 项目状态

- 架构：**v0.1，FROZEN FOR IMPLEMENTATION**（只实现，不扩边界）
- 定位：AnimaFlux models the **life**, not the universe（模拟生命本身，不模拟宇宙）
- 当前任务：P0 → P1 起，按 Roadmap 推进

## 冻结铁律（不可违反，除非「真实编码证明冲突」）

### 状态模型
- 13 个 Core State 已冻结：Identity / Body / Personality / Emotion / Drive / Memory / Belief / Value / Goal / Relationship / World Model / Self Model / Narrative。**不再新增。**
- 6 个 Core Cognitive Process 已冻结：Perception / Memory Retrieval / Appraisal / Decision-Planning / Communication / Reflection。**不再新增。**

### 所有权与数据流
- **自己的状态自己解释；别人的状态只能提出影响；读取走公开能力；最终由内核统一提交。**
- 一个 State Namespace 恰好一个 active Primary Owner；非 Owner 不能直接写 State。
- 跨模块改变 = **Influence**（不是 State Delta）；跨模块读取 = **Capability**（immutable View / DTO）。
- 流程固定：`Event/Perception → Process → Influence → State Resolver → Owner → Next State`。
- Plugin 拿不到 raw StateStore / DB / TransactionCoordinator / PluginManager internals。

### 知识边界（最重要）
- `Objective Reality ≠ Perception ≠ Memory ≠ Belief ≠ World Model ≠ Narrative`
- `Event ≠ Memory`；`Retrieval ≠ Reconsolidation`；`Forgetting ≠ Delete`。
- 「不知道」≠「不记得」：Agent 的 Knowledge Boundary 必须严格可测。

### LLM 策略
- LLM = Cognitive Capability，**不是 Agent / 不是 Runtime 主控**。
- **代码 owns：规则 / 权限 / 状态所有权 / Resolver / 事务 / Commit / Replay 正确性**。禁止依赖 LLM 保证这些。
- **Deterministic First**；LLM 调用前走 `LLMNeedAssessment`；process-specific minimal context，禁止 Universal Full Agent Context。
- **Exact Replay 永不回拨历史 LLM**，直接用已验证的历史结果。
- 禁止用完整聊天 Transcript 当「记忆系统」。

### 持久化
- 官方 v0.1 后端 = **SQLite**；Core State = Namespace + entity_key + Immutable Version + JSON Payload。
- **State 不覆盖，只出新版本（Copy-on-Write）**；Checkpoint 引用 Commit；Branch 不复制历史。
- Memory 是 v0.1 唯一强制 Specialized Store；Vector/Experience Index 是 Derived、可重建、非 source of truth。

### 工程纪律
- **Mock / Fake 先于真实 provider**（LLM、Environment、Embedding 先 fake）。
- 不为了快速 Demo 绕过 Owner / Influence / Transaction / Memory / Knowledge Boundary。
- 不引入微服务 / Redis / Kafka / 分布式 / 图数据库 / 外部向量库。
- 不要过早优化；每阶段必须可运行、可测试。

## Roadmap（P0 → P12）

```
P0  Project Skeleton           P6  Perception & Appraisal
P1  Core Contracts             P7  Memory & Experience      ★Gate
P2  Kernel                     P8  Motivation & Social Cognition
P3  State Runtime      ★Gate   P9  Slow Self Development
P4  SQLite Transaction ★Gate   P10 Replay & Branch          ★Gate
P5  First Life Slice           P11 Public API / CLI / Demo
                               P12 Hardening & v0.1 Release
```

- **硬 Gate：P3 / P4 / P7 / P10**，过 Gate 前跑 Architecture Regression。
- 里程碑：Runtime Lives → Persistent Life → Cognitive Life → Evolving Life。

## Architecture Regression（必须长期保留，随 P1–P4 逐步填充）

```
Owner isolation · Capability immutability · Transaction rollback
Replay exactness · Branch isolation · Knowledge boundary
LLM retry reuse · External action idempotency
Memory versioning · Development Context
```

另需长期保留测试：Same Age / Different Experience；Different Age / Same Relevant Experience；Experience ≠ Competence ≠ Self-Efficacy。

## 变更控制

- 架构单向冻结：**只有真实编码证明当前设计存在技术冲突时才改架构**，不因「实现麻烦」改。
- 新功能默认进 v0.2 backlog；不继续增加 Core State / Process。
- 任何对文档的偏离必须留一条记录：指向被推翻的文档章节 + 冲突证据。
