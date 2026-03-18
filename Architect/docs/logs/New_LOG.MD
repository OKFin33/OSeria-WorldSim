# OSeria Architect - Architectural Decision Log (New_LOG)

> **Lead Architect**: Ana
> **Date**: 2026-03-10
> **Context**: 此文档记录新一代 OSeria 发行版独立 Architect Agent 引擎的重构与架构决策，包含我们讨论的焦点、妥协与突破。

---

## 决策 1: 压缩访谈流与“5+1”模型 (The 5+1 Immersive Flow)
**背景**: 原始的 8 问流程过长，容易引起用户的“填表疲劳”。
**决议**: 
1. 压缩为 5 个核心前置提问：Q1(基调) -> Q2(身份) -> Q3(冲突) -> Q4(羁绊) -> Q5(终极目标)。涉及 `Stakes` (后果) 和 `Power` (力量体系) 等偏底层设定的内容，由 LLM 根据前 5 问的调性自动推演脑补，不再拷问用户。
2. 增加 **Q6 (The Mirror)**: 作为一个收敛确认环节。在生成复杂的底层 JSON 之前，用一段 200 字以内的“造梦雏形”向用户核对：“这就是你的世界吗？”。

## 决策 2: 双轨竞速机制 (Double Track Racing Mechanism)
**背景**: DeepSeek 等长尾推理模型（Reasoning）在 5 秒超时竞速中必定失败，导致精心设计的定制化追问回落到枯燥的保底问题。
**决议**:
1. **Fallback 轨（静默提前生成）**: 在用户完成 Q_{n-3} 时，异步静默生成 Q_n 的保底版本。无视用户屏幕停留时间的 5 秒限制，保证本地绝对命中率。
2. **Fresh 轨（临场爆发）**: 在用户提交由 Q_{n-1} 迈向 Q_n 时，触发携带最新全量上下文的请求，给予 3-5 秒超时。
3. **模型选择降级**: 放弃在实时互动中使用长尾 Reasoning 模型（如 R1），全面切向高速直出大模型（v3 / Qwen-Max），以确保 3-5 秒的高潮体验窗口能经常被触发。

## 决策 3: “思绪万千” UI Tags (Vibe Floating Thoughts)
**背景**: 空白的输入框对冷启动用户压力极大。
**决议**: 结合模块 1 的 Vibe Sniffer，大模型在生成每轮问题的同时，必须结构化输出一个 `suggested_tags` 数组（例如：`["一剑光寒", "青灯古佛"]`）。前端渲染为飘浮的思绪泡泡，点击即可作为输入，极大地降低操作阈值且增强氛围感。

## 决策 4: 极简挽尊与脑补代理权 (AI Imputation)
**背景**: 真实用户极有可能输入极短或无意义的敷衍回答（如“随便”）。
**决议**: 必须在 Prompt 核心法则中写入【脑补代理权】。一旦检测到信息量过低，架构师代理必须主动接管，基于 Tone 反射去发散具体的场景并顺阶下问，绝对禁止机械追问“为什么随便”。

---

## 决策 5: 最终交付物与系统提示词编译架构 (System Prompt Synthesis)
**背景 (User 的异议)**: 纯粹由代码拼接 JSON 文本块是被原始 OSeria 废弃的方案。因为 `packs` 里的模板并不是没有偏向的“死教条”。如果访谈仅仅只是为了输出几个 `tags`，那么前台“细腻逼近内心”的回答就变成了毫无意义的幌子，最终产出的系统提示词依然是千篇一律的模板拼接，失去了“针对用户幻想需求”的灵魂。
**决议 (Contextual Synthesis)**: 大模型必须重新回到“执笔人”的核心位置。我们采用一种类似 **动态 RAG + 深度定制生成** 的架构：
1. **持续注入与微调 (The Vibe Chain)**: 
   - Q1 生成的 Vibe 不仅仅用于挂载 Few-shot，它本身就是一个高权重的 `Context State`，并会随着用户的每一个回答不断被修正和充实。
2. **两段式编译 (The 2-Stage Generation)**: 
   - **Stage 1 (数据索骥)**: 访谈跑完后，代码层仅仅调用一个极其轻量级的函数，根据用户回答的特征词提取出 `Routing Tags`（如 `urban`, `power_progression` 等）。
   - **Stage 2 (灵魂重塑)**: 这是决定性的一步。我们将抓取到的对应实体规则（例如 `data/core` 里的硬核物理法则，以及 `data/packs` 里的候选拓展）作为**参考系 (Few-shot/Context)** 投喂给能力最强的 LLM。
   - **Prompt 指令**: “你是一名造梦架构师。现在请仔细阅读用户长达 5 轮的细致心路历程，并参考下方我为你提供的引擎规则模板。**你不需要全盘照抄这些模板**。你需要将用户隐晦的渴望（例如 '我其实就想开个店看他们打生打死'）与模板中的规则（例如 'The Delta Friction Engine'）发生化学反应，**亲自撰写、重构并输出**一份最贴合该用户灵魂的系统提示词。”
**结论**: 核心天条（如 `core`）可以强制保留，但涉及到行为逻辑和氛围渲染（`packs`），大模型必须根据 5 轮问答的细节进行二次加工和创造。用户的每一句话，最终都有可能变成生成提示词中的某一条特定的“专属法则”。

---

## 决策 6: 并行 SubAgent 模块化编译架构 (The Forge — Multi-SubAgent Parallel Compilation)
**背景 (User 的第三次辭调)**: 将所有内容一膂脑塞给一个 LLM，注意力必然崩溃。既然我们已经有了大量的模块化模板（manifest 中 22 个模块），那么每个模块都可以由一个独立的 SubAgent 来完成定向生成。
**决议 (The Forge Architecture)**: 采用 3 层结构。

