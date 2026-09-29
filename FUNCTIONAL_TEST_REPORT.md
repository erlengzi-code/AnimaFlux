# AnimaFlux 功能测试报告（Functional Test Report）

> 测试套件：`tests/functional/` · 运行日期：2026-09-27 · 结果：**20 passed / 0 failed**

## 一、套件约束（用户约定，已落地）

| 约束 | 落实方式 |
| --- | --- |
| 只走公开 API | 全部经 `AnimaFlux` / `LifeHandle` / `LifeBranchHandle`，不 import `StateStore` / `StateResolver` / `TransactionCoordinator` / `PluginManager` 内部 |
| scripted-fake LLM 场景 | `conftest.py` 的 `_ScriptedProvider` + `scripted_llm` fixture，确定性替身验证「LLM 只是 Cognitive Capability」（§15D） |
| 独立目录 | `tests/functional/`，与单元/架构回归测试分离 |
| 聚焦 Python API 层 | 不涉及 Web / CLI / 跨进程；跨模块事件用公开 `step(extra_influences=...)` 注入（与官方 `demo.py` 同构） |

## 二、测试维度 → 覆盖状态 / 认知过程 → 结果

### ① 生命切片与情绪（`test_life_slice.py`）— 3 通过

| 场景 | 覆盖 State / Process | 断言 |
| --- | --- | --- |
| 初生 | Identity / Value / Emotion + 全 13 State 概览 | 12 Core State seed、MEMORY 为 Specialized Store 不 seed；情绪中性、零记忆/信念/关系/目标 |
| 惊魂一日 | Perception→Appraisal→Emotion | threat→fear（负 valence）落地，mood 被拉低；600s 半衰期后强度衰减但 episode 仍在 |
| 身体的流逝 | Body（Homeostasis / Sleep） | `advance(3600)` → energy 下降、fatigue 累积，概览同步反映 |

### ② 认知闭环与知识边界（`test_cognition_boundary.py`）— 4 通过

| 场景 | 覆盖 State / Process | 断言 |
| --- | --- | --- |
| 完整认知闭环 | Perception→Retrieval→Appraisal→Emotion/Drive/Goal/Relationship→Decision→Communication | threat→fear + safety 需要 + 提议目标（Proposal≠Active）+ 关系 first_impression + 回应 |
| 知识边界（不知道） | Memory（Formation / Retrieval） | 从未感知「皇帝遇刺」→ 检索结果不含该事实；真实「danger」可检索（FOUND） |
| 忘了≠删了 | Memory（Accessibility 门控） | `min_accessibility` 门控下检索不到，但 `memories()` 仍在（Stored ≠ Retrievable） |
| 同输入不同时点不同评价 | Appraisal + SelfModel（self-efficacy） | 首次演讲恐惧 → 获得 self-efficacy → 同类成功为 joy；自我效能领域特定、≠ 全局自尊 |

### ③ 动机与社会认知（`test_motivation_social.py`）— 2 通过

| 场景 | 覆盖 State / Process | 断言 |
| --- | --- | --- |
| 交朋友 | Relationship | first_impression → trust 增长被 bounded（慢维度单步上限），首次实质更新脱离 first_impression |
| 从证据到信念 | Belief | 显著观察 → 有感知证据支撑的信念（非空穴来风） |

### ④ 慢自我发展（`test_slow_development.py`）— 4 通过

| 场景 | 覆盖 State / Process | 断言 |
| --- | --- | --- |
| 复盘人生 | Reflection→Narrative/Personality/SelfModel | 反复威胁 → 沉淀 narrative theme（带 provenance）+ emotional_reactivity 微升（bounded）+ self_esteem 微降（bounded） |
| 证据不足不变 | Reflection（低频） | 1 条威胁不反思，慢状态不变 |
| 显式反思 | Reflection（force） | `reflect_now()` 在阈值以下也能沉淀 |
| 反复失去 | Reflection→Value | 反复失去 → 形成/强化 `stability` 价值承诺 |

### ⑤ 持久化与时间线（`test_persistence_timeline.py`）— 4 通过

| 场景 | 覆盖 State / Process | 断言 |
| --- | --- | --- |
| 一生可保存 | Checkpoint | 快照 State + Version Map |
| 一生可回放 | Replay | `timeline()` 只读，不产生新状态版本 |
| 未走的路 | Branch（fork） | post-fork 分叉（affection / resentment 各自演化），pre-fork 共享（trust 不变） |
| 续命 | Restore / Open | 同一生命经 Restore 与 Open 均可继续演化 |

### ⑥ scripted-fake LLM 场景（`test_llm_cognition.py`）— 3 通过

| 场景 | 覆盖 | 断言 |
| --- | --- | --- |
| 语言实现交给 LLM | LLMCapability（language realization） | 回应 = scripted 文本，provider 恰被调 1 次；fear 情绪照常落地（LLM 不影响状态决议） |
| LLM 失败回退 | Deterministic fallback（§15D.23） | provider 抛错 → 确定性模板，Tick 仍 committed |
| 默认确定性 | Deterministic First（§15D.2） | 不配置 LLM 时同输入同输出 |

## 三、结论

- **20 / 20 全绿**，一次通过，未改动任何生产代码。
- 覆盖 13 个 Core State 中的 12 个（MEMORY 经 Specialized Store 的公开读 `memories()` / `retrieve()` 验证）+ 6 个 Cognitive Process 全部命中。
- 与架构回归（`tests/architecture/`，10 invariant + 3 长期测试）互补：架构回归验内部铁律，功能套件验公开 API 的端到端「生命切片」行为。
- 全量回归：`300 passed, 1 skipped`（skipped 为 env-gated 的真实网络 smoke test，与本套件无关）。
