# AnimaFlux / 灵演 — 设计规范与开发交接文档

> **持续维护版 · v0.1 架构冻结**
>
> 项目状态：`FROZEN FOR IMPLEMENTATION`
>
> 本文用于让新的开发 Agent 快速接手项目。完整细节以《AnimaFlux_技术架构设计规范_v5.9_FINAL.md》为准。

---

# 1. 项目定位

项目名称：

```text
AnimaFlux
中文：灵演
```

Tagline：

> **AnimaFlux — An Open Runtime for Evolving Digital Life**

Slogan：

> **让 AI 活着，而不只是回答。**
>
> **Let AI live, not just answer.**

核心公式：

```text
Agent
=
LLM
+ State
+ Dynamics
+ Memory
+ Environment
```

AnimaFlux 不是把一个超长角色 Prompt 包在 LLM 外面。

它的核心目标是：

```text
持续时间
持续状态
经历形成记忆
记忆影响未来
关系发生变化
目标与信念演化
形成自我与人生叙事
历史可恢复
人生可分支
行为可追溯
```

核心边界：

> **AnimaFlux models the life, not the universe.**
>
> **AnimaFlux 模拟生命本身，而不是模拟整个宇宙。**

外部世界通过 Environment Adapter 接入，不实现完整城市、经济、地图、战斗、物品或物理世界模拟。

---

# 2. Core State v1.0

正式冻结 13 个 Core State：

```text
1. Identity
2. Body
3. Personality
4. Emotion
5. Drive
6. Memory
7. Belief
8. Value
9. Goal
10. Relationship
11. World Model
12. Self Model
13. Narrative
```

核心边界：

```text
Identity
= 客观上我是谁

Body
= 客观身体 / 生理边界

Personality
= 长期稳定的反应倾向

Emotion
= 当前 / 近期情绪与 Mood

Drive
= 为什么产生行动动力

Memory
= 我主观记住了什么

Belief
= 我认为哪些命题是真的

Value
= 我认为哪些东西重要 / 值得 / 应该

Goal
= 我想让未来变成什么

Relationship
= 我对某个社会对象的长期主观关系状态

World Model
= 我如何结构化理解外部世界

Self Model
= 我认为自己是谁

Narrative
= 我如何解释自己的人生
```

关键区分：

```text
Objective Reality
≠
Perception
≠
Memory
≠
Belief
≠
World Model
≠
Narrative
```

以及：

```text
Drive = Why
Goal = What
Plan = How
Action = Do
```

---

# 3. Life Loop v0.1

标准 Tick：

```text
0. Tick Preparation
1. Environment / External Input Preparation
2. Body & Lifecycle Update
3. Event Collection
4. Perception
5. Memory Retrieval & Context Activation
6. Appraisal
7. Internal Dynamics
8. Goal Review & Decision
9. Action Intent / Output
10. Consequence Ingestion & Memory Formation
11. Reflection & Slow-State Update
12. Commit & Advance Time
```

规则：

```text
Tick(t, Δt)
Snapshot at tick start
Working State during resolution
Commit only after validation
Commit before Runtime Time advances
```

外部副作用不能被 SQLite rollback。

External Action / LLM 等非确定结果必须 Journal 化并支持技术 Retry 复用。

---

# 4. Kernel / Runtime

## Kernel

只负责机制：

```text
Time
Random
Plugin Manager
Capability Registry
Namespace Registry
Event Routing
Scheduler
```

Kernel 不理解：

```text
Emotion
Memory
Goal
Belief
Relationship
```

等具体生命语义。

## Runtime

负责：

```text
Life Loop
Execution Context
State Resolver
Transaction
Checkpoint
Replay
Branch
Failure Isolation
Trace
Input Journal
Development Context
Bootstrap
```

---

# 5. State Ownership

核心规则：

> **自己的状态自己解释；别人的状态只能提出影响；读取别人状态走公开能力；最终状态由内核统一提交。**

一个 State Namespace：

```text
exactly one active Primary Owner
```

非 Owner：

```text
不能直接写 State
```

跨模块改变：

```text
Influence
```

跨模块读取：

```text
Capability / immutable View
```

Owner：

```text
Current State
+ Influence Batch
→ Next State
```

StateOwner 默认：