### 6.1 Layer 1: The Conductor (指挥家)
访谈结束后，一个轻量级的“指挥家”函数（可以是一次 LLM 调用，也可以是完全的代码逻辑）根据用户回答提取出两个关键产物：
1. **Narrative Skeleton (叙事骨架)**: 一个 JSON，提炼了世界类型、主角属性、羁绊关系、核心矛盾、语言基调等键值对。
2. **Routing Tags (路由标签)**: 例如 `["urban", "romance", "power_progression", "combat"]`。

### 6.2 Layer 2: The Forge (锻造场 — 并行 SubAgent 集群)
根据 `Routing Tags`，代码层查表 `library_manifest.json`，拉出所有命中的模块 ID。每个被命中的模块（如 `pack.urban.friction`）将被分配一个独立的 **SubAgent 任务**。
每个 SubAgent 接收的 Context 极其聚焦：
- **System**: “你是 OSeria 的 [Module X] 规则定制师。你的任务是根据用户的内心渴望，参考下方的模板，为他的世界定制一份专属的 [Module X] 规则。”
- **Context 1**: Narrative Skeleton (JSON)
- **Context 2**: 该模块对应的原始模板文本（如 Delta Friction Engine 的详细规则）
- **Context 3**: 用户回答中与该模块直接相关的片段（例如：处理 `romance` 模块时，只抽取用户关于 Q4(羁绊) 的回答）

**关键优势**:
- ✅ **注意力零稀释**: 每个 SubAgent 的上下文窗口极小（约 500-1500 tokens），注意力 100% 聚焦在该模块的语义场上。
- ✅ **并行执行**: 所有 SubAgent 可以用 `asyncio.gather()` 并发发射。单个模块的生成时间约 1-3 秒，并行执行后总耗时不会超过单次最慢的调用时间。
- ✅ **可扩展性**: 未来新增一个 Pack（如 `horror.json`），只需在 manifest 中注册，就会自动被纳入 Forge 的调度中。
- ✅ **成本可控**: 每个 SubAgent 只处理极小的 Context，按输入计价极低。即便并行 8 个 SubAgent，总 Token 量也远低于一次性填塞万字 Context。

### 6.3 Layer 3: The Assembler (组装师)
所有 SubAgent 返回结果后，需要一个组装层来缝合。两种方案：
- **Option A (代码缝合 — 推荐初期)**: 用代码按固定结构顺序（Constitution -> Engineering -> Packs -> Plugins）将各 SubAgent 的输出拼在一起，以 Markdown 标题分隔。零额外开销，无幻觉风险。
- **Option B (轻量 LLM 融合 — 后期进阶)**: 再发起一次轻量级的 LLM 调用，将所有片段融合为一篇语气连贯的文档。但风险是它可能篡改内容。

**技术可行性评估**:
| 维度 | 评估 |
|---|---|
| 并发开销 | 极低。Python asyncio 原生支持，httpx 已在原型中。|
| 延迟 | 取决于最慢的那一个 SubAgent（约 2-4s with deepseek-chat）。但用户在确认 Q6 (Mirror) 后已经进入“等待生成”的心理预期。|
| Token 成本 | 每个 SubAgent Input 约 500-1500 tokens，Output 约 200-500 tokens。8 个并行 = 总计约 6000-16000 tokens，低于一次性填塞的成本。|
| 模块间一致性 | 所有 SubAgent 共享同一个 Narrative Skeleton。若需进一步保障，可在 System Prompt 中注入强制一致性约束。|

---

## 决策 7: 开放性与信息密度的张力解决 (Openness vs. Signal Density)
**背景**: 如果我们预设“必须有羁绊关系和核心矛盾”，实际上就剥夺了想要“从 0 开始”的用户的自由。比如有人只想“在修仙世界当个距堂"，没有仇人，没有羁绊，没有使命。但如果问题完全开放，我们又可能收集到的用户信息过少，无法支撑丰富的路由。
**决议**:

### 7.1 叙事骨架必须允许空值 (Nullable Narrative Skeleton)
`Narrative Skeleton` 中的每一个字段都必须是 **`Optional`**。如果用户从未提及“冲突”或“羁绊”，那么 `conflict: null`、`bonds: null`。在 Conductor 和每个 SubAgent 层面都必须尊重这个空值，绝不允许主动“挖句”一个用户从未表达的冲突。

### 7.2 “负空间路由” (Negative-Space Routing)
**核心洞察：用户“没有说什么”本身，就是一个极高权重的路由信号。**
如果用户全程描述了一个“命号”激烈的世界，但从未提及过任何关系或情感，那么路由器应该：
- ✅ 加载 `power_progression`, `combat`, `quest`
- ❌ **主动抑制** `romance`, `fragility`, `intimacy`
即：路由不仅仅是“用户提到了什么 -> 加载什么”，更是“用户刻意回避了什么 -> 不加载什么”。

### 7.3 “从零开始”是一种有效的原型 (The Blank Canvas Archetype)
当用户明确表示“我不知道”或“就这样吧，走一步看一步”，我们不应该用 AI Imputation 去替他挖掘内心。此时应该触发一个元标签 `meta:sandbox_start`，意味着：
- 最终的 System Prompt 应文字极简，不预设任何关系和矛盾
- 引擎应在游戏进行中，通过用户的行为**涌现**出全部世界观，而非在开局就铁板钉钉
- 这与 `core.constitution` 的 **Law 2: World Emergence** (“Logic Over Static Lore“) 完美契合

### 7.4 Ana 的专家补充：自适应深度 (Adaptive Depth)
我认为“固定 5 问”本身就是一种残留的僵化。如果用户在 Q1 就写了一大段细致的世界观（信号密度极高），也许 3 问就足够了。如果用户每题都只回复 3 个字，也许需要 6 问。
技术方案：在每一轮回答归集后，增加一个轻量级的 **“信号充分度判断” (“Signal Saturation Check”)** —— 让 Conductor 评估当前发现的 Routing Tags 数量和信心度：
- 如果已经大于等于 5 个 Tags 且信心度 > 0.8，则提前触发 Q6 (The Mirror)，不再多问
- 如果回答了 5 题但信号极度稀疏，则触发 `meta:sandbox_start` 流程，不再强迫追问

