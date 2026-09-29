# AnimaFlux Local Web Console Plan v0.2 FINAL

> 状态：**FROZEN FOR IMPLEMENTATION**
>
> 定位：AnimaFlux 的本地可视化控制台。
>
> 技术：**FastAPI + Vanilla JavaScript**
>
> 目标：**保证核心不被破坏的前提下，尽可能完整、直观、美观地展示 AnimaFlux 已有能力。**

---

# 1. 总体定位

本地 Web 前后端不是新的 Runtime，也不是新的业务核心。

它只是 AnimaFlux Public API 的一个消费者，与现有：

```text
CLI
Demo
Web
```

平级。

核心一句话：

> **Web 是冻结核心外面的一层玻璃外皮：尽可能完整地展示生命，但永远不成为生命本身。**

当前使用场景：

```text
Local Development
Local Demo
Local Debugging
Life Inspection
Timeline Visualization
Branch / Replay Visualization
```

当前不是：

```text
Public SaaS
Multi-user Platform
Multi-tenant Service
Distributed Web System
```

因此 v0.1 不为互联网生产部署增加不必要复杂度。

---

# 2. 总体架构

```text
Browser
  │
  │ HTTP / JSON
  │ optional lightweight streaming
  ▼
src/animaflux/web/
  │
  │ Public Facade only
  ▼
AnimaFlux / LifeHandle / Inspector / Public Replay APIs
  │
  ▼
Frozen Core
  │
  ▼
SQLite
```

唯一合法依赖方向：

```text
web
→ public API
→ core
```

禁止：

```text
web → StateStore
web → StateOwner
web → StateResolver
web → TransactionCoordinator
web → SQLite Repository internals
web → PluginManager internals
```

Core 必须保持：

```text
zero import fastapi
zero import uvicorn
zero dependency on frontend
```

通过 import-direction Contract Test 持续保护。

---

# 3. 代码位置

不拆独立仓库。

Web 代码统一放：

```text
src/animaflux/web/
```

推荐目录：

```text
src/animaflux/web/
├── app.py
├── sessions.py
├── dto.py
├── errors.py
├── routes/
│   ├── lives.py
│   ├── interaction.py
│   ├── state.py
│   ├── history.py
│   └── branches.py
└── static/
    ├── index.html
    ├── css/
    │   └── app.css
    └── js/
        ├── main.js
        ├── api.js
        ├── router.js
        ├── renderers.js
        └── views/
            ├── lives.js
            ├── life.js
            ├── talk.js
            ├── timeline.js
            ├── mind.js
            └── branches.js
```

v0.1 不为未来假设提前创建大量空模块。

---

# 4. Web 依赖隔离

FastAPI / Uvicorn 不进入 Core 硬依赖。

使用 Optional Extra：

```text
animaflux[web]
```

概念上：

```text
pip install animaflux
→ 不安装 FastAPI

pip install "animaflux[web]"
→ 安装 FastAPI + Uvicorn
```

Web 是可选展示能力，不改变 Core Dependency Surface。

---

# 5. 本地运行模型

默认：

```text
host = 127.0.0.1
workers = 1
```

当前仅服务本机开发者 / 演示者。

因此 v0.1 暂不实现：

```text
JWT
Login
Multi-user auth
Multi-tenant isolation
Distributed lock
Multi-worker write coordination
Public internet hardening
```

---

# 6. SQLite

继续使用：

```text
SQLite
+
WAL mode
```

原因：

```text
本地部署简单
读多写少
Timeline / Mind 等只读页面可与写操作共存
```

当前不引入：

```text
Redis
PostgreSQL
Distributed Lock
```

---

# 7. Session Registry

进程内维护：

```text
(agent_id, branch_id)
→ LifeSession
```

而不是只使用：

```text
agent_id
```

原因：

同一个 Agent 可以同时拥有：

```text
Main
Branch A
Branch B
```

每个 LifeSession 至少包含：

```text
LifeHandle
threading.Lock
```

---

# 8. 单写者与锁

所有变更操作按照：

```text
(agent_id, branch_id)
```

粒度串行执行。

包括：

```text
step
advance
observe
send_text
checkpoint
branch-related mutation
```

本地单用户场景不实现复杂 Actor Runtime。

