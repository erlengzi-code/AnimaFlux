# AnimaFlux 追溯映射表（AD → 模块 → 契约测试）

> 用途：让「贴不贴文档」可验证。每一段代码都能指回文档哪一节，每一节文档都有对应实现与测试，防止凭感觉乱写、防止漏实现。
>
> 维护规则：
> - 写代码前先查本表，确认它实现的是哪条 AD；代码注释里挂 `# ref: v5.9 §X.Y`。
> - 每完成一个模块，把「状态」从 `待实现` 改成 `已实现`，并补上测试文件。
> - 新增 AD 受变更控制约束（见 CLAUDE.md），本表随之更新。

列说明：**阶段**=Roadmap 归属；**模块(计划)**=文档 §16A 约定的目标路径；**契约测试**=Architecture Regression 里的 invariant 或专项测试。

## 基础设施（P0–P4）

| AD / 文档章节 | 内容 | 模块(计划) | 契约测试 |
|---|---|---|---|
| §16A Python Project Structure | 目录与依赖边界 | `src/animaflux/**` | — |
| §11 Plugin Manifest+Lifecycle | 插件发现/生命周期 | `kernel/plugin_*` | `test_plugin_lifecycle` |
| §8 Hook | 生命周期钩子 | `kernel/hook.py` | `test_hook_cannot_bypass_ownership` |
| §10 Scheduler | 调度器 | `kernel/scheduler.py` | `test_scheduler_world_time` |
| §13 Runtime Context | ExecutionContext/StateView | `runtime/context.py` | `test_stateview_version_rule` |
| §12 Process Protocol | Process 调用模型 | `contracts/process.py` | `test_process_no_direct_state_mutation` |
| §9 Capability | 能力接口/Registry | `contracts/capability.py`, `kernel/capability_registry.py` | **test_capability_immutability** |
| §3 State Ownership | Owner 规则 | `contracts/state.py`, `runtime/resolver.py` | **test_owner_isolation** |
| §7 State Resolver | 裁决器/Resolution Round | `runtime/resolver.py` | test_resolver_order_independent |
| §14 State Store Core | 版本化状态存储 | `state/store.py` | **test_memory_versioning**(见 P7) |
| §15 Snapshot Strategy | Copy-on-Write | `state/snapshot.py` | test_cow_no_inplace_mutation |
| §16 Checkpoint+Persistence | Commit Journal/Checkpoint | `runtime/checkpoint.py` | test_checkpoint_refs_commit |
| §19 Tick Transaction | 事务协调器 | `runtime/transaction.py` | **test_transaction_rollback** |
| §18 Default Persistence Backend | SQLite 后端 | `persistence/sqlite.py` | test_sqlite_backend_contract |
| §22 Determinism+Random | RandomService/Random Stream | `kernel/random.py` | test_random_stream_reproducible |

## Core State（P5 / P8 / P9）

| AD / 文档章节 | 内容 | 模块(计划) | 契约测试 |
|---|---|---|---|
| §13N Identity | 生命身份 | `plugins/default_life/identity.py` | `tests/plugins/test_identity.py` |
| §13B Body | 身体/生理 | `plugins/default_life/body.py` | `tests/plugins/test_body.py` |
| §13D Emotion | 情绪/Mood | `plugins/default_life/emotion.py` | `tests/plugins/test_emotion.py` |
| §13E Drive | 驱力/需求 | `plugins/default_life/drive.py` | `tests/plugins/test_drive.py` |
| §13F Memory | 记忆(唯一 Specialized Store) | `memory/memory_store.py`, `contracts/memory.py` | **test_memory_versioning**, **test_knowledge_boundary**, `tests/memory/test_memory_store.py` |
| §13G Belief | 信念 | `plugins/default_life/belief.py` | `tests/plugins/test_belief.py` |
| §13I Goal | 目标 | `plugins/default_life/goal.py` | `tests/plugins/test_goal.py` |
| §13J Relationship | 关系 | `plugins/default_life/relationship.py` | `tests/plugins/test_relationship.py` |
| §13C Personality | 人格(Slow) | `plugins/default_life/personality.py` | `tests/plugins/test_personality.py` |
| §13H Value | 价值(Slow) | `plugins/default_life/value.py` | `tests/plugins/test_value.py` |
| §13K World Model | 世界模型 | `plugins/default_life/world_model.py` | `tests/plugins/test_world_model.py` |
| §13L Self Model | 自我模型 | `plugins/default_life/self_model.py` | `tests/plugins/test_self_model.py` |
| §13M Narrative | 人生叙事 | `plugins/default_life/narrative.py` | `tests/plugins/test_narrative.py` |