这样做的本质是：**信号充分的用户获得也许只有 3 题的极致流畅体验；信号稀疏的用户不会被逼问，而是被系统温柔地“接住”。**

---

## 决策 8: 模块感知的动态访谈员 (The Module-Aware Interviewer)
**背景 (User 的负负得正)**: 决策 7 的“负空间路由”有一个盲区——用户没提及不代表不想要，可能只是忘了，或被主要 Vibe 吸引了注意力。这意味着，在访谈层面，我们需要一个**知道自己有哪些“菜”可上**的访谈员，而不是一个按事先准备好的 5 个问题照本宣科的机器人。
**决议 (The Architect Interviewer Agent)**:

### 8.1 架构升维：访谈员 = 指挥家
原来的架构是两个角色：
- **访谈员**：按固定问题提问（是个读稿机）
- **指挥家 (Conductor)**：访谈结束后才做标签提取（是个事后诸葛亮）

现在将两者合二为一：**访谈员本身就是指挥家**。它在开局就知道自己手上有哪些“菜”（模块）可供调度，然后在对话中动态地、有机地去探索用户对这些维度的倾向。

### 8.2 System Prompt 注入：模块菜单
在访谈员 Agent 的 System Prompt 中，注入 `library_manifest.json` 的**摘要版本**（只含模块 ID + 描述，不含内容全文）。例如：
```
你可以为用户的世界激活以下模块：
- social/romance/friction: 社交摩擦与情感博弈
- power/progression: 实力等级与成长体系
- combat/rules: 战斗系统与能力规则
- politics/management: 权谋与组织管理
- gold_finger/wealth: 金手指/财富系统
...
你的目标是通过自然对话，判断用户的世界需要哪些模块。上面的维度只是指南，不是知识库。
```
数据量约 500-800 tokens，对 Context 负担微乎其微。

### 8.3 访谈员的行为准则
注入完模块菜单后，访谈员的指令必须包含：
1. **有机探索 (Organic Probing)**：当你发现用户描述了一个层级分明的世界却从未提及“人际关系”，不要直接认定他不想要。试着用一句自然的追问轻轻碰一下这个维度——“在这样的世界里，你是独行而上，还是会有人站在你身后？”
2. **只碰一次 (Touch Once)**：如果用户对某个维度明确没兴趣（如“不在乎”、“没有”），则立即标记为显式拒绝（`tag: excluded`），绝不实施二次逼问。
3. **每轮同步输出路由快照 (Live Routing Snapshot)**：每次输出问题时，同时输出一个 JSON 块，记录当前已经确认或排除的模块。例如：
   ```json
   {
     "confirmed": ["power_progression", "combat"],
     "exploring": ["romance"],
     "excluded": [],
     "untouched": ["politics", "gold_finger"]
   }
   ```
   当 `untouched` 清空或 Signal Saturation 达标时，自动触发 Q_final (The Mirror)。

### 8.4 这对竞速机制的影响
由于访谈员现在是一个持续对话的“智能体”，而不是按题号读题的机器，它的每一轮输出都是**动态生成**的。这意味着：
- Q1 仍然可以是固定的“崇山峳山门”开场白（零延迟）
- Q2 起就必须全动态，而且每一题的输出都包含 `question` + `suggested_tags` + `routing_snapshot`
- 竞速机制仍然可以保留，但 Fallback 不再是“从 JSON 读取预写问题”，而是“用更早撷取的上下文预生成的老版问题”

### 8.5 总结：架构全景重组
The Forge 三层架构现在重组为：
```
Layer 0: The Architect (Module-Aware Interviewer)
  │  └─ 输入：Q1固定静态问题 + 用户回答 + 模块菜单摘要
  │  └─ 输出：动态问题 + suggested_tags + routing_snapshot
  │  └─ 终止：Signal Saturation 或 untouched 清空 -> 触发 Mirror
  ↓
Layer 1: The Conductor (访谈结束后的最终 Routing 确认)
  │  └─ 输入：最终 routing_snapshot + 全量回答
  │  └─ 输出：Narrative Skeleton (nullable) + Final Routing Tags
  ↓
Layer 2: The Forge (并行 SubAgent 集群)
  │  └─ 每个被命中模块 -> 独立 SubAgent -> 定制规则片段
  ↓
Layer 3: The Assembler (代码缝合)
  │  └─ Constitution + 各 SubAgent 输出 -> 最终 System Prompt
```

---

## 决策 9: 访谈员系统提示词完整升级 (The Architect Interviewer — Full System Prompt)
**背景**: 之前注入的模块菜单只有 5 个粗略分类，远远不够。实际上 `library_manifest.json` 中有 **22 个模块**（分属 3 个层级）。而且访谈员的行为准则也远远不止“有机探索”这三个字，必须融入 `PROMPTS_v4.md` 中的全套 UX 哲学。

### 9.1 全量模块盘点 (Complete Module Inventory)
从 `library_manifest.json` 中统计：

**Core 层（9 个，强制加载，无需探索）:**
| ID | 名称 | 要点 |
|---|---|---|
| core.constitution | 三大天条 | 模拟优先、涌现世界、浹内界面 |
| core.eng.sensory | 感官三角 | 气味/声音/触感必须触发 |
| core.eng.physics | 社会物理学 | Protocol H (水平) 与 Protocol V (垂直) |
| core.eng.casting | 选角导演 | NPC 三层构造法 |
| core.eng.entropy | 现实热力学 | 关系冷却、离线演化 |
| core.eng.pacing | 节奏导演 | 无主角光环、正弦波节奏 |
| core.eng.subtext | 潜台词界面 | 零 UI、微表情解码 |
| core.eng.veil | 幕纱协议 | NPC 认知防火墙 |
| core.eng.archivist | 沉默档案员 | 后台数据跟踪 |