前端在请求执行期间同时：

```text
disable button
show loading
```

降低重复提交。

---

# 9. Core Execution

v0.1 不强制新增复杂 `CoreExecutionService`。

默认路径：

```text
FastAPI Route
→ SessionRegistry
→ acquire LifeSession lock
→ call LifeHandle public method
```

如果真实编码发现：

```text
SQLite Connection thread affinity
```

等明确问题，再增加集中 Execution Service。

原则：

> **真实问题出现以后再增加结构，不为假设复杂化。**

---

# 10. Public Facade 扩展

Web 需要的能力全部通过 Public API 补齐。

允许新增纯只读 / 高层 Public Facade，例如：

```text
AnimaFlux.list_lives()
LifeHandle.summary()
LifeHandle.inspect(...)
LifeHandle.timeline(...)
LifeHandle.list_checkpoints()
LifeHandle.list_branches()
LifeHandle.trace(...)
AnimaFlux.replay(...)
```

禁止 Web 直接调用：

```text
backend.list_commits()
ReplayEngine internals
SQLite Repository
```

原则：

> **如果 UI 需要某项核心信息，先设计 Public Read View，而不是穿透 Core。**

---

# 11. LifeSummaryView

首页推荐增加：

```text
LifeSummaryView
```

它是一个只读聚合 View。

建议包含：

```text
Identity Summary
Runtime Life Time
Chronological Age
Life Stage
Active Role
Body Summary
Emotion Summary
Top Drives
Active Goals
Important Relationship
Development Summary
Recent Life Events
```

注意：

```text
LifeSummaryView
≠
new Core State
```

---

# 12. REST API

## 12.1 Life

```text
GET  /api/lives
POST /api/lives
GET  /api/lives/{life_id}
```

用途：

```text
list lives
create life
life summary
```

---

## 12.2 Runtime

```text
POST /api/lives/{life_id}/step
POST /api/lives/{life_id}/advance
```

例如：

```json
{
  "delta": "1d"
}
```

---

## 12.3 Interaction

```text
POST /api/lives/{life_id}/observe
POST /api/lives/{life_id}/say
```

`say` 返回：

```text
TurnResult
```

---

## 12.4 State

```text
GET /api/lives/{life_id}/states
GET /api/lives/{life_id}/states/{namespace}
```

`/states` 返回 13 个 Core State 的摘要。

单 Namespace 接口返回详细只读 View。

---

## 12.5 Memory

```text
GET /api/lives/{life_id}/memories
GET /api/lives/{life_id}/memories/{memory_id}
```

可支持：

```text
?type=episodic
?limit=30
```

---

## 12.6 Development

```text
GET /api/lives/{life_id}/development
```

返回：

```text
chronological_age
life_stage
roles
major_transitions
domain_experience[]
```

Domain Experience：

```text
domain
exposure
practice
diversity
recency
```

---

## 12.7 Timeline / Trace

```text
GET /api/lives/{life_id}/timeline
GET /api/lives/{life_id}/traces/{trace_ref}
```

Timeline 返回：

```text
TimelineEntry
```

而不是让前端直接解析 Commit Journal。

Trace 用于：

```text
Why ↗
```

展示。

---

## 12.8 Checkpoint

```text
GET  /api/lives/{life_id}/checkpoints
POST /api/lives/{life_id}/checkpoints
```

创建示例：

```json
{
  "label": "before long-distance transition"
}
```

---

## 12.9 Branch

```text
GET  /api/lives/{life_id}/branches
POST /api/lives/{life_id}/branches
```

创建：

```json
{
  "checkpoint_id": "...",
  "name": "alternate-life"
}
```

---

## 12.10 Replay

```text
GET or POST /api/lives/{life_id}/replay
```

具体 GET / POST 形式根据现有 Public Replay API 收敛。

必须保持：

```text
Replay = Read Only
```

Web 不直接操作 ReplayEngine 内部。

---

# 13. Branch 参数

推荐使用：

```text
?branch=<branch_id>
```

例如：

```text
GET  /api/lives/A?branch=main
POST /api/lives/A/say?branch=branch_B
```

SessionRegistry 同样使用：

```text
(agent_id, branch_id)
```

定位 LifeHandle。

---

# 14. Checkpoint 与 Branch