```text
sync
deterministic
pure-ish
no DB
no LLM
no network
```

---

# 6. Event / Influence

Event：

```text
已经确认发生的客观 Runtime 事实
```

Event immutable。

修正：

```text
new correction / invalidation Event
```

Influence：

```text
一个模块向另一个 State 提出的语义影响
```

Influence 不是最终 State Delta。

流程：

```text
Event / Perception
→ Process
→ Influence
→ State Resolver
→ Owner
→ Next State
```

---

# 7. Capability

跨 Plugin 读取：

```text
Capability
```

原则：

> **依赖能力，不依赖实现。**

Capability 返回：

```text
immutable View / DTO
```

Plugin 不允许拿到：

```text
raw StateStore
DB
TransactionCoordinator
PluginManager internals
```

---

# 8. Core Cognitive Processes

冻结 6 个：

```text
Perception
Memory Retrieval
Appraisal
Decision / Planning
Communication
Reflection
```

它们都是 Process，不是新增 Core State。

---

# 9. Perception

定义：

> 从当前可以感知的信息中，决定这个生命真正注意到了什么，并形成主观 PerceivedEvent。

```text
External Reality
≠
Observation Opportunity
≠
PerceivedEvent
```

流程：

```text
Observation
→ Sensory Gate
→ Attention Selection
→ Perceptual Interpretation
→ PerceivedEventSet
```

Body：

```text
能不能感知
```

Perception：

```text
实际上感知 / 注意到了什么
```

不做内部完整光学、声学、3D 遮挡模拟。

---

# 10. Appraisal

定义：

> **不是“发生了什么”，而是“这件被我感知到的事，对我来说意味着什么”。**

可能使用：

```text
Goal
Value
Relationship
Memory
Belief
Self Model
Personality
Body
Drive
Development Context
```

输出结构化意义因素，而不是一个单一 Emotion Label。

Appraisal 不直接写：

```text
Emotion
Belief
Goal
Relationship
Self Model
```

只输出：

```text
AppraisalResult
+
target-specific Influence / Evidence
```

---

# 11. Memory

Memory 是：

```text
subjective persistent record
```

不是 Event Log。

类型：

```text
Episodic
Semantic
Procedural
Autobiographical
```

规则：

```text
Event ≠ Memory
Retrieval ≠ Reconsolidation
Forgetting ≠ Delete
```

Memory Retrieval 永远是预算化选择，不把全部人生塞给 LLM。

---

# 12. Communication

AnimaFlux 有正式交流能力。

交流不是：

```text
user message
→ LLM
→ reply
```

而是：

```text
External Communication
→ Observation
→ Perception
→ Retrieval
→ Appraisal
→ Emotion / Drive / Goal / Relationship
→ Decision
→ CommunicativeIntent
→ Language Realization
→ Validation
→ External Action
```

所以交流会真实影响：

```text
Memory
Relationship
Belief
Emotion
Goal
Narrative
```

Communication LLM 只能表达已经确定的 Intent / Allowed Claims。

它不能：

```text
偷偷撒谎
泄露秘密
增加 Agent 不知道的事实
```

---

# 13. Developmental Context：年龄与阅历

正式规则：

```text
Age
≠ Experience
≠ Skill
≠ Self-Efficacy
```

Chronological Age：

```text
Identity.birth_time + Runtime Time
```

Biological Age / Maturity：

```text
Body
```

Life Stage：

```text
Derived View / replaceable LifeStagePolicy
```

Experience：

```text
Domain-specific
```

不设计：

```text
agent.experience_level
maturity = 76%
```

例如：

```text
social.conflict
public_speaking
research
career_interview
relationship.long_term
life.loss
```

各自不同。

DevelopmentContextView 组合：

```text
Chronological Age
Biological Maturity
Life Stage
Relevant Domain Experience
Role
Major Transition
```

不同 Owner / Process 自己解释 Development Context。

禁止全局：

```text
age_multiplier
```

阅历真正影响：

```text
Novelty
Familiarity
Coping
Uncertainty
Candidate Generation
Fast Path
Decision Depth
Memory Retrieval relevance
Reflection evidence richness
```

经验多并不保证更正确、更成熟或更冷静。

---

# 14. LLM Strategy

LLM：

```text
Cognitive Capability
≠ Agent
```