## Core Cognitive Process（P6 / P8 / P9）

| AD / 文档章节 | 内容 | 模块(计划) | 契约测试 |
|---|---|---|---|
| §14A Perception | 感知/主观 PerceivedEvent | `plugins/default_cognition/perception.py` | `tests/plugins/test_perception.py` |
| §14B Appraisal | 评估(不直接写 State) | `plugins/default_cognition/appraisal.py` | `tests/plugins/test_appraisal.py` |
| §14C Memory Retrieval | 检索/预算化 | `memory/retrieval.py` | test_retrieval_budget, `tests/memory/test_retrieval.py` |
| §14D Decision/Planning | 决策(四阶段) | `plugins/default_cognition/decision.py`, `contracts/decision.py` | `tests/plugins/test_decision.py` |
| §14E Communication | 交流/披露策略 | `plugins/default_cognition/communication.py`, `contracts/communication.py` | `tests/plugins/test_communication.py`, **test_knowledge_boundary** |
| §14F Reflection | 反思(Slow) | `plugins/default_cognition/reflection.py` | `tests/plugins/test_reflection.py` |

## 横切 / 集成（P6–P11）

| AD / 文档章节 | 内容 | 模块(计划) | 契约测试 |
|---|---|---|---|
| Cross-cutting Developmental Context | 年龄/阅历/DevelopmentContextView | `contracts/development.py`, `runtime/development.py` | **test_development_context**, **test_same_age_different_experience**, **test_different_age_same_experience**, **test_experience_not_competence_not_self_efficacy** |
| Cross-cutting Experience | 领域阅历/Derived Index | `memory/experience.py`, `contracts/experience.py` | `tests/memory/test_experience.py` |
| §16D.21 Schema Migration | 迁移边界/CompatibilityError | `persistence/migration.py` | `tests/persistence/test_migration.py` |
| §16D.22/23/31/33/34 Hardening | 插件/Provider 替换、No-LLM、Fuzz、长跑 | — | `tests/test_hardening.py` |
| §15B Default Life Loop | 标准 Tick 接线 | `runtime/lifeloop.py` | `tests/runtime/test_lifeloop.py` |
| §15A Core Dependency Map | 依赖方向 | 全模块 import 检查 | test_import_direction |
| §15D LLM Call Strategy | LLM 调用策略 | `llm/call_strategy.py` | **test_llm_retry_reuse**, `tests/llm/test_call_strategy.py` |
| §15C.11 LLM Provider | 远程 Provider（SiliconFlow, OpenAI-compatible） | `llm/providers.py` | `tests/llm/test_providers.py`（含 live smoke, 默认 skip） |
| §12C/§15B.17 External Action | 外部副作用 Journal/幂等 | `environment/action_journal.py`, `contracts/environment.py` | **test_external_action_idempotency**, `tests/environment/test_action_journal.py` |
| §21 Replay+Branch | 重放/分支/Restore | `runtime/replay.py`, `runtime/branch.py`, `runtime/restore.py`, `runtime/checkpoint.py` | **test_replay_exactness**, **test_branch_isolation**, `tests/runtime/test_replay.py`, `test_branch.py`, `test_restore.py` |
| §16C Public API | AnimaFlux/LifeHandle/send_text | `src/animaflux/api.py`, `contracts/turn.py` | `tests/test_api.py` |
| §16C.29 CLI | create/step/…/replay | `src/animaflux/cli/__init__.py` | `tests/test_api.py`（open/restore 语义） |
| §16E Official Demo | 主线 A + 主线 B | `src/animaflux/demo.py` | `tests/test_demo.py` |

## 长期保留的三条（文档 §19 / §16D.27）

| 测试 | 含义 | 阶段 |
|---|---|---|
| test_same_age_different_experience | 同年龄不同阅历 → 认知不同 | P7+ |
| test_different_age_same_experience | 同阅历不同年龄 → 认知不同 | P7+ |
| test_experience_not_competence_not_self_efficacy | 经验≠能力≠自我效能 | P7+ |