必须保持：

```text
Checkpoint
≠
Branch
```

标准流程：

```text
POST checkpoint
→ checkpoint_id

POST branch
→ from_checkpoint
```

不要把：

```text
branch = checkpoint + branch
```

偷偷合并成唯一语义。

未来可以提供便利操作，但底层概念保持分离。

---

# 15. DTO / Web Serializer

Core 不为了 HTTP 修改 Domain Model。

Web 自己负责：

```text
Frozen Dataclass
Enum
datetime
timedelta
Nested DTO
↓
JSON-safe Web DTO
```

统一放：

```text
web/dto.py
```

必须保持：

```text
Persistence Serializer
≠
Web Serializer
```

---

# 16. Response Envelope

成功：

```json
{
  "data": {},
  "meta": {
    "request_id": "...",
    "trace_ref": null
  }
}
```

错误：

```json
{
  "error": {
    "code": "LIFE_NOT_FOUND",
    "message": "..."
  },
  "meta": {
    "request_id": "...",
    "trace_ref": null
  }
}
```

不向浏览器返回内部 Stack Trace。

---

# 17. Error Mapping

Web 只把 Core Error 映射成稳定 HTTP Error。

例如：

```text
LifeNotFound
BranchNotFound
Validation Error
Runtime Paused
Compatibility Error
Tick Commit Failure
```

Web 不吞掉核心错误语义。

---

# 18. 健康检查

本地版只需要：

```text
GET /api/health
```

返回：

```json
{
  "status": "ok"
}
```

暂不实现：

```text
healthz
readyz
Kubernetes readiness
automatic LLM deep probe
```

---

# 19. Logging

只使用标准 Python Logging。

建议记录：

```text
request_id
life_id
branch_id
tick_id
trace_ref
error
```

暂不引入：

```text
OpenTelemetry
Prometheus
ELK
Distributed Tracing
```

---

# 20. Authentication

v0.1：

```text
Authentication = none
```

前提：

```text
127.0.0.1 local-only
```

未来若绑定 LAN / Public Network，再增加安全能力。

---

# 21. CORS

FastAPI 同时托管：

```text
frontend
+
/api
```

默认同源。

所以 v0.1 不做复杂 CORS。

只有开发阶段前后端真的分开运行时，才临时开放 localhost allowlist。

---

# 22. HTTP 幂等

v0.1 不增加 Durable HTTP Idempotency Layer。

不使用：

```text
ExternalActionJournal
LLM retry reuse
```

假装解决 HTTP Command Idempotency。

本地操作使用：

```text
per-life lock
button disabled while pending
single-user usage
```

已经足够。

---

# 23. Streaming

Streaming 不是 v0.1 必需项。

第一版：

```text
POST /say
→ UI shows thinking
→ wait complete TurnResult
→ render committed reply
```

优先保证：

```text
Generate
→ Validate
→ Commit
→ Display
```

如果后续确实需要，再增加轻量流式：

```text
turn.started
turn.processing
turn.completed
```

不实时暴露：

```text
emotion.delta
appraisal internal delta
uncommitted state changes
raw token stream
```

---

# 24. 前端技术

正式采用：

```text
HTML
CSS
Vanilla JavaScript
ES Modules
fetch
```

不使用：

```text
npm
Vite
Webpack
React
Vue
```

原因：

当前本地展示规模不需要额外 Node Toolchain。

---

# 25. 前端页面

完整页面：

```text
Lives
Life
Talk
Timeline
Mind
Branches
```

进入某个 Life 后主导航：

```text
Life
Talk
Timeline
Mind
Branches
```

---

# 26. Lives 页面

功能：

```text
list lives
open life
create life
show status
show current branch
show current life time
```

保持简单。

---

# 27. Life 页面

定位：

> **Life Overview**

展示：

```text
Name
ALIVE / PAUSED
Life Time
Chronological Age
Life Stage
Role
Mood
Body
Drive
Goal
Important Relationship
Relevant Memory
Development
Recent Events
```

视觉沿用：

```text
Life Observatory
Dark
Minimal
Scientific
Alive
Calm
```

可以保留：

```text
Life Orb
```

作为轻量生命状态视觉中心。

---

# 28. Talk 页面

布局：

```text
Conversation
+
Current Life Context
```

