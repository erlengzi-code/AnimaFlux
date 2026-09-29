# AnimaFlux 技术架构设计规范

> 持续维护文档：本文档只记录 AnimaFlux 的工程与运行时架构。后续每正式敲定一个技术方案，都继续写入本文件。

## 一、总体技术目标

AnimaFlux 的工程目标不是实现一个巨大的 `DigitalLifeAgent` 类，而是构建一个：

> **微内核 + 可插拔生命模块 + 统一运行时**

整体方向：

```text
AnimaFlux
├── Kernel
│   负责“系统怎么运行”
└── Plugins
    负责“数字生命具有什么能力、采用什么模型”
```

核心要求：

1. 第三方开发者可以独立开发插件。
2. Emotion、Memory、Body 等模块可以被替换。
3. Kernel 不依赖某一种心理学模型。
4. Kernel 不依赖某一家 LLM Provider。
5. Kernel 不依赖某一种世界设定。
6. 插件之间尽量低耦合，避免循环依赖。
7. 所有关键状态变化可追踪、可调试、可回放。

---

## 二、Architecture Decision #1：Kernel 与 Plugin 边界【已敲定】

### 2.1 Kernel 的定义

Kernel（内核）可以理解为：

> **AnimaFlux 的“操作系统内核”。**

它不负责定义爱情、愤怒、人格、创伤、疾病是什么。

它只负责：

```text
插件如何加载
时间如何推进
Life Loop 如何运行
状态如何保存
事件如何传递
Influence 如何传递
什么时候调用插件
状态什么时候提交
插件失败怎么办
```

因此：

> **Kernel 负责运行机制，不负责生命领域知识。**

### 2.2 Plugin 的定义

Plugin（插件）负责：

> **具体生命能力和具体模型。**

例如：

```text
BodyPlugin
EmotionPlugin
MemoryPlugin
PersonalityPlugin
BeliefPlugin
RelationshipPlugin
```

未来第三方还可以提供：

```text
TraumaPlugin
DreamPlugin
AttachmentPlugin
AdvancedDiseasePlugin
ChineseCulturePlugin
CyberpunkWorldPlugin
```

不同插件可以使用完全不同的内部理论，只要遵循 AnimaFlux 统一协议。

### 2.3 为什么不能把所有逻辑写进 DigitalLifeAgent

不采用：

```text
DigitalLifeAgent
├── update_body()
├── update_emotion()
├── update_memory()
├── update_belief()
├── update_relationship()
├── simulate_disease()
├── simulate_love()
└── ...
```

这种不断膨胀的“大类”设计。

原因：

1. 功能增加后类会失控。
2. 各模块容易相互直接依赖。
3. 容易形成循环依赖。
4. 第三方难以替换单个模块。
5. 一个模块升级可能影响整个 Agent。
6. 无法形成真正的开放插件生态。

例如：

```text
Emotion → Memory
Memory → Belief
Belief → Emotion
```

如果都通过直接对象调用实现，会快速形成强耦合。

### 2.4 Microkernel（微内核）的含义

“微内核”不是单纯追求代码少。

它的真正含义是：

> **内核只保留所有插件共同依赖、并且不能合理归属某一个业务插件的基础机制。**

判断规则：

> 如果把 Emotion、Memory、Body 等全部替换掉，这项能力是否仍然必须存在？

如果答案是“必须”，它很可能属于 Kernel。

例如：

```text
插件加载
时间推进
Tick 生命周期
状态事务
事件分发
调度
错误隔离
```

都属于 Kernel 候选。

如果答案是“不一定”，通常更适合做 Plugin。

例如：

```text
Big Five 人格模型
OCC 情绪模型
梦境
创伤
爱情
疾病模型
文化模型
```

### 2.5 Kernel 当前候选组成

```text
AnimaFlux Kernel
├── Runtime
│   控制 Life Loop
├── Plugin Manager
│   插件发现、加载、启动、关闭
├── State Store
│   State Snapshot / Working State / Commit
├── Time Engine
│   世界时间和 Tick
├── Event System
│   Event 分发
├── Influence System
│   跨模块影响传递
├── State Resolver
│   组织状态裁决
├── Scheduler
│   Process 调度
└── Infrastructure
    日志、随机数、持久化接口、错误隔离等
```

Kernel 中存在 `State Resolver`，不代表 Kernel 知道“失恋应该悲伤多少”。

Kernel 只负责：

```text
收集 Influence
↓
找到目标 State Owner
↓
调用相应领域插件
↓
组织结果
↓
统一提交
```

具体心理规则仍由插件负责。

### 2.6 Kernel 与领域知识的边界

例如发生：

```text
Event:
JobLost
```

Kernel 不理解失业应该悲伤、害怕还是找工作。

Kernel 只负责将 Event 放入 Life Loop。

随后不同插件分别解释：

```text
MemoryPlugin：
召回以前的失业经历

BeliefPlugin：
某些“工作不稳定”信念被强化

EmotionPlugin：
根据认知评价产生恐惧、羞耻、愤怒等

DrivePlugin：
安全相关 Drive 上升

GoalPlugin：
寻找工作 Goal 的优先级上升
```

因此：

```text
Kernel = 流程
Plugin = 领域规则
```

### 2.7 LLM 不属于 Kernel

Kernel 不直接绑定 OpenAI、Claude、Gemini、DeepSeek 或本地模型。

而是依赖抽象能力：

```text
LLM Capability
```

具体实现可以来自不同 Provider Plugin。

因此正式确定：

> **LLM 是可替换能力提供者，不是 Kernel 本体。**

### 2.8 World 不属于 Kernel

Kernel 不应该写死现代城市、中世纪、赛博朋克、火星殖民地或奇幻世界。

Kernel 只提供：

```text
World Runtime / World Capability
```

具体世界由不同 World Plugin 实现。

因此：

> **同一个 Digital Life 可以被放入不同 World Plugin 中运行。**

### 2.9 最终架构原则

正式接受：

> **Kernel = 运行生命的机制。**

> **Plugin = 生命具体拥有什么能力，以及这些能力采用什么模型。**

更直白地说：

> **Kernel 不懂“人”，Kernel 只懂怎样让一组描述“人”的插件稳定协作。**

### 2.10 状态

```text
Architecture Decision:
Kernel / Plugin Boundary v0.1

Status:
Accepted
```

---

## 三、Architecture Decision #2：State Ownership（状态所有权）【已敲定】

### 3.1 定义

State Ownership（状态所有权）用于回答：

> **一份状态到底归谁管理，谁有资格解释和修改它？**

例如：

```text
EmotionPlugin
负责 state.emotion

BodyPlugin
负责 state.body

MemoryPlugin
负责 state.memory
```

正式原则：

> **自己的状态自己解释；别人的状态只能提出影响；读取别人状态走公开能力；最终状态由内核统一提交。**

---

### 3.2 为什么不能让插件直接修改彼此状态

如果所有插件都能直接修改任何状态，会快速产生：

```text
EmotionPlugin → Body
BodyPlugin → Emotion
MemoryPlugin → Emotion
RelationshipPlugin → Emotion
EmotionPlugin → Relationship
```

最终形成：

- 强耦合
- 循环依赖
- 修改来源难追踪
- 插件替换困难
- 状态修改顺序影响结果
- 第三方插件容易破坏其他模块

例如：

```text
sleep_quality:
0.8 → 0.3
```

如果多个插件都直接修改它，就很难回答：

> **到底是谁改的？为什么改？哪一个插件应该对此负责？**

---

### 3.3 一个 State Namespace 对应一个 Owner

正式采用：

```text
state.identity
state.body
state.personality
state.emotion
state.drive
state.memory
state.belief
state.value
state.goal
state.relationship
state.world_model
state.self_model
state.narrative
```

每个主要 State Namespace 默认有一个明确的 Primary Owner。

例如：

```text
state.body
Owner = BodyPlugin
```

```text
state.emotion
Owner = EmotionPlugin
```

Owner 负责：

- State Schema
- State Validation
- State Evolution
- Influence Interpretation

中文：

- 定义状态结构
- 校验状态是否合法
- 计算状态如何变化
- 解释其他模块发来的影响

---

### 3.4 非 Owner 不允许直接写 State

例如 EmotionPlugin 不能直接修改：

```text
state.body.sleep_quality
```

它只能产生：

```text
ChronicStressInfluence
```

然后交给 BodyPlugin / State Resolver。

BodyPlugin 再根据自己的身体模型决定：

```text
sleep_quality
recovery
health
```

到底怎样变化。

因此：

```text
EmotionPlugin
↓
Influence
↓
BodyPlugin
↓
Body Next State
```

而不是：

```text
EmotionPlugin
↓
直接修改 state.body
```

---

### 3.5 为什么 Influence 比直接写字段更适合插件生态

假设存在：

```text
SimpleBodyPlugin
```

内部只有：

```text
energy
health
sleep
```

另一个插件：

```text
AdvancedBodyPlugin
```

内部可能有：

```text
cardiovascular
immune
endocrine
sleep_cycle
metabolism
```

如果 EmotionPlugin 直接依赖：

```text
state.body.sleep_quality
```

替换 BodyPlugin 后字段结构变化，EmotionPlugin 就可能失效。

如果 EmotionPlugin 只产生：

```text
type = chronic_stress
```

则不同 BodyPlugin 都可以按自己的内部模型解释这个 Influence。

因此：

> **Influence 传递语义，不传递对方内部实现细节。**

---

### 3.6 读取其他插件状态也不应直接访问内部字段

写权限严格限制。

读权限也采用公开接口。

例如 EmotionPlugin 不应该随意读取：

```text
state.body.internal.xxx
```

而应通过未来的：

```text
Body Capability
```

请求公开信息，例如：

```text
当前疲劳程度
当前疼痛信号
当前生理唤醒程度
```

因此正式方向：

```text
Own State
→ Owner 管理

Other State Write
→ Influence

Other State Read
→ Capability
```

Capability 会在后续单独设计。

---

### 3.7 Owner 也不能绕过 Tick 事务随意写状态

Owner 的含义不是：

> 随时可以直接改数据库。

而是：

> **Owner 对自己 State 的变化拥有最终领域解释权。**

Life Loop 中仍然遵循：

```text
Snapshot State
↓
计算 Next State
↓
Working State
↓
Validation
↓
Kernel Commit
```

因此：

> **状态属于插件，但提交属于 Kernel。**

这是本项正式架构原则之一。

---

### 3.8 一个 Namespace 默认只能有一个 Primary Owner

例如同时安装：

```text
BasicEmotionPlugin
OCCEmotionPlugin
PADEmotionPlugin
```

没有问题。

但当前 Runtime 中：

```text
state.emotion
```

默认只能选择其中一个 Primary Owner。

例如：

```text
emotion provider = OCCEmotionPlugin
```

其他插件可以：

- 提供辅助能力
- 产生 Influence
- 作为 Interaction Plugin

但不能同时都成为 `state.emotion` 的最终写入者。

这样才能避免多个插件争夺同一状态控制权。

---

### 3.9 双向影响不等于双向直接写入

例如 Body 和 Emotion 可以互相影响：

```text
Body
↓
Capability
↓
Emotion
```

同时：

```text
Emotion
↓
Influence
↓
Body
```

双方都可以形成反馈循环，但都不直接修改对方内部状态。

因此：

> **业务上可以双向耦合，代码层面仍保持低耦合。**

---

### 3.10 State Ownership v0.1 最终规则

正式接受：

```text
1. 每个主要 State Namespace 有一个明确 Primary Owner。

2. Owner 负责：
   - State Schema
   - State Validation
   - State Evolution
   - Influence Interpretation

3. 非 Owner：
   - 不允许直接写其他 State
   - 不依赖其他插件内部字段
   - 通过 Influence 提出跨模块影响
   - 通过 Capability 读取公开信息

4. 一个 Runtime 中，
   一个 State Namespace 默认只能有一个 Primary Owner。

5. Owner 负责计算 Next State，
   Kernel 负责统一 Commit。
```

最终原则：

> **Own State → Owner decides**  
> **Other State → Influence only**  
> **Public Read → Capability**  
> **Final Write → Kernel Commit**

状态：

```text
Architecture Decision:
State Ownership v0.1

Status:
Accepted
```

---

## 四、代码与实现语言约束【已敲定】

AnimaFlux 当前正式实现语言：

> **Python**

后续技术架构文档中的：

- 代码示例
- 伪代码
- 接口示例
- 插件示例
- 测试示例
- 项目骨架

统一使用 Python。

不在 AnimaFlux 技术文档中加入其他语言的实现示例。

---

## 五、Architecture Decision #3：Event（事件系统）【已敲定】

### 5.1 定义

Event（事件）表示：

> **世界里已经发生的一件客观事实。**

例如：

```text
下雨了
陈默失业了
张三说了一句话
伴侣提出分手
Agent 摔伤了
公司宣布裁员
孩子出生了
父亲去世了
```

Event 只描述：

> **“发生了什么。”**

它不负责描述：

> **“这件事应该让谁悲伤多少、害怕多少、改变什么信念。”**

这些属于后续的 Perception、Appraisal 和 Influence。

---

### 5.2 Event 与 State 的区别

Event 表示一次已经发生的变化。

State 表示变化之后当前持续存在的状态。

例如：

```text
Event:
GotMarried
```

之后：

```text
Identity State:
marital_status = married
```

再例如：

```text
Event:
LegInjured
```

之后：

```text
Body State:
injury = active
mobility ↓
```

正式区分：

```text
Event = 发生了一次变化
State = 变化以后现在是什么样
```

---

### 5.3 Event 与 Influence 的区别

Event：

```text
发生了什么
```

Influence：

```text
这件事可能怎样影响某个 State
```

例如：

```text
Event:
relationship.breakup.requested
```

经过：

```text
Perception
↓
Appraisal
```

之后可能产生：

```text
Emotion Influence
Drive Influence
Relationship Influence
Self Model Influence
```

因此：

```text
Event
↓
Perception
↓
Appraisal
↓
Influence
↓
State Change
```

Event 与 Influence 不能混为一体。

---

### 5.4 Action Proposal 不是 Event

例如：

```text
“我准备去和张三表白”
```

属于：

```text
Action Proposal
```

只有世界确认：

> **这件事真的发生了**

以后，才产生 Event。

正式链路：

```text
Intent
↓
Action Proposal
↓
World Action Resolver
↓
Actual Outcome
↓
Event
```

因此：

> **Event 必须代表已经被世界确认发生的事情。**

---

### 5.5 Event 创建后默认不可修改

Event 一旦进入 Event Log，就默认视为客观历史记录。

例如：

```text
10:00
老板说：
“项目延期了。”
```

不能以后直接把原 Event 覆盖成：

```text
“项目取消了。”
```

如果后来发现原记录错误，应通过新的：

```text
EventCorrection
EventInvalidated
```

等事件表达。

正式原则：

> **历史修正通过新事件完成，不直接篡改已有 Event。**

---

### 5.6 Event 公共结构

Event v0.1 至少包含以下公共概念：

```text
event_id
event_type
world_time
source
participants
targets
payload
visibility
causal_refs
importance_hint
```

解释如下。

#### event_id

事件唯一标识。

例如：

```text
EVT-000001
```

#### event_type

事件类型。

例如：

```text
career.job.lost
conversation.message.spoken
world.weather.rain_started
body.injury.occurred
relationship.breakup.requested
```

#### world_time

事件发生的世界时间。

注意：

> 使用 AnimaFlux World Time，而不是电脑真实时间。

#### source

事件来源。

例如：

```text
World
Company
Agent A
Body
WeatherSystem
```

#### participants

参与事件的主体。

例如：

```text
A 与 B 争吵
participants = [A, B]
```

#### targets

事件主要针对的主体。

例如：

```text
Company 裁掉 A

source = Company
target = A
```

#### payload

事件特有业务内容。

例如失业事件：

```python
{
    "reason": "restructuring",
    "position": "engineer",
}
```

Kernel 不解释这些具体字段。

#### visibility

表示：

> **谁理论上有机会感知这个 Event。**

#### causal_refs

表示：

> **哪些 Event 参与导致了当前 Event。**

#### importance_hint

世界 / 事件生产者给出的粗略重要性提示。

它不是主体最终主观重要度。

---

### 5.7 visibility 与真正感知必须分开

例如：

```text
A 在 10 米外向 B 挥手
```

Event 对附近 Agent：

```text
visibility = local_area
```

但某个 Agent：

```text
视力差
正在低头
注意力在别处
```

仍然可能没有看见。

因此：

```text
Event.visibility
```

只决定：

> **有没有进入感知范围的可能。**

真正感知仍然需要：

```text
visibility
+
Body Sensory Capability
+
Attention
+
Perception
```

最终形成：

```text
Perceived Event
```

---

### 5.8 一个客观 Event，多份主观 Perception

正式采用：

> **世界中的客观 Event 只有一份。**

例如：

```text
A 对 B 说：
“我不想再见你了。”
```

世界只记录一个：

```text
conversation.message.spoken
```

但是：

```text
A 的 Perception：
“我终于说出来了。”

B 的 Perception：
“他彻底不要我了。”

旁观者 C：
“他们好像吵架了。”
```

因此：

```text
1 Objective Event
↓
N Perceived Events
```

而不是为每个 Agent 复制一份客观 Event。

---

### 5.9 causal_refs 使用多引用结构

事件可能由多个原因共同产生。

例如疾病可能同时受到：

```text
年龄
长期压力
遗传倾向
感染
```

影响。

因此不使用单一：

```text
causal_parent
```

而采用：

```text
causal_refs = [...]
```

例如：

```python
causal_refs = (
    "EVT-101",
    "EVT-205",
    "EVT-331",
)
```

用于未来：

```text
Causal Trace
人生回放
因果分析
调试
```

---

### 5.10 importance_hint 不是主观重要度

同一 Event 对不同 Agent 的意义不同。

例如：

```text
Event:
world.weather.rain_started
```

世界层面：

```text
importance_hint = 0.2
```

但对于今天正在举行户外婚礼的 Agent：

```text
subjective_importance = 0.9
```

因此：

```text
importance_hint
```

只提供系统级提示。

最终：

> **这件事对“我”有多重要**

由 Appraisal 决定。

---

### 5.11 谁可以产生 Event

以下组件都可以提出事件：

```text
World Plugin
Body Plugin
Action Resolver
Scheduler
External User Input
System Process
```

例如：

```text
World:
world.weather.rain_started

Body:
body.disease.heart_attack_occurred

Action Resolver:
conversation.message.spoken

Scheduler:
identity.birthday.reached
```

但它们不应直接随意写 Event Log。

统一经过：

```text
Kernel Event System
```

进行：

```text
结构校验
Event ID 分配
世界时间写入
Queue 入队
Event Log 持久化
```

---

### 5.12 Event 默认进入 Queue

不采用：

```text
Event 产生
↓
立刻递归调用所有 Plugin
```

否则容易形成：

```text
Event
↓
Event
↓
Event
↓
无限嵌套
```

正式采用：

```text
Event
↓
Event Queue
↓
Kernel 在对应 Life Loop 阶段统一处理
```

这样与之前确定的：

```text
Tick
↓
收集 Event
↓
统一 Perception
↓
统一 Appraisal
```

保持一致。

---

### 5.13 Immediate Consequence Pass

部分事件需要即时产生有限后果。

例如：

```text
A 打 B
↓
Hit Event
↓
B Body 立即产生损伤和疼痛信号
```

这类情况通过：

```text
Immediate Consequence Pass
```

处理。

但即时通道必须：

```text
有界
可追踪
不可无限递归
```

它不是绕过 Event Queue 的万能后门。

---

### 5.14 Event Type 使用命名空间

不采用一个巨大的中央枚举。

推荐：

```text
world.weather.rain_started
career.job.lost
relationship.breakup.requested
body.injury.occurred
conversation.message.spoken
```

第三方 Plugin 可以注册自己的事件：

```text
dream.nightmare.occurred
culture.ritual.completed
```

因此：

> **Kernel 不需要知道所有 Event Type 的具体业务含义。**

---

### 5.15 Event 的具体业务内容放入 payload

Event 基类只保存公共字段。

不同事件类型自己的内容放在：

```text
payload
```

例如：

```python
{
    "reason": "restructuring",
    "position": "engineer",
}
```

未来可以进一步支持：

```text
Typed Payload
```

但 Kernel 仍只依赖 Event 公共协议。

---

### 5.16 Python 概念模型

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    world_time: datetime

    source: str | None = None

    participants: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()

    payload: dict[str, Any] = field(default_factory=dict)

    visibility: str = "public"

    causal_refs: tuple[str, ...] = ()

    importance_hint: float = 0.0
```

其中：

```python
frozen=True
```

表达：

> **Event 创建后默认不再被修改。**

此代码仅表示当前协议语义，最终实现仍可继续优化。

---

### 5.17 Kernel Event System 的职责

Kernel Event System 负责：

```text
Event ID 分配
公共字段校验
世界时间写入
Event Queue 管理
visibility 候选分发
Event Log 持久化
causal_refs 维护
```

Kernel Event System 不负责：

```text
解释失恋应该多悲伤
判断疾病心理意义
判断下雨是否重要
```

这些属于领域 Plugin 和后续 Appraisal。

---

### 5.18 Event System v0.1 最终原则

正式接受：

1. **Event 表示已经发生的客观事实。**
2. **Event 与 State 分离。**
3. **Event 与 Influence 分离。**
4. **Action Proposal 不是 Event，世界确认发生后才生成 Event。**
5. **Event 创建后默认不可修改。**
6. **Event Log 保存客观历史。**
7. **一个客观 Event 可以产生多个不同 Agent 的主观 Perception。**
8. **visibility 只表示“有机会感知”，不保证真正感知。**
9. **Event 支持多个 causal_refs。**
10. **Event 可以有 importance_hint，但主观重要性由 Appraisal 决定。**
11. **多种系统都可提出 Event，但由 Kernel Event System 统一创建、校验和登记。**
12. **Event 默认进入 Queue，不进行无界同步递归。**
13. **即时反应使用受控 Immediate Consequence Pass。**
14. **Event Type 使用可扩展命名空间。**
15. **具体业务数据放在 payload，Kernel 只依赖公共 Event 协议。**

状态：

```text
Architecture Decision:
Event System v0.1

Status:
Accepted
```

---

## 六、Architecture Decision #4：Influence（影响系统）【已敲定】

### 6.1 定义

Influence（影响）表示：

> **一个 Process / Plugin 对某个 State 提出的“状态影响建议”。**

它不是已经发生的客观事实，也不是最终状态变化结果。

正式区分：

```text
Event
=
发生了什么

Influence
=
这件事可能怎样影响某个 State

State Change
=
State Owner 最终计算出来的状态变化
```

典型链路：

```text
Event
↓
Perception
↓
Appraisal
↓
Influence
↓
State Resolver
↓
State Owner
↓
Next State
```

---

### 6.2 Influence 不直接操作目标字段

不采用：

```text
sadness += 0.3
sleep_quality -= 0.2
self_confidence -= 0.4
```

作为跨插件协议。

原因是这会让其他插件知道目标 State 的内部字段。

例如：

```text
BasicEmotionPlugin
```

可能拥有：

```text
sadness
anger
fear
joy
```

而：

```text
PADEmotionPlugin
```

可能只有：

```text
pleasure
arousal
dominance
```

如果跨插件 Influence 写死：

```text
sadness + 0.3
```

就无法替换 Emotion Plugin。

因此正式采用：

> **语义化 Influence。**

例如：

```text
social_rejection
relationship_loss
chronic_stress
physical_pain
status_gain
financial_insecurity
goal_failure
social_support
```

目标 Plugin 根据自己的内部模型解释这些语义。

---

### 6.3 Influence 是插件之间的“中间语言”

Influence 不描述具体事件细节，而描述：

> **事件经过主观解释后，对状态产生的抽象意义。**

例如：

```text
Event:
老板公开批评 Agent
```

经过 Appraisal 后可能得到：

```text
social_evaluation_threat
self_image_threat
status_loss
```

然后不同 State Owner 分别解释。

例如：

```text
EmotionPlugin
→ 羞耻 / 愤怒 / 恐惧变化

SelfModelPlugin
→ 自信、自我效能变化

DrivePlugin
→ 认可、安全相关 Drive 变化

RelationshipPlugin
→ 对老板的信任、尊重变化
```

因此：

> **Influence 表达“影响意义”，State Owner 决定“具体怎么算”。**

---

### 6.4 Influence 与 Event 的抽象层级不同

Event 应尽量具体：

```text
老板说：
“你这次做得很差。”
```

Influence 应更抽象：

```text
social_evaluation_threat
```

不能把 Influence 再写成：

```text
boss_said_you_are_bad
```

否则只是重复 Event。

正式原则：

```text
Event = 具体事实
Influence = 抽象影响语义
```

---

### 6.5 一条 Influence 只指向一个 State Namespace

正式采用：

```text
one Influence
→ one target_state
```

例如：

```text
Influence A
target = emotion
type = social_rejection

Influence B
target = drive
type = social_disconnection

Influence C
target = self_model
type = self_image_threat
```

不采用：

```text
targets = [emotion, drive, self_model]
```

这种一条 Influence 多目标模式。

原因：

- 因果链更清楚
- 每个 target 可有不同 magnitude
- Resolver 更简单
- 调试更容易
- 不同 Owner 的解释互不干扰

---

### 6.6 magnitude 表示影响强度，不是字段增量

Influence 支持：

```text
magnitude
```

例如：

```text
social_rejection
magnitude = 0.8
```

它表示：

> **“社会拒绝这一影响很强。”**

不代表：

```text
sadness += 0.8
```

EmotionPlugin 仍需结合：

```text
Personality
Relationship
Belief
Memory
Mood
Current Context
```

计算最终情绪变化。

因此：

```text
magnitude = 影响强度
≠
最终 State Delta
```

---

### 6.7 duration 与 decay

Influence 可以是：

```text
瞬时
短期
长期
```

例如：

```text
突然受惊
→ 持续数分钟
```

```text
关系冲突
→ 可能持续数天
```

```text
慢性工作压力
→ 可能持续数月
```

因此 Influence 可以携带：

```text
duration
expires_at
decay
```

`decay` 表示影响随时间减弱的方式。

Kernel 负责保存与调度这些信息，但具体数学解释由目标 State Owner 负责。

---

### 6.8 confidence

Influence 支持：

```text
confidence
```

表示：

> **产生这条 Influence 的 Process 对自己判断有多确定。**

例如：

```text
“她最近好像在躲我。”
```

可能产生：

```text
social_rejection
confidence = 0.45
```

而明确收到：

```text
“我以后不想再和你联系。”
```

可能：

```text
social_rejection
confidence = 0.98
```

目标 Plugin 可据此调整响应强度。

---

### 6.9 Influence 必须支持因果追踪

重要 Influence 应能追踪：

```text
source_plugin
cause_event_refs
cause_memory_refs
```

例如：

```text
Influence:
type = self_image_threat
magnitude = 0.8

source_plugin:
appraisal.default

cause_event_refs:
EVT-1001
```

这样可以建立：

```text
State Change
↓
Influence
↓
Appraisal
↓
Perceived Event
↓
Objective Event
```

完整 Causal Trace。

---

### 6.10 谁可以产生 Influence

任何被 Runtime 授权参与 Life Loop 的 Process / Plugin 都可以产生 Influence。

例如：

```text
AppraisalPlugin
EmotionPlugin
MemoryPlugin
RelationshipPlugin
BodyPlugin
InteractionPlugin
```

但 Influence 不应直接交给目标 Plugin 立即执行。

统一进入：

```text
Influence Buffer
```

---

### 6.11 Influence Buffer

Influence Buffer 可以理解为：

> **当前 Tick 的“影响收件箱”。**

例如当前 Tick 同时存在：

```text
老板批评
身体疲劳
朋友安慰
想起过去失败
```

可能形成：

```text
social_rejection
fatigue
social_support
failure_memory_activation
```

这些 Influence 先统一进入 Buffer。

之后：

```text
State Resolver
```

再组织处理。

正式区分：

```text
Event Queue
=
“发生了什么”的队列

Influence Buffer
=
“这些事情可能怎样影响 State”的缓冲区
```

---

### 6.12 Influence 不即时递归执行

不采用：

```text
产生 Influence
↓
目标 State 马上改变
↓
产生新 Influence
↓
下一个 State 马上改变
↓
继续递归
```

因为容易导致无限循环。

正式采用：

```text
产生 Influence
↓
Influence Buffer
↓
State Resolver
↓
按 Round 有界处理
```

例如：

```text
Round 1:
直接影响

Round 2:
二阶影响

Round 3:
三阶影响

停止
```

与 Life Loop 中已确定的有限传播原则保持一致。

---

### 6.13 Influence Type 可扩展，但不由 Kernel 写死

Influence Type 可以由 Plugin 注册。

例如：

```text
social_rejection
chronic_stress
physical_pain
goal_failure
status_gain
```

Kernel 不需要理解这些语义。

Kernel 只需要知道：

```text
target_state
```

然后把 Influence 路由给对应 State Owner。

---

### 6.14 Kernel 路由，Owner 解释

例如：

```text
target_state = emotion
type = social_rejection
magnitude = 0.8
```

Kernel 的职责：

```text
找到 state.emotion 的 Primary Owner
↓
交给 EmotionPlugin
```

EmotionPlugin 的职责：

```text
解释 social_rejection
↓
结合自身模型
↓
计算 emotion_next
```

正式原则：

> **Kernel routes, Owner interprets.**

中文：

> **内核负责送达，状态所有者负责解释。**

---

### 6.15 不支持的 Influence

如果目标 Owner 不认识某个 Influence Type：

```text
type = abandonment_trigger
```

第一版默认处理：

```text
忽略该 Influence
+
记录 Warning
```

例如：

```text
UnsupportedInfluenceWarning
```

不能因为单个不兼容 Influence 让整个 Runtime 崩溃。

未来可以通过 Capability Negotiation 在插件加载阶段提前发现兼容性问题。

---

### 6.16 Influence 创建后默认不可修改

与 Event 类似，Influence 创建后默认不可修改。

如果后续需要抵消或修正：

> 创建新的 Influence。

而不是偷偷修改旧 Influence。

这样 Causal Trace 更清晰，也更容易调试。

---

### 6.17 Influence 与 Event 生命周期不同

Event：

```text
世界层面的客观历史
→ Event Log
→ 长期保存
```

Influence：

```text
运行时状态影响建议
→ Influence Buffer
→ 通常生命周期较短
```

例如：

```text
Event:
partner_died
```

可以永久存在 Event Log。

而：

```text
Influence:
relationship_loss
```

可能只在当前 Tick 或后续一段时间发挥作用。

---

### 6.18 Python 概念模型

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Influence:
    influence_id: str

    source_plugin: str
    target_state: str

    influence_type: str
    magnitude: float

    created_at: datetime

    confidence: float = 1.0

    duration_seconds: float | None = None
    decay: str | None = None

    cause_event_refs: tuple[str, ...] = ()
    cause_memory_refs: tuple[str, ...] = ()

    metadata: dict[str, Any] = field(default_factory=dict)
```

该结构仅表达当前协议语义，最终实现阶段仍可优化。

---

### 6.19 Influence System v0.1 最终原则

正式接受：

1. **Influence 是跨模块的状态影响建议。**
2. **Influence 与 Event 分离。**
3. **Influence 不直接表示最终 State Delta。**
4. **跨插件 Influence 优先采用语义类型，而不是直接操作目标字段。**
5. **一条 Influence 只指向一个 target State Namespace。**
6. **Influence 支持 magnitude，但它表示影响强度，不等于最终字段变化量。**
7. **Influence 支持 duration / decay。**
8. **Influence 支持 confidence。**
9. **Influence 必须支持 source_plugin、cause_event_refs、cause_memory_refs 等因果追踪信息。**
10. **Influence 创建后默认不可修改。**
11. **Influence 统一进入 Influence Buffer。**
12. **State Resolver 按有限 Round 处理，不允许即时无界递归。**
13. **Kernel 只负责路由 Influence。**
14. **State Owner 负责解释 Influence。**
15. **Owner 遇到不支持的 Influence 时默认忽略并记录 Warning，不让 Runtime 崩溃。**
16. **Influence Type 可由插件扩展，不由 Kernel 写死。**

状态：

```text
Architecture Decision:
Influence System v0.1

Status:
Accepted
```

---

## 七、Architecture Decision #5：State Resolver（状态裁决器）【已敲定】

### 7.1 定义

State Resolver（状态裁决器）负责：

> **组织一个 Tick 内多个 Influence 对各个 State 的计算过程。**

它不负责理解具体心理、生理或社会领域规则。

正式分工：

```text
State Resolver
=
负责“组织计算”

State Owner
=
负责“领域计算”
```

### 7.2 为什么需要 State Resolver

同一个 Tick 中，一个 State 可能同时收到多条 Influence。

例如：

```text
social_rejection       0.8
social_support         0.5
physical_pain          0.6
goal_success           0.4
failure_memory_trigger 0.7
```

如果 Influence 一到就立即修改 State，处理顺序可能改变最终结果。

因此正式采用：

```text
先收齐
↓
统一分组
↓
一次交给 State Owner
↓
计算 Next State
```

### 7.3 Resolver 与 State Owner 的职责边界

State Resolver 负责：

```text
Influence 分组
Owner 查找
调用顺序
Resolution Round
异常处理
Working State 管理
确定性
Deferred Influence
```

State Owner 负责：

```text
理解 Influence
领域规则
数学模型
State Evolution
Next State 计算
```

Resolver 不自己写任何 Emotion、Body、Memory 等领域公式。

### 7.4 Kernel 不规定 Influence 的数学合并规则

例如：

```text
social_support 0.4
social_support 0.6
```

到底应该相加、取最大还是非线性组合，由目标 State Owner 决定。

正式原则：

> **Resolver 聚合调用，不负责领域数学。**

### 7.5 同一 State 每 Round 默认只 resolve 一次

一个 Round 中 Emotion 即使收到 10 条 Influence，也默认只调用一次：

```python
emotion_plugin.resolve(...)
```

一次性接收该 Round 的全部 Influence。

这样可以减少顺序依赖，并方便批量计算、测试和因果追踪。

### 7.6 Influence 到达顺序不能决定业务结果

业务结果不依赖：

```text
谁先进入 Influence Buffer
```

如需表达先后关系，必须通过：

```text
world_time
created_at
priority
influence_id
```

等明确字段。

稳定排序主要用于保证可复现性，不代表排在前面的 Influence 一定更重要。

### 7.7 Resolution Round

State Resolver 采用有限轮次传播。

例如：

```text
失业
↓
Round 1:
fear ↑
security_drive ↑

↓
Round 2:
body chronic_stress influence
find_job goal pressure ↑

↓
Round 3:
attention toward recruitment ↑
```

后续影响不继续在当前 Tick 无限递归。

### 7.8 默认最大轮数

v0.1 默认：

```python
max_resolution_rounds = 3
```

这是 Runtime 安全阀，不代表心理因果只有三层。

### 7.9 v0.1 停止条件

第一版采用：

```text
当前 Round 没有产生新的 Influence
```

则提前停止。

因此：

```text
Stop if:
1. no new influences
or
2. max_rounds reached
```

暂不要求 Kernel 理解不同 State 的数学收敛程度。

### 7.10 Deferred Influence Queue

达到最大 Round 后仍产生的新 Influence 不能丢弃。

它们进入：

```text
Deferred Influence Queue
```

并在后续 Tick 继续处理。

这样长期心理、生理和社会反馈可以沿着真实时间逐步展开。

### 7.11 Working State

Resolver 的计算结果先进入：

```text
Working State
```

正式流程：

```text
Snapshot State
↓
State Resolver
↓
State Owner resolve()
↓
Working State
↓
Validation
↓
Kernel Commit
```

因此：

> **Resolver 负责算，Kernel 最终负责提交。**

### 7.12 State Owner 失败时的处理

如果 Core State Owner 在 `resolve()` 中发生异常：

```text
当前 Resolution 失败
↓
当前 Tick 不 Commit
↓
回滚到 Snapshot
```

防止出现部分 State 已更新、部分 State 未更新的半完成状态。

### 7.13 可复现性

在：

```text
同一个 Snapshot
+
同一组 Influence
+
同一个 Random Seed
```

条件下，应尽量得到相同结果。

Resolver 不应依赖网络到达随机顺序、Python set 无意义顺序或系统真实时间。

### 7.14 Influence Priority

Influence 可以支持：

```text
priority
```

例如：

```text
normal
high
critical
```

但 Kernel 不简单规定：

```text
高 priority 自动覆盖低 priority
```

具体业务解释仍由 State Owner 决定。

### 7.15 StateResolutionResult

State Owner 的输出建议至少包括：

```text
next_state
emitted_influences
emitted_events
changed
trace
```

Python 概念结构：

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class StateResolutionResult:
    next_state: Any
    emitted_influences: tuple = ()
    emitted_events: tuple = ()
    changed: bool = True
    trace: dict | None = None
```

其中 `trace` 用于解释：

> **为什么当前 State 从 A 变成 B。**

### 7.16 State Owner 概念接口

例如：

```python
class EmotionPlugin:

    def resolve(
        self,
        current_state,
        influences,
        context,
    ) -> StateResolutionResult:
        ...
```

Kernel Resolver 只负责调用，不理解具体 Emotion 业务。

### 7.17 State Resolver 总流程

```text
Influence Buffer
↓
按 target_state 分组
↓
稳定排序
↓
找到对应 State Owner
↓
每个 Owner 每 Round resolve 一次
↓
生成 Next State
↓
进入 Working State
↓
收集 emitted_influences
↓
下一 Resolution Round
```

如果没有新的 Influence，则提前结束。

如果达到最大 Round，剩余 Influence 进入 Deferred Influence Queue。

最后：

```text
Validate Working State
↓
Kernel Commit
```

### 7.18 State Resolver v0.1 最终原则

正式接受：

1. **State Resolver 不理解具体领域规则。**
2. **Resolver 负责组织计算，State Owner 负责领域计算。**
3. **同一 Round 先收齐 Influence，再统一处理。**
4. **Influence 按 target_state 分组。**
5. **同一个 State Owner 每 Round 默认只 resolve 一次。**
6. **Owner 一次性接收该 Round 的全部相关 Influence。**
7. **Kernel 不规定 Influence 的数学合并方式。**
8. **Owner 可以产生新的二阶 Influence。**
9. **新 Influence 进入下一 Round，不即时递归。**
10. **默认 max_resolution_rounds = 3。**
11. **当前 Round 没有新 Influence 时提前停止。**
12. **达到最大 Round 后，剩余 Influence 进入 Deferred Influence Queue。**
13. **Resolver 结果先进入 Working State，不直接 Commit。**
14. **Core State Owner resolve 失败时，当前 Tick 默认回滚。**
15. **同一 Snapshot + Influence + Random Seed 应尽量可复现。**
16. **Influence 可以携带 priority，但 Kernel 不简单按 priority 覆盖业务结果。**
17. **State Owner 应返回 Resolution Trace，支持因果解释和调试。**

状态：

```text
Architecture Decision:
State Resolver v0.1

Status:
Accepted
```

---

## 八、Architecture Decision #6：Hook（生命周期钩子）【已敲定】

### 8.1 定义

Hook（生命周期钩子）表示：

> **Kernel 运行到某个固定生命周期阶段时，为 Plugin 提供的标准执行入口。**

它解决的问题是：

> **Plugin 怎么知道“现在轮到我执行了”？**

例如：

```text
Tick 开始
World 更新完成
Event 收集完成
Perception 完成
Appraisal 完成
Resolution 完成
Commit 前
Tick 结束
```

Plugin 不应通过在 Runtime 中到处写 `if` 判断来接入流程，而应注册标准 Hook。

---

### 8.2 Hook 与 Event 的区别

Event：

> **世界里发生了什么。**

Hook：

> **Runtime 当前运行到哪个阶段。**

例如：

```text
career.job.lost
```

属于 Event。

而：

```text
on_tick_start
on_after_appraisal
on_before_commit
```

属于 Hook。

正式区分：

```text
Event = 世界事实
Hook = Runtime 生命周期位置
```

---

### 8.3 Hook 与 Scheduler 的区别

Hook：

> **当 Runtime 运行到这个阶段时调用我。**

Scheduler：

> **到了某个时间点或满足某个时间条件时运行某个任务。**

例如：

```text
on_tick_end
```

是 Hook。

而：

```text
每天 23:00 执行 Reflection
```

属于 Scheduler。

正式区分：

```text
Hook = 生命周期时机
Scheduler = 时间条件
```

---

### 8.4 Hook 是生命周期“插槽”

Life Loop 可以理解成一条固定流水线：

```text
A
↓
B
↓
C
↓
D
```

Kernel 在少数重要边界开放：

```text
[Hook]
```

Plugin 可以挂到这些位置执行。

但：

> **Plugin 可以接入生命周期，不能随意重写整个生命周期。**

---

### 8.5 v0.1 核心 Hook 集合

第一版只开放少量、稳定、语义明确的核心 Hook：

```text
on_runtime_start

on_tick_start

on_after_world_update

on_after_event_collection

on_before_perception

on_after_perception

on_after_appraisal

on_before_resolution

on_after_resolution

on_before_decision

on_after_action_resolution

on_before_commit

on_after_commit

on_tick_end

on_runtime_stop
```

这些都是 Runtime 的大阶段边界，而不是具体领域内部实现细节。

---

### 8.6 Hook 不能绕过 State Ownership

Plugin 挂在某个 Hook 上，不代表获得超级权限。

例如：

```text
on_after_appraisal
```

中的 Plugin 仍然不能直接：

```python
state.emotion.sadness += 0.5
```

Hook 回调仍然必须遵守：

```text
Other State Write
→ Influence

Own State Evolution
→ State Owner / Resolver

Final State Write
→ Kernel Commit
```

Hook 只是执行时机，不是权限后门。

---

### 8.7 Hook 回调优先返回 Proposal

Plugin 在 Hook 中应优先返回：

```text
Event Proposal
Influence Proposal
Warning
其他受控 Proposal
```

而不是：

```text
自己直接写数据库
自己改正式 State
自己调用其他 Plugin
```

Kernel 接收 Hook 结果后，再统一放入：

```text
Event Queue
Influence Buffer
```

---

### 8.8 HookResult 概念结构

Python 概念模型：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class HookResult:
    events: tuple = ()
    influences: tuple = ()
    warnings: tuple = ()
```

例如：

```python
class TraumaPlugin:

    def on_after_appraisal(self, context) -> HookResult:
        ...
```

Kernel 再统一处理：

```python
result = plugin.on_after_appraisal(context)

event_queue.extend(result.events)
influence_buffer.extend(result.influences)
```

---

### 8.9 Plugin 如何注册 Hook

具体 Python API 暂不在本阶段写死。

语义上 Plugin 需要声明：

```text
我监听哪些 Hook
```

例如：

```text
on_after_appraisal
on_tick_end
```

未来可通过：

- Plugin Manifest
- Plugin Class Metadata
- Decorator

等方式实现。

具体语法在 Plugin Protocol 阶段再确定。

---

### 8.10 同一 Hook 的执行顺序

多个 Plugin 可以监听同一 Hook。

执行顺序不能随机。

正式采用：

```text
priority
+
plugin_id
```

作为稳定排序依据。

例如：

```text
priority = 100  → early
priority = 500  → normal
priority = 900  → late
```

如果 priority 相同：

```text
按 plugin_id 稳定排序
```

从而保证相同配置下尽量可复现。

注意：

> Hook priority 只表示 Hook 内执行顺序，不表示业务重要性。

---

### 8.11 Critical 与 Non-Critical Hook

Hook Registration 支持：

```text
critical = True / False
```

#### Critical Hook

例如核心状态校验发生在：

```text
on_before_commit
```

如果失败：

```text
当前 Tick 中止
↓
不 Commit
↓
回滚 Snapshot
```

#### Non-Critical Hook

例如：

```text
MetricsPlugin
```

在 `on_tick_end` 统计失败。

可以：

```text
记录 PluginHookError
↓
跳过
↓
继续 Runtime
```

不需要让整个生命 Tick 回滚。

---

### 8.12 Hook 可以产生 Event 和 Influence

Hook 中可以生成：

```text
Event Proposal
Influence Proposal
```

例如：

```text
on_after_appraisal
```

TraumaPlugin 判断当前事件触发旧创伤：

```text
target = emotion
type = trauma_trigger
```

然后放入 Influence Buffer。

再例如：

```text
on_tick_end
```

某 Plugin 发现满足生日条件，可以提出：

```text
identity.birthday.reached
```

Event。

但都不能绕过 Queue / Buffer 直接递归处理。

---

### 8.13 第三方 Plugin 第一版不能随意创建新的 Kernel Hook

正式确定：

> **Kernel Hook 集合由 AnimaFlux Core 定义。**

第三方 Plugin 第一版不能随意新增全局 Hook，例如：

```text
on_after_trauma_analysis
on_before_dream_generation
```

如果某 Plugin 需要内部生命周期：

> 在 Plugin 内部自己组织。

原因：

- 防止 Runtime 生命周期碎片化
- 防止 Plugin 相互依赖私有 Hook
- 保持 Kernel 可预测
- 保持 Plugin 协议稳定

---

### 8.14 Hook 应少而稳定

Kernel 不提供：

```text
on_emotion_before_sadness_update
on_memory_after_vector_search
```

这类领域内部 Hook。

否则 Kernel 就开始理解具体 Emotion、Memory 内部结构。

正式原则：

> **Kernel Hook 只覆盖 Runtime 生命周期边界，不覆盖领域内部实现细节。**

---

### 8.15 HookContext

Plugin 被调用时需要有限运行上下文。

例如：

```text
tick_id
world_time
phase
只读 Snapshot
受控 Runtime Services
```

这些信息应封装为：

```text
HookContext
```

而不是把整个 Kernel 对象直接交给 Plugin。

---

### 8.16 不把整个 Kernel 私有对象暴露给 Plugin

不采用：

```python
plugin.on_hook(kernel)
```

让 Plugin 可以访问整个：

```text
State Store
Plugin Manager
Scheduler
Private Runtime Object
```

正式采用：

> **最小权限上下文。**

Plugin 只能拿到：

```text
HookContext
+
明确公开的 Capability
```

不能直接依赖：

```text
kernel._private_xxx
```

---

### 8.17 Hook System v0.1 最终原则

正式接受：

1. **Hook 是 Kernel 生命周期扩展点。**
2. **Hook 与 Event 分离。**
3. **Hook 与 Scheduler 分离。**
4. **Kernel 只定义少量、稳定、语义明确的核心 Hook。**
5. **第三方 Plugin 第一版不能随意创建新的 Kernel Hook。**
6. **Plugin 可以注册一个或多个 Hook。**
7. **同一 Hook 多 Plugin 使用 priority + plugin_id 稳定排序。**
8. **Hook priority 只决定执行顺序，不代表业务重要性。**
9. **Hook 回调不能绕过 State Ownership。**
10. **Hook 回调优先返回 Event / Influence / Proposal。**
11. **Kernel 接收 HookResult 后统一进入 Event Queue / Influence Buffer。**
12. **HookContext 只暴露有限运行环境。**
13. **不把整个 Kernel 私有对象交给 Plugin。**
14. **Hook 支持 Critical / Non-Critical。**
15. **Critical Hook 失败可以中止当前 Tick。**
16. **Non-Critical Hook 失败记录错误后可继续。**
17. **Kernel Hook 只定义 Runtime 生命周期边界，不定义 Emotion / Memory 等领域内部细节。**

状态：

```text
Architecture Decision:
Hook System v0.1

Status:
Accepted
```

---

## 九、Architecture Decision #7：Capability（能力接口）【已敲定】

### 9.1 定义

Capability 表示：

> **Plugin 对外公开的标准能力接口。**

它解决的问题是：

> **一个 Plugin 想使用另一个 Plugin 的公开能力，但又不能直接依赖对方内部 State、具体类或私有实现，应该怎么做？**

正式原则：

```text
Plugin
↓
依赖 Capability
↓
不依赖具体 Provider Plugin
```

### 9.2 Capability 与 State Ownership 的关系

此前已确定：

```text
Other State Write
→ Influence
```

Capability 补充：

```text
Other State Read / Service Use
→ Capability
```

因此完整规则：

```text
Own State
→ Owner 管理

Read Other Plugin
→ Capability

Influence Other State
→ Influence
```

一句话：

> **要数据，用 Capability；要改变别人，用 Influence。**

### 9.3 为什么不能直接读取其他 Plugin 内部 State

例如 EmotionPlugin 想知道当前疲劳程度。

不能直接写：

```python
fatigue = state.body.fatigue
```

因为不同 Body Plugin 内部结构可能完全不同。

例如：

```text
SimpleBodyPlugin
→ fatigue
```

而：

```text
AdvancedBodyPlugin
→ sleep_debt
→ energy_reserve
→ metabolic_load
→ recovery_state
```

EmotionPlugin 不应该知道这些内部细节。

因此它只调用：

```text
body.status Capability
```

并询问：

```text
当前疲劳程度是多少？
```

### 9.4 Capability 是受控服务，不只是 Getter

Capability 可以公开：

```text
查询能力
搜索能力
生成能力
世界查询能力
模型调用能力
```

例如：

```text
body.status
memory.search
llm.chat
llm.structured
world.query
```

因此：

> **Plugin ≠ Capability。**

一个 Plugin 可以提供多个 Capability。

### 9.5 Capability 应按能力拆分

不建议创建一个巨大的 `BodyCapability`。

更推荐：

```text
body.status
body.sensory
body.mobility
body.reproductive
```

这样调用方只依赖真正需要的能力。

正式原则：

> **Capability 采用最小依赖设计。**

### 9.6 Capability 不能成为绕过 State Ownership 的写入后门

不提供：

```python
emotion_capability.set_sadness(...)
body_capability.set_health(...)
```

跨 State 修改仍必须通过：

```text
Influence
```

对于需要写入的服务，也优先返回或提交 Proposal，而不是直接修改正式 State。

### 9.7 Capability Registry

Kernel 维护：

```text
Capability Registry
```

它可以理解成：

> **整个 Runtime 的“能力通讯录”。**

例如：

```text
body.status
→ AdvancedBodyPlugin

memory.search
→ MemoryPlugin

llm.chat
→ OpenAIPlugin
```

调用方只查询 Capability Registry，不自行寻找具体 Plugin。

### 9.8 一个 Capability 可以有多个 Provider

例如：

```text
OpenAIPlugin
ClaudePlugin
LocalLlamaPlugin
```

都可以提供：

```text
llm.chat
```

因此：

> **一个 Capability 可以注册多个 Provider。**

Runtime 配置一个 Primary Provider 用于默认调用。

第一版不随机选择 Provider。

### 9.9 State Owner 与 Capability Provider 不同

State Owner 解决：

> **谁拥有某份 State。**

Capability Provider 解决：

> **谁提供某项服务。**

例如：

```text
state.emotion
→ 一个 Primary Owner
```

而：

```text
llm.chat
→ 可有多个 Provider
→ Runtime 选择一个 Primary Provider
```

两者不能混淆。

### 9.10 Required 与 Optional Capability

Plugin Manifest 需要区分：

```text
required capabilities
optional capabilities
```

Required 缺少时，Runtime 应在启动阶段直接报错。

Optional 存在时增强功能，不存在仍可运行。

### 9.11 Capability Version

Capability 从协议层面支持版本。

例如：

```text
capability_id = memory.search
version = 1.0
```

v0.1 不要求立即实现完整复杂版本解析，但协议设计必须预留版本。

### 9.12 Core Capability 与 Extension Capability

Core Capability 由 AnimaFlux 官方协议定义，例如：

```text
body.status
memory.search
llm.chat
world.query
```

第三方 Plugin 也可以定义 Extension Capability，例如：

```text
dream.symbol_analysis
culture.chinese_ritual
```

### 9.13 Capability Contract

如果两个 Plugin 都声明：

```text
provides body.status
```

则必须遵守同一个 Contract。

正式原则：

> **相同 Capability ID 必须遵守相同接口协议。**

### 9.14 Python 使用 Protocol 表达 Contract

Python 优先使用：

```python
from typing import Protocol


class BodyStatusCapability(Protocol):

    def get_fatigue_level(self, agent_id: str) -> float:
        ...

    def get_pain_level(self, agent_id: str) -> float:
        ...
```

具体 Plugin 不必继承巨大基类，只要符合协议即可。

### 9.15 Capability 返回 View / DTO，不直接返回内部 State

不采用：

```python
def get_body_state():
    return self._state
```

更推荐返回只读公开视图：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class BodyStatusView:
    fatigue: float
    pain: float
    arousal: float
```

因此：

> **Capability 暴露公开 View，不暴露内部 State 对象。**

### 9.16 Capability 查询必须基于明确 Runtime Context

Life Loop 中可能同时存在：

```text
Snapshot State
Working State
Committed State
```

Capability 不能自行读取所谓“最新状态”。

调用必须基于明确 Runtime Context，由 Runtime 决定当前阶段允许读取哪一份状态视图。

### 9.17 同步与异步 Capability

Capability Contract 可以自行定义同步或异步接口。

例如：

```python
def get_fatigue_level(...):
    ...
```

或：

```python
async def generate(...):
    ...
```

Kernel 不强制所有 Capability 全部 sync 或全部 async。

### 9.18 Capability 可见性

只有 Plugin 明确注册到 Capability Registry 的能力，才对其他 Plugin 可见。

内部对象、私有方法、私有 State 默认不可访问。

### 9.19 Capability 数据流

读取：

```text
EmotionPlugin
↓
Capability Registry
↓
body.status
↓
BodyPlugin
↓
BodyStatusView
```

影响：

```text
EmotionPlugin
↓
Influence Buffer
↓
target = body
↓
BodyPlugin
```

正式牢记：

```text
Capability = 问
Influence = 影响
```

### 9.20 Capability System v0.1 最终原则

正式接受：

1. **Capability 是 Plugin 对外公开的标准能力接口。**
2. **Plugin 依赖 Capability，而不是依赖具体 Plugin 实现。**
3. **跨 Plugin 读取公开信息优先通过 Capability。**
4. **跨 State 修改仍必须通过 Influence。**
5. **Capability 尽量按能力拆分，遵循最小依赖。**
6. **一个 Plugin 可以提供多个 Capability。**
7. **一个 Capability 可以有多个 Provider。**
8. **Runtime 为同一 Capability 选择 Primary Provider。**
9. **Capability Registry 由 Kernel 管理。**
10. **Plugin Manifest 区分 Required 和 Optional Capability。**
11. **Required Capability 缺失时，在 Runtime 启动阶段直接失败。**
12. **Capability 从协议层面支持版本。**
13. **Core Capability 由 AnimaFlux 定义标准 Contract。**
14. **第三方可以定义 Extension Capability。**
15. **相同 Capability ID 的 Provider 必须遵守相同 Contract。**
16. **Python 优先使用 `Protocol` 表达 Capability Contract。**
17. **Capability 返回公开 View / DTO，不直接暴露内部可变 State。**
18. **Capability 调用必须基于明确 Runtime Context。**
19. **Capability 可以同步或异步，由具体 Contract 定义。**
20. **只有明确注册的 Capability 才对其他 Plugin 可见。**

状态：

```text
Architecture Decision:
Capability System v0.1

Status:
Accepted
```

---

## 十、Architecture Decision #8：Scheduler（调度器）【已敲定】

### 10.1 定义

Scheduler 负责：

> **决定某个 Process / Task 在什么 World Time 应该执行。**

正式区分：

```text
Event = 发生了什么
Hook = Runtime 运行到哪一步
Scheduler = 什么时候运行某个任务
```

### 10.2 Scheduler 只基于 World Time

生日、衰老、吃药、目标截止日等全部使用 AnimaFlux World Time，而不是服务器真实时间。

### 10.3 v0.1 支持四类 Schedule

```text
1. Every Tick
2. Fixed Interval
3. Calendar Schedule
4. One-shot
```

Every Tick Process 必须接收 `delta_time`，不能假设 Tick 长度固定。

### 10.4 Condition-based Trigger 暂不归 Scheduler

Scheduler v0.1 只解决时间问题。

状态条件触发交给 Hook、Event、Rule Process、Interaction Plugin。

### 10.5 Time Skip 与 Catch-up Policy

时间快进时，Scheduler 必须判断哪些任务需要补执行、合并执行或跳过。

v0.1 支持：

```text
RUN_ALL
RUN_ONCE
COALESCE
SKIP
```

COALESCE 用于把大量重复任务合并成一次批量计算，是长期人生模拟的重要基础。

### 10.6 next_due_time

Time Engine 快进前，应先询问：

```text
Scheduler.next_due_time()
```

关键 Schedule 不能被直接跨过。

正式原则：

> **平淡时间可以压缩，关键节点不能直接跨过去。**

### 10.7 Schedule 保存 Task 描述，不保存 Python callback

Schedule 持久化：

```text
task_type / process_id
```

例如：

```text
reflection.daily
body.aging
goal.deadline_check
```

不能把内存中的 Python 函数对象作为持久化协议。

### 10.8 Schedule 基础字段

概念字段：

```text
schedule_id
owner_plugin
task_type
schedule_type
next_run_at
priority
catch_up_policy
payload
enabled
```

### 10.9 owner_plugin

Schedule 必须记录 owner_plugin，便于 Plugin 卸载、禁用、升级时清理或迁移相关任务，避免“幽灵 Schedule”。

### 10.10 task_type

Kernel 只负责：

```text
时间到了
↓
根据 task_type 找执行者
↓
执行
```

业务语义由 Plugin 定义。

### 10.11 Schedule 到期后不能直接修改 Core State

Scheduler 只触发 Process。

Scheduled Process 仍需通过：

```text
Event
Influence
Proposal
```

进入正常 Life Loop。

### 10.12 同时到期任务稳定排序

采用：

```text
due_time
↓
priority
↓
schedule_id
```

保证可复现性。

priority 只表示调度顺序，不表示业务重要性。

### 10.13 Schedule Failure

Schedule Task 可区分：

```text
critical
non-critical
```

Critical 失败可以导致当前 Tick 回滚。

Non-Critical 失败记录错误后继续。

同时建议记录：

```text
last_run_at
last_status
failure_count
```

### 10.14 Retry Policy

v0.1 不采用无限自动重试。

协议预留：

```text
retry_policy
max_retries
```

后续实现再细化。

### 10.15 Plugin 可以动态提出 Schedule 变更

Plugin 可以提交：

```text
CreateScheduleProposal
CancelScheduleProposal
RescheduleProposal
PauseScheduleProposal
ResumeScheduleProposal
```

Kernel 校验后再真正修改 Scheduler。

### 10.16 Schedule 与 Event 的区别

Schedule：

> **未来准备执行的任务。**

Event：

> **已经发生的事实。**

未来可能变化，因此 Schedule 可以 reschedule / pause / cancel。

Event 默认不可修改。

### 10.17 Scheduler 属于 Kernel

正式确定：

```text
Scheduler → Kernel
```

具体 Task 语义属于 Plugin。

### 10.18 Scheduler v0.1 最终原则

正式接受：

1. **Scheduler 只负责基于 World Time 的时间调度。**
2. **Scheduler 与 Hook、Event 分离。**
3. **v0.1 支持 Every Tick、Fixed Interval、Calendar、One-shot 四类 Schedule。**
4. **条件触发暂不归 Scheduler 管。**
5. **Schedule 使用 World Time，不使用系统真实时间。**
6. **Every Tick Process 必须接收 delta_time。**
7. **Schedule 支持 Catch-up Policy。**
8. **Catch-up 支持 RUN_ALL、RUN_ONCE、COALESCE、SKIP。**
9. **Scheduler 为 Time Engine 提供 next_due_time。**
10. **支持通过 COALESCE 压缩长期平淡时间。**
11. **关键 Schedule / Event 不允许被 Time Skip 直接跨过。**
12. **Schedule 保存可持久化 task_type，不直接保存 Python callback。**
13. **Schedule 记录 owner_plugin。**
14. **同时到期任务使用 due_time + priority + schedule_id 稳定排序。**
15. **priority 只表示执行顺序，不表示业务重要性。**
16. **Scheduler 不直接修改 Core State。**
17. **Scheduled Process 仍通过 Event / Influence / Proposal 影响系统。**
18. **Plugin 可以动态提出 Create / Cancel / Reschedule / Pause / Resume Proposal。**
19. **Kernel 校验 Proposal 后才真正修改 Schedule。**
20. **Schedule 可以修改和取消，因为它描述未来。**
21. **Scheduler 属于 Kernel；具体 Task 语义属于 Plugin。**

状态：

```text
Architecture Decision:
Scheduler v0.1

Status:
Accepted
```

---

## 十一、Architecture Decision #9：Plugin Manifest + Plugin Lifecycle【已敲定】

### 11.1 Plugin Manifest 的作用

Plugin Manifest 是插件的静态声明，用于告诉 Runtime：

```text
我是谁
我的版本是多少
我拥有哪些 State
我提供哪些 Capability
我依赖哪些 Capability
我监听哪些 Hook
我提供哪些 Task Type
我和哪个 Kernel 版本兼容
```

它不保存 Runtime State。

---

### 11.2 plugin_id 与 name 分离

```text
plugin_id
= 稳定机器标识

name
= 人类可读名称
```

例如：

```text
plugin_id:
animaflux.emotion.occ

name:
OCC Emotion Model
```

`plugin_id` 发布后尽量保持稳定。

---

### 11.3 Plugin Version

Plugin 版本采用：

```text
major.minor.patch
```

例如：

```text
1.0.0
1.1.0
1.1.1
2.0.0
```

Plugin Version 与 State Schema Version 分离。

---

### 11.4 两层 Manifest 结构

正式采用：

```text
pyproject.toml
+
Python PluginManifest
```

#### pyproject.toml 负责

```text
Python 包身份
包版本
Python 依赖
AnimaFlux Entry Point
```

#### Python PluginManifest 负责

```text
State Ownership
Capability
Hook
Task Type
Kernel Compatibility
State Schema Version
```

不额外把 YAML 作为核心必需协议，避免多份元数据长期不一致。

---

### 11.5 Plugin Discovery 使用 Python Entry Point

Plugin 安装后通过 Python Entry Point 被 Runtime 自动发现。

正式区分：

```text
Discovery
≠
Load
```

Discovery 只确认：

```text
系统里有哪些 Plugin
```

并不立即执行 Plugin 代码。

---

### 11.6 Plugin Lifecycle

正式生命周期：

```text
Installed
↓
Discovered
↓
Enabled / Selected
↓
Validated
↓
Loaded
↓
Initialized
↓
Started
↓
Running
↓
Stopping
↓
Stopped
↓
Unloaded
```

---

### 11.7 Enabled 与 Installed 分离

一个 Plugin 被安装，不代表 Runtime 一定启用它。

例如：

```text
BasicEmotionPlugin
OCCEmotionPlugin
PADEmotionPlugin
```

可以同时安装，但当前 Runtime 只能选择一个作为：

```text
state.emotion Primary Owner
```

---

### 11.8 Validated 阶段

Runtime 在真正运行前检查：

```text
plugin_id 是否重复
Kernel 版本是否兼容
Required Capability 是否存在
State Owner 是否冲突
Hook 是否存在
Capability Contract 是否兼容
Task Type 是否冲突
依赖图是否存在循环
```

原则：

> **Fail Fast，在 Runtime 启动前发现结构问题。**

---

### 11.9 Required 与 Optional 依赖

Required Capability：

```text
形成硬依赖
```

缺失则 Plugin 无法启动。

Optional Capability：

```text
有则增强
无则降级
```

不形成硬启动依赖。

---

### 11.10 Required Dependency Graph

Required Capability 会形成 Plugin 依赖图。

例如：

```text
MemoryPlugin
↓
ReflectionPlugin
```

Kernel 根据依赖关系决定初始化顺序。

如果：

```text
A requires B
B requires A
```

形成循环依赖，则在 Validated 阶段直接报错。

Required 依赖图必须能够进行拓扑排序。

---

### 11.11 Manifest 声明内容

PluginManifest 至少声明：

```text
plugin_id
name
version
kernel_compatibility
owns_states
provides_capabilities
requires_capabilities
optional_capabilities
hooks
task_types
state_schema_version
```

Python 概念结构：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str

    kernel_compatibility: str

    owns_states: tuple[str, ...] = ()

    provides_capabilities: tuple[str, ...] = ()
    requires_capabilities: tuple[str, ...] = ()
    optional_capabilities: tuple[str, ...] = ()

    hooks: tuple[str, ...] = ()
    task_types: tuple[str, ...] = ()

    state_schema_version: int | None = None
```

Manifest 是静态、只读声明。

---

### 11.12 Plugin 初始化阶段

Initialized 阶段允许：

```text
读取配置
准备内部缓存
准备模型
注册内部资源
```

但不能随意修改 Agent 正式 State。

---

### 11.13 Start 阶段

所有 Enabled Plugin 完成：

```text
Validation
Initialization
Dependency Ordering
```

以后，Runtime 再进入 Started / Running。

避免：

```text
Plugin A 已开始运行
Plugin B 还没准备好
```

---

### 11.14 Stop / Unload

Plugin 停止时可以：

```text
停止内部任务
释放模型资源
刷写缓存
关闭外部连接
```

Stop 阶段主要负责工程资源清理，不用于重大生命 State 修改。

---

### 11.15 v0.1 禁止 Core State Owner 运行中热替换

正式确定：

> **第一版本禁止 Core State Owner 在 Runtime Running 状态下热替换。**

例如不能在 Agent 运行过程中直接：

```text
OCCEmotionPlugin
↓
立即替换为
PADEmotionPlugin
```

因为这涉及：

```text
State Schema Migration
Deferred Influence
Capability Provider
Hook
Schedule
Working State
```

等复杂一致性问题。

正式流程：

```text
Stop Runtime
↓
Validate Replacement
↓
Migrate State
↓
Replace Owner
↓
Restart Runtime
```

普通无状态辅助 Plugin 的动态 Enable / Disable 可作为后续增强能力研究，但不属于 v0.1 核心要求。

---

### 11.16 Core State Owner 卸载约束

如果 Plugin 拥有 Core State：

```text
state.emotion
state.body
state.memory
...
```

则不能在 Runtime 运行中直接卸载并留下：

```text
State exists
but no owner
```

必须：

```text
停止 Runtime
+
指定 Replacement Owner
或
终止该 Runtime
```

---

### 11.17 Plugin 禁用后的 Schedule

Plugin Disable / Unload 时：

```text
owner_plugin = 当前 Plugin
```

的 Schedule 默认：

```text
Pause
```

而不是直接永久删除。

这样未来重新启用 Plugin 时可以继续恢复或迁移。

---

### 11.18 Capability 注销

Plugin 禁用或卸载前，Kernel 必须检查：

```text
是否有其他 Enabled Plugin
仍然 Required 依赖它提供的 Capability
```

如果有：

> 禁止直接卸载，除非先替换 Provider 或停用依赖方。

---

### 11.19 Plugin Version 与 State Schema Version 分离

例如：

```text
plugin_version = 1.3.0
state_schema_version = 2
```

Plugin 算法升级不一定意味着 State Schema 改变。

State Schema 改变时，由 Plugin 提供 Migration。

Kernel 负责安全执行迁移事务。

---

### 11.20 Plugin Manifest + Lifecycle v0.1 最终原则

正式接受：

1. **Plugin 使用稳定 plugin_id 与独立 name。**
2. **Plugin Version 使用 major.minor.patch。**
3. **采用 pyproject.toml + Python PluginManifest 两层结构。**
4. **Plugin Discovery 使用 Python Entry Point。**
5. **Discovery 与 Load 分离。**
6. **Installed 与 Enabled 分离。**
7. **生命周期为 Installed → Discovered → Enabled → Validated → Loaded → Initialized → Started → Running → Stopping → Stopped → Unloaded。**
8. **启动前完成 State Owner、Capability、Hook、Task、版本兼容性校验。**
9. **Required Capability 形成硬依赖。**
10. **Optional Capability 不形成硬依赖。**
11. **Required Dependency Graph 不允许循环。**
12. **Manifest 声明 owns_states / provides / requires / optional / hooks / task_types。**
13. **Manifest 是静态声明，不保存 Runtime State。**
14. **第一版本禁止 Core State Owner 运行中热替换。**
15. **Core State Owner 替换需 Stop Runtime → State Migration → Replace → Restart。**
16. **Plugin Disable / Unload 时，其 Schedule 默认 Pause。**
17. **Capability 注销前必须重新检查依赖完整性。**
18. **Plugin Version 与 State Schema Version 分离。**
19. **State Schema Migration 由 Plugin 提供，Kernel 负责事务性执行。**

状态：

```text
Architecture Decision:
Plugin Manifest + Lifecycle v0.1

Status:
Accepted
```

---

## 十二、下一阶段：Runtime 高层架构补全

目前已完成 Plugin Runtime 的大部分基础协议。

下一步不再继续按零散小概念推进，而需要先从高层检查还缺哪些“系统级支柱”。

待讨论的主要模块包括：

```text
Runtime Context
Persistence / Event Store / Snapshot
Transaction / Commit
Error Isolation
Configuration
World Runtime
Process / Task Protocol
Observability / Trace
Security / Plugin Permission
Testing / Replay / Determinism
```

这些模块将共同组成 AnimaFlux Runtime v1 的完整技术架构。

## 十二、Architecture Decision #10A：Process Protocol Core（Process 核心协议）【已敲定】

### 12.1 定义

Process 是：

> **AnimaFlux Runtime 中统一的可执行生命逻辑单元。**

它用于承载真正的领域逻辑，例如：

```text
Perception Process
Appraisal Process
Reflection Process
Decision Process
Memory Formation Process
Body Aging Process
Goal Review Process
```

---

### 12.2 Plugin 与 Process 的关系

正式区分：

```text
Plugin
=
一个功能模块 / 插件包

Process
=
Plugin 内部可被 Runtime 调用执行的逻辑单元
```

一个 Plugin 可以包含一个或多个 Process。

例如：

```text
EmotionPlugin
├── EmotionDecayProcess
├── EmotionAppraisalProcess
└── EmotionResolutionProcess
```

---

### 12.3 Hook / Scheduler / Life Loop 与 Process 的关系

正式采用：

```text
Hook
↓
触发 Process

Scheduler
↓
触发 Process

Life Loop Stage
↓
触发 Process
```

因此 Runtime 不需要为 Hook、Scheduler、Life Loop 分别发明不同的领域逻辑调用方式。

---

### 12.4 Process 的标准调用模型

Process 不应定义任意混乱参数：

```python
def run(a, b, c, d, whatever):
    ...
```

正式方向：

```python
result = process.run(context)
```

其中：

```text
context
=
Runtime Context
```

返回：

```text
ProcessResult
```

---

### 12.5 Process 不直接修改 Core State

Process 不能绕过：

```text
State Ownership
Influence
State Resolver
Kernel Commit
```

直接修改正式 Core State。

正式数据流：

```text
Process
↓
Event / Influence / Action Proposal / Schedule Proposal
↓
Runtime
↓
Resolver / Scheduler / Action Resolver
↓
Working State
↓
Commit
```

---

### 12.6 Process 与 State Owner 的区别

Process：

> **执行一段生命逻辑。**

State Owner：

> **决定自己拥有的 State 最终如何变化。**

例如：

```text
AppraisalProcess
```

可以生成：

```text
target = emotion
type = social_evaluation_threat
```

但最终 Emotion State 如何变化，仍由：

```text
Emotion State Owner
```

负责。

---

### 12.7 ProcessResult

Process 应优先返回受控结果，而不是直接产生不可追踪副作用。

概念上可包含：

```text
events
influences
actions
schedule proposals
warnings
trace
```

Kernel 再统一接入对应 Runtime 子系统。

---

### 12.8 Process Protocol Core v0.1 最终原则

正式接受：

1. **Process 是 Runtime 中统一的可执行生命逻辑单元。**
2. **一个 Plugin 可以包含一个或多个 Process。**
3. **Hook、Scheduler、Life Loop Stage 都可以触发 Process。**
4. **Process 使用统一 Runtime Context 作为主要执行输入。**
5. **Process 返回 ProcessResult。**
6. **Process 不直接修改其他 Core State。**
7. **Process 通过 Event / Influence / Action Proposal / Schedule Proposal 等受控结果影响 Runtime。**
8. **State Owner 与普通 Process 分工明确：Process 负责逻辑，Owner 负责 State 最终解释。**

状态：

```text
Architecture Decision:
Process Protocol Core v0.1

Status:
Accepted
```

---

## 十三、Architecture Decision #10B：Runtime Context【已敲定】

Runtime Context 是 Kernel 为一次 Process 执行提供的受控运行环境。它不是整个 Kernel，也不是万能参数字典。

它同时承担：
- 数据版本边界
- 权限边界
- 时间边界
- 信息可见性边界
- 随机性边界
- Trace 边界

### 13.1 结构

```text
RuntimeContext
├── ExecutionContext
├── TimeContext
├── StateView
├── EventView
├── WorldView
├── CapabilityAccess
├── RandomService
└── TraceContext
```

### 13.2 ExecutionContext

至少包含：

```text
runtime_id
agent_id
tick_id
plugin_id
process_id
phase
resolution_round
```

### 13.3 TimeContext

至少包含：

```text
world_time
delta_time
```

所有生命逻辑基于 World Time，不使用服务器真实时间。

### 13.4 StateView 版本规则

Process 不允许自行选择任意 State 版本。

Resolution 前的 Process 默认读取：

```text
TickSnapshotView
```

State Resolution 采用逐 Round 冻结：

```text
Round 1 读取 Tick Snapshot S0
→ 生成 Working S1

Round 2 统一读取冻结后的 S1
→ 生成 Working S2

Round 3 统一读取冻结后的 S2
→ 生成 Working S3
```

Resolution 后的 Goal Review / Decision / Planning 等读取：

```text
ResolvedWorkingView
```

概念上区分：

```text
TickSnapshotView
ResolutionRoundView
ResolvedWorkingView
CommittedView
```

### 13.5 Capability 绑定 Context

Capability Provider 不能绕过 Runtime Context 自行读取数据库“最新状态”。

Capability 调用必须读取当前 Phase 对应的 StateView。

### 13.6 EventView 与 WorldView

Process 不默认获得完整 Event Log 或完整 Objective World。

EventView 与 WorldView 必须根据：

```text
Agent Scope
Location
Visibility
Sensory Capability
Permission
Current Phase
```

进行限制。

因此 Agent 无法通过 Plugin 绕过感知机制获得上帝视角。

### 13.7 RandomService

Plugin 不应自行使用无管理的全局随机源。

统一通过：

```python
context.random
```

由 Kernel 管理 Random Seed，以支持 Replay、科研实验和 Debug。

### 13.8 TraceContext

TraceContext 用于记录：

```text
trace_id
tick_id
process_id
parent_trace_id
causal_refs
```

从而形成：

```text
Objective Event
→ Perception
→ Appraisal
→ Influence
→ Resolution
→ State Change
```

完整因果链。

### 13.9 Runtime Context 不暴露的内容

默认不直接提供：

```text
数据库连接
完整 State Store
完整 Event Store
Plugin Manager
Scheduler 内部对象
Kernel 私有对象
其他 Agent 私有 State
任意写权限
系统真实时间
未管理的全局随机数
```

### 13.10 Process 输出

Runtime Context 是受控执行环境。

Process 的变化结果仍然通过：

```text
ProcessResult
```

返回 Event / Influence / Action Proposal / Schedule Proposal / Warning / Trace。

不能通过修改 Context 偷偷改变 Runtime。

### 13.11 Runtime Context v0.1 最终原则

正式接受：

1. Runtime Context 是 Process 的受控执行环境，不是整个 Kernel。
2. Context 采用职责拆分结构，不做万能字典。
3. Process 不允许自行选择任意 State 版本。
4. Resolution 前 Process 默认读取 TickSnapshotView。
5. 每个 Resolution Round 读取上一 Round 冻结后的 ResolutionRoundView。
6. Decision / Planning 等 Resolution 后 Process 读取 ResolvedWorkingView。
7. Capability 调用必须绑定当前 Runtime Context。
8. EventView / WorldView 必须遵守 Agent 信息边界。
9. 随机性统一通过 Kernel RandomService 获取。
10. TraceContext 负责 Process 级因果追踪。
11. Runtime Context 不暴露 Kernel 私有对象和任意写权限。
12. Process 通过 ProcessResult 输出，不通过 Context 直接修改 Runtime。

状态：

```text
Architecture Decision:
Runtime Context v0.1

Status:
Accepted
```

---

# 技术架构阶段 A：Plugin Runtime Protocol【阶段完成】

截至当前，阶段 A 已正式敲定：

```text
#1  Kernel / Plugin Boundary
#2  State Ownership
#3  Event System
#4  Influence System
#5  State Resolver
#6  Hook System
#7  Capability System
#8  Scheduler
#9  Plugin Manifest + Lifecycle
#10 Process Protocol + Runtime Context
```

阶段 A 的目标是：

> 定义 Plugin 如何被发现、如何运行、如何读信息、如何传递影响、如何调度、如何安全参与 Life Loop。

当前状态：

```text
Status:
Frozen for Runtime v0.1
```

除非后续 Stage B / C 暴露真实架构冲突，否则不再随意修改阶段 A 的核心协议。

---

# 技术架构阶段 B：Runtime Infrastructure

下一阶段解决：

> 一个数字生命活几十年，它的状态、历史、事务、回滚、持久化和回放到底怎么保证。

第一大块：

```text
State Store + Persistence
```

将依次讨论：

```text
1. State Store 的职责和边界
2. State Namespace 如何组织
3. Snapshot / Working State / Commit 如何存
4. Event Log 如何持久化
5. Snapshot 与 Event Log 的关系
6. Memory 等大规模状态如何存储
7. Transaction / Rollback
8. Checkpoint / Save / Load
9. Replay
10. Schema Migration
```

## 十四、Architecture Decision #11A：State Store Core（状态存储核心）【已敲定】

### 14.1 定义

State Store 是：

> **AnimaFlux 当前生命状态的统一管理中心。**

它负责：

```text
State 当前版本
Snapshot
Working State
Commit
Rollback
State Namespace 管理
```

但不负责理解具体领域语义。

---

### 14.2 State Owner 与 State Store 分工

正式区分：

```text
State Owner
=
状态是什么意思、如何变化

State Store
=
状态现在是哪一版、如何保存、如何提交
```

例如：

```text
EmotionPlugin
```

负责：

```text
social_rejection 如何影响 emotion
```

State Store 负责：

```text
emotion 当前 Committed 版本
Tick Snapshot
Working State
最终 Commit
```

---

### 14.3 Plugin 不控制底层持久化

Plugin 不直接决定：

```text
SQLite
PostgreSQL
JSON
文件
其他数据库
```

Plugin 只定义：

```text
State Schema
State Evolution
Validation
Migration
```

真正持久化由 Runtime Infrastructure 统一负责。

---

### 14.4 Core State 统一进入 State Store

所有 Core State 均由统一 State Store 管理。

概念上按：

```text
agent_id
+
state_namespace
```

组织。

例如：

```text
agent-001
├── identity
├── body
├── personality
├── emotion
├── drive
├── belief
├── value
├── goal
├── relationship
├── world_model
├── self_model
└── narrative
```

Memory 等超大历史型状态允许后续使用 Specialized Store。

---

### 14.5 三类核心状态版本

正式区分：

```text
Committed State
Tick Snapshot
Working State
```

#### Committed State

上一个成功 Tick 已正式提交的状态。

#### Tick Snapshot

当前 Tick 开始时，从 Committed State 冻结出的稳定视图。

#### Working State

当前 Tick 计算中的候选新状态。

---

### 14.6 Commit / Rollback 语义

正式流程：

```text
Committed S100
↓
Create Tick Snapshot
↓
Life Loop
↓
Working S101
↓
Validation
├── Success → Commit → Committed S101
└── Failure → Discard → Committed 仍为 S100
```

Tick 只有整体成功后，Working State 才能成为新的正式状态。

---

### 14.7 不保存一个巨大不可拆分的 Agent 对象

不采用：

```text
一个超大 AgentState
里面塞全部状态和全部历史
```

作为唯一持久化单元。

原因：

```text
不同 State 增长模式不同
Memory 可能巨大
Relationship 可能持续增长
Event Log 可能达到百万级
```

正式采用 Namespace 级管理。

---

### 14.8 State Store 不等于数据库

State Store 是：

> **架构接口 / 运行时角色。**

底层 Persistence Backend 可以替换。

例如：

```text
InMemory Backend
SQLite Backend
PostgreSQL Backend
其他后端
```

Plugin 不感知具体 Backend。

---

### 14.9 Specialized Store 预留

以下内容后续允许脱离普通 Core State Snapshot，进入专门存储：

```text
Memory Store
Event Store
Trace Store
Large Relationship History
Vector Index
```

核心原则：

> **热状态与大规模历史数据不强行混在一个 State Blob 里。**

---

### 14.10 State Store Core v0.1 最终原则

正式接受：

1. **State Store 属于 Kernel / Runtime Infrastructure。**
2. **State Owner 管领域语义，State Store 管版本与提交。**
3. **Plugin 不直接控制底层持久化。**
4. **所有 Core State 统一经过 State Store 管理。**
5. **至少区分 Committed State、Tick Snapshot、Working State。**
6. **Tick 整体成功后才 Commit。**
7. **Tick 失败时 Working State 丢弃，Committed State 保持不变。**
8. **State 按 agent_id + state_namespace 组织。**
9. **State Store 是抽象接口，不等同于某种数据库。**
10. **Memory / Event Log 等大规模数据允许使用 Specialized Store。**

状态：

```text
Architecture Decision:
State Store Core v0.1

Status:
Accepted
```

---

## 十五、Architecture Decision #11B：Snapshot Strategy【已敲定】

### 15.1 核心方案

正式采用：

> **Immutable State Version + Namespace-level Copy-on-Write**

中文：

> **不可变状态版本 + 按 State Namespace 写时复制。**

不采用每个 Tick 对整个 Agent State 做全量 `deepcopy`。

---

### 15.2 Committed State Version 默认不可原地修改

一旦某个 State Version 成为正式版本：

```text
emotion_v20
body_v31
goal_v12
```

就默认不可原地修改。

状态变化通过：

```text
旧版本
↓
创建新版本
```

完成。

---

### 15.3 Tick Snapshot 主要保存稳定版本引用

Tick 开始时，不要求把所有 State 数据完整复制一份。

概念上：

```text
Tick Snapshot
=
Namespace → Immutable Version Reference
```

例如：

```text
identity    → identity_v5
body        → body_v31
emotion     → emotion_v20
goal        → goal_v12
value       → value_v8
```

---

### 15.4 Namespace-level Copy-on-Write

只有真正发生变化的 Namespace 才创建新版本。

例如当前 Tick：

```text
Body 改变
Emotion 改变
```

则：

```text
body_v31    → body_v32
emotion_v20 → emotion_v21
```

而：

```text
goal_v12
value_v8
narrative_v4
```

保持原版本引用。

---

### 15.5 Working State

Working State 本质上是：

> **一张候选 Namespace → Version 映射。**

例如：

```text
Working State
├── identity    → identity_v5
├── body        → body_v32
├── emotion     → emotion_v21
├── goal        → goal_v12
└── value       → value_v8
```

未变化 Namespace 继续复用旧版本。

---

### 15.6 Resolution Round 同样使用版本化视图

例如：

```text
Round 0:
emotion_v20
body_v31

Round 1:
emotion_v21
body_v31

Round 2:
emotion_v21
body_v32
```

同一个 Round 读取统一冻结版本。

下一 Round 才读取上一 Round 的新结果。

---

### 15.7 Rollback

由于旧 Committed Version 从未被原地修改：

```text
Tick Failure
↓
Discard Working Version Map
↓
Committed State 保持不变
```

因此 Rollback 不需要逐字段“改回去”。

---

### 15.8 Memory / Event Log 不参与普通全量 State Copy

大型历史数据：

```text
Memory Store
Event Store
Trace Store
```

不随每个 Tick Snapshot 做完整复制。

Snapshot 只需要保存：

```text
版本引用
Cursor
Store Revision
```

等必要位置标记。

---

### 15.9 Tick Snapshot 与 Checkpoint 分离

正式区分：

```text
Tick Snapshot
=
短生命周期运行时稳定视图
```

```text
Checkpoint
=
用于长期恢复、Replay、Branch 的持久化存档点
```

每个 Tick 可以存在 Snapshot，但不意味着每个 Tick 都永久保存 Checkpoint。

---

### 15.10 临时版本回收

仅用于当前：

```text
Tick
Resolution Round
Rollback
```

的临时 State Version，在不再被：

```text
Committed State
Checkpoint
Branch
Working State
```

引用后，可以被清理。

---

### 15.11 Life Branch 能力预留

由于历史版本可共享，架构上预留：

```text
Checkpoint
↓
Branch A
Branch B
```

例如：

```text
30岁 Checkpoint
├── 接受上海工作
└── 拒绝上海工作
```

两个分支可以共享 30 岁以前的大量历史版本。

---

### 15.12 Snapshot Strategy v0.1 最终原则

正式接受：

1. **Committed State Version 默认不可原地修改。**
2. **Tick Snapshot 主要由稳定 State Version 引用组成。**
3. **State 按 Namespace 进行 Copy-on-Write。**
4. **只有变化的 Namespace 创建新版本。**
5. **Working State 是 Namespace → Version 的候选映射。**
6. **Resolution Round 使用冻结版本视图，避免同 Round 顺序污染。**
7. **Tick 失败时丢弃 Working Version，旧 Committed Version 不受影响。**
8. **Memory / Event Log 等大型历史数据不参与普通全量 State Copy。**
9. **Tick Snapshot 与 Persistent Checkpoint 分离。**
10. **无人引用的临时版本可以回收。**
11. **架构预留共享历史版本的 Life Branch / Experiment Branch 能力。**

状态：

```text
Architecture Decision:
Snapshot Strategy v0.1

Status:
Accepted
```

---

## 十六、Architecture Decision #11C：Checkpoint + Persistence【已敲定】

### 16.1 三个概念严格分离

正式区分：

```text
Tick Snapshot
=
当前 Tick 计算时使用的稳定状态视图

Durable Commit
=
当前 Tick 成功后，状态变化正式生效并可靠持久化

Checkpoint
=
用于快速恢复、Replay、Branch 的长期一致性恢复点
```

三者不能混为一体。

---

### 16.2 每个成功 Tick 都必须形成 Durable Commit

不采用：

```text
只有创建 Checkpoint 时才写持久化
```

否则两个 Checkpoint 之间的生命经历可能因崩溃而丢失。

正式采用：

```text
每个成功 Tick
→ Durable Commit

周期 / 重大节点 / 手动等
→ Checkpoint
```

---

### 16.3 Event Log 不是唯一 State 真相来源

AnimaFlux 不采用纯 Event Sourcing 作为唯一恢复机制。

原因包括：

```text
LLM 输出未必长期严格可复现
外部 Provider 可能发生变化
Plugin 版本可能变化
随机过程可能复杂
历史模型环境可能无法完整重建
```

因此：

> **已经 Commit 的 State 也必须可靠持久化。**

---

### 16.4 双轨持久化

正式采用：

```text
State Persistence
+
Event Log
```

其中：

```text
State
=
“现在是谁 / 当前是什么状态”

Event Log
=
“经历了什么”
```

两者职责分离。

---

### 16.5 Commit Journal

增加：

```text
Commit Journal
```

记录每个成功 Tick：

```text
哪些 State Namespace
从哪个 Version
变成哪个 Version
```

例如：

```text
Tick 101:
body_v20 → body_v21
emotion_v30 → emotion_v31

Tick 102:
goal_v8 → goal_v9
```

正式职责区分：

```text
Event Log
= 发生了什么

Commit Journal
= 哪些 State Version 正式生效

Checkpoint
= 从哪里可以快速恢复
```

---

### 16.6 Checkpoint 不是巨大 Python 对象副本

Checkpoint 主要保存：

> **恢复所需版本引用 + Runtime Metadata。**

概念结构：

```text
RuntimeCheckpoint
├── checkpoint_id
├── runtime_id
├── world_time
├── tick_id
├── world_state_ref
├── agent_state_version_maps
├── event_log_cursor
├── commit_journal_cursor
├── memory_store_revision
├── scheduler_revision
├── deferred_influence_revision
├── random_state
├── plugin_environment
└── state_schema_versions
```

---

### 16.7 Runtime / World 是最高一致性 Checkpoint 单位

多 Agent 世界中不能分别在不同时间保存 Agent A、Agent B、World 后，把它们当成同一个一致性存档。

正式采用：

> **Runtime / World Checkpoint 作为最高一致性恢复单位。**

例如：

```text
RuntimeCheckpoint
├── World
├── Agent A
├── Agent B
├── Agent C
├── Scheduler
├── Event Cursor
└── Random State
```

---

### 16.8 Agent Export 与 Runtime Checkpoint 分离

正式区分：

```text
Runtime Checkpoint
=
完整恢复一个 Runtime / World

Agent Export
=
导出某一个数字生命，用于迁移、研究、复制或放入另一个世界
```

两者不是同一个概念。

---

### 16.9 Checkpoint 至少保存哪些 Runtime 信息

Checkpoint 至少需要覆盖：

```text
State Version Map
World Time
Tick ID
Event Log Cursor
Commit Journal Cursor
Memory Store Revision
Scheduler State
Deferred Influence State
Random State
Plugin Set
Plugin Version
State Schema Version
World State Reference
```

---

### 16.10 Random State 必须持久化

不仅保存初始 seed，还应保存：

> **随机生成器当前运行状态。**

这样从 Checkpoint 恢复后：

```text
下一次 random()
```

才能尽量延续原本轨迹。

---

### 16.11 Scheduler / Deferred Influence 必须持久化

Checkpoint / Durable Runtime State 必须覆盖：

```text
未来 One-shot Schedule
周期 Schedule
next_run_at
enabled 状态
Deferred Influence Queue
```

否则 Runtime 重启后：

```text
未来任务
跨 Tick 影响
```

会凭空消失。

---

### 16.12 Checkpoint 创建策略

支持：

```text
周期性 Checkpoint
重大节点 Checkpoint
手动 Checkpoint
系统迁移 / 升级 / Branch 前 Checkpoint
```

重大节点是否需要 Checkpoint 由策略层判断，Kernel 不硬编码“结婚、死亡”等具体人生语义。

---

### 16.13 Checkpoint 只能在稳定 Commit 边界创建

不允许：

```text
Tick 执行到一半
```

创建正式 Checkpoint。

正确流程：

```text
Life Loop
↓
Working State
↓
Validation
↓
Durable Commit
↓
Checkpoint
```

因此每个正式 Checkpoint 都对应一个完整、一致、合法的 Runtime 状态。

---

### 16.14 Checkpoint 使用 Version Reference

结合 Snapshot Strategy，Checkpoint 不重复复制所有未变化 State。

例如：

```text
CP-101:
body → body_v82
emotion → emotion_v251
goal → goal_v42

CP-102:
body → body_v83
emotion → emotion_v251
goal → goal_v42
```

未变化版本继续共享。

因此：

> **Checkpoint 本质上是一组稳定版本引用 + Runtime Metadata。**

---

### 16.15 Checkpoint 后的 Tick 不会丢失

例如：

```text
CP-100
↓
Tick 101 Durable Commit
↓
Tick 102 Durable Commit
↓
Tick 103 Durable Commit
↓
Crash
```

恢复时：

```text
加载最近 Checkpoint
+
Commit Journal / Durable State Version
```

恢复到最新成功 Tick，而不是退回 CP-100。

---

### 16.16 Checkpoint 原子发布

创建 Checkpoint 时使用：

```text
PENDING
↓
写入并校验所有引用与 Metadata
↓
COMMITTED
```

只有：

```text
COMMITTED
```

Checkpoint 才允许作为恢复源。

失败的：

```text
PENDING
FAILED
```

不得被加载为有效存档。

---

### 16.17 Plugin Environment 必须进入 Checkpoint

Checkpoint 保存：

```text
plugin_id
plugin_version
state_schema_version
```

以支持：

```text
兼容性检查
State Migration
历史实验环境识别
```

---

### 16.18 Checkpoint + Persistence v0.1 最终原则

正式接受：

1. **Tick Snapshot、Durable Commit、Checkpoint 严格分离。**
2. **每个成功 Tick 都形成可靠 Durable Commit。**
3. **Event Log 不作为唯一 State 恢复来源。**
4. **采用 State Persistence + Event Log 双轨存储。**
5. **增加 Commit Journal 记录正式 State Version 变更。**
6. **Checkpoint 是一致性恢复锚点，不是完整历史副本。**
7. **Checkpoint 主要保存 Version Reference + Runtime Metadata。**
8. **Runtime / World 是多 Agent 情况下最高一致性 Checkpoint 单位。**
9. **Agent Export 与 Runtime Checkpoint 分离。**
10. **Checkpoint 保存 State、Event Cursor、Memory、Scheduler、Deferred Influence、Random State、Plugin Environment 等恢复信息。**
11. **Checkpoint 只能在成功 Durable Commit 后创建。**
12. **支持周期、重大节点、手动、迁移前等 Checkpoint 策略。**
13. **Checkpoint 后的成功 Tick 通过 Durable Commit + Commit Journal 恢复。**
14. **Checkpoint 使用原子发布，只有 COMMITTED 状态允许恢复。**
15. **Checkpoint 保存 Plugin Version 与 State Schema Version。**

状态：

```text
Architecture Decision:
Checkpoint + Persistence v0.1

Status:
Accepted
```

---

## 十七、Architecture Decision #11D：Persistence Backend Layering【已敲定】

### 17.1 逻辑 Store 与物理数据库分离

AnimaFlux 的 Persistence 首先按职责划分逻辑 Store。

逻辑 Store：

```text
Hot State Store
State Version Store
Checkpoint Store
Event Store
Commit Journal Store
Memory Store
Runtime State Store
Vector Index
Trace Store
Artifact Store
```

这些 Store 不等于必须部署多个数据库。

第一版多个逻辑 Store 可以共享同一个物理数据库 Backend。

---

### 17.2 State Persistence

负责当前状态与版本：

```text
Hot State Store
State Version Store
Checkpoint Store
```

其中：

```text
Hot State Store
= 当前 Namespace 指向哪个正式版本

State Version Store
= 不可变 State Version 内容

Checkpoint Store
= Runtime 一致性恢复锚点
```

---

### 17.3 Historical Persistence

负责生命历史：

```text
Event Store
Commit Journal Store
Memory Store
```

职责：

```text
Event Store
= 客观世界发生了什么

Commit Journal
= 哪些 State Version 在哪个 Tick 正式生效

Memory Store
= Agent 主观长期记忆记录
```

Event 与 Memory 严格分离。

---

### 17.4 Runtime Persistence

负责跨 Tick 必须延续的运行时数据：

```text
Scheduler State
Deferred Influence
Random State
其他 Pending Runtime State
```

程序重启后必须恢复这些状态，避免：

```text
未来任务消失
长期 Influence 消失
随机轨迹重新开始
```

---

### 17.5 Auxiliary Storage

辅助存储：

```text
Vector Index
Trace Store
Artifact Store
```

#### Vector Index

用于：

```text
Memory semantic search
其他语义检索
```

但不是 Memory Source of Truth。

#### Trace Store

保存：

```text
Process Trace
Causal Trace
Performance Trace
Debug Trace
```

Trace 不等于 Event。

#### Artifact Store

保存：

```text
长文本
文件
图片
音频
视频
LLM 原始大响应
实验产物
```

数据库只保存引用和 Metadata。

---

### 17.6 Memory Store 与 Vector Index 分离

正式采用：

```text
Memory Store
= Memory Record 真数据

Vector Index
= 可重新生成的搜索索引
```

例如：

```text
MEM-100
↓
Memory Store 保存完整记录

MEM-100
↓
Embedding
↓
Vector Index
```

Embedding 模型更换时，只重新建立索引，不修改原 Memory Record。

---

### 17.7 Event Store 与 Memory Store 分离

正式区分：

```text
Event Store
= 客观历史

Memory Store
= 主观记忆
```

Agent 可以：

```text
遗忘
误记
重解释
```

Memory，但不能修改客观 Event Log。

---

### 17.8 Trace Store 与 Event Store 分离

例如：

```text
父亲去世
```

属于 Event。

而：

```text
EmotionPlugin.resolve() took 32ms
```

属于 Trace。

程序执行信息不属于世界历史。

---

### 17.9 Source of Truth 与派生索引分离

Source of Truth 包括：

```text
Committed State Version
Event Log
Commit Journal
Memory Record
Checkpoint Metadata
Schedule / Runtime State
```

派生数据包括：

```text
Vector Index
Cache
Search Index
Metrics
可重建 Trace 派生统计
```

派生索引损坏后应能从 Source of Truth 重建。

---

### 17.10 第一版不主动引入复杂基础设施

第一版不为了技术栈丰富而强制引入：

```text
Redis
独立向量数据库
分布式消息队列
```

只有在：

```text
大规模 Multi-Agent
分布式 Runtime
超大 Memory Index
跨进程协调
```

真正需要时再扩展。

---

### 17.11 Persistence Backend Layering v0.1 最终原则

正式接受：

1. **State Persistence 包含 Hot State、State Version、Checkpoint。**
2. **Historical Persistence 包含 Event Store、Commit Journal、Memory Store。**
3. **Runtime Persistence 保存 Scheduler、Deferred Influence、Random State 等跨 Tick 数据。**
4. **Auxiliary Storage 包含 Vector Index、Trace Store、Artifact Store。**
5. **Memory Store 与 Vector Index 分离。**
6. **Event Store 与 Memory Store 分离。**
7. **Trace Store 与 Event Store 分离。**
8. **Artifact Store 用于大文本、文件和二进制对象。**
9. **逻辑 Store 与物理数据库分离。**
10. **多个逻辑 Store 第一版可以共享一个数据库 Backend。**
11. **Source of Truth 与可重建派生索引明确区分。**
12. **Plugin 依赖 Store Contract / Capability，不直接绑定数据库。**
13. **第一版不主动引入 Redis 或独立向量数据库。**

状态：

```text
Architecture Decision:
Persistence Backend Layering v0.1

Status:
Accepted
```

---

## 十八、Architecture Decision #11E：Default Persistence Backend【已敲定】

### 18.1 v0.1 总体策略

AnimaFlux v0.1 不同时实现多套完整数据库 Backend。

正式采用：

```text
InMemory Backend
→ 测试 / 单元测试 / 临时实验

SQLite Backend
→ v0.1 默认正式持久化 Backend

PostgreSQL
→ 仅保留扩展接口，不作为 v0.1 实现重点
```

核心目标：

> **先保证本地开箱即用和 Runtime 语义完整，不因为未来规模化场景提前引入过多数据库实现复杂度。**

---

### 18.2 SQLite 作为默认 Backend

SQLite 负责 v0.1 的主要持久化能力，包括：

```text
Hot State
State Version
Event Store
Commit Journal
Checkpoint
Memory Record
Scheduler State
Deferred Influence State
Runtime Metadata
Trace Metadata
Artifact Metadata
```

优点：

```text
无需独立数据库服务
一个文件即可运行
适合开源项目
适合本地实验
部署门槛低
支持事务和索引
```

---

### 18.3 InMemory Backend

InMemory Backend 用于：

```text
单元测试
Runtime 测试
快速实验
临时模拟
```

它必须尽量遵守与 SQLite 相同的 Store Contract 和 Runtime 语义。

但它不是长期 Source of Truth。

---

### 18.4 PostgreSQL 只保留扩展口

v0.1 不要求实现完整 PostgreSQL Backend。

但 Persistence Architecture 必须保持：

```text
Runtime
↓
Persistence Contract
↓
Backend Adapter
```

不能让 Runtime 或 Plugin 直接依赖 SQLite 特有 API。

因此未来可以新增：

```text
PostgreSQLBackend
```

而不修改上层 Runtime 协议。

---

### 18.5 PostgreSQL 不进入 v0.1 主开发范围

第一版不投入以下内容：

```text
PostgreSQL 专用 Schema 优化
连接池调优
分区
高并发写优化
PostgreSQL 专用 JSON / Vector 扩展
```

这些作为未来：

```text
Server Mode
Large-scale Multi-Agent
Cloud Runtime
```

扩展方向保留。

---

### 18.6 Database / Vector / Artifact Backend 继续解耦

即使 v0.1 使用 SQLite：

```text
Database Backend
Vector Index Backend
Artifact Store Backend
```

仍保持逻辑分离。

默认本地模式可以是：

```text
SQLite
+
Local Vector Index
+
Local Artifact Store
```

---

### 18.7 Runtime Transaction Contract 高于 SQLite API

AnimaFlux 先定义自己的：

```text
Tick Transaction
Checkpoint Transaction
Migration Transaction
```

语义。

SQLite Backend 负责实现这些 Contract。

不能反过来让 SQLite 的具体 API 决定 Runtime 架构。

---

### 18.8 Default Persistence Backend v0.1 最终原则

正式接受：

1. **v0.1 默认正式 Backend 为 SQLite。**
2. **InMemory Backend 用于测试与临时实验。**
3. **PostgreSQL 仅保留 Backend 扩展接口，不作为 v0.1 实现重点。**
4. **Runtime 只依赖 Persistence Contract，不直接依赖 SQLite。**
5. **Plugin 不直接编写数据库 SQL。**
6. **SQLite 与 InMemory 应遵守同一套 Runtime 语义。**
7. **Database、Vector Index、Artifact Store 保持解耦。**
8. **未来可以增加 PostgreSQLBackend，而不修改上层 Runtime 协议。**
9. **v0.1 不提前投入 PostgreSQL 专用性能优化。**
10. **Runtime Transaction Contract 高于具体数据库事务 API。**

状态：

```text
Architecture Decision:
Default Persistence Backend v0.1

Status:
Accepted
```

---

## 十九、Architecture Decision #11F：Tick Transaction【已敲定】

### 19.1 定义

Tick Transaction 表示：

> **一个 Tick 内所有必须一起成立的核心生命变化，要么全部正式生效，要么全部不生效。**

避免产生：

```text
State 已更新
Memory 没写完
Scheduler 没更新
Event 已经落盘
```

这种“半个 Tick 的人生”。

---

### 19.2 Transaction Coordinator

Kernel / Runtime Infrastructure 增加：

```text
Transaction Coordinator
```

负责：

```text
Begin Tick Transaction
Collect Critical Writes
Validate
Persist
Commit
Rollback
Post-Commit Dispatch
```

Plugin 不直接控制数据库事务。

---

### 19.3 Critical Write

以下数据默认属于 Tick Critical Write：

```text
Core State Version
Current State Pointer
Durable Event
Memory Source-of-Truth Record
Scheduler State
Deferred Influence State
Commit Journal
必要 World State
```

其中任何关键写入失败：

```text
当前 Tick 不得 Commit
```

---

### 19.4 Non-Critical / Post-Commit Write

以下内容默认允许在 Tick Commit 后处理：

```text
Vector Index
Cache
Metrics
Search Index
部分 Performance Trace
可重建派生数据
```

这些失败：

```text
不回滚已经成立的生命 Tick
```

而是记录并后续重试 / 重建。

---

### 19.5 Event 在 Commit 前保持 Pending

当前 Tick 新生成的 Event 在正式 Commit 前：

```text
Pending Event
```

不能提前进入 Durable Event Log。

流程：

```text
Proposed
↓
Validated
↓
Pending
↓
Tick Commit
↓
Durable Event
```

一旦进入 Durable Event Store，继续遵循 Event 不可变原则。

---

### 19.6 Working State Version

计算阶段产生：

```text
Working / Candidate State Version
```

它不是正式状态。

只有 Tick Transaction 成功以后：

```text
Candidate Version
→ Committed Version
```

失败则丢弃。

---

### 19.7 Commit 顺序

概念提交顺序：

```text
1. Freeze Working Result
2. Validate
3. Begin Persistence Transaction
4. Persist New State Versions
5. Persist Pending Events
6. Persist Memory Source-of-Truth Records
7. Persist Scheduler / Deferred Runtime State
8. Write Commit Journal
9. Update Current State Pointers
10. Commit Backend Transaction
11. Mark Tick COMMITTED
12. Trigger Post-Commit Work
```

具体数据库实现可以优化，但不能破坏此事务语义。

---

### 19.8 Current State Pointer 后更新

Current State Pointer 不应在核心数据准备完成前提前指向新版本。

必须确保：

```text
新 State Version 已存在
必要 Event 已存在
必要 Memory 已存在
Commit Journal 已准备
```

之后再更新当前版本指针。

---

### 19.9 Tick Status

概念状态：

```text
RUNNING
COMMITTING
COMMITTED
FAILED
```

恢复逻辑只认可：

```text
COMMITTED
```

Tick。

---

### 19.10 Crash Recovery

如果程序在 Tick 中途崩溃：

```text
最新 COMMITTED Tick
↓
恢复 Committed State
↓
忽略 / 清理未提交临时数据
↓
继续运行
```

v0.1 SQLite Backend 尽量依赖单一 SQLite Transaction 保证核心写入原子性。

---

### 19.11 Memory Record 与 Vector Index 分离

Memory Source-of-Truth Record：

```text
Critical
```

对应 Embedding / Vector Index：

```text
Post-Commit
```

因此 Vector Index 更新失败不会导致已经形成的 Memory 消失。

---

### 19.12 Artifact 等非数据库资源

Artifact 等无法直接加入 SQLite Transaction 的资源，不进入核心事务内部直接“先正式生效”。

建议模式：

```text
Write Temporary Resource
↓
Validate / Hash
↓
Commit Metadata Reference
↓
Finalize Resource
```

失败的临时资源后续清理。

---

### 19.13 外部输入

外部输入与 Runtime 内部 Event 分离。

架构上预留：

```text
Input Journal
```

用于可靠记录用户 / 外部系统输入，使 Tick 失败后能够重新消费。

v0.1 不要求立刻完整实现复杂消息系统。

---

### 19.14 Plugin 事务边界

Plugin：

```text
只返回 ProcessResult / Proposal
```

不能：

```text
自行 BEGIN / COMMIT 数据库事务
直接修改 State Store
直接写 Event Store
```

统一由 Runtime Transaction Coordinator 提交。

---

### 19.15 Tick Transaction v0.1 最终原则

正式接受：

1. **一个 Tick 的核心生命变化具备原子提交语义。**
2. **Kernel 增加 Transaction Coordinator。**
3. **Plugin 不自行管理数据库事务。**
4. **Core State、Event、Memory Source-of-Truth、Scheduler、Deferred Influence、Commit Journal 等属于 Critical Write。**
5. **Vector Index、Cache、Metrics、部分 Trace 等属于 Post-Commit / Non-Critical Write。**
6. **当前 Tick 新 Event 在 Commit 前保持 Pending。**
7. **Working State Version 在 Commit 前不是正式版本。**
8. **Current State Pointer 在核心数据准备完成后再更新。**
9. **Commit Journal 与 State / Event 等处于同一事务语义中。**
10. **v0.1 SQLite Backend 尽量使用一个 SQLite Transaction 提交全部 Critical Write。**
11. **Tick 只有 Backend Transaction 成功后才标记 COMMITTED。**
12. **Crash Recovery 只恢复最后成功 COMMITTED 状态。**
13. **Post-Commit 派生数据失败不回滚已成立 Tick。**
14. **Artifact 等外部资源采用临时资源 + Commit 引用方式处理。**
15. **架构预留 Input Journal，但 v0.1 不要求实现复杂消息系统。**

状态：

```text
Architecture Decision:
Tick Transaction v0.1

Status:
Accepted
```

---

## 二十、Architecture Decision #11G：Retention / Archival / Garbage Collection【已敲定】

### 20.1 基本原则

AnimaFlux 长期运行时，数据不能无限无差别保留。

正式区分：

```text
Canonical History
Runtime Versions
Derived / Observability Data
```

其中：

```text
Canonical History
= 生命和世界真正发生过的历史

Runtime Versions
= Snapshot / Rollback / Resolution 所需的运行时版本

Derived / Observability
= 可重建索引、缓存、Metrics、部分 Trace
```

### 20.2 State Version 使用 Reference-based GC

State Version 不按照“旧了就删”处理。

正式采用：

> **引用保护 + GC Root。**

GC Root 至少包括：

```text
Current State
Active Working State
Committed Checkpoint
Active Branch
Pinned Experiment
```

从 GC Root 仍然可达的 State Version 不允许删除。

### 20.3 Checkpoint / Branch 引用保护

只要某个 Checkpoint 或 Branch 仍然引用对应 State Version，就必须保留。

### 20.4 Canonical Event 默认长期保留

Canonical Event 默认不因“时间太久”直接删除。

未来可以进行 Hot / Cold Archive 分层，但归档不等于丢失 Source of Truth。

### 20.5 Event Summary 是派生数据

Daily / Annual / Life Period Summary 可用于粗粒度查询，但不能替代 Original Event。

### 20.6 Commit Journal

v0.1 默认完整保存。未来允许 Compaction、Cold Archive、Segment Summary。

### 20.7 Memory Forgetting 与物理删除分离

> **心理意义上的“忘记”不等于数据库 DELETE。**

通过 accessibility、clarity、retrieval_probability、detail fading、activation 等变化表达遗忘。

### 20.8 Memory 冷热分层

未来允许 Hot Memory / Cold Memory，但 Cold Memory 仍属于 Source of Truth。

### 20.9 Vector Index 可重建

Vector Index 可删除、重建、更换 Embedding Model 后重新生成。

### 20.10 Trace Retention

Trace 至少区分：

```text
Causal Trace
Performance / Debug Trace
```

Performance / Debug Trace 可使用 TTL、Sampling、Aggregation、Cold Archive。

### 20.11 Artifact 引用保护

Artifact 在仍被 Memory / Event / Narrative 等引用时不能删除。无引用且无 Pin 时才进入 GC Candidate。

### 20.12 Checkpoint Retention

Checkpoint 支持 Retention Policy 与：

```text
pinned = True
```

用于禁止自动清理。

### 20.13 GC 不能只根据时间判断

GC 至少检查：

```text
是否 Current
是否被 Checkpoint 引用
是否被 Branch 引用
是否 Pinned
是否 Source of Truth
是否可以重建
是否已安全归档
```

### 20.14 Retention Manager

Runtime Infrastructure 增加：

```text
Retention Manager
```

负责 Reference Analysis、Retention Policy、Archive Candidate、GC Candidate、Safety Check、Cleanup。

### 20.15 GC 属于 Non-Critical Maintenance

GC / Archive 不参与正常 Life Tick Transaction。失败时记录错误并后续重试，不能导致当前生命 Tick 回滚。

### 20.16 Retention / Archival / GC v0.1 最终原则

正式接受：

1. **State Version 使用 reference-based GC。**
2. **Current State、Checkpoint、Branch、Pinned Experiment 等作为 GC Root。**
3. **被 Checkpoint / Branch 引用的 State Version 不允许删除。**
4. **无引用且满足 Retention Policy 的 State Version 才能成为 GC Candidate。**
5. **Canonical Event 默认长期保留，可归档但不轻易删除。**
6. **Event Summary 是派生数据，不能替代 Canonical Event。**
7. **Commit Journal v0.1 默认完整保存，未来允许压缩与归档。**
8. **Memory Forgetting 与物理删除严格分离。**
9. **Memory 允许冷热分层，但 Source-of-Truth Record 默认保留。**
10. **Vector Index 属于可重建派生数据。**
11. **Trace 区分 Causal Trace 与 Performance / Debug Trace。**
12. **Artifact 使用引用保护。**
13. **Checkpoint 支持 Retention Policy 与 pinned。**
14. **Runtime 增加 Retention Manager。**
15. **GC / Archive 属于 Non-Critical Maintenance，不参与生命 Tick Transaction。**

状态：

```text
Architecture Decision:
Retention / Archival / GC v0.1

Status:
Accepted
```

---

## 二十一、Architecture Decision #11H：Replay + Life Branch【已敲定】

正式区分 RESTORE、REPLAY、RESIMULATE 三种模式。

- RESTORE：加载最新已提交状态并继续原 Runtime。
- REPLAY：只读回放已发生历史，不产生新 State / Event / Memory / Schedule。
- RESIMULATE：从历史 Checkpoint 创建新 Branch，重新运行 Life Loop。

### 核心规则

1. Exact Replay 不重新调用 LLM，优先读取历史 Event、Commit Journal、State Version、Causal Trace、Stored Process Result、Stored LLM Result。
2. State Replay 用于高层人生时间线；Exact Replay 用于 Debug、因果分析和科研复现。
3. Replay Runtime 是 Read-only。
4. 从历史节点重新运行 Life Loop 必须创建新 Branch，不能覆盖原历史。
5. 历史 COMMITTED Timeline 默认不可修改；修改过去通过 Fork 实现。
6. Life Branch 默认从 Runtime / World Checkpoint Fork。
7. 单独复制 Agent 定义为 Agent Export / Clone，不称为 Life Branch。
8. Fork 前 State Version、Event、Memory、Artifact 可共享；Fork 后各 Branch 独立增长。
9. Branch 至少记录 branch_id、parent_branch_id、fork_checkpoint_id、fork_world_time、created_at、branch_name、description、random_mode、pinned。
10. Branch 支持 deterministic 与 fresh_random 两种 Random Mode。
11. Checkpoint / Branch 保存 Environment Fingerprint，包括 Kernel、Plugin、State Schema、LLM、Prompt、Random 配置等。
12. 环境兼容性至少区分 Compatible、Compatible With Migration、Non-Equivalent。
13. External Input 架构继续预留 Input Journal；Replay 读取历史输入，Re-simulation 可复用或覆盖。
14. Life Branch 可用于反事实模拟，但结果只是当前模型与运行环境下的 model-dependent trajectory。
15. Active Branch 属于 GC Root；删除 Branch 后由 Retention Manager 清理独占且无人引用的数据。
16. Branch / Experiment 支持 pinned。

状态：

```text
Architecture Decision:
Replay + Life Branch v0.1

Status:
Accepted
```

---

## 二十二、Architecture Decision #11I：Determinism + Random + LLM Reproducibility【已敲定】

### 22.1 总体原则

AnimaFlux 正式采用：

> **Deterministic Core + Nondeterministic Boundary**

即：

```text
可控的 Runtime 核心
→ 尽量严格确定

LLM / Tool / External API
→ 不假设绝对确定，通过记录输入输出保证历史可回放
```

---

### 22.2 Deterministic 与 Reproducible 分离

```text
Deterministic
=
相同输入 + 相同状态 + 相同随机状态
→ 相同输出

Reproducible
=
即使原组件并非严格确定，
也能依赖历史记录准确恢复当时已发生结果
```

因此 LLM 本身不需要被假设为严格 Deterministic，历史仍然可以 Exact Replay。

---

### 22.3 RandomService

Plugin 业务随机性统一通过：

```python
context.random
```

获取。

禁止生命业务逻辑自行依赖无管理的全局随机源。

---

### 22.4 Random Stream

RandomService 支持独立 Random Stream。

随机流可以根据：

```text
runtime_id
branch_id
agent_id
random_domain / process_id
```

稳定派生。

例如：

```text
agent-001 / emotion
agent-001 / body.disease
agent-002 / emotion
world.weather
```

互相隔离。

一个 Plugin 新增随机调用，不应该无意改变另一个 Plugin 或 Agent 的随机轨迹。

---

### 22.5 Stable Ordering

所有会影响业务结果的集合处理必须采用稳定排序。

例如：

```text
Hook
Influence
Schedule
Action Proposal
State Resolution
```

不能依赖：

```text
Set 遍历顺序
未指定 ORDER BY 的数据库返回顺序
线程完成顺序
网络返回速度
```

---

### 22.6 并发计算与确定性提交分离

允许：

```text
Process Parallel Compute
```

但业务 Resolution / Commit 必须由 Runtime 统一收集结果后按照稳定规则处理。

不能：

```text
谁先返回
谁先改变世界
```

---

### 22.7 World Time 与 Wall Clock 分离

生命逻辑只使用：

```text
context.world_time
```

系统真实时间只能用于：

```text
日志时间
性能监控
工程 Metadata
```

不能影响 Body / Emotion / Decision / World Rule 等生命逻辑。

---

### 22.8 LLM Call Record

关键生命 Process 的 LLM 调用应记录足够的可追踪信息，例如：

```text
llm_call_id
provider
model
model_revision（若可获得）
prompt_template_id
prompt_template_version
request parameters
retrieved_context_refs
input / request artifact ref
response / response artifact ref
structured_output
usage
world_time
tick_id
process_id
branch_id
```

大型 Prompt / Response 可以进入 Artifact Store，由数据库保存 Ref + Hash。

---

### 22.9 Exact Replay 不重新调用 LLM

Exact Historical Replay 使用：

```text
Stored LLM Result
Stored Tool Result
Stored Process Result
```

而不是重新调用当前 Provider。

这样即使 Provider 或 Model 后续发生变化，已发生历史仍然可以准确回放。

---

### 22.10 External Tool / API Record

外部 Tool / API 与 LLM 使用同样原则。

记录：

```text
tool_id
tool_version
input
output
world_time
external timestamp（如有）
error
```

Replay 使用历史 Output。

Re-simulation 才重新执行外部调用。

---

### 22.11 Re-simulation

从 Fork 点以后：

```text
LLM
Tool
External API
```

可以正常重新调用。

所有新结果属于新 Branch。

不得覆盖原 Timeline。

---

### 22.12 Locked Experiment Environment

科研 / A-B 人生实验支持环境锁定概念。

可锁定：

```text
Kernel Version
Plugin Version
Prompt Version
LLM Provider / Model
LLM Parameters
Random Root Seed
World Config
```

尽量保证实验只改变明确指定变量。

---

### 22.13 Environment Fingerprint

Checkpoint / Branch 保存 Environment Fingerprint。

用于判断：

```text
Compatible
Compatible With Migration
Non-Equivalent
```

不能把重大环境变化后的再模拟冒充为原环境精确复现。

---

### 22.14 三个复现等级

正式定义：

```text
Level 1:
Exact Historical Replay

Level 2:
Deterministic Core Re-execution

Level 3:
Best-effort Re-simulation
```

#### Level 1

读取已经持久化的历史结果，不重新执行非确定性边界。

#### Level 2

对 Kernel / 本地规则 / RandomService 等确定性核心重新执行。

相同输入、版本和 Random State 下应尽量产生相同结果。

#### Level 3

重新运行包含 LLM / Tool / External API 的未来模拟。

即使配置相同，也不承诺未来绝对一致。

---

### 22.15 Random Draw Trace

Normal Mode 默认保存：

```text
Root Seed
Random Stream State
```

不要求永久记录每一次 random draw。

Strict Research / Debug Mode 可额外记录：

```text
stream_id
draw_index
draw_value
```

用于高强度科研复现和 Debug。

---

### 22.16 Determinism + Reproducibility v0.1 最终原则

正式接受：

1. **采用 Deterministic Core + Nondeterministic Boundary。**
2. **不承诺整个 LLM Runtime 绝对确定性。**
3. **Plugin 业务随机性统一使用 Kernel RandomService。**
4. **RandomService 支持按 Runtime / Branch / Agent / Domain 派生独立 Random Stream。**
5. **不同 Plugin / Agent 的随机轨迹尽量相互隔离。**
6. **业务集合处理全部采用 Stable Ordering。**
7. **并发用于计算，业务提交顺序由 Runtime 决定。**
8. **生命逻辑只使用 World Time。**
9. **关键 LLM Call 保存模型、参数、Prompt Version、Context Ref 和结果。**
10. **Exact Replay 使用历史 LLM / Tool Result。**
11. **External Tool / API 同样记录输入输出。**
12. **Re-simulation 从 Fork 点后正常重新调用 LLM / Tool。**
13. **科研 Branch 支持 Locked Experiment Environment。**
14. **Environment Fingerprint 用于环境等价判断。**
15. **正式定义 Exact Historical Replay、Deterministic Core Re-execution、Best-effort Re-simulation 三个等级。**
16. **Normal Mode 保存 Seed / Stream State；Research / Debug Mode 可记录 Random Draw Trace。**
17. **大型 LLM Prompt / Response 可以进入 Artifact Store。**

状态：

```text
Architecture Decision:
Determinism + Random + LLM Reproducibility v0.1

Status:
Accepted
```

---

## 二十三、Architecture Decision #11J：Error Isolation + Failure Policy【已敲定】

### 23.1 总体原则
AnimaFlux 正式区分 Critical Failure 与 Non-Critical Failure。核心目标是：故障不能无意破坏生命状态，非核心故障也不能轻易拖垮整个 Runtime。

### 23.2 Critical Failure
如果失败会让当前 Tick 的生命状态不再可信，则属于 Critical。典型包括 Core State Owner resolve 失败、World Action Resolver 失败、State Validation 失败、Critical Memory 写入失败、Scheduler Critical State 持久化失败、Transaction Commit 失败、Source-of-Truth Persistence 失败。

处理：
```text
Abort Tick
→ Rollback
→ 保留上一 Committed State
```

### 23.3 Non-Critical Failure
Metrics、Performance Trace、Vector Index、Cache、可选分析 Plugin、UI 推送等失败，可以记录错误后继续 Tick，不回滚已成立生命状态。

### 23.4 Criticality 决策来源
Criticality 由 Kernel Contract + Plugin Manifest + Process Registration 共同决定。Core State Owner 执行核心 State Resolution / Validation / Migration 时默认 Critical。

### 23.5 Runtime Health State
正式区分：
```text
HEALTHY
DEGRADED
PAUSED
FAILED
```
其中 PAUSED 是工程运行状态，不等于 Agent dead。

### 23.6 Timeout 与 Retry
Process / Capability Call 支持 Timeout。Retry 必须有限、可配置、可追踪，并区分 Transient Failure 与 Permanent Failure。

### 23.7 LLM Failure 分类
至少区分：
```text
Timeout
RateLimit
ProviderUnavailable
InvalidResponse
Authentication / Configuration Error
```

Structured Output 解析失败允许有限 Repair / Retry，之后再按 Process Criticality 决定 Rollback 或 Degrade。

### 23.8 Fallback
External Capability 可配置 Fallback Provider / Strategy。Fallback 必须记录 original_provider、fallback_provider、failure_reason、tick_id、world_time，并进入 Trace / Environment Metadata。

### 23.9 Circuit Breaker
LLM / External Tool Provider 架构上支持简化 Circuit Breaker：
```text
CLOSED
OPEN
HALF_OPEN
```
连续失败时暂时停止调用故障 Provider。

### 23.10 Plugin Quarantine
Optional Plugin 连续失败时可进入 QUARANTINED，暂停其 Hook / Schedule，并将其 Capability 标记 unavailable。其他 Runtime 可继续。

Core State Owner 不能被隔离后继续 Life Loop；连续失败应使 Runtime PAUSED。

### 23.11 Required Capability Failure
Required Capability 全部不可用时，根据调用方 Process Criticality决定 Critical Caller → Abort / Pause，Non-Critical Caller → Degrade / Skip。

### 23.12 Runtime Failure 与 Simulation Failure 分离
Simulation Failure 属于世界内部事件；Runtime Failure 属于工程系统故障。Runtime Failure 默认进入 Operations / Failure Trace，不自动变成人生 Event。

### 23.13 Source-of-Truth Persistence Failure
Source-of-Truth Persistence 无法可靠提交时：
```text
Tick FAILED
→ Rollback
→ Runtime PAUSED / bounded retry
```
不允许默认只在内存继续推进。

### 23.14 Tick Retry 与非确定性结果复用
同一个 Tick 因工程故障 Retry 时，优先复用已经成功产生的 LLM / Tool 非确定性结果，避免基础设施故障无意改变 Simulation Semantics。

架构上支持：
```text
tick_id
attempt_id
```

### 23.15 Failure Record
至少记录：
```text
failure_id
tick_id
attempt_id
branch_id
plugin_id
process_id
failure_type
severity
attempt
error_code
fallback_used
recovered
```

### 23.16 Failure Manager
Kernel / Runtime Infrastructure 增加 Failure Manager，负责 Classify Failure、Apply Failure Policy、Retry、Fallback、Quarantine、Pause Runtime、Record Failure Trace。

### 23.17 v0.1 不做自动代码修复
第一版优先保证失败可检测、状态不损坏、错误可追踪、Optional 可降级、Core 可安全暂停。

### 23.18 Error Isolation + Failure Policy v0.1 最终原则
1. 区分 Critical Failure 与 Non-Critical Failure。
2. Core State Owner 核心职责失败默认 Critical。
3. Critical Failure 导致当前 Tick Abort + Rollback。
4. Non-Critical Failure 可以记录后继续 Tick。
5. Runtime 支持 HEALTHY / DEGRADED / PAUSED / FAILED。
6. Runtime PAUSED 与 Agent 生命状态完全分离。
7. Process / Capability Call 支持 Timeout。
8. Retry 必须有限，并区分 Transient / Permanent Failure。
9. LLM Failure 按具体类型分类处理。
10. External Capability 可配置 Fallback，但必须记录。
11. Optional Plugin 连续失败可进入 QUARANTINED。
12. Core State Owner 不能隔离后继续正常 Life Loop。
13. Required Capability 不可用时根据调用方 Criticality 决定 Abort / Pause / Degrade。
14. Runtime Failure 与 Simulation Event 严格分离。
15. Source-of-Truth Persistence 不可用时默认暂停 Runtime。
16. 同 Tick 技术性 Retry 优先复用已成功的 LLM / Tool 结果。
17. 引入 FailureRecord / Failure Trace。
18. Kernel 增加 Failure Manager。
19. Plugin 可声明 Timeout / Criticality / Fallback 建议，但最终 Policy 由 Runtime 控制。
20. v0.1 不做自动代码修复。

状态：
```text
Architecture Decision:
Error Isolation + Failure Policy v0.1

Status:
Accepted
```

---

## 二十四、Architecture Decision #11K：Observability + Causal Trace【已敲定】

### 24.1 人话解释

这一部分解决两个问题：

```text
系统是不是正常运行？
这个数字生命为什么会变成现在这样？
```

前者是工程可观测性，给开发者看。

后者是生命因果追踪，给研究者和用户看。

最简单记法：

```text
Log / Metrics / Engineering Trace
= 看系统

Causal Trace / Life Timeline
= 看生命
```

### 24.2 六类记录正式分工

正式区分：

```text
Log
Metrics
Engineering Trace
Failure Trace
Causal Trace
Life Timeline
```

Log 记录工程事件；Metrics 记录统计指标；Engineering Trace 记录程序执行路径；Failure Trace 记录失败与恢复过程；Causal Trace 记录生命状态变化的模型内部计算因果；Life Timeline 提炼高层人生节点。

### 24.3 Causal Trace 的含义

Causal Trace 表达 AnimaFlux 模型内部的 computational causality（计算因果）。

例如：

```text
老板公开批评
→ Agent 感知为公开羞辱
→ 召回过去被羞辱的记忆
→ Appraisal 判定社会评价威胁高
→ social_evaluation_threat Influence
→ fear 上升
→ Goal 改变
→ 开始找工作
```

它不宣称这是现实人类心理学的真实因果证明。

### 24.4 核心对象使用稳定 ID

关键对象都应拥有稳定 ID，例如：

```text
Event
PerceivedEvent
AppraisalResult
Memory
Influence
StateChange
Decision
Action
LLM Call
Tick
Checkpoint
```

从而可以形成：

```text
EVT-100
→ PER-20
→ APP-50
→ INF-90
→ STATE_CHANGE-100
→ DEC-77
→ ACT-90
→ EVT-101
```

### 24.5 StateChangeRecord

引入逻辑 StateChangeRecord，用于关联：

```text
from_version
to_version
changed_paths / summary
cause_influence_refs
cause_event_refs
process_id
tick_id
branch_id
```

State Version 仍然是状态真数据。

StateChangeRecord 是因果索引与解释记录。

### 24.6 关键输入可追踪

关键 Process 应保留实际参与计算的 Input References，例如：

```text
Event refs
Memory refs
Belief refs
Value refs
Goal refs
State Version refs
Prompt Version
LLM Call ref
```

这样以后可以回答：

> 这个决定当时到底看到了什么信息？

### 24.7 Runtime Causal Trace 与 LLM 自我解释分离

LLM 可以生成 Self-explanation，但不能作为唯一因果依据。

```text
Runtime Causal Trace
= 系统实际记录的输入 / 输出 / 依赖关系

LLM Explanation
= 模型对自己的语言解释
```

### 24.8 Narrative 与 Causal Trace 分离

```text
Narrative
= Agent 第一人称如何解释自己的人生

Causal Trace
= Runtime 第三人称记录实际计算链
```

两者允许不一致。

### 24.9 Causal Graph

AnimaFlux 逻辑上形成 Causal Graph（因果关系图）。

关系可以包括：

```text
perceived_as
used_in
produced
contributed_to
triggered_by
amplified_by
inhibited_by
derived_from
```

v0.1 不要求使用图数据库。

SQLite 中使用逻辑关系表即可。

### 24.10 CausalRecord / CausalEdge

概念结构：

```text
source_ref
relation_type
target_ref
tick_id
branch_id
```

例如：

```text
EVT-100 --perceived_as--> PER-20
MEM-30 --used_in--> APP-50
APP-50 --produced--> INF-90
INF-90 --contributed_to--> STATE_CHANGE-100
```

### 24.11 Life Timeline

Life Timeline 是给人看的高层人生时间轴。

它根据 event importance、subjective importance、relationship impact、state change magnitude、narrative relevance 等提炼重要节点。

Life Timeline 是派生视图，不是 Source of Truth。

### 24.12 三种观察视角

未来界面可按三种视角组织：

```text
Runtime Operator View
Researcher View
Life View
```

Runtime Operator 关注工程状态；Researcher 关注因果链和 Branch 差异；Life View 关注人生事件、情绪和关系变化。

### 24.13 结构化 Log

正式日志至少携带：

```text
runtime_id
branch_id
agent_id
tick_id
plugin_id
process_id
level
event
```

### 24.14 Engineering Trace 与 Causal Trace 共享关联 ID

同一个处理节点既可以查看性能，也可以查看对生命造成的影响。

### 24.15 核心 Causal Metadata 与普通 Trace 分层

```text
Causal Core
→ 随 Tick Transaction 可靠保存

Engineering Detail
→ Post-Commit / Non-Critical
```

### 24.16 Observability 不得改变 Simulation Semantics

开启 Debug / Metrics / Trace 不能改变 Random 顺序、Plugin 执行顺序、LLM Prompt 或业务状态。

### 24.17 v0.1 不强制复杂外部监控基础设施

第一版优先：

```text
Structured Log
Internal Metrics Registry
SQLite Trace / Causal Store
```

保留未来 OpenTelemetry / Prometheus / Grafana 扩展口。

### 24.18 Observability + Causal Trace v0.1 最终原则

正式接受：

1. Log、Metrics、Engineering Trace、Failure Trace、Causal Trace、Life Timeline 严格分工。
2. Engineering Observability 解释 Runtime 怎么运行。
3. Causal Trace 解释生命状态为什么变化。
4. Causal Trace 表达模型内部 computational causality。
5. 关键 Runtime / Life 对象使用稳定 ID。
6. 引入 StateChangeRecord。
7. 关键 Appraisal、Memory Retrieval、Decision Input References 可追踪。
8. Runtime Causal Trace 与 LLM Self-explanation 分离。
9. Narrative 与 Causal Trace 分离。
10. 逻辑上形成 Causal Graph。
11. v0.1 使用 SQLite 关系记录即可，不引入图数据库。
12. Life Timeline 是派生视图，不是 Source of Truth。
13. Observability 不得改变 Simulation Semantics。
14. 核心 Causal Metadata 随 Tick Transaction 可靠保存。
15. Performance / Debug Detail 可 Post-Commit。
16. 结构化 Log 携带 Runtime / Branch / Agent / Tick / Plugin / Process 上下文。
17. Runtime Operator / Researcher / Life View 共享底层数据但展示不同。
18. v0.1 不强制 Prometheus / OpenTelemetry 等外部基础设施。

状态：

```text
Architecture Decision:
Observability + Causal Trace v0.1

Status:
Accepted
```

---

# 技术架构阶段 B：Runtime Infrastructure【高层复盘】

### 人话解释

这一阶段我们一直在解决的，其实只有一句话：

> **怎样让一个数字生命可以安全、长期、可恢复、可解释地活很多年？**

目前已经把“状态怎么存、怎么提交、怎么恢复、怎么分支、怎么处理错误、怎么解释原因”基本串起来了。

已敲定：

```text
#11A State Store
#11B Snapshot Strategy
#11C Checkpoint + Persistence
#11D Persistence Backend Layering
#11E Default Backend
#11F Tick Transaction
#11G Retention / Archival / GC
#11H Replay + Life Branch
#11I Determinism + Random + LLM Reproducibility
#11J Error Isolation + Failure Policy
#11K Observability + Causal Trace
```

### 阶段 B 还剩的高层问题

从完整 Runtime 角度看，还剩两个值得单独敲定的系统级问题：

```text
1. Configuration / Runtime Profile
2. Security / Plugin Permission Boundary
```

其中：

```text
Configuration
= AnimaFlux 通过什么配置决定用哪些 Plugin、哪个 LLM、哪个 World、
  时间速度、随机种子、存储模式等

Security
= 第三方 Python Plugin 能做什么、不能做什么，
  以及 v0.1 能提供多强的隔离
```

这两项完成后：

> **Stage B 可以正式冻结。**

然后进入：

# Stage C：Life Interaction Boundary【重新收缩后的正式方向】

## 三十、Stage C 重新定位

### 30.1 人话解释

AnimaFlux 的核心目标不是：

> **造一个完整世界。**

而是：

> **模拟一个数字生命 / 一个人本身，怎样随着时间、经历和关系不断变化。**

因此正式确立项目边界：

```text
AnimaFlux
= 模拟生命本身

External Environment
= 提供生命所处的世界
```

核心口号：

> **AnimaFlux models the life, not the universe.**

中文：

> **AnimaFlux 模拟生命本身，而不是模拟整个宇宙。**

---

## 30.2 AnimaFlux Core 负责什么

AnimaFlux Core 继续聚焦：

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

Perception
Appraisal
Reflection
Decision
Long-term evolution

Time
State
Persistence
Replay
Life Branch
Causal Trace
Plugin Runtime
```

核心问题是：

> **“一个人经历某件事以后，会怎样理解、记住、感受、改变，并最终成为怎样的人？”**

---

## 30.3 AnimaFlux Core 不负责什么

以下内容不进入 v0.1 Core：

```text
完整城市地图
复杂 Location / Space System
World Entity / Item System
战斗系统
经济系统
天气模拟
政治模拟
资源生产
历史事件生成器
修仙规则系统
小说世界运行器
游戏物理
完整社会模拟
```

这些可以由：

```text
外部 World Simulator
Game Engine
Historical Simulator
Novel World Project
Social Simulation Project
```

实现。

AnimaFlux 只与其通信。

---

## 30.4 原 Stage C World 设计处理

此前设计的：

```text
Simulation World Model
Location + Space
World Entity + Object Model
World Action Resolver
```

不再作为 AnimaFlux Core 架构决策。

正式从 Core 规范中删除。

其中有价值的设计思想未来可以：

```text
作为独立 World 项目
作为 Example Adapter
作为外部参考设计
```

重新使用，但不进入 AnimaFlux v0.1 开发范围。

---

# 三十一、Architecture Decision #12A：Environment Adapter【新 Stage C 起点】

### 31.1 人话解释

AnimaFlux 不负责造世界，但必须能：

> **“被放进不同世界里。”**

例如：

```text
现实应用
历史人物模拟器
小说世界模拟器
游戏引擎
社会模拟器
人工交互环境
```

所以需要一个统一接口：

```text
Environment Adapter
```

可以把它理解成：

> **AnimaFlux 和外部世界之间的转换插头。**

---

## 31.2 总体结构

```text
External Environment
        │
        │ Event / Observation / Context
        ▼
Environment Adapter
        │
        ▼
     AnimaFlux
        │
        │ Action Intent
        ▼
Environment Adapter
        │
        ▼
External Environment
        │
        │ Action Result / Consequence
        └──────────────────────► AnimaFlux
```

---

## 31.3 Environment Adapter 不模拟世界

Environment Adapter 不是：

```text
World Runtime
```

它不负责：

```text
生成天气
计算战斗
管理物品
模拟城市
计算经济
决定历史事件
```

它只负责：

```text
转换输入
转换输出
信息边界
时间对齐
标识映射
```

---

## 31.4 不同世界使用不同 Adapter

例如：

```text
HistoricalWorldAdapter
NovelWorldAdapter
GameAdapter
HumanInteractionAdapter
BenchmarkAdapter
```

这些 Adapter 最终都转换成 AnimaFlux 能理解的统一协议。

因此 AnimaFlux 不需要知道：

```text
皇帝是什么
灵根是什么
坦克是什么
魔法是什么
```

只需要理解：

```text
发生了什么
Agent 看到了什么
Agent 想做什么
结果是什么
```

---

# 三十二、Architecture Decision #12B：External Event + Observation Protocol

### 32.1 人话解释

外部世界需要告诉这个数字生命：

> **“外面发生了什么，以及你现在能看到什么。”**

这两个概念要区分。

```text
External Event
= 外部世界发生的事情

Observation
= 这个 Agent 实际获得的信息
```

---

## 32.2 External Event

External Event 表示：

> **环境确认已经发生的客观事实。**

例如：

```text
某人死亡
收到一封信
被公开批评
工资到账
战争爆发
好友发来消息
```

它可以进入 AnimaFlux 原有：

```text
Event
→ Perception
→ Appraisal
→ Memory
```

链路。

---

## 32.3 Observation

Observation 表示：

> **当前 Agent 实际可以接触到的信息。**

例如：

```text
看到某人哭泣
听到一句话
收到一条消息
感觉天气很冷
被告知一个消息
```

环境可以直接提供 Observation，也可以提供 External Event 后由 AnimaFlux Perception 进一步处理。

---

## 32.4 External Context

环境还可以附加：

```text
location label
nearby people
social context
current task
environment tags
available public facts
```

但这些只是：

```text
Context
```

不是 AnimaFlux 自己维护的完整世界状态。

---

## 32.5 外部信息不能直接写入主观 State

外部输入不能直接：

```text
修改 Belief
修改 Memory
修改 Emotion
修改 Goal
```

必须继续经过：

```text
Perception
Appraisal
Memory Formation
Influence
State Resolver
```

从而保留主观差异。

---

# 三十三、Architecture Decision #12C：Action Intent + Action Result Protocol

### 33.1 人话解释

AnimaFlux 负责：

> **“这个人想做什么。”**

外部世界负责：

> **“这件事到底有没有发生、结果怎样。”**

因此正式区分：

```text
Action Intent
Action Result
```

---

## 33.2 Action Intent

Action Intent 表示：

> **Agent 的行动意图。**

例如：

```text
接受邀请
拒绝工作
给 B 发消息
去某个地方
攻击某人
服用丹药
向皇帝进言
开始闭关
```

AnimaFlux 只需要表达：

```text
actor
action_type
target
content
intent / motivation refs
world_time
```

不负责裁决世界规则。

---

## 33.3 Action Result

外部 Environment 接收 Action Intent 后决定：

```text
success
failure
partial success
blocked
delayed
```

并返回：

```text
result
consequence
observations
new external events
```

这些结果再进入 AnimaFlux。

---

## 33.4 世界规则不属于 AnimaFlux

例如：

```text
刺杀是否成功
修仙是否突破
汽车是否能启动
皇帝是否批准奏章
门是否能打开
```

都由外部 Environment 决定。

AnimaFlux 不实现：

```text
Action Preconditions
Combat Rules
Economy Rules
Item Rules
World Physics
```

---

# 三十四、Architecture Decision #12D：Agent-to-Agent Interaction Boundary

### 34.1 人话解释

多 Agent 不是 AnimaFlux 的核心世界模拟系统。

更简单的方式是：

> **每个数字生命都是独立 AnimaFlux Runtime，通过外部 Environment 互动。**

例如：

```text
AnimaFlux(A)
      │
      ├── Action Intent
      ▼
Social Environment
      │
      ├── Event / Observation
      ▼
AnimaFlux(B)
```

---

## 34.2 Agent 私有状态完全隔离

Agent A 不能直接读取：

```text
B.memory
B.belief
B.goal
B.self_model
```

只能通过：

```text
B 的语言
B 的行为
外部 Observation
公共信息
```

形成自己的判断。

---

## 34.3 Relationship 仍然属于 Person Runtime

例如：

```text
A → B relationship
```

仍然存于 A 的 Relationship State。

```text
B → A relationship
```

存于 B。

外部 Environment 只负责：

```text
让双方产生互动事件
```

不维护双方的主观关系状态。

---

## 34.4 Multi-Agent 不是 v0.1 核心优化目标

v0.1 优先：

> **把一个 Digital Life 模拟深。**

不以：

```text
10,000 Agents
massive society simulation
```

作为核心目标。

未来多个 AnimaFlux Instance 可以通过外部环境连接。

---

# 三十四·增、Architecture Decision #12E：Proactive Agency & World Effect（主观能动性与主动行为）

> 文档类型：Architecture Addendum / 增量设计
> 版本：v0.1
> 状态：Accepted for Incremental Implementation

### 34E.1 人话解释

在 `#12A–#12D` 之上，补全主动行为能力：生命**不仅被世界改变，也能主动作用于世界**。

核心原则：

> **The world shapes the life, and the life acts back on the world.**
> **世界塑造生命，生命也反过来作用于世界。**

在不推翻既有 13 Core States、Life Loop、Persistence、Replay/Branch、Web 架构的前提下，激活「主动行为链路」。

### 34E.2 为什么需要这次增量

现有 AnimaFlux 已经具备：Perception、Appraisal、Drive、Goal、Decision、ActionIntent、Environment Adapter、ActionResult。

协议层实际上已经允许：

```text
Life → ActionIntent → Environment → ActionResult
```

但现阶段实现和 Scenario 更偏向：

```text
External Event → Perception → Internal Change → Decision
```

因此整体表现容易退化为 `World → Life`，而不是完整的 `Life ↔ World`。

问题不是缺少新的 Core State，而是：**主动行为链路没有被真正激活。**

### 34E.3 本次增量不新增 Core State

正式决定：

- 不新增 Agency State
- 不新增 Proactivity State
- 不新增 Initiative Score

禁止设计：

```text
agency = 0.82
proactivity = 0.71
```

主观能动性不是独立数值状态，而是现有系统共同作用后的**行为性质**：

```text
Drive + Goal + Belief + Value + Memory + Personality
+ Self Model + World Model + Relationship
        ↓
     Decision
        ↓
    ActionIntent
        ↓
    Environment
```

### 34E.4 双向生命闭环

原有主要路径：

```text
External Event → Observation → Perception → Memory Retrieval
→ Appraisal → Internal Dynamics → Decision → ActionIntent
```

本次补充第二条合法起点：

```text
Internal Motivation → Drive / Goal / Belief / Memory / World Model
→ Decision → ActionIntent → Environment
→ ActionResult → Observation → Perception
```

最终完整闭环：

```text
World → Life → Decision → Action → World → Life
```

### 34E.5 Reactive Decision 与 Proactive Decision

Decision 正式支持两类来源。

**Reactive Decision**（反应式）：由外部变化触发。

```text
Alex sends a message → decide whether/how to reply
```

典型输入：PerceivedEvent、ActionResult、new Observation。

**Proactive Decision**（主动式）：没有新的重大外部事件，也允许生命主动采取行为。

典型来源：Active Goal、Active Drive、Unresolved uncertainty、Relationship intention、Existing plan、Procedural memory、Self-related intention。

例如：

```text
Goal:    准备明天的研究汇报
Memory:  上次临场问题准备不足
Belief:  提前获得反馈可能有帮助
→ Decision → seek_feedback
```

这里没有任何人先要求 Mira 去找导师。这属于：**Self-Initiated Action**。

### 34E.6 Decision Trigger

为了让 Trace 明确区分「反应式」和「主动式」，给 DecisionContext 增加轻量 Trigger 信息。

概念：`DecisionTriggerType`

```text
EXTERNAL     presentation_scheduled_event
INTERNAL     active_goal + competence_drive
SCHEDULED    regular goal review opportunity
```

建议字段：`trigger_type`、`trigger_refs`。

这不是新的 State，只是 Decision Artifact / Context Metadata。

### 34E.7 Decision 的执行条件

旧实现如果是 `if perceived_events: run_decision()` 需要调整。

正式逻辑：

```text
should_decide =
    has_new_perception
    OR has_relevant_active_goal
    OR has_active_drive
    OR has_unfinished_plan
    OR has_information_need
    OR scheduled_decision_opportunity
```

但 `should_decide = true` 并不意味着必须行动。Decision 必须允许：`NO_ACTION` / `WAIT` / `CONTINUE` / `DEFER` / `ACTION_INTENT`。

因此：**有主观能动性 ≠ 每个 Tick 都必须做事。**

### 34E.8 Candidate Generation 增量

现有 Reactive Candidate 保留，新增 Proactive Candidate Source。

候选来源：Active Goal、Active Drive、Belief、World Model、Procedural Memory、Relevant Episodic Memory、Relationship Goal、Self Model、Plan、Information Gap。

例如：

```text
Goal: 提高公开表达能力
Candidates: rehearse / seek_feedback / ask_colleague / rest / wait
```

### 34E.9 主动信息获取

主动获取信息正式作为 Agency 的一部分。

现有 Communication 中的 `ASK` / `CLARIFY` / `VERIFY` 不仅是回复方式，也可以由内部不确定性主动触发。

```text
I do not know → Is this important? → Can I obtain evidence? → ASK / CLARIFY / VERIFY
```

这不破坏 Knowledge Boundary，反而强化：**「不知道」≠「永远被动等待」。**

### 34E.10 ActionIntent 增量

不重做已有 ActionIntent，只建议增加少量可选字段：

```text
initiative
goal_refs
motivation_refs
expected_outcome
```

示例：

```text
actor:            Mira
action_type:      seek_feedback
target:           mentor
initiative:       proactive
goal_refs:        presentation_goal
motivation_refs:  competence_drive
expected_outcome: 获得一次汇报前反馈
```

其中 `expected_outcome` 只是 Agent 的主观预期，不是 Environment 的真实结果。

旧数据默认：`initiative = null`、`goal_refs = []`、`motivation_refs = []`、`expected_outcome = null`，确保向后兼容。

### 34E.11 Environment 不再只是输入源

Environment Adapter 原有职责：External Event / Observation → Life；ActionIntent → External World；ActionResult → Life。

本次明确：Environment 必须**真正解析 Agent Action**，而不只是给 Agent 喂事件。

最小接口概念：

```text
resolve_action(intent, context) → ActionResult
```

测试 Scenario 不需要通用世界规则引擎，可以简单按 `action_type` 分发：

```text
prepare_task / seek_feedback / communicate / rest
ask_clarification / accept_offer / decline_offer / wait
```

### 34E.12 Environment 可以改变什么

Environment 只修改：

```text
ScenarioState / External Facts / External Actor State
Scheduled External Events / Action Resolution State
```

例如：

```text
presentation_preparation += 1
mentor_feedback_received = true
message_delivered = true
```

禁止：

```text
Environment → Emotion / Belief / Goal / Relationship / Self Model
```

这些必须继续通过：`ActionResult → Observation → Perception → Appraisal → Influence / Evidence → Owner` 完成。

### 34E.13 ScenarioState

测试型 Scenario Environment 可以维护很小的客观状态。

例如：`presentation_preparation`、`mentor_feedback_received`、`alex_contact_state`、`role_offer_status`、`scheduled_events`、`resolved_action_ids`、`scenario_cursor`。

这些属于 **External World Facts，不属于 Life State。**

### 34E.14 Action 对未来结果产生影响

测试 Scenario 必须证明：Agent 的行动真正能够改变未来外部条件。

例如：

```text
prepare_task → preparation level increases
seek_feedback → mentor feedback becomes available
rest → future fatigue context improves
communicate → social interaction may occur
```

然后未来 `presentation outcome` 可以依赖 `preparation` / `feedback` / `fatigue` / `scenario seed`。

但 Environment 不能直接定义「Mira becomes confident」，只定义 `presentation result = positive / mixed / poor`。内部意义仍由 AnimaFlux 决定。

### 34E.15 Environment Action Vocabulary

为了避免重新走向 World Simulator，v0.1 Agency 只支持有限动作词汇。

建议第一版只实现：

```text
prepare_task
seek_feedback
communicate
```

三类分别验证：Goal-driven Agency、Information-seeking Agency、Relationship-driven Agency。

跑通以后再补：`rest`、`ask_clarification`、`accept_offer`、`decline_offer`、`attend_event`、`wait`。

### 34E.16 不建立完整 Affordance System

当前不新增复杂：Affordance Registry、World Capability Graph、Generic Action Rule Engine。

第一版 Environment Adapter 只需提供 `supported_actions()` 或等价能力：

```text
{ "prepare_task", "seek_feedback", "communicate", "rest", "wait" }
```

Decision Candidate 必须经过：`candidate → environment supports? → keep / reject`。

以后真正出现多个复杂 Environment，再考虑正式 Affordance Protocol。

### 34E.17 Life Loop 修改原则

不重写 Life Loop。继续保留：Internal Dynamics、Goal Review & Decision、Action Intent / Output、Consequence Ingestion。

只明确：**Step 8（Decision）不再要求必须存在外部 PerceivedEvent 才能进入。**

Decision Context 可以由 External Trigger / Internal Trigger / Scheduled Opportunity 三类入口产生。

### 34E.18 Autonomous Action Opportunity

- 如果现有 Life Loop 每个有效 Tick 都会执行 Goal Review：不新增任何 Scheduler Task。
- 如果当前实现只有外部 Observation 才进入 Decision：增加轻量 `autonomous_decision_opportunity`。

它只触发：「现在有没有值得主动处理的事情？」，合法结果：`NO_ACTION`。

频率由 Scenario / Runtime Profile 决定，不要求高频运行。

### 34E.19 Communication 不需要重构

原来：Incoming communication → Perception → Decision → CommunicativeIntent。

现在增加：Drive / Goal / Relationship intention → Decision → CommunicativeIntent。

因此 Agent 可以主动 contact Alex / ask mentor / request help / clarify uncertainty。

后续仍完全复用：CommunicativeIntent → Language Realization → Validation → Environment。

### 34E.20 Reflection 不直接发起 Action

Reflection 继续保持：Long-term understanding → Evidence / Proposal。

禁止：`ReflectionProcess → direct ActionIntent`。

Reflection 如产生新的认识：Reflection → Belief / Goal / Self / Narrative Proposal → later Decision → ActionIntent。这样 Process Boundary 不变。

### 34E.21 Replay / Branch 兼容

Exact Replay：不重新执行主动 Decision、不重新解析 Action、不重新调用 Environment。它继续读取历史 DecisionResult / ActionIntent / ActionResult / State Changes。

RESIMULATE / Branch：允许重新运行新版主动 Decision，因此 `same past → different proactive choices → different future`，增强 Branch 的价值。

新的 Decision / Agency 版本应进入：Process Version、Environment Fingerprint、Replay Compatibility Metadata。

### 34E.22 对现有 Growing Year Scenario 的最小修改

原有 `Day 3: presentation scheduled`、`Day 4: Alex encourages`、`Day 7: presentation happens` 不需要推翻。只需要把中间时间打开为 Action Opportunity：

```text
Day 3: presentation scheduled
Day 4: normal tick, Agent may proactively act
Day 5: normal tick, Agent may proactively act
Day 6: normal tick, Agent may proactively act
Day 7: presentation resolved from ScenarioState
```

Agent 可以选择 prepare / seek_feedback / communicate / rest / wait，最终结果读取这些行为留下的 ScenarioState。

### 34E.23 示例：第一次汇报

Environment：`3 days later: formal presentation`。

Agent 可能产生：

```text
Path A: prepare → seek_feedback → rest
Path B: prepare → prepare → little rest
Path C: wait → late preparation
```

Environment 根据外部事实解析最终 `presentation_result`；而 Emotion / Memory / Belief / Self-Efficacy / Narrative 全部继续由 AnimaFlux 自己形成。

### 34E.24 示例：关系主动性

旧模式：Alex contacts Mira → Mira reacts。

新增：Connection Drive + Relationship Goal + contact recency → Decision → communicate(Alex)。

Agent 可以主动 send message / ask clarification / seek support / repair conflict。External actor 是否回应，由 Scenario Environment 决定。

### 34E.25 示例：主动影响自己的成长轨迹

```text
Goal:       Improve public speaking
Memory:     Feedback helped last time
World Model: Practice and feedback are useful
Decision:   seek_feedback
Environment: mentor gives feedback
Future:     presentation outcome changes
```

然后 Experience / Memory / Belief / Self Model / Narrative 自然产生不同长期结果。这才真正体现：**Agent 不只是被经历塑造，也会通过自己的选择塑造新的经历。**

### 34E.26 Trace 展示

新增主动行为后，Causal Trace 推荐支持：

```text
Drive → Goal → Memory / Belief / World Model
→ Decision → ActionIntent → Environment Resolution → ActionResult
```

例如：「Why did Mira contact Alex?」→ Drive: Connection → Goal: Maintain important relationship → Memory: Long silence previously caused distance → Belief: Proactive contact can maintain connection → Decision: Contact now → ActionIntent: communicate(Alex) → ActionResult: message delivered。

### 34E.27 Web 展示最小修改

现有 Web 不重做。Timeline 新增一种可视化标签 `Proactive Action`，点击 `Why` 展示：Drive → Goal → Memory / Belief → Decision → Action → World Result。

Life Overview 可选增加一句「最近主动做了什么」，但不是主页面必须项。

### 34E.28 新增测试

```text
27.1 No External Trigger Agency Test
     条件：no new external event + active goal + relevant drive + supported action
     验证：Decision can produce proactive ActionIntent（不要求固定是哪一个行为）

27.2 Environment Boundary Test
     验证：ActionIntent → Environment → ScenarioState changed，
     同时 Environment never directly mutates Core State

27.3 Agency Consequence Test
     从同一个 Checkpoint 分两条：Branch A: seek_feedback / Branch B: wait，
     后续 Environment outcome differs，进而允许 Memory / Experience / Belief /
     Self Model / Narrative 长期出现差异

27.4 Knowledge-Seeking Agency Test
     条件：important uncertainty exists + information can be requested
     验证：Decision may produce ASK / CLARIFY / VERIFY，
     不能由 Runtime 直接填入隐藏事实

27.5 Replay Compatibility Test
     Exact Replay：proactive Decision calls = 0、environment calls = 0，
     仍能重现历史主动行为
```

### 34E.29 实施顺序

为最大程度保护现有代码：

```text
A1 放宽 Decision Trigger（允许无 PerceivedEvent 的内部触发）
A2 Candidate Generation 增加 Proactive Candidate
A3 ActionIntent 增加 initiative / refs
A4 ScenarioEnvironment.resolve_action()
A5 Action 改变 ScenarioState
A6 ActionResult 走现有 Consequence Ingestion
A7 补 Agency Tests
A8 最后增加 Web Timeline / Why 展示
```

### 34E.30 现有模块修改范围

主要修改：Decision Trigger、Decision Candidate Generation、ActionIntent optional metadata、Scenario Environment Action Resolution、Scenario tests。

原则上保持不变：13 Core States、StateOwner、State Resolver、State Store、Persistence、Memory Store、Appraisal、Communication Pipeline、Checkpoint、Exact Replay、Branch infrastructure、Public Web architecture。

因此这是 **incremental capability activation**，而不是 **architecture rewrite**。

### 34E.31 非目标

本次不做：Full World Simulator、Generic Physics、Map Navigation、Inventory、Economy、Autonomous NPC Society、Open-ended Tool Loop、Unlimited Autonomous Action、Global Affordance Graph、Agency Score、Artificial free-will metric。

### 34E.32 最终冻结原则

```text
1.  不新增第 14 个 Core State。
2.  Agency 是行为性质，不是数值状态。
3.  Decision 支持 Reactive + Proactive 两种入口。
4.  无外界刺激时，Active Goal / Drive 也可以触发 Decision。
5.  NO_ACTION / WAIT 永远是合法结果。
6.  主动行为必须继续走 ActionIntent。
7.  Environment 只修改外部 ScenarioState。
8.  Environment 不能直接修改 Core State。
9.  ActionResult 必须重新进入 Life cognition。
10. Agent 的 Action 必须能够改变未来外部条件。
11. 第一版只支持少量测试动作。
12. 不引入完整 World Simulator。
13. ASK / CLARIFY / VERIFY 是正式主动信息获取行为。
14. Communication Pipeline 继续复用。
15. Reflection 不直接行动。
16. Exact Replay 不重新执行主动决策。
17. Branch / RESIMULATE 可以产生不同主动行为。
18. 主动行为必须进入 Causal Trace。
19. Web 只负责展示，不参与 Agency 决策。
20. 所有改造优先保持旧数据与旧 Checkpoint 兼容。
```

### 34E.33 最终状态

```text
Document: AnimaFlux Agency & Proactive Action Addendum
Version:  v0.1
Status:   Accepted for Incremental Implementation
```

核心总结：AnimaFlux 不再只是「世界发生事情后，一个生命如何反应」，还必须支持「一个生命因为自己的目标、动力、记忆和信念，主动做出行为，并因此改变未来世界」。

最终闭环：External → Internal + Internal → Action → External，也就是 `Life ↔ World`。

---

# 三十五、Stage C v0.1 最终范围

Stage C 保留五项：

```text
#12A Environment Adapter
#12B External Event + Observation Protocol
#12C Action Intent + Action Result Protocol
#12D Agent-to-Agent Interaction Boundary
#12E Proactive Agency & World Effect（主观能动性与主动行为）
```

不再扩张：

```text
World Runtime
Location Graph
World Entity
Inventory
Combat
Economy
World Physics
```

---

# 三十六、修订后的总体架构

```text
                  External Environment
                         │
                Event / Observation
                         │
                         ▼
                Environment Adapter
                         │
                         ▼
                    AnimaFlux
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
      Life Runtime                  Core States
          │                             │
          ├── Perception                ├── Body
          ├── Appraisal                 ├── Emotion
          ├── Memory                    ├── Memory
          ├── Decision                  ├── Belief
          └── Reflection                ├── Goal
                                        ├── Relationship
                                        ├── Self Model
                                        └── Narrative
                         │
                         ▼
                   Action Intent
                         │
                         ▼
                Environment Adapter
                         │
                         ▼
                External Environment
```

---

# 三十七、重新确认项目边界

最终边界：

> **AnimaFlux 模拟“生命内部”。**

外部项目模拟：

> **“生命生活的世界”。**

二者通过标准协议连接。

这样同一个 AnimaFlux Person 可以被放入：

```text
现实世界
历史模拟器
小说世界
游戏
实验环境
另一个社会模拟系统
```

而无需改变 Core Life Runtime。

---

# 三十八、下一阶段方向

Stage C 完成后，不再继续设计世界系统。

下一阶段进入：

# Stage D：Core Life Model Implementation Design

重点回到真正核心：

```text
Body 如何演化
Emotion 如何生成与衰减
Memory 如何编码 / 检索 / 遗忘
Belief 如何形成和修正
Drive 如何形成
Goal 如何生成 / 竞争 / 终止
Relationship 如何长期演化
Self Model 如何改变
Narrative 如何形成
```

也就是：

> **真正开始设计“这个人到底怎么活”。**

# Stage C：Life Interaction Boundary【正式冻结】

### 人话解释

Stage C 只解决一件事：

> **这个数字生命怎样和外部世界交换信息。**

正式冻结的四项：

```text
#12A Environment Adapter
#12B External Event + Observation Protocol
#12C Action Intent + Action Result Protocol
#12D Agent-to-Agent Interaction Boundary
```

核心边界：

```text
AnimaFlux
= 模拟生命内部

External Environment
= 模拟生命所处世界
```

正式原则：

> **AnimaFlux models the life, not the universe.**

Stage C 状态：

```text
Frozen
```

如果未来外部世界项目需要更复杂的 Location / Entity / Combat / Economy 等能力，
由外部 World Simulator 自己实现，不回灌到 AnimaFlux Core。

---

# Stage D：Core Life Model Implementation Design

### 人话解释

从这里开始，AnimaFlux 真正进入核心：

> **“这个人到底怎么活、怎么变。”**

接下来重点不再是 Runtime 基础设施，而是 13 个生命状态本身：

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

为了避免 13 个 State 各自发展成不同风格，
Stage D 首先需要建立统一：

```text
Core State Implementation Contract
```

也就是：

> **每一种生命状态都必须按照同一套问题来设计。**

统一模板至少包括：

```text
State Meaning
Schema
Update Frequency
Inputs
Processes
Influences
Outputs
Fast / Medium / Slow Dynamics
LLM Usage
Deterministic Rules
Validation
Persistence
Causal Trace
Initialization
Migration
```

下一项：

## Architecture Decision #13A：Core State Implementation Contract【已敲定】

### 人话解释

这一部分的作用是：

> **以后 13 个 Core State 都必须按照同一套规范设计，不能 Body 一套、Emotion 一套、Memory 又一套。**

统一要求每个 State 都回答：

```text
它负责什么？
内部存什么？
别人能看到什么？
变化有多快？
哪些输入能影响它？
它接受哪些 Influence？
有哪些 Process 让它变化？
哪些由代码计算？
哪些允许 LLM 参与？
怎么初始化？
怎么校验？
怎么保存和升级？
为什么会变成现在这样？
```

### 13A.1 State Meaning

每个 State 必须明确：

```text
Owns
Does Not Own
```

即：

> **它负责什么，以及明确不负责什么。**

避免状态语义重叠。

### 13A.2 Schema

每个 State 定义自己的内部数据结构。

只保存：

> **长期演化真正需要的状态。**

临时计算结果不应全部塞进 State。

### 13A.3 Internal State 与 Public View

正式区分：

```text
Internal State
Public View
```

其他 Plugin 默认通过公开 View / Capability 获取所需信息，而不是读取 State 内部实现。

### 13A.4 Update Frequency

每个 State 明确自己的变化速度：

```text
Fast
Medium
Slow
```

避免一次事件让所有长期状态同时剧烈变化。

### 13A.5 Inputs

每个 State 明确：

```text
允许读取哪些输入
```

输入只参与计算，不代表可以直接修改输入来源的 State。

### 13A.6 Influence Contract

跨 State 修改继续通过：

```text
Influence
```

每个 State Owner 明确：

```text
Supported Influence Types
Possible Output Influences
```

不支持的 Influence 默认：

```text
ignore + warning
```

而不是让 LLM 自由猜测。

### 13A.7 State 与 Process 分离

正式坚持：

```text
State
= 现在是什么样

Process
= 怎么变化
```

例如：

```text
EmotionStateOwner
≠
AppraisalProcess
≠
EmotionDecayProcess
```

### 13A.8 Deterministic Rule 与 LLM Usage

每个 State 必须明确：

```text
哪些由 deterministic code 完成
哪些允许 LLM
哪些禁止 LLM
```

总原则：

> **LLM 负责复杂语义，代码负责稳定机制。**

### 13A.9 Validation

Owner 生成 Next State 后必须：

```text
validate
```

通过后才能进入 Commit。

### 13A.10 Initialization

每个 State 定义初始化策略。

历史人物 / 小说人物初始化时保留：

```text
EXPLICIT
SOURCE_CLAIM
INFERRED
ASSUMPTION
```

等 provenance（来源类型）。

### 13A.11 Persistence / Migration

Plugin 不自行管理数据库。

每个 State 至少提供：

```text
Schema Version
Serialize / Deserialize Contract
Migration
```

真正 Persistence / Snapshot / Commit 仍由 State Store 管理。

### 13A.12 Causal Trace

重要 State Change 必须提供：

```text
change_summary
cause_refs
reason_codes
```

让 Runtime 可以回答：

> **“为什么这个 State 变成现在这样？”**

### 13A.13 Core State Implementation Contract v0.1 最终原则

正式接受：

1. **13 个 Core State 遵守统一 State Implementation Contract。**
2. **每个 State 明确 Owns / Does Not Own。**
3. **每个 State 定义 Internal Schema 和较小 Public View。**
4. **每个 State 明确 Fast / Medium / Slow 动态。**
5. **每个 State 明确允许读取的 Inputs。**
6. **跨 State 修改只能通过 Influence。**
7. **每个 State Owner 声明支持的 Influence Types。**
8. **State 与 Process 严格分离。**
9. **每个 State 明确 deterministic code 的职责。**
10. **每个 State 明确 LLM 使用位置与禁区。**
11. **总原则：LLM 负责复杂语义，代码负责稳定机制。**
12. **Next State 必须 Validation 后才能 Commit。**
13. **每个 State 定义 Initialization。**
14. **历史 / 小说人物初始化保留 provenance。**
15. **Plugin 不自行决定数据库。**
16. **每个 State 提供 Schema Version / Migration。**
17. **重要 State Change 提供 Causal References。**
18. **Owner 负责最终状态解释，Process 负责产生变化因素。**
19. **Runtime 统一负责 Snapshot / Resolution / Commit / Rollback。**
20. **后续 13 个 State 全部按同一模板设计。**

状态：

```text
Architecture Decision:
Core State Implementation Contract v0.1

Status:
Accepted
```

---

## Architecture Decision #13B：Body【已敲定】

### 人话解释

Body 解决的是：

> **这个数字生命客观上身体怎么样，以及身体状态怎样限制和影响他的一生。**

AnimaFlux 不做医学人体模拟器。

只模拟那些真正会影响：

```text
情绪
需求
感知
行动能力
长期健康
衰老
死亡
```

的身体状态。

---

### 13B.1 Body 的语义边界

Body 表示：

> **客观生理状态 + 身体能力边界。**

Body 不表示：

```text
“我觉得自己很虚弱”
“我觉得自己很丑”
“我很害怕疼痛”
```

这些分别更接近：

```text
Self Model
Belief
Emotion / Appraisal
```

正式坚持：

```text
Objective Body
≠
Subjective Body Experience
```

---

### 13B.2 Body v0.1 的七个核心区域

```text
Body
├── Constitution
├── Life Cycle
├── Homeostasis
├── Health & Damage
├── Sleep & Fatigue
├── Physical Capabilities & Senses
└── Appearance / Physical Traits
```

Reproductive Physiology 只预留扩展，不作为 v0.1 深入实现重点。

---

### 13B.3 Constitution

Constitution 表示长期、缓慢变化的身体基线，例如：

```text
recovery_capacity
endurance_baseline
sleep_need
pain_sensitivity
aging_tendency
```

v0.1 不模拟基因、染色体和细胞级机制。

---

### 13B.4 Life Cycle

`birth_time` 属于 Identity。

```text
chronological_age
=
World Time - Identity.birth_time
```

因此不重复存储。

Body 保存：

```text
biological_age
```

允许：

```text
chronological_age != biological_age
```

`vital_status` 由 Body 权威管理。

架构预留：

```text
ALIVE
DYING
DEAD
```

---

### 13B.5 Homeostasis

Homeostasis 表示身体基础平衡。

v0.1 可包含：

```text
energy
hydration
nutrition
physical_stress
```

Body 只产生身体缺口。

例如：

```text
nutrition low
```

通过 Influence 影响 Drive。

Body 不直接创建：

```text
Goal: 找食物
```

---

### 13B.6 Health & Damage

v0.1 重点保存：

```text
general_health
pain_signal
injuries
conditions
recovery_state
```

重大 Injury / Condition 可以拥有独立记录。

不模拟完整器官和医学病理过程。

---

### 13B.7 Pain Signal 与主观痛苦

正式区分：

```text
Body Pain Signal
≠
Subjective Suffering
```

Body 产生生理疼痛信号。

Emotion / Personality / Appraisal 等决定这个人如何体验和解释疼痛。

---

### 13B.8 Sleep & Fatigue

Sleep/Fatigue 属于 v0.1 核心能力。

至少支持：

```text
fatigue
sleep_debt
sleep_state
recent_sleep_quality
```

这些状态通过规则更新，并影响：

```text
Drive
Emotion
Attention
Memory
Decision
```

---

### 13B.9 Physical Capabilities

Body 描述身体能否支持某种行动，例如：

```text
mobility
strength
endurance
fine_motor
speech
```

Decision 可以产生某种 Action Intent。

但身体能力可以形成：

```text
feasibility context
```

供 Decision / Environment 使用。

---

### 13B.10 Senses

感官能力属于 Body，例如：

```text
vision
hearing
smell
touch
```

正式区分：

```text
Body
= 能不能感知

Attention / Perception
= 有没有真正注意和形成感知
```

---

### 13B.11 Appearance

Body 可以保存：

```text
stable physical traits
observable appearance traits
```

例如：

```text
height
body build
apparent age
scar
posture
```

但：

```text
Body Image
```

属于 Self Model。

---

### 13B.12 Body 多时间尺度

Body 自身存在：

```text
Fast
Medium
Slow
```

三种动态。

#### Fast
energy / fatigue / hydration / pain。

#### Medium
injury recovery / illness / sleep debt / fitness。

#### Slow
biological aging / chronic decline / appearance aging / constitution drift。

---

### 13B.13 Body 接受的 Influence

v0.1 可以支持：

```text
physical_damage
healing
nutrition_intake
hydration_intake
sleep
physical_exertion
illness_onset
treatment
environmental_stress
psychophysiological_stress
```

具体 Body Plugin 可以扩展。

---

### 13B.14 Body 对其他 State 的影响

Body 可以向：

```text
Drive
Emotion
Perception
Decision
Self Model
```

提供公开 View 或 Influence。

例如：

```text
fatigue
→ rest_need

pain
→ negative affect pressure

vision impairment
→ perception capability

mobility impairment
→ decision feasibility

appearance change
→ self-model input
```

---

### 13B.15 Body Processes

v0.1 核心 Process：

```text
BodyTimeUpdateProcess
SleepRecoveryProcess
ExertionProcess
DamageRecoveryProcess
ConditionProgressProcess
AgingProcess
VitalStatusEvaluationProcess
```

不同 Process 可以由 Scheduler 以不同频率触发。

---

### 13B.16 LLM Boundary

Body Core Owner 默认不调用 LLM。

规则：

> **生理机制优先 deterministic code + RandomService。**

LLM 可以用于：

```text
把非结构化外部描述
转换成候选 Body Influence
```

但不能直接写 Body State。

尤其：

> **LLM 不能直接宣布 vital_status = DEAD。**

死亡必须由 BodyOwner / VitalStatusEvaluation 根据结构化状态规则确认。

---

### 13B.17 Validation

Body 适合严格数值 Validation。

例如：

```text
0 <= energy <= 1
0 <= fatigue <= 1
0 <= pain_signal <= 1
biological_age >= 0
```

并校验状态组合一致性。

---

### 13B.18 Initialization

Body Initialization 支持：

```text
manual configuration
source extraction
inference
simulation assumption
```

历史 / 小说人物的身体参数保留 provenance。

---

### 13B.19 Public Views

Body 不向所有 Plugin 暴露完整内部状态。

建议提供：

```text
BodyStatusView
SensoryCapabilityView
PhysicalCapabilityView
AppearanceView
```

按使用方需要提供最小信息。

---

### 13B.20 Body v0.1 最终原则

正式接受：

1. **Body 表示客观生理状态和身体能力边界。**
2. **Body 不表示主观身体体验。**
3. **v0.1 不发展成医学人体模拟器。**
4. **核心包含 Constitution、Life Cycle、Homeostasis、Health/Damage、Sleep/Fatigue、Capabilities/Senses、Appearance。**
5. **Reproductive Physiology 只预留扩展。**
6. **chronological age 由 Identity.birth_time + World Time 推导。**
7. **biological_age 属于 Body。**
8. **vital_status 由 Body 权威管理。**
9. **Pain Signal 与 Subjective Suffering 分离。**
10. **身体缺口通过 Influence 影响 Drive，而不是 Body 直接生成 Goal。**
11. **重大 Injury / Condition 可以拥有独立记录。**
12. **Body 支持 Fast / Medium / Slow 三层生理动态。**
13. **Sleep/Fatigue 是 v0.1 核心能力。**
14. **Sensory Capability 属于 Body，Attention / Perception 不属于 Body。**
15. **Appearance 保存客观身体特征，Body Image 属于 Self Model。**
16. **Body 接受标准 physical / sleep / nutrition / illness / treatment Influence。**
17. **Body 向其他 State 提供 View / Influence。**
18. **Body Core 主要使用 deterministic code + RandomService。**
19. **BodyOwner 默认不直接调用 LLM。**
20. **LLM 只能协助把非结构化描述转换成候选 Influence。**
21. **死亡必须由 Body 规则确认。**
22. **Body 提供有限 Public View。**
23. **Initialization 保留 provenance。**
24. **Body 重要变化进入 Causal Trace。**

状态：

```text
Architecture Decision:
Body v0.1

Status:
Accepted
```

---

## Architecture Decision #13C：Personality【已敲定】

### 人话解释

Personality 表示：

> **一个人长期相对稳定的反应倾向。**

它不是：

```text
下一步一定做什么
当前是什么情绪
具体相信什么
具体想要什么
```

最重要原则：

> **Personality 是 Bias，不是 Action Command。**

---

### 13C.1 语义边界

Personality 与以下状态严格分离：

```text
Emotion
Belief
Value
Drive
Relationship
Self Model
Identity
```

例如：

```text
Personality:
一般更谨慎

Belief:
B 正在欺骗我

Relationship:
我现在不信任 B

Emotion:
我现在很焦虑
```

四者不是同一件事。

---

### 13C.2 Slow State

Personality 属于典型：

```text
Slow State
```

一次普通事件不能让人格大幅改变。

长期经历、持续环境压力、重复行为模式和人生阶段变化，才可能缓慢塑造 Personality。

---

### 13C.3 Official v0.1 Personality Model

官方 v0.1 Plugin 可以采用：

```text
Big Five-inspired Core Traits
```

例如：

```text
openness
conscientiousness
extraversion
agreeableness
emotional_reactivity
```

但 Core Protocol 不绑定 Big Five。

未来可以替换为：

```text
HEXACO
Custom Trait Model
Narrative Personality Model
```

---

### 13C.4 Core Traits 与 Facets

PersonalityState 可以包含：

```text
Core Traits
Optional Facets
Plasticity
```

Facets 用于更细的反应倾向，例如：

```text
risk_tolerance
assertiveness
persistence
trust_tendency
impulsivity
novelty_seeking
```

v0.1 不追求大量 Facet。

---

### 13C.5 Trait 与对象特定状态分离

例如：

```text
trust_tendency
```

可以属于 Personality。

但：

```text
trust(B)
```

必须属于 Relationship。

正式原则：

```text
Personality
= baseline bias

Relationship
= person-specific state
```

---

### 13C.6 Plasticity

Personality 稳定但不冻结。

通过：

```text
plasticity
```

描述人格可塑性。

人格变化要求：

```text
长期累计证据
低频更新
有限幅度
可追踪原因
```

---

### 13C.7 Development Evidence

普通事件不能直接：

```text
Trait += large_delta
```

应先形成：

```text
Personality Development Evidence
```

例如：

```text
long_term_adaptation
repeated_behavior_pattern
persistent_environment_pressure
major_life_transition
long_term_relationship_pattern
sustained_self_regulation
```

PersonalityDevelopmentProcess 再根据：

```text
evidence
duration
plasticity
life_stage
current_trait
```

计算有限变化。

---

### 13C.8 Personality 对其他系统的主要输出

Personality 主要提供 Bias：

```text
Appraisal Bias
Emotion Dynamics Bias
Drive Bias
Social Bias
Decision Style Bias
```

Personality 不直接产生 Action。

---

### 13C.9 Standard Personality Bias Contract

其他 Plugin 不应直接依赖：

```text
neuroticism
extraversion
...
```

等具体 Trait 字段。

Personality Plugin 应提供标准：

```text
PersonalityBiasView / Capability
```

例如：

```text
threat_reactivity_bias
social_engagement_bias
planning_bias
novelty_bias
cooperation_bias
persistence_bias
```

这样不同 Personality Plugin 可以替换。

---

### 13C.10 Personality Initialization

支持：

```text
manual
questionnaire
template
source extraction
behavior inference
simulation assumption
```

历史 / 小说人物人格估计可以带：

```text
value
confidence
provenance_refs
```

例如：

```text
TraitEstimate
```

来源主要用于：

```text
Initialization
Research
Trace
Re-evaluation
```

而不是每 Tick 注入 LLM。

---

### 13C.11 Personality Processes

v0.1 主要包括：

```text
PersonalityBiasProcess
PersonalityDevelopmentProcess
PersonalityConsistencyValidation
```

Development 低频执行。

---

### 13C.12 LLM Boundary

PersonalityOwner 默认不需要每 Tick 调用 LLM。

LLM 主要用于：

```text
从人物资料提取 Trait Evidence
低频总结长期行为模式
```

LLM 可以产生：

```text
Development Evidence
```

但不能直接决定最终 Trait 数值。

最终变化由 PersonalityOwner 通过确定规则计算。

---

### 13C.13 Bounded Change

每次 Personality Update 必须：

```text
bounded
```

即：

> **单次更新只能有限变化。**

防止一个事件导致人格跳变。

具体阈值由后续实验确定。

---

### 13C.14 Life Stage

架构允许：

```text
Life Stage
```

影响 Personality Plasticity。

v0.1 不要求精确心理学模型，只预留输入。

---

### 13C.15 Personality v0.1 最终原则

正式接受：

1. Personality 表示长期稳定的反应倾向。
2. Personality 是 Bias，不是 Action Command。
3. Personality 与 Emotion / Belief / Value / Drive / Relationship / Self Model 分离。
4. Personality 是典型 Slow State。
5. 官方 v0.1 可以采用 Big Five-inspired Core Traits。
6. Core Protocol 不绑定 Big Five。
7. 支持 Optional Facets。
8. Trait 数值是模拟器内部连续参数，不作为心理诊断结果。
9. 支持 Plasticity。
10. 人格变化依赖长期累计证据。
11. 普通事件不能直接大幅修改 Trait。
12. 重大事件主要通过长期适应间接塑造 Personality。
13. Personality 主要影响 Appraisal / Emotion / Drive / Social / Decision Bias。
14. Personality 不直接产生 Action。
15. 对具体人物的 trust 属于 Relationship。
16. 初始化支持 confidence + provenance。
17. Trait Evidence 与当前 Personality State 可以分开保存。
18. PersonalityDevelopmentProcess 低频运行。
19. 每次人格更新必须 bounded。
20. PersonalityOwner 默认不每 Tick 调 LLM。
21. LLM 主要负责资料解析与长期模式总结。
22. LLM 产生 Evidence，不直接写最终 Trait。
23. 其他模块依赖 Personality Bias Contract，而不是具体 Trait 字段。
24. Life Stage 可以影响 Plasticity。
25. 重要人格变化进入 Causal Trace。

状态：

```text
Architecture Decision:
Personality v0.1

Status:
Accepted
```

---

## Architecture Decision #13D：Emotion【已敲定】

### 人话解释

Emotion 表示：

> **当前和近期正在发生的情绪反应，以及持续更久的整体心境。**

正式采用：

```text
Emotion
├── Active Emotion Episodes
└── Mood
```

Emotion 不是单一标签，也不是 Personality。

---

### 13D.1 Emotion 与 Appraisal 分离

正式坚持：

```text
Event / Perception
↓
Memory Retrieval
↓
Appraisal
↓
Emotion
```

Appraisal 负责：

> **“这件事对我意味着什么？”**

Emotion 负责：

> **“因此我产生什么情绪反应？”**

Emotion Plugin 不重新解释完整世界。

---

### 13D.2 EmotionEpisode

Emotion 的基本动态单位：

```text
EmotionEpisode
```

表示一次具体、有来源的情绪反应。

可包含：

```text
episode_id
emotion_type
intensity
valence
arousal
started_at
last_updated_at
target_ref
trigger_refs
appraisal_refs
decay_profile
status
```

Episode 可以随时间衰减和重新激活。

---

### 13D.3 多情绪共存

一个 Agent 可以同时存在：

```text
sadness
relief
fear
anger
affection
```

等多个 Emotion Episode。

正式禁止：

```text
current_emotion = single_value
```

作为唯一 Source of Truth。

---

### 13D.4 Active 与 Historical 分离

当前 EmotionState 只保存仍然对当前状态产生明显作用的 Active Episodes。

已经结束的 Episode 进入：

```text
Event Log
Causal Trace
Memory / Historical Records
```

而不是永久堆在当前 State。

---

### 13D.5 Emotion Taxonomy

Core 不写死唯一 Emotion Taxonomy。

官方 v0.1 Plugin 可以提供基础 Emotion Families，例如：

```text
joy
sadness
anger
fear
disgust
surprise
relief
hope
shame
guilt
pride
affection
```

其他 Emotion Plugin 可以采用不同模型。

---

### 13D.6 Type + Intensity + Valence/Arousal

官方实现可以组合：

```text
Emotion Type
+
Intensity
+
Valence
+
Arousal
```

避免只用标签或只用二维情绪空间。

---

### 13D.7 Mood

Mood 表示：

> **一段时间内较稳定、较模糊的整体情绪底色。**

正式区分：

```text
Emotion Episode
= Fast

Mood
= Medium
```

Mood 具有惯性，不因单个普通事件瞬间反转。

---

### 13D.8 Emotion Generation Inputs

Emotion Generation 主要接收：

```text
Appraisal Result
Personality Bias
Body Status
Current Mood
Goal Significance
Relationship Significance
Belief Context
Memory Retrieval
```

这些因素通过结构化输入和 Bias 影响 Emotion。

---

### 13D.9 Decay 与 Reactivation

EmotionEpisode 支持：

```text
Decay
Reactivation
```

时间会降低强度。

Memory Retrieval / New Event / Reflection 可以重新触发相关 Appraisal，使 Episode 加强或生成新的关联 Episode。

---

### 13D.10 Aggregate View

多个同类 Episode 不强制合并成一个 Source of Truth。

内部保留独立因果。

对外提供：

```text
Aggregate Emotion View
```

例如：

```text
anger_activation
overall_valence
arousal
dominant_emotions
regulation_load
```

`dominant_emotion` 只作为派生 View。

---

### 13D.11 Mood Update

Mood 可由：

```text
Recent Emotion Episodes
Body / Sleep
Long-term Stress
Goal Progress
Social Experience
```

缓慢形成。

更新采用：

```text
bounded
+
smoothed
```

方式。

---

### 13D.12 Emotion Regulation

Emotion Regulation 属于 Process，而不是 EmotionState 本身。

v0.1 只保留统一 Process 边界，不深入心理治疗级模型。

---

### 13D.13 Emotion 对 Memory 的影响

Emotion 可以提供：

```text
Emotional Salience View
```

供 MemoryFormationProcess 使用。

Emotion 不直接修改 Memory State。

---

### 13D.14 Emotion 对 Drive / Decision 的影响

Emotion 可以提供 Bias，但不直接产生 Action。

---

### 13D.15 长期状态边界

单次 Emotion Episode 不直接大幅修改：

```text
Personality
Self Model
Narrative
```

长期重复情绪模式需要经过 Reflection / Long-term Adaptation / Development Evidence。

---

### 13D.16 Emotion Processes

v0.1 包括：

```text
EmotionGenerationProcess
EmotionDecayProcess
EmotionReactivationProcess
MoodUpdateProcess
EmotionRegulationProcess
EmotionAggregationProcess
```

---

### 13D.17 LLM Boundary

EmotionOwner 默认不直接调用 LLM。

LLM 主要用于 Appraisal 的复杂语义理解。

结构化 Appraisal 之后：

> **Emotion Dynamics 尽量使用 deterministic code + RandomService。**

---

### 13D.18 Initialization

Emotion 初始化支持：

```text
empty active episodes
neutral / configured mood
scenario recent history
```

历史 / 小说人物从剧情中间启动时，可以根据近期历史建立初始 Episode / Mood，并保留 provenance。

---

### 13D.19 Validation

Emotion 支持严格 Validation，例如：

```text
0 <= intensity <= 1
-1 <= valence <= 1
0 <= arousal <= 1
started_at <= last_updated_at
```

Inactive Episode 不参与 Aggregate View。

---

### 13D.20 Emotion v0.1 最终原则

正式接受：

1. Emotion 表示当前和近期情绪动态。
2. Emotion = Active Emotion Episodes + Mood。
3. 多个甚至矛盾情绪可以同时存在。
4. EmotionEpisode 保存类型、强度、时间、对象和因果引用。
5. 历史 Episode 不永久保留在当前 EmotionState。
6. Core 不写死唯一 Emotion Taxonomy。
7. 官方实现可以采用 Type + Intensity + Valence/Arousal。
8. dominant emotion 只是派生 View。
9. Appraisal 是 Emotion Generation 的主要上游。
10. Personality、Body、Goal、Relationship、Belief、Memory 通过 Appraisal / Bias 影响 Emotion。
11. Episode 属于 Fast State，Mood 属于 Medium State。
12. Episode 支持 Decay 和 Reactivation。
13. 同类 Episode 保留独立因果，同时提供 Aggregate View。
14. Mood 缓慢形成并具有惯性。
15. Emotion Regulation 属于 Process。
16. Emotion 通过 Emotional Salience 影响 Memory Formation。
17. Emotion 通过 Bias 影响 Drive / Decision，不直接产生 Action。
18. 单次 Emotion 不直接修改长期 Personality / Self Model。
19. v0.1 提供 Generation / Decay / Reactivation / Mood / Regulation / Aggregation Processes。
20. EmotionOwner 默认不直接调用 LLM。
21. LLM 主要用于 Appraisal。
22. Emotion Dynamics 主要使用 deterministic code + RandomService。
23. Emotion Plugin 可以替换具体心理学模型。
24. 初始化支持 Scenario Recent History。
25. EmotionState 只保存当前活动情绪状态。
26. 重要 Emotion Change 进入 Causal Trace。

状态：

```text
Architecture Decision:
Emotion v0.1

Status:
Accepted
```

---

## Architecture Decision #13E：Drive【已敲定】

### 人话解释

Drive 模块解决：

> **一个人为什么现在想行动。**

正式区分：

```text
Need = 我缺什么
Drive = 为什么现在想行动
Goal = 我具体想做到什么
Plan = 怎么做
Action = 真正去做
```

坚持：

```text
Drive = Why
Goal  = What
Plan  = How
Action = Do
```

---

### 13E.1 Need 属于 Drive 模块

Need 不新增第14个 Core State。

正式采用：

```text
DriveState
├── Needs
└── Active Drives
```

Need 是 Drive System 内部基础状态。

---

### 13E.2 Need 定义

Need 表示：

> **生命当前某种重要条件与期望状态之间的缺口 / 压力。**

Core 不写死唯一 Need 列表。

---

### 13E.3 多 Need 并存

不采用严格马斯洛层级作为 Core 规则。

多个 Need 可以同时存在、同时高、互相冲突。

---

### 13E.4 Need Sources

Need 可以来自：

```text
Body
Emotion
Relationship
Goal Progress
Value
Self Model
Memory
Context
```

---

### 13E.5 Emotion / Need / Value 分离

```text
Emotion = 我现在怎么感觉
Need = 我缺什么
Value = 我认为什么重要
```

---

### 13E.6 Drive 定义

Drive 表示：

> **当前已经被激活，并正在推动注意、目标选择或行为选择的动机力量。**

---

### 13E.7 Drive Activation

```text
Need
+
Personality
+
Emotion
+
Value
+
Memory
+
Context
→
Drive Activation
```

---

### 13E.8 Need 与 Goal 分离

一个 Need 可以产生多个 Goal。

一个 Goal 也可以由多个 Drive 支持。

---

### 13E.9 Drive 动态属性

Drive 至少区分：

```text
activation
urgency
persistence
```

---

### 13E.10 连续状态与惯性

Need / Drive 使用连续强度并具有惯性。

短暂满足不会让长期 Need 瞬间归零。

---

### 13E.11 Drive Conflict

多个 Active Drive 可以冲突。

Drive System 可以输出：

```text
MotivationalConflictView
```

但不在 Drive 层决定最终行为。

---

### 13E.12 Goal Feedback

```text
External Result
→ State Change
→ Need Reassessment
→ Drive Update
```

`Goal achieved` 不等于长期 Drive 自动消失。

---

### 13E.13 Latent Need 与 Active Drive

v0.1 允许：

```text
latent needs
active drives
```

但不引入复杂潜意识理论。

---

### 13E.14 Drive Processes

```text
NeedAssessmentProcess
DriveActivationProcess
DriveDynamicsProcess
DriveSatisfactionProcess
DriveConflictSummaryProcess
```

---

### 13E.15 Public View

Drive 对外提供：

```text
MotivationView
ActiveMotivationView
LongTermNeedPatternView
MotivationalConflictView
```

---

### 13E.16 LLM Boundary

DriveOwner 默认不直接调用 LLM。

社会 / 心理 Need 可以低频使用 LLM 生成 Need Assessment Evidence。

最终 Need / Drive 数值由 DriveOwner 计算。

---

### 13E.17 Initialization

通常由：

```text
Body baseline
Relationship baseline
Scenario
Personality
Recent history
```

计算初始 Needs。

中途 Scenario 可初始化长期 Need Deficit / Active Drive，并保留 provenance。

---

### 13E.18 Causal Trace

重要 Drive Change 要能够追踪：

```text
Need
Emotion
Value
Memory
Relationship
Personality
Context
```

等来源。

---

### 13E.19 Drive v0.1 最终原则

正式接受：

1. Need 保留在 Drive 模块内部。
2. Need 表示重要条件缺口 / 压力。
3. Drive 表示当前已激活的行动动力。
4. Goal 表示具体未来状态。
5. Drive = Why，Goal = What，Plan = How，Action = Do。
6. 多 Need / Drive 可同时存在。
7. 不采用严格马斯洛层级作为 Core 规则。
8. Core 不写死唯一 Need Domain 列表。
9. Need 可由多个 State / Context 共同形成。
10. Emotion / Need / Value 分离。
11. Need 不直接生成 Goal。
12. Drive Activation 综合 Need + Personality + Emotion + Value + Memory + Context。
13. 同一 Need 可形成多个 Goal。
14. 同一 Goal 可由多个 Drive 支持。
15. Drive 至少区分 Activation / Urgency / Persistence。
16. Need / Drive 使用连续状态并具有惯性。
17. Drive 可以冲突，但不直接决定行为。
18. Drive 不直接产生 Action。
19. Goal / Decision 负责具体选择。
20. Goal Result 通过 State / Need Feedback 影响 Drive。
21. Goal achieved 不代表 Drive 自动消失。
22. 支持 latent needs / active drives。
23. v0.1 提供 NeedAssessment / Activation / Satisfaction / Dynamics 等 Process。
24. 不同 Drive Type 可以定义不同动态规则。
25. Drive 通过 Public View 对外暴露动机信息。
26. DriveOwner 默认不直接调用 LLM。
27. LLM 可低频辅助产生 Need Assessment Evidence。
28. 最终 Need / Drive 状态由 Owner 规则决定。
29. Goal Generation 比 Drive 更新更适合使用 LLM。
30. Scenario 中途初始化支持长期 Need Deficit / Active Drive。
31. 重要 Drive Change 进入 Causal Trace。

状态：

```text
Architecture Decision:
Drive v0.1

Status:
Accepted
```

---

## Architecture Decision #13F：Memory【已敲定】

### 人话解释

Memory 不是：

> **聊天记录 + 向量数据库。**

它表示：

> **一个人经历事情以后，主观地记住了什么、忘了什么、什么时候想起来，以及过去如何在新的理解下被重新解释。**

正式坚持：

```text
Reality
≠
Perception
≠
Memory
```

---

### 13F.1 Event 与 Memory 分离

```text
Event
= 客观发生了什么

Memory
= Agent 主观记住了什么
```

同一个 Event 可以在不同 Agent 中形成不同 Memory。

---

### 13F.2 Memory 与 Belief 分离

```text
Memory
= 我记得 / 学到过什么

Belief
= 我现在认为哪些判断是真的
```

Memory 可以保留过去曾经学过但现在已不再相信的内容。

---

### 13F.3 Memory 与 Narrative 分离

Memory 保存人生材料。

Narrative 负责：

> **“这些经历说明我的人生是什么样的故事。”**

Autobiographical Memory 仍然不等于 Narrative。

---

### 13F.4 Memory Types

v0.1 支持：

```text
Episodic
Semantic
Procedural
Autobiographical
```

#### Episodic
具体经历。

#### Semantic
学习 / 概括得到的知识痕迹。

#### Procedural
know-how。

#### Autobiographical
高度 Self-relevant 的人生记忆。

---

### 13F.5 Working Memory 不作为第五种持久 Memory

当前正在处理的信息由：

```text
RuntimeContext
Current Perception
RetrievedMemorySet
Current Goal
Current Emotion
```

等共同构成 Cognitive Context。

不新增持久 Working Memory Core State。

---

### 13F.6 Memory Formation

不是所有 Event 都形成长期 Memory。

Memory Formation 可以综合：

```text
Novelty
Importance
Emotional Salience
Goal Relevance
Self Relevance
Relationship Relevance
Surprise
Repetition
```

形成：

```text
MemoryCandidate
```

再决定：

```text
persist
compress
merge
ignore
```

---

### 13F.7 Memory Record Attributes

重要属性必须区分：

```text
importance
accessibility
confidence
emotional_salience
consolidation_strength
```

正式禁止用一个 `strength` 代替全部概念。

`confidence` 表示 Agent 有多确信自己的记忆，不代表客观准确率。

---

### 13F.8 Specialized Memory Store

Memory 不存入巨大 AgentState JSON。

正式采用：

```text
Current Memory Metadata / Revision
+
Specialized Memory Store
```

Checkpoint 保存：

```text
revision / cursor / root reference
```

而不是复制完整人生记忆。

---

### 13F.9 Memory Store 与 Vector Index

正式规定：

```text
Memory Store
= Source of Truth

Vector Index
= Derived Index
```

Embedding 只用于检索辅助。

Vector Index 可以重建。

---

### 13F.10 Memory Retrieval Query

Retrieval Query 可以包含：

```text
semantic query
people refs
time range
event / subject refs
goal refs
drive refs
relationship refs
emotion context
self relevance
```

不能退化成单一文本相似度查询。

---

### 13F.11 Retrieval Ranking

Retrieval 可以综合：

```text
semantic relevance
recency
accessibility
importance
emotional salience
person relevance
goal relevance
drive relevance
self relevance
contextual relevance
```

具体权重属于：

```text
MemoryRetrievalPolicy
```

由 Memory Plugin 定义。

---

### 13F.12 Diversity / Budget

Retrieval 需要：

```text
ranking
deduplication
diversity
memory count budget
token budget
```

正式禁止：

> **把整个 Memory Store 注入 LLM。**

---

### 13F.13 RetrievedMemorySet

RetrievedMemorySet 是临时 Cognitive Context。

它不会因为被检索出来就自动形成新的 Memory。

---

### 13F.14 Retrieval Modes

v0.1 至少支持：

```text
Cued Retrieval
Deliberate Retrieval
```

复杂 spontaneous recall / dream / intrusive memory 暂不进入 v0.1。

---

### 13F.15 Forgetting

正式规定：

```text
Forgetting
≈ Accessibility Decay
```

而不是：

```text
DELETE memory
```

正式坚持：

> **Forgetting ≠ GC / Delete。**

---

### 13F.16 Consolidation

新记忆经过：

```text
Encoding
↓
Consolidation
```

逐渐形成更稳定的长期 Memory。

Consolidation 可以受：

```text
importance
emotion
self relevance
repetition
Body / Sleep
```

影响。

---

### 13F.17 Retrieval 与 Accessibility

重复 Retrieval 可以提高 Accessibility。

但：

```text
Accessibility
≠
Fidelity
```

“越容易想起”不等于“越准确”。

---

### 13F.18 Reconsolidation / Reconstruction

Retrieval 默认只读。

只有明确触发：

```text
MemoryReconsolidationProcess
```

时，才允许产生 Memory 新版本。

例如可以改变：

```text
interpretation
confidence
emotional tone
importance
detail compression
links to later knowledge
```

旧 Version 不无痕覆盖。

---

### 13F.19 错误记忆

AnimaFlux 允许错误 Memory。

但必须能够来自：

```text
perception error
source confusion
inference
reconstruction
misinformation
```

正式原则：

> **允许有来源的记忆失真，不允许无来源的模型幻觉。**

---

### 13F.20 Semantic Generalization

重复 Episodic Memory 可以通过：

```text
SemanticGeneralizationProcess
```

形成 Semantic Memory。

Generalization 必须保留：

```text
source_memory_refs
```

不能凭空总结。

---

### 13F.21 Autobiographical Synthesis

Reflection 可以从多个 Episodic Memory 中生成：

```text
Autobiographical Memory Proposal
```

但 Autobiographical Memory 仍不等于 Narrative。

---

### 13F.22 Memory Processes

v0.1 核心：

```text
MemoryFormationProcess
MemoryRetrievalProcess
MemoryConsolidationProcess
MemoryAccessibilityDecayProcess
MemoryReactivationProcess
MemoryReconsolidationProcess
```

扩展：

```text
SemanticGeneralizationProcess
AutobiographicalSynthesisProcess
```

---

### 13F.23 Randomness

Retrieval 可在高分候选之间使用：

```text
RandomService
```

产生有限、可复现的小幅随机性。

---

### 13F.24 Memory Capability

其他模块不能：

```text
memory_store.get_all()
```

必须通过：

```text
Memory Retrieval Capability
```

获得受限 `RetrievedMemorySet`。

---

### 13F.25 Character Knowledge Boundary

历史 / 小说人物初始化必须遵守：

```text
Character Knowledge Boundary
```

正式坚持：

```text
完整资料库知道
≠
角色记得 / 知道
```

Memory Initialization 依据：

```text
character-specific experience
information access
known past
```

而不是 Global Timeline。

---

### 13F.26 LLM Boundary

LLM 适合：

```text
subjective summarization
semantic generalization
autobiographical synthesis
reconstruction proposal
```

LLM 不负责：

```text
physical deletion
basic accessibility decay
database retrieval
version management
source tracking
```

LLM 生成的新长期 Memory 内容必须带：

```text
source_memory_refs / source_refs
```

---

### 13F.27 Objective History 不随 Memory 改写

Memory Version 可以变化。

但：

```text
Objective Event Log
```

永远不会因主观记忆变化而改变。

---

### 13F.28 Memory v0.1 最终原则

正式接受：

1. Memory 是主观持久记录，不是 Objective Event Log。
2. Event ≠ Perception ≠ Memory。
3. Memory ≠ Belief。
4. Memory ≠ Narrative。
5. v0.1 支持 Episodic / Semantic / Procedural / Autobiographical。
6. Episodic Memory 保存主观经历。
7. Semantic Memory 保存知识痕迹。
8. Procedural Memory 保存 know-how。
9. Autobiographical Memory 保存高度 Self-relevant 人生记忆。
10. v0.1 不新增持久 Working Memory State。
11. 不是所有 Event 都进入长期 Memory。
12. Memory Formation 综合 Novelty / Importance / Emotion / Goal / Self / Relationship / Repetition。
13. Importance / Accessibility / Confidence / Emotional Salience / Consolidation Strength 分离。
14. Confidence 不等于 Accuracy。
15. Memory 使用 Specialized Memory Store。
16. Checkpoint 保存 Memory revision/reference。
17. Memory Store 是 Source of Truth。
18. Vector Index 是 Derived Index。
19. Embedding 不是 Memory 本身。
20. Retrieval 不只依赖 Semantic Similarity。
21. Retrieval 综合时间、重要度、情绪、人物、Goal、Drive、Self、Context。
22. Retrieval Policy 属于 Memory Plugin。
23. Retrieval 支持 Diversity / Budget。
24. 禁止把全部 Memory 注入 LLM。
25. RetrievedMemorySet 是临时 Cognitive Context。
26. Retrieval 默认只读。
27. Reconsolidation 必须显式触发并产生版本。
28. 旧 Memory Version 不无痕覆盖。
29. 允许有来源的记忆失真。
30. 不允许无来源 LLM 幻觉写入长期 Memory。
31. Forgetting 主要表现为 Accessibility Decay。
32. Forgetting ≠ Delete / GC。
33. 重要记忆更容易 Consolidate。
34. 重复 Retrieval 可以提升 Accessibility，但不代表更准确。
35. Consolidation 可以受 Body / Sleep 影响。
36. Episodic Memory 可以 Generalize 成 Semantic Memory。
37. Generalization 保留 source refs。
38. Autobiographical Memory 可以经 Reflection 形成。
39. v0.1 支持 Cued / Deliberate Retrieval。
40. 核心 Processes 为 Formation / Retrieval / Consolidation / AccessibilityDecay / Reactivation / Reconsolidation。
41. Generalization / AutobiographicalSynthesis 作为扩展 Process。
42. Retrieval 第一层优先代码 + Index。
43. 可使用 RandomService 做可复现的小幅随机性。
44. 其他模块只能通过 Memory Capability 检索。
45. Memory 不直接修改其他 State。
46. 历史 / 小说人物初始化遵守 Character Knowledge Boundary。
47. 完整 Canon 不等于 Agent Memory。
48. 初始化按角色实际经历 / 信息访问建立 Memory。
49. LLM 适合摘要、概括、重构建议和自传综合。
50. LLM 不负责物理删除、基础衰减、数据库检索、版本管理。
51. LLM 生成新长期 Memory 必须附来源。
52. Reconstruction 中事实 / 解释 / 推断要保留边界。
53. Memory Version 变化进入 Causal Trace。
54. Objective Event Log 永远不因 Memory 变化而改变。

状态：

```text
Architecture Decision:
Memory v0.1

Status:
Accepted
```

---

## Architecture Decision #13G：Belief【已敲定】

### 人话解释

Belief 表示：

> **一个人当前认为什么是真的。**

它不是客观真相，也不是 Memory。

正式坚持：

```text
Objective Reality
≠
Memory
≠
Belief
```

---

### 13G.1 Belief 是 Subjective Truth

Belief 可以是正确的，也可以是错误的。

只要 Agent 没有获得足够反证：

```text
错误 Belief
```

仍然可以长期存在。

系统不能使用上帝视角偷偷修正。

---

### 13G.2 Memory 与 Belief 分离

```text
Memory
= 我记得 / 学到过什么

Belief
= 我现在认为什么是真的
```

Memory 是证据来源之一。

Belief 是当前判断。

---

### 13G.3 Belief 与 Value 分离

```text
Belief
= is / likely / causes

Value
= matters / should / worth
```

Belief 描述事实和因果判断。

Value 描述重要性与规范性判断。

---

### 13G.4 Belief 与 Self Model 分离

Self-related Belief 不自动等于 Self Model。

长期一致的 Self-related Beliefs 可以通过 Reflection 影响 Self Model。

---

### 13G.5 Belief 与 World Model

单个 Belief 是具体判断。

World Model 是大量 Belief 组织形成的主观世界结构。

---

### 13G.6 BeliefRecord

概念上可以包含：

```text
belief_id
proposition
confidence
stability
activation
evidence_refs
source_refs
formed_at
last_updated_at
validity
status
scope / type
```

核心语义：

```text
我相信什么
我有多信
为什么信
这个信念有多稳定
```

---

### 13G.7 Confidence 与 Stability

正式区分：

```text
Confidence
= 当前有多相信

Stability
= 有多难被新证据改变
```

两者不能混为一个强度值。

---

### 13G.8 Active Belief

Belief 可以存在但当前不活跃。

正式区分：

```text
Belief Exists
≠
Belief Currently Active
```

当前 Cognitive Context 只激活少量相关 Belief。

---

### 13G.9 Belief Conflict

允许多个甚至矛盾的 Belief 同时存在。

Belief Conflict 可以产生：

```text
cognitive tension
reflection trigger
decision uncertainty
emotion pressure
```

但系统不自动删除任一 Belief。

---

### 13G.10 Belief Sources

Belief 可以由：

```text
Perception
Memory
Communication
Inference
Reflection
External Information
Social Influence
```

形成。

---

### 13G.11 Evidence-driven Update

Belief Formation / Update 必须由 Evidence 驱动。

Evidence 可以保留：

```text
source_type
source_reliability
directness
recency
consistency
```

并影响 Belief confidence / stability。

---

### 13G.12 Personality / Emotion / Relationship 的作用

它们可以影响：

```text
evidence weighting
source credibility
interpretation bias
update threshold
```

但不能凭空创建 Belief。

---

### 13G.13 Belief Lifecycle

Belief 可以经历：

```text
ACTIVE
WEAKENED
REJECTED
SUPERSEDED
DORMANT
OBSOLETE
```

等生命周期概念。

旧 Belief 不直接 DELETE。

---

### 13G.14 Version / Revision

重要 Belief 支持版本化。

例如：

```text
v1
“人基本值得信任”

v2
“多数人在利益冲突时不一定可信”

v3
“可信度取决于关系和情境”
```

用来追踪世界观演化。

---

### 13G.15 Scope / Type

Belief 可以按：

```text
global
person-specific
domain-specific
causal
predictive
self-related
```

等分类。

Core 不强制固定枚举。

---

### 13G.16 Belief 对 Appraisal / Decision 的作用

Belief 是 Appraisal 和 Decision 的重要输入。

它提供：

```text
世界是什么样
别人可能怎样
哪些行为可能有效
后果可能是什么
```

---

### 13G.17 Belief Update Policy

不同 Belief Type 可以使用不同 Update Policy。

可以采用：

```text
probabilistic update
weighted evidence
rule-based revision
LLM-assisted inference
```

Core 不写死统一贝叶斯公式。

---

### 13G.18 Confidence 不是客观概率

`confidence` 表示：

> **模拟器中的主观确信程度。**

不解释为精确客观概率。

---

### 13G.19 Source Awareness

Belief Evidence 必须尽可能保留：

```text
source refs
source credibility
information channel
```

Relationship 可以影响 Source Credibility。

---

### 13G.20 Conflict Detection

v0.1 不做完整形式逻辑 / 定理证明。

只需要支持：

```text
explicit contradiction
semantic conflict proposal
shared subject conflict
```

以及结构化 Conflict View。

---

### 13G.21 Belief Activation / Retrieval

其他 Process 不能读取全部 Belief。

通过：

```text
Belief Capability
```

获得当前相关 Belief Set。

检索可综合：

```text
subject
relationship
goal
memory activation
semantic relevance
confidence
context
```

---

### 13G.22 Specialized Store

Belief 数量较大时，可以采用：

```text
Belief Store
+
Active Belief Set / Revision Pointer
```

而不是巨大 State JSON。

v0.1 允许 Specialized Store，但不强制独立数据库。

---

### 13G.23 Formation 与 Update 分离

```text
BeliefFormationProcess
```

负责首次形成新判断。

```text
BeliefUpdateProcess
```

负责已有 Belief 在新 Evidence 下变化。

---

### 13G.24 Revision 与 Update 分离

Update：

```text
confidence 0.6 → 0.7
```

Revision：

```text
“B 不可靠”
→
“B 在工作上可靠，但私人承诺不可靠”
```

Revision 属于更高层语义调整。

---

### 13G.25 Temporal Validity / Obsolescence

部分 Belief 可以拥有：

```text
validity window
expires_at
```

过期后：

```text
OBSOLETE
```

而不是删除。

---

### 13G.26 Character Knowledge Boundary

历史 / 小说人物 Belief 必须遵守：

```text
Character Knowledge Boundary
```

Runtime 知道的事实不自动进入 Agent Belief。

只有通过：

```text
Perception
Communication
Evidence
```

获得的信息才能推动 Belief。

---

### 13G.27 LLM Boundary

LLM 适合：

```text
Belief Candidate extraction
semantic inference
conflict proposal
revision proposal
```

LLM 不直接决定最终 `confidence` 数值。

LLM 提出的新 Belief 必须附带：

```text
evidence_refs
```

否则不能直接成为成熟 Belief。

低 confidence 可以表达 Hypothesis，不新增独立 Hypothesis State。

---

### 13G.28 Belief Processes

v0.1 包括：

```text
BeliefFormationProcess
BeliefUpdateProcess
BeliefActivationProcess
BeliefConflictDetectionProcess
BeliefRevisionProcess
BeliefObsolescenceProcess
```

前四个为核心。

---

### 13G.29 Public Views

可以提供：

```text
RelevantBeliefView
PredictiveBeliefView
CausalBeliefView
BeliefConflictView
BeliefHistoryView
```

按 Process 最小需要暴露。

---

### 13G.30 Causal Trace

重要 Belief Change 必须能够追踪：

```text
supporting evidence
contradictory evidence
source reliability
memory refs
relationship bias
emotion context
revision history
```

---

### 13G.31 Belief v0.1 最终原则

正式接受：

1. Belief 表示 Agent 当前认为什么是真的。
2. Belief 是 Subjective Truth。
3. Memory ≠ Belief。
4. Belief ≠ Value。
5. Belief ≠ Self Model。
6. 单个 Belief 与 World Model 分离。
7. BeliefRecord 保存 proposition / confidence / evidence / source / time / status 等。
8. Confidence 与 Stability 分离。
9. Belief Exists 与 Active Belief 分离。
10. 允许冲突 Belief 共存。
11. Conflict 不自动删除 Belief。
12. Belief 可来自 Perception / Memory / Communication / Inference / Reflection。
13. Evidence 保留来源和可信度。
14. Belief Update 必须 Evidence-driven。
15. Personality / Emotion / Relationship 只影响 Evidence Weighting / Interpretation。
16. Memory 是 Belief 的重要证据来源。
17. Belief 支持生命周期状态。
18. 旧 Belief 不直接 DELETE。
19. 重要 Belief 支持 Version / Revision History。
20. Belief 可按 scope/type 分类，但 Core 不强制固定枚举。
21. Self-related Belief 不自动成为 Self Model。
22. Belief 强烈影响 Appraisal 和 Decision。
23. Belief 影响 Goal 路径和结果预期，而不是直接修改 Drive。
24. 新 Evidence 可以 support / contradict / qualify Belief。
25. 不同 Belief Type 可以有不同 Update Policy。
26. Core 不强制统一贝叶斯公式。
27. Confidence 是主观确信程度，不等于客观概率。
28. Belief 必须 Source-aware。
29. Relationship 可以影响 Source Credibility。
30. v0.1 不做完整形式逻辑证明。
31. Belief Activation 只把少量 Relevant Beliefs 放进 Cognitive Context。
32. Belief Store 可以 Specialized。
33. Belief Retrieval 不只依赖向量相似度。
34. Formation 与 Update 分离。
35. Revision 与普通 Update 分离。
36. Belief 可以 Reinforce / Weaken / Revise / Become Obsolete。
37. Temporal Belief 可支持 validity / expiration。
38. Obsolete 不等于删除。
39. Objective Reality 不自动修正 Agent Belief。
40. 所有修正必须经过 Agent 可访问 Evidence。
41. 历史 / 小说人物遵守 Character Knowledge Boundary。
42. LLM 适合 Candidate / Inference / Conflict / Revision Proposal。
43. LLM 不直接决定最终 confidence。
44. LLM 新建 Belief 必须附 Evidence References。
45. 低 confidence 可表达 hypothesis。
46. Predictive Belief 可作为 subtype / metadata。
47. v0.1 Processes 包括 Formation / Update / Activation / Conflict / Revision / Obsolescence。
48. 其他模块通过有限 Belief View / Capability 获取相关信念。
49. 重要 Belief Change 进入 Causal Trace。
50. Belief History 应能展示一个人的世界观如何变化。

状态：

```text
Architecture Decision:
Belief v0.1

Status:
Accepted
```

---

## Architecture Decision #13H：Value【已敲定】

### 人话解释

Value 表示：

> **一个人认为什么重要、值得和应该。**

正式区分：

```text
Belief = 我认为什么是真的
Drive  = 我现在为什么想行动
Value  = 我认为什么重要 / 值得 / 应该
Goal   = 我具体想达到什么未来状态
```

### 13H.1 Value 与其他 State 的边界

Belief、Drive、Goal、Personality 与 Value 分离。

Value 不只表示道德，也包括家庭、成就、自由、安全、归属、知识、创造、传统等长期重要性倾向。

### 13H.2 Slow State

Value 属于典型 Slow State。一次普通事件不应直接大幅改变价值体系。

### 13H.3 ValueCommitment

Value 可以使用 `ValueCommitment` 作为基本单位，概念上可包括：

```text
value_id
value_type
importance
commitment
stability
context_scope
source_refs
formed_at
last_updated_at
```

其中 Importance 表示“我认为它有多重要”，Commitment 表示“我愿意为它付出多大代价”，Stability 表示“它有多难改变”。

### 13H.4 Value 不是概率分布

多个 Value 可以同时很高，不要求所有 Value Importance 之和为 1。

### 13H.5 Value Conflict

允许：

```text
Value vs Value
Value vs Drive
Value vs Behavior
```

冲突不能简单按单一分数机械决定，由 Decision 结合 Context / Goal / Drive / Belief / Emotion 处理。

### 13H.6 Context Scope

Value 可以拥有 base importance + contextual activation / scope，但 v0.1 不做过度细化。

### 13H.7 Value Formation / Development

Value 可以受到家庭教育、文化、重大人生事件、长期行为、关系与身份转换、长期目标结果和 Reflection 等长期塑造。

单次行为或事件不能直接证明或大幅修改 Value。

### 13H.8 Reflection

Reflection 是 Value Development / Revision 的重要入口：

```text
Event
→ Emotion / Memory / Belief / Self
→ Reflection
→ Value Development Evidence
→ Slow Value Update
```

### 13H.9 Social Norm ≠ Personal Value

社会规范、文化背景和 Identity Role 可以形成 Value Development Context，但不自动等于个人 Value。

### 13H.10 Initialization

历史 / 小说人物可通过明确台词、长期行为、重大选择、人物资料、文化背景推断 Value，并保留 confidence / provenance / source_refs。

### 13H.11 Value Model

Core Protocol 不绑定唯一心理学价值理论。

官方 v0.1 可以提供简化默认 Value Domains，例如：

```text
family
security
autonomy
achievement
status
loyalty
fairness
care
honesty
tradition
freedom
knowledge
creativity
belonging
pleasure
meaning
```

### 13H.12 Value 对 Goal / Decision 的作用

Value 不直接生成固定 Goal，主要影响 Goal Evaluation、Goal Prioritization 和 Decision Trade-off。

### 13H.13 ValueAlignmentView

Value Plugin 可以提供 `ValueAlignmentView`，描述候选 Goal / Action 的 supporting_values、conflicting_values、support_strength、conflict_strength，但不直接输出最终 Action。

### 13H.14 Value 与 Appraisal

Value 可以影响事件是否触碰重要原则、Goal 是否值得追求、Behavior 是否造成价值违背，并通过 Appraisal 影响 Emotion。

### 13H.15 Value-Behavior Conflict

行为与重要 Value 冲突时，可以形成 `value_violation`，供 Emotion、Reflection、Self Model、Narrative 使用。

### 13H.16 Active Value

正式区分：

```text
Value Exists
≠
Value Currently Salient
```

长期 ValueState 保存基础 Commitment；当前 ActiveValueContext / ValueConflictView 更适合作为派生 View。

### 13H.17 Bounded Update

Value Update 必须 slow、bounded、evidence-driven。

### 13H.18 Value Revision

ValueRevision 可以改变价值含义本身，而不只是数值。

### 13H.19 LLM Boundary

LLM 适合 Value Evidence Extraction、Long-term Pattern Summary、Value Conflict Interpretation、Value Revision Proposal。

LLM 不直接写最终 Value 数值。ValueOwner 默认不每 Tick 调 LLM。

### 13H.20 Public Views

可提供：

```text
ValuePriorityView
ValueAlignmentView
ValueConflictView
ActiveValueView
```

### 13H.21 Value Processes

v0.1 包括：

```text
ValueActivationProcess
ValueAlignmentProcess
ValueConflictProcess
ValueDevelopmentProcess
ValueRevisionProcess
```

真正修改 ValueState 的主要是低频 Development / Revision。

### 13H.22 Validation

Value 数值可做范围校验，但不要求所有 Value Importance 之和为 1。

### 13H.23 Value v0.1 最终原则

正式接受：

1. Value 表示一个人认为什么重要、值得和应该。
2. Belief / Drive / Goal / Personality 与 Value 分离。
3. Value 不只表示道德价值。
4. Value 属于 Slow State。
5. Value 可以使用 ValueCommitment。
6. Value 至少区分 Importance / Stability；协议允许 Commitment。
7. 多个 Value 可以同时很高。
8. Value 不是概率分布。
9. 允许 Value Conflict。
10. Value Conflict 不由单一分数机械解决。
11. Value 可以存在 Context Scope。
12. Value 由长期社会化、经历、行为和 Reflection 塑造。
13. 单次普通事件不直接大幅修改 Value。
14. Reflection 是 Value Development / Revision 的重要入口。
15. Repeated Behavior 可形成 Development Evidence，但单次行为不直接证明 Value。
16. Social Norm ≠ Personal Value。
17. 初始化支持 confidence / provenance。
18. Core Protocol 不绑定唯一价值理论。
19. 官方 v0.1 可以提供默认 Value Domains。
20. Value 不直接生成固定 Goal。
21. Value 主要影响 Goal Evaluation / Prioritization / Decision。
22. Goal / Action 可以同时支持与冲突多个 Value。
23. Value Plugin 提供 ValueAlignmentView。
24. Value Trade-off 保留结构化原因。
25. Value 可以影响 Appraisal。
26. Value-Behavior Conflict 可影响 Emotion / Reflection / Self。
27. 支持 Value-vs-Value / Value-vs-Drive / Value-vs-Behavior 冲突。
28. Value 不维护永久固定排行榜。
29. Value Exists 与 Active Value 分离。
30. 长期 ValueState 与当前 ActiveValueContext 分离。
31. Value 变化依赖长期 Development Evidence。
32. 每次 Value Update 必须 bounded。
33. ValueRevision 可以改变价值含义。
34. LLM 适合 Value Evidence / Conflict / Revision Proposal。
35. LLM 不直接写最终 Value。
36. ValueOwner 默认不每 Tick 调 LLM。
37. 提供 Priority / Alignment / Conflict / Active Views。
38. Value History 不默认暴露。
39. Initialization 支持 manual / template / source extraction / inference。
40. Culture 只是 Context，不决定个体 Value。
41. Identity Role 不自动等于 Value。
42. Narrative 可以表达 / 强化 Value，但不直接写 Value。
43. v0.1 Processes 包括 Activation / Alignment / Conflict / Development / Revision。
44. Value Validation 不要求 Importance 总和为 1。
45. 重要 Value Change 进入 Causal Trace。

状态：

```text
Architecture Decision:
Value v0.1

Status:
Accepted
```

---

## Architecture Decision #13I：Goal【已敲定】

### 人话解释

Goal 表示：

> **Agent 想达到的具体未来状态。**

正式区分：

```text
Drive = Why
Goal  = What
Plan  = How
Action = Do
```

Goal 不是 Drive、Plan 或 Action。

---

### 13I.1 Goal Hierarchy / Graph

Goal 支持长期 / 中期 / 短期层级。

但不强制严格单父节点树。

同一个 Goal 可以支持多个更高层 Goal，因此采用：

```text
Goal Graph
```

的思想。

---

### 13I.2 Goal Status

v0.1 支持：

```text
PROPOSED
ACTIVE
PAUSED
ACHIEVED
FAILED
ABANDONED
OBSOLETE
```

其中 FAILED / ABANDONED / OBSOLETE 必须区分。

---

### 13I.3 Desired State / Success Criteria

Goal 应尽可能包含：

```text
description
desired_state
success_criteria
```

允许模糊 Goal，但必须承认：

```text
evaluation_policy = subjective / mixed
```

而不是伪造精确完成条件。

---

### 13I.4 Goal Evaluation

Goal 可以支持：

```text
objective evaluation
subjective evaluation
mixed evaluation
```

客观 Goal 优先由 deterministic / external result 判断。

主观 Goal 可结合 Reflection / Self / Relationship 等评估。

---

### 13I.5 Goal Sources

Goal 可以来自：

```text
Drive
Value
Belief
Identity Role
Relationship
External Obligation
Reflection
Existing Goal Decomposition
```

但不能凭空创建。

---

### 13I.6 Goal Proposal 与 Active Goal

正式采用：

```text
Goal Proposal
↓
Goal Evaluation
↓
Goal Adoption
↓
ACTIVE
```

想到一个 Goal 不等于真正采纳。

---

### 13I.7 Goal Adoption

Goal Adoption 可以考虑：

```text
drive support
value alignment
belief feasibility
expected cost
risk
relationship impact
existing goal conflict
body feasibility
time horizon
resource availability
```

最终由 GoalOwner / Goal Policy 负责。

---

### 13I.8 Goal Priority

不使用一个永久 `priority` 数值。

区分：

```text
base importance
urgency
current activation
deadline pressure
commitment
```

---

### 13I.9 Goal Conflict

至少支持：

```text
Resource Conflict
Outcome Conflict
Value Conflict
```

Goal System 识别冲突，但最终行为仲裁属于 Decision。

---

### 13I.10 Goal Progress

Goal 支持 Progress。

但不强制所有 Goal 使用：

```text
0 ~ 100%
```

可以采用：

```text
milestones
signals
custom evaluator
```

---

### 13I.11 Deadline

Goal 的 deadline：

```text
optional
```

并非所有 Goal 都需要截止时间。

---

### 13I.12 Commitment

Goal Commitment 表示：

> **Agent 已经投入多少意愿持续追求这个具体 Goal。**

Goal Commitment 与 Value Commitment 分离。

---

### 13I.13 External Obligation

外部要求 / 责任不自动成为 Goal。

正式坚持：

```text
External Request
↓
Perception / Belief / Value / Role
↓
Goal Adoption
```

Agent 可以接受、拒绝、拖延。

---

### 13I.14 Goal Review

Goal Review 固定发生在 Decision 前。

检查：

```text
still relevant?
still possible?
already achieved?
failed?
obsolete?
paused?
should reactivate?
```

---

### 13I.15 Subjective Knowledge Boundary

Goal Review 使用：

```text
Agent 可知的信息
```

而不是偷看 Objective Reality。

因此：

```text
Subjective Feasibility
≠
Objective Feasibility
```

---

### 13I.16 Action Failure ≠ Goal Failure

单次 Action / Attempt 失败不代表 Goal 失败。

可以：

```text
Action Failed
↓
Plan Re-evaluation
↓
Goal remains ACTIVE
```

---

### 13I.17 Goal Decomposition

复杂 Goal 可以拆成子 Goal。

LLM 可以生成：

```text
GoalDecompositionProposal
```

但必须经过 GoalOwner Validation。

需要限制：

```text
depth
number
budget
```

防止无限拆分。

---

### 13I.18 Goal Relations

v0.1 可以支持：

```text
supports / parent
depends_on
conflicts_with
```

dependency graph 需要防非法循环。

Goal System 不变成项目管理软件。

---

### 13I.19 Goal 与其他 State

Goal Context 可以影响：

```text
Memory Retrieval
Appraisal
Emotion
Decision
```

Belief 提供可行性与后果判断。

Value 提供 worth / alignment。

Relationship 可以成为 Goal target / context。

Self Model 可以影响 Goal Adoption。

Goal Outcome 可以通过 Reflection 反向影响 Self Model / Narrative / Value。

---

### 13I.20 Goal History

当前 GoalState 不永久保存整个人生 Goal History。

历史 Goal 进入：

```text
Goal Store
Event / Trace
```

v0.1 使用 SQLite 普通持久化即可。

---

### 13I.21 Goal Public Views

可以提供：

```text
ActiveGoalView
GoalHistoryView
GoalContextView
```

按 Process 最小需要暴露。

---

### 13I.22 Goal Processes

v0.1 包括：

```text
GoalGenerationProcess
GoalAdoptionProcess
GoalReviewProcess
GoalActivationProcess
GoalProgressProcess
GoalConflictProcess
GoalDecompositionProcess
GoalClosureProcess
```

---

### 13I.23 Goal Outcome

GoalClosure 产生：

```text
GoalOutcome
```

重要 Goal Outcome 可以成为重大 Life Event，并影响：

```text
Emotion
Memory
Drive
Reflection
Self Model
Narrative
```

---

### 13I.24 LLM Boundary

LLM 适合：

```text
Goal Proposal
Goal Clarification
Goal Decomposition
Alternative Goal Generation
Semantic Success Criteria Proposal
Goal Revision Proposal
```

LLM 不直接修改 Goal status。

---

### 13I.25 Goal Completion

客观 Goal Completion：

```text
优先 deterministic / external evidence
```

主观 Goal Completion：

```text
Reflection
+
LLM-assisted evaluation
+
evidence refs
```

---

### 13I.26 不现实 / 冲突 Goal

允许：

```text
unrealistic goals
conflicting goals
irrational persistence
```

AnimaFlux 不强制 Agent 永远理性最优。

但“不理性”仍需要：

```text
Personality
Emotion
Belief
Relationship
History
```

等可追踪因果。

---

### 13I.27 Goal v0.1 最终原则

正式接受：

1. Goal 表示 Agent 想达到的具体未来状态。
2. Goal ≠ Drive；Drive 是 Why，Goal 是 What。
3. Goal ≠ Plan；Plan 是 How。
4. Goal ≠ Action；Action 是 Do。
5. Goal 支持层级和图关系。
6. 支持 PROPOSED / ACTIVE / PAUSED / ACHIEVED / FAILED / ABANDONED / OBSOLETE。
7. FAILED / ABANDONED / OBSOLETE 分离。
8. Goal 应尽可能表示 Desired State / Success Criteria。
9. 允许模糊 Goal。
10. 支持 objective / subjective / mixed evaluation。
11. Goal 可以来自 Drive / Value / Belief / Identity / Relationship / Obligation / Reflection / Decomposition。
12. Goal Proposal 与 Active Goal 分离。
13. LLM 可以生成 Proposal，但不能直接激活 Goal。
14. Goal Adoption 综合 Motivation / Value / Feasibility / Cost / Risk / Conflict。
15. Goal Priority 不使用单一永久数字。
16. 区分 Base Importance / Urgency / Activation / Deadline Pressure / Commitment。
17. Goal 支持暂停和重新激活。
18. Goal Conflict 是核心能力。
19. 至少支持 Resource / Outcome / Value Conflict。
20. Goal System 不负责最终行为仲裁。
21. Goal 向 Decision 提供 Goal Context。
22. Goal 支持 Progress，但不强制百分比。
23. Progress 可以使用 milestone / signal / evaluator。
24. Deadline 可选。
25. Goal Commitment 与 Value Commitment 分离。
26. External Request 不自动成为 Goal。
27. 外部要求必须经过 Agent Goal Adoption。
28. Goal 可以重新解释 / 暂停 / 放弃。
29. Goal Review 固定发生在 Decision 前。
30. Goal Review 遵守主观知识边界。
31. Goal Success 也遵守 Character Knowledge Boundary。
32. Action Failure ≠ Goal Failure。
33. 复杂 Goal 支持 Decomposition。
34. LLM 可提出子 Goal，但由 GoalOwner 验证。
35. Goal Decomposition 限制深度 / 数量。
36. Dependency Graph 防非法循环。
37. v0.1 不变成项目管理系统。
38. Goal Context 影响 Memory Retrieval。
39. Goal Relevance 影响 Appraisal / Emotion。
40. Emotion 可以影响 Goal Persistence，但不能直接修改 Goal。
41. Belief 提供 Feasibility / Outcome Expectation。
42. Value 提供 Worth / Alignment。
43. Relationship 可以成为 Goal Target / Context。
44. Self Model 与 Goal 通过慢反馈相互影响。
45. 当前 GoalState 不保存完整人生 Goal History。
46. 历史 Goal 进入 Goal Store / Event / Trace。
47. v0.1 可使用 SQLite。
48. 提供 ActiveGoalView / GoalHistoryView / GoalContextView。
49. Processes 包括 Generation / Adoption / Review / Progress / Conflict / Decomposition / Closure。
50. GoalClosure 产生 GoalOutcome。
51. 重要 GoalOutcome 可以成为重大 Life Event。
52. LLM 适合 Proposal / Clarification / Decomposition / Revision。
53. LLM 不直接修改 Goal status。
54. 客观 Goal Completion 优先 deterministic / external evidence。
55. 主观 Goal Completion 可以 LLM-assisted，但必须保留 evidence refs。
56. Subjective Feasibility 与 Objective Feasibility 分离。
57. 允许不现实 Goal。
58. 允许冲突 Goal。
59. 不强制 Agent 始终理性最优。
60. 非理性 Persistence 仍需要可追踪原因。
61. 重要 Goal Change / Closure 进入 Causal Trace。

状态：

```text
Architecture Decision:
Goal v0.1

Status:
Accepted
```

---

## Architecture Decision #13J：Relationship【已敲定】

### 人话解释

Relationship 表示：

> **Agent 针对某个具体人物形成的主观关系状态。**

正式坚持：

```text
Relationship(A → B)
≠
Relationship(B → A)
```

两者独立存在。

---

### 13J.1 Objective Relation Facts 与 Subjective Relationship 分离

```text
Objective Relation Facts
= 夫妻、父子、同事、上下级等客观关系事实

Subjective Relationship State
= 信任、亲密、依恋、怨恨、尊重、依赖等主观状态
```

客观关系事实不自动决定关系质量。

---

### 13J.2 Directional State

Relationship 必须是有方向的。

A 对 B 的关系与 B 对 A 的关系互不共享。

多 Agent 之间不能直接读取对方私有 Relationship State。

---

### 13J.3 多维关系

正式禁止使用单一：

```text
favorability
```

作为 Relationship Source of Truth。

官方 v0.1 可以包含：

```text
familiarity
trust
affection
attachment
closeness
respect
dependence
resentment
obligation
```

等核心维度。

---

### 13J.4 Fast / Medium / Slow

Relationship 内部存在不同时间尺度。

例如：

```text
Fast:
tension
current salience

Medium:
closeness
trust movement

Slow:
attachment
deep trust
resentment
dependence pattern
```

一次短期冲突不应直接重写长期关系。

---

### 13J.5 Affection / Emotion 分离

长期 Affection 不等于当前 Emotion。

允许：

```text
affection high
+
current anger high
```

同时存在。

---

### 13J.6 Resentment / Anger 分离

```text
Emotion anger
= 当前生气

Relationship resentment
= 长期积累的关系性负面倾向
```

---

### 13J.7 Perceived Power

Relationship 可以保存：

```text
perceived power balance
```

但 Objective Role Power 仍属于外部关系事实 / 环境上下文。

---

### 13J.8 Profile 与 Active Context

概念上区分：

```text
RelationshipProfile
+
ActiveRelationshipContext
```

Profile 保存长期关系。

Active Context 保存当前 tension / salience / recent interaction tone 等较快状态。

---

### 13J.9 Relationship Update

正式采用：

```text
External Event
↓
Perception
↓
Memory / Belief / Existing Relationship
↓
Appraisal
↓
Emotion
↓
Relationship Update Evidence
↓
RelationshipOwner
```

Event 不直接写 Relationship。

---

### 13J.10 History-aware Update

Relationship Update 必须：

```text
bounded
+
history-aware
```

重大背叛等事件可以产生较大变化，但变化必须与事件重要度、历史关系、Appraisal 和 Evidence 匹配。

---

### 13J.11 Relationship 与 Memory

RelationshipState 不保存完整互动历史。

完整历史仍位于：

```text
Memory
Event Log
Causal Trace
```

Relationship 是长期互动在 Agent 心中的压缩状态。

---

### 13J.12 Relationship 与 Belief

Belief 可以产生：

```text
trust / respect update evidence
```

但 Belief 与 Relationship 分离。

---

### 13J.13 Relationship 与 Personality

```text
Personality
= general social bias

Relationship
= person-specific accumulated state
```

人格可以影响初始 trust baseline 等，但不能覆盖具体关系历史。

---

### 13J.14 First Impression

新人物出现时：

```text
Personality
Role
Prior Information
First Impression
Social Context
```

可以形成初始低稳定性 Relationship。

First Impression 不等于成熟长期关系。

---

### 13J.15 Relationship Label

例如：

```text
friend
partner
rival
mentor
enemy
parent
colleague
```

只是 Context / Label。

一个人物可以同时拥有多个 Label。

Label 不替代多维 Relationship Profile。

---

### 13J.16 Relationship 对其他模块

Relationship 是：

```text
Appraisal
Memory Retrieval
Belief Source Credibility
Need Assessment / Drive
Goal
Reflection
```

的重要输入。

但 Relationship 不直接修改其他 State。

---

### 13J.17 “我认为对方怎么看我”

A 无法直接读取：

```text
Relationship(B → A)
```

A 对：

> **“B 怎么看我”**

的判断属于 A 的：

```text
Belief
```

v0.1 不构建无限递归 social mental model。

---

### 13J.18 Processes

v0.1 包括：

```text
RelationshipFormationProcess
RelationshipUpdateProcess
RelationshipDecayProcess
RelationshipConflictProcess
```

Repair 可以作为特殊 Update。

---

### 13J.19 Dimension-specific Dynamics

不同 Relationship Dimension 使用不同 Dynamics。

长期不互动可能降低：

```text
closeness / salience
```

但不意味着：

```text
trust
attachment
resentment
```

统一按时间下降。

---

### 13J.20 LLM Boundary

LLM 适合：

```text
social meaning interpretation
relationship update evidence extraction
relationship summary
repair / betrayal / rejection semantic interpretation
```

LLM 不直接写：

```text
trust = 0.32
affection = 0.71
```

最终数值由 RelationshipOwner / Policy 计算。

RelationshipOwner 默认不每 Tick 调 LLM。

---

### 13J.21 Public Views

可以提供：

```text
RelationshipSummaryView
RelationshipSignificanceView
TrustView
SocialContextView
RelationshipConflictView
```

---

### 13J.22 Persistence

大量 Relationship 使用：

```text
Relationship Store
+
Active / Important Relationship Index
```

而不是巨大 AgentState JSON。

v0.1 使用 SQLite 足够。

---

### 13J.23 Relationship Formation Threshold

不是每个路人都创建长期 RelationshipProfile。

Formation Policy 可以综合：

```text
interaction repetition
importance
emotion
self relevance
goal relevance
social role
```

决定何时 materialize 长期关系。

---

### 13J.24 Initialization

重要已有关系可以在 Scenario 初始化时直接创建。

历史 / 小说人物 Relationship Initialization 必须遵守：

```text
Character Knowledge Boundary
```

只基于该角色实际经历 / 感知 / 信息访问。

初始化保留 provenance。

---

### 13J.25 Causal Trace

重要 Relationship Change 必须能够追踪：

```text
source event
memory
belief
appraisal
emotion
previous relationship state
```

让系统回答：

> **“为什么 A 现在这样看 B？”**

---

### 13J.26 Relationship v0.1 最终原则

正式接受：

1. Relationship 表示 Agent 针对具体人物形成的主观关系状态。
2. Relationship 是 directional。
3. A→B 与 B→A 独立。
4. Objective Relation Facts 与 Subjective Relationship State 分离。
5. 法律 / 亲属 / 职位关系不自动决定关系质量。
6. 不使用单一 favorability 作为 Source of Truth。
7. 官方 v0.1 使用多维 Relationship Profile。
8. 核心可包含 Familiarity / Trust / Affection / Attachment / Closeness / Respect / Dependence / Resentment / Obligation。
9. Current Tension / Salience 与长期 Profile 分离。
10. Relationship 内部支持多时间尺度。
11. Affection ≠ Current Emotion。
12. Resentment ≠ Current Anger。
13. Trust 可未来扩展为 domain-specific。
14. Perceived Power 与 Objective Role Power 分离。
15. Relationship 变化具有惯性和历史依赖。
16. 重大事件可产生大变化，但必须有结构化因果。
17. Event 不直接写 Relationship。
18. 关系更新经过 Perception / Appraisal / Evidence / Owner。
19. 相同 Event 可对不同 Agent 产生不同关系变化。
20. RelationshipState 不保存完整互动历史。
21. 历史保存在 Memory / Event / Trace。
22. Relationship 是长期互动的压缩主观状态。
23. Belief 可以影响 Relationship，但两者分离。
24. Emotion 可以影响 Relationship，但当前 Emotion 不等于长期关系。
25. Personality 提供 general social bias。
26. 新关系初始化受 Personality / Role / Prior Info / First Impression 影响。
27. First Impression 只形成低稳定性初始关系。
28. 更新应 bounded + history-aware。
29. Relationship Label 只是 Context / Metadata。
30. 一个对象可拥有多个 relation labels。
31. Goal 可以引用 Relationship / Target，但不能直接修改 Relationship。
32. Relationship 是 Appraisal 重要输入。
33. Relationship 影响 Memory Retrieval。
34. Trust 影响 Belief Source Credibility。
35. Relationship 可以经 Need Assessment 影响 Drive。
36. 长期 Relationship 经 Reflection 影响 Self Model / Narrative。
37. 多 Agent 不可互读私有 Relationship State。
38. A 不可直接知道 B→A 的真实关系状态。
39. “我认为对方怎么看我”属于 Belief。
40. v0.1 不做无限递归 social mental model。
41. Processes 包括 Formation / Update / Decay / Conflict。
42. 不同 Dimension 使用不同 Dynamics。
43. 长期不互动不意味着 Trust 自动下降。
44. LLM 用于复杂社会语义和 Update Evidence。
45. LLM 不直接写最终维度数值。
46. RelationshipOwner 根据当前状态 / 历史 / Evidence 计算最终变化。
47. RelationshipOwner 默认不每 Tick 调 LLM。
48. 提供 Relationship Summary / Significance / Trust / Social Context / Conflict Views。
49. Relationship 使用 Specialized Store / Index。
50. v0.1 SQLite 足够。
51. 不是每个陌生人都创建长期 Profile。
52. Formation Policy 决定何时 materialize。
53. 重要关系可在 Scenario 初始化时创建。
54. 历史 / 小说人物初始化遵守 Character Knowledge Boundary。
55. 初始化保留 provenance。
56. 重要 Relationship Change 进入 Causal Trace。

状态：

```text
Architecture Decision:
Relationship v0.1

Status:
Accepted
```

---

## Architecture Decision #13K：World Model【已敲定】

### 人话解释

World Model 表示：

> **Agent 对外部世界的主观结构化认知。**

它不是 AnimaFlux 内部的 World Simulator。

正式坚持：

```text
External Environment
= 世界实际上向 Agent 提供了什么

World Model
= Agent 认为这个世界大概是什么样
```

---

### 13K.1 主观性

World Model 必须允许：

```text
Incomplete
Outdated
Incorrect
Uncertain
```

Agent 不拥有上帝视角。

Objective Reality 不自动同步到 World Model。

---

### 13K.2 Belief 与 World Model

```text
Belief
= 一个具体 Proposition

World Model
= 多个 Belief 的结构化组织
```

Belief Store 是 Subjective Proposition Source of Truth。

World Model 不复制全部 Belief，而保存：

```text
belief_refs
structural relations
higher-level schemas
derived organization
```

---

### 13K.3 五类核心结构

v0.1 可以包含：

```text
Entity Knowledge
Relation Model
Causal Model
Social / Norm Model
Temporal / Predictive Model
```

---

### 13K.4 Entity Knowledge

World Model 可以引用：

```text
external entity refs
known labels
known attributes
belief refs
```

但：

> **World Model 引用外部 Entity，不拥有外部 Entity。**

不重新引入内部 World Entity System。

---

### 13K.5 Relation Model

表示 Agent 认为实体之间是什么关系。

例如：

```text
B manages Team-A
Project-P depends on Budget-Q
```

Relation Model 与 Relationship State 分离。

---

### 13K.6 Causal Model

表示：

> **Agent 认为事情通常怎样影响事情。**

Subjective Causal Model 不等于 Objective Causality。

错误因果模型是合法状态。

---

### 13K.7 Social / Norm Model

表示 Agent 对：

```text
social rules
role expectations
norms
institutional rules
```

的主观认知。

Social Norm Knowledge 与 Personal Value 分离。

---

### 13K.8 Temporal / Predictive Model

World Model 可以支持有限、局部、与当前决策相关的后果推测。

v0.1 不做完整未来世界模拟。

---

### 13K.9 Spatial / Temporal Knowledge

允许保存：

```text
X near Y
route known
office usually opens at 9
```

等 Agent 已知信息。

但不重新引入地图、寻路、物理和空间模拟系统。

---

### 13K.10 Incremental Integration

World Model 主要由：

```text
Perception
Memory
Belief Update
Communication
Reflection
```

驱动。

推荐链路：

```text
Observation
→ Perception
→ Memory
→ Belief
→ World Model Integration
```

采用增量更新，而不是每次全量重建。

---

### 13K.11 ActiveWorldModelView

当前认知只激活 World Model 的一小部分。

正式采用：

```text
WorldModelQuery
→ Relevant Nodes / Relations / Causal Beliefs
→ Budgeted ActiveWorldModelView
```

禁止把完整 World Model 注入 LLM。

---

### 13K.12 Mental Simulation

支持有限：

```text
Agent Mental Simulation
```

即：

> **Agent 在真正行动前，对可能后果做主观推演。**

正式区分：

```text
Agent Mental Simulation
≠
Runtime Resimulation
```

Mental Simulation 结果不是 Objective Event。

---

### 13K.13 Prediction

WorldModelPredictionProcess 可以产生：

```text
PredictedOutcomeSet
```

预测保留：

```text
confidence
uncertainty
source belief refs
```

Prediction 可以形成 Predictive Belief，但不新增 Core State。

---

### 13K.14 Semantic Memory / Belief / World Model

正式区分：

```text
Semantic Memory
= 我记得 / 学到过什么

Belief
= 我当前认可什么是真的

World Model
= 我怎样组织这些判断形成世界结构
```

---

### 13K.15 Relationship / Self Model Boundary

```text
World Relation
≠
Relationship State
```

World Model 描述“B 是经理”等主观世界关系。

Relationship 描述“我信不信任 B”。

同时：

```text
World Model
= world according to me

Self Model
= myself according to me
```

---

### 13K.16 Theory of Mind Boundary

v0.1 不为每个其他人物建立完整：

```text
Personality
Belief
Goal
Self Model
```

副本。

不做无限 Theory-of-Mind 递归。

允许轻量 `KnownPersonModel View`。

---

### 13K.17 World Schema

World Model 可以持久化高层 Schema：

> **某类情境通常怎样运作。**

例如：

```text
Interview Schema
Restaurant Schema
Workplace Schema
```

World Schema 与 Procedural Memory 分离但可互相引用。

---

### 13K.18 Causal Rules

Causal Rule 可以带：

```text
confidence
context_scope
conditions
exceptions
belief_refs
```

而不是全部作为确定规则。

---

### 13K.19 Conflict / Revision

World Model 允许结构冲突。

Conflict 不自动删除其中一边。

重要结构变化通过：

```text
WorldModelRevisionProcess
```

并进入 Causal Trace。

---

### 13K.20 Update Speed

World Model 总体属于：

```text
Medium / Slow State
```

局部事实结构可以快速更新。

深层 causal / social schema 更慢。

---

### 13K.21 Processes

v0.1 包括：

```text
WorldModelIntegrationProcess
WorldModelActivationProcess
WorldModelRevisionProcess
WorldModelPredictionProcess
```

可扩展：

```text
CausalModelUpdateProcess
WorldModelConsistencyProcess
```

---

### 13K.22 LLM Boundary

LLM 适合：

```text
relation extraction
schema induction
causal abstraction
conflict interpretation
revision proposal
limited subjective prediction
```

LLM 不直接创建无 Evidence 的世界事实。

LLM Prediction 不进入 Objective Event Log。

---

### 13K.23 三层 Source of Truth

正式区分：

```text
External Environment / Event Log
= Objective Runtime Evidence

Belief Store
= Subjective Proposition Source of Truth

World Model
= Subjective Structural Model
```

三层不能混。

---

### 13K.24 Persistence

World Model 可以包含：

```text
Persistent Subjective Schemas
+
Derived Index / Views
```

v0.1 使用 SQLite。

Checkpoint 保存：

```text
world_model_revision / refs
```

而不是重复复制完整认知图。

---

### 13K.25 Character Knowledge Boundary

历史 / 小说人物 World Model 必须遵守：

```text
Character Knowledge Boundary
```

未来事实、上帝视角资料、现代研究者掌握的真相都不能自动进入角色 World Model。

---

### 13K.26 Initialization

可以来自：

```text
Initial Beliefs
Semantic Memory
Character-known facts
Scenario Context
Role knowledge
Past experience
Source extraction
Simulation assumptions
```

保留：

```text
provenance
confidence
source_refs
```

---

### 13K.27 External Entity Lifecycle

外部 Entity 的变化不自动同步到 Agent World Model。

只有 Agent 获得新 Evidence 后：

```text
Observation / Communication
→ Belief Update
→ World Model Update
```

才改变。

---

### 13K.28 Public Views

可以提供：

```text
ActiveWorldModelView
EntityKnowledgeView
CausalModelView
SocialNormView
PredictedOutcomeView
DecisionWorldContext
AppraisalWorldContext
```

---

### 13K.29 Validation

Validation 只检查：

```text
reference validity
schema validity
technical consistency
confidence ranges
```

不检查 World Model 是否客观正确。

---

### 13K.30 World Model v0.1 最终原则

正式接受：

1. World Model 表示 Agent 对外部世界的主观结构化认知。
2. World Model 不是内部 World Simulator。
3. 不重新引入地图、经济、物理、城市、物品等完整世界系统。
4. External Environment 与 World Model 分离。
5. World Model 允许 Incomplete / Outdated / Incorrect / Uncertain。
6. Agent 只能根据可访问 Evidence 更新 World Model。
7. Objective Reality 不自动同步。
8. Belief 是 Proposition；World Model 是结构组织。
9. Belief Store 是 Subjective Proposition Source of Truth。
10. World Model 不完整复制全部 Belief。
11. 保存 belief refs + structural relations + higher-level schemas。
12. v0.1 包含 Entity / Relation / Causal / Social-Norm / Temporal-Predictive 五类结构。
13. World Model 引用外部 Entity，不拥有它。
14. Relation Model 与 Relationship State 分离。
15. Causal Model 是主观因果认知。
16. Social Norm Knowledge 与 Personal Value 分离。
17. Prediction 只做有限局部推演。
18. v0.1 不做完整未来世界模拟。
19. 允许有限 Spatial / Temporal Knowledge。
20. 不重新引入地图 / 路径 / 物理引擎。
21. World Model Update 主要由 Belief Change 驱动。
22. 使用 incremental integration。
23. 只激活当前相关局部内容。
24. 禁止完整 World Model 注入 LLM。
25. 使用 WorldModelQuery + Budget。
26. 支持有限 Mental Simulation。
27. Mental Simulation ≠ Runtime Resimulation。
28. Mental Simulation Result 不是 Objective Event。
29. PredictedOutcome 保留 uncertainty / confidence。
30. Prediction 可形成 Predictive Belief。
31. Semantic Memory / Belief / World Model 分离。
32. Memory 是知识痕迹，Belief 是当前认可，World Model 是结构组织。
33. World Model 与 Relationship / Self Model 分离。
34. 不做完整他人心智副本。
35. 不做无限 Theory-of-Mind 递归。
36. 可以提供轻量 KnownPersonModel View。
37. World Model 可持久化高层 Schema。
38. World Schema 表示情境通常怎样运作。
39. Procedural Memory 与 World Schema 分离但可互引。
40. Causal Rule 支持 confidence / context / exception。
41. World Model Conflict 不自动删除冲突认知。
42. 重要结构变化进入 Revision / Causal Trace。
43. World Model 属于 Medium / Slow State。
44. 局部事实可快更新，深层 Schema 慢更新。
45. Active Salience 更适合作为临时 View。
46. v0.1 Processes 包括 Integration / Activation / Revision / Prediction。
47. LLM 适合抽取、概括、Revision Proposal 和有限预测。
48. LLM 不直接创造无 Evidence 世界事实。
49. LLM Prediction 不进入 Objective Event Log。
50. Objective / Belief / World Model 三层 Source of Truth 分离。
51. World Model 包含 Persistent Schemas + Derived Views。
52. v0.1 使用 SQLite。
53. Checkpoint 保存 revision / refs。
54. 历史 / 小说人物遵守 Character Knowledge Boundary。
55. 未来事实 / 上帝视角信息不能进入。
56. 现代研究真相也不自动等于历史人物认知。
57. Initialization 来自 Initial Beliefs / Semantic Memory / Character-known facts / Scenario。
58. Initialization 保留 provenance / confidence / source refs。
59. External Entity 变化不自动同步。
60. 必须经过新 Evidence 才更新。
61. 提供 ActiveWorldModel / EntityKnowledge / Causal / SocialNorm / PredictedOutcome Views。
62. Decision / Appraisal 只获得最小相关 World Context。
63. Validation 检查技术一致性，不要求客观正确。
64. Consistency Process 发现冲突但不替 Agent 选真相。
65. 重要 World Model Change 进入 Causal Trace。

状态：

```text
Architecture Decision:
World Model v0.1

Status:
Accepted
```

---

## Architecture Decision #13L：Self Model【已敲定】

### 人话解释

Self Model 表示：

> **Agent 认为自己是什么样的人。**

正式区分：

```text
Identity
= 客观上我是谁

Self Model
= 我眼中的自己
```

---

### 13L.1 Identity 与 Self Model 分离

Identity 保存客观身份、角色和持续身份信息。

Self Model 保存：

```text
我觉得自己是谁
我觉得自己有什么能力
我怎么看自己的身体
我觉得自己在各种角色中表现怎样
```

两者可以不一致。

---

### 13L.2 Body 与 Body Image 分离

```text
Body
= 客观身体状态

Body Image
= Agent 对自己身体的主观评价
```

Body Image 属于 Self Model。

---

### 13L.3 Core Structure

Self Model v0.1 核心支持：

```text
Current Self
Ideal Self
Feared Self
Self Evaluations
```

Self Evaluations 可以包含：

```text
self_efficacy
self_esteem
body_image
role_self_views
```

---

### 13L.4 Current / Ideal / Feared Self

```text
Current Self
= 我觉得自己现在是谁

Ideal Self
= 我希望成为谁

Feared Self
= 我害怕自己变成谁
```

三者是同一个 Self Model 的不同视角，不是三个 Agent。

---

### 13L.5 Self Discrepancy

Current / Ideal / Feared Self 之间的距离通过：

```text
SelfDiscrepancyView
```

表达。

Self Discrepancy 是派生 View，不必永久存储全部 gap。

---

### 13L.6 Self-Efficacy

Self-Efficacy 表示：

> **Agent 是否相信自己能完成某类事情。**

优先采用 domain-specific 形式，例如：

```text
research
public speaking
programming
social conflict
leadership
```

不使用一个万能 `confidence` 代替全部领域能力感。

---

### 13L.7 Self-Esteem

Self-Esteem 表示：

> **较高层的整体自我价值感。**

它属于 Medium / Slow Self Evaluation。

当前 Emotion 不等于 Self-Esteem。

---

### 13L.8 Role Self-View

正式区分：

```text
Identity Role
= 客观拥有某个角色

Role Self-View
= 我认为自己在这个角色中表现怎样
```

---

### 13L.9 Self-related Belief 与 Self Model

Self-related Belief 是具体判断。

Self Model 是长期组织这些判断形成的自我结构。

长期一致的 Self-related Beliefs 可以通过 Reflection 进入 Self Model。

---

### 13L.10 Self Model 允许错误与矛盾

Self Model 不要求与 Personality、Body、Objective Performance、Other people's opinions 完全一致。

错误自我认知和内部矛盾是合法状态。

---

### 13L.11 Evidence-driven Update

单次 Event / Failure 不直接大幅修改 Self Model。

推荐链路：

```text
Event
→ Perception
→ Appraisal
→ Emotion
→ Memory
→ Self-related Belief
→ Repeated Pattern / Reflection
→ SelfModel Evidence
→ SelfModelOwner
```

---

### 13L.12 Major Life Events

重大人生事件可以触发更强 Self Model Re-evaluation。

但仍需经过：

```text
Memory
Belief
Reflection
Evidence
```

而不是 Event 直接写 Self Model。

---

### 13L.13 Main Evidence Sources

包括：

```text
Goal Outcomes
Memory
Self-related Beliefs
Relationship Feedback
Body Changes
Repeated Behavior
Identity Roles
Value-Behavior Conflict
Reflection
```

---

### 13L.14 Others' Feedback

别人对 Agent 的评价不能直接写 Self Model。

必须经过 source credibility、relationship significance、memory、belief、reflection 整合。

---

### 13L.15 Goal Outcomes

Goal Outcome 对 Self Model 的影响取决于 Appraisal / Belief / Interpretation，而不是 Goal 成功 / 失败本身。

---

### 13L.16 Personality 与 Self Model

```text
Personality
= 模拟器认为的长期响应倾向

Self Model
= Agent 自己认为的性格 / 能力 / 身份
```

两者可以不一致。

---

### 13L.17 Value 与 Self Model

Value 常影响 Ideal Self，但 Value 与 Self Model 分离。

Value-Behavior Conflict 可以通过 Appraisal / Reflection 影响 Self Model。

---

### 13L.18 Feared Self

Feared Self 可以来自：

```text
Memory
Observed others
Narrative
Value violation
Past trauma
Relationship
Social expectations
```

并作为长期 Slow State 存在。

---

### 13L.19 Time Scale

Self Model 总体属于：

```text
Medium / Slow State
```

具体领域 Self-Efficacy 可以比核心自我概念变化更快。

---

### 13L.20 Self Aspect

Self Model 应优先使用结构化：

```text
SelfAspect
```

而不是一整段自然语言。

概念属性可以包括：

```text
domain
dimension
assessment
confidence
stability
evidence_refs
```

---

### 13L.21 Natural Language Summary

自然语言 Self Summary 只作为 Derived View，用于 UI / Prompt / Reflection / Narrative，不作为唯一 Source of Truth。

---

### 13L.22 Ideal / Feared Self Storage

Ideal / Feared Self 不复制 Current Self 全部结构，只保存重要 desired / feared aspects。

---

### 13L.23 Self Model 对其他模块

Self Model 是 Drive / Goal / Appraisal / Decision / Emotion / Narrative 的重要输入。

Self-Efficacy 尤其影响 Goal Adoption / Persistence。

---

### 13L.24 Narrative 与 Self Model

```text
Self Model
= 我认为自己是谁

Narrative
= 我怎样解释自己为什么成为这样
```

两者可以互相影响，但不能合并。

---

### 13L.25 Update vs Revision

普通 Update：

```text
research self-efficacy
0.62 → 0.66
```

结构性 Revision：

```text
“我不适合科研”
→
“我擅长理论，但不擅长实验”
```

Revision 更适合由 Reflection + LLM 提出。

---

### 13L.26 LLM Boundary

LLM 适合 long-term self pattern extraction、initialization、self-conflict interpretation、Current / Ideal / Feared Self extraction、SelfModel Revision Proposal。

LLM 不直接覆盖 Self Model。

最终 Update 由 SelfModelOwner 做 bounded change。

---

### 13L.27 Initialization

原创 Agent 可以来自 manual profile / template / questionnaire / derived initial beliefs / scenario assumptions。

历史 / 小说人物可以来自 explicit self-statements、behavior、known social feedback、past goal outcomes、autobiographical memory、source interpretation，并保留 confidence / provenance / source refs。

---

### 13L.28 Character Knowledge Boundary

必须区分：

```text
外部人物评价
≠
角色自身自我认知
```

作者旁白或现代研究者判断不能自动写入角色 Self Model。

---

### 13L.29 Public Views

可以提供：

```text
CurrentSelfView
SelfEfficacyView
RoleSelfView
BodyImageView
SelfDiscrepancyView
IdentityThreatView
```

---

### 13L.30 Persistence

v0.1 使用普通 State Store 即可。

历史变化通过 State Versions / Causal Trace 保存。

---

### 13L.31 Processes

v0.1 包括：

```text
SelfModelUpdateProcess
SelfEfficacyUpdateProcess
SelfDiscrepancyProcess
RoleSelfReviewProcess
SelfModelRevisionProcess
```

---

### 13L.32 Validation

Validation 检查 reference validity / confidence range / stability range / schema version / technical consistency。

不检查 Self Model 是否客观正确。

---

### 13L.33 Self Model v0.1 最终原则

正式接受：

1. Self Model 表示 Agent 认为自己是什么样的人。
2. Identity 与 Self Model 分离。
3. Body 与 Body Image 分离。
4. 核心支持 Current / Ideal / Feared Self。
5. 三者不是三个 Agent。
6. Current Self 表示当前自我认识。
7. Ideal Self 表示希望成为谁。
8. Feared Self 表示害怕成为谁。
9. Self Discrepancy 使用派生 View。
10. Self-Efficacy 应尽量 domain-specific。
11. Self-Esteem 表示较高层整体自我价值感。
12. Global Self-Esteem 不替代领域 Self-Efficacy。
13. Body Image 属于 Self Model。
14. Role Self-View 与 Identity Role 分离。
15. Self Model 允许矛盾和分领域差异。
16. 不压缩成一个总 self_score。
17. Self-related Belief 与 Self Model 分离。
18. 单次普通 Event / Failure 不直接大幅修改 Self Model。
19. 重大事件也通过 Memory / Belief / Reflection / Evidence 更新。
20. Evidence 来自 Goal / Memory / Belief / Relationship / Body / Behavior / Reflection。
21. 别人评价不直接写 Self Model。
22. Goal Outcome 的影响取决于 Appraisal。
23. Personality 与 Self Model 分离。
24. Agent 可以错误认识自己的 Personality。
25. Value 会影响 Ideal Self。
26. Feared Self 可以长期存在。
27. Self Model 属于 Medium / Slow State。
28. SelfAspect 可拥有 Confidence / Stability / Evidence Refs。
29. 结构化 SelfAspect 是 Source of Truth。
30. 自然语言 Self Summary 只是 Derived View。
31. Ideal / Feared Self 不复制完整 Current Self。
32. Self Model 是 Drive / Goal / Appraisal / Decision 重要输入。
33. Self-Efficacy 强烈影响 Goal Adoption / Persistence。
34. Self Model 与 Narrative 分离。
35. Narrative / Reflection 可以产生 SelfModel Revision Evidence。
36. 普通 Update 与结构性 Revision 分离。
37. Update 必须 Evidence-driven + bounded。
38. LLM 适合模式总结 / 初始化 / Conflict / Revision Proposal。
39. LLM 不直接覆盖最终 Self Model。
40. SelfModelOwner 默认不每 Tick 调 LLM。
41. Initialization 支持 manual / template / source extraction / inference。
42. 历史 / 小说人物必须区分外部评价与自我认识。
43. Self Model 遵守 Character Knowledge Boundary。
44. 提供 CurrentSelf / SelfEfficacy / RoleSelf / BodyImage / SelfDiscrepancy / IdentityThreat Views。
45. v0.1 使用 State Store 即可。
46. Processes 包括 Update / SelfEfficacyUpdate / SelfDiscrepancy / RoleSelfReview / Revision。
47. Validation 检查技术一致性，不检查客观正确性。
48. 重要 Self Model Change 进入 Causal Trace。

状态：

```text
Architecture Decision:
Self Model v0.1

Status:
Accepted
```

---

## Architecture Decision #13M：Narrative【已敲定】

Narrative 表示：

> **Agent 对自己人生经历的高层组织和解释。**

正式区分：

```text
Event = 发生了什么
Memory = 我记住了什么
Belief = 我相信什么
Self Model = 我觉得自己是谁
Narrative = 我怎样解释自己为什么成为今天这样
```

### 13M.1 核心边界

- Narrative ≠ Objective Event。
- Narrative ≠ Memory。
- Narrative ≠ Belief。
- Narrative ≠ Self Model。
- Narrative 可以重新解释过去的意义，但不能改写 Objective Event。
- Narrative 不直接修改 Memory Source of Truth。
- 需要改变 Memory 表示时，必须经过 MemoryReconsolidationProcess → MemoryOwner。

### 13M.2 Structured Narrative

NarrativeState 不以单篇长文本作为唯一 Source of Truth。

v0.1 结构化支持：

```text
Life Themes
Turning Points
Life Chapters / Narrative Arcs
Causal Interpretations
Identity Statements
Current Life Chapter
```

自然语言 Life Story 只是 Derived View。

### 13M.3 Life Theme

Life Theme 表示长期反复出现的人生主题，例如：

```text
seeking approval
fear of abandonment
pursuit of independence
family responsibility
achievement through persistence
freedom vs security
```

Theme 与 Value / Personality 分离。

### 13M.4 Turning Point

Turning Point 表示：

> **Agent 主观认为改变了人生方向的重要经历。**

Objective Event Importance 不等于 Narrative Importance。

Turning Point 必须保留 source refs。

### 13M.5 Life Chapter

Narrative 支持人生阶段结构，例如：

```text
寻找方向
证明自己
建立家庭
重新开始
寻找意义
```

Chapter 可以带 start_time / end_time optional / theme_refs / turning_point_refs / important memory refs / summary。

### 13M.6 Narrative Causality

Narrative 可以表达：

> **为什么我变成了今天这样。**

这种因果解释是主观人生解释：

```text
Narrative Causality ≠ Objective Causality
```

允许错误、无法验证和反事实解释。

### 13M.7 Identity Statements / Current Life Chapter

Narrative 可以保存高层人生身份陈述，并允许 Agent 认为自己处于 transition / recovery / growth / crisis / exploration / stagnation / rebuilding 等人生阶段。

Current Life Chapter 只影响认知 Context，不直接决定 Action。

### 13M.8 Multiple Narratives

允许 multiple themes / multiple interpretations / conflicting narratives。

同一经历可以同时拥有不同意义。系统不强制唯一人生故事。

### 13M.9 Slow State

Narrative 属于典型 Slow State。

主要通过 Reflection / Major Life Event / Life Stage Transition / Long-term Pattern Accumulation 低频更新。

### 13M.10 Formation Inputs

Narrative 主要读取：

```text
Autobiographical Memory
Major Goal Outcomes
Relationship History
Self Model
Belief
Value
Identity Transition
Major Body / Life Events
Reflection
```

普通 Episodic Memory 不自动进入 Narrative。

### 13M.11 Reflection / LLM Boundary

Narrative Formation 强依赖 Reflection。

LLM 适合 long-term semantic synthesis、life theme discovery、turning point interpretation、causal interpretation、life-story compression、revision proposal。

但 LLM 不能自由编写无来源人生故事，也不能直接覆盖 NarrativeState。

### 13M.12 Evidence / Provenance

任何重要 Narrative Proposal 必须保留 memory refs / goal refs / relationship refs / self-model refs / belief refs / value refs。

Unsupported Narrative Hypothesis 不能直接成为成熟 Narrative。

Narrative 中 Fact / Interpretation / Meaning 应尽量保持边界。

### 13M.13 Narrative Bias

Narrative 可以影响 Memory Retrieval / Belief Interpretation / Appraisal / Self Model / Goal Generation / Value Development，但只能作为 bounded Bias，不能直接修改其他 State。

Narrative Reflection 应允许访问 counter-narrative evidence，防止无限自我强化。

系统不自动把负面 Narrative 改成积极 Narrative。

### 13M.14 Versioning

Narrative Revision 必须 Versioned。

旧 Narrative Version 保留，以观察一个人如何重新解释自己的过去。

### 13M.15 Initialization / Character Knowledge Boundary

从出生开始的 Agent 可以几乎没有 Narrative。

中途 Scenario 可以初始化已有 Narrative。

历史 / 小说人物必须区分：

```text
Character Self-Narrative
External Narrator Claim
Researcher Interpretation
```

外部解释不能自动写入角色 Narrative。

Narrative 遵守 Character Knowledge Boundary。

### 13M.16 Public Views

可提供：

```text
LifeThemeView
CurrentLifeChapterView
TurningPointView
ActiveNarrativeView
NarrativeIdentityView
NarrativeConflictView
```

### 13M.17 Persistence / Processes

Narrative 规模不大，v0.1 使用普通 State Store + State Version History 即可。

v0.1 Processes：

```text
NarrativeFormationProcess
TurningPointProcess
NarrativeRevisionProcess
LifeChapterProcess
NarrativeActivationProcess
```

### 13M.18 Narrative v0.1 最终原则

正式接受：

1. Narrative 是人生经历的高层组织和解释。
2. Narrative 不改写 Objective Event。
3. Narrative 不直接改写 Memory。
4. Narrative 使用结构化 Source of Truth。
5. Life Story 文本只是 Derived View。
6. 支持 Life Theme / Turning Point / Life Chapter / Causal Interpretation / Identity Statement。
7. Turning Point 是主观重要性。
8. Narrative Causality 不等于 Objective Causality。
9. 允许错误、反事实、冲突 Narrative。
10. Narrative 属于 Slow State。
11. Reflection 是主要形成和更新入口。
12. LLM 适合低频语义综合，但不能无来源编故事。
13. 重要 Proposal 必须附 Evidence Refs。
14. Narrative 只能通过 Bias 影响其他 State。
15. Narrative Revision 不自动 Reconsolidate Memory。
16. Narrative 自我强化必须 bounded / counter-evidence aware。
17. 系统不强制积极叙事。
18. Narrative Revision 需要 Versioning。
19. 历史 / 小说人物遵守 Character Knowledge Boundary。
20. 重要 Narrative Change 进入 Causal Trace。

状态：

```text
Architecture Decision:
Narrative v0.1

Status:
Accepted
```

---

## Architecture Decision #13N：Identity Implementation【已敲定】

### 人话解释

Identity 表示：

> **Agent 客观上的“是谁”。**

正式区分：

```text
Identity
= 客观上的我

Self Model
= 我眼中的我
```

---

### 13N.1 Runtime Identity 与 Life Identity 分离

`agent_id`、`runtime_id`、`branch_id`、`checkpoint_id` 等属于 Runtime Metadata。

它们不属于 Life Identity，也不应进入角色主观认知，除非 Scenario 明确要求。

---

### 13N.2 Identity Structure

Identity v0.1 采用：

```text
Persistent Identity
Current Identity
Role Identity
```

三层结构。

---

### 13N.3 Birth Time / Age / Biological Age

正式规定：

```text
birth_time
→ Identity

chronological_age
→ birth_time + Runtime Time 派生

biological_age
→ Body
```

Age 不作为直接写入 State 的字段。

---

### 13N.4 Vital Status

```text
Body.vital_status
```

是 ALIVE / DYING / DEAD 的权威 Source of Truth。

Identity 不重复保存。

---

### 13N.5 Naming

姓名属于可变化的 Current Identity。

支持：

```text
primary_name
aliases
```

历史改名通过 State Version / IdentityTransition 保存。

---

### 13N.6 Core Schema 保持小

Identity 不做现实人口档案数据库。

Core 只保存生命模拟真正需要的：

```text
subject_ref
birth_time
current naming
roles
extensible identity attributes
revision metadata
```

---

### 13N.7 Life Stage

Life Stage 默认通过：

```text
chronological age
Body
Scenario Policy
```

派生。

提供 `LifeStageView`。

不把人类固定年龄段写死在 Core。

---

### 13N.8 Role

Role 是 Identity 最重要的动态部分。

一个 Agent 可以同时拥有多个 Role。

Role 可以有：

```text
role_id
role_type
label
context_ref
status
started_at
ended_at
authority / external_ref
source_refs
```

---

### 13N.9 Role Boundary

正式区分：

```text
Role
≠ Obligation
≠ Goal
```

以及：

```text
Identity Role
≠ Role Self-View
```

客观上是研究者，不等于主观上认为自己是优秀研究者。

---

### 13N.10 External Authority

AnimaFlux 保存 life-side Role representation。

外部 Environment / Adapter 可以成为其负责领域的事实权威。

外部 Role 可以通过：

```text
external_ref
authority
```

记录来源。

---

### 13N.11 Identity Transition

身份变化必须通过：

```text
Event / Identity Evidence
↓
IdentityOwner
↓
Identity Transition
```

例如：

```text
birth
rename
graduation
employment
promotion
marriage
parenthood
retirement
```

---

### 13N.12 Identity Transition 不直接修改其他 State

IdentityTransition 可以成为：

```text
Goal
Reflection
Narrative
Value
Self Model
Relationship
```

的 Evidence / Context。

但不得直接写这些 State。

---

### 13N.13 Extensible Attributes

性别、国籍、物种、文化身份等不大规模写死进 Core Schema。

需要时通过：

```text
extensible identity attributes
```

表达。

---

### 13N.14 Update Frequency

Identity 属于典型 Slow State。

更新主要：

```text
event-driven
```

而不是每 Tick 执行。

---

### 13N.15 Processes

v0.1 包括：

```text
IdentityInitializationProcess
IdentityTransitionProcess
RoleUpdateProcess
LifeStageDerivationProcess
IdentityValidationProcess
```

---

### 13N.16 Initialization

从出生启动：

```text
birth_time
initial name
initial roles optional
```

中途 Scenario / 历史人物：

```text
birth_time
current name
current objective roles
```

并保留：

```text
EXPLICIT
SOURCE_CLAIM
INFERRED
ASSUMPTION
```

provenance。

---

### 13N.17 Conservative Inference

Identity 属于偏客观状态。

正式原则：

> **Unknown 优于无来源硬猜。**

争议身份事实可以带 confidence / alternative claim refs，但不把全部 Identity 概率化。

---

### 13N.18 Objective Identity 与 Agent Knowledge 分离

Objective Identity 可以包含 Agent 当前自己并不知道的信息。

因此 Identity Capability 必须遵守 Knowledge Boundary。

正式区分：

```text
ObjectiveIdentityView
KnownIdentityView / cognitive identity context
```

主观“我是谁”仍由 Belief / Self Model / Memory 表达。

---

### 13N.19 Self-Claim 不等于 Identity Fact

Agent / LLM 说：

```text
“我已经是医生。”
```

不能自动修改 Identity。

正式坚持：

> **Self-claim does not mutate objective Identity.**

IdentityOwner 只接受具有客观 / 权威来源的 Transition Evidence。

---

### 13N.20 Death

死亡不会删除 Identity。

Body.vital_status 决定生命循环停止。

Identity / History / Narrative / Relationship impact 仍然保留。

---

### 13N.21 LLM Boundary

IdentityOwner 运行期默认 deterministic。

LLM 主要用于：

```text
unstructured identity evidence extraction
historical / fictional source parsing
role evidence extraction
```

LLM 不直接决定 Objective Identity Change。

---

### 13N.22 Validation

Identity Validation 可以完全 deterministic，例如：

```text
birth_time <= runtime time
role.started_at <= role.ended_at
role ids unique
revision monotonic
only one active primary_name
```

Derived age 不接受直接写入。

---

### 13N.23 Versioning

Identity Change 必须 Versioned。

当前 IdentityState 不内嵌完整身份历史。

历史通过：

```text
State Version
IdentityTransitionRecord
Causal Trace
```

保存。

---

### 13N.24 Public Views

可以提供：

```text
IdentitySummaryView
ActiveRoleView
ChronologicalAgeView
LifeStageView
IdentityTransitionView
```

不同 Observer Scope：

```text
Operator
Researcher
Life
```

可以获得不同程度的 Identity 信息。

---

### 13N.25 Identity v0.1 最终原则

正式接受：

1. Identity 表示 Agent 客观上的“是谁”。
2. Identity 与 Self Model 分离。
3. Runtime ID / Branch ID 不属于 Life Identity。
4. Identity 不感知 Checkpoint / Plugin 等 Runtime Metadata。
5. 采用 Persistent / Current / Role 三层结构。
6. birth_time 属于 Identity。
7. chronological age 派生，不持久化。
8. biological age 属于 Body。
9. vital_status 权威属于 Body。
10. 姓名属于 Current Identity。
11. Identity Core Schema 保持小而可扩展。
12. Life Stage 默认派生。
13. LifeStagePolicy 可替换。
14. 一个 Agent 可以同时拥有多个 Role。
15. Role 有生命周期。
16. Role ≠ Obligation ≠ Goal。
17. Identity Role ≠ Role Self-View。
18. 外部 Environment 可以成为部分 Role 的事实权威。
19. 外部 Role 保留 external_ref / authority。
20. 无外部世界时 Scenario Bootstrap 可初始化 Role。
21. Role Change 必须经过 Identity Transition Evidence。
22. IdentityTransition 是重要 Life Change。
23. IdentityTransition 不直接修改其他 State。
24. 额外人口统计信息通过可扩展 attributes。
25. Identity 不保存 current location。
26. Identity 不保存 Personality / Goal / Belief / Narrative 等。
27. Identity 属于 Slow State。
28. Identity Update 主要 event-driven。
29. v0.1 Processes 包括 Initialization / Transition / RoleUpdate / LifeStageDerivation / Validation。
30. 历史 / 小说人物初始化保留 provenance。
31. Identity 推断应保守。
32. Unknown 优于无来源猜测。
33. 争议事实可选 confidence / alternative claims。
34. Objective Identity 可以包含 Agent 自己不知道的信息。
35. Identity Capability 遵守 Knowledge Boundary。
36. ObjectiveIdentityView 与 Agent-known identity context 分离。
37. 主观身份认知仍由 Belief / Self Model / Memory 表达。
38. 死亡不删除 Identity。
39. IdentityOwner 默认 deterministic。
40. LLM 主要用于 Identity Evidence Extraction。
41. Self-claim 不直接修改 Objective Identity。
42. IdentityOwner 只接受客观 / 权威 Transition Evidence。
43. Validation 完全可 deterministic。
44. Derived age 不接受直接写入。
45. Identity 修改必须 Versioned。
46. 当前 State 不内嵌完整身份历史。
47. 历史由 Version / TransitionRecord / Trace 保存。
48. 提供 IdentitySummary / ActiveRole / ChronologicalAge / LifeStage / IdentityTransition Views。
49. Observer Scope 控制不同视角可见信息。
50. 重要 Identity Change 进入 Causal Trace。

状态：

```text
Architecture Decision:
Identity Implementation v0.1

Status:
Accepted
```

---

# Stage D：Core State Implementation【完成】

13 个 Core State 全部完成 v0.1 方案：

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

现在进入：

# Stage E：Core Cognitive Processes

## Architecture Decision #14A：Perception【已敲定】

### 核心定义

Perception 是 Process，不新增 Core State。

正式链路：

```text
External Reality
↓
Observation Opportunity
↓
Sensory Gate
↓
Attention Selection
↓
Perceptual Interpretation
↓
PerceivedEventSet
```

正式坚持：

```text
Reality
≠
Observation
≠
Perception
```

### 14A.1 Sensory Gate

Body 决定：

> **能不能感知。**

Perception 决定：

> **实际上感知到了什么。**

Environment Adapter 负责提供合理的 Observation Opportunity。

AnimaFlux 不内部实现光学、声学、3D 遮挡等完整物理感知模拟。

### 14A.2 Attention

Attention 属于临时 Cognitive Context，不新增长期 AttentionState。

必须存在：

```text
Attention Budget
```

避免 Agent 处理全部 Observation。

Attention 可以综合：

```text
Novelty
Intensity
Goal Relevance
Drive Relevance
Emotion Relevance
Self Relevance
Relationship Relevance
Threat
Expectation Violation
Task Relevance
```

Goal / Drive / Emotion / Relationship / Self / Narrative 只形成 bounded top-down bias。

它们不能凭空创造不存在的外部事实。

### 14A.3 Perceptual Interpretation

Perception 负责：

```text
我注意到了什么
我听见 / 看见 / 感觉到了什么
表层语义是什么
```

Appraisal 负责：

```text
这件事对我意味着什么
```

Belief 负责：

```text
我最终认为哪些判断是真的
```

因此 Perception 只做浅层语义理解，不承担深层个人意义判断。

### 14A.4 PerceivedEvent

Perception 的标准输出为：

```text
PerceivedEventSet
```

单个 PerceivedEvent 概念上包含：

```text
source_observation_refs
source_event_refs optional
modality
perceived_content
confidence
clarity
salience
uncertainty
entity_refs
noticed_at
```

同一个 Objective Event 可以对不同 Agent 产生 0..N 个不同 PerceivedEvents。

### 14A.5 Misperception

允许：

```text
听错
看错
认错
漏掉
理解不完整
```

但错误必须有机制来源，例如：

```text
low clarity
noise
occlusion
attention interruption
ambiguity
limited information
bounded prior expectation bias
```

正式原则：

> **允许有来源的误感知，不允许无来源的 LLM hallucination 被当作 Perception。**

### 14A.6 Observer Boundary

Agent 通常不知道自己遗漏了什么。

Operator / Researcher 可以查看：

```text
available observations
selected observations
dropped observations
perception trace
```

Life 视角只能得到真正的 PerceivedEventSet。

### 14A.7 Interoception

对身体内部状态的感知属于 Perception Process。

正式区分：

```text
Objective Body State
≠
Perceived Internal Signal
```

例如：

```text
Body pain signal
→ Perceived pain
→ Appraisal
→ subjective suffering / Emotion
```

### 14A.8 Recognition vs Recall

正式区分：

```text
Recognition
= “这是 B”
→ 可以属于 Perception

Recall
= “我想起 B 五年前背叛我”
→ 属于 Memory Retrieval
```

Perception 只允许轻量 recognition context，不做深层 Autobiographical Retrieval。

### 14A.9 Processes

v0.1 可以包含：

```text
ObservationIngestionProcess
SensoryGatingProcess
AttentionSelectionProcess
PerceptualInterpretationProcess
InteroceptionProcess
```

核心仍是：

```text
Sensory Gate
Attention Selection
Perceptual Interpretation
```

### 14A.10 Randomness

Attention 在相近候选之间可以使用小幅 `RandomService`。

随机必须可复现。

高威胁 / 高显著性输入可以抢占当前注意力。

### 14A.11 LLM Boundary

结构化 Observation：

```text
优先 deterministic parsing
```

复杂自然语言 / 社会线索 / 模糊语义：

```text
可选 LLM semantic interpretation
```

LLM 输出必须结构化。

LLM 不直接输出：

```text
最终 Emotion
成熟 Belief
个人意义结论
```

### 14A.12 Memory / Belief Boundary

PerceivedEvent 不自动形成长期 Memory。

```text
看见
≠
记住
```

PerceivedEvent 只是 Belief Formation 的 Evidence，不等于成熟 Belief。

### 14A.13 Communication Input

用户、其他 Agent、NPC 等语言输入统一走：

```text
Environment Adapter
↓
Communication Observation
↓
Perception
```

不建立独立 Chatbot 认知链。

### 14A.14 Action Result Visibility

正式区分：

```text
Objective Action Result
≠
Actor-visible Observation
```

Environment Adapter 必须决定：

> 哪些结果对哪个 Agent 可见。

不可见结果不能偷偷进入 Agent Perception。

### 14A.15 Context Budget

Perception 只读取最小 Context，例如：

```text
sensory capability
current focus
active goals
dominant drives
affective summary
relevant relationship summary
small recognition hints
```

禁止读取完整 Memory / Belief / Narrative / Relationship Store。

### 14A.16 Failure Policy

复杂语义 Parser 失败时可以降级：

```text
partial perception
uncertain perception
raw recognized content
```

关键结构化感知优先 deterministic。

Perception confidence / uncertainty 必须传递给下游。

### 14A.17 Persistence / Trace

Perception 不新增长期 PerceptionState。

当前结果存在 Tick Cognitive Context。

重要 PerceivedEvent / Misperception 可以进入 Causal Trace：

```text
Objective Event
→ Observation
→ PerceivedEvent
→ Appraisal
→ State Change
```

### 14A.18 Perception v0.1 最终原则

正式接受：

1. Perception 是 Process，不新增 Core State。
2. Reality / Observation / Perception 分离。
3. Observation 表示感知机会，不代表真正注意到。
4. Perception 采用 Sensory Gate → Attention → Interpretation。
5. Body 决定感官能力。
6. Environment Adapter 负责世界侧可见性。
7. AnimaFlux 不做完整物理感知模拟。
8. Attention 有有限 Budget。
9. 不允许 Agent 全量处理所有 Observation。
10. Top-down State 只能形成 bounded Attention Bias。
11. Bias 不能凭空制造世界事实。
12. Perception 回答“我注意到了什么”。
13. Appraisal 回答“这对我意味着什么”。
14. Belief 回答“我认为哪些判断是真的”。
15. PerceivedEvent 是标准输出。
16. 一个 Objective Event 可以产生多个 Agent-specific PerceivedEvents。
17. Confidence / Clarity / Salience / Uncertainty 分离。
18. 允许有来源的 Misperception。
19. 不允许无来源 LLM hallucination 进入感知事实。
20. Agent 通常不知道自己遗漏了哪些信息。
21. Operator / Researcher 可以查看 dropped trace。
22. Interoception 属于 Perception。
23. Objective Body ≠ Subjective Internal Perception。
24. Recognition 与 Recall 分离。
25. Perception 不做深层 Memory Retrieval。
26. Attention 可以有可复现小幅随机性。
27. 高显著性输入可以抢占 Attention。
28. 结构化 Observation 优先 deterministic。
29. LLM 只负责复杂语义解析。
30. LLM 输出必须结构化。
31. LLM 不直接产生 Emotion / mature Belief。
32. PerceivedEvent 不自动成为长期 Memory。
33. Perception Output 是 Belief 的 Evidence，不是 Belief 本身。
34. Communication Input 统一走 Environment → Observation → Perception。
35. Objective Result 与 Agent-visible Result 分离。
36. Perception Context 受 Budget 控制。
37. Perception 不读取整个长期 Store。
38. 语义 Parser 失败可以降级。
39. 不确定性必须向下游传播。
40. Perception 不新增持久 State。
41. 重要 Perception / Misperception 进入 Causal Trace。
42. Core Protocol 不写死唯一 Attention 心理模型。
43. 官方 v0.1 提供有限注意 + 可选 LLM 语义解析的默认实现。

状态：

```text
Architecture Decision:
Perception v0.1

Status:
Accepted
```

---

## Architecture Addendum：Communication 作为 Stage E 核心 Process【已敲定】

交流能力正式纳入 AnimaFlux v0.1。

Communication 不新增第14个 Core State。

正式原则：

```text
Communication
= Cognitive / Action Process
```

而不是长期生命状态。

### 通信总链路

```text
Agent A
↓
Decision
↓
Communicative Intent
↓
Language Realization
↓
Communicative Action Intent
↓
Environment Adapter
↓
External Communication Event
↓
Recipient-visible Observation
↓
Agent B Perception
↓
Memory Retrieval / Appraisal / Belief / Relationship / Emotion
```

### 核心边界

正式接受：

1. Agent-to-Agent Communication 必须经过 Environment，不直接互读 Cognitive State。
2. Human ↔ Agent 也使用同一 Interaction Boundary。
3. Incoming Communication 统一作为 Observation 进入 Perception。
4. Outgoing Communication 从 Decision 产生 Communicative Intent。
5. Communicative Intent ≠ Utterance。
6. Decision 决定“要不要说、说什么、透露多少”。
7. Language Realization 负责“具体怎么表达”。
8. Receive Message 不代表 Must Reply。
9. Knowledge Availability ≠ Disclosure Choice。
10. Agent 可以选择沉默、回避、部分披露、澄清、询问、拒绝等行为。
11. 允许 deception / concealment，但必须是有因果、有 Intent 的行为。
12. LLM 不得把 hallucination 伪装成 Agent Knowledge。
13. Language Realization 只能使用 Agent 可访问的 Knowledge / Intent。
14. Communication Validation 检查 Intent Fidelity 与 Knowledge Grounding。
15. 交流效果由接收者自己的 Perception + Appraisal 决定。
16. Sender 不能直接指定 Receiver 的 Emotion / Belief / Relationship Change。
17. ConversationContext 属于临时 Runtime Context，不新增 Core State。
18. 长期重要交流沉淀到 Memory / Belief / Relationship / Goal 等现有 State。
19. Communication 不维护另一套长期聊天历史 Source of Truth。
20. Communication 可作为主动获取信息的行为，例如 ASK / CLARIFY / VERIFY。
21. Speech Act 可形成 Promise / Request / Agreement 等 Evidence，但不新增 Commitment Core State。
22. Personality / Emotion / Relationship / Role / Social Context 可以影响表达风格。
23. 它们提供 Style Bias，不直接决定固定台词。
24. 多人可见性 / 私聊 / 公共频道由 Environment Adapter 负责。
25. A 不能通过 Communication 直接修改 B 的内部状态。
26. Communication 是让 Memory / Belief / Value / Relationship / Goal / Self 等模块进入社会互动闭环的关键 Process。

### Stage E 顺序更新

Stage E 正式调整为：

```text
#14A Perception
#14B Appraisal
#14C Memory Retrieval
#14D Decision / Planning
#14E Communication
#14F Reflection
```

Communication 的完整字段、协议、Validation 和 LLM Realization 契约将在 #14E 进一步细化。

状态：

```text
Architecture Decision:
Communication Placement v0.1

Status:
Accepted
```

---

## Architecture Decision #14B：Appraisal【已敲定】

### 核心定义

Appraisal 是 Process，不新增 Core State。

正式区分：

```text
Perception = 我感知到了什么
Appraisal = 这件事对我意味着什么
Emotion = 我因此产生什么感受
Belief = 我认为哪些判断是真的
Decision = 我最终准备怎么做
```

### 14B.1 多维 Appraisal

Appraisal 不能压缩成单一正负分。同一事件可以同时支持一个 Goal、威胁另一个 Goal、符合一个 Value、违反另一个 Value，并带来 Self / Relationship / Drive 等不同意义。

### 14B.2 Primary / Secondary Appraisal

官方 v0.1 可以采用两组问题：

```text
Primary: 这件事和我有什么关系？
Secondary: 我能怎么办？
```

Primary 可包含 relevance、novelty / expectedness、goal impact、value impact、self relevance、relationship relevance、drive / need relevance、threat / loss / opportunity / gain。

Secondary 可包含 agency / responsibility、controllability、coping potential、certainty、urgency、future implication、available resources。

Core Protocol 不绑定唯一心理学理论。

### 14B.3 Relevance Screening / Cognitive Budget

昂贵 Appraisal 前先做 Relevance Screening。低相关事件可以 minimal appraisal 或跳过深层 Appraisal。Appraisal 必须受 Cognitive Budget 控制。

### 14B.4 Appraisal Inputs

Appraisal 只读取筛选后的 View，例如：

```text
RetrievedMemorySet
RelevantBeliefView
ActiveGoalView
ActiveValueView
RelationshipSignificanceView
CurrentSelfView
PersonalityBiasView
BodyStatusView
MotivationalContextView
ActiveWorldModelView
ActiveNarrativeView
AffectiveContextView
```

不能直接访问完整 Store。

### 14B.5 AppraisableItem

Appraisal 不只处理 PerceivedEvent，也可处理 Retrieved Memory、Predicted Outcome、Perceived Internal Signal、Goal Threat、Self Discrepancy 等 AppraisableItem，但都受 Budget 控制。

### 14B.6 AppraisalResult

概念上包含：

```text
appraisable_item_ref
relevance
overall_significance
novelty / expectedness
goal_impacts[]
value_impacts[]
self_impacts[]
relationship_impacts[]
drive_need_impacts[]
attribution
controllability
coping_potential
certainty
urgency
anticipated_consequences[]
tags[]
confidence
source_refs
reason_codes
reappraisal_of optional
```

overall_significance 不能替代具体 Facets。

### 14B.7 Attribution / Coping

Agency / Responsibility 属于主观 Attribution，不是 Objective Truth。需要长期保留时，由 Belief System 决定是否形成成熟 Belief。

正式区分：

```text
Controllability = 事情还能不能被改变
Coping Potential = 我有没有能力 / 资源应付它
```

### 14B.8 Mixed Meaning

Appraisal 必须保留混合与冲突意义，而不是压成单一 valence。一个事件可以同时是 Opportunity、Loss、Value Conflict、Identity Threat。

### 14B.9 No Direct Mutation

AppraisalResult 是 Cognitive Artifact，不是 State Mutation。

Emotion、Drive、Relationship、Belief、Memory、Goal、Decision 等下游 Process 读取 AppraisalResult 后，再由各自 Owner 更新状态。

### 14B.10 LLM Boundary

简单 / 结构化 Appraisal 优先 deterministic。复杂社会 / 语义 Appraisal 可选 LLM。

LLM 只输出 Structured Appraisal Proposal，不直接产生最终 Emotion / Belief / Decision。

LLM 必须遵守 Character Knowledge Boundary，只能看到 Agent 可访问的 PerceivedEvent 与 Context。

### 14B.11 Wrong Appraisal / Reappraisal

Appraisal 可以错误。Runtime 不自动纠正。

出现新 Evidence 时，可以触发 bounded、Evidence-grounded 的 Reappraisal。

Reappraisal 不允许无限递归，也不自动把负面解释改成积极解释。

### 14B.12 Failure Policy

复杂 LLM Appraisal 失败时，降级为 minimal / uncertain appraisal。

原则：

> **Unknown / Uncertain 优于无来源乱猜。**

### 14B.13 Persistence / Trace

Appraisal 不需要长期 State Store。重要 AppraisalResult 进入 Trace Store，形成：

```text
PerceivedEvent
→ Context
→ Appraisal
→ Emotion / Belief / Relationship / Decision
```

的可追踪因果链。

### 14B.14 Appraisal v0.1 最终原则

正式接受：

1. Appraisal 是 Process，不新增 Core State。
2. Perception / Appraisal / Emotion / Belief / Decision 分离。
3. 同一事件对不同 Agent 可以产生不同 Appraisal。
4. Appraisal 必须多维。
5. Core 不绑定唯一心理学理论。
6. 深层 Appraisal 前先做 Relevance Screening。
7. Appraisal 受 Cognitive Budget 控制。
8. Goal / Value / Self / Relationship / Drive 都可贡献意义 Facet。
9. Novelty 与 Importance 分离。
10. Threat / Loss / Opportunity / Gain 等可作为默认 Tags，但 Core 不写死。
11. Agency / Responsibility 是主观 Attribution。
12. Controllability 与 Coping Potential 分离。
13. Certainty / Ambiguity 必须保留。
14. Future Implication 可以读取 World Model Prediction。
15. Predicted Outcome 不是 Objective Event。
16. Appraisal 支持通用 AppraisableItem。
17. AppraisalContext 只由有限 View 组成。
18. Appraisal 不直接访问底层 Store。
19. Prior Mood / Emotion 可形成 bounded Bias。
20. Personality / Narrative / Self 只形成 bounded Interpretation Bias。
21. Bias 不能压过 Counter-Evidence。
22. AppraisalResult 由多个 Facet 组成。
23. Confidence 必须向下游传播。
24. Appraisal 不直接修改任何 Core State。
25. 下游 Process 根据 AppraisalResult 形成各自 Evidence / Influence。
26. Memory Formation 可使用 Appraisal Significance。
27. Appraisal Importance 与 Emotion Intensity 分离。
28. Belief Update 可读取 Attribution，但 Appraisal 不判定真值。
29. Relationship Update 可读取 Appraisal，但最终变化由 Owner 决定。
30. Goal Review 可读取 Goal Impact，但 Appraisal 不改 Goal Status。
31. 简单 Appraisal 优先 deterministic。
32. 复杂语义 Appraisal 可以使用 LLM。
33. LLM 只输出 Structured Appraisal Proposal。
34. LLM 不直接产生最终 Emotion / Belief / Decision。
35. Appraisal 遵守 Character Knowledge Boundary。
36. Appraisal 可以错误。
37. Runtime 不自动纠正错误 Appraisal。
38. 新 Evidence 可触发 Reappraisal。
39. Reappraisal 必须 Evidence-grounded + bounded。
40. 不允许无界递归 Reappraisal。
41. 系统不自动强行积极解释。
42. LLM 失败时降级为 uncertain appraisal。
43. Unknown / Uncertain 优于无来源乱猜。
44. 重要 AppraisalResult 进入 Causal Trace。
45. Appraisal 不需要长期 State Store。

状态：

```text
Architecture Decision:
Appraisal v0.1

Status:
Accepted
```

---

## Architecture Decision #14C：Memory Retrieval【已敲定】

Memory Retrieval 是 Process，不新增 Core State。

正式区分：

```text
Memory Store = 我过去记住了什么
Memory Retrieval = 我现在偏偏想起什么
```

Memory Retrieval 不等于 Vector Top-K。

### 14C.1 Retrieval Signals

官方 v0.1 Retrieval 可以综合：

```text
Semantic Relevance
Recency
Accessibility
Importance
Emotional Salience
Person Relevance
Goal Relevance
Drive Relevance
Self Relevance
Relationship Relevance
Context Relevance
```

具体权重由 `MemoryRetrievalPolicy` 决定。

### 14C.2 Structured Retrieval Request

使用结构化 `MemoryRetrievalRequest`，而不是单一字符串 Query。Query 可以包含 semantic query、entity/person refs、time scope、goal/drive/relationship/self refs、emotion context、memory types、retrieval mode 和 budget。

Query 由 Runtime / Memory Retrieval Process 构建；LLM 可辅助 Reformulation，但不能直接扫描 Memory Store。

### 14C.3 Cued / Deliberate Retrieval

v0.1 正式支持：

```text
Cued Retrieval
Deliberate Retrieval
```

Cued Retrieval 主要位于 Perception 后、Appraisal 前。

Deliberate Retrieval 可由 Decision / Communication / Reflection 主动触发。

### 14C.4 Hybrid Retrieval

Candidate Generation 采用多路召回，例如 semantic vector、person-linked、goal-linked、relationship-linked、recent、importance、metadata candidates。

官方 v0.1 推荐 Hybrid Retrieval。

Vector Index 是 Derived Index；Memory Store 始终是 Source of Truth。

### 14C.5 Accessibility / Forgetting

正式坚持：

```text
Stored ≠ Currently Retrievable
```

Forgetting 主要通过 Accessibility Decay 表现，而不是删除 Memory。

Importance 高不代表永远能轻易想起。

### 14C.6 Ranking / Bias

Retrieval Policy 可使用 hard filter / soft score / boost。

Emotion / Mood / Narrative 只能形成 bounded retrieval bias，不能把相反 Evidence 永久屏蔽。

Goal / Drive / Self / Relationship / Person Context 是重要 Signals。

### 14C.7 Diversity

Retrieval 必须支持 diversity-aware selection / deduplication / near-duplicate suppression。

允许有限 Counter-Evidence Opportunity，但不强制机械 50/50 平衡。

### 14C.8 Budget

Retrieval 至少受：

```text
memory_count_budget
token_budget
```

限制。

禁止把大量人生 Memory 全部注入当前 Cognitive Context。

### 14C.9 Progressive Disclosure

Memory 可以提供 compact / standard / expanded 多级 View。

默认使用 compact；关键 Memory 可 bounded expansion。

### 14C.10 Context Expansion Retrieval

标准流程：

```text
Perception
→ Initial Retrieval
→ Appraisal
```

高 significance / high uncertainty / insufficient context 时，可以触发一次或少量 Context Expansion Retrieval，再进行 bounded Reappraisal。

禁止无限 Retrieval / Appraisal 循环。

### 14C.11 RetrievedMemorySet

`RetrievedMemorySet` 是结构化 Cognitive Artifact，可包含 memory refs、memory type、compact content、retrieval score、relevance factors、confidence、source refs、budget used、retrieval mode、trace metadata。

Life-level View 不必暴露具体算法 score。

### 14C.12 Confidence / Provenance

Memory Confidence / Provenance 必须随 Retrieved View 传递。

Reconstructed / Generalized / Autobiographical Memory 必须保留来源。

### 14C.13 Read-only / Reactivation

Retrieval 默认 read-only。

Retrieval 不直接修改 Memory 内容。

可以产生 `MemoryReactivationEvidence`，由 MemoryOwner bounded 更新 Accessibility / last_retrieved_at。

### 14C.14 Retrieval ≠ Reconsolidation

```text
想起来 ≠ 改写记忆
```

Memory Content Revision 仍需 MemoryReconsolidationProposal → MemoryOwner。

### 14C.15 Appraisal / Association

Retrieved Memory 可成为 AppraisableItem，但不能直接修改 Emotion。

v0.1 只允许轻量 bounded associative retrieval，不允许无限联想链。

### 14C.16 Type-aware Retrieval

Semantic / Episodic / Procedural / Autobiographical Memory 可以使用不同 Representation。

Procedural Memory 可通过 Procedure Capability 提供 know-how。

### 14C.17 Retrieval Failure

Deliberate Retrieval 可以合法返回 FOUND / PARTIAL / UNCERTAIN / NOT_FOUND 等语义。

原则：

> **“想不起来”是合法认知结果。**

系统不得让 LLM 编造缺失 Memory。

### 14C.18 LLM Boundary

LLM 适合 complex query reformulation、small candidate reranking、semantic clustering / dedup、memory compression。

Primary Candidate Retrieval 必须主要由代码 + Index 完成。

LLM 绝不能发明不存在的 Memory。

### 14C.19 Character Knowledge Boundary

Memory Retrieval 只能访问 Agent 自身拥有的 Memory。

历史 / 小说人物不能把现代资料、Objective Event Log 或 Researcher Knowledge 当作自身 Memory 检索。

### 14C.20 Replay / Failure Isolation

Randomness 使用 RandomService。

Exact Replay 可以读取历史 RetrievedMemorySet；Resimulation 根据 Branch 当前状态重新 Retrieval。

Vector Index 故障时可降级到 metadata / recent / exact refs / keyword / SQLite Search。

Vector Index 故障不能影响 Memory Source of Truth。

### 14C.21 Causal Trace

Research Trace 可以记录 query、candidate source、ranking factor、selection、budget、dropped candidates。

Life 视角不暴露内部 Ranking 算法。

重要 Retrieval / Reactivation 进入 Causal Trace。

### 14C.22 Memory Retrieval v0.1 最终原则

正式接受：

1. Memory Retrieval 是 Process，不新增 Core State。
2. Memory Store 与当前 Retrieval 分离。
3. Retrieval 不等于 Vector Top-K。
4. Semantic Similarity 只是一个 Signal。
5. Retrieval 综合语义、时间、可访问性、重要度、情绪、人物、Goal、Drive、Self、Relationship、Context。
6. 权重属于 MemoryRetrievalPolicy。
7. 使用结构化 MemoryRetrievalRequest。
8. Query 由 Runtime / Memory Process 构建。
9. LLM 可辅助 Reformulation，但不能扫描 Memory Store。
10. 支持 Cued / Deliberate Retrieval。
11. Cued Retrieval 位于 Perception 后、Appraisal 前。
12. Deliberate Retrieval 可由 Decision / Communication / Reflection 发起。
13. Candidate Generation 使用多路召回。
14. 官方 v0.1 推荐 Hybrid Retrieval。
15. Vector Index 只是 Derived Index。
16. Memory Store 是 Source of Truth。
17. Accessibility 决定当前可召回性。
18. Forgetting 主要通过 Accessibility Decay。
19. Emotion / Narrative 只能形成 bounded Bias。
20. Goal / Drive / Self / Relationship / Person 是重要 Signals。
21. Retrieval 必须 Diversity-aware。
22. 可保留有限 Counter-Evidence Opportunity。
23. 使用 memory_count_budget + token_budget。
24. Memory 支持 compact / standard / expanded View。
25. Detail Expansion 必须 bounded。
26. 标准流程为 Initial Retrieval → Appraisal。
27. 必要时允许 Context Expansion Retrieval → bounded Reappraisal。
28. 不允许 Retrieval / Appraisal 无限循环。
29. RetrievedMemorySet 是结构化 Cognitive Artifact。
30. Confidence / Provenance 必须传下游。
31. Retrieval 默认 read-only。
32. Retrieval 可产生 Reactivation Evidence。
33. Retrieval ≠ Reconsolidation。
34. Retrieved Memory 可以成为 AppraisableItem。
35. Associative Retrieval 只允许 bounded expansion。
36. Retrieval 必须 memory-type aware。
37. Deliberate Retrieval 可以合法 NOT_FOUND / UNCERTAIN。
38. “想不起来”是合法结果。
39. LLM 只适合小规模语义辅助。
40. Primary Retrieval 由代码 + Index 完成。
41. LLM 不能发明 Memory。
42. Retrieval 遵守 Character Knowledge Boundary。
43. Exact Replay 可读取历史 Retrieval Result。
44. Resimulation 重新 Retrieval。
45. Vector Index 故障可降级。
46. Life 视角不暴露 Ranking 算法。
47. 重要 Retrieval / Reactivation 进入 Causal Trace。

状态：

```text
Architecture Decision:
Memory Retrieval v0.1

Status:
Accepted
```

---

## Architecture Decision #14D：Decision / Planning【已敲定】

### 核心定义

正式区分：

```text
Drive = Why
Goal = What
Decision = 现在选哪个方向
Plan = How
Action Intent = 这次准备做什么
Action Result = 外部世界实际发生什么
```

Decision / Planning 是 Process，不新增 Core State。

---

### 14D.1 Bounded Rationality

AnimaFlux 不把 Agent 设计成全知、无限搜索、永远求数学最优的规划器。

正式采用：

> **Bounded Rationality（有限理性）**

Agent 只在：

```text
有限 Candidate
有限 Context
有限时间 / Budget
主观 Belief / World Model
当前心理状态
```

下做选择。

---

### 14D.2 No-action / Wait / Defer

不是每个 Tick 都必须产生外部行为。

允许：

```text
NO_ACTION
WAIT
DEFER
CONTINUE
```

“暂时不决定”本身是合法 Decision。

---

### 14D.3 Decision Context

Decision 读取有限 View / Cognitive Artifact，例如：

```text
Appraisal
Active Goals
Active Drives
Active Values
Relevant Beliefs
Retrieved Memories
Emotion / Mood
Relevant Relationships
Self Model
World Model
Narrative Context
Body Capability
Identity / Roles
Environment-visible Constraints
```

不得直接访问完整底层 Store。

---

### 14D.4 Four-stage Decision

v0.1 默认：

```text
1. Decision Framing
2. Candidate Generation
3. Candidate Evaluation
4. Selection / Commitment
```

然后在需要时：

```text
Planning
```

---

### 14D.5 Decision Framing

先明确：

> **“当前到底在决定什么？”**

DecisionFrame 可以包含：

```text
decision_problem
trigger_refs
relevant_goal_refs
time_horizon
urgency
deadline optional
known_constraints
uncertainties
```

低意义事件无需进入 Deliberative Decision。

---

### 14D.6 Candidate Generation

候选来源可以包括：

```text
existing plan
habit
procedural memory
goal-specific policy
environment available actions
world model
past successful behavior
optional LLM proposal
```

候选必须受：

```text
candidate_budget
```

限制。

---

### 14D.7 Candidate Feasibility

正式区分：

```text
Subjective Feasibility
≠
Objective Executability
```

Agent 根据自己知道的 Body / Belief / World Model / Environment Context 判断“我能不能做”。

真正能否执行由 Environment 决定。

---

### 14D.8 Candidate Validation

候选进入评估前需要 Validation：

```text
action schema valid
capability available
knowledge boundary respected
body feasibility
known resource availability
environment contract
target validity
```

LLM 不能凭空添加能力、人物或资源。

---

### 14D.9 Candidate Evaluation

不使用单一 Universal Utility Score 作为 Source of Truth。

CandidateEvaluation 保留结构化 Trade-off：

```text
goal_supports[]
goal_conflicts[]
value_supports[]
value_conflicts[]
drive_supports[]
relationship_effects[]
self_implications[]
predicted_outcomes[]
risk
uncertainty
feasibility
reversibility
urgency
emotional_bias
```

内部可以使用数值，但不能把全部意义压成一个总分。

---

### 14D.10 Fast / Deliberative Path

官方 v0.1 支持：

```text
Fast Path
Deliberative Path
```

低风险、熟悉、重复行为可使用 Habit / Procedure。

高风险、高冲突、高不确定、低可逆决策进入 Deliberative Path。

不新增独立 System 1 / System 2 State。

---

### 14D.11 Satisficing

Selection 不要求找到全局最优。

正式允许：

> **找到一个足够可接受的方案后停止继续搜索。**

即 Satisficing。

---

### 14D.12 Hard Constraint / Soft Preference

正式区分：

```text
Hard Constraint
Soft Preference
```

Body 不可行动、Action Protocol 禁止等可以是 Hard Constraint。

Value 默认是 strong preference / constraint，而不是永远无法违反的硬规则。

这样才能允许：

```text
Value-Behavior Conflict
```

---

### 14D.13 Subjective Irrationality

允许：

```text
avoidance
irrational persistence
attachment-driven choice
fear-driven delay
emotion-biased decision
```

但必须有可追踪原因。

Randomness 不能替代因果解释。

---

### 14D.14 Randomness

随机性：

```text
small
bounded
reproducible
```

只适合：

```text
tie-breaking
low-stakes variation
exploration
```

重大 Value Conflict 不允许用随机数代替 Decision。

---

### 14D.15 Decision Output

DecisionResult 是结构化 Cognitive Artifact。

概念上：

```text
decision_id
frame_ref
selected_candidate_ref
selected_intent
rejected_candidate_refs
major_tradeoffs
uncertainty
confidence
defer / no-action reason
source_refs
trace metadata
```

---

### 14D.16 Action Intent Boundary

真正交给 Environment 的是：

```text
ActionIntent
```

Environment 不读取 Agent 的整个内部 Decision Context。

正式坚持：

```text
Intent ≠ Result
```

Agent 决定意图，Environment 决定世界结果。

---

### 14D.17 Communicative / Cognitive Intent

Decision 可以产生：

```text
External Action Intent
Communicative Intent
Cognitive Intent
```

Cognitive Intent 例如：

```text
Deliberate Retrieval
Reflection Request
Context Expansion
Planning Request
```

不新增长期 Core State。

---

### 14D.18 Planning

不是所有 Decision 都需要 Planning。

复杂、多步、长期行为才需要。

Planning 把：

```text
“我要做什么”
```

变成：

```text
“准备按什么步骤做”
```

---

### 14D.19 Goal Decomposition ≠ Plan

Subgoal 是未来目标状态。

Plan Step 是实现 Goal 的行动策略。

Plan Step 不自动成为 Goal。

---

### 14D.20 Plan Artifact

Plan 不新增 Core State。

重要 Plan 可以作为：

```text
Cognitive Artifact
Decision Artifact
Trace Artifact
```

保存。

Plan 可以失败、替换和 Replan，而 Goal 保持不变。

---

### 14D.21 Planning Boundary

Planning 必须使用：

```text
Agent World Model
Agent Knowledge
Known Resources
Body Capability
Environment Action Contract
```

而不是 Objective World 上帝视角。

---

### 14D.22 Planning Validation

LLM Plan Proposal 必须经过：

```text
PlanValidation
```

检查：

```text
capability
resource
body feasibility
known environment constraint
goal consistency
knowledge boundary
dependency validity
action type validity
```

---

### 14D.23 Replanning

Plan Step 失败不等于 Goal 失败。

允许：

```text
Action / Plan Step Failed
↓
Replan
↓
Goal remains ACTIVE
```

Replanning 必须 bounded。

---

### 14D.24 LLM Boundary

LLM 适合：

```text
decision framing assistance
candidate generation
trade-off interpretation
complex social reasoning
planning
replanning proposal
```

但：

```text
simple / routine / structured
→ deterministic / policy

complex / social / ambiguous
→ LLM-assisted
```

最终 Intent 仍需 Policy / Validation。

---

### 14D.25 Decision Confidence

Decision Confidence 表示 Agent 对自己的选择有多确定。

它不等于 Objective Correctness。

Agent 可以高置信度做出客观上糟糕的选择。

---

### 14D.26 Decision Commit / External Commit

正式区分：

```text
Decision Selected
↓
Action Intent Created
↓
Environment Accepts / Executes
```

内部 Runtime rollback 不等于回滚已经发生的外部行为。

---

### 14D.27 No Direct State Mutation

Decision 不直接修改：

```text
Belief
Relationship
Narrative
Drive
Value
Goal outcome
```

真正的 Action Result 经后续 Process 才能形成这些 State 的变化。

---

### 14D.28 Actor-controlled Action

Action Intent 必须描述：

> **Actor 自己能尝试执行的行为。**

不允许：

```text
make B trust me
make B forgive me
make B happy
```

这种直接控制别人内部状态的 Action。

合法形式是：

```text
tell B the truth
apologize to B
ask B to talk
offer help
```

接收者效果由接收者自己的 Perception / Appraisal / Decision 决定。

---

### 14D.29 Trace

Decision Trace 与 Narrative Explanation 分离。

低重要度 Decision 可以简化记录。

重要 Decision 应记录：

```text
Decision Frame
Candidates
Validation
Trade-offs
Predicted Outcomes
Selection
Plan
```

从而回答：

> **“为什么这个 Agent 当时这样选？”**

---

### 14D.30 Decision / Planning v0.1 最终原则

正式接受：

1. Decision / Planning 是 Process，不新增 Core State。
2. Drive = Why，Goal = What，Decision = 当前方向，Plan = How，Action = Do。
3. Decision 与 Planning 分离。
4. Action Intent 与 Action Result 分离。
5. AnimaFlux 采用 Bounded Rationality。
6. Agent 不做全知无限搜索。
7. Decision 只使用有限 Candidate / Context / Budget。
8. 支持 WAIT / DEFER / CONTINUE / NO_ACTION。
9. Goal Review 固定发生在 Decision 前。
10. DecisionContext 只使用筛选后的 Views。
11. Decision 不直接访问底层 Store。
12. Decision 默认分 Framing / Candidate Generation / Evaluation / Selection。
13. 低意义事件无需深度 Decision。
14. Candidate Generation 有 Budget。
15. 候选可来自 Habit / Procedure / Existing Plan / Environment / World Model / LLM。
16. Candidate 必须 Validation。
17. Subjective Feasibility 与 Objective Executability 分离。
18. Candidate Evaluation 使用结构化 Trade-off。
19. Universal Utility Score 不是唯一 Source of Truth。
20. Reversibility / Risk / Uncertainty 影响 Decision Depth。
21. 支持 Fast / Deliberative Path。
22. Habit 是候选，不是不可中断脚本。
23. 支持 Satisficing。
24. Hard Constraint 与 Soft Preference 分离。
25. Value 默认不是绝对不可违反规则。
26. 允许 Value-Behavior Conflict。
27. 允许有因果的主观“不理性”。
28. Randomness 小幅、bounded、可复现。
29. Randomness 不替代重大 Decision 因果。
30. DecisionResult 是 Cognitive Artifact。
31. Environment 只接收 ActionIntent。
32. Intent ≠ Result。
33. Decision 可产生 Communicative / Cognitive / External Intent。
34. Planning 仅在需要时运行。
35. Goal Decomposition 与 Plan Step 分离。
36. Plan 不新增 Core State。
37. 重要 Plan 可作为 Artifact 持久化。
38. Plan Failure ≠ Goal Failure。
39. Replanning 必须 bounded。
40. Planning 只使用 Agent-accessible Knowledge / World Model。
41. LLM Plan 必须经过 Validation。
42. LLM 不能凭空增加能力 / 人物 / 资源。
43. 简单 Decision 优先 deterministic / policy。
44. 复杂 Decision 可以 LLM-assisted。
45. 最终 Intent 仍需 Policy / Validation。
46. Decision Confidence ≠ Objective Correctness。
47. Decision Commit 与 Environment Commit 分离。
48. 内部 rollback 不回滚已发生外部世界。
49. Decision 不直接修改其他 Core State。
50. Action Result 经后续 Process 才形成状态变化。
51. Action Intent 必须是 Actor 自己可执行 / 可尝试的行为。
52. 不允许 Action 直接指定他人内部心理结果。
53. Communication 只能表达尝试安慰 / 说服 / 道歉，而不能指定接收者效果。
54. Decision Trace 与 Narrative Explanation 分离。
55. 重要 Decision / Planning 进入 Causal Trace。

状态：

```text
Architecture Decision:
Decision / Planning v0.1

Status:
Accepted
```

---

## Architecture Decision #14E：Communication【已敲定】

### 核心定义

Communication 是 Cognitive / Action Process，不新增 Core State。

正式链路：

```text
Decision
↓
Communicative Intent
↓
Language Realization
↓
Communication Validation
↓
Communicative Action Intent
↓
Environment Adapter
↓
External Communication Event
↓
Recipient-visible Observation
↓
Receiver Perception / Appraisal / Belief / Relationship / Emotion
```

---

### 14E.1 Communicative Intent ≠ Utterance

正式区分：

```text
Communicative Intent
= 我想表达什么

Utterance
= 我具体怎么说出来
```

Decision 决定：

```text
要不要说
说什么
对谁说
透露多少
是否澄清 / 隐瞒 / 拒绝
```

Communication 负责把已经确定的 Intent 转换成可执行表达。

---

### 14E.2 CommunicativeIntent

概念上可以包含：

```text
actor_ref
target_refs
speech_act
communicative_goal
content_intents[]
disclosure_policy
epistemic_stance
style_constraints
relationship_context_ref
channel_preference
urgency
source_refs
decision_ref
```

---

### 14E.3 Speech Act

官方默认 Communication Plugin 可以提供：

```text
INFORM
ASK
ANSWER
REQUEST
ACCEPT
REFUSE
APOLOGIZE
THANK
COMFORT
WARN
PERSUADE
PROMISE
CLARIFY
CONFRONT
GREET
END_CONVERSATION
```

等常见 Speech Act。

Core 不永久绑定唯一枚举。

---

### 14E.4 Knowledge / Disclosure / Choice

正式区分：

```text
Knowledge Availability
≠
Disclosure Permission
≠
Communication Choice
```

Agent 知道某件事，不代表愿意告诉当前对象。

Disclosure 可以受：

```text
Relationship
Value
Goal
Promise / obligation
Risk
Social Norm
```

影响。

---

### 14E.5 Disclosure Policy

单次 Communication Intent 可以表达：

```text
fully disclose
partially disclose
be vague
withhold
redirect
```

等表达约束。

Communication 不应把 Agent 当前 Belief / Memory 全部透明输出。

---

### 14E.6 Concealment vs Deception

正式区分：

```text
Concealment
= 知道但选择不说

Deception
= 故意让对方形成与自己当前 Belief 不一致的判断
```

Deception 不等于客观上说错话。

它是相对于 Agent 自己 Epistemic State 的 Intentional Mismatch。

---

### 14E.7 LLM 没有自主撒谎权限

如果 Decision 只要求：

```text
withhold
```

Language Realization LLM 不得擅自升级成：

```text
deception
```

撒谎必须来自明确 Communicative Intent。

---

### 14E.8 Knowledge Grounding

Communication Claim 应尽量保留：

```text
claim refs
epistemic status
source refs
confidence
```

可区分：

```text
directly observed
remembered
believed
inferred
speculative
intentionally deceptive
```

具体枚举实现阶段再收敛。

---

### 14E.9 Claim Type

Communication Validation 需要区分：

```text
factual claim
epistemic claim
self-report
preference / value expression
intention
commitment
social act
```

不是所有语言内容都用 Belief Store 判断真假。

---

### 14E.10 Expression Style

Personality / Emotion / Relationship / Role / Social Norm 可以影响：

```text
directness
warmth
verbosity
assertiveness
formality
hedging
emotional expression
```

这些只形成 Style Bias。

不得改变已经确定的 Communicative Intent。

---

### 14E.11 ConversationContext

Communication 使用临时：

```text
ConversationContext
```

例如：

```text
conversation_ref
participants
channel
recent_turn_refs
active_topics
pending_questions
recent commitments
turn owner
```

ConversationContext 属于 Runtime Interaction Context，不新增 Core State。

---

### 14E.12 Conversation Context vs Memory

正式区分：

```text
ConversationContext
= 当前交流工作区

Memory
= 长期主观记忆
```

会话结束后，普通上下文可以消退。

长期重要交流通过正常 Life Loop 进入：

```text
Memory
Belief
Relationship
Goal
```

Communication 不维护另一套永久 Chat History Source of Truth。

---

### 14E.13 Communication Validation

Draft Utterance 在发送前必须经过 Validation。

至少检查：

```text
Intent Fidelity
Knowledge Grounding
Disclosure Compliance
Target / Channel Validity
Action Protocol Validity
```

---

### 14E.14 Intent Fidelity

最终语言不能把 Intent 说歪。

例如：

```text
Intent:
polite refusal + preserve relationship
```

不能输出明显攻击性表达。

---

### 14E.15 Knowledge Grounding

Language Realization 不得扩大 Agent Knowledge。

LLM 不能添加没有：

```text
Belief ref
Memory ref
Observation ref
authorized speculation
```

支持的新事实。

---

### 14E.16 Disclosure Compliance

最终表达必须遵守：

```text
allowed claims
forbidden claims
sensitive refs
```

不能在生成阶段无意泄露被 Intent 明确隐藏的信息。

---

### 14E.17 Target / Channel / Protocol

Recipient、Channel、Visibility、Environment Action Contract 必须校验。

LLM 不能生成当前 Environment 不支持的交流能力。

---

### 14E.18 Bounded Repair

Validation 失败后允许：

```text
bounded repair
```

但不能无限：

```text
generate
→ validate
→ rewrite
→ ...
```

失败时：

```text
minimal conservative utterance
defer
NO_UTTERANCE
```

都优于 hallucination / disclosure violation。

---

### 14E.19 Sender Cannot Control Receiver

Sender 只能决定：

```text
attempt to comfort
attempt to persuade
apologize
warn
request
```

不能决定：

```text
receiver becomes happy
receiver trusts me
receiver forgives me
receiver is persuaded
```

接收效果由 Receiver 自己的：

```text
Perception
Memory Retrieval
Appraisal
Belief
Relationship
Emotion
Decision
```

决定。

---

### 14E.20 Promise / Request / Agreement

Promise / Request / Agreement 等 Speech Act 可以形成：

```text
Goal Proposal
Social Obligation Evidence
Belief Evidence
Relationship Evidence
Memory
```

但 Communication 不直接修改这些 State。

---

### 14E.21 Information-seeking Communication

Communication 不只是输出信息。

正式支持：

```text
ASK
CLARIFY
VERIFY
```

等主动获取 Evidence 的社会行为。

Agent 可以通过交流减少自己的不确定性。

---

### 14E.22 Multi-Agent Boundary

多 Agent Communication 必须经过：

```text
Agent A
↓
Communicative Action Intent
↓
Environment
↓
Recipient-visible Observation
↓
Agent B Perception
```

不允许 Agent 直接读取 / 写入彼此内部 State。

---

### 14E.23 Channel Abstraction

Private / Public / Text / Speech / Persistent / Ephemeral 等通过统一：

```text
Channel Metadata
```

表达。

不为微信、电话、论坛、游戏聊天等分别构建心智架构。

---

### 14E.24 Human Interaction

Human ↔ Agent 统一使用：

```text
HumanInteractionAdapter
↓
Communication Observation
↓
Perception / Cognition
↓
Communicative Action
```

用户不是直接访问底层 LLM 的特殊入口。

---

### 14E.25 Operator Control Plane

正式区分：

```text
Operator Control Plane
≠
In-world Communication
```

暂停模拟、保存 Checkpoint、切换 Profile 等 Runtime 指令不能伪装成角色世界中的对话。

---

### 14E.26 Minimal Communication Context

Language Realization 只读取最小授权 Context，例如：

```text
Communicative Intent
Allowed Content Claims
Emotion Expression View
Personality Style View
Target Relationship Summary
Role / Social Context
Recent Conversation Context
Language Constraints
```

禁止读取完整 Memory / Belief / Narrative / Relationship Store。

---

### 14E.27 Internal State ≠ Full Verbal Disclosure

Agent 不需要把完整内心透明表达出来。

允许：

```text
silence
vagueness
partial disclosure
emotional masking
“I don't know how to say it”
```

等行为。

---

### 14E.28 Failure Types

正式区分：

```text
Language Realization Failure
≠
Environment Delivery Failure
```

LLM Failure 可以 bounded retry / template fallback / minimal utterance / defer。

Environment Delivery Failure 由外部世界返回 Action Result，并由 Agent 是否可见决定是否进入 Perception。

---

### 14E.29 CommunicativeActionIntent

Communication 的标准输出为：

```text
CommunicativeActionIntent
```

概念上包含：

```text
actor_ref
target_refs
channel
speech_act
utterance
claim_refs
communicative_goal_refs
disclosure_metadata
decision_ref
intent_ref
trace_ref
```

然后交给 Environment Adapter。

---

### 14E.30 Trace

重要 Communication 应能追踪：

```text
Decision
→ CommunicativeIntent
→ Allowed Claims / Disclosure
→ Draft
→ Validation
→ Final Utterance
→ Environment Result
```

普通中间 Draft 只在 Debug / Research 配置下保存。

Life 视角不暴露内部 Intent Fidelity / Validation Score。

---

### 14E.31 Communication v0.1 最终原则

正式接受：

1. Communication 是 Process，不新增 Core State。
2. Incoming Communication 走 Perception。
3. Outgoing Communication 从 Decision 的 CommunicativeIntent 开始。
4. CommunicativeIntent 与 Utterance 分离。
5. Decision 决定是否说 / 说什么 / 透露多少。
6. LLM 主要负责具体语言表达。
7. Speech Act 使用可扩展 Vocabulary。
8. Knowledge Availability ≠ Disclosure Permission ≠ Communication Choice。
9. 支持 Full / Partial / Vague / Withhold / Redirect 等 Disclosure。
10. Concealment 与 Deception 分离。
11. Deception 基于 Agent 自己的 Belief，而非 Objective Truth。
12. LLM 没有自主撒谎权限。
13. Communication Claim 应保留 Epistemic Grounding。
14. 不同 Claim Type 使用不同验证规则。
15. Personality / Emotion / Relationship / Role / Norm 只形成 Style Bias。
16. Style Bias 不能改变 Intent。
17. ConversationContext 是临时 Runtime Context。
18. ConversationContext 不新增 Core State。
19. 长期重要交流仍进入 Memory / Belief / Relationship / Goal。
20. Communication 不维护永久 Chat History Source of Truth。
21. Draft 必须经过 Intent Fidelity / Knowledge / Disclosure / Target / Protocol Validation。
22. Language Realization 不得扩大 Agent Knowledge。
23. Disclosure Compliance 必须可验证。
24. Validation Repair 必须 bounded。
25. 保守表达 / 沉默优于 hallucination。
26. Sender 不能直接控制 Receiver 的心理结果。
27. Promise / Request / Agreement 只形成 Evidence / Proposal，不直接写 State。
28. 支持 ASK / CLARIFY / VERIFY 等主动获取信息行为。
29. Multi-Agent Communication 必须经过 Environment。
30. Agent 之间不得互读私有 State。
31. Channel 使用统一抽象。
32. Human ↔ Agent 也走统一 Interaction Boundary。
33. Operator Control Plane 与 In-world Communication 分离。
34. Language Realization 使用最小授权 Context。
35. Internal State 不等于 Full Verbal Disclosure。
36. 允许沉默 / 模糊 / 隐瞒 / 不知道怎么说。
37. Language Failure 与 Delivery Failure 分离。
38. LLM Failure 可 bounded retry / fallback。
39. CommunicativeActionIntent 是 Environment 标准输出。
40. Communication Validator 检查契约，不做文学评分。
41. Communication 不负责事后人生反思。
42. 重要 Communication Intent / Grounding / Validation / Final Action 进入 Causal Trace。

状态：

```text
Architecture Decision:
Communication v0.1

Status:
Accepted
```

---

## Architecture Decision #14F：Reflection【已敲定】

### 核心定义

Reflection 是低频、长时间尺度、模式与意义导向的 Cognitive Process，不新增 Core State。

正式区分：

```text
Decision / Planning
= 现在该做什么、怎么做

Appraisal
= 当前事情对我意味着什么

Memory Retrieval
= 现在想起什么

Reflection
= 回头看一段经历，它们共同说明了什么

Narrative
= 长期反思后沉淀下来的人生解释
```

---

### 14F.1 Trigger / Scope

Reflection 不每 Tick 运行。

触发来源：

```text
Scheduler
Major Goal Outcome
Relationship Transition
Identity Transition
Major Body / Life Change
Repeated Value Conflict
Repeated Behavior Pattern
Major Belief Revision
Life-stage Transition
Decision CognitiveIntent
```

重大事件可以形成 Reflection Need，但不要求当场深度反思。

Reflection 必须先形成：

```text
ReflectionTrigger
ReflectionScope
```

控制主题、时间窗口和证据范围。

---

### 14F.2 Budgeted Context

Reflection 不允许读取完整人生 Store。

正式流程：

```text
Reflection Trigger
↓
Reflection Scope
↓
Deliberate Memory Retrieval
↓
Relevant State Views
↓
Counter-Evidence
↓
BudgetedReflectionContext
```

Reflection 只使用 Agent 自己可访问的信息。

---

### 14F.3 Pattern Detection

Reflection 的核心能力之一是识别：

```text
repeated behavior
repeated goal failure
relationship pattern
belief contradiction
value-behavior conflict
self-model inconsistency
long-term adaptation
```

PatternCandidate 不是 Personality Fact。

---

### 14F.4 Proposal / Evidence Only

Reflection 不直接修改：

```text
Belief
Value
Personality
Self Model
Relationship
Goal
Narrative
Memory
```

只产生：

```text
BeliefRevisionProposal
ValueDevelopmentEvidence
PersonalityDevelopmentEvidence
SelfModelEvidence / RevisionProposal
RelationshipEvidence
GoalReviewEvidence
NarrativeProposal / RevisionProposal
MemoryReconsolidationProposal
SemanticGeneralizationProposal
```

最终由对应 Owner 决定是否更新以及更新多少。

---

### 14F.5 Counter-Evidence

Reflection Context 必须允许：

```text
supporting evidence
contradicting evidence
exceptions
uncertainty
```

进入。

但 Counter-Evidence 不等于强制正面化。

Reflection 追求 Evidence Grounding，而不是 Positivity。

---

### 14F.6 Uncertainty

Reflection 可以合法输出：

```text
SUPPORTED
TENTATIVE
CONFLICTED
INSUFFICIENT_EVIDENCE
```

等语义。

正式原则：

> **没有明确结论也是合法 Reflection Result。**

---

### 14F.7 Reappraisal Boundary

```text
Reappraisal
= 对具体事件重新解释

Reflection
= 对长期经历 / 模式 / 人生阶段进行高层整合
```

Reflection 可以触发有限 Reappraisal。

不允许大规模、无界地重新评价历史全部事件。

---

### 14F.8 Memory Boundary

Reflection 可以请求：

```text
MemoryReconsolidationProposal
SemanticGeneralizationProposal
```

但不能直接改 Memory。

旧 Memory Version 必须保留。

重要 Reflection 本身可以通过 MemoryFormation 形成长期 Memory。

---

### 14F.9 Slow-State Development

Reflection 对慢状态只产生 Evidence / Proposal。

尤其：

```text
Personality
Value
Core Self Model
Narrative
```

必须遵守各自 Slow / Bounded Update 规则。

一次 Reflection 不得大幅任意重塑人格或价值。

---

### 14F.10 Narrative

Narrative 是 Reflection 最重要的长期沉淀目标之一。

Reflection 可以：

```text
discover life themes
identify turning points
revise causal interpretations
propose chapter transitions
```

但 NarrativeOwner 才能正式 Version / Commit。

---

### 14F.11 LLM Boundary

Reflection 是 v0.1 合理的核心 LLM 调用点之一。

LLM 适合：

```text
long-horizon synthesis
pattern discovery
contradiction analysis
alternative interpretation
counter-evidence comparison
self-model reasoning
narrative revision proposal
```

但必须：

```text
Evidence-grounded
source-ref aware
uncertainty aware
bounded
```

LLM 不得无来源构造心理故事或 Objective Facts。

---

### 14F.12 Bounded Reflection

不采用：

```text
reflect
→ critique
→ reflect again
→ critique again
→ ...
```

无限循环。

Reflection Round 必须有限。

Scheduler 管理 Reflection Frequency。

---

### 14F.13 ReflectionResult

ReflectionResult 是结构化 Cognitive Artifact，概念上包含：

```text
observations[]
pattern_candidates[]
contradictions[]
open_questions[]
revised_interpretations[]

belief_revision_proposals[]
self_model_evidence[]
value_development_evidence[]
personality_development_evidence[]
relationship_evidence[]
goal_review_evidence[]
narrative_proposals[]
memory_reconsolidation_proposals[]

confidence
source_refs
trace_metadata
```

自然语言 Reflection Summary 只是 Derived View。

---

### 14F.14 Validation

Reflection Proposal Validation 至少检查：

```text
source refs exist
no fabricated event
knowledge boundary
target valid
confidence / uncertainty present
unsupported certainty
no direct state mutation
```

不同 State Owner 自己决定所需 Evidence Threshold。

---

### 14F.15 Persistence / Replay / Failure

ReflectionResult 不新增长期 Core State。

重要 Reflection Artifact 可保存到：

```text
Trace Store
Artifact Store
```

Exact Replay 使用历史 ReflectionResult。

Resimulation 可以重新运行 Reflection。

普通 Reflection Failure 不应使 Life Runtime 崩溃。

---

### 14F.16 Reflection v0.1 最终原则

正式接受：

1. Reflection 是 Process，不新增 Core State。
2. Reflection 是低频、长时间尺度、模式与意义导向过程。
3. Reflection 与 Decision / Appraisal / Retrieval / Narrative 分离。
4. Narrative 是 State，Reflection 是其主要形成 / 修订 Process。
5. Reflection 不每 Tick 运行。
6. Scheduler / Major Event / CognitiveIntent 可以触发 Reflection。
7. Reflection 使用 Trigger + Scope。
8. Reflection 不加载完整人生 Store。
9. 使用 Deliberate Retrieval + Relevant Views 构造 Budgeted Context。
10. Pattern Detection 是核心能力之一。
11. PatternCandidate 不等于 Personality Fact。
12. Reflection 对所有其他 State 只产生 Proposal / Evidence。
13. Reflection 不直接修改任何 Core State。
14. Counter-Evidence 必须可以进入 Context。
15. Counter-Evidence 不等于强制正面化。
16. Reflection 追求 Evidence Grounding，不追求 Positivity。
17. 允许多种解释并存。
18. 允许 Uncertainty / Open Question / Insufficient Evidence。
19. Reappraisal 是局部；Reflection 是高层长期整合。
20. Reflection 可以触发有限 Reappraisal。
21. 不允许无界重评全部历史。
22. Reflection 可提出 MemoryReconsolidationProposal。
23. Reflection 不能直接修改 Memory。
24. 旧 Memory Version 保留。
25. Reflection 可以提出 SemanticGeneralizationProposal。
26. Personality / Value / Core Self / Narrative 更新必须 bounded。
27. Personality 需要长期证据积累。
28. Value 主要依赖长期或重大 Evidence。
29. Self-Efficacy 可以比 Core Self Model 更快更新。
30. Narrative 可以重大 Revision，但保留历史 Version。
31. Reflection 是合理核心 LLM 调用点。
32. LLM 输出必须 Evidence-grounded。
33. LLM 不得无来源构造心理故事。
34. 重要结论必须 source refs + confidence / uncertainty。
35. Reflection Prompt 必须要求 Grounding。
36. Reflection Context 必须有严格 Budget。
37. Reflection Pipeline 可以多阶段，但必须 bounded。
38. 不采用开放式“反思直到满意”循环。
39. Reflection Frequency 由 Scheduler 管。
40. Decision 可以请求 Scope-limited Reflection。
41. Reflection 可以合法失败。
42. “没有足够证据”是合法结果。
43. Reflection 不创建 Objective Facts。
44. Reflection 可以为 Goal Generation 提供 Context，但不直接激活 Goal。
45. Reflection 的目标是形成新的理解，而不是保证优化 / 进步。
46. AnimaFlux 不把 Reflection 设计成自动心理治疗器。
47. Personality / Emotion 只形成 Reflection Bias / Style。
48. Core 不写死唯一 Reflection 心理模型。
49. 官方 v0.1 可以提供 DefaultReflectionProcess。
50. Reflection Proposal 必须经过 Validation。
51. 各 State Owner 决定自己的 Evidence Threshold。
52. ReflectionResult 是 Cognitive Artifact，不是 Core State。
53. 重要 Reflection 可进入 Trace / Artifact Store。
54. Exact Replay 复用历史 Reflection Result。
55. Resimulation 可重新 Reflection。
56. 普通 Reflection Failure 不应导致 Runtime 崩溃。
57. 重要 Reflection 与后续 Slow-State Change 进入 Causal Trace。

状态：

```text
Architecture Decision:
Reflection v0.1

Status:
Accepted
```

---

# Stage E：Core Cognitive Processes【完成】

```text
#14A Perception         ✅
#14B Appraisal          ✅
#14C Memory Retrieval   ✅
#14D Decision / Planning✅
#14E Communication      ✅
#14F Reflection         ✅
```

---

# Stage F：Integration / Wiring

## Architecture Decision #15A：Core Dependency Map【已敲定】

### 核心定义

跨模块正式只允许以下显式连接：

```text
Capability Read
Process Input
Influence
Event
Proposal / Evidence
```

总规则：

> **读取别人用 Capability；影响别人用 Influence；长期修订别人用 Proposal / Evidence；客观事实用 Event；最终 State 修改只能由对应 State Owner 完成。**

### 15A.1 Read / Change / Commit 三平面

```text
READ PLANE
Capability / View / Process Input

CHANGE PLANE
Influence / Evidence / Proposal / Event

COMMIT PLANE
State Resolver
→ State Owner
→ State Store
```

### 15A.2 Capability Read

Capability 用于跨模块只读访问，返回 Immutable View / DTO，不暴露可变内部 State。

State Owner 读取其他 State 也必须通过公开 Capability。

### 15A.3 Process Input

Process 运行所需上下文应由 Runtime Context 组装，例如：

```text
PerceivedEvent
RetrievedMemorySet
AppraisalResult
DecisionResult
ReflectionResult
```

这些属于 Cognitive Artifact，不是长期 State。

### 15A.4 Influence

Influence 表示跨 State 的当前动态影响。目标 State Owner 解释 Influence，并决定最终 Next State。

### 15A.5 Proposal / Evidence

Proposal / Evidence 用于长期发展、Revision 和 Reflection 结果，例如：

```text
PersonalityDevelopmentEvidence
ValueDevelopmentEvidence
BeliefRevisionProposal
SelfModelRevisionProposal
NarrativeRevisionProposal
```

它们不直接修改 State。

### 15A.6 Event

Event 表示已经确认发生的 Objective Runtime / External Fact。

正式坚持：

```text
Event ≠ Influence
Event ≠ State
```

发生了什么，不等于 State 应该怎么变化。

### 15A.7 Write Authority

每个 State 只能由自己的 Owner 写入：

```text
IdentityOwner → Identity
BodyOwner → Body
PersonalityOwner → Personality
EmotionOwner → Emotion
DriveOwner → Drive
MemoryOwner → Memory
BeliefOwner → Belief
ValueOwner → Value
GoalOwner → Goal
RelationshipOwner → Relationship
WorldModelOwner → World Model
SelfModelOwner → Self Model
NarrativeOwner → Narrative
```

Cognitive Process 默认不能直接写任何 Core State。

### 15A.8 Memory Boundary

普通 Cognitive Process 不直接读取 Memory Store，只能通过 Memory Retrieval Contract 获取 RetrievedMemorySet。

Read API 不允许隐藏 Accessibility Update 等副作用。

### 15A.9 Reflection / Decision / Perception Boundary

Reflection 可以广泛读取，但直接写入权限为 none，只输出 Proposal / Evidence。

Decision 可以广泛读取有限 View，但主要输出 DecisionResult / PlanArtifact / ActionIntent / CommunicativeIntent / CognitiveIntent。

Perception 权限保持最小，只处理 Observation、Body Sensory Capability、有限 Attention Bias View 和 recognition hints。

### 15A.10 Environment / Multi-Agent Boundary

统一：

```text
LIFE → WORLD
ActionIntent

WORLD → LIFE
Observation / External Event / Action Result
```

Environment 不直接修改主观 Core State。

Agent A 与 Agent B 的私有 StateStore 不直接连接；多 Agent 交互必须经过 Environment。

### 15A.11 Hidden Mutation Forbidden

所有副作用必须显式。禁止 Read API 内部偷偷修改 State。

例如 Memory Retrieval 后需要提高 Accessibility，应走：

```text
Retrieval
→ MemoryReactivationEvidence
→ MemoryOwner
```

### 15A.12 Plugin Decoupling

插件依赖：

```text
Capability Contract
Influence Contract
Process Contract
View DTO
```

而不是其他 Plugin 的内部 Schema。

### 15A.13 Feedback Loop / Snapshot Semantics

允许 Emotion ↔ Retrieval ↔ Appraisal 等反馈，但同一 Tick 内不得无界同步递归。

统一通过：

```text
Frozen Tick Snapshot
bounded retrieval
bounded reappraisal
bounded resolver rounds
Working State
Commit
```

控制。

### 15A.14 Forbidden Dependencies

正式禁止：

```text
cross-state direct mutation
cross-agent private-state reads
Cognitive Process direct Store mutation
Plugin direct DB connection
Plugin direct Runtime Transaction manipulation
Plugin direct Scheduler internals manipulation
Reflection reading Objective Event Log as Life knowledge
Communication LLM reading full Belief / Memory Store
Decision raw-querying Memory Store
```

### 15A.15 最终原则

正式接受：

1. 跨模块连接显式区分 Capability Read / Process Input / Influence / Event / Proposal-Evidence。
2. Read / Change / Commit 三平面分离。
3. 读取别人用 Capability。
4. 影响别人用 Influence。
5. 长期修订别人用 Proposal / Evidence。
6. 客观事实使用 Event。
7. 最终 State 修改只能由对应 Owner 完成。
8. Cognitive Process 默认不能直接写 Core State。
9. Capability 返回 Immutable View / DTO。
10. Owner 读取其他 State 也走 Capability。
11. Runtime 优先组装 Process Input。
12. Process 不自行遍历底层 Store。
13. Memory Store 只能经 Retrieval Contract 访问。
14. Reflection 广读但不直接写任何 State。
15. Decision 广读但主要输出 Intent / Artifact。
16. Perception 权限保持最小。
17. Communication 不直接修改 Receiver State。
18. Multi-Agent 交互必须经过 Environment。
19. Environment 不直接写主观 State。
20. 所有副作用必须显式。
21. 禁止 Read API 隐藏 Mutation。
22. Event 与 Influence 分离。
23. Influence 与 Proposal / Evidence 分离。
24. Cognitive Artifact 与 Core State 分离。
25. Feedback Loop 允许，但必须 bounded。
26. Tick 使用 Frozen Snapshot。
27. Working State 只在 Resolver / Owner 层形成。
28. Commit 后才成为下一版 State。
29. Plugin 依赖能力，不依赖实现。
30. 重要跨模块因果边进入 Causal Trace。

状态：

```text
Architecture Decision:
Core Dependency Map v0.1

Status:
Accepted
```

---

## Architecture Decision #15B：Default Life Loop Wiring【已敲定】

### 核心定义

AnimaFlux v0.1 保持原 12-step Life Loop，不再扩展主阶段数量：

```text
0  Tick Preparation
1  Environment / External Input Preparation
2  Body & Lifecycle Update
3  Event Collection
4  Perception
5  Memory Retrieval & Context Activation
6  Appraisal
7  Internal Dynamics
8  Goal Review & Decision
9  Action Intent / Output
10 Consequence Ingestion & Memory Formation
11 Reflection & Slow-State Update
12 Commit & Advance Time
```

---

### 15B.1 Snapshot + Working View

Tick 开始：

```text
Committed State(t)
↓
TickSnapshotView
```

Tick 内部允许通过 Resolution Barrier 形成：

```text
ResolvedWorkingView
```

供后续阶段读取。

但：

```text
ResolvedWorkingView ≠ Commit
```

Critical Failure 时整个 Tick 仍可 Rollback。

---

### 15B.2 Resolution Barriers

v0.1 默认使用少量主要 Barrier：

```text
R0  Lifecycle Barrier
R1  Internal Dynamics Barrier
R2  Goal Barrier
R3  Consequence / Slow-State Barrier
```

不在每个 Process 后都立即 Resolve。

---

### 15B.3 R0：Lifecycle Barrier

Step 2 处理：

```text
Body Update
Identity Transition when evidence exists
Lifecycle processes
```

R0 后：

```text
Perception
```

可以读取当前 Tick 最新的 Body / Sensory Capability。

R0 仍不是持久化 Commit。

---

### 15B.4 Environment Input / Input Journal

Step 1 将：

```text
External Event
Observation
Communication
previous Action Result
Environment Context Update
```

统一归一化为：

```text
EnvironmentInputBatch
```

不可确定外部输入必须进入：

```text
Input Journal
```

Exact Replay 使用历史 Input Journal，而不是重新访问外部世界。

---

### 15B.5 Objective Event vs Observation

Step 3 收集 Objective Runtime / External Events。

正式区分：

```text
Objective Event
≠
Agent-visible Observation
```

Life Cognition 从 Observation 开始，而不是直接读取 Objective Event Log。

---

### 15B.6 Perception

Step 4 调用：

```text
Sensory Gate
Attention Selection
Perceptual Interpretation
```

输出：

```text
PerceivedEventSet
```

PerceivedEvent 是 Cognitive Artifact，不需要 Resolver。

复杂自然语言 / 社会语义可选 LLM；结构化 Observation 优先 deterministic。

---

### 15B.7 Memory Retrieval / Context Activation

Step 5：

```text
PerceivedEvent
↓
Memory Retrieval
↓
RetrievedMemorySet
↓
Relevant State Views
↓
CognitiveContext
```

Context Activation 的目标是：

> **只激活当前需要的一小部分“心智内容”，而不是加载完整 Agent。**

Memory Reactivation 只形成 Evidence，不直接修改 Memory。

---

### 15B.8 Appraisal

Step 6 使用：

```text
PerceivedEvent
RetrievedMemorySet
Relevant Beliefs
Goals
Values
Relationship
Self
Personality Bias
Body
World Model
Narrative
Prior Affect
```

生成：

```text
AppraisalResult
```

Appraisal 不直接写 State。

---

### 15B.9 Context Expansion

高 significance / high uncertainty / insufficient context 时允许：

```text
Context Expansion Retrieval
↓
Bounded Reappraisal
```

默认只允许极少轮次。

禁止：

```text
Retrieval ↔ Appraisal
```

无限循环。

---

### 15B.10 Internal Dynamics

Step 7 将 AppraisalResult 转换为不同 State 的：

```text
Influence
Evidence
Proposal
```

例如：

```text
Emotion Influence
Drive Influence
Belief Evidence
Relationship Evidence
World Model Integration
Memory Reactivation Evidence
```

Process 不直接写 State。

---

### 15B.11 R1：Internal Dynamics Barrier

Step 7 完成后：

```text
State Resolver
→ corresponding Owners
→ ResolvedWorkingView-R1
```

Decision 后续可以读取当前 Tick 最新的：

```text
Emotion
Drive
Belief
Relationship
World Model
```

---

### 15B.12 Goal Review

Step 8A 在 Decision 前运行 Goal Review。

可以产生：

```text
Goal Activation Evidence
Goal Pause Proposal
Goal Progress Evidence
Goal Closure Evidence
Goal Conflict Context
Goal Generation Proposal
```

GoalOwner 决定最终 Goal State。

Decision 不偷偷创建 Goal。

---

### 15B.13 R2：Goal Barrier

Goal Review 完成后：

```text
GoalOwner
↓
ResolvedWorkingView-R2
```

Decision 使用 Review 完成后的 Goal Context。

正式坚持：

```text
Goal Review before Decision
```

---

### 15B.14 Decision / Planning

Step 8B 运行：

```text
Decision Framing
Candidate Generation
Candidate Validation
Candidate Evaluation
Selection
Planning if needed
```

合法结果包括：

```text
WAIT
DEFER
NO_ACTION
CognitiveIntent
CommunicativeIntent
ExternalActionIntent
```

Planning 只在复杂行为需要时运行。

---

### 15B.15 Communication

只有 Decision 已经形成：

```text
CommunicativeIntent
```

时才调用 Communication。

用户消息不会直接：

```text
prompt → language LLM
```

而必须经过：

```text
Perception
→ Memory Retrieval
→ Appraisal
→ Internal Dynamics
→ Goal Review
→ Decision
→ Communication
```

---

### 15B.16 External Action Boundary

Step 9 将：

```text
ActionIntent
```

交给 Environment Adapter。

External Action 是外部副作用边界。

内部 Tick Transaction Rollback 不代表现实 / 外部世界可以 Rollback。

---

### 15B.17 External Action Retry

Action 必须使用稳定的：

```text
action_id
correlation_id
attempt_id
```

技术性 Tick Retry 不应重复已经成功执行的外部动作。

如环境支持，应使用 idempotency。

---

### 15B.18 Consequence Ingestion

Step 10 接收：

```text
ActionResult
External Events
Actor-visible Observation
Recipient-visible Observation
```

正式坚持：

```text
ActionResult ≠ Agent-visible Observation
```

是否可见由 Environment Adapter 决定。

---

### 15B.19 Immediate Consequence Pass

v0.1 支持一次 Controlled Immediate Consequence Pass：

```text
Action Result
↓
Visible Observation
↓
Limited Perception
↓
Minimal Retrieval
↓
Appraisal
↓
Immediate State Evidence
```

但它不是第二次完整 Life Loop。

不允许再次无限 Decision / External Action。

原则上一个 Tick 只有一个主要 External Action Batch。

---

### 15B.20 Memory Formation

Memory Formation 位于 Consequence 之后。

综合：

```text
Perception
Appraisal
Emotion
Goal relevance
Relationship significance
Action / Result
```

产生：

```text
Memory Formation Proposal
```

由 MemoryOwner 最终写入。

---

### 15B.21 Reflection / Slow State

Step 11 由 Scheduler / Trigger 决定是否执行。

大部分 Tick 可以跳过。

Reflection 读取经过 Resolution 的 Working Context，不读取半成品 Change Buffer。

Reflection 输出 Slow-State Proposal / Evidence。

---

### 15B.22 R3：Final Resolution Barrier

Step 10 + Step 11 的：

```text
Body Consequence
Emotion Influence
Belief Evidence
Relationship Evidence
Goal Progress
Memory Formation
Personality Evidence
Value Evidence
Self Model Proposal
Narrative Proposal
Memory Reconsolidation Proposal
```

统一进入 State Resolver。

形成：

```text
Final Working State
```

---

### 15B.23 Final Validation / Commit

R3 后执行：

```text
State schema validation
owner invariants
cross-reference validation
version consistency
critical artifact validation
scheduler state validation
deferred influence validation
```

全部通过后才进入 Step 12 Commit。

---

### 15B.24 Commit

Step 12 是 Tick 唯一正式发布新 Committed State 的地方。

Critical writes 包括：

```text
State Versions
Memory source-of-truth changes
Durable Events
Scheduler state
Deferred Influences
Commit Journal
Required causal refs
```

Current State Pointer 尽量在事务后段发布。

---

### 15B.25 Advance Time

正式顺序：

```text
Commit
↓
Advance Runtime Time
```

Commit 失败时不能提前推进 Runtime Time。

---

### 15B.26 Post-Commit

以下通常属于非关键 Post-Commit：

```text
Vector Index Update
Cache Refresh
Metrics
Engineering Trace Enrichment
Artifact Finalization
Observability Export
```

它们失败不能使已成功 Commit 的生命状态消失。

---

### 15B.27 LLM Boundary in Life Loop

LLM 主要可出现在：

```text
Perception semantic interpretation
Memory query reformulation / small rerank
Complex Appraisal
Complex Goal proposal/decomposition
Decision / Planning
Communication language realization
Memory semantic compression/generalization
Reflection
```

以下绝不能依赖 LLM 保证正确性：

```text
Runtime Time
State Ownership
Permission
Transaction
Commit
Replay correctness
Schema validation
State invariant
```

正式原则：

> **LLM 负责理解、提出、表达、反思；代码负责时钟、状态、规则、权限、事务和提交。**

---

### 15B.28 Ordering / Parallelism

同批 Observation 使用 stable ordering。

可以 Parallel Compute，但：

```text
Influence collection
Resolution
Commit
```

必须 deterministic ordering。

---

### 15B.29 Error Handling

非关键 LLM Process Failure：

```text
degrade / fallback / skip
```

Core Owner fatal error、State invariant violation、Persistence failure 等 Critical Error：

```text
Abort Tick
Rollback
Pause Runtime if required
```

---

### 15B.30 Time Skip

Time Skip 使用：

```text
Δt
Scheduler catch-up policy
compressed lifecycle update
```

而不是运行大量空 Tick。

重大事件可促使后续 Tick 粒度变细。

---

### 15B.31 Death

Body.vital_status 是死亡权威。

死亡后停止普通 Goal Review / Decision Loop。

历史、Event、其他 Agent 的社会影响仍可继续存在。

---

### 15B.32 Default Life Loop Wiring v0.1 最终原则

正式接受：

1. 保持原 12-step Life Loop。
2. Tick 开始冻结 Committed State。
3. Tick 内使用少量 Resolution Barrier。
4. ResolvedWorkingView 不等于 Commit。
5. R0 位于 Body / Lifecycle 后。
6. R1 位于 Internal Dynamics 后。
7. R2 位于 Goal Review 后。
8. R3 位于 Consequence / Slow-State 后。
9. Environment Input 统一归一化。
10. 外部不可确定输入进入 Input Journal。
11. Objective Event 与 Observation 分离。
12. Agent Cognition 从 Observation 开始。
13. Perception Output 是 Artifact。
14. Context Activation 只加载有限相关内容。
15. Retrieval 副作用只形成 Evidence。
16. Appraisal 不直接写 State。
17. Context Expansion / Reappraisal bounded。
18. Internal Dynamics 只产生 Influence / Evidence。
19. R1 后 Decision 可见当前 Tick 的新 Emotion / Drive / Belief / Relationship。
20. Goal Review 在 Decision 前。
21. Goal Generation 不由 Decision 偷偷完成。
22. R2 后才运行 Decision。
23. Planning 只在需要时运行。
24. Communication 只处理已存在的 CommunicativeIntent。
25. 用户输入必须经过完整 Cognition。
26. Action Dispatch 是 External Side-effect Boundary。
27. Internal Rollback 不等于 External Rollback。
28. External Action 使用 stable correlation / attempt identity。
29. Retry 不重复外部副作用。
30. ActionResult 与 Agent-visible Observation 分离。
31. 支持一次受控 Immediate Consequence Pass。
32. Immediate Pass 不是完整第二 Life Loop。
33. 一 Tick 原则上一个主要 External Action Batch。
34. Memory Formation 在 Consequence 后。
35. Reflection 低频、可跳过。
36. Reflection 读取 Resolved Working Context。
37. R3 形成 Final Working State。
38. R3 后必须 Final Validation。
39. Step 12 是唯一正式 Commit。
40. Commit 成功后才 Advance Time。
41. Vector / Cache / Metrics 等属于 Post-Commit 非关键工作。
42. LLM 不承担 Runtime 正确性。
43. 结构化机械计算优先 deterministic。
44. Observation / Process execution 使用 stable ordering。
45. 可 Parallel Compute，但 Resolution / Commit 有确定顺序。
46. 非关键 LLM Failure 优先 degrade。
47. Critical Owner / Persistence Failure 必须 Abort / Rollback / Pause。
48. Time Skip 用 Δt + catch-up。
49. Death 由 Body vital_status 权威决定。
50. 完整 Tick 因果链进入 Causal Trace。

状态：

```text
Architecture Decision:
Default Life Loop Wiring v0.1

Status:
Accepted
```

---

## Architecture Decision #15C：Official Plugin Set【已敲定】

### 核心原则

Plugin Architecture 与 Python Distribution 拆包是两回事。

AnimaFlux v0.1 采用：

> **架构上细粒度可替换，工程交付上粗粒度打包。**

不把每个类、每个小 Process 都拆成独立插件或独立 pip 包。

---

### 15C.1 Runtime Infrastructure

以下属于 Framework Host，不是普通 Life Plugin：

```text
Kernel
LifeLoopRunner
StateResolver
StateStore Coordinator
Scheduler
RandomService
Transaction Coordinator
PluginManager
CapabilityRegistry
FailureManager
Replay / Branch
Trace Coordinator
```

Kernel / Runtime 负责生命“怎么运行”，不负责具体心理语义。

---

### 15C.2 Runtime Providers

Persistence / Trace / Index 等属于 Runtime Provider，而不是 Life Model Plugin。

v0.1：

```text
SQLitePersistenceBackend
InMemoryPersistenceBackend
Simple / Local Vector Index
Null Vector Index
ConsoleTraceSink
SQLiteTraceSink
```

PostgreSQL / OpenTelemetry / external vector DB 作为未来扩展。

---

### 15C.3 Core State Owner Plugins

13 个 Core State 在逻辑上保持独立 Active Owner：

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

一个 Namespace 同时只能存在一个 Active Owner。

官方默认实现作为一个：

```text
Default Life Bundle
```

统一交付。

---

### 15C.4 Logical Plugin ≠ Separate Package

官方可以只有一个主 Python Distribution：

```text
animaflux
```

但内部注册多个逻辑 Plugin Component。

因此：

```text
13 logical owners
≠
13 repositories
≠
13 pip packages
```

正式采用：

> **粗粒度发行，细粒度运行时选择。**

---

### 15C.5 One Plugin May Own Multiple Namespaces

Protocol 层允许一个 Plugin 声明：

```text
owned_namespaces:
  - emotion
  - drive
```

但 Runtime 仍保证：

```text
one namespace
→ one active owner
```

官方默认实现保持单 Namespace Owner 边界清晰。

---

### 15C.6 State-specific Internal Processes

State Plugin 内部的小 Process 默认不再全部独立成 Plugin。

例如 Emotion Plugin 内部可以包含：

```text
EmotionGeneration
EmotionDecay
EmotionRegulation support
```

Goal Plugin 内部可以包含：

```text
GoalGeneration
GoalAdoption
GoalReview
GoalProgress
GoalClosure
```

Memory Plugin 内部可以包含：

```text
MemoryFormation
Reactivation
Reconsolidation
```

正式避免：

> **Every Class Is A Plugin**

---

### 15C.7 Core Cognitive Process Providers

6 个 Core Cognitive Process 逻辑上独立可替换：

```text
Perception
Memory Retrieval
Appraisal
Decision / Planning
Communication
Reflection
```

官方默认实现作为：

```text
Default Cognition Bundle
```

统一交付。

---

### 15C.8 State Owner vs Process Provider

State Owner：

```text
exactly one active owner
```

不允许运行中 silent fallback 到另一语义模型。

State Owner failure：

```text
Pause / Fail
```

而不是自动切换默认实现。

Process Provider：

```text
multiple installed
one configured primary by default
```

可以配置明确 fallback，因为它主要输出 Cognitive Artifact，而不拥有长期 State Schema。

---

### 15C.9 Memory / Vector Boundary

Memory Source of Truth 与 Vector Index 分离。

```text
Memory Store
= Source of Truth

Vector Index
= Derived Index / Auxiliary Provider
```

v0.1 不强依赖外部 Vector DB。

无 Embedding / Vector Index 时，Memory Retrieval 必须能退化为：

```text
metadata
keyword
recency
structured lookup
SQLite search
```

---

### 15C.10 Environment Adapter

Environment Adapter 是正式 Extension Point。

官方 v0.1 只需要：

```text
Null / Sandbox Environment Adapter
Human Interaction Adapter
```

Historical / Novel / Game / Benchmark Environment 仅保留 Protocol 与示例方向，不做完整官方 v0.1 实现。

继续坚持：

> **AnimaFlux models the life, not the universe.**

---

### 15C.11 LLM Provider

Cognitive Plugin 不直接依赖具体模型厂商 SDK。

统一通过：

```text
LLMCapability
```

访问模型。

具体 Provider 可以是：

```text
OpenAI-compatible
local model
other remote provider
Mock / Scripted provider
No-LLM provider
```

---

### 15C.12 Mock / No-LLM

官方测试必须支持：

```text
MockLLMProvider
ScriptedLLMProvider
```

用于：

```text
deterministic tests
CI
replay tests
failure injection
```

建议提供 No-LLM / deterministic fallback 模式用于测试、调试和基础模拟。

No-LLM 模式不承诺与真实 LLM 模式具有同等智能效果。

---

### 15C.13 Embedding Capability

Embedding 与 Chat / Reasoning LLM 分离：

```text
EmbeddingCapability
≠
LLMCapability
```

Embedding 默认是 Optional Capability。

Memory Retrieval 不应因为缺失 Embedding 而无法运行。

---

### 15C.14 Runtime-owned Time / Random / Scheduler

以下属于 Kernel / Runtime：

```text
Runtime Time
RandomService
Scheduler
```

普通 Plugin 不允许：

```text
自行使用 system clock 作为生命时钟
自行 import 全局 random 产生语义随机
自行创建定时线程绕过 Scheduler
```

---

### 15C.15 Auxiliary Providers

Trace / Metrics / Index 等可以是 Auxiliary Provider。

但正式坚持：

> **Observability must not change life semantics.**

---

### 15C.16 Five Provider Categories

Official Plugin Set 统一按五类理解：

```text
A. Runtime Infrastructure
B. Core State Owner Plugins
C. Cognitive Process Plugins
D. External Capability / Environment Providers
E. Auxiliary Providers
```

其中 A 类不是普通插件。

---

### 15C.17 Reference Profile

官方 Default / Normal Profile 应自动展开成完整 Reference Runtime。

用户配置粗粒度：

```text
life_model: default
cognition: default
persistence: sqlite
environment: human_interaction
```

Runtime Plan 再展开成细粒度 Owner / Provider Selection。

用户不需要手工启用十九个逻辑组件。

---

### 15C.18 Fine-grained Override

Research Profile 可以覆盖局部实现，例如：

```text
Emotion Owner
Appraisal Provider
Decision Provider
```

其余继续使用官方默认。

这样支持实验而不要求重建整个 Life Model。

---

### 15C.19 Capability-first Dependency

Plugin Dependency 优先声明：

```text
Capability Contract
```

而不是具体 Plugin ID。

例如：

```text
requires:
  MemoryRetrievalCapability
  GoalViewCapability
  BeliefViewCapability
```

避免和具体实现强耦合。

---

### 15C.20 Manifest Requirements

v0.1 Manifest 至少表达：

```text
plugin_id
plugin_version
kernel_compatibility
owned_state_namespaces
provided_capabilities
required_capabilities
optional_capabilities
registered_processes
registered_hooks
registered_tasks
permissions
state_schema_versions
entrypoint
```

具体 Python dataclass 在 Stage G 定义。

---

### 15C.21 Plugin Version vs State Schema Version

正式区分：

```text
plugin_version
≠
state_schema_version
```

Process Provider 通常没有长期 State Schema。

State Owner Plugin Upgrade 必须进行：

```text
schema compatibility
migration validation
transactional migration when needed
```

---

### 15C.22 Permission

Plugin Permission 默认最小化。

Cognitive Plugin 不需要：

```text
direct DB
Runtime transaction internals
Scheduler internals
all-agent private state
Secrets
```

LLM / Environment Provider 可以声明：

```text
network
secret access
external action
```

等额外权限。

---

### 15C.23 Trusted same-process Plugins

v0.1 same-process third-party plugins 仍视为 trusted code。

Permission System 提供：

```text
architecture capability control
audit
configuration approval
```

但不假装 Python 同进程已经实现强 Sandbox。

---

### 15C.24 Hot Swap

正式区分：

```text
Replaceable
≠
Hot-swappable
```

Core State Owner 不支持运行时 Hot Replace。

v0.1 Process Provider 也不实现复杂在线 Hot Swap。

切换实现应在：

```text
pause / checkpoint
runtime restart
controlled branch / migration
```

边界完成。

---

### 15C.25 Reference Implementation

Default Plugin 表示：

> **官方保证协议兼容、可运行、可测试的参考实现。**

不表示：

> **唯一正确的人类心理模型。**

所有官方 Default Plugins 必须通过完整 Reference Profile Integration Test。

---

### 15C.26 Explicit v0.1 Non-goals

官方 v0.1 不实现：

```text
full world simulator
physics engine
economy
inventory
combat system
city simulation

distributed life runtime
massive multi-agent scaling engine
hot plugin replacement

mandatory graph database
mandatory external vector database

advanced psychology plugin zoo
therapy module
mental disorder simulator

self-code-editing / autonomous code-repair plugin

historical world engine
novel world engine
game engine
```

只保留必要 Extension Point。

---

### 15C.27 Official Plugin Set v0.1 最终原则

正式接受：

1. Plugin Architecture 与 Python Distribution 拆包分离。
2. v0.1 不拆成几十个独立 pip 包。
3. 运行时保持细粒度 Provider / Owner Selection。
4. Kernel / Runtime Infrastructure 不是普通 Life Plugin。
5. PluginManager / CapabilityRegistry / Scheduler / RandomService / Resolver / Transaction 属于 Framework Host。
6. Persistence 属于 Runtime Provider。
7. 13 个 Core State 逻辑上拥有独立 Active Owner。
8. 官方 State Owner 作为 Default Life Bundle 交付。
9. 一个 Bundle 可以包含多个逻辑 Plugin Component。
10. Installed ≠ Selected。
11. 一个 State Namespace 只能有一个 Active Owner。
12. Protocol 允许单 Plugin 拥有多个 Namespace。
13. 官方默认保持清晰单 Namespace Owner 边界。
14. State-specific 小 Process 默认放在 State Plugin 内部。
15. 不采用 Every Class Is A Plugin。
16. 六大 Cognitive Process 逻辑上独立可替换。
17. 官方 Cognitive Process 作为 Default Cognition Bundle 交付。
18. Process Provider 可以多个 Installed，但默认一个 Primary。
19. State Owner 不允许 silent fallback。
20. State Owner failure 默认 Pause / Fail。
21. Process Provider 可配置明确 fallback。
22. Memory Store 与 Vector Index 分离。
23. v0.1 不强依赖外部 Vector DB。
24. Environment Adapter 是正式 Extension Point。
25. 官方 v0.1 只实现极简 Sandbox + HumanInteraction Adapter。
26. 不实现完整 Historical / Novel / Game World。
27. LLM 通过 Capability 注入，不在认知 Plugin 写死厂商 SDK。
28. Embedding 与 LLM Capability 分离。
29. Embedding 是 Optional Capability。
30. 无 Embedding 时 Retrieval 必须能运行。
31. 官方测试提供 Mock / Scripted LLM。
32. 建议提供 No-LLM fallback。
33. No-LLM 不承诺完整智能效果。
34. Runtime Time / Random / Scheduler 属于 Kernel。
35. Plugin 不自行绕过 Runtime 时钟 / Random / Scheduler。
36. Trace / Metrics / Index 属于 Auxiliary Provider。
37. Observability 不改变生命语义。
38. Official Plugin Set 按五类理解。
39. Default Profile 自动展开完整 Reference Runtime。
40. 用户配置粗粒度，Runtime Selection 细粒度。
41. Research Profile 支持局部 Override。
42. Bundle 是配置 / 发行便利概念，不增加复杂 Kernel 语义。
43. Plugin Dependency 优先 Capability-first。
44. Manifest 声明 owner / capability / process / hook / task / permission / schema / compatibility。
45. plugin_version 与 state_schema_version 分离。
46. Process Provider 通常没有 State Schema。
47. Permission 默认最小化。
48. LLM / Environment Provider 可声明额外 Network / Secret / External Action 权限。
49. same-process third-party plugin v0.1 属于 trusted code。
50. Replaceable ≠ Hot-swappable。
51. Core State Owner 不运行时 Hot Replace。
52. v0.1 Process Provider 也不做复杂在线 Hot Swap。
53. State Plugin Upgrade 必须 schema / migration validation。
54. Migration 必须 transactional。
55. Process Version 进入 Environment Fingerprint / Replay Compatibility。
56. Default Plugins 必须通过 Reference Profile Integration Test。
57. Default Plugin 是参考实现，不宣称唯一正确心理模型。
58. v0.1 明确限制世界模拟、分布式、多插件动物园等 Scope。
59. Core 提供生命运行规则。
60. Default Plugins 提供可运行 Reference Life。
61. 第三方通过稳定 Contract 替换局部实现。

状态：

```text
Architecture Decision:
Official Plugin Set v0.1

Status:
Accepted
```

---

## Cross-cutting Architecture Decision：Developmental Context & Experience Modulation v0.1【已敲定】

### 核心定义

年龄、人生阶段与阅历必须影响数字生命的认知与长期发展，但：

```text
Age
≠ Experience
≠ Skill
≠ Self-Efficacy
```

本决策不新增第 14 个 Core State。

正式关系：

```text
Identity.birth_time
+ Runtime Time
→ Chronological Age

Body
→ Biological Age / Maturity

LifeStagePolicy
→ LifeStageView

Memory / Goal Outcomes / Actions / Relationships / Roles / Procedural History
→ ExperienceProfileView

Chronological Age
+ Biological Maturity
+ Life Stage
+ Relevant Domain Experience
+ Role / Transition Context
→ DevelopmentContextView
```

`DevelopmentContextView` 是 Derived View / Runtime Context，不是 Source-of-Truth State。

---

### 1. Chronological Age

Chronological Age 继续由：

```text
Identity.birth_time
+
Runtime Time
```

派生。

禁止在多个 State 内重复保存可变年龄字段。

---

### 2. Biological Age / Maturity

Biological Age / Maturity 继续由 Body 负责。

正式区分：

```text
Chronological Age
≠
Biological Age
```

不同 Body Model 可以对成熟、衰老、恢复等使用不同策略。

---

### 3. Life Stage

Life Stage 是 Derived View，不是硬编码年龄标签。

通过：

```text
LifeStagePolicy
```

结合：

```text
chronological age
biological maturity
scenario/species lifespan
role / transition context
```

生成。

Core 不硬编码：

```text
0-12 child
13-18 teenager
...
```

等固定人类年龄段。

官方 Human Default 可以提供参考策略，但必须可替换。

---

### 4. Domain Experience

不设计：

```text
agent.experience_level
```

单一全局阅历值。

Experience 必须 Domain-specific，例如：

```text
social.conflict
social.intimacy
work.management
work.research
skill.public_speaking
life.loss
life.caregiving
```

Domain taxonomy 可扩展。

---

### 5. ExperienceProfileView

ExperienceProfileView 从真实生命历史派生。

概念上：

```text
DomainExperience
├── domain
├── exposure
├── practice
├── diversity
├── recency
├── success_failure_mix
├── significant_episode_refs
├── procedural_refs
└── confidence
```

Experience Claim 应尽可能保留 Source Refs。

---

### 6. Experience ≠ Competence ≠ Self-Efficacy

正式区分：

```text
Experience
= 我经历过多少 / 什么

Competence / Skill
= 我实际会不会

Self-Efficacy
= 我认为自己会不会
```

一个人可以：

```text
experience high
competence low
```

也可以：

```text
competence high
self-efficacy low
```

禁止把三个概念合并。

---

### 7. Experience Index

允许：

```text
ExperienceIndex
```

作为 Derived / Auxiliary Index，避免每 Tick 扫描全部 Memory / History。

它不是 Source of Truth。

更新失败：

```text
不阻塞 Core Tick Commit
```

并应可以从历史 Source Rebuild。

---

### 8. DevelopmentContextBuilder

引入：

```text
DevelopmentContextBuilder
```

作为 Runtime / Integration 层 Context Builder。

它通过 Capability / Derived Index 读取：

```text
Identity
Body
Memory / History
Goal Outcomes
Relationship History
Roles / Identity Transitions
Procedural Memory
```

构造：

```text
DevelopmentContextView
```

不拥有长期 State。

---

### 9. Owner-specific Interpretation

禁止全局：

```text
age_multiplier
experience_multiplier
```

每个 State Owner / Process 根据自己的语义解释 Development Context。

原则：

> **发展背景是输入，不是统一状态修改公式。**

---

### 10. Personality

Development Context 主要调节：

```text
plasticity
stability
development evidence weight
```

不允许：

```text
age > X
→ trait += Y
```

PersonalityOwner 仍基于长期 Development Evidence 做 bounded slow update。

---

### 11. Value

Life Stage / Experience 可以影响：

```text
evidence weighting
plasticity
stability
context relevance
```

但年龄不能直接生成或重写 Value。

---

### 12. Self Model

Domain Experience 与 Goal / Action Outcomes 可影响：

```text
domain-specific self-efficacy
self-assessment evidence
```

但 Experience 本身不等于 Self-Efficacy。

一次事件对经验不足者与有大量 Counter-Evidence 的经验丰富者可以产生不同 Self Model 影响。

---

### 13. Appraisal

Development Context 可以进入 AppraisalContext。

尤其影响：

```text
novelty
familiarity
coping potential
certainty
expectedness
available learned strategy
```

同一事件对于不同 Experience Profile 可以产生不同 Appraisal。

---

### 14. Emotion

不采用：

```text
age → emotion
```

直接映射。

Experience 对 Emotion 的影响主要通过：

```text
Appraisal
learned regulation strategy
Procedural Memory
Belief
Narrative
past sensitivity
```

间接体现。

经验多不必然更冷静，也可能形成更强敏感性或偏差。

---

### 15. Memory Retrieval

阅历越丰富，Memory Pool 越大，但一次 Retrieval Budget 不因此自动增加。

正式原则：

> **Experience richness increases candidate richness, not cognitive context size.**

Expert-like retrieval 可以通过：

```text
Domain Experience
Semantic Generalization
Procedural Memory
World Model
```

提高结构相关的召回质量。

---

### 16. Goal

Goal 可以读取：

```text
Life Stage
Active Role
Time Horizon
Domain Experience
```

作为 Context。

但年龄不直接生成：

```text
marriage goal
retirement goal
parenthood goal
```

等固定人生模板。

---

### 17. Relationship

Relationship / Social Experience 可以影响：

```text
expectation
interpretation
social strategy availability
relationship pattern recognition
```

但年龄本身不直接决定：

```text
trust
maturity
attachment quality
```

---

### 18. Decision / Planning

Domain Experience 可以影响：

```text
Candidate Generation
Fast Path availability
Procedural shortcut
Subjective Feasibility
Risk Estimate
Decision Depth
```

熟悉领域可能：

```text
更多依赖 Habit / Procedure / Fast Path
```

陌生、高重要、高不确定领域可能：

```text
更高 Deliberation
更多 ASK / CLARIFY
更低 certainty
```

---

### 19. Communication

Communication 可以读取：

```text
social experience
communication experience
role experience
```

形成表达策略 Context。

但禁止仅根据年龄刻板化：

```text
年龄大 → 圆滑
年龄小 → 幼稚
```

---

### 20. Reflection / Narrative

人生时间跨度与阅历积累可以提供更多：

```text
longitudinal evidence
turning points
role transitions
repeated patterns
life chapters
```

但：

```text
age ↑
≠
reflection depth automatically ↑
```

Narrative Chapter 可以参考 Life Stage / Role / Turning Point，但不强制统一人生模板。

---

### 21. LLM Context

LLM 优先接收：

```text
structured DevelopmentContextView
relevant DomainExperience
```

而不是只给裸年龄让模型自行猜测心理特征。

例如：

```text
life_stage = early_career
domain_experience.public_speaking = low
```

比：

```text
age = 23
```

更有认知意义。

---

### 22. LLM Need / Decision Depth

Development Context 可以参与：

```text
LLMNeedAssessment
DecisionDepthPolicy
```

例如：

```text
familiar domain
+ high experience
+ stable procedure
→ prefer fast / deterministic path

novel domain
+ low experience
+ high importance
+ high uncertainty
→ allow bounded deeper reasoning
```

但仍受 Runtime Budget 控制。

---

### 23. Growth

成长不定义为：

```text
age++
```

而是：

```text
Experience
+ Memory
+ Semantic Generalization
+ Procedural Memory
+ Belief
+ World Model
+ Self Model
+ Narrative
```

长期共同变化。

正式目标：

> **让人生经历改变 Agent 的认知方式，而不仅仅增加记忆数量。**

---

### 24. Developmental Context v0.1 最终原则

正式接受：

1. 年龄 / Life Stage / Experience 必须影响生命运行。
2. 不新增第14个 Core State。
3. Chronological Age 由 Identity.birth_time + Runtime Time 派生。
4. Biological Age / Maturity 属于 Body。
5. Life Stage 是可替换 Derived View。
6. Age ≠ Experience ≠ Skill ≠ Self-Efficacy。
7. 不设计单一全局 experience_level。
8. Experience 必须 domain-specific。
9. ExperienceProfileView 从真实历史派生。
10. ExperienceProfileView 不是 Source of Truth。
11. Experience Index 可存在，但必须可重建。
12. Experience Index failure 不阻塞 Core Tick。
13. DevelopmentContextBuilder 属于 Runtime / Integration。
14. DevelopmentContextView 提供 age / maturity / stage / relevant experience / roles / transitions。
15. 每个 Owner / Process 自己解释 Development Context。
16. 禁止全局 age multiplier。
17. Personality 主要通过 Plasticity / Stability 接受 Development Context。
18. Value 通过 Evidence Weight / Plasticity 接受影响。
19. Self Model 使用 Domain Experience / Outcome History 调节 Self-Efficacy Evidence。
20. Appraisal 使用 Experience 判断 Novelty / Familiarity / Coping / Certainty。
21. Emotion 不使用简单 age→emotion 规则。
22. Emotion Regulation 差异主要来自 learned strategy / history。
23. Retrieval 使用 Experience Context，但 Budget 不随阅历无限增大。
24. 经验丰富不意味着一次召回更多 Memory。
25. Goal 可读 Life Stage / Role / Horizon，但年龄不直接生成 Goal。
26. Relationship 使用 social/relationship experience，而不是年龄决定成熟度。
27. Decision 使用 Experience 调节 Candidate / Fast Path / Feasibility / Risk / Depth。
28. 熟悉领域可更多走 Fast Path。
29. 陌生重要领域可增加受控 Deliberation / ASK / CLARIFY。
30. Communication 使用 social/communication experience，不做年龄刻板化。
31. Reflection 随人生积累获得更多纵向 Evidence，但不因年龄自动更深刻。
32. Narrative Chapter 可参考 Life Stage / Role / Turning Point，但无统一人生模板。
33. LifeStagePolicy 必须可替换。
34. 禁止各模块散落大量 if age > X。
35. LLM 优先接收结构化 Development Context，而不是裸年龄。
36. Age / Experience 形成 Context / Bias / Plasticity / Evidence Weight，不替代 Core State。
37. Experience 多不必然更理性、更成熟或更冷静。
38. Experience 可以形成适应，也可以形成敏感、偏见与错误模式。
39. Experience Claim 尽可能保留 Source Refs。
40. Development Context 可参与 LLMNeedAssessment / DecisionDepthPolicy。
41. 熟悉问题可以减少不必要 LLM 调用。
42. 陌生、高重要、高不确定问题允许更深的 bounded cognition。
43. 数字生命的成长来自历史积累改变认知结构，而不是简单年龄增加。

状态：

```text
Architecture Decision:
Developmental Context & Experience Modulation v0.1

Status:
Accepted
```

---

## Architecture Decision #15D：LLM Call Strategy【已敲定】

### 核心定义

LLM 是 AnimaFlux 的 Cognitive Capability，不是 Agent 本体。

正式坚持：

```text
LLM
≠
Agent
```

数字生命仍然由：

```text
State
+ Dynamics
+ Memory
+ Environment
+ Runtime
+ LLM Capability
```

共同组成。

---

### 15D.1 Runtime-owned LLM Invocation

Cognitive Process 不直接调用具体厂商 SDK。

统一：

```text
Cognitive Process
↓
LLMCapability
↓
Configured LLM Provider
```

每次调用必须通过受控 `LLMCallRequest`。

---

### 15D.2 Deterministic First

能由代码稳定完成的任务优先 deterministic。

以下不得依赖 LLM 保证正确性：

```text
Runtime Time
Scheduler
RandomService
Permission
State Ownership
State Resolver
Schema Validation
Transaction
Commit / Rollback
Replay correctness
```

---

### 15D.3 LLM Appropriate Tasks

LLM 主要用于：

```text
complex semantic interpretation
candidate proposal
trade-off interpretation
language realization
long-horizon reflection
semantic synthesis
```

原则：

> **LLM 负责理解、提出、表达、反思；代码负责规则、权限、状态、事务和事实边界。**

---

### 15D.4 LLMNeedAssessment

每个 Process 在调用 LLM 前先进行 deterministic `LLMNeedAssessment`。

可以考虑：

```text
semantic complexity
uncertainty
significance
deterministic fallback availability
domain familiarity
relevant domain experience
budget
decision depth
```

不允许再调用另一个 LLM 判断“是否应该调用 LLM”。

---

### 15D.5 Development Context Integration

年龄 / 阅历通过结构化：

```text
DevelopmentContextView
DomainExperience
LifeStageView
```

影响：

```text
familiarity
novelty
uncertainty
decision depth
LLM need
```

正式禁止：

```text
raw age
→ model freely stereotypes personality
```

LLM 优先看到：

```text
life stage
relevant domain experience
role context
familiarity / novelty
```

而不是只看到裸年龄。

---

### 15D.6 LLMCallPolicy

统一 `LLMCallPolicy` 负责：

```text
is_allowed
is_needed
model_profile
input budget
output budget
retry policy
repair policy
fallback policy
```

Process 提供语义上的 LLM Need，Runtime Policy 决定是否允许和如何调用。

---

### 15D.7 Process-specific Context

不存在 Universal Full Agent Context。

正式使用：

```text
PerceptionContext
AppraisalContext
DecisionContext
CommunicationContext
ReflectionContext
```

等 Process-specific Context。

LLM 不自行遍历完整 Agent State。

---

### 15D.8 Minimum Context Principle

Runtime 负责：

```text
Capability Read
Retrieval
Context Selection
Knowledge Boundary
Permission Filtering
Budget Packing
```

然后只把最小必要 Context 交给 LLM。

---

### 15D.9 Source Refs / Confidence / Provenance

重要输入进入 LLM 时应保留：

```text
source_refs
confidence
provenance
```

重要输出必须能够引用其 Evidence。

Causal Trace 使用这些引用追踪：

```text
Perception / Memory / Belief
→ LLM Call
→ Cognitive Artifact
→ Influence / Evidence
→ State Change
```

---

### 15D.10 Structured Output

除自然语言表达等天然文本任务外：

```text
Structured Output
```

是默认。

例如：

```text
AppraisalProposal
DecisionProposal
ReflectionProposal
GoalProposal
```

不依赖自由文本后处理猜字段。

---

### 15D.11 Validation

Raw LLM Response 必须经过：

```text
Schema Validation
↓
Semantic / Domain Validation
```

Schema Validation 检查：

```text
fields
types
enum
ranges
```

Semantic Validation 检查：

```text
source refs
knowledge boundary
permission
disclosure
action validity
state mutation boundary
```

LLM 不能成为自己输出的最终 Validator。

---

### 15D.12 Prompt Versioning

每个 Prompt 必须拥有：

```text
prompt_template_id
prompt_version
```

并进入：

```text
Trace
LLMCallRecord
Environment Fingerprint
```

Prompt 与业务逻辑分离管理。

---

### 15D.13 Thin System Prompt

Static Process Prompt 应保持薄。

它主要定义：

```text
process role
input contract
forbidden behavior
output schema
source-ref rules
```

Agent Personality / Life History 不应长期写死在 System Prompt。

初始 Character Bible 主要用于 Bootstrap。

运行期以当前 State View 为准。

---

### 15D.14 Process-specific Prompt

Perception / Appraisal / Decision / Communication / Reflection 使用不同 Prompt Contract。

不使用统一：

```text
“你就是这个角色，请回答……”
```

万能人格 Prompt。

---

### 15D.15 Model Profiles

Process 不硬编码具体模型名。

使用抽象 Model Profile，例如：

```text
semantic_fast
reasoning_standard
reasoning_deep
language_natural
```

Provider / Profile 再映射到具体模型。

---

### 15D.16 Experience-aware Reasoning Depth

相关领域 Experience 可以影响 Reasoning Depth：

```text
high familiarity
+ mature procedural memory
+ ordinary importance
→ prefer Fast / deterministic path

low experience
+ novel situation
+ high importance
+ high uncertainty
→ allow bounded deeper reasoning
```

不是：

```text
age ↑
→ cheaper model
```

而是 Domain Experience / Familiarity 起作用。

---

### 15D.17 Budget

LLM Budget 是 Runtime 一等概念。

支持：

```text
Runtime Budget
Tick Budget
Process Budget
```

并控制：

```text
call_count
input_token_budget
output_token_budget
optional cost budget
```

Budget Exhaustion 是合法运行状态。

---

### 15D.18 Context Packing

Token Budget 与 Memory / Context Budget 联动。

Context 以：

```text
Memory View
Belief View
Goal View
Relationship View
Development Context
```

等结构单元进行选择、压缩、打包。

不使用粗暴字符串截断作为主要策略。

---

### 15D.19 Context Manifest

重要 LLM Call 建议记录：

```text
perceived_event_refs
memory_refs
belief_refs
goal_refs
relationship_refs
self_refs
development_context_refs
narrative_refs
omitted_due_to_budget
```

用于 Debug / Research。

---

### 15D.20 LLMCallRecord

重要调用记录：

```text
llm_call_id
agent_id
branch_id
tick_id
attempt_id
process_id

provider
model
model_revision

prompt_template_id
prompt_version
output_schema_version

generation_policy
context_manifest

request_artifact_ref
response_artifact_ref
validated_structured_result

token_usage
latency
status
retry / repair lineage
```

完整 Prompt / Response 进入受控 Artifact / Trace，而不是普通日志。

---

### 15D.21 Replay

正式规定：

```text
Exact Historical Replay
→ never call LLM again
→ reuse historical validated result

Deterministic Core Re-execution
→ rerun deterministic core
→ reuse stored nondeterministic results

RESIMULATE
→ may call LLM again
→ create new branch outcome
```

Exact Replay 的稳定性来自保存历史结果，而不是相信模型可重复。

---

### 15D.22 Technical Retry

同一 Logical Tick / Call 在技术重试时：

```text
reuse previously successful nondeterministic result
```

尽量避免由于数据库等后续失败导致 Agent “重新想一次”。

---

### 15D.23 Retry / Repair / Fallback

正式区分：

```text
Retry
= technical failure

Repair
= output format / contract violation

Fallback
= switch to safer simpler strategy
```

全部必须 bounded。

关键语义发生显著变化时必须作为新 Proposal 再次 Validation。

---

### 15D.24 Process-specific Fallback

Fallback 不使用统一“失败就换更强模型”。

例如：

```text
Appraisal
→ minimal deterministic appraisal

Communication
→ template / minimal utterance / defer

Reflection
→ skip current reflection
```

Fallback Policy 属于 Process-specific Policy。

---

### 15D.25 Cache

v0.1 只建议：

```text
Exact Request Cache
```

Fingerprint 应包含：

```text
prompt version
model
generation policy
context refs / content hash
output schema
```

不建议 Decision / Reflection 使用 Semantic Cache。

---

### 15D.26 Generation Policy

Core 不把 `temperature` 等厂商参数当作核心语义。

使用：

```text
determinism level
diversity policy
reasoning depth
output budget
```

等抽象策略。

Provider 再映射到模型具体参数。

---

### 15D.27 Runtime Random vs LLM Randomness

Runtime `RandomService` 与 LLM nondeterminism 分离。

即使 Provider 支持 seed：

```text
LLM seed
≠
Exact Replay guarantee
```

Replay 仍依赖保存历史 validated result。

---

### 15D.28 State Owner Boundary

LLM 输出永远不能绕过对应 State Owner。

例如：

```text
Appraisal LLM
→ AppraisalResult
→ Emotion Influence
→ EmotionOwner
```

而不是直接写 Emotion。

Reflection LLM 也只能产生 Development Evidence / Revision Proposal。

---

### 15D.29 Communication Boundary

Communication LLM 只负责：

```text
Language Realization
```

其输入必须已经限定：

```text
CommunicativeIntent
Allowed Claims
Disclosure Policy
Style Context
Conversation Context
```

不能擅自改变 Intent、撒谎、泄密或增加 Agent Knowledge。

---

### 15D.30 Prompt Injection / Untrusted Content

外部输入：

```text
other agent speech
human message
web content
memory quote
environment text
```

都属于：

```text
Untrusted Data
```

不能改变：

```text
Process Role
Output Schema
Knowledge Boundary
Disclosure Policy
Permission
Runtime Instruction
```

---

### 15D.31 Tool Calling

若 Provider 支持 Tool Calling，只允许暴露：

```text
Process-scoped Capability
```

禁止直接暴露：

```text
StateStore
Database
Transaction
PluginManager
Scheduler internals
unrestricted Environment execution
other Agent private state
```

v0.1 不采用开放式 autonomous tool loop 作为主认知机制。

---

### 15D.32 Secret Boundary

Secret 不进入 Prompt。

LLM / Environment Provider 通过：

```text
SecretProvider
```

获得自己的凭证。

Cognitive Plugin 不接触 Secret。

---

### 15D.33 Cost / Latency

```text
token usage
cost
latency
```

属于 Runtime Observability，不属于 Life State。

正式区分：

```text
wall-clock latency
≠
simulated runtime time
```

如果需要模拟思考时间，由 Time / Cognitive Policy 明确产生。

---

### 15D.34 Call Granularity

默认尽量：

```text
one process
→ one main LLM call
```

而不是把每个 Facet 拆成大量独立调用。

典型目标：

```text
Perception      0~1
Retrieval       0~1 optional
Appraisal       0~1
Decision        0~1
Communication   0~1 + bounded repair
Reflection      0~2 low-frequency
```

不是硬编码，但作为 v0.1 成本与复杂度控制目标。

---

### 15D.35 Runtime Profiles

v0.1 概念支持：

```text
deterministic
hybrid
llm_rich
```

官方默认：

```text
hybrid
```

无论哪种 Profile：

```text
State Ownership
Permission
Transaction
Commit
Replay Correctness
```

都不交给 LLM。

---

### 15D.36 LLM Call Strategy v0.1 最终原则

正式接受：

1. LLM 是 Cognitive Capability，不是 Agent 本体。
2. Cognitive Process 通过统一 LLMCapability 调用模型。
3. 不在 Cognitive Plugin 中写死模型厂商 SDK。
4. 每次调用使用受控 LLMCallRequest。
5. deterministic 可稳定完成的任务优先代码。
6. Runtime Time / Random / Permission / Owner / Resolver / Transaction / Commit / Replay correctness 禁止依赖 LLM。
7. LLM 主要用于复杂语义理解、候选提出、表达和反思。
8. 每个 Process 有明确 LLM 权限。
9. 使用 deterministic LLMNeedAssessment。
10. LLMNeedAssessment 可读取 Domain Experience / Familiarity / Uncertainty。
11. 裸年龄不直接决定心理输出。
12. Development Context 以结构化 View 进入需要它的 Process。
13. Runtime 负责准备 Context。
14. LLM 不自行遍历完整 Agent State。
15. 不存在 Universal Full Agent Context。
16. 每个 Process 使用最小独立 Context Schema。
17. Context 必须满足 Character Knowledge Boundary。
18. 多 Agent 私有 State 不得因 LLM 调用泄露。
19. 重要输入保留 source refs / confidence / provenance。
20. 除文本表达任务外 Structured Output 为默认。
21. 每类任务有明确 Output Schema。
22. Raw Response 先 Schema Validation。
23. 再进行 Semantic / Domain Validation。
24. LLM 不是自己输出的最终 Validator。
25. Prompt 有 stable ID / Version。
26. Prompt Version 进入 Trace / Fingerprint。
27. Prompt 与业务逻辑分离。
28. Static System Prompt 保持薄。
29. Character Bible 主要用于 Bootstrap。
30. 运行期以当前 State View 为准。
31. Prompt 必须 Process-specific。
32. Model Name 不在 Process 中硬编码。
33. 使用抽象 Model Profile。
34. Domain Experience 可以影响 Fast / Deliberative Path。
35. Experience 多不必然更正确。
36. LLM Budget 是 Runtime 一等概念。
37. 支持 Runtime / Tick / Process 多层 Budget。
38. Budget Exhaustion 是合法状态。
39. Context 以结构化 View 为单位打包。
40. 建议记录 Context Manifest。
41. 完整 Prompt / Response 进入受控 Artifact / Trace。
42. 每个模型调用拥有稳定 llm_call_id。
43. LLMCallRecord 记录模型、Prompt、Context、Schema、Usage、Latency、Lineage。
44. Validated Structured Result 直接持久化。
45. Exact Replay 绝不重调历史 LLM。
46. Deterministic Core Re-execution 复用历史 nondeterministic result。
47. RESIMULATE 才允许重新调用 LLM。
48. Technical Tick Retry 尽量复用成功的 LLM Result。
49. Retry / Repair / Fallback 分离。
50. 三者全部 bounded。
51. Fallback Policy 是 Process-specific。
52. v0.1 只建议 Exact Request Cache。
53. Decision / Reflection 不建议 Semantic Cache。
54. GenerationPolicy 使用抽象语义，不绑定 temperature。
55. Runtime Random 与 LLM nondeterminism 分离。
56. LLM seed 不是 Replay 保证。
57. LLM 输出不能绕过 State Owner。
58. Appraisal LLM 不直接写 Emotion / Belief。
59. Reflection LLM 不直接改 Personality / Value / Self / Narrative。
60. Communication LLM 不得改变 Intent / Knowledge / Disclosure。
61. External Content 永远作为 Untrusted Data。
62. Prompt Injection 不得改变 Runtime Contract。
63. Tool Calling 只能暴露 Process-scoped Capability。
64. 不暴露 Store / DB / Transaction / unrestricted action。
65. v0.1 不采用开放式 autonomous tool loop。
66. Runtime 编排 Cognition，LLM 提供局部语义能力。
67. Secret 不进入 Prompt。
68. Token / Cost / Latency 属于 Observability。
69. wall-clock latency 不等于 simulated time。
70. 默认避免一个 Process 拆成大量 LLM Call。
71. 同一 Tick 不默认所有 Process 都调用 LLM。
72. 官方默认使用 hybrid Profile。
73. llm-rich 也不能突破 Runtime / Owner 主权。
74. Provider / Model 可替换，只要满足 Capability Contract。
75. Experience / Life Stage 改变的是 Context、Familiarity、Plasticity 与 Reasoning Need，而不是通过年龄刻板印象替代真实 State。

状态：

```text
Architecture Decision:
LLM Call Strategy v0.1

Status:
Accepted
```

---

# Stage F：Integration / Wiring【完成】

```text
#15A Core Dependency Map       ✅
#15B Default Life Loop Wiring  ✅
#15C Official Plugin Set       ✅
#15D LLM Call Strategy         ✅
```

---

# Stage G：Implementation Blueprint

## Architecture Decision #16A：Python Project Structure【已敲定】

### 核心原则

AnimaFlux v0.1 使用：

```text
single repository
single main Python distribution
src/ layout
contract-first layering
runtime-owned orchestration
plugin-owned life semantics
```

Plugin Architecture 不等于多仓库 / 多 pip 包。

---

### 16A.1 Top-level Layout

推荐：

```text
animaflux/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── configs/
├── docs/
├── examples/
├── scripts/
├── src/
│   └── animaflux/
└── tests/
```

---

### 16A.2 `src/animaflux`

核心目录：

```text
src/animaflux/
├── contracts/
├── kernel/
├── runtime/
├── state/
├── plugins/
├── persistence/
├── llm/
├── environment/
├── observability/
├── config/
└── cli/
```

---

### 16A.3 Contracts Layer

`contracts/` 是最稳定的公共协议层。

建议按领域组织：

```text
contracts/
├── common/
├── runtime/
├── state/
├── cognition/
├── environment/
├── llm/
└── plugin/
```

其中定义：

```text
IDs
Event
Influence
Evidence
ActionIntent
Process Protocol
StateOwner Protocol
Capability Protocol
Cognitive Context / Result
Environment Adapter Contract
LLM Capability Contract
Plugin Manifest
```

Contracts 不依赖任何具体 Default Plugin。

---

### 16A.4 Kernel

Kernel 只处理机制：

```text
Clock
RandomService
CapabilityRegistry
PluginManager
NamespaceRegistry
EventRouter
Scheduler
```

Kernel 不理解：

```text
Emotion
Goal
Belief
Memory
Relationship
```

等领域语义。

---

### 16A.5 Runtime

Runtime 负责：

```text
Life Loop
Tick
Execution Context
State Resolver
Runtime Transaction
Runtime Plan
Checkpoint
Replay
Branch
Failure Isolation
Causal Trace
Input Journal
Development Context
Bootstrap
```

`LifeLoopRunner` 是编排者，不包含具体心理算法。

---

### 16A.6 Runtime Context Boundary

Plugin 获取：

```text
ExecutionContext / ProcessContext
```

而不是完整 Runtime 对象。

Plugin 不应因此获得：

```text
raw DB
StateStore internals
Transaction internals
Scheduler internals
PluginManager internals
```

---

### 16A.7 State Infrastructure

`state/` 只包含通用 State 基础设施，例如：

```text
StateStore
Snapshot
StateVersion
WorkingState
Namespace
Serialization
Migration
```

具体：

```text
EmotionState
GoalState
BeliefState
```

属于对应 Plugin，而不是 Framework Core。

---

### 16A.8 Default Life Plugins

官方默认 State Owner 放：

```text
plugins/default_life/
```

逻辑上包括 13 个 Core State Owner。

State-specific 小 Process 留在对应 Plugin 内部，不全部拆成独立插件。

---

### 16A.9 Default Cognition Plugins

官方默认 Cognitive Process 放：

```text
plugins/default_cognition/
```

包括：

```text
Perception
Memory Retrieval
Appraisal
Decision / Planning
Communication
Reflection
```

Cognitive Artifact / Provider Protocol 放 `contracts/cognition/`。

---

### 16A.10 Memory Boundary

Memory Owner 与 Memory Retrieval Process 分离。

Memory Plugin 负责：

```text
Memory state/source-of-truth semantics
Formation
Reactivation
Reconsolidation
```

Retrieval 属于 Default Cognition。

---

### 16A.11 Persistence

`persistence/` 只理解通用 Persistence Contract / State payload。

v0.1 实现：

```text
SQLite
InMemory
```

不提前创建未实现 PostgreSQL / External Vector DB 空目录。

正式坚持：

```text
Domain Model
≠
Persistence Model
```

---

### 16A.12 LLM Infrastructure

`llm/` 负责：

```text
Provider
Request
Policy
Budget
Validation
Prompt Registry
Call Records
```

具体 Appraisal / Decision / Reflection Prompt 跟对应 Cognitive Plugin 一起版本化。

LLM Infrastructure 不理解具体心理语义。

---

### 16A.13 Environment

Environment Contract 与 Adapter 实现分离。

v0.1 官方实现：

```text
Null / Sandbox Adapter
HumanInteractionAdapter
```

HumanInteractionAdapter 不允许绕过 Life Loop 直接调用 LLM。

---

### 16A.14 Configuration

用户配置：

```text
configs/*.yaml
```

解析代码：

```text
src/animaflux/config/
```

两者分离。

---

### 16A.15 Observability / CLI

Observability 只做：

```text
logging
metrics
trace sink
life timeline
```

不改变生命语义。

CLI 位于最外层，通过 RuntimeBuilder / RuntimePlan 操作 Runtime。

---

### 16A.16 Bootstrap

新生命初始化逻辑属于 Runtime Bootstrap。

具体 Character / Scenario 模板不写死在 Runtime。

---

### 16A.17 Tests

测试建议：

```text
tests/
├── unit/
├── contract/
├── integration/
├── replay/
└── fixtures/
```

AnimaFlux 特别重视：

```text
contract
integration
replay
```

而不只单元测试。

---

### 16A.18 Implementation Order

目录蓝图不等于第一天创建所有文件。

第一批只实现：

```text
Event
Influence
Process
StateOwner
Capability
Snapshot
Resolver
Tick
```

先用 InMemory Runtime 跑通。

然后：

```text
Persistence
small state vertical slice
cognition vertical slice
incremental state expansion
```

---

### 16A.19 Vertical Slice

架构设计顺序与实现顺序分离。

实现采用小型 Vertical Slice，不一次实现全部 13 State。

先验证：

```text
Owner
View
Influence
Resolver
State Store
Transaction
Persistence
```

再逐步扩展。

---

### 16A.20 Python Model Style

推荐：

```text
dataclass
Protocol
Enum
composition
explicit functions
```

内部高频 Value Object 优先 immutable dataclass。

配置 / 外部输入 / LLM Structured Output 可优先使用 Pydantic。

不使用全裸 dict，也不把所有对象全部强制 Pydantic。

---

### 16A.21 Import Direction

正式原则：

```text
Default Plugins
→ Framework Contracts / Public Runtime Context

Framework Core
↛ Default Plugin internals
```

特别禁止：

```text
runtime/
kernel/
generic persistence/
```

直接 import `DefaultEmotionState` 等具体 Default Plugin 类型。

---

### 16A.22 RuntimeBuilder / RuntimePlan

建议使用：

```text
RuntimeBuilder
```

负责：

```text
Config
Plugin Discovery
Capability Resolution
State Owner Selection
Backend Construction
Environment Construction
Runtime Plan
```

`RuntimePlan` 记录最终 Owner / Provider / Backend / Model / Adapter 组合，并进入 Environment Fingerprint。

---

### 16A.23 Avoid God Object / Overengineering

避免：

```text
LifeRuntime God Object
```

也避免：

```text
Factory / Mediator / Orchestrator
```

类数量爆炸。

Python 实现保持显式、轻量、可读。

---

### 16A.24 Plugin Discovery

v0.1 Plugin Discovery 保持简单。

官方 Built-in Plugin 可显式注册。

第三方未来可使用 Python Entry Points。

不依赖复杂目录扫描 / subclass 魔法发现。

---

### 16A.25 IDs / Time / Random

IDs 在 Contract 层统一定义。

生命逻辑禁止直接使用：

```text
datetime.now()
time.time()
global random
```

生命周期时间使用：

```text
context.time
```

随机使用：

```text
context.random
```

---

### 16A.26 Sync / Async Boundary

I/O Boundary 使用 async。

纯领域计算尽量 sync。

推荐：

```text
Process Protocol
→ async-capable

StateOwner
→ sync / deterministic / pure-ish

Persistence
→ I/O

LLM
→ async I/O

Environment
→ async I/O
```

StateOwner 不访问网络、LLM、数据库。

---

### 16A.27 Framework Choice

AnimaFlux Core Runtime 自己实现。

不把 LangChain / LangGraph 作为核心 Runtime。

外部框架可以作为 Provider / Tool 辅助集成，但不能拥有：

```text
Life Loop
State Ownership
Influence
Transaction
Replay
```

核心语义。

---

### 16A.28 Explicit Non-goals

v0.1 不引入：

```text
Microservices
Redis
Kafka
Celery
Kubernetes
Distributed Runtime
Graph DB requirement
External Vector DB requirement
Plugin Marketplace
Visual Node Editor
Hot Reload
Massive Multi-agent Infrastructure
```

第一版依赖保持克制。

---

### 16A.29 Python Project Structure v0.1 最终原则

正式接受：

1. v0.1 单仓库、单主 Python Distribution。
2. 使用 `src/animaflux`。
3. Plugin Architecture 不等于多 pip 包。
4. `contracts/` 是公共协议层。
5. Contracts 不依赖 Default Plugin。
6. Kernel 只处理机制，不理解生命领域语义。
7. Runtime 负责编排、解析、事务、Replay、Trace 等。
8. LifeLoopRunner 是编排者。
9. Plugin 获取 Context，不获取完整 Runtime。
10. StateResolver 是跨 State Change 统一入口。
11. Runtime Transaction 高于具体 DB Transaction。
12. DevelopmentContextBuilder 位于 Runtime / Integration 层。
13. 通用 State Infrastructure 与具体 State Schema 分离。
14. 具体 State Schema 属于对应 Plugin。
15. Default Life / Default Cognition 分开组织。
16. State-specific 小 Process 留在对应 Plugin 内部。
17. Memory Owner 与 Retrieval 分离。
18. Persistence 不理解具体心理 Plugin。
19. SQLite + InMemory 是 v0.1 默认实现。
20. 不提前建立未实现 Backend 空目录。
21. LLM Infrastructure 与 Cognition Prompt 分离。
22. Prompt 跟 Cognitive Plugin 版本化。
23. Environment Contract 与 Adapter 实现分离。
24. Human Adapter 不绕过 Life Loop。
25. Config Code 与 YAML 分离。
26. Observability 不改变生命语义。
27. CLI 通过 RuntimeBuilder / RuntimePlan 操作系统。
28. Bootstrap 与具体 Character Template 分离。
29. Tests 按 unit / contract / integration / replay 分层。
30. 目录蓝图不等于第一天创建所有文件。
31. 先做最小 Runtime。
32. Persistence 后接。
33. State 用 Vertical Slice 逐步扩展。
34. 架构顺序与实现顺序分离。
35. Domain Model ≠ Persistence Model。
36. 不全用裸 dict。
37. 不全用 Pydantic。
38. Plugin 不访问 Store / DB / Transaction internals。
39. Persistence 不 import Default Plugin。
40. Runtime 不 import Default Plugin 实现。
41. Default Plugin 依赖 Framework，Framework 不反向依赖 Default Plugin。
42. 使用 RuntimeBuilder / RuntimePlan 组装。
43. 避免 God Object。
44. 避免过度 Class / Factory 设计。
45. Python 风格偏 dataclass / Protocol / composition / explicit function。
46. Plugin Discovery v0.1 保持简单。
47. IDs 统一。
48. 生命时间不直接使用 system clock。
49. 生命随机不直接使用 global random。
50. I/O async，纯领域计算 sync。
51. Process 可以 async。
52. StateOwner 默认 sync / deterministic / pure-ish。
53. StateOwner 不访问网络 / LLM / DB。
54. 同输入尽量得到同 Next State。
55. v0.1 不引入无关分布式基础设施。
56. 不强依赖 Graph DB / External Vector DB。
57. LangChain / LangGraph 不拥有 AnimaFlux Core Runtime。
58. 外部库只能作为辅助 Provider / Tool。
59. 第一版依赖保持克制。
60. 真正扩展边界由 Contract 保证，而不是目录名字保证。

状态：

```text
Architecture Decision:
Python Project Structure v0.1

Status:
Accepted
```

---

## Architecture Decision #16B：Persistence Schema【已敲定】

### 核心原则

SQLite 是 AnimaFlux v0.1 官方默认持久化后端。

Persistence 的职责是：

> **保存某个 State 的哪一版、哪一次 Tick 提交了什么、如何恢复 / Replay / Branch。**

Persistence 不负责定义：

> **Emotion、Goal、Belief 等 Plugin State 内部一定有哪些字段。**

正式采用：

```text
Generic Versioned JSON State
+
Specialized Stores only where scale/query semantics justify it
```

---

### 16B.1 Generic State Version

Core State 使用：

```text
namespace
+ optional entity_key
+ immutable version
+ plugin/schema metadata
+ payload_json
```

通用 `state_version` 概念字段：

```text
state_version_id
agent_id
created_branch_id

namespace
entity_key nullable
revision

plugin_id
plugin_version
schema_version

payload_json
content_hash

created_tick_id
created_runtime_time
parent_version_id nullable

created_at_wall
```

StateVersion 一经创建不可修改。

---

### 16B.2 Current Pointer

当前使用哪一版由独立：

```text
state_current
```

表达。

唯一语义键：

```text
(agent_id, branch_id, namespace, entity_key)
```

State Current Pointer 是当前 State 权威入口。

不通过扫描 `state_version` 猜最新版本。

---

### 16B.3 Copy-on-Write

未变化 Namespace 不创建新 Version。

Commit 可以继续引用已有 Immutable Version。

因此：

```text
Tick changes only changed namespaces
```

而不是每 Tick 复制完整 Agent State。

---

### 16B.4 Tick Attempt vs Commit

正式区分：

```text
Tick Attempt
≠
Successful Commit
```

失败 Tick Attempt 也需要记录。

`tick_attempt` 用于：

```text
attempt lineage
technical retry
failure diagnosis
nondeterministic output reuse
```

Commit Journal 只表示成功发布的生命状态版本。

---

### 16B.5 Commit Journal

一次 Tick Commit 记录：

```text
commit_id
runtime_id
agent_id
branch_id
tick_id
tick_attempt_id
runtime_time_before
runtime_time_after
delta_t
status
environment_fingerprint
random_state_ref
```

并通过：

```text
commit_state_ref
```

保存：

```text
namespace/entity_key
→ state_version_id
```

的完整版本地图或必要引用。

---

### 16B.6 Current Pointer Publish

Tick Critical Transaction 中：

```text
new state versions
events
memory critical writes
scheduler/deferred state
commit journal
commit refs
```

先写。

`state_current` 尽量在事务后段更新。

Commit 失败时旧 Current Pointer 仍保持一致。

---

### 16B.7 Checkpoint

Checkpoint 不复制完整 State Payload。

Checkpoint 引用：

```text
successful commit
tick
runtime time
branch
runtime metadata
environment fingerprint
```

通过 Commit Map 恢复完整 State Version Set。

Checkpoint 只引用：

```text
COMMITTED
```

状态。

---

### 16B.8 Branch

Branch 保存：

```text
branch_id
parent_branch_id
fork_checkpoint_id
fork_commit_id
fork_tick_id
random_mode
environment_fingerprint
```

Fork 前共享 Immutable History。

Fork 后独立产生新 Version。

Branch 不复制完整历史。

---

### 16B.9 Version Provenance vs Visibility

`state_version.created_branch_id` 只表示：

> 该 Version 在哪个 Branch 被创建。

它不表示：

> 只有该 Branch 才能引用该 Version。

当前 State 以 Pointer / Commit Map 为权威。

---

### 16B.10 Event Store

Objective Runtime History 使用 append-oriented Event Log。

概念字段：

```text
event_id
runtime_id
agent_id nullable
branch_id
event_type
producer_plugin_id
runtime_time
tick_id
subject_ref
payload_json
cause_refs
visibility_metadata
status
created_at_wall
```

Event immutable。

Correction / Invalidation 使用新 Event，不覆盖原 Event。

---

### 16B.11 Column vs JSON Rule

正式规则：

> **Core Runtime 经常筛选、排序、关联的字段独立成列；Plugin 私有语义放 JSON。**

例如：

```text
agent_id
branch_id
tick_id
runtime_time
namespace
status
```

是列。

而：

```text
emotion episodes
goal criteria
narrative themes
```

属于 Plugin JSON Payload。

---

### 16B.12 Specialized Memory Store

Memory 不使用一个不断膨胀的大 `MemoryState` JSON。

正式特殊化为：

```text
memory_entry
memory_version
memory_runtime_state
```

---

### 16B.13 Memory Entry

`memory_entry` 表示：

> **这是哪一条逻辑 Memory。**

保存：

```text
memory_id
agent_id
created_branch_id
memory_type
created_tick_id
status
current_version_id
```

---

### 16B.14 Memory Version

`memory_version` 表示：

> **当前如何记得这件事。**

保存：

```text
memory_version_id
memory_id
revision
content_json
summary_text
confidence
importance
emotional_salience
source_refs
provenance
created_tick_id
created_runtime_time
parent_version_id
```

Reconsolidation 创建新 Version，不覆盖旧 Memory Content。

---

### 16B.15 Memory Runtime State

机械 Retrieval 元数据与 Memory Content Revision 分离。

例如：

```text
accessibility
last_retrieved_runtime_time
retrieval_count
updated_tick_id
```

放：

```text
memory_runtime_state
```

因此：

```text
retrieving a memory
≠
rewriting a memory
```

---

### 16B.16 Derived Index

Vector Index / Experience Index 属于：

```text
Derived
Rebuildable
Non-source-of-truth
```

Index 更新失败不阻塞 Core Tick Commit。

v0.1 不强制实现 Experience Index。

---

### 16B.17 Scheduler Persistence

`scheduled_task` 持久化：

```text
task_id
runtime_id
agent_id nullable
branch_id
owner_plugin_id
process_id
task_type
schedule_payload
catch_up_policy
next_run_runtime_time
status
```

持久化 Process ID / Task Type，不持久化 Python callback。

---

### 16B.18 Deferred Influence

Resolver 超出 bounded rounds 的 Influence 必须持久化：

```text
deferred_influence
```

保存：

```text
influence_id
agent_id
branch_id
target_namespace
influence_type
payload_json
source_refs
created_tick_id
eligible_runtime_time
expires_runtime_time
status
```

---

### 16B.19 Input Journal

所有 External Nondeterministic Input 进入：

```text
input_journal
```

例如：

```text
Human message
Environment observation
Action result
External API result
```

Exact Replay 从 Input Journal 读取，而不是重新访问外部世界。

---

### 16B.20 LLM Call Store

`llm_call` 保存：

```text
llm_call_id
agent_id
branch_id
tick_id
attempt_id
process_id

provider
model
model_revision

prompt_template_id
prompt_version
output_schema_version

generation_policy
context_manifest

request_artifact_id
response_artifact_id
validated_structured_result

input_tokens
output_tokens
estimated_cost
latency_ms
status
retry_parent_id
```

Exact Replay 直接使用历史 validated structured result。

---

### 16B.21 Artifact Store

大型 Prompt / Response / Export 等不强塞主表。

Artifact Metadata 在 SQLite：

```text
artifact_id
artifact_type
content_hash
storage_backend
storage_path_or_key
mime_type
size_bytes
metadata_json
created_tick_id
created_at_wall
```

大内容 v0.1 可保存在本地 Artifact Directory。

---

### 16B.22 Causal Trace

v0.1 使用：

```text
causal_node
causal_edge
```

而不是引入 Graph DB。

Node 可表示：

```text
EVENT
PERCEIVED_EVENT
MEMORY
APPRAISAL
INFLUENCE
STATE_CHANGE
DECISION
ACTION_INTENT
ACTION_RESULT
LLM_CALL
REFLECTION
```

Edge 表达：

```text
RETRIEVED_FOR
GENERATED
SUPPORTED_BY
CAUSED_CHANGE
LED_TO
```

等关系。

Life Timeline 从 Event / Trace 派生。

---

### 16B.23 Optional entity_key

Generic State 支持：

```text
namespace
+
entity_key
```

用于天然多实例 State，例如：

```text
relationship
entity_key = person:B
```

从而使 A→B 与 A→C 分别版本化。

---

### 16B.24 Specialized Store Scope

v0.1 强制 Specialized Store：

```text
Memory only
```

Goal / Belief / World Model 等先使用 Generic State Version。

未来若数据规模要求，可以由 Plugin 迁移到 Specialized Persistence Provider。

---

### 16B.25 Runtime Identity vs Life Identity

技术实例使用：

```text
life_agent
```

只保存：

```text
agent_id
runtime status metadata
default branch ref
```

不保存：

```text
name
age
occupation
```

这些属于 Identity Plugin State。

---

### 16B.26 Runtime Instance

`runtime_instance` 表示一次 Runtime Session。

它与 Agent 不同。

保存：

```text
runtime_id
agent_id
branch_id
status
profile_name
kernel/runtime version
config fingerprint
last committed tick
wall-clock lifecycle metadata
```

---

### 16B.27 Failure Record

关键故障持久化：

```text
failure_record
```

保存：

```text
failure_id
runtime_id
agent_id
branch_id
tick_attempt_id
component_type
component_id
failure_type
severity
message
details_json
retryable
created_at_wall
```

支持 Failure Isolation / Pause / Retry / Diagnosis。

---

### 16B.28 Plugin / Schema Metadata

State Payload 必须保存：

```text
plugin_id
plugin_version
schema_version
```

无法迁移旧 Schema 时显式 Compatibility Failure。

禁止偷偷猜测旧 Payload。

---

### 16B.29 Content Hash

重要 Immutable Payload / Artifact 保存：

```text
content_hash
```

用于：

```text
mutation detection
dedup
checkpoint verification
cache fingerprint
replay debugging
```

---

### 16B.30 Runtime Time vs Wall Clock

数据库字段必须区分：

```text
runtime_time
wall_clock_time
```

生命语义使用 Runtime Time。

运维 / latency / persistence diagnosis 使用 Wall Clock。

---

### 16B.31 Stable IDs

跨表业务引用使用 Stable Opaque ID。

不依赖 SQLite autoincrement 作为核心语义 ID。

SQLite rowid 可以内部存在，但不是 Runtime Contract。

---

### 16B.32 Index Design

索引围绕真实访问路径。

重点包括：

```text
state_current:
(agent_id, branch_id, namespace, entity_key)

state_version:
(agent_id, namespace, revision)

event_log:
(branch_id, runtime_time)
(branch_id, event_type, runtime_time)

memory:
(agent_id, memory_type)
(agent_id, created_runtime_time)

scheduler:
(status, next_run_runtime_time)

llm_call:
(branch_id, tick_id)
(process_id, status)

causal_edge:
(from_node_id)
(to_node_id)
(branch_id, tick_id)
```

不采用“所有字段都加索引”。

---

### 16B.33 Memory Semantic Search

SQLite 负责：

```text
source-of-truth
metadata filtering
time/person/type filtering
```

Semantic Vector Search 属于 Derived Index Provider。

两者组合完成 Retrieval。

---

### 16B.34 Branch Memory Semantics

Fork 前 Memory History 共享。

Fork 后新 Memory / Reconsolidation 独立演化。

Branch 不复制完整 Memory Store。

具体高效 visibility / cursor 实现在编码阶段收敛，但语义必须保持：

```text
shared pre-fork
independent post-fork
```

---

### 16B.35 Retention / GC

GC 依据：

```text
Current State
Active Working
Committed Checkpoint
Active Branch
Pinned Experiment
```

等 Roots / References。

不采用：

```text
old → delete
```

v0.1 不急于实现自动 GC。

优先提供安全 Retention / inspection 能力。

---

### 16B.36 Tick Transaction

SQLite v0.1 中一次 Tick Critical Commit 尽量使用一个 DB Transaction。

大致顺序：

```text
BEGIN
new state versions
memory critical changes
durable events
scheduler changes
deferred influences
commit journal
commit refs
state current pointer
COMMIT
```

---

### 16B.37 External Side Effects

External Action 不属于 SQLite Rollback 范围。

持久化：

```text
Action correlation
Input / Action Result Journal
```

支持 Technical Retry 复用结果而不重复外部副作用。

---

### 16B.38 Nondeterministic Input vs Life Commit

正式区分：

```text
Nondeterministic Input Fact
≠
Committed Life State
```

例如某次 LLM Result 已真实获得，即使后续 Tick Commit 失败，该外部调用事实仍可能需要保留用于 Retry / Trace。

---

### 16B.39 Avoid Giant Agent Blob

禁止把整个 Agent 保存为：

```text
agent.state_json
```

每 Tick 覆盖。

这会破坏：

```text
versioning
branch
partial change
replay
causal history
schema migration
```

---

### 16B.40 Avoid Over-normalized Psychology Schema

也禁止 Core DB 为每个心理细节建固定业务表。

否则 Persistence Schema 会反过来定义心理模型。

正式采用中间路线：

```text
Generic Versioned JSON
+
Memory Specialized Store
+
必要 Runtime / Historical / Trace tables
```

---

### 16B.41 Persistence Domains

正式按四类理解：

```text
CORE STATE
State Version / Current / Commit / Checkpoint / Branch

HISTORICAL
Event / Memory / Input Journal

RUNTIME
Scheduler / Deferred Influence / Tick Attempt / Failure

AUXILIARY
LLM Call / Artifact / Causal Trace / Derived Index
```

---

### 16B.42 Source of Truth

Source-of-Truth 包括：

```text
state_version
commit_journal
event_log
memory_entry/version
checkpoint recovery metadata
input_journal
scheduled_task
deferred_influence
validated llm_call result
```

Derived / Rebuildable 包括：

```text
Vector Index
Experience Index
Cache
Metrics
部分 debug indexes
```

---

### 16B.43 v0.1 Core SQLite Tables

推荐最终约：

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

约 21 张稳定 Runtime 基础表。

---

### 16B.44 Implementation Order

Persistence 也采用 Vertical Slice：

第一批：

```text
life_agent
life_branch
state_version
state_current
tick_attempt
commit_journal
commit_state_ref
```

先验证：

```text
State Version
→ Tick Commit
→ Restore
```

第二批：

```text
checkpoint
event_log
input_journal
scheduled_task
deferred_influence
```

第三批：

```text
memory_entry
memory_version
memory_runtime_state
```

最后：

```text
llm_call
artifact
causal_node
causal_edge
failure_record
```

---

### 16B.45 Persistence Schema v0.1 最终原则

正式接受：

1. SQLite 是 v0.1 官方持久化后端。
2. Core Persistence 不固化 Default Plugin 心理字段。
3. Plugin State 使用 Namespace + Immutable Version + JSON Payload。
4. StateVersion 不可变。
5. Current State 使用独立 Pointer。
6. Current Pointer 在 Commit 后段更新。
7. 使用 Copy-on-Write。
8. Commit Journal 保存 Tick 版本地图。
9. Tick Attempt 与 Commit 分离。
10. 失败 Attempt 可记录。
11. Checkpoint 引用成功 Commit，不复制 State。
12. Branch 引用 Fork Point，不复制历史。
13. Branch 可引用父 Branch 创建的 Version。
14. Pointer / Commit Map 是 Current State 权威。
15. Event Log immutable / append-oriented。
16. Correction 通过新 Event。
17. 高频 Runtime 查询字段做列。
18. Plugin 私有语义进 JSON。
19. Memory 使用 Specialized Store。
20. Memory Entry / Version / Runtime Accessibility 分离。
21. Reconsolidation 创建新 Memory Version。
22. Retrieval metadata 不等于 Memory Revision。
23. Vector Index 是 Derived。
24. Experience Index 是 Derived。
25. v0.1 不强制 Experience Index。
26. Scheduler 持久化 process/task identity。
27. Deferred Influence 可跨 Tick。
28. Input Journal 支持 Exact Replay。
29. LLM Call 保存 validated result。
30. Exact Replay 使用历史 LLM Result。
31. 大 Prompt / Response 使用 Artifact Store。
32. Artifact 保存 content hash。
33. Causal Trace 使用 Node + Edge。
34. v0.1 不要求 Graph DB。
35. Life Timeline 从 Trace / Event 派生。
36. Relationship 等可使用 optional entity_key。
37. v0.1 只有 Memory 强制 Specialized Store。
38. Goal / Belief / World Model 先用 Generic State Version。
39. 未来可迁移 Specialized Persistence。
40. Runtime Agent ID 与 Life Identity 分离。
41. `life_agent` 不保存生命身份语义。
42. Runtime Instance 与 Agent 分离。
43. Tick Attempt 支持 Retry lineage。
44. Failure Record 持久化关键故障。
45. State Payload 记录 plugin / schema metadata。
46. 无法迁移旧 Schema 时显式失败。
47. Important immutable data 保存 content_hash。
48. Runtime Time 与 Wall Clock 分离。
49. 使用 stable opaque IDs。
50. 索引围绕真实查询。
51. Memory semantic search 与 source-of-truth metadata 分离。
52. Fork 前历史共享，Fork 后独立演化。
53. Branch 不复制 Memory / State 全历史。
54. GC 基于 Roots / References。
55. v0.1 不急于自动 GC。
56. Tick Critical Commit 尽量一个 SQLite Transaction。
57. Current Pointer 尽量最后发布。
58. External Action 不属于 DB Rollback。
59. External / LLM Result 使用 Journal / Correlation 支持 Retry。
60. Nondeterministic Input Fact 与 Committed Life State 生命周期分离。
61. 不使用巨大单一 `agent_state` Blob。
62. 不过度范式化心理模型。
63. 使用 Generic Versioned JSON + 必要 Specialized Store。
64. Persistence 分 Core State / Historical / Runtime / Auxiliary。
65. Source-of-Truth 与 Derived Data 明确分离。
66. Persistence 实现按 Vertical Slice 分批完成。

状态：

```text
Architecture Decision:
Persistence Schema v0.1

Status:
Accepted
```

---

## Architecture Decision #16C：Public API / CLI【已敲定】

### 核心原则

Public API 必须表达：

> **用户想对一个数字生命做什么。**

而不是暴露：

> **Runtime 内部如何实现。**

AnimaFlux v0.1 采用小型 Facade API，隐藏：

```text
StateResolver
StateOwner
StateStore
Transaction
PluginManager
CommitJournal
```

等内部机制。

---

### 16C.1 API Layers

Public API 分为三层：

```text
1. Life User API
2. Inspection / Research API
3. Plugin Development API
```

三层不混用。

---

### 16C.2 `AnimaFlux` Facade

`AnimaFlux` 是应用级框架入口。

概念使用：

```python
app = AnimaFlux.from_config("configs/normal.yaml")
```

内部负责：

```text
Load Config
Plugin Discovery
Capability Resolution
Runtime Plan
Persistence
LLM / Environment Provider
```

普通用户不直接操作 RuntimeBuilder / PluginManager。

---

### 16C.3 `LifeHandle`

`create_life()` 返回安全生命操作入口：

```text
LifeHandle
```

Public API 可简称 `Life`。

用户不直接获得可变 AgentState。

---

### 16C.4 Create Life

概念 API：

```python
life = await app.create_life(
    bootstrap=...
)
```

内部完成：

```text
technical agent id
main branch
13 Core State initialization
provenance
scheduler
random state
initial versions
initial commit
optional genesis checkpoint
```

用户不手工初始化各 State Owner。

---

### 16C.5 Runtime Config vs Character Bootstrap

正式区分：

```text
Runtime Config
≠
Character Bootstrap
```

Runtime Config 描述：

```text
plugins
persistence
LLM
environment
runtime policy
```

Character Bootstrap 描述：

```text
who this life initially is
initial identity
initial traits
important relations
scenario assumptions
provenance
```

---

### 16C.6 Step / Advance

`step()`：

> 执行一个 Tick。

`advance()`：

> 让 Runtime Time 前进一段时间，由 Time Policy / Scheduler 决定压缩或细化执行。

禁止公开任意：

```text
set_time()
```

绕过生命周期更新。

---

### 16C.7 Observation Input

通用外部输入统一通过：

```python
await life.observe(observation)
```

Observation 进入 Environment / Input Boundary。

它不能直接修改 Belief / Emotion / Goal 等 State。

---

### 16C.8 Human Communication Convenience API

Human Interaction 提供：

```python
turn = await life.send_text("...")
```

其内部必须经过：

```text
HumanInteractionAdapter
→ Communication Observation
→ Perception
→ Retrieval
→ Appraisal
→ Internal Dynamics
→ Goal Review
→ Decision
→ Communication
→ Action Result
```

`send_text()` 绝不等于 `llm.chat()`。

---

### 16C.9 TurnResult

`send_text()` 返回结构化：

```text
TurnResult
├── text
├── tick_id
├── runtime_time
├── action_result
├── committed
└── trace_ref optional
```

普通用户主要使用 `text`。

高级用户可追踪 Trace。

---

### 16C.10 Streaming

v0.1 不直接把未经 Validation 的 LLM Token 实时输出给用户。

默认：

```text
Generate
→ Validate
→ Commit / Dispatch
→ Present
```

可以对已验证文本做 UI chunk streaming。

真正 incremental validated token streaming 留作未来扩展。

---

### 16C.11 Inspect API

提供只读 Inspection：

```text
State View
Goals
Memory inspection
Timeline
Trace
```

返回 Immutable View，不返回可变内部 State。

Inspection 必须遵守：

```text
Operator
Researcher
Life
```

Observer Scope。

---

### 16C.12 No Direct State Mutation

Public API 禁止：

```text
set_state()
direct relationship mutation
raw emotion field mutation
raw belief mutation
```

研究实验若需施加影响，应通过：

```text
Research Event
Research Influence
Test Fixture
```

并仍经过 Owner / Version / Trace。

Raw State 修改仅属于 Migration / Recovery 内部工具。

---

### 16C.13 Checkpoint

提供：

```python
checkpoint = await life.checkpoint(...)
```

返回 `CheckpointRef`。

用户不需要理解 Commit Map / StateVersion 细节。

---

### 16C.14 Restore

Restore 推荐由 App 层重新构建 Runtime：

```python
life = await app.restore(checkpoint)
```

而不是简单原对象原地回退。

Restore 包括：

```text
plugin/schema compatibility
scheduler
random state
environment fingerprint
runtime reconstruction
```

---

### 16C.15 Restore / Replay / Branch Separation

Public API 必须保持：

```text
RESTORE
REPLAY
BRANCH / RESIMULATE
```

语义分离。

Restore：

> 延续原生命。

Replay：

> 只读历史重放。

Branch：

> 从历史点产生另一条人生。

---

### 16C.16 Replay

Replay Session 是 read-only。

允许：

```text
inspect
timeline
trace
step-through
```

禁止：

```text
send_text
new external action
new state commit
```

修改历史必须 Branch / Resimulate。

---

### 16C.17 Branch

Branch API 从 Checkpoint / Commit Fork 新 Life Branch。

返回对象仍然表现为 `LifeHandle`，但 branch_id 不同。

Fork 前共享历史，Fork 后独立演化。

Public API 不暴露底层 Version Sharing 细节。

---

### 16C.18 Plugin Selection

普通用户通过：

```text
Config / Profile / Override
```

选择 Plugin / Provider。

不直接操作 PluginManager。

运行中不提供普通 Hot Swap API。

---

### 16C.19 Research Overrides

Research Profile 可以：

```text
override emotion owner
override appraisal provider
override decision provider
```

但应创建新的 Runtime / Branch 或在安全 Pause / Restart 边界生效。

Override 必须进入 RuntimePlan / Environment Fingerprint。

---

### 16C.20 Plugin Developer API

第三方 Plugin Developer 使用：

```text
contracts.*
PluginManifest
StateOwner Protocol
Process Protocol
Capability Protocol
EnvironmentAdapter Protocol
```

与普通 Life User API 分开文档。

---

### 16C.21 API Stability Levels

正式区分：

```text
Public Stable API
Extension Contract API
Internal API
```

Public Stable 例如：

```text
AnimaFlux
Life / LifeHandle
Observation
CheckpointRef
BranchRef
```

Extension API 主要为 `animaflux.contracts.*`。

Runtime / persistence implementation details 属于 Internal API。

---

### 16C.22 Runtime Lifecycle

Public Runtime Lifecycle 可以支持：

```text
pause
resume
close
open
```

但保持用户体验简单。

`create_life()` 不要求用户手工完成 initialize/start 多阶段。

---

### 16C.23 Pause / Close / Death

正式区分：

```text
PAUSED
≠
DEAD

Runtime CLOSED
≠
Life DEAD
```

死亡仍由 Body.vital_status 权威决定。

---

### 16C.24 Open Existing Life

提供：

```python
life = await app.open_life(agent_id, ...)
```

加载最新 Committed State / selected branch。

若 Plugin / Schema 不兼容：

```text
explicit Compatibility Error
```

不能静默猜测。

---

### 16C.25 History / Timeline

提供领域中立历史查询：

```text
events
timeline
trace
```

而不是暴露 SQL。

默认 Timeline 面向人类可读。

Research Mode 可显示：

```text
node ids
state versions
source refs
llm_call ids
```

---

### 16C.26 Memory Inspection vs Agent Recall

正式区分：

```text
Research / Operator Memory Inspection
≠
Agent Memory Retrieval
```

普通交互中 Agent 想回忆必须走 Cognitive Retrieval。

外部 Inspector 不应被误当作 Agent 自己的记忆能力。

---

### 16C.27 No Standalone `decide()`

普通 Life API 不公开：

```text
life.decide()
```

绕过 Perception / Appraisal / Goal Review。

Decision 只能由 Life Loop 在合法 Context 中执行。

---

### 16C.28 Reflection Request

若需要手动请求 Reflection，Public API 应表达：

```text
request reflection
```

本质上提交 CognitiveIntent / Scheduler Request。

不直接暴露 ReflectionProcess 内部执行。

---

### 16C.29 CLI

CLI 是 Python Public API 的 Shell，不直接操作内部 DB。

建议命令分组：

```text
life
interact
history
checkpoint
plugin
```

主要覆盖：

```text
create/open/status/step/advance/pause/resume
chat/observe
timeline/events/trace/inspect
checkpoint/restore/branch/replay
plugin list/validate/plan
```

---

### 16C.30 Plugin Plan / Validate

CLI 支持离线：

```text
plugin plan
plugin validate
```

提前发现：

```text
missing capability
owner conflict
version mismatch
permission issue
dependency cycle
```

避免 Runtime 启动一半才失败。

---

### 16C.31 Config-first Public Setup

普通配置以 YAML Profile 为主。

Python Override 用于少量研究 / 测试覆盖。

所有影响 Replay 的 Override 必须写入 RuntimePlan / Fingerprint。

---

### 16C.32 Dynamic Config

v0.1 不构建复杂 Runtime Hot Config 系统。

未来可动态调整：

```text
LLM Budget
Observability Level
部分 Runtime Policy
```

但重要变化必须被记录。

Static Owner / Persistence / Plugin Version 不可随意原地修改。

---

### 16C.33 Export

Agent Export 与 Checkpoint 分离。

v0.1 保留 Export API 方向，但不强制实现完整 Portable Life Package。

---

### 16C.34 REST / Web UI

v0.1 Core 不强制：

```text
REST server
WebSocket server
Authentication
Frontend
User management
```

先提供：

```text
Python API
CLI
HumanInteractionAdapter
```

外部应用可在其上构建 Web / Game / App。

---

### 16C.35 Intent-based API

Public API 以：

```text
create
open
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

等用户意图为中心。

不公开：

```text
set_current_pointer
insert_event
resolve_round
commit_state_ref
```

内部机制 API。

---

### 16C.36 Public API / CLI v0.1 最终原则

正式接受：

1. Public API 使用小型 Facade。
2. 普通 Life API / Research API / Plugin Development API 分层。
3. `AnimaFlux` 是应用级入口。
4. `LifeHandle` 是单生命安全操作入口。
5. `create_life()` 隐藏 13 State 初始化细节。
6. Runtime Config 与 Character Bootstrap 分离。
7. `step()` 表示一个 Tick。
8. `advance()` 表示按 Runtime Time Policy 前进。
9. 不公开任意 `set_time()`。
10. 通用外部输入使用 `observe()`。
11. Human 对话使用 `send_text()` Convenience API。
12. `send_text()` 必须经过完整 Cognition。
13. `send_text()` 不等于 `llm.chat()`。
14. TurnResult 返回文本 + Tick / Trace 等有限元数据。
15. v0.1 不输出未经 Validation 的 Token Stream。
16. Inspect 返回 Immutable View。
17. Inspect 遵守 Observer Scope。
18. Public API 不允许直接 State Mutation。
19. Research Injection 仍需经过 Owner / Trace。
20. Raw State 修改只属于 Migration / Recovery。
21. Checkpoint 提供高层 Ref。
22. Restore 重建 Runtime。
23. Restore / Replay / Branch 语义分离。
24. Replay read-only。
25. 修改历史必须新 Branch / Resimulation。
26. Branch 对用户隐藏底层 Version Sharing。
27. Plugin Selection 主要走 Config / Profile。
28. 普通 API 不操作 PluginManager。
29. Research Override 进入 RuntimePlan / Fingerprint。
30. Plugin Developer API 与 Life User API 分开。
31. 区分 Stable Public / Extension / Internal API。
32. Pause / Close / Death 语义分离。
33. 支持 open existing life。
34. Schema incompatible 时显式失败。
35. History / Timeline 提供领域中立 Query。
36. Memory Inspection 与 Agent Recall 分离。
37. 普通 API 不暴露 standalone decide。
38. Reflection 使用 request / intent，不直接运行内部 Process。
39. CLI 只是 Public API Shell。
40. CLI 不直接写数据库。
41. CLI 支持 plugin plan / validate。
42. 配置以 YAML Profile 为主。
43. Python Override 用于少量实验。
44. 重要 Override 必须可追踪。
45. v0.1 不做复杂 Runtime Hot Config。
46. Agent Export 与 Checkpoint 分离。
47. v0.1 不强制 REST / Web UI。
48. Public API 采用 Intent-based 设计。
49. 内部 Runtime Mechanism 不进入普通 Public API。
50. Public API 应让开发者感觉在操作一个持续存在的生命，而不是调用一组 Agent 内部函数。

状态：

```text
Architecture Decision:
Public API / CLI v0.1

Status:
Accepted
```

---

## Architecture Decision #16D：Testing Strategy【已敲定】

### 核心目标

AnimaFlux 的测试不仅验证：

```text
functional correctness
```

还必须验证：

```text
architectural correctness
life semantics invariants
```

一个系统即使“看起来像人”，但如果：

```text
Reflection 直接改 Personality
Communication 越过 Decision
Replay 重新调用 LLM
Agent A 读取 Agent B 私有 State
```

仍然属于失败。

---

### 16D.1 Test Layers

正式采用：

```text
Unit Tests
Contract Tests
Integration Tests
Replay / Branch Tests
Scenario / Life Tests
```

并用：

```text
Invariant Tests
```

横穿所有层。

---

### 16D.2 Framework Tests vs Default Model Tests

正式区分：

```text
Framework Tests
```

验证：

```text
Runtime
Contract
Persistence
Replay
Branch
Permission
Plugin isolation
Transaction
```

以及：

```text
Default Model Tests
```

验证官方：

```text
Emotion
Personality
Appraisal
Decision
...
```

的具体规则。

第三方 Plugin 只要求通过 Framework Contract，不要求复制官方心理模型行为。

---

### 16D.3 StateOwner Unit Tests

StateOwner 必须验证：

```text
same input → same output
no in-place mutation
namespace ownership
schema validation
bounded update
causal metadata
```

StateOwner 应保持 sync / deterministic / pure-ish。

---

### 16D.4 Slow-state Tests

Personality / Value / Self / Narrative 等 Slow State 必须验证：

```text
ordinary event
→ no massive jump

long-term consistent evidence
→ bounded development
```

Age / DevelopmentContext 可以调节 Plasticity，但不能退化成裸年龄硬编码。

---

### 16D.5 Developmental Context Tests

必须长期保留：

```text
Same Age, Different Experience
Different Age, Same Relevant Experience
Experience ≠ Competence ≠ Self-Efficacy
```

三类回归测试。

核心目标：

> **系统因真实 Domain Experience 不同而表现不同，而不是因裸 age 数字自动产生“成熟/幼稚”等刻板结论。**

---

### 16D.6 Contract Tests

State Owner / Process / Capability / Environment / LLM Provider 都需要官方 Contract Test Suite。

Contract Test 验证：

```text
协议
权限
只读性
Schema
State ownership
failure contract
source refs
```

而不是要求不同实现给出相同心理结果。

---

### 16D.7 Capability Immutability

Capability 返回的 View 必须只读。

修改 View 不得改变真实 State。

---

### 16D.8 Process Mutation Boundary

Cognitive Process 不能直接写任何 Core State。

测试应确保 ProcessContext 不暴露：

```text
raw StateStore
DB connection
TransactionCoordinator
PluginManager
unrestricted write API
```

---

### 16D.9 Integration Tests

重点验证完整小链路，例如：

```text
Observation
→ Perception
→ Appraisal
→ Influence
→ Resolver
→ Owner
→ Working State
→ Commit
```

同时检查：

```text
source refs
state versioning
commit map
causal trace
```

---

### 16D.10 Communication Integration

Human Communication 不只检查最终字符串。

必须验证：

```text
Communication Observation
→ Perception
→ Retrieval
→ Appraisal
→ Internal Dynamics
→ Goal Review
→ Decision
→ CommunicativeIntent
→ Language Realization
→ Validation
→ Action Result
```

---

### 16D.11 Knowledge Boundary

Agent 不可访问未被 Observation / Memory / Belief 等主观路径获得的信息。

Runtime Objective Event Log 不得偷偷修正 Agent 当前认知。

Multi-agent 测试必须检查：

```text
LLM ContextManifest
```

中没有其他 Agent 私有 State 引用。

---

### 16D.12 Misperception

允许 mechanistic misperception。

测试必须证明：

```text
Objective Reality
≠
PerceivedEvent
```

并且在新 Evidence 到来之前，Runtime 不会用 god-view 自动纠正。

---

### 16D.13 Memory Tests

正式验证：

```text
Event ≠ Memory
retrieval ≠ reconsolidation
forgetting ≠ delete
```

Retrieval 可以更新 `memory_runtime_state`，但不能偷偷修改 Memory Content Version。

Reconsolidation 必须创建新 Memory Version。

---

### 16D.14 Transaction / Rollback

必须使用 Failure Injection 验证：

```text
partial writes
commit failure
current pointer publish failure
```

均不会产生半提交生命状态。

Commit 失败：

```text
runtime time not advanced
old current pointers remain authoritative
```

---

### 16D.15 External Action Retry

场景：

```text
External Action succeeded
→ later DB commit failed
→ technical retry
```

第二次 Attempt 不得重复真实外部动作。

必须验证：

```text
external action count = 1
tick attempt count > 1 allowed
```

---

### 16D.16 LLM Retry Reuse

LLM 成功、后续 Tick 失败时：

```text
technical retry
→ reuse previous validated LLM result
```

而不是重新“思考一次”。

Scripted / Mock LLM 必须可以记录 call count。

---

### 16D.17 Exact Replay

Exact Replay 必须验证：

```text
no new LLM call
no environment access
no new Event
no new Memory
no new State Commit
```

Replay 比较：

```text
commit sequence
state version refs / hashes
important causal artifacts
```

而不只比较最终状态。

---

### 16D.18 Replay Golden Tests

固定：

```text
Input Journal
Random seed
Mock LLM outputs
```

形成稳定 Reference Scenario。

保存预期：

```text
commit hashes / version sequence
```

用于 Runtime Regression。

---

### 16D.19 Branch Isolation

Branch Test 验证：

```text
pre-fork versions shared
post-fork versions diverge
main branch unaffected
branch memories isolated after fork
```

Branch 创建不得复制完整历史。

---

### 16D.20 Determinism / Ordering

必须测试：

```text
same snapshot
same input
same random seed
same stored nondeterministic outputs
→ same result
```

并测试：

```text
stable influence ordering
serial vs parallel compute
```

在 Ordered Resolution 后结果一致。

---

### 16D.21 Migration

State Schema Migration 必须测试：

```text
old supported schema
→ current schema
```

不支持的旧 Schema 必须显式 `CompatibilityError`。

禁止静默猜测。

---

### 16D.22 Plugin Replacement

使用故意不同内部 Schema 的 Anti-Coupling Test Plugin。

只要提供标准 Capability，其他模块仍应运行。

用于发现：

```text
Framework / other Plugin
```

偷偷依赖 Default Plugin 私有字段。

---

### 16D.23 Environment / LLM Provider Replacement

Core Runtime 不能依赖具体：

```text
HumanInteractionAdapter
specific LLM SDK
```

Contract Test 使用 Fake / Mock Provider 验证可替换性。

---

### 16D.24 Communication Disclosure

Communication LLM 即使生成 forbidden claim，也必须被 Validation 拦截。

Intent / Knowledge / Disclosure Policy 是权威边界。

---

### 16D.25 Reflection

Reflection 只能产生：

```text
Evidence / Proposal
```

不能直接输出新的 Core State。

Counter-Evidence 必须有机会进入 Context。

同时不能把 Counter-Evidence 变成强制正面化。

---

### 16D.26 Scenario Tests

Scenario Test 不规定唯一心理答案。

测试：

```text
constraints
causal relevance
knowledge boundary
state ownership
meaningful differentiation
```

而不是：

```text
sadness must equal 0.8
```

同一事件对不同生命产生不同结果可以是正确行为。

---

### 16D.27 Same Event, Different Life

官方 Reference Profile 应包含：

```text
same external event
+
different memory/personality/relationship/experience
→ different appraisal / decision
```

的标志性测试。

---

### 16D.28 Life Stage Policy Replacement

用 Fictional / Alternative LifeStagePolicy 测试 Core Runtime。

Core 中不得散落：

```text
if age >= 18
```

等固定人类年龄规则。

---

### 16D.29 Time Skip / Scheduler

测试：

```text
RUN_ALL
RUN_ONCE
COALESCE
SKIP
```

Catch-up Policy。

对于声明支持 aggregation 的 deterministic dynamics，验证 compressed time 的 Contract。

---

### 16D.30 Death Lifecycle

Body.vital_status = DEAD 后：

```text
ordinary Goal Review / Decision
```

停止。

但：

```text
history
checkpoint
external consequences
other agents' state
```

仍然可存在。

Runtime close 不能被误判成死亡。

---

### 16D.31 LLM Budget / No-LLM

测试：

```text
budget exhausted
```

时 Process 正确 degrade / fallback。

使用 NoLLMProvider 时：

```text
Runtime starts
Tick commits
State evolves
Checkpoint works
Replay works
```

必须成立。

---

### 16D.32 Mock LLM as Default Testing Provider

绝大多数自动化测试使用：

```text
MockLLMProvider
ScriptedLLMProvider
```

真实远程 LLM 不作为 CI 的硬依赖。

Live LLM Test 只验证：

```text
schema
boundary
validation
intent fidelity
```

不要求逐字输出一致。

---

### 16D.33 Property / Fuzz Tests

Property-based Testing 适用于：

```text
Resolver ordering
bounded rounds
state invariants
immutable previous state
random legal inputs
```

Fuzz 可用于外部输入 Contract。

v0.1 可逐步引入，不要求第一天全部完成。

---

### 16D.34 Performance / Long-run Tests

v0.1 不测试百万 Agent。

重点测试：

```text
10k memories
1k~10k ticks
branch creation
restore
replay
SQLite commit latency
Copy-on-Write growth
```

防止明显 O(n²) 设计。

---

### 16D.35 Causal Trace / Timeline

重要 Decision 必须可反查关键链：

```text
Observation
→ Perception
→ Memory/Appraisal
→ Influence
→ State Change
→ Decision
```

Timeline 不同 Observer View 只改变展示粒度，不改变底层事实。

---

### 16D.36 Observability Invariance

相同：

```text
input
seed
LLM fixtures
```

下，开启 minimal / verbose Trace：

> 最终生命 State 必须一致。

Observability 不得改变语义。

---

### 16D.37 Test Fixtures

建议长期维护：

```text
blank_life
minimal_adult
novice_agent
experienced_agent
two_agent_private_knowledge
relationship_conflict
long_memory_history
dead_agent
```

Integration Fixture 尽量通过 Bootstrap / Event / Influence 建立状态，不直接 SQL 篡改。

---

### 16D.38 TestRuntimeBuilder

建议提供测试专用：

```text
TestRuntimeBuilder
```

组合：

```text
InMemory Store
Scripted LLM
Fixed Random Seed
Fake Environment
Failure Injection Backend
```

减少测试样板代码。

---

### 16D.39 Architecture Invariant Coverage

Coverage 不只看代码行覆盖率。

维护 Architecture Invariant Coverage，例如：

```text
Non-owner cannot mutate State
Replay no LLM call
Branch isolation
Memory retrieval != reconsolidation
Age != experience
Knowledge boundary
LLM retry reuse
External action idempotency
```

---

### 16D.40 Architecture Regression Suite

每次重大重构至少运行：

```text
Owner isolation
Capability immutability
Transaction rollback
Replay exactness
Branch isolation
Knowledge boundary
LLM retry reuse
External action idempotency
DevelopmentContext behavior
```

---

### 16D.41 Testing Strategy v0.1 最终原则

正式接受：

1. 测试 Functional Correctness + Architectural Correctness。
2. Unit / Contract / Integration / Replay-Branch / Scenario 五层。
3. Invariant Test 横穿所有层。
4. Framework Test 与 Default Psychology Test 分离。
5. 第三方 Plugin 不要求复制官方心理输出。
6. StateOwner 测 deterministic / immutable / ownership。
7. Slow State 测 bounded development。
8. Age / Experience 需要专门回归测试。
9. Same Age / Different Experience 必须表现可区分。
10. Different Age / Same Relevant Experience 不得自动刻板化。
11. Experience ≠ Competence ≠ Self-Efficacy。
12. Capability View 必须 immutable。
13. Process 不能直接写 State。
14. ProcessContext 不暴露 raw runtime internals。
15. Integration 测完整 causal chain。
16. Communication 不只测最终文本。
17. Knowledge Boundary 独立测试。
18. Misperception 必须允许存在。
19. Runtime 不使用 god-view 自动纠正 Agent。
20. Event ≠ Memory。
21. Retrieval ≠ Reconsolidation。
22. Forgetting ≠ Delete。
23. Transaction 必须 Failure Injection。
24. Commit 失败不得发布部分 State。
25. Runtime Time 只有 Commit 后推进。
26. External Action technical retry 不重复执行。
27. LLM technical retry 复用已成功 Result。
28. Exact Replay 不调用 LLM / Environment。
29. Replay 不产生新 State / Event / Memory。
30. Replay 比较历史序列，不只最终状态。
31. Replay Golden Test 固定 Input / Random / LLM Fixtures。
32. Branch Fork 前共享，Fork 后隔离。
33. 同输入 / Seed / Nondeterministic Output 应 deterministic。
34. Stable Ordering 必须测试。
35. Parallel Compute 不得改变 Ordered Resolution 结果。
36. Schema Migration 有显式兼容测试。
37. 使用 Anti-Coupling Plugin 测真正可替换性。
38. Environment / LLM Provider 可替换。
39. Communication Disclosure Validation 独立测试。
40. Reflection 只输出 Proposal / Evidence。
41. Counter-Evidence 不等于强制正面化。
42. Scenario Test 不规定唯一心理答案。
43. Same Event, Different Life 是官方标志性测试。
44. LifeStagePolicy 可替换。
45. Core 不硬编码固定年龄阈值。
46. Time Skip / Scheduler Catch-up 必须测试。
47. Death / Pause / Close 语义分离。
48. LLM Budget Exhausted 是合法状态。
49. No-LLM Runtime 必须能运行。
50. 自动化测试默认 Mock / Scripted LLM。
51. 远程 LLM 不作为 CI 硬依赖。
52. Property-based Testing 适合 Resolver / Invariant。
53. Fuzz 只作为补充。
54. v0.1 性能测试聚焦单一深度 Life。
55. 长期 Tick / Memory Growth 需要测试。
56. Causal Trace 关键链必须可反查。
57. Observability 不得改变生命语义。
58. Test Fixtures 区分 Unit / Integration。
59. 建议 TestRuntimeBuilder。
60. 维护 Architecture Invariant Coverage。
61. 重大重构必须跑 Architecture Regression Suite。

状态：

```text
Architecture Decision:
Testing Strategy v0.1

Status:
Accepted
```

---

## Architecture Decision #16E：v0.1 Demo【已敲定】

### 核心目标

v0.1 Demo 不追求“大而全”，而要证明：

> **AnimaFlux 中的数字生命是持续存在、会积累经历、会形成记忆与关系、会因过去而改变，并且人生可以被保存、解释、重放与分支。**

---

### 16E.1 Demo Scope

v0.1 只做：

```text
Single Deep Digital Life
+
Human User
+
Minimal Scenario Environment
```

不做：

```text
AI Town
massive multi-agent
world simulator
city / economy / inventory / combat
```

继续坚持：

> **AnimaFlux models the life, not the universe.**

---

### 16E.2 Demo Character

官方 Demo 使用一个持续存在的数字生命。

Bootstrap 至少包含：

```text
Identity
Life Stage / Role
Personality
initial Values
initial Goals
important Relationship with Human User
limited prior Memories
initial Domain Experience
```

年龄只是事实背景，不作为人格捷径。

---

### 16E.3 Story Line A：Experience Growth

第一条主线：

```text
第一次正式公开汇报
→ Memory / Appraisal / Emotion / Self-Efficacy / Experience
→ Time Skip
→ 多次相关经历
→ 再次面对类似公开汇报
```

目标：

> **展示 Same Person, Different Experience。**

---

### 16E.4 First Presentation

第一次面对正式公开汇报时：

```text
public_speaking experience = low
novelty = high
uncertainty = high
goal relevance = high
self relevance = high
```

具体 Emotion / Decision 由 Runtime / Default Model 产生。

Scenario 不写死：

```text
must be anxious
must be afraid
```

---

### 16E.5 Human Support

Human User 可以提供支持性交流。

它必须走完整：

```text
HumanInteractionAdapter
→ Observation
→ Perception
→ Retrieval
→ Appraisal
→ Internal Dynamics
→ Goal Review
→ Decision
→ Communication
```

Support 可以成为 Relationship / Emotion / Memory Evidence，但不能直接修改 State。

---

### 16E.6 Presentation Result

Scenario Environment 提供结构化客观结果，例如：

```text
completed
feedback
difficult questions
visible outcome
```

Agent 只通过可见 Observation 感知。

随后形成：

```text
Goal progress
Memory
Self-Efficacy Evidence
Experience accumulation
World Model / Procedural knowledge
```

---

### 16E.7 Time Skip

使用：

```text
advance()
Time Skip
Scheduler catch-up
compressed events
```

推进数月。

不模拟大量空 Tick。

---

### 16E.8 Later Similar Event

后续再次面对类似公开汇报。

此时允许：

```text
Experience higher
Novelty lower
Coping support richer
Relevant memories richer
Procedural Memory available
Decision Fast Path more likely
```

重点证明：

> **人生经历改变了后续认知方式。**

不是通过 Demo 特例写死。

---

### 16E.9 Development Context Inspection

Demo 可以展示：

```text
Chronological Age
Life Stage
Relevant Domain Experience
Role Context
```

但不输出统一“成熟度分数”。

---

### 16E.10 Story Line B：Relationship Transition

第二条主线：

Human User 表示：

```text
未来可能无法经常联系
```

必须完整经过：

```text
Perception
Memory Retrieval
Appraisal
Emotion / Drive
Goal Review
Decision
Communication
```

并自然调用 Relationship / Belief / Self / Narrative 等相关状态。

---

### 16E.11 Causal Why View

Demo 必须支持：

```text
Why did this life respond this way?
```

通过 Causal Trace 展示：

```text
Observation
→ PerceivedEvent
→ Relevant Memories
→ Relationship / Goal / Belief context
→ Appraisal
→ State Influences
→ Decision
→ Communication
```

而不是让 LLM事后自由编一个理由。

---

### 16E.12 Checkpoint

在关键关系节点创建：

```text
Checkpoint
```

作为可恢复 / 可分支的人生节点。

---

### 16E.13 Two Branches

从同一 Checkpoint 创建至少两条 Branch：

```text
Branch A
→ temporary distance / continued contact

Branch B
→ long-term separation
```

Fork 前共享历史。

Fork 后：

```text
Belief
Emotion
Goal
Relationship
Memory
Narrative
```

可以独立演化。

---

### 16E.14 No Scripted Psychology

Scenario 只能提供：

```text
objective events
observations
action results
time progression
```

禁止直接写：

```text
Mira should feel sad
trust -= 0.3
narrative becomes loss
```

所有心理变化必须经过 Runtime / Owner。

---

### 16E.15 Reflection / Narrative

至少展示一次低频 Reflection / Narrative Update。

用于证明：

> Agent 不只存事件，还会在长期尺度上重新组织人生意义。

但不为了 Demo 强行快速修改 Personality / Value。

---

### 16E.16 Persistence Across Process Restart

Demo 必须展示：

```text
run
interact
commit
close process
restart
open_life()
continue
```

数字生命不能随着 Python 进程结束而消失。

不能用完整聊天 transcript 重新塞 Prompt 假装记忆。

---

### 16E.17 Selective Memory / Forgetting

至少展示：

```text
important event remembered
low-significance detail not necessarily remembered
```

Researcher 可从 Event Log 看到客观历史。

Agent 不一定能 Retrieval 到。

正式展示：

```text
Reality
≠
Memory
```

---

### 16E.18 Unknown / Knowledge Boundary

至少展示一次：

```text
Agent does not know
```

当信息没有进入 Agent 的可知路径时，LLM 不得通过世界常识 /猜测补成内部知识。

---

### 16E.19 Memory Reconstruction

错误记忆 / Reconsolidation 不作为 v0.1 主 Demo 必需项。

第一版先展示：

```text
memory formation
selective retrieval
forgetting / accessibility
confidence
```

---

### 16E.20 Core State Presentation

13 Core State 不需要逐个做功能秀。

State 应通过故事自然体现。

World Model 等可参与后台，不需要单独 UI showcase。

---

### 16E.21 Body Scope

Body 只提供轻量真实 Context，例如：

```text
fatigue
sleep
physical readiness
```

不把 Demo 扩展成生理模拟器。

---

### 16E.22 Demo UI

v0.1 使用 CLI 即可。

不强制 Web UI。

建议提供：

```text
Life Summary
Timeline
Development Context
Why / Causal Trace
Checkpoint / Branch
Replay
```

---

### 16E.23 Deterministic / Interactive Modes

Demo 支持两种模式：

```text
deterministic
interactive
```

Deterministic：

```text
Scripted LLM
fixed random seed
reference scenario
```

用于：

```text
CI
tutorial
replay demonstration
architecture verification
```

Interactive：

```text
hybrid profile
real LLM provider optional
human interaction
```

两种模式共享同一 Life Runtime。

---

### 16E.24 Real vs Fake Components

Demo 中必须使用真实实现：

```text
Runtime
State Resolver
Persistence
Memory
Checkpoint
Branch
Replay
Trace
```

可以 Fake：

```text
Environment Provider
LLM Provider
```

因为它们本来就是边界 Provider。

---

### 16E.25 Reference Scenario

官方 Demo Scenario 同时作为：

```text
Reference Integration Scenario
```

用于 CI / Regression。

Demo 与测试共享事实 Scenario，但不共享写死心理结果。

---

### 16E.26 v0.1 Success Criteria

完整闭环：

```text
Create
→ Interact
→ Persist
→ Restart
→ Remember selectively
→ Accumulate experience
→ React differently later
→ Relationship changes
→ Checkpoint
→ Branch
→ Different futures
→ Exact Replay
→ Explain Why
```

全部成立即可认为 v0.1 Demo 成功。

---

### 16E.27 v0.1 Demo 最终原则

正式接受：

1. v0.1 只做单一深度 Digital Life。
2. 不做 AI Town / 大型 Multi-Agent。
3. Human User 是主要社会对象。
4. 外部世界使用极小 Scenario Environment。
5. Scenario 只提供客观 Event / Observation。
6. Demo 重点证明 Persistent Life。
7. 第一条主线展示 Experience Growth。
8. 使用两次相似 Public Presentation Event。
9. 第一次应体现低相关 Domain Experience。
10. 后续事件利用真实 Memory / Experience / Procedural Knowledge。
11. 成长不得由 Demo 特例写死。
12. 年龄不是认知差异快捷变量。
13. Human Support 经过完整 Cognition。
14. 重大经历形成长期 Memory。
15. 时间推进使用 Time Skip。
16. 第二条主线展示 Relationship Transition。
17. 关系消息必须经过完整认知链。
18. Demo 必须支持 Causal Why View。
19. 关键节点创建 Checkpoint。
20. 从同一 Checkpoint 至少创建两个 Branch。
21. Fork 前共享，Fork 后独立。
22. Branch 心理差异必须由 Runtime 自然产生。
23. 至少展示一次 Reflection / Narrative 慢变化。
24. 不为了 Demo 强行快速改 Personality / Value。
25. Body 只做轻量 Context。
26. DevelopmentContext / DomainExperience 可 Inspection。
27. 必须演示程序重启后继续生命。
28. 使用真实 SQLite Persistence。
29. 不使用完整聊天记录重灌 Prompt 假装记忆。
30. 展示 Selective Memory。
31. 至少展示一次“不记得”。
32. 至少展示一次“不知道”。
33. Agent 不可读取 Objective Event Log 作为神谕。
34. Memory Reconstruction 不作为主 Demo 必需。
35. 13 Core State 不逐个做功能秀。
36. State 通过故事自然体现。
37. CLI 足够。
38. v0.1 不强制 Web UI。
39. 提供 Life Summary。
40. 提供 Human-readable Timeline。
41. 提供 Why / Causal Trace。
42. 支持 deterministic demo mode。
43. 支持 hybrid interactive mode。
44. Deterministic mode 使用 Scripted LLM + fixed seed。
45. Interactive mode 可接真实 LLM。
46. 两种模式共用同一 Runtime。
47. Demo 不依赖真实远程 LLM 才能运行。
48. v0.1 不需要第二个完整 Agent。
49. v0.1 不做无限 autonomous daemon。
50. manual step / advance / scenario / interaction 为主。
51. Runtime / Persistence / Branch / Replay 必须是真实现。
52. Environment / LLM 可以 Fake。
53. Demo Scenario 同时是 Reference Integration Scenario。
54. 成功标准是 Create → Live → Persist → Grow → Branch → Replay → Explain。
55. Demo 核心叙事是：过去会改变现在，同一个现在也可以走向不同未来。

状态：

```text
Architecture Decision:
v0.1 Demo

Status:
Accepted
```

---

# Architecture Decision #16F：Implementation Roadmap【已敲定】

## 16F.1 总体实施原则

v0.1 不采用“13 个 State 全部实现完，再第一次运行”的开发方式。

正式采用：

```text
Minimal Runtime
→ Small Vertical Slice
→ Persistence
→ Cognition
→ Memory / Experience
→ Social / Motivation
→ Slow Development
→ Replay / Branch
→ Public Demo
→ Hardening
```

每个阶段都必须保持系统可运行，并用测试 Gate 阻止错误地基继续向后传播。

---

## 16F.2 开发阶段

### P0 — Project Skeleton

目标：

```text
可安装
可 import
可测试
有最小配置与项目骨架
```

主要交付：

```text
pyproject.toml
src/animaflux/
tests/
configs/
examples/
```

禁止提前实现：

```text
13 个空 Plugin
完整数据库
LLM 业务逻辑
Web UI
LangChain / LangGraph Core
```

完成标准：

```text
pip install -e .
pytest
import animaflux
```

全部成功。

---

### P1 — Core Contracts

实现最小公共协议：

```text
ID
RuntimeTime
Event
Observation
Influence
Evidence
ProcessResult
StateOwner
Capability
StateView
PluginManifest
```

重点：

```text
immutable contract
typed boundary
domain-neutral
```

Contracts 中不得出现具体心理模型字段。

完成标准：

```text
Event / Influence / View immutable
Process 不具备 direct state mutation
StateOwner Protocol 可被测试实现使用
```

---

### P2 — Kernel

实现：

```text
RuntimeClock
RandomService
CapabilityRegistry
NamespaceRegistry
Scheduler
PluginManager
```

Kernel 不理解 Emotion / Memory / Goal 等生命语义。

必测：

```text
duplicate state owner
missing required capability
dependency cycle
scheduler stable ordering
fixed-seed reproducibility
```

---

### P3 — State Runtime

先使用测试 State 和 InMemory Backend 跑通：

```text
Committed State
→ Tick Snapshot
→ Influence
→ State Resolver
→ State Owner
→ Working State
→ Commit / Rollback
```

必须实现：

```text
one namespace one owner
stable influence ordering
bounded resolver rounds
secondary influence
deferred influence contract
immutable committed state
rollback
```

这是第一道硬 Gate。

---

### P4 — SQLite Transaction

第一批 Persistence 只实现：

```text
life_agent
life_branch
state_version
state_current
tick_attempt
commit_journal
commit_state_ref
```

核心验证：

```text
State Version
→ Commit
→ Process Exit
→ Restart
→ Restore Same State
```

必须进行 Failure Injection，并证明半提交不会发布。

---

### P5 — First Life Slice

第一批真实生命 State：

```text
Identity
Body
Emotion
```

Identity 最小实现：

```text
birth_time
current name
active roles
chronological age derived view
```

Body 最小实现：

```text
energy
fatigue
sleep
sensory capability
vital_status
```

Emotion 最小实现：

```text
episodes
intensity
valence/arousal
mood
decay
```

完成后系统首次成为一个可跨进程持续存在、会随时间变化的 Life Runtime。

---

### P6 — Perception & Appraisal

实现：

```text
NullEnvironmentAdapter
ScenarioEnvironmentAdapter

Observation
→ Perception
→ PerceivedEvent
→ Appraisal
→ Emotion Influence
→ EmotionOwner
```

同时实现 LLM 基础设施：

```text
LLMCapability
LLMCallRequest
LLMCallPolicy
ScriptedLLMProvider
NoLLMProvider
Structured Output Validation
```

此阶段默认不依赖真实远程 LLM。

---

### P7 — Memory & Experience

实现 Specialized Memory Store：

```text
memory_entry
memory_version
memory_runtime_state
```

实现：

```text
Memory Formation
Memory Retrieval
minimal Reconsolidation
```

第一版 Retrieval 优先：

```text
metadata
recency
importance
person relevance
goal relevance
keyword
```

不强制 Vector DB。

同时实现：

```text
DevelopmentContextBuilder
LifeStageView
ExperienceProfileView
```

必须通过：

```text
Same Age, Different Experience
Different Age, Same Relevant Experience
Experience ≠ Competence ≠ Self-Efficacy
```

测试。

这是第二道关键硬 Gate。

---

### P8 — Motivation & Social Cognition

加入：

```text
Drive
Belief
Goal
Relationship
```

以及：

```text
Decision
minimal Planning
Communication
HumanInteractionAdapter
```

形成第一条完整 Human Cognition Loop：

```text
Human Message
→ Perception
→ Retrieval
→ Appraisal
→ Emotion / Drive / Belief / Relationship
→ Goal Review
→ Decision
→ CommunicativeIntent
→ Communication
→ Human
```

此阶段再接真实 OpenAI-compatible / other LLM Provider。

---

### P9 — Slow Self Development

补齐：

```text
Personality
Value
World Model
Self Model
Narrative
Reflection
```

实现重点：

```text
slow-state bounded update
DevelopmentContext plasticity
Current / Ideal / Feared Self
World Model as subjective structure, not simulator
Narrative themes / chapters / turning points
Reflection outputs proposals/evidence only
```

P9 完成后：

```text
13 Core States
6 Core Cognitive Processes
Development Context
Human Communication
```

全部存在。

之后禁止继续增加 v0.1 心理子系统。

---

### P10 — Replay & Branch

实现：

```text
Checkpoint
Restore
Input Journal
LLM Call Record
Artifact Store
Causal Trace persistence
Exact Replay
Deterministic Core Re-execution
RESIMULATE
Life Branch
```

实现顺序：

```text
Exact Replay first
→ Branch second
```

完成标准：

```text
Original Run: LLM calls = N, Environment calls = M
Exact Replay: LLM calls = 0, Environment calls = 0

commit sequence / hashes match
```

Branch 必须满足：

```text
pre-fork shared
post-fork isolated
main not polluted
```

这是第三道硬 Gate。

---

### P11 — Public API / CLI / Official Demo

实现：

```text
AnimaFlux
LifeHandle

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
```

实现官方 Reference Demo：

```text
First presentation
→ experience accumulation
→ later similar presentation

Important relationship transition
→ checkpoint
→ Branch A / Branch B

Restart
→ open_life
→ selective memory
→ replay
→ why / causal trace
```

---

### P12 — Hardening & v0.1 Release

不增加新的 Core 功能。

只进行：

```text
bug fixing
architecture regression
migration tests
long-run tests
performance
documentation
examples
packaging
release
```

重点规模：

```text
1k–10k ticks
~10k memories
multiple checkpoints
several branches
SQLite growth
replay
```

不以百万 Agent 并发为 v0.1 目标。

---

## 16F.3 重大里程碑

### Milestone A — Runtime Lives

P3 完成：

```text
State
→ Influence
→ Owner
→ Resolve
→ Commit
```

### Milestone B — Persistent Life

P5 完成：

```text
Identity
Body
Emotion
Time
Persistence
```

可跨进程继续。

### Milestone C — Cognitive Life

P8 完成：

```text
Perception
Memory
Appraisal
Emotion
Drive
Goal
Relationship
Decision
Communication
```

形成真正可交互生命。

### Milestone D — Evolving Life

P10/P11 完成：

```text
Experience
Self
Narrative
Reflection
Persistence
Replay
Branch
Explainability
```

v0.1 核心论点成立。

---

## 16F.4 阶段 Gate

每阶段执行：

```text
Implementation
→ Unit Tests
→ Contract / Integration Gate
→ Phase Notes
→ Stable Milestone
→ Next Phase
```

P3 / P4 / P7 / P10 为硬 Gate。

阶段未稳定时不得用“先往后写”绕过问题。

---

## 16F.5 Boundary-first Development

外部 Boundary 统一：

```text
LLM
Environment
Embedding
```

采用：

```text
Fake / Mock first
→ Core stable
→ Real provider later
```

禁止第一天就把 Runtime Debug 和真实模型 / 网络不确定性混在一起。

---

## 16F.6 No Premature Optimization

v0.1：

```text
SQLite first
metadata retrieval first
single deep life first
```

不因为未来假设提前引入：

```text
Redis
Kafka
Qdrant cluster
Neo4j
microservices
distributed runtime
massive multi-agent scaling
```

---

## 16F.7 Scope Freeze

从本决策生效后：

> **只填完当前已经确定的 AnimaFlux 边界，不再扩边界。**

新的：

```text
Skill State
Culture Model
Dream System
Advanced Attachment Model
Moral Reasoning System
World Simulator
```

等概念默认进入：

```text
v0.2+ backlog
```

只有在真实编码中发现：

```text
current design is technically impossible
current decisions contradict each other
core correctness would be broken
```

时，才允许修改 v0.1 Architecture。

---

## 16F.8 Completion Definition

v0.1 的完成条件不是：

> 再也想不到新的功能。

而是：

> **当前冻结的 13 Core States、6 Core Cognitive Processes、Runtime Wiring、Persistence、Replay/Branch、Public API、Testing 与 Reference Demo 全部实现并验证。**

正式停止条件：

```text
AnimaFlux v0.1 Architecture is complete
when the frozen architecture is implemented and verified.
No additional conceptual subsystem is required for v0.1.
```

---

## 16F.9 Priority

### MUST

```text
State Resolver
State Ownership
Persistence
Memory
Development Context
Human Communication
Checkpoint
Replay
Branch
Causal Trace
Reference Demo
```

### SHOULD

```text
Vector Retrieval
Real LLM Provider
richer research tooling
```

### LATER

```text
Web product frontend
portable full-life export
mass multi-agent
distributed runtime
world simulation
plugin marketplace
```

注：下面新增的前端展示规范属于 **Demo / Presentation Layer**，不改变 Runtime Architecture。

---

## 16F.10 Final Status

```text
Architecture Decision:
Implementation Roadmap v0.1

Status:
Accepted
```

---

# Appendix A：Frontend Presentation Specification v0.1【已敲定】

> 本附录只定义前端视觉与信息呈现，不包含 HTML 实现，不改变 Runtime / Core State / Process 架构。

## A.1 产品定位

官方展示前端采用：

> **Life Observatory / 数字生命观察舱**

而不是传统 CRUD 后台，也不是普通聊天机器人 UI。

核心视觉目标：

```text
Minimal
Dark
Scientific
Alive
Calm
```

用户应直观感受到：

> **这里存在一个持续生活、记忆、成长和分叉的数字生命。**

---

## A.2 视觉风格

推荐：

```text
深色科研界面
克制的轻科幻
少量生命感动画
大量留白
弱阴影
细边框
清晰信息层级
```

避免：

```text
传统 Element 后台
赛博朋克光污染
大量 KPI 卡片
十几种高饱和状态颜色
满屏粒子 / 扫描线
```

---

## A.3 基础颜色

推荐基础色：

```text
Main Background       #0B0E14
Primary Panel         #111620
Secondary Panel       #171D28
Border                #252C38

Primary Life Accent   #67E8D4
```

语义辅助色仅少量使用：

```text
Emotion       Purple
Memory        Amber
Goal          Blue
Relationship  Soft Pink
Body          Green
Warning       Orange
Critical      Red
```

不为 13 个 Core State 各自分配一种强颜色。

---

## A.4 主导航

v0.1 主入口只保留：

```text
Life
Talk
Timeline
Mind
Branches
```

不要把 13 个 Core State 全做一级菜单。

含义：

```text
Life      = 它现在是谁
Talk      = 它如何与你交流
Timeline  = 它经历过什么
Mind      = 这些经历现在怎样留在它身上
Branches  = 它的人生还可能变成什么
```

---

## A.5 Top Bar

固定显示：

```text
AnimaFlux
Life Name
ALIVE / PAUSED 等状态
Current Branch
Runtime Life Time
```

主要操作：

```text
Step
Advance
Checkpoint
```

不要在顶部堆过多操作按钮。

---

## A.6 Life Overview

首页重点展示：

```text
Life Name
Chronological Age
Life Stage
Current Role
Current Mood
Current Focus
Body Energy / Fatigue
Active Drives
Active Goals
Important Relationship
Relevant Memory
Development Context
Recent Life Events
```

普通视图以人类可读语言优先，不默认展示大量内部浮点数。

---

## A.7 Life Orb

首页可使用一个抽象 Life Orb 作为生命视觉中心。

状态表现：

```text
ALIVE
→ slow breathing glow

PAUSED
→ animation stopped

DEAD
→ dark / no breathing
```

动画必须克制，不做游戏式 HUD。

---

## A.8 Life Time

生命时间始终可见，例如：

```text
Day 184 · 10:42
24y 6m
```

强调 Agent 是存在于时间中的生命。

Wall-clock Debug 信息只在 Research View 展示。

---

## A.9 Timeline

Timeline 采用纵向人生时间线，不用普通日志表格。

节点可根据语义轻量区分：

```text
important event
memory
relationship event
goal event
turning point
checkpoint
```

点击节点后，从侧边展开：

```text
what happened
what was perceived
relevant memories
appraisal
state effects
decision / consequence
```

即 Human-readable Causal Trace。

---

## A.10 Mind

13 个 Core State 不做 13 张平铺卡片。

建议按认知层次分组：

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

点击后使用侧边 Detail Drawer 展开。

---

## A.11 Emotion Detail

展示：

```text
Current Mood
Active Emotion Episodes
Intensity
Started Time
Trend / Decay
Recent Causes
```

必须强调 Causes / Context，而不仅是数值。

---

## A.12 Memory Presentation

Memory 使用卡片 / 列表，而不是数据库表格。

支持：

```text
Episodic
Semantic
Procedural
Autobiographical
```

Accessibility 可以通过轻微视觉淡化表达。

但不能模糊到不可读。

---

## A.13 Development / Experience

Development 不显示统一“成熟度”。

展示：

```text
Chronological Age
Life Stage
Current Roles
Major Transitions

Domain Experience:
Exposure
Practice
Diversity
Recency
```

避免 RPG：

```text
Level 8
Maturity 76%
```

正式遵守：

```text
Age ≠ Experience ≠ Skill ≠ Self-Efficacy
```

---

## A.14 Branches

Branches 页面使用人生分叉树。

展示：

```text
Genesis
Important checkpoints
Main branch
Alternative branches
```

当前 Branch 使用主 Cyan 高亮。

点击 Branch 可看到：

```text
fork point
unique memories
belief changes
relationship transitions
narrative differences
```

支持 Main vs Branch 对比。

---

## A.15 Talk

Talk 不做纯 ChatGPT 风格。

推荐：

```text
Left:
Conversation

Right:
Current Life Context
```

右侧普通模式可显示：

```text
Mood
Active Goal
Life Stage
Relevant Context Summary
```

每条重要回复旁边可以提供：

```text
Why ↗
```

用于展开 Human-readable Causal Trace。

---

## A.16 Life / Research View

统一前端提供：

```text
Life View
Research View
```

Life View：

```text
human-readable
minimal
narrative
```

Research View 增加：

```text
Tick ID
State Version
Source Refs
Confidence
Appraisal Factors
LLM Call ID
Plugin
```

无需单独做一个传统 Admin Backend。

---

## A.17 Advance Time

使用简洁弹窗：

```text
10 minutes
1 hour
1 day
1 week
Custom
```

提示：

```text
Scheduled events may occur during this period.
```

禁止表现成直接 set_time。

---

## A.18 Checkpoint

Checkpoint 使用人生节点语义而不是数据库术语。

创建时显示：

```text
Name
Current Life Time
Current Branch
```

Timeline 中使用轻量菱形节点表现。

---

## A.19 Typography

推荐：

```text
Inter
Noto Sans SC / 思源黑体
```

普通正文约：

```text
14px
```

技术 ID / Tick / Version 等 Research 信息使用：

```text
JetBrains Mono
```

不使用难读的“科幻字体”作为正文。

---

## A.20 Component Style

推荐：

```text
8–12px radius
1px subtle border
weak shadow
large whitespace
4–6 main visual blocks per page
```

避免：

```text
huge SaaS rounded cards
dense dashboards
excessive gradients
```

---

## A.21 Animation

v0.1 仅保留：

```text
Life Orb breathing
state value soft transition
new timeline event fade
branch line growth
```

不使用：

```text
background particles
scanning effects
full-screen neon animation
```

---

## A.22 Frontend Scope

此规范只要求展示层。

v0.1 前端可以先使用：

```text
static / mock data
```

用于 Demo UI 设计。

真实 Runtime API 接入属于后续实现。

不因为前端展示需求修改 Core Runtime Architecture。

---

## A.23 Frontend 最终原则

1. 前端定位为 Life Observatory。
2. 不做传统后台管理系统视觉。
3. 不做普通 ChatGPT 单页聊天视觉。
4. 使用深色、克制、科研、轻生命感设计。
5. 主导航只保留 Life / Talk / Timeline / Mind / Branches。
6. 生命时间始终可见。
7. Life Overview 优先展示当前生命状态。
8. Life Orb 只承担轻量生命感，不做游戏特效。
9. Timeline 是关键展示页面。
10. Causal Why 是关键辨识度功能。
11. Mind 将 13 State 分组而不是平铺。
12. Memory Accessibility 可视觉淡化。
13. Experience 不做 RPG Level。
14. 年龄不等于成熟度。
15. Branches 使用人生树视觉。
16. Talk 同时显示有限 Current Life Context。
17. 普通模式不展示大量技术 ID。
18. Research Mode 提供 Trace / Version / Source 等技术数据。
19. 前端只读展示必须走 Public View。
20. 不通过 UI 直接修改 Core State。
21. Step / Advance / Checkpoint 使用生命语义表达。
22. 动画克制。
23. 大量留白，避免信息过密。
24. Demo 优先清楚表达“它在活着”，而不是炫技。

状态：

```text
Frontend Presentation Specification: v0.1
Status: Accepted
Implementation HTML: not part of the specification
```

---

# Architecture Freeze

截至本版本：

```text
Core State                    ✅
Life Loop                     ✅
Kernel / Runtime              ✅
Plugin Protocol               ✅
Persistence                   ✅
Environment Boundary          ✅
Cognitive Processes           ✅
Communication                 ✅
Development / Experience      ✅
LLM Strategy                  ✅
Project Structure             ✅
Database Schema               ✅
Public API / CLI              ✅
Testing Strategy              ✅
Reference Demo                ✅
Implementation Roadmap        ✅
Frontend Presentation Spec    ✅
```

正式状态：

```text
AnimaFlux v0.1 Architecture
Status: FROZEN FOR IMPLEMENTATION
```

从现在开始：

> **只填完当前已经确定的 AnimaFlux 边界，不再扩边界。**

若出现新的功能构想，默认放入：

```text
v0.2+ backlog
```

除非真实实现证明当前冻结设计存在技术冲突或核心正确性问题。