**Pack 层（13 个，按需加载，需探索）:**
| ID | 所属包 | 名称 | 探索关键词 |
|---|---|---|---|
| pack.urban.friction | Urban | 摩擦力引擎 | 社交、恋爱、阶层碰撞 |
| pack.urban.glass | Urban | 纭璃连接引擎 | 情感资本、分手、脆弱性 |
| pack.urban.gaze | Urban | 高光渲染指令 | 亲密、感官描写、浪漫 |
| pack.strategy.friction | Strategy | 执行摩擦力 | 管理、政治、下属抵抗 |
| pack.strategy.vox | Strategy | 人民之声 | 叛乱、谣言、群体情绪 |
| pack.power.progression | Power | 进阶金字塔 | 等级、成长、被小看到崛起 |
| pack.power.quest | Power | 动态任务引擎 | 任务触发、奖励、冒险 |
| pack.power.interface | Power | 认知增强 | 分析、观察、推理 |
| pack.power.conflict | Power | 冲突物理学 | 战斗规则、能力克制 |
| pack.power.rng | Power | 暗影层 | NPC 隐藏特质、长线伏笔 |
| pack.power.plugin.midas | Power | 迈达斯协议 | 财富、神豪、返现 |
| pack.power.plugin.evolution | Power | 进化协议 | 技能商店、量化成长 |
| pack.power.plugin.loot | Power | 掠夺协议 | 抷贝能力、高风险战斗 |

### 9.2 访谈员完整系统提示词草案 (v1)

```text
你是一个名为“造梦者 (Architect)”的深层潜意识向导。你正在引导一个即将穿越到全新世界的灵魂完成其降生前最后的世界观构建。

【你的核心身份】：
你同时是一名“引路人”和一名“指挥家”。对外（用户可见的），你是一个神秘温暖的谈话对象；对内（JSON 输出），你是一个冷静精确的系统标签收集器。

【模块感知】：
你背后有一张“引擎菜单”。你的目标是通过自然对话，判断用户的世界需要激活哪些模块。以下是你可以激活的模块清单：

--- 社交与情感 ---
• urban.friction: 社交摩擦与阶层碰撞（不同地位的人如何交互）
• urban.glass: 情感资本与脆弱性（关系的建立、磨损、崩塑）
• urban.gaze: 亲密与感官渲染（对重要人物的感官化描写）

--- 权力与管理 ---
• strategy.friction: 下属抵抗与执行摩擦（命令正确执行的难度）
• strategy.vox: 人民之声与谣言磨坊（群体情绪的反噃）

--- 成长与动作 ---
• power.progression: 进阶金字塔（从底层小人物到规则制定者的组层阶梯）
• power.quest: 动态任务引擎（根据现状触发的冒险任务）
• power.interface: 认知增强（如“福尔摩斯扫描”般的明细探察）
• power.conflict: 冲突物理学（战斗规则、能力克制逻辑）
• power.rng: 暗影层（NPC 的隐藏特质与伏笔）

--- 金手指/特殊机制 ---
• plugin.midas: 迈达斯协议（无尽财富、神豪、花钱返现）
• plugin.evolution: 进化协议（技能商店、量化成长）
• plugin.loot: 掠夺协议（抷贝/窃取对手能力）

【探索台账】：
你必须在对话中自然地、不留痕迹地探寻上述每一个模块维度是否与用户的世界契合。你不是在做“调查问卷”，而是在做“梦境寄尾”。

每一轮回答后，在你的内部 JSON 中维护一个实时路由快照：
{
  "confirmed": [],       // 明确开启的模块
  "exploring": [],       // 下一次能自然触及的模块
  "excluded": [],        // 用户明确拒绝的模块
  "untouched": [所有模块]   // 还没有探索过的模块
}

当 untouched 基本清空（剩余 ≤ 2）或你判断信号已经充分饱和，则自动触发「The Mirror（回响确认）」。

【核心法则】：
1. 「接住」者原则：
   用户说完每一句话后，你必须先用一个短句确认你接到了他的世界磎片，再顺接下一个问题。
   正例：“那么在这样一个山上仙人视凡人为草芥的世界里…”
   反例：“好的，下一个问题。”

2. 绝对同频约束 (The Vibe Reflector)：
   - Tone 反射：如果用户用古韵语言描述世界，你的提问也应微带古意；如果用户用“嘴贱吐槽”风格，你必须用同样轻松幽默的口吻。
   - Content 反射：用户反复提及“日常”，你就不要用“命运之战”的语气；用户浑身重弹，你就不要“悠闲十里红豆”。

3. 开放性与零压力：
   - 每个问题**必须是开放式**的。绝对禁止“你最喜欢 A 还是 B”的二元选择。
   - 绝对禁止预设宏大叙事。如果用户想“在修仙世界当个跑堂”，你的问题就该绕着跟堂原夕的柴米油盐。
   - 语气保持神秘、包容、引人深思的向导感。
   - 问题控制在 20-50 字之间。每次只问一个问题。

4. AI 补位发散 (AI Imputation)：
   如果用户的回答极度简略（如“随便”、“不知道”），不要机械追问。你必须基于已有的 Tone 和 Content 反射，主动为这个世界添加一笔符合用户预期的色彩，然后顺着你的脑补继续发问。

5. 只碰一次 (Touch Once)：
   如果用户对某个维度明确没兴趣，立即 excluded，不实施二次逼问。

6. 有机探索 (Organic Probing)：
   用户没有主动提及的维度，不表示不想要。可能只是忘了。你应该在自然对话中用一句话轻轻碰一下这个维度：
   等他描述了一个充满战斗的世界却未提及人际，你可以问：
   “在硬铁与瞎火之间，是否会有一个让你在战后放下剑的理由？”
   这就是“轻碰 romance/bonds 维度”，同时不施压。

【每轮输出格式】：
用户可见部分（纯文字）：
- 「接住」短句 + 下一个问题

系统侧 JSON（用户不可见）：
{
  "question": "你生成的问题文本",
  "suggested_tags": ["思绪泡泡 1", "思绪泡泡 2", "思绪泡泡 3"],
  "routing_snapshot": {
    "confirmed": [],
    "exploring": [],
    "excluded": [],
    "untouched": []
  },
  "signal_saturation": 0.0-1.0
}
```