Current Context 可展示：

```text
Mood
Active Goal
Relationship
Relevant Memory Summary
Development Context Summary
```

Agent 重要回复旁提供：

```text
Why ↗
```

点击后打开 Causal Trace Drawer。

---

# 29. Timeline 页面

展示：

```text
Events
Memory Formation
Goal Change
Relationship Change
Turning Point
Checkpoint
```

点击节点后显示：

```text
what happened
what was perceived
relevant memories
appraisal
state effects
decision / consequence
```

Timeline 数据全部由 Public Timeline View 提供。

---

# 30. Mind 页面

完整展示全部 13 Core State：

```text
Identity
Body
Personality
Emotion
Drive
Memory
Belief
Value
Goal
Relationship
World Model
Self Model
Narrative
```

分组：

```text
STABLE SELF
Identity
Personality
Value
Self Model
Narrative

ACTIVE MIND
Emotion
Drive
Belief
Goal

LIFE CONTEXT
Body
Memory
Relationship
World Model
```

使用：

```text
renderers.js
```

为不同 Namespace 做轻量定制渲染。

---

# 31. Memory View

支持：

```text
type filter
important memories
recent memories
memory detail
accessibility
confidence
source / provenance where allowed
```

Accessibility 可以用轻微视觉淡化表示。

---

# 32. Development View

展示：

```text
Chronological Age
Life Stage
Current Roles
Major Transitions
Domain Experience
```

Domain Experience 展示：

```text
Exposure
Practice
Diversity
Recency
```

禁止：

```text
Maturity %
Experience Level
RPG Level
Experience Rank
```

必须体现：

```text
Age ≠ Experience ≠ Skill ≠ Self-Efficacy
```

---

# 33. Branches 页面

至少实现：

```text
branch tree
checkpoint list
switch branch
create branch
compare branches
```

Branch Compare 第一版可对比：

```text
Core State Summary
Important Memories
Goals
Relationship
Narrative
Development
```

核心展示：

```text
shared past
different future
```

---

# 34. Research View

前端支持：

```text
Life View
Research View
```

Life View：

```text
human-readable
minimal
```

Research View 额外展示：

```text
Tick ID
State Version
Source Refs
Confidence
LLM Call ID
Plugin
Appraisal Factors
Trace IDs
```

不另做传统 Admin Backend。

---

# 35. Web 开发阶段

## W0 — Web Foundation

实现：

```text
[web] optional extra
FastAPI app
static frontend serving
SessionRegistry
per Life+Branch lock
DTO serialization
list lives
life summary Public Facade
import-direction test
```

完成标准：

```text
Existing Core tests all green
Core imports zero FastAPI
Browser can open local page
Existing Life can be listed
```

---

## W1 — Full Core Operations

优先完成功能覆盖：

```text
create / open
step
advance
say
observe

13 state inspect
memory
development

timeline
trace
checkpoint
branch
replay
```

所有能力必须只走 Public API。

---

## W2 — Complete Frontend

完成：

```text
Lives
Life
Talk
Timeline
Mind
Branches
```

以及：

```text
13 State renderers
Memory view
Development view
Why drawer
Branch compare
Checkpoint operations
```

---

## W3 — Polish

最后处理：

```text
loading state
error toast
empty state
responsive layout
animations
better timeline
better branch tree
optional simple streaming
animaflux web command
```

W3 不增加新的 Core Life 能力。

---

# 36. v0.1 明确不做

```text
Login
JWT
Multi-user
Multi-tenant
Complex CORS
Durable HTTP idempotency
Multiple uvicorn workers
Distributed locks
Redis
WebSocket
Real-time Emotion delta
Real-time Appraisal delta
Raw LLM token streaming requirement
Prometheus
OpenTelemetry
Kubernetes readiness model
Production internet deployment
```

这些都不阻塞本地展示。

---

# 37. 当前开发优先级

```text
1. 不破坏冻结 Core
2. Core 功能覆盖全面
3. 信息展示清楚
4. Life / Timeline / Branch / Why 足够直观
5. 页面美观
6. 本地使用方便
7. 最后才考虑生产 Web 工程能力
```

---

# 38. 最终状态

