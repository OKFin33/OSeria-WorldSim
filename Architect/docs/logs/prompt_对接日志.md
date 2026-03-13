# Prompt / Dev 对接日志

## 文档用途

这不是单边日志，而是 `Prompt Agent <-> Dev Agent` 的交接文档。

用途：

- 记录 prompt 侧本轮实际修改了什么
- 记录开发侧对这些修改的承接反馈
- 把双方对问题、边界、预期效果对齐到同一份文档里

阅读规则：

- `Prompt Agent Log` 记录 prompt 侧已完成的文本修改
- `Dev Agent Feedback` 记录开发侧回复、承接思路或后续落地建议
- `Shared Handoff Rules` 是双方后续都应遵守的交接规范
- 若某段写到代码实现状态，以对应分支实际 diff / commit 为准

---

## 2026-03-13

### Prompt Agent Log

Owner:

- Prompt Agent

Scope:

- 仅修改 `Architect/prompts/` 下的 prompt 文件
- 不修改代码
- 不修改 schema
- 不修改状态机
- 不修改前端与架构边界

Problem Targets:

- `DossierUpdater` 首轮仍会过度自信
- `InterviewComposer` 过早收紧问题空间
- `InterviewComposer` 容易围绕同一幕画面打转
- `BubbleComposer` 仍偏系统引导，不像用户自然会点的回答
- `CompileOutput` 倾向把未真正处理的维度整包塞进 `emergent_dimensions`

Not In Scope:

- 代码逻辑
- Landing bug
- 状态机
- schema
- Forge / Assembler 链路实现

Changed Files:

1. `Architect/prompts/dossier_updater_system_prompt.md`
2. `Architect/prompts/interview_composer_system_prompt.md`
3. `Architect/prompts/bubble_composer_system_prompt.md`
4. `Architect/prompts/compile_output_system_prompt.md`

#### 1. `dossier_updater_system_prompt.md`

改了什么：

- 新增 `Separate Shell From Desire` 原则，明确题材词、视觉词、能力词不等于主角身份、人生目标、情绪核心。
- 强化 `bootstrap` 阶段约束，要求前两轮优先保住开放面，禁止把“题材 + 意象 + 规则感”自动收束成单一路线。
- 新增字段写入前门槛检查：
  - 这是用户明说，还是模型脑补
  - 这是世界壳层，还是主角命运
  - 写死后会不会把后续问题空间绑窄
  - 更适合硬字段，还是弱区 / open thread
- 增补禁止规则，明确禁止：
  - 把规则感直接写成唯一主轴
  - 把能力词直接写成情绪核
  - 把单一场景画面扩写成整个世界的唯一结构结论

为什么改：

- 真实链路里，“修仙 / 御剑 / 冷剑光 / 有规矩”过快被收成“剑修秩序压迫线”。
- 这会直接把后续 `InterviewComposer` 可探索空间压窄。

希望取得什么效果：

- 首轮 dossier 更像“保守工作档案”，而不是提前定调的世界文案。
- `world_premise` 不再偷写主角命运。
- `fantasy_vector` 不再偷写成长路径。
- `emotional_seed` / `taste_bias` 在证据不足时更愿意留空或降级到弱区。

#### 2. `interview_composer_system_prompt.md`

改了什么：

- 新增 `Open Before Narrow` 原则，明确前几轮优先打开世界层次、位置感、压迫来源与关系结构。
- 在坏问题定义中新增：
  - 假开放真分叉题
  - 场景打转题
- 新增“开放优先法则”和“场景使用规则”，要求：
  - 先问世界结构与位置感
  - 避免在同一幕里持续做二选一细化
  - 如果已经围绕同一幕问过 1-2 轮，下一问必须打开新的层次
- 强化 `mirror` 规则，要求 Mirror 不能只是最近几轮同一幕事件的压缩复述，还必须带出：
  - 世界如何运转
  - 用户想站在什么位置
  - 这种位置为何有吸引力或压迫感