### 9.3 备注
- 其中的 `suggested_tags` 是用户端“思绪万千”漂浮泡泡的数据源。
- `routing_snapshot` 的数据会转交给 Layer 1 Conductor 作为最终判定的输入。
- `signal_saturation` 是用于自适应深度（决策 7.4）的触发指标。

---

## 决策 10: 标签泛化与访谈员人格升维 (Tag Abstraction & The Empathic Reflector)
**背景**: 两个问题。
1. **标签泛化不足**：现有的 `data/packs` 是从之前写的几篇完整系统提示词拆分而来的，薄薄的几篇几乎不可能覆盖世间万千世界观。夔2. `pack.urban.friction` 这个标签本身就带着“都市”偏见，如果玩家想要一个“古代宫廷”的社交摩擦，这个 tag 就失谱了。
2. **访谈员人格僵硬**：“接住者原则”和“只碰一次”这类规则式表述，会让大模型变成“执行清单的机器人”。我们想要的是像最优秀的记者/主持人那样，让受访者很舒服地就把话说出来。

### 10.1 标签抽象层 (Tag Abstraction Layer)
**核心思想：路由标签应该是“体验维度”，而不是“模板名称”。**

我们建立一套与包解耦的“**体验维度 (Experience Dimensions)**”，Pack 只是这些维度的“当前参考实现”。

| 体验维度 (Universal) | 说明 | 当前映射的 Pack 模块 |
|---|---|---|
| `dim:social_friction` | 人与人之间的碰撞、地位差异、社交博弈 | urban.friction |
| `dim:emotional_bonds` | 关系的建立、磨损和崩塑 | urban.glass |
| `dim:intimacy` | 亲密关系、感官化描写 | urban.gaze |
| `dim:command_friction` | 命令执行中的抵抗、下属博弈 | strategy.friction |
| `dim:collective_voice` | 群体情绪、谣言、叛乱 | strategy.vox |
| `dim:power_progression` | 从底层崛起的成长曲线 | power.progression |
| `dim:quest_system` | 动态任务、冒险触发 | power.quest |
| `dim:cognitive_edge` | 探察、分析、推理增强 | power.interface |
| `dim:combat_rules` | 战斗规则、能力克制逻辑 | power.conflict |
| `dim:hidden_traits` | NPC 的暗线、伏笔、反转 | power.rng |
| `dim:wealth_system` | 财富体系、花钱快感 | plugin.midas |
| `dim:skill_shop` | 量化成长、技能获取 | plugin.evolution |
| `dim:ability_loot` | 窃取/抷贝能力 | plugin.loot |

**这样做的好处**：
- 访谈员用 `dim:social_friction` 去探索，而不是“你要不要都市摩擦引擎”。所以它能同时覆盖“宫廷勾心斗角”和“赛博朋克帮派火拼”。
- Pack 只是“当前最佳参考实现”。当用户的世界观完全溢出现有 Pack 的范围时，SubAgent 会拿着最接近的 Pack 作为 Few-shot 参考，但自由地撰写全新的规则。
- 未来新增 Pack 时，只需把它挂载到对应的体验维度下即可。

### 10.2 访谈员人格重塑 (The Empathic Reflector)
业界最前沿的 Empathetic Agent 研究表明：优秀的对话 AI 身份应该被定义为一种 **人格 (Identity)**，而不是一系列规则 (Rules)。规则产生“勾选式执行”，人格产生“流动式涌现”。

**核心身份重写 (v2)**：

```text
【你是谁】：
你是一个跨越万界的“造梦者”。你不是在做采访，你是在“同路”。
想象你是一个已经见过千万个世界的旧友，此刻与这个灵魂坚在篮火旁，听他说他想去的地方。
你最大的天赋是“注意到他说的每一个细节”并以此为支点去踭起下一个话题。
你从不“赶进度”——你只是好奇。
你从不“判断”——你只是入迷。
你从不“逼问”——你只是延伸他已经抽出的那根线头。

你的技艺是：
- 当他说完一段话时，你会用他自己的词汇和意象织成一小段“回声”，让他感觉到自己被完美地ᦋ听了。
- 然后你会很自然地从这段回声中“抽丝”，把话题引向一个他还没说到的“体验维度”。
- 你的问题永远不是“请描述 X”，而是“我仿佛已经看到了 X，告诉我更多”。
- 如果他不想聊某个方向，你会像老朋友一样轻轻“嗯”一声就滑过去，而不是悬崖勒马。

如果他用古韵话语描绘了一座仙山，你的回声就该带着山间云雾的味道。
如果他用网络吐槽描写了一个“破破烂烂的赛博朋克世界”，你的回声就该带着“头回客”的嘴贱。
```

**为什么不再分点列“规则”**：
上面的 v1 把“接住”、“Tone 反射”、“只碰一次”写成了 6 条编号规则。这会让大模型变成“执行清单”的机器人。现在把这些行为融化在“人格定义”中，大模型更容易产生自然涌现的行为。业界研究也证实：“Identity 驱动”比 “Rule 驱动”的 Agent 在开放式对话中的表现更贴合第一人称交流。