```text
Document:
AnimaFlux Local Web Console Plan

Version:
v0.1

Technology:
FastAPI + Vanilla JavaScript

Deployment:
Local-only

Status:
Accepted / Frozen for Implementation
```

下一步：

```text
W0 — Web Foundation
```

---

# 39. Final Implementation Decisions【一次性敲定】

本节用于消除 W0–W3 实现过程中剩余的歧义。

从本节开始，除非真实实现证明存在技术冲突，否则不再增加 Web 架构决策。

---

## 39.1 API Prefix

所有后端接口统一使用：

```text
/api/v1
```

例如：

```text
GET  /api/v1/lives
POST /api/v1/lives/{id}/say
GET  /api/v1/lives/{id}/timeline
```

前端静态页面挂载：

```text
/
```

FastAPI 自动文档保留：

```text
/docs
/openapi.json
```

仅用于本地开发。

---

## 39.2 Frontend Routing

前端使用：

```text
Hash Router
```

例如：

```text
#/lives
#/life/{id}
#/life/{id}/talk
#/life/{id}/timeline
#/life/{id}/mind
#/life/{id}/branches
```

原因：

```text
无需服务端 SPA fallback 配置
无 bundler
刷新页面行为简单
```

---

## 39.3 Frontend State Model

不引入 Redux / Pinia / Vuex 等状态管理。

只维护极小运行态：

```text
appState = {
  lifeId,
  branchId,
  viewMode
}
```

其中：

```text
viewMode = life | research
```

导航状态优先由 URL Hash 表达。

业务数据按页面进入时重新通过 API 获取。

---

## 39.4 Branch Selection

默认：

```text
branch = main
```

所有支持 Branch 的接口统一：

```text
?branch=<branch_id>
```

前端切换 Branch 后：

```text
更新 appState.branchId
更新 URL
重新拉取当前页面数据
```

不在前端长期缓存多 Branch 的可变状态。

---

## 39.5 Data Refresh Policy

v0.1：

```text
No polling
No WebSocket
No background sync
```

用户执行修改操作后：

```text
mutation request
→ success
→ refresh affected views
```

例如：

```text
say
→ refresh talk + life summary

advance
→ refresh life summary + timeline + mind

branch
→ refresh branches
```

单用户本地场景不需要复杂实时同步。

---

## 39.6 Runtime Time Source

前端绝不能通过浏览器本地时间推导生命时间。

所有：

```text
Life Time
Age
Tick
Life Stage
```

必须来自 Public API。

浏览器：

```text
Date.now()
```

只能用于 UI 临时计时，例如 loading duration，不能进入 Life Semantics。

---

## 39.7 Create Life UI

Lives 页面提供：

```text
Create Life
```

第一版创建方式：

```text
Basic Form
+
Advanced Bootstrap JSON
```

Basic Form 只收最少信息，例如：

```text
Name
Birth Time / Initial Age Input
Initial Role
Optional Template
```

高级模式允许：

```text
paste / edit bootstrap JSON
```

Web 只负责表单与 DTO。

它不得自己推导：

```text
Personality
Belief
Value
Emotion
```

创建结果仍由：

```text
AnimaFlux.create_life(...)
```

决定。

---

## 39.8 No Destructive Delete in v0.1

v0.1 前端不提供：

```text
Delete Life
Delete Branch
Delete Memory
Delete Event
```

这些涉及：

```text
history
GC
branch roots
retention
```

不属于当前本地展示需求。

未来如增加，必须走正式 Public API。

---

## 39.9 Pause / Resume

为了功能完整，Web 可以暴露：

```text
POST /api/v1/lives/{id}/pause
POST /api/v1/lives/{id}/resume
```

前提是现有 Public API 已支持。

必须保持：

```text
PAUSED ≠ DEAD
CLOSED ≠ DEAD
```

---

## 39.10 Restore

Checkpoint Restore 属于高级操作。

建议接口：

```text
POST /api/v1/lives/{id}/restore
```

Body：

```text
checkpoint_id
```

UI：

```text
Research View / Checkpoint Detail
```

并要求明确确认。

Restore 必须调用 Public Restore API。

前端不能通过改 current pointer 或数据库记录实现。

---

## 39.11 Replay UI

Replay 永远只读。

Replay 页面/模式允许：

```text
timeline
step through history
inspect historical state
inspect trace
```