原则：

```text
Runtime orchestrates cognition
LLM handles complex semantics
Code owns rules / permission / state / transaction
```

禁止依赖 LLM 保证：

```text
Clock
Random
Permission
State Ownership
Resolver
Transaction
Commit
Replay correctness
```

调用前：

```text
LLMNeedAssessment
```

考虑：

```text
semantic complexity
uncertainty
significance
domain familiarity
experience
budget
```

LLM 使用：

```text
process-specific minimal context
```

不存在：

```text
Universal Full Agent Context
```

默认：

```text
Structured Output
Source Refs
Schema Validation
Semantic Validation
```

Prompt / Model / Context / Result 全版本化、可追踪。

Exact Replay：

```text
never calls historical LLM again
```

直接使用历史 validated result。

---

# 15. Persistence

官方 v0.1：

```text
SQLite
```

Core State：

```text
Namespace
+ optional entity_key
+ Immutable State Version
+ JSON Payload
```

核心表：

```text
life_agent
runtime_instance
life_branch

state_version
state_current

tick_attempt
commit_journal
commit_state_ref
checkpoint

event_log
input_journal

memory_entry
memory_version
memory_runtime_state

scheduled_task
deferred_influence

llm_call
artifact

causal_node
causal_edge
failure_record
```

核心原则：

```text
State 不覆盖，只出新版本
Copy-on-Write
Current Pointer 独立
Checkpoint 引用 Commit
Branch 不复制历史
```

Memory 是 v0.1 唯一强制 Specialized Store。

Vector Index / Experience Index：

```text
Derived
Rebuildable
not source of truth
```

---

# 16. Replay / Branch

三种语义严格区分：

```text
RESTORE
= 从历史状态继续原生命

REPLAY
= 只读重放已经发生的历史

RESIMULATE / BRANCH
= 从过去产生新的未来
```

Exact Replay：

```text
no LLM call
no environment call
no new state
no new event
no new memory
```

Branch：

```text
shared pre-fork history
independent post-fork evolution
```

---

# 17. Public API

普通使用者主要看到：

```text
AnimaFlux
LifeHandle
```

核心操作：

```text
create_life
open_life
step
advance
observe
send_text
inspect
checkpoint
restore
branch
replay
pause
resume
```

禁止：

```text
set_state
direct owner call
direct resolver call
raw DB mutation
set_time
```

`send_text()` 必须完整经过 Cognition，不能等价于 `llm.chat()`。

---

# 18. Python Project Structure

推荐：

```text
src/animaflux/
├── contracts/
├── kernel/
├── runtime/
├── state/
├── plugins/
│   ├── default_life/
│   └── default_cognition/
├── persistence/
├── llm/
├── environment/
├── observability/
├── config/
└── cli/
```

关键依赖：

```text
Default Plugin → Framework Contract

Framework Core ↛ Default Plugin Internal Schema
```

内部对象优先：

```text
dataclass
Protocol
Enum
composition
```

配置 / 外部输入 / LLM Structured Output 可使用 Pydantic。

AnimaFlux Core Runtime 自己实现，不以 LangChain / LangGraph 作为 Runtime 主体。

---

# 19. Testing

测试五层：

```text
Unit
Contract
Integration
Replay / Branch
Scenario / Life
```

Invariant Test 横穿所有层。

最重要 Architecture Regression：

```text
Owner isolation
Capability immutability
Transaction rollback
Replay exactness
Branch isolation
Knowledge boundary
LLM retry reuse
External action idempotency
Memory versioning
Development Context
```

必须长期保留：

```text
Same Age, Different Experience
Different Age, Same Relevant Experience
Experience ≠ Competence ≠ Self-Efficacy
```

Scenario Test 不要求唯一心理答案。

---

# 20. Official v0.1 Demo

只做：

```text
Single Deep Digital Life
+
Human User
+
Minimal Scenario Environment
```

主线 A：

```text
第一次公开汇报
→ Experience / Memory / Self-Efficacy
→ 时间推进
→ 后续类似汇报
→ 同一个人因阅历不同产生不同认知
```

主线 B：

```text
重要关系对象可能离开
→ Relationship / Appraisal / Emotion / Goal / Communication
→ Checkpoint
→ Branch A / Branch B
→ 不同长期未来
```