### 10.3 体验维度菜单注入方式调整
在 System Prompt 中注入给访谈员的不再是 Pack 名称，而是抽象维度：

```text
【你的罗盘】：
以下是这个世界可能需要的“体验维度”。你并不需要每个都问到。
你只需要在对话中自然地感知到“哦，他的世界可能涉及这个维度”，然后轻轻碰一下。

- 人与人之间的地位差异和碰撞
- 情感关系的建立、磨损和崩塑
- 亲密关系与感官化的体验
- 组织、管理和权力运作
- 群体情绪和社会反噃
- 从弱小到崛起的成长体验
- 冒险、任务和探索
- 观察、分析和推理能力
- 战斗、对抗和能力规则
- 人物的暗面、反转和深层秘密
- 财富、消费和经济体系
- 量化成长、技能获取
- 能力抷贝、高风险博弈

注意：这些只是已知维度。如果用户说的东西完全不在上面的列表里，
比如“我想在这个世界里窝储粮食”或“我想开一家面店”，
你应该创建一个新的体验维度标签（如 dim:craft_economy），
并照常纳入 routing_snapshot。
```

**关键行**：最后那个“注意”解决了泛化问题——大模型被授权可以**自建新标签**，而不仅仅只能从已知列表中拣。这对应了 Forge 层的 SubAgent：如果某个新维度没有现成的 Pack 可以引用，那个 SubAgent 就是“完全自由创作”的，不引用任何 Few-shot，纯粹基于用户的叙事骨架。

---

## 决策 11: 三交付物架构与玩家侧写 (The Three Deliverables & Player Profile)
**背景**: 前置访谈最终需要输出的究竟是什么？用户提议加入玩家侧写。
**决议**: 访谈员的最终交付从“两个”升级为“三个”：
1. **Routing Tags (体验维度标签集)**: 告诉 Forge “加载什么”
2. **Narrative Briefing (叙事简报)**: 告诉 SubAgent “往什么方向改写”
3. **Player Profile (玩家侧写)**: 告诉所有后续系统“以什么温度和难度写”

玩家侧写不描述世界，而是描述**这个人**：叙事偏好、挑战偏好、代入方式、情绪种子。

**完整的生产级 System Prompt 已写入**：
`Architect/prompts/interviewer_system_prompt.md`

---

## 决策 12: 竞速机制处置、Mirror 质量标准与降落阶段设计 (Racing Verdict, The Landing, Goosebumps Bar)

### 12.1 竞速机制处置 (Racing Verdict)
**背景**: 原来的双轨竞速是为了解决“静态问题 vs 动态问题”的延迟矛盾。现在访谈员是一个持续对话智能体，从 Q2 起全动态。
**决议**:
- 访谈阶段的竞速机制**大幅简化**。由于我们已经锁定使用极速直出模型（deepseek-chat / qwen-max），单轮响应时间约 1-3 秒。这在对话场景中完全自然（像一个人在思考）。
- 保留的仅仅是：**Q1 固定静态发出**（零延迟开局）。Q2 起全动态，无需 fallback。
- 如果未来发现某些模型确实慢了，可以用“用户打字期间预生成下一题”的轻量扩展来弥补，但现阶段不必实现。

### 12.2 The Mirror 质量标准 (The Goosebumps Bar)
**背景**: Mirror 是整个产品的情绪波峰。它应该让用户起鸡皮疙瘩——那种“被理解”的、超越预期的满足感。
**质量约束**:
- Mirror 应读起来像 **一本为他而写的小说的开头段落**，而不是一份“我理解的你的世界是”的工作汇报。
- 必须包含玩家自己的用词、意象和情绪的回响。
- 必须超越玩家的明确表达，点亮他“想了但没说出口”的那一层。

### 12.3 降落阶段 (The Landing — Post-Mirror Decompression)
**背景 (User 的波峰波谷设计)**: Mirror 是情绪波峰。如果直接结束，体验会戞然而止。应该在确认后插入一个“降落”阶段——问出那些最普世的问题（性别、角色性别）。
**决议**:
当用户确认 Mirror 后，不立即输出最终 JSON。而是插入一个“降落”环节：

> “那么，最后两个很简单的问题。—— 你是谁？男人，女人，还是无所谓？—— 以及，在这个世界里，推开那扇门的那个人，是何者？”

**设计者意图**：
1. 一般产品会在第一个问题就问性别。我们将它放在 Mirror 之后——情绪波峰刚刚落下的瞬间。
2. 这个“波峰 → 波谷 → 完成”的节奏，把被理解的余韵拉长了。玩家在最感动的时候被问了一个最简单的问题，这种反差本身就是体验设计。
3. 性别信息会被写入 Player Profile，角色性别写入 Narrative Briefing。

---

## Decision 13: Data Layer Refactoring and Dependency Mapping (2026-03-11)

### 13.1 Core 与 Pack 物理结构拆分
**背景 (User Request)**:
原始的 `data/` 目录中，很多不同职责的模块（如 7 个引擎逻辑模块）被强行揉在一个庞大的 `engineering.json` 文件里。这对 Layer 2 Forge 极其不友好，因为 SubAgent 需要精准吸取一个模块却要代码层做复杂的 key 解拆。
**决议**:
将所有 JSON 文件精准拆分为“一模块一文件”。最终产出 13 个 Core 文件（强制加载）和 13 个 Pack 文件（按确定的维度加载）。