禁止：

```text
say
step new tick
advance
observe
commit
```

若用户想从过去改变未来：

```text
Create Branch
```

而不是修改 Replay Session。

---

## 39.12 Branch Compare

v0.1 Branch Compare 比较：

```text
两个 Branch 的当前 Head
```

普通 Life View 对比：

```text
Mood / Emotion Summary
Active Goals
Relationship Summary
Important Memories
Development
Self / Narrative Summary
```

Research View 可附加：

```text
State Version
namespace revision
structured JSON diff
```

不做复杂历史三方 merge。

---

## 39.13 List Pagination

虽然是本地工具，但 Memory / Timeline 可能长期增长。

因此列表接口统一支持：

```text
limit
cursor
```

例如：

```text
GET /api/v1/lives/{id}/memories?limit=30&cursor=...
GET /api/v1/lives/{id}/timeline?limit=50&cursor=...
```

v0.1 不要求复杂分页组件。

前端使用：

```text
Load more
```

即可。

---

## 39.14 State Inspection Contract

```text
GET /states
```

返回：

```text
namespace
display name
summary
schema / view metadata where allowed
```

用于 Mind Overview。

```text
GET /states/{namespace}
```

返回完整 Public Inspect View。

前端不通过：

```text
/states
```

一次加载所有巨大完整 Payload。

---

## 39.15 Plugin / Unknown Namespace Rendering

前端必须允许未来 Plugin 扩展。

`renderers.js` 采用：

```text
known namespace
→ custom renderer

unknown namespace
→ generic object renderer
```

官方 13 State 使用定制 Renderer。

其他可公开 Namespace：

```text
Research View
→ Extensions
```

展示。

不能因为新增 Plugin Namespace 就让整个 Mind 页面报错。

---

## 39.16 Generic Renderer

Generic Renderer 支持：

```text
string
number
boolean
enum-like text
array
nested object
null
```

以折叠式只读树展示。

不允许 Generic Renderer 编辑 State。

---

## 39.17 Why / Trace Contract

`Why` 页面/Drawer 统一按照以下层级展示：

```text
Input / Observation
↓
Perception
↓
Relevant Memory / Context
↓
Appraisal
↓
Influence / State Change
↓
Goal / Decision
↓
Communication / Action
```

缺少某一层时正常省略。

前端不根据文本自行“猜原因”。

所有原因来自 Public Causal Trace。

---

## 39.18 Talk Rendering Safety

模型输出、Memory、Narrative、Observation 都属于：

```text
untrusted display text
```

默认使用：

```text
textContent
```

渲染。

禁止直接：

```text
element.innerHTML = modelOutput
```

v0.1 默认不需要 Markdown 渲染。

未来如支持 Markdown：

```text
must sanitize before HTML insertion
```

即使是本地工具，也保持这个边界。

---

## 39.19 Research JSON Display

Research View 可以显示：

```text
raw Public View JSON
```

但必须：

```text
read-only
escaped
pretty printed
```

它仍然不是数据库 Raw Payload Editor。

---

## 39.20 No Web Settings System

v0.1 不单独建设：

```text
Web Settings
LLM Settings
Plugin Settings UI
Runtime Hot Config UI
```

Web 使用 AnimaFlux 已有配置文件：

```text
AnimaFlux.from_config(...)
```

前端可以只读显示当前 Runtime/Profile 信息，但不在线热修改 Core Configuration。

---

## 39.21 Startup Command

最终提供：

```text
animaflux web
```

建议参数：

```text
--config <path>
--host 127.0.0.1
--port 8000
```

默认：

```text
host = 127.0.0.1
port = 8000
```

可选：

```text
--open
```

用于启动后自动打开浏览器。

---

## 39.22 Static Asset Packaging

`static/` 必须作为 Python Package Data 发布。

目标：

```text
pip install "animaflux[web]"
animaflux web
```

即可使用。

不要求用户：

```text
npm install
npm run build
copy frontend dist
```

---

## 39.23 Browser Cache

API 数据默认按实时本地调试使用。

v0.1 不建立：

```text
Service Worker
Offline Cache
Client Data Cache Layer
```

API 请求应优先获取当前 Public View。

静态 CSS / JS 使用普通浏览器缓存即可。