- 增补与真实问题对应的正反例，显式打掉“死寂还是低语”这类窄分叉问法。

为什么改：

- 真实链路中的问题，在 Turn 1 后就快速压向“规矩压人”的单一路径。
- Turn 2-5 又持续围绕“越线坠落”这同一幕做近景变体，导致访谈推进感变弱。

希望取得什么效果：

- 前 1-2 轮更像“系统正在继续理解我想进入什么世界”。
- 中段不再长期困在一个镜头里打转。
- 问题更像打开世界结构，而不是帮用户选择系统预设分支。
- Mirror 更像高一级的理解回声，而不是漂亮复述。

#### 3. `bubble_composer_system_prompt.md`

改了什么：

- 新增 `Completion, Not Coaching` 原则，明确 Bubble 是用户侧补完，不是系统引导。
- 在生成规则中增加要求：
  - 至少 1 个 bubble 要像自然接话
  - 如果 3 个 bubbles 只是同一句系统总结的修辞改写，宁可少给
  - 当前问题已偏窄时，不要再做更窄的按钮分叉
  - `advance` 必须能从 `latest_user_message + dossier` 合理推出
- 在硬约束中新增禁止：
  - 系统文案感 / 宣传语 / 主题句 / 金句海报
  - 多个 bubble 共用“那一刻我才明白”类同模板总结句
  - 借 `advance` 偷渡主角化 / 爽文化 / 命定路线
- 增加“当前问题已经偏窄”时的正反例，明确 bubble 不应退化成选项按钮。

为什么改：

- 真实链路里的 bubbles 与问题高度同质，更像系统替用户总结。
- 它们不够像用户“顺手会点”的自然回答。

希望取得什么效果：

- Bubble 更接近用户自然会说的话。
- `answer` 更贴当前题面。
- `advance` 只前进半步，不再抢答用户欲望。
- 减少游戏按钮感和系统指导感。

#### 4. `compile_output_system_prompt.md`

改了什么：

- 补充 `emergent_dimensions` 约束：不能把所有未触及维度机械整包倒入，只能保留那些与当前 dossier 世界轮廓相容、可自然涌现的维度。
- 补充硬约束：`emergent_dimensions` 不能写成“剩余维度清单”。

为什么改：

- 真实链路里 `confirmed_dimensions` 为空后，compile 倾向把大批未真正确认的维度塞入 `emergent_dimensions`。

希望取得什么效果：

- compile 层少一点“库存清仓”味道。
- 在不修改 schema 和代码的前提下，尽量减少 compile 失真。

Prompt Agent Judgment:

prompt 可修的部分：

- 首轮过度自信
- 前几轮过早收紧
- 中段场景打转
- 泡泡系统引导感过强
- compile 层对 emergent 的机械扩写

明显不是 prompt 单独能修掉的部分：

- `Mirror -> Landing` 衔接 bug
- `routing_snapshot.confirmed` 形成机制偏弱
- Forge 无任务导致的最终 `system_prompt` 个性化深度不足

---

### Dev Agent Feedback

Owner:

- Dev Agent

Section Type:

- 开发侧回复 / 对接反馈
- 用于说明开发侧如何承接 prompt 侧问题
- 本段是否已实际落地，以对应代码 diff 为准

Problem Targets:

- `DossierUpdater` 的首轮保守性与中后段收束能力需要代码协同，不应完全依赖 prompt 自觉
- `Mirror -> Landing` 需要确定性兜底，不能继续把 Mirror 文本原样带进 Landing
- `CompileOutput` 需要更像“冻结后的下游稳定接口”，不能在 `confirmed_dimensions` 为空时直接让 Forge 空转
- `Blueprint` 至少不能继续出现 `protagonist_hook / core_tension` 重复同一句的问题

Referenced Files:

1. `Architect/interviewer.py`
2. `Architect/result_packager.py`
3. `Architect/tests/test_interviewer_steering.py`
4. `Architect/tests/test_result_packager.py`

#### 1. `interviewer.py`

开发侧回复原文：

改了什么：

- 在 `bootstrap` 阶段新增代码级 guardrail：
  - 不再粗暴清空所有 `confirmed`
  - 只下调高风险、容易首轮过度自信的成长/能力向维度：
    - `dim:power_progression`
    - `dim:combat_rules`
    - `dim:ability_loot`
    - `dim:skill_shop`
    - `dim:command_friction`
- 在 `stabilize` 阶段新增 routing 收束逻辑：
  - 对在历史中反复出现、支持度足够的 `exploring` 维度做有限提升，进入 `confirmed`
- 在 `compile_output()` 后新增归一化：
  - 如果 LLM 产出的 `confirmed_dimensions` 为空，则结合当前 `RoutingSnapshot + history` 做有限补强
  - `emergent_dimensions` 不再允许无限扩张，而是受当前 routing 约束并上限裁剪
- 为 `landing` 增加确定性兜底：
  - 当 `InterviewComposer` 没真正给出 landing 文本、返回模式不对、或直接复用了上一段 Mirror 时，回退到内置 landing 问题

为什么改：

- prompt 已经更保守，但仅靠 prompt 仍不足以阻止首轮“题材词 -> 成长线”漂移
- 当前 `confirmed_dimensions` 形成过弱，导致真实链路里 `Forge` 经常无任务可做
- `Landing` bug 会直接打断后续 UX 调优

希望取得什么效果：

- prompt 的保守性不再只靠语言约束，还会被代码层兜住
- `CompileOutput` 更像稳定的冻结接口，不会轻易出现“全部 confirmed 为空、全部 emergent 清仓”的假完成
- Forge 至少在合理情况下能拿到少量高置信任务，不再完全空转
- Landing 不会再因为 prompt 抖动而直接坏掉

#### 2. `result_packager.py`

开发侧回复原文：

改了什么：

- `core_tension` 抽取时，避免与 `protagonist_hook` 使用同一句
- 若摘要有多句，优先寻找与 hook 不同的第二句有效 tension

为什么改：

- 真实链路里 `Blueprint` 的 `protagonist_hook / core_tension` 经常重复，降低阅读价值

希望取得什么效果：

- Blueprint 仍然是轻摘要，但至少不再明显自我重复

#### 3. 测试补充

开发侧回复原文：

新增/加强的测试包括：

- `landing` 在 `InterviewComposer` 返回 Mirror 类文本时，会启用 fallback
- `CompileOutput` 会对空 `confirmed` 和过宽 `emergent` 做归一化
- `Blueprint` 的 `protagonist_hook` 与 `core_tension` 不应重复同一句

Dev Agent Judgment:

这轮不是“继续靠 prompt 硬拧”，而是把 prompt 微调对应到代码层最关键的三个支点：

1. 早期 guardrail
2. 中后期 routing 收束
3. compile / landing 的确定性兜底

也就是说：

- prompt 决定方向和语气
- 代码负责防止 prompt 一次抖动就把主链拖坏

本轮仍未解决的问题：

- `InterviewComposer` 早期问题仍可能偏窄，只是比之前更可控
- `BubbleComposer` 是否真的像“用户会顺手点的回答”，仍需继续用真实链路验证
- `confirmed_dimensions` 形成机制虽然加强，但还没有被真实多题材基准集充分验证
- `Blueprint` 目前只是轻摘要，质量提升空间仍然很大

---

### Shared Handoff Rules

从这一轮开始，prompt 不应再被当作“随手改的文本”，而应被当作有 release discipline 的产品部件。以下规则适用于双方后续交接：

1. 每个 prompt 有独立版本号
- 例如：
  - `DossierUpdater v0.3`
  - `InterviewComposer v0.4`
  - `BubbleComposer v0.2`
  - `CompileOutput v0.2`