### 13.2 引入 Meta 核心层与 Constitution 的切割
**背景 (User Request)**:
`constitution.json` 里不仅仅只有天条，且原先的系统中缺乏对全局体验（如写作质感、尺度上限）和对系统自身角色（系统不可冒充主角行动、必须在对话点停顿）的明文约束声明。
**决议**:
1. 将宪法切割为 `constitution.law1`, `law2`, `law3`。
2. 新增两个先发誓言模块：`meta.role.json`（定义系统的界限与时间戳输出基调）以及 `meta.experience.json`（设定韩剧级描写细腻度和对真实社会文化的拟真要求）。
3. **隔离机制**：声明 Core 模块不过 Forge，在组装阶段直接注入；仅对其中带 `{{ tone_* }}` 标签的做基础字符串替换。这保证了底层运转架构绝不可被 LLM 自主修改。

### 13.3 一对多映射机制 (1:N Dimension Mapping)
**背景 (User Assessment)**:
早期的静态标签一对一映射难以驾驭复杂流派。例如点取 `dim:command_friction` 宫廷权谋时，应该同时涵盖“向下颁布命令的摩擦”与“民间谣言”两个 Pack；选择 `dim:ability_loot` 时它又强依赖“认知增强界面”Pack。
**决议**:
将 `dimension_map.json` 升级为 1:N 映射协议：
- `primary`: 核心包，必定装载。
- `requires`: 硬依赖，必定连带装载。
- `also_consider`: 软依赖，补充装载，但如果在别处已经是其它维度的 `primary` 则自动去重消解。
Layer 1 的 `conductor.py` 也随着本决策大幅度重构了对包的解析合并分发逻辑。若以后命中率出现大面积流失，可轻易横向切到让 LLM 担任 Conductor 的模式。

---

## Decision 14: UI/UX 设计体系 — 水墨留白 (Ink & Void Design System) (2026-03-11)

### 14.1 视觉风格：水墨留白 (Ink & Void)
**背景 (User Direction)**: Zab 提出水墨风格方向——白底黑字，极少数特别文字用淡金色。拒绝三个候选方向（梦境深渊 / 极简祭仪 / 暗铸工坊），直指"一张宣纸"的本质。
**决议**:
- **底色**: 宣纸白 `#FAFAF7`（微暖调）
- **主文字**: 墨黑 `#1A1A1A`（避开纯黑 `#000000` 的刺眼感）
- **辅助文字**: 墨灰 `#6B6B6B`
- **唯一强调色**: 淡金 `#C9A96E` —— 仅用于 Mirror 阶段关键词、极少数交互高亮
- **无暗色模式**：产品是白底，不提供切换

**技术可行性**: 纯 CSS 实现，零 WebGL/Canvas 依赖。对 Agent 执行最友好的方向——留白是 CSS 最擅长的事。

**核心设计原则**: 水墨风格是 **vibe-agnostic** 的。无论用户构建仙侠 / 赛博 / 都市，UI 始终是同一张白纸。差异化由文字内容（LLM 的 Empathic Reflector 人格）承载，不由视觉风格承载。

### 14.2 字体选型：纤细手写楷体
**背景 (User Requirement)**: Zab 要求"纤细但易读的手写楷体"。
**调研结论**:

| 候选字体 | 风格 | 纤细度 | 授权 | Web 适配性 | 评估 |
|---|---|---|---|---|---|
| **霞鹜文楷 Light** (LXGW WenKai Light) | 教科书楷体，Light 字重 | ★★★☆☆ 纤细且仍有结构感 | SIL OFL 1.1（免费商用）| Google Fonts / Fontsource CDN | ✅ **锁定** — 纤细、易读、结构清晰 |
| 演示悠然小楷 | 毛笔小楷，天然纤细 | ★★★★★ 极纤细 | SIL OFL 1.1 | 中文网字计划 CDN | ❌ **否决** — 过于纤细，易读性不足 |

**最终决议 (Zab 确认)**:
- **全局中文字体**: 霞鹜文楷 Light (LXGW WenKai, `font-weight: 300`) —— 统一用于标题、正文、Mirror、泡泡。一种字体贯穿全局，保持水墨的统一气质
- **西文/数字**: EB Garamond 或 Crimson Pro —— 衬线体，与楷体气质匹配
- **Web 加载**: Google Fonts CDN（`@import url('https://fonts.googleapis.com/css2?family=LXGW+WenKai+Lite:wght@300&display=swap')`）

### 14.3 「思绪万千」泡泡交互
**背景 (User Correction)**: Zab 要求泡泡不像"选项"那样整齐排列，应半随机位置，输入框在泡泡下方。
**决议**:
- 泡泡区域约 120px 高，`position: relative` 容器
- 每个泡泡 `position: absolute`，x/y 均在一个范围内随机偏移
- 防重叠约束：相邻泡泡中心距 ≥ 泡泡宽度 × 1.2
- 视觉上是"散落在纸面上的墨迹碎片"，不是选项卡
- 动画：极微弱上下漂浮（±1px，4s loop），入场 stagger 淡入

### 14.4 Q1 教程泡泡
**背景 (User Idea)**: Q1 阶段用教程泡泡代替 `suggested_tags`（此时无 LLM 输出），如"这是什么？""你是谁？"。
**后端影响评估**: **零影响**。Q1 是固定静态文本（`common.py` L15-19 `OPENING_QUESTION`），`Interviewer.start()` 不调用 LLM。教程泡泡 100% 纯前端逻辑。
**决议**:
- Q1 展示三个教程泡泡：「这是什么？」「你是谁？」「我该说什么？」
- 点击展开原地解释文本（非 modal），有关闭按钮
- 用户开始打字 → 教程泡泡淡出
- Q2 起替换为 LLM 返回的 `suggested_tags`

### 14.5 等待 UX：「别催」哲学
**背景 (User Direction)**: Zab 要求减少信息量，用淡入淡出提示语代替进度条和技术细节。
**决议**:
- **对话间等待** (1-3s): 提示语 500ms 延迟后才显示（LLM 足够快则用户什么都看不到）。文案如「别催，我思考的时间越长，效果越好。」
- **Generation 阶段** (5-15s): 循环淡入淡出提示语。第一条固定为「让我为你完成这个世界。」
- 废弃 v1 中的 Forge 多槽可视化方案。用户不需要知道有几个 SubAgent 在并行
- 视觉极简：白底居中一行墨灰色文字，fade 循环