开发阶段如缓存干扰，可使用版本 query 或 no-cache response。

---

## 39.24 Loading / Error UX

所有 mutation：

```text
Step
Advance
Say
Checkpoint
Branch
Restore
```

执行期间：

```text
disable relevant control
show loading / thinking
```

失败时：

```text
restore button state
show error toast / inline error
preserve unsent user input where possible
```

不因 HTTP 失败直接刷新整个页面。

---

## 39.25 Session Registry Lifetime

本地 v0.1 Life 数量有限。

因此 Session Registry：

```text
no automatic eviction required
```

首次访问懒加载。

服务退出时正常释放引用 / backend resource。

不实现：

```text
LRU
distributed session
persistent web session table
```

---

## 39.26 Manual Reflection

如果当前 Public API 已存在：

```text
request_reflection()
```

可在 Research View 提供：

```text
Request Reflection
```

但语义必须是：

```text
schedule / cognitive request
```

不是 Web 直接调用内部 ReflectionProcess。

如果 Public API 尚未提供，此功能不阻塞 Web v0.1。

---

## 39.27 Frontend Testing

不引入 Node Test Toolchain。

最低要求：

### Backend

```text
pytest
FastAPI TestClient
API contract tests
session / branch tests
DTO tests
import-direction tests
```

### Frontend

W0–W2：

```text
manual browser smoke
```

W3 如有需要可以增加：

```text
Python Playwright optional E2E
```

但不是 Core Dependency。

---

## 39.28 API Contract First

Frontend 不根据 Python 内部对象结构写死。

所有前端页面只能依赖：

```text
documented HTTP DTO
```

后端 DTO 改动时：

```text
update API contract tests
```

避免 JS 依赖 Core dataclass 私有字段。

---

## 39.29 Functional Coverage Matrix

Web v0.1 以“功能覆盖全面”为主要验收标准。

至少必须覆盖：

| Core/Public 能力 | Web 页面 |
|---|---|
| Life list/create/open | Lives |
| Life summary | Life |
| Step | Life |
| Advance Time | Life |
| Pause/Resume（若 Public API 已有） | Life |
| Human send_text | Talk |
| Observation | Research / Life action |
| 13 State inspect | Mind |
| Memory | Mind / Memory panel |
| Development Context | Life / Mind |
| Timeline | Timeline |
| Causal Trace / Why | Talk / Timeline |
| Checkpoint | Timeline / Branches |
| Branch create/switch | Branches |
| Branch Compare | Branches |
| Restore | Research / Checkpoint |
| Replay | Timeline / Research |
| Research metadata | Research View |

---

## 39.30 Final Non-goals

除前文已有 Non-goals 外，再明确：

```text
No editable raw State JSON
No DB admin console
No SQL browser
No visual Plugin editor
No drag-and-drop cognitive workflow builder
No runtime hot plugin swap UI
No world map
No game inventory
No multi-agent town dashboard
```

这些不属于当前 Local Web Console。

---

# 40. Web Architecture Freeze

到此为止，本地 Web 方案已经具备：

```text
Technology
Dependency Boundary
Deployment Model
Concurrency Boundary
Public API Boundary
REST Surface
Branch Semantics
Replay / Restore Semantics
DTO
Frontend Structure
Frontend Routing
State Rendering
Memory / Development
Timeline / Why
Branch Compare
Testing
Packaging
Implementation Roadmap
Non-goals
```

不再需要新的 Web 架构讨论。

正式状态：

```text
Document:
AnimaFlux Local Web Console Plan

Version:
v0.2 FINAL

Architecture:
FROZEN FOR IMPLEMENTATION

Next:
W0 → W1 → W2 → W3
```

只有以下情况允许修改本方案：

```text
1. 现有冻结 Core 的真实 Public API 与本方案发生技术冲突
2. 当前 SqliteBackend 的真实线程模型无法支持既定调用方式
3. 浏览器平台限制使既定交互无法实现
4. 测试证明当前边界会破坏 Core correctness
```

以下情况不允许重新扩架构：

```text
“以后可能用得上”
“这个功能看起来更酷”
“别的 Agent 框架都有”
“可以顺便做成 SaaS”
```

现在应直接进入：

```text
W0 — Web Foundation
```