必须展示：

```text
process restart persistence
selective memory
“不记得”
“不知道”
Causal Why
Exact Replay
```

---

# 21. Frontend Presentation v0.1

前端定位：

> **Life Observatory / 数字生命观察舱**

不是传统后台，也不是纯聊天页。

视觉：

```text
Dark
Minimal
Scientific
Alive
Calm
```

主导航：

```text
Life
Talk
Timeline
Mind
Branches
```

## Life

展示：

```text
Life Name
ALIVE
Life Time
Age
Life Stage
Role
Mood
Focus
Energy / Fatigue
Drive
Goal
Important Relationship
Relevant Memory
Development
Recent Events
```

可以使用抽象 Life Orb：

```text
ALIVE → slow breathing
PAUSED → still
DEAD → dark
```

## Talk

不是单纯聊天窗口。

布局：

```text
Conversation
+
Current Life Context
```

重要回复旁提供：

```text
Why ↗
```

## Timeline

纵向人生时间线。

点击事件展开：

```text
what happened
what was perceived
relevant memories
appraisal
state effects
decision / consequence
```

## Mind

分组：

```text
STABLE SELF
Identity / Personality / Value / Self Model / Narrative

ACTIVE MIND
Emotion / Drive / Belief / Goal

LIFE CONTEXT
Body / Memory / Relationship / World Model
```

## Branches

树状人生分叉：

```text
Genesis
↓
Checkpoint
↙       ↘
Main     Alternative
```

支持 Branch Compare。

## Development

只显示：

```text
Age
Life Stage
Roles
Domain Experience:
Exposure / Practice / Diversity / Recency
```

禁止：

```text
Maturity 80%
Experience Level 9
```

## Research Mode

增加：

```text
Tick ID
State Version
Source Refs
Confidence
Appraisal factors
LLM Call ID
Plugin
```

普通 Life View 保持人类可读。

前端展示层不得直接修改 Core State。

---

# 22. Implementation Roadmap

正式顺序：

```text
P0 Project Skeleton
P1 Core Contracts
P2 Kernel
P3 State Runtime
P4 SQLite Transaction
P5 Identity + Body + Emotion
P6 Perception + Appraisal
P7 Memory + Experience
P8 Drive + Belief + Goal + Relationship + Decision + Communication
P9 Personality + Value + World Model + Self Model + Narrative + Reflection
P10 Checkpoint + Replay + Branch
P11 Public API + CLI + Official Demo
P12 Hardening + v0.1 Release
```

硬 Gate：

```text
P3
P4
P7
P10
```

外部 Provider：

```text
Mock / Fake first
Real provider later
```

不要过早优化。

---

# 23. v0.1 明确不做

```text
Full World Simulator
AI Town
Massive Multi-Agent Scaling
Microservices
Redis
Kafka
Distributed Runtime
Mandatory Graph DB
Mandatory External Vector DB
Plugin Marketplace
Hot Plugin Replacement
Web Product Platform
Autonomous Infinite Life Daemon
Open-ended LLM Tool Loop
```

这些默认：

```text
v0.2+
```

---

# 24. 开发 Agent 接手规则

新的开发 Agent 必须遵守：

1. 完整技术细节以 `AnimaFlux_技术架构设计规范_v5.9_FINAL.md` 为准。
2. 当前架构已经冻结，不继续增加 Core State / Core Cognitive Process。
3. 新功能默认进入 v0.2 backlog。
4. 只有真实编码证明当前设计存在技术冲突时才修改架构。
5. 从 P0/P1 开始，按 Roadmap 实现。
6. 每阶段必须可运行、可测试。
7. 先 Mock Boundary，再接真实 LLM / Environment。
8. 不为了快速 Demo 绕过 Owner / Influence / Transaction / Memory / Knowledge Boundary。
9. 不使用完整聊天 Transcript 当作“记忆系统”。
10. 不把 LLM 重新变成 Runtime 主控。

---

# 25. Final Status

```text
Project:
AnimaFlux / 灵演

Architecture:
v0.1

Status:
FROZEN FOR IMPLEMENTATION

Next Work:
P0 → P1
```

从现在开始：

> **只填完当前已经确定的 AnimaFlux 边界，不再扩边界。**