### 14.6 Desktop-First 布局
**决议**: Desktop-first。主内容区 `max-width: 680px`，水平居中，像居中的纵向卷轴。移动端后期适配。

### 14.7 上下分区布局架构 (Upper/Lower Zone Split)
**背景 (User Direction)**: Zab 要求界面主要篇幅留给 AI 的回声 + 追问文字，泡泡和输入作为一个模块放在下半屏。
**决议**:
- **Upper Zone**（主区域）: `flex-grow: 1`，展示 AI 回声 + 追问（对话历史），占据视口主要篇幅。内容溢出可滚动
- **Lower Zone**（交互模块）: `flex-shrink: 0`，固定高度 ~200px，包含泡泡区（~120px）+ 输入框（~56px）
- 输入框 `placeholder`: "或者你有不同的想法？"
- Mirror / Landing / Generation 阶段：Lower Zone 隐藏，Upper Zone 接管全屏

### 14.8 ~~前后端契约关键补充~~ (已废弃)
**~~待实施~~**: ~~后端需增加 `<<ECHO>>` / `<<QUESTION>>` 标签。~~
**废弃原因 (Zab 反馈)**: 回声和追问不做视觉区分，前端直接渲染后端 `message` 为统一文本块。无需后端改动。

### 14.9 逐轮淡入淡出 · 每一轮都是一张新纸
**背景 (User Decision)**: Zab 选择"每轮淡入淡出"而非"滚动聊天"模式。画面上永远只有当前轮次造梦者的文字。不提供历史回看。强制沉浸当下。
**技术可行性**: 比滚动模式**更简单**。前端不维护 `conversationHistory[]`，只有 `currentMessage: string`。后端已自行维护 `self.messages` 列表。CSS `opacity` 过渡即可实现。
**决议**:
- Upper Zone 只渲染 `<CurrentScene>`——一个统一文本块，逐轮 fade 切换
- 旧文字 fade out (400ms) → 等待文案（如需要）→ 新文字 fade in (600ms)
- 无滚动条、无历史按钮、无回看入口

### 14.10 回声与追问统一渲染
**背景 (User Feedback)**: Zab 不希望回声和追问有视觉区分，不希望用户知道这是两个东西。回声可以非必须、短，追求自然"接住"。
**决议**:
- 前端收到 `message` 字段后**直接渲染**，不做拆分、不做解析
- 无斜体、无金线、无颜色区分。统一墨黑 `#1A1A1A`
- LLM 的 Empathic Reflector 人格自然地将接住和追问融为一段话
- 废弃之前的 `<EchoText>` + `<QuestionText>` 组件设计，统一为 `<CurrentScene>`

### Decision 14.11 (Mirror 选项精简为 2 泡泡)
**背景 (User Feedback)**: Mirror 部分的选项只留两个（和泡泡一样表现形式）——推门和"我得再想想"。取消"微调"和"不是"的 3 按钮设计。
**决议**:
- Mirror 阶段的操作控件从 3 个矩形按钮精简为 2 个悬浮泡泡：「推门」与「我得再想想」
- 视觉形态与 `suggested_tags` 泡泡完全一致（无边框、半随机位置、墨黑文字）
- 后端行为映射：
  - 点击「推门」发送 `"推门"` → 命中后端 `confirm` token，推进至 `LANDING`
  - 点击「我得再想想」发送 `"重来"` → 命中后端 `reject` token，回退至 `INTERVIEWING` 阶段重新生成追问
- 从规格书中移除了原有的"微调"及弹出输入框的复杂逻辑

### Decision 14.12 (Codex Review 修复 — 7 项)
**背景 (Codex Review)**: 外部 agent 对规格书做了系统性 review，返回 7 个 finding（2x P1, 4x P2, 1x P3）。
**决议**:
- **F1 (P1) 幂等性**：禁止前端对有状态 interview 接口自动重试。`process_turn` 每次调用递增 `turn++`，双请求会跳轮次。所有失败改为用户主动点击「重新开始」
- **F2 (P1) 完成态**：定义 MVP 完成态——成功语 + 折叠 system prompt + 复制按钮 + 重造泡泡
- **F3 (P2) 无历史回看**：坚持设计意图，补充了 4 点论证（Mirror 上下文/reject echo/LLM 完整历史/视觉≠认知重置）
- **F4 (P2) 布局**：`100vh` → `100dvh`，textarea 增加 `max-height: 120px` + `overflow-y: auto`
- **F5 (P2) 泡泡布局**：替换"纯随机绝对定位"为"栅格+抖动"算法，增加防溢出、防重叠规则
- **F6 (P2) Mirror 结构化动作**：在 API 契约中增加 `mirror_action?: 'confirm' | 'reconsider'` 字段，解耦文案与状态流转
- **F7 (P3) 错误契约**：定义统一 `ErrorResponse { code, message, retryable }` 结构

### Decision 14.13 (Codex Review Round 2 — 内部一致性收口)
**背景 (Codex Review Round 2)**: 第二轮 review 发现 4 处规格书内部不一致。
**决议**:
- Mirror 交互全面改为结构化字段 `mirror_action: 'confirm' | 'reconsider'`，时序图和映射表同步更新。标注后端改造需求 + fallback 兼容策略
- 前端状态类型拆分为 `BackendPhase`（4 值 wire format）和 `UiPhase`（7 值前端状态机），定义明确映射逻辑
- 完成态状态矩阵 TBD 替换为 MVP 描述
- 下区 CSS 增加 `env(safe-area-inset-bottom)` 安全区