2. 每次改动必须绑定真实问题编号
- 例如：
  - `UX-P1` 首轮 dossier 过度自信
  - `UX-P2` 问题过早收紧
  - `UX-P3` 场景打转
  - `UX-P4` bubble 系统引导感过强
  - `UX-P5` Mirror 复述化
  - `UX-P6` emergent_dimensions 清仓

3. 每次改动必须跑固定 benchmark 场景
- 至少应固定：
  - 修仙 + 规矩 + 不要纯爽文
  - 校园异能 + 表层秩序 + 暗流
  - 现代 / 都市 / 赛博管理感

4. 每个 prompt 必须有验收门槛
- 不是“感觉更好了”就算升级
- 需要明确：
  - 不应再出现什么
  - 期待出现什么

5. 每次升级都要写 release note
- 至少包括：
  - `Version`
  - `Problem Target`
  - `Behavior Change`
  - `Expected UX Improvement`
  - `Known Risks`

---

## 2026-03-13（InterviewComposer 补丁与首问更新）

### 本轮目标

- 把人工微调后的 `InterviewComposer` prompt 正式纳入版本基线
- 把首个固定开场问题从 `闭上眼` 更新为 `想象一下`
- 确保 prompt、运行时代码和测试基线同步

### 修改文件

1. `Architect/prompts/interview_composer_system_prompt.md`
2. `Architect/common.py`
3. `Architect/tests/test_pipeline.py`
4. `Architect/frontend/src/App.test.tsx`

### 改动记录

#### 1. `interview_composer_system_prompt.md`

改了什么：

- 强化角色开场，把访谈员进一步拉回“造梦者 / 同路人”
- 将以下约束正式写实：
  - 假开放真分叉题
  - 场景打转题
  - `Open Before Narrow`
  - 场景使用规则
  - Mirror 不得只是最近几轮同一幕的压缩复述
- 新增更贴近真实链路问题的正反例：
  - 避免围绕“越线坠落”连续做近景窄追问
  - 避免把“有规矩，但别太老套”压成门规/皇权/家族之类的系统分叉

为什么改：

- 当前问题不是完全跑偏，而是“很快开始缩窄”
- 需要把“继续打开世界层次”从一般原则升级为明确行为规范

希望取得什么效果：

- 前 2 轮更像继续理解世界，而不是逼用户选支线
- 中段不再长期困在同一幕镜头里做修辞变体
- Mirror 更像高一级的理解回声，而不是高压缩复述

#### 2. `common.py`

改了什么：

- 固定首问从：
  - `闭上眼。`
  改成：
  - `想象一下。`

为什么改：

- `想象一下` 更轻、更开放，仪式感更弱
- 更像邀请用户展开画卷，而不是被系统强制进入某种氛围

希望取得什么效果：

- 首问更柔和
- 更适合作为开放探索的起点

#### 3. 测试同步

改了什么：

- 把引用旧首问文案的测试一并更新

为什么改：

- 固定开场问题已经属于产品基线，不能 prompt 改了、代码和测试还活在旧版本

希望取得什么效果：

- 后续任何首问变更都会立即暴露在测试基线里，不会悄悄漂移

### 本轮判断

这一轮属于：

- `InterviewComposer v0.5` 补丁
- `OpeningQuestion v0.2` 基线更新

这不是架构改动，而是一次明确的版本内行为修正。

### 版本化要求补充

以后凡是出现这种“人工觉得更顺、更开放、更像人”的 prompt 微调，都必须同时同步三件事：

1. `Prompt Release Note`
- 标注这次改动命中的 UX 问题

2. `Runtime Baseline`
- 若牵涉固定首问、固定 phase 文本，必须同步代码常量

3. `Test Baseline`
- 至少改掉直接引用旧文案的测试，避免 prompt 和运行时基线脱节
