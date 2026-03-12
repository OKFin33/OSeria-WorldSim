# OSeria Architect Engine — 实施计划与开发路径图

> 版本：v0.2  
> 日期：2026-03-12  
> 性质：实时开发路径图  
> 规则：本文件保留“计划性”，但所有条目必须显式标注 `已实现 / 部分实现 / 计划中`

整改说明：
当前 Architect 在多轮迭代后出现了明显的层级重影：长期状态、最终交付、蓝图展示和 prompt 责任边界互相串味，导致问题、泡泡、Mirror 与最终编译链路并未共享同一份稳定理解。
本次整改的目标不是继续补丁式叠功能，而是把 Architect 强制收口为 `State Layer -> Compile Layer -> Delivery Layer` 三层，并以 `world_dossier + player_dossier + routing_snapshot` 作为唯一长期状态。
预期结果是：四大核心功能将基于同一认知底座工作；Compile Output 成为唯一稳定中间接口；蓝图与 system prompt 不再各自重复“再理解”一次用户。

## 0. 使用说明

这不是归档文档，也不是宣传稿。  
它的职责是同时回答三件事：

1. 当前代码已经做到哪里
2. 还缺什么
3. 下一步应该先做什么

从本文开始，`当前代码` 与 `下一版本目标` 必须分开处理：

- `当前代码`：作为可运行基线记录，不再作为架构真相继续扩写
- `下一版本目标`：作为唯一整改方向，后续实现必须以本文定义的层级和契约为准

状态图例：

- `已实现`：代码存在，且已通过当前仓库中的基本验证
- `部分实现`：主链路存在，但边界、测试或契约尚未收口
- `计划中`：方向已定，但仓库中尚无对应落地

## 0.1 当前实现检查点

截至 2026-03-12，当前仓库中已经成立的能力：

- `Interviewer -> Conductor -> Forge -> Assembler -> ResultPackager` 主链路已落地
- FastAPI API 层已落地：
  - `POST /api/interview/start`
  - `POST /api/interview/message`
  - `POST /api/generate`
  - `GET /api/health`
- Session 管理、`mirror_action` 结构化入口、`BlueprintSummary` 打包已落地
- React + TypeScript + Vite 前端骨架已落地于 `Architect/frontend/`
- 后端测试当前 `23/23` 通过
- 前端构建当前 `npm run build` 通过
- 前端测试当前 `3/3` 通过

仍未收口的点：

- Runtime 尚未独立实现
- 访谈 repair pass 仍缺少更细的观测/告警
- SSE 流式输出尚未接入
- 访谈结果尚未以“两份 dossier 持续编译”的形式逐轮固化，导致问题、泡泡、Mirror 与最终蓝图仍有偏离用户真实意图的情况

## 1. 技术栈约定

### Backend

- 语言：Python 3.10+
- 框架：FastAPI + Uvicorn
- 数据模型：Pydantic v2
- 并发：`asyncio`
- LLM 接入：OpenAI 兼容客户端

### Frontend

- 框架：React 18 + TypeScript + Vite
- 样式：原生 CSS
- 状态：React hooks

### 当前不做的替换

- 不更换前端框架
- 不引入数据库作为第一优先级
- 不在 Runtime 未定义前提前做跨阶段接线

## 2. 当前基线与 vNext 目标架构

### 2.1 当前代码基线

```text
User
  -> Frontend
  -> API / Service / Session
  -> Interviewer Runtime
  -> InterviewArtifacts
  -> Conductor
  -> Forge
  -> Assembler
  -> ResultPackager
  -> BlueprintSummary + system_prompt
  -> Runtime (planned)
```

### 分层状态

| 层 | 当前状态 | 说明 |
| --- | --- | --- |
| Interviewer Runtime | 已实现 | 支持状态机、Mirror、Landing、最终 artifacts |
| Steering | 已实现 | 轻量 steering hint 已接入 |
| Conductor | 已实现 | 代码路由，支持 `requires` / `also_consider` |
| Forge | 已实现 | `asyncio.gather()` 并发生成规则片段 |
| Assembler | 已实现 | Core 变量提取 + 固定章节组装 |
| ResultPackager | 已实现 | 启发式生成 `BlueprintSummary` |
| API / Session | 已实现 | FastAPI + `InMemorySessionStore` |
| Runtime | 计划中 | 当前仓库无独立实现 |

### 2.2 vNext 目标认知管线

当前主链路是：

```text
User input
  -> Interviewer (single creative call)
  -> routing_snapshot
  -> Mirror / Complete
```

下一阶段目标链路是：

```text
User input
  -> Call 1: Dossier Updater
  -> World Dossier + Player Dossier (session state)
  -> Call 2: Interview Composer
  -> visible_text + question / Mirror text
  -> Call 3: BubbleComposer
  -> bubble_candidates
  -> phase transition / Mirror / Landing
  -> Compile Output
  -> FrozenCompilePackage
  -> blueprint / system_prompt
```

设计原则：

- `Call 1` 负责理解和状态更新
- `Call 2` 负责创作和表达
- `Call 3` 负责从当前用户心智视角生成候选回答
- `World Dossier + Player Dossier` 是认知层单一事实源
- 对话历史仍保留，但降级为证据输入，不再是唯一记忆容器

### 2.3 vNext Canonical Layer Model

下一版本只允许三层，不允许再出现并列真相源：

1. `State Layer`
   - `routing_snapshot`
   - `world_dossier`
   - `player_dossier`
2. `Compile Layer`
   - `CompileOutput`
   - `FrozenCompilePackage`
3. `Delivery Layer`
   - `blueprint`
   - `system_prompt`

强约束：

- twin dossier 是长期状态，不是临时总结
- `CompileOutput` 是编译语义摘要，不是另一份长期状态
- `FrozenCompilePackage` 是唯一冻结下游输入包
- blueprint 与 system prompt 是交付层，不再各自重做一遍理解

### 2.4 已拍板的 vNext 决策

以下决策已确认，不再作为待讨论项反复摇摆：

1. 命名策略
   - 长期状态统一命名为：
     - `WorldDossier`
     - `PlayerDossier`
     - `RoutingSnapshot`
   - 唯一中间接口统一命名为：
     - `CompileOutput`
   - 唯一下游冻结输入包统一命名为：
     - `FrozenCompilePackage`
   - 下游受控上下文统一命名为：
     - `ForgeContext`
     - `AssemblerContext`
   - 交付层统一命名为：
     - `Blueprint`
     - `SystemPrompt`
   - 三次核心调用统一命名为：
     - `DossierUpdater`
     - `InterviewComposer`
     - `BubbleComposer`
   - 当前代码中的 `InterviewArtifacts` 仅视为旧实现名，vNext 不再沿用

2. 模型策略
   - `DossierUpdater`
   - `InterviewComposer`
   - `BubbleComposer`
   - Mirror 生成
   - `CompileOutput` 相关提炼
   在当前版本全部采用单一模型
   - 差异只通过 prompt、temperature、response schema 控制
   - 本轮不引入多模型分工

## 3. 组件实施矩阵

### 3.1 数据层

| 组件 | 状态 | 当前事实 | 后续任务 |
| --- | --- | --- | --- |
| `data/core/*.json` | 已实现 | 当前实际为 2 个 meta + 3 个 constitution law + 8 个 engine 文件 | 保持模块内容稳定，避免在代码中硬编码正文 |
| `data/packs/*.json` | 已实现 | 当前 Pack 文件由 `Conductor` 读取并分发给 Forge | 后续可补充更多 Pack，但不影响现链路 |
| `data/dimension_map.json` | 已实现 | 当前为维度到 Pack 的主映射表 | 未来抽出显式 registry，并补充可维护元数据 |
| 显式维度 registry | 已实现 | 体验维度已迁入 `data/interview_dimensions.json` 并由代码加载 | 继续补强可点击泡泡文案与世界理解元数据 |

### 3.2 Prompt 层

| 组件 | 状态 | 当前事实 | 后续任务 |
| --- | --- | --- | --- |
| `prompts/interviewer_system_prompt.md` | 已实现 | 当前是旧 monolith 访谈员 prompt，仍承载现行 runtime | 作为当前基线保留；vNext 不再继续扩写，后续由独立 `Interview Composer` prompt 接替 |
| `prompts/interview_composer_system_prompt.md` | 部分实现 | 已新增 `Call 2` prompt 初版，但尚未接入运行时 | 继续从旧 monolith 提炼，直到完全承担 `InterviewComposer` 职责 |
| `prompts/dossier_updater_system_prompt.md` | 部分实现 | 已有 prompt 初稿，且已对齐 vNext dossier schema，但尚未接入运行时 | 接入 `Call 1` 独立调用，并补充少量实现期边界约束 |
| `prompts/bubble_composer_system_prompt.md` | 部分实现 | 已新增独立泡泡生成 prompt 初版 | 接入 `BubbleComposer`，并根据真实样本调优 `answer / advance` 边界 |
| `prompts/compile_output_system_prompt.md` | 部分实现 | 已新增独立 compile prompt 初版 | 若 `CompileOutput` 继续由 LLM 收束生成，则接入 compile 阶段并与 `FrozenCompilePackage` 构造流程对齐 |
| `prompts/subagent_system_prompt.md` | 已实现 | Forge 子代理模板已接线 | 未来可增强 Pack 间一致性约束 |

### 3.3 运行时层

| 组件 | 状态 | 当前事实 | 后续任务 |
| --- | --- | --- | --- |
| `interview_controller.py` | 已实现 | 4 阶段状态机；Mirror 条件为 `untouched <= 2` 或 `turn >= 6` | 参数后续可配置化 |
| `interviewer.py` | 已实现 | 负责多轮访谈、Mirror/Landing/Complete 流转与 artifacts 输出 | 下一步拆成 `Call 1 Dossier Updater + Call 2 Interview Composer + Call 3 BubbleComposer` 管线 |
| dossier updater runtime | 计划中 | 当前无独立 dossier 更新调用 | 新增独立低温结构化调用，更新两份 dossier |
| steering hint | 已实现 | 基于上一轮 snapshot 和最新输入长度调整 probing 顺序 | 未来如需更重策略，再单独设计 |
| bubble generator | 部分实现 | 当前已从随机 tag 转为后端 deterministic 规则生成，但仍主要依赖题面切片与维度 phrase bank | 升级为独立 `BubbleComposer`，从当前用户心智视角生成 `bubble_candidates` |
| `conductor.py` | 已实现 | 纯代码路由，不是二次 LLM 指挥层 | vNext 继续只吃 `CompileOutput`，不引入 dossier 消费 |
| `forge.py` | 已实现 | 并发生成规则片段 | 下一步改为读取 `FrozenCompilePackage.compile_output + forge_context` |
| `assembler.py` | 已实现 | `generate_json()` 提取 8 个 core 变量后组装 | 下一步改为读取 `FrozenCompilePackage.compile_output + assembler_context` |

### 3.4 API / Session / Packaging 层

| 组件 | 状态 | 当前事实 | 后续任务 |
| --- | --- | --- | --- |
| `api_models.py` | 已实现 | 已定义 `BackendPhase`、请求/响应模型、`ErrorResponse` | 保持与前端 `types.ts` 同步 |
| `session_store.py` | 已实现 | 当前仅内存态 `InMemorySessionStore` | 下一步把 `world_dossier / player_dossier / last_compiled_turn` 纳入 session state |
| `service.py` | 已实现 | 已承接 `start / message / generate` 业务逻辑 | 下一步承接双调用编排、dossier 持久化与接口升级 |
| `api.py` | 已实现 | FastAPI 路由、`ArchitectServiceError` 包装与 422 统一错误包装已落地 | 后续增加更细的观测与日志 |
| `result_packager.py` | 已实现 | 输出产品展示用 `BlueprintSummary` | 当前版本保持轻摘要，只吃 `CompileOutput` |

### 3.5 前端骨架

| 组件 | 状态 | 当前事实 | 后续任务 |
| --- | --- | --- | --- |
| `frontend/src/App.tsx` | 已实现 | 维护 `UiPhase` 与生成流程 | 后续拆更清晰的结果/错误层 |
| `MirrorView` / `LandingView` / `GenerationView` | 已实现 | 对应主流程关键节点 | 继续收口细节文案和交互动画 |
| `CompleteView` + `PromptInspector` | 已实现 | 当前蓝图结果层由 `CompleteView` 承载，Prompt 查看器为独立组件 | 后续如需更细，可再拆内部子组件 |
| 前端自动化测试 | 已实现 | 当前已有最小交互回归测试（Q1、Mirror、Generate Retry） | 后续继续扩充覆盖范围 |

## 4. vNext 正式契约

### 4.1 Phase 契约

后端只返回 4 个 `BackendPhase`：

- `interviewing`
- `mirror`
- `landing`
- `complete`

前端额外维护 3 个本地 `UiPhase`：

- `idle`
- `q1`
- `generating`

实施原则：

- 不向后端新增 `q1` 和 `generating`
- 不把前端展示态混进后端协议

### 4.2 Compile Output 契约

vNext 不再把 `InterviewArtifacts` 当作长期概念继续扩写。

当前代码中的 `InterviewArtifacts` 仅视为旧实现名称；进入 vNext 后，唯一合法的编译语义摘要统一命名为 `CompileOutput`。

正式字段：

- `confirmed_dimensions`
- `emergent_dimensions`
- `excluded_dimensions`
- `narrative_briefing`
- `player_profile`

实施原则：

- `CompileOutput` 是 `State Layer` 收束后的最小稳定语义摘要，不是另一份长期状态
- `/api/generate` 与后续 `Conductor / Forge / Assembler / ResultPackager` 的主输入以这组字段为准
- 不让前端从 `system_prompt` 反解析这些信息
- 不允许并行维护另一套与其语义重叠的“final artifacts”命名体系
- `CompileOutput` 必须在 Landing 完成后生成并冻结，不允许在每次生成时重新漂移
- 如果 `CompileOutput` 的收束步骤继续通过 LLM 完成，则必须使用独立 `compile_output_system_prompt.md`，不允许复用 `InterviewComposer` prompt

配套冻结规则：

- `CompileOutput` 不直接承担下游 flavor context
- vNext 额外定义 `FrozenCompilePackage` 作为唯一冻结下游输入包
- `FrozenCompilePackage` 结构固定为：

```ts
type FrozenCompilePackage = {
  compile_output: CompileOutput;
  forge_context: ForgeContext;
  assembler_context: AssemblerContext;
}
```

- `CompileOutput` = 唯一编译语义摘要
- `FrozenCompilePackage` = 唯一下游冻结输入包
- Delivery 层只读 `FrozenCompilePackage`，绝不再读 live dossier

### 4.2A Twin Dossier 契约

这是下一阶段要补上的正式能力，目前状态为 `计划中`。

问题定义：

- 当前逐轮稳定维护的只有 `routing_snapshot`
- `narrative_briefing` 与 `player_profile` 只在访谈结束后一次性生成
- 因此系统虽然“知道碰过哪些维度”，却没有把“现在理解到的世界是什么、用户真正偏好的情绪与代入方式是什么”逐轮固化下来
- 直接后果是：
  - 后续问题偶尔偏题
  - 泡泡像系统自说自话
  - Mirror 与最终蓝图前的总结不一定打到用户心里

目标：

- 让最终三交付成果不再只在最后一轮临时总结，而是在每一轮都维护两份可复用的 dossier
- 让四个核心消费者都基于这两份逐轮更新的理解，而不是只靠 LLM 的隐式记忆

四个主要消费者：

1. 访谈员问题生成器
2. 泡泡候选回答生成器
3. Mirror 生成器
4. Compile Output / 蓝图 / system prompt 生成链路

建议新增的逐轮认知状态：

```json
{
  "routing_snapshot": {
    "confirmed": [],
    "exploring": [],
    "excluded": [],
    "untouched": []
  },
  "world_dossier": {
    "world_premise": "当前理解下，这是什么世界",
    "tension_guess": "当前最可能的主张力判断，后续仍可修正",
    "scene_anchor": "这一轮最关键的画面锚点",
    "open_threads": ["仍在试探的悬而未决点"],
    "soft_signals": {
      "notable_imagery": ["用户关于世界的关键意象"],
      "unstable_hypotheses": ["尚未坐实但值得继续跟踪的世界判断"]
    }
  },
  "player_dossier": {
    "fantasy_vector": "用户真正想要进入的是哪种幻想位置",
    "emotional_seed": "他在追的核心情绪是什么",
    "taste_bias": "更偏压迫、爽感、细腻、冷硬、热血等哪一类",
    "language_register": "文风上更接近怎样的表达",
    "user_no_go_zones": ["用户明确不想进入的方向"],
    "soft_signals": {
      "notable_phrasing": ["用户这一轮最值得保留的原话"],
      "subtext_hypotheses": ["尚未完全坐实，但值得继续跟踪的用户判断"],
      "style_notes": "对文风密度、节奏、语气偏好的轻量备注"
    }
  },
  "change_log": {
    "newly_confirmed": [],
    "newly_rejected": [],
    "needs_follow_up": []
  }
}
```

设计约束：

- `world_dossier` 与 `player_dossier` 是长期状态，不是最终交付物的替代
- 两份 dossier 必须以结构化字段为主，但保留少量非结构化 `soft_signals`
- 字段要控制在最小必要集合，不做庞大画像系统
- 两份 dossier 必须每轮写入会话态，并在下一轮被四个消费者共享消费
- `world_dossier` 保存“这个世界正在被理解成什么”
- `player_dossier` 保存“这个用户正在被理解成什么”
- `tension_guess` 只能表示“当前主张力猜测”，不能被系统当作不可动摇的世界真理
- `user_no_go_zones` 用于约束系统不要持续往用户明确排斥的方向推进
- `soft_signals` 的职责不是替代结构化字段，而是保存那些容易在纯 JSON 枚举中丢失的字里行间细节

字段语义要求：

- 仅给字段名，不足以让模型稳定理解字段职责
- vNext 必须为 twin dossier 的每个正式字段补齐字段语义表
- `DossierUpdater` 不允许只靠字段名字面猜测字段含义
- 字段语义表必须同时服务：
  - `implementation_plan.md`
  - `dossier_updater_system_prompt.md`
  - 后续 schema / validator

正式要求的字段语义表内容：

1. `field_name`
2. `records`
   - 这个字段记录什么
3. `does_not_record`
   - 这个字段明确不记录什么
4. `granularity`
   - 该写到什么粒度，避免过粗或过细
5. `certainty_rule`
   - 允许写成“明确判断”还是“当前猜测”
6. `positive_example`
7. `negative_example`

执行原则：

- 先减少字段数，再增强字段定义
- 不允许靠“多字段覆盖更多情况”掩盖字段语义不清
- 对 UX 影响更大的字段，优先给出更严格的语义定义

### 4.2A.1 Twin Dossier Field Semantics Contract

本节定义 vNext 首批正式字段的内涵边界。后续如增字段，必须按同样格式补齐，不能只加字段名。

#### `world_dossier.world_premise`

- `records`
  - 当前系统理解下，这个世界最核心的整体命题与基本形态
- `does_not_record`
  - 详细百科设定
  - 局部事件流水账
- `granularity`
  - 1-2 句即可，必须能回答“这到底是什么世界”
- `certainty_rule`
  - 可以是当前稳定判断，但不应夸张为最终真理
- `positive_example`
  - `这是一个能力高度日常化、表面平稳但暗中被严格管理的校园异能世界。`
- `negative_example`
  - `学校、广播站、操场、老师、学生、失控事件、秩序……`

#### `world_dossier.tension_guess`

- `records`
  - 当前最可能的主张力判断，即这个世界目前最像围绕哪一种冲突或压力展开
- `does_not_record`
  - 永久主题定论
  - 所有冲突来源的完整列表
- `granularity`
  - 1 句，突出一个主张力即可
- `certainty_rule`
  - 只能写成“当前猜测”，后续允许被修正
- `positive_example`
  - `当前最主要的张力像是个人意志与上位秩序之间的压迫冲突。`
- `negative_example`
  - `这个世界的核心张力已经确定，之后都不能偏离这一点。`

#### `world_dossier.scene_anchor`

- `records`
  - 这一轮最能代表世界气味的一幅画面或一个瞬间
- `does_not_record`
  - 抽象主题词
  - 宏大设定总结
- `granularity`
  - 1 个清晰画面锚点，便于后续问题、Mirror 和蓝图复用
- `certainty_rule`
  - 可暂时性存在，后续可替换为更强锚点
- `positive_example`
  - `操场上的失控异能被广播站悄悄改写成一则普通事故通报。`
- `negative_example`
  - `异能、秩序、压迫感、紧张氛围。`

#### `world_dossier.open_threads`

- `records`
  - 当前仍值得继续追问、但尚未坐实的世界问题
- `does_not_record`
  - 已经确认的事实
  - 任意扩写的新设定
- `granularity`
  - 1-3 条即可，每条都必须能转化为后续追问
- `certainty_rule`
  - 必然是未决状态
- `positive_example`
  - `命令链条顶端究竟是具体的人，还是更无形的秩序。`
- `negative_example`
  - `这个世界还有很多可以探索的地方。`

#### `player_dossier.fantasy_vector`

- `records`
  - 用户真正想进入的幻想位置或身份感
- `does_not_record`
  - 题材标签
  - 笼统的“喜欢修仙/异能”
- `granularity`
  - 1 句，回答“用户想在这个世界里成为什么位置的人”
- `certainty_rule`
  - 可以是较稳定判断，但若证据不足应保持克制
- `positive_example`
  - `用户想站在一个被压住、被低估、但可以逐步翻身的位置。`
- `negative_example`
  - `用户喜欢修仙。`

#### `player_dossier.emotional_seed`

- `records`
  - 用户真正追求的核心情绪回报
- `does_not_record`
  - 表层风格词堆砌
- `granularity`
  - 1 句，回答“用户到底想感受到什么”
- `certainty_rule`
  - 可以是当前高概率判断，但不应装成绝对正确
- `positive_example`
  - `用户追的是被轻视后翻身、重新夺回主动权的情绪。`
- `negative_example`
  - `用户想要爽。`

#### `player_dossier.taste_bias`

- `records`
  - 用户整体偏好的口味方向
- `does_not_record`
  - 太细的节奏或镜头规则
- `granularity`
  - 1 句或短语组合，回答“整体更偏哪种味道”
- `certainty_rule`
  - 允许中等强度判断
- `positive_example`
  - `偏森严、压抑、克制，而不是轻松热闹。`
- `negative_example`
  - `喜欢很多不同东西。`

#### `player_dossier.language_register`

- `records`
  - 用户更接受什么表达密度和语言气质
- `does_not_record`
  - 具体文案模板
- `granularity`
  - 1 句，回答“系统应该怎么对他说话”
- `certainty_rule`
  - 应谨慎，不要因一两句原话就过度定型
- `positive_example`
  - `更接受意象密度较高、略带文学感但不过分堆砌的表达。`
- `negative_example`
  - `以后所有文案都必须写成古风散文。`

#### `player_dossier.user_no_go_zones`

- `records`
  - 用户明确排斥或反复表现出不想进入的方向
- `does_not_record`
  - 仅凭猜测得出的“可能不喜欢”
- `granularity`
  - 1-3 条，必须足够具体，便于系统避让
- `certainty_rule`
  - 只有证据明显时才写入
- `positive_example`
  - `不要让恋爱关系成为主导驱动力。`
- `negative_example`
  - `也许他不喜欢复杂设定。`

#### `world_dossier.soft_signals.notable_imagery`

- `records`
  - 用户或系统本轮里最值得保留的关键意象
- `does_not_record`
  - 所有出现过的名词
- `granularity`
  - 1-3 条短句
- `certainty_rule`
  - 可保留弱信号
- `positive_example`
  - `剑光像命令的延长线。`
- `negative_example`
  - `剑、光、天、山、风。`

#### `world_dossier.soft_signals.unstable_hypotheses`

- `records`
  - 尚未坐实但值得继续跟踪的世界判断
- `does_not_record`
  - 已确认设定
- `granularity`
  - 1-2 条即可
- `certainty_rule`
  - 必须明确是弱判断
- `positive_example`
  - `这个世界的控制感可能比表面看到的更制度化。`
- `negative_example`
  - `这个世界绝对由某个委员会控制。`

#### `player_dossier.soft_signals.notable_phrasing`

- `records`
  - 用户原话里最能体现偏好的句子或短语
- `does_not_record`
  - 普通流水句
- `granularity`
  - 1-3 条原话片段
- `certainty_rule`
  - 允许原样保留，不做过度解释
- `positive_example`
  - `不是逍遥自在的云游，而是森严的等级与命令。`
- `negative_example`
  - `我觉得这个还行。`

#### `player_dossier.soft_signals.subtext_hypotheses`

- `records`
  - 系统对用户隐性偏好的弱判断
- `does_not_record`
  - 明确结论
- `granularity`
  - 1-2 条
- `certainty_rule`
  - 必须保留“可能/也许/像是”语气
- `positive_example`
  - `他在意的也许不是修仙本身，而是被秩序压住后的向上挣扎。`
- `negative_example`
  - `他最想要的就是反抗父权。`

#### `player_dossier.soft_signals.style_notes`

- `records`
  - 与表达方式有关的轻量提示
- `does_not_record`
  - 具体句式模板
- `granularity`
  - 1 句短备注
- `certainty_rule`
  - 只能做轻提示，不可过度锁死文风
- `positive_example`
  - `偏好有画面感，但不喜欢过满过玄的修辞。`
- `negative_example`
  - `之后所有输出都必须完全模仿鲁迅。`

### 4.2A.2 Prompt Budget Discipline

字段粒度会直接影响 prompt 长度、模型注意力和长期稳定性，因此 vNext 必须遵守以下规则：

1. 不用增加字段数量来代替字段语义清晰度
2. `implementation_plan.md` 保留完整字段语义表
3. `dossier_updater_system_prompt.md` 只保留执行必需的字段说明，不重复整份长文档
4. `InterviewComposer` prompt 不重复解释全部字段，只消费必要字段切片
5. 若未来新增字段，必须先证明其 UX 价值，再评估其 prompt 成本
6. 当字段解释与模型注意力冲突时，优先压缩字段数量，而不是牺牲字段定义清晰度

更新时机：

1. 用户新输入到达
2. 先基于上一轮 twin dossier + 最新用户输入更新 dossier
3. 再基于更新后的 twin dossier 生成：
   - 下一轮问题
   - BubbleComposer 输入所需上下文
   - 或 Mirror
4. Landing 后，从 dossier 收束生成 `Compile Output`，再继续生成 `blueprint / system_prompt`

正式调用方式：

- `Call 1: Dossier Updater`
  - 输入：上一轮 `world_dossier + player_dossier`、最近对话片段、最新用户输入
  - 输出：更新后的 twin dossier JSON
- `Call 2: Interview Composer`
  - 输入：最新 twin dossier、必要对话片段、当前 phase
  - 输出：用户可见文本、question / Mirror text
- `Call 3: BubbleComposer`
  - 输入：`PlayerDossier`、`WorldDossier`、`RoutingSnapshot`、当前 `question`、最近 1 轮用户输入、必要时最近 1 轮 assistant 输出
  - 输出：`bubble_candidates`

架构要求：

- `Call 1` 必须独立调用，不与创作型输出合并
- dossier 不允许作为 `Call 2` 的顺手副产物存在
- `Call 2` 必须消费最新 twin dossier，而不是只看原始对话历史

原因：

- 三类任务的目标不同：状态更新求稳、问题表达求自然、候选回答模拟求贴合用户心智
- 把结构化更新、创作表达、bubble 生成拆开，更利于 repair、观测和问题定位
- 对格式遵循波动较大的模型，这种职责拆分比单次混合输出更稳

与最终三交付成果的关系：

- `routing_snapshot` 持续演化 -> 最终 `confirmed_dimensions / emergent_dimensions / excluded_dimensions`
- `world_dossier` 持续演化 -> 最终 `narrative_briefing`
- `player_dossier` 持续演化 -> 最终 `player_profile`
- 两份 dossier 的 `soft_signals` 持续积累 -> 为 Mirror 文风、蓝图措辞和最终 system prompt 的细部质感提供证据

### 4.2B 泡泡生成契约（下一迭代）

当前状态：`部分实现`

当前事实：

- 泡泡已不再直接信任原始 `suggested_tags`
- 后端已有 `bubble_suggester.py`
- 但当前机制仍以：
  - 题面字符串切片
  - 引号锚点模板
  - 维度 phrase bank
  为主

这解决了脏输出问题，但还没解决“真正贴合用户意图”的问题。

下一阶段的正式定义：

- 泡泡不再定义为“系统想继续问什么”
- 泡泡定义为“当前 dossier 所描绘出的这个用户，在看到当前问题时，最可能顺手接出的 2-3 个候选回答”
- 泡泡生成职责从 `InterviewComposer` 中剥离，独立为 `BubbleComposer`
- `BubbleComposer` 的角色不是系统继续提问，而是受 dossier 约束的“当前用户心智投影”

建议新增字段：

```json
{
  "bubble_candidates": [
    {
      "text": "闭关千年的老祖",
      "kind": "answer"
    },
    {
      "text": "庞大臃肿的长老会",
      "kind": "answer"
    },
    {
      "text": "命令本身像活物一样运转",
      "kind": "advance"
    }
  ]
}
```

规则：

- 每轮最多 3 个
- 默认结构为：
  - `1-2` 个 `answer`
  - `0-1` 个 `advance`
- 泡泡必须像“用户会说的话”，不是“系统会问的话”
- `advance` 表示：比用户当前显性表达更清晰半步，但仍必须落在 dossier 支撑的心智范围内
- 禁止回退成：
  - 抽象维度名
  - 题干残片
  - 纯粹的系统分析语言

输入依赖：

- 当前 `question`
- 当前 `routing_snapshot`
- `world_dossier`
- `player_dossier`
- 最近一轮用户输入

实现原则：

- 作为独立 `BubbleComposer` 调用生成 `bubble_candidates`
- 后端负责：
  - 结构校验
  - 去重
  - 长度限制
  - fallback
- 不把泡泡并入 `Call 1`
- 不把泡泡重新并回 `InterviewComposer`
- `BubbleComposer` 与 `InterviewComposer` 使用同一模型，但 prompt 与职责独立
- 必须新增专用 `bubble_composer_system_prompt.md` 编写任务，不能复用 `InterviewComposer` prompt 凑合

### 4.2C 接口与基建迭代要求

这不是单纯改 prompt。以下接口和基建都必须随 twin dossier 架构一起升级：

1. `api_models.py`
- interview turn response 需要新增正式字段：
  - `bubble_candidates`
  - typed `routing_snapshot`
- twin dossier 默认作为服务端内部状态，不默认暴露给前端
- `Compile Output` 取代旧 `InterviewArtifactsModel` 成为唯一正式编译接口模型
- `/api/generate` 的 vNext 请求模型只保留 `session_id`
- `suggested_tags` 在 vNext 中直接删除，不再走兼容字段路线
- vNext 前后端改造按原子发布执行，不保留双字段兼容窗口

2. `session_store.py`
- session record 需要持久化：
  - 当前 twin dossier
  - 已冻结的 `CompileOutput`
  - 已冻结的 `FrozenCompilePackage`
  - 最新一次 dossier update 的 turn
  - 最新一次 dossier update 的状态：
    - `updated`
    - `conservative_update`
    - `update_skipped`
    - `hard_failed`
  - 当前 turn transaction 的状态：
    - `pending_turn`
    - `pending_response_generation`
    - `pending_compile`
  - 当前 follow-up 信号（如 `mirror_rejected`）
  - dossier 版本号 / schema 版本（至少预留）

3. `service.py`
- 需要显式编排：
  - `Call 1: Dossier Updater`
  - `Call 2: Interview Composer`
  - `Call 3: BubbleComposer`
- Landing 完成后需要立即生成并写入 `CompileOutput`
- Landing 完成后需要基于 `CompileOutput + dossier 白名单切片` 立即冻结 `FrozenCompilePackage`
- `/api/generate` 默认只消费 session 中已冻结的 `FrozenCompilePackage`
- 需要定义 dossier 更新失败、composer 失败、bubble 失败的不同恢复路径
- 需要把 `dossier_update_status` 与轻量 follow-up 信号显式传给 `InterviewComposer`

4. `interviewer.py`
- 当前单次 creative call 管线需要拆开
- repair pass 需要覆盖 twin dossier 核心字段
- Mirror 与 Complete 阶段都要改成 dossier-aware
- Landing 完成后要显式生成 `CompileOutput`
- freeze `FrozenCompilePackage` 的动作必须基于已生成的 `CompileOutput` 执行，不得回读 live dossier

5. `frontend types + state`
- 前端类型需要显式接收 `bubble_candidates`
- 前端不再消费 `suggested_tags`
- 前后端协议切换按一次性原子发布实施
- 结果层如后续需要展示“系统当前理解”，必须通过单独、明确的派生字段暴露，而不是直接泄露 dossier

6. 质量回归基线
- 新增 dossier 稳定性样本
- 新增“同一用户连续多轮后 world/player dossier 是否漂移”的回归样本
- 新增“问题/泡泡/Mirror/蓝图是否共用同一理解”的一致性样本

### 4.2D Mirror Contract

Mirror 在 vNext 中的正式角色：

- Mirror 不是普通中途总结
- Mirror 不是 `CompileOutput` 的提前版
- Mirror 是基于 twin dossier 生成的“高浓度理解回声”
- Mirror 的职责是让用户低成本判断：
  - 系统是否真的沿着他想要的世界在理解
  - 当前理解是否需要校正

Mirror 正常生成规则：

- Mirror 继续作为 `InterviewComposer` 的 phase mode
- Mirror 以 twin dossier 为主输入，不允许只基于最近一轮临场发挥
- Mirror 当前版本只输出文本，不附带额外结构信号
- Mirror 的文本目标是：
  - 有画面
  - 有压缩后的理解感
  - 能让用户快速判断“对 / 不对”

Reject 正式流程：

1. 用户点击 `我得再想想`
2. 系统不重新生成 Mirror
3. 系统写入一次轻量事件信号：
   - `change_log.needs_follow_up += ["mirror_rejected"]`
4. 不立即重写 `WorldDossier / PlayerDossier` 的核心字段
5. 回到 Interview 阶段
6. `InterviewComposer` 下一问进入单轮 recovery 行为：
   - 必须是校正型问题
   - 必须具体、场景化、非 meta
   - 不允许变成“系统在和用户讨论自己的理解过程”
7. 用户回答后，再由 `DossierUpdater` 依据新证据修正 twin dossier
8. 至少再进行 1-2 轮访谈后，才允许再次进入 Mirror

Reject 设计原则：

- reject 的含义是“当前理解没打中”，不是“这段文字不够漂亮”
- reject 后先问，再修 dossier；不允许先靠猜测重写核心理解
- recovery 信号只持续 1 轮，不应成为长期模式

为什么这样设计：

- 直接重新生成 Mirror，本质上只是系统再猜一轮，UX 价值很低
- 重型 `mirror_recovery mode` 会增加 prompt 负担，并破坏访谈沉浸感
- 轻量 recovery flag + 单轮校正问题，在核心 UX 和即时 UX 之间成效比最佳

### 4.3 结果页契约

当前正式输出：

- `blueprint`
- `system_prompt`

其中：

- `system_prompt` 是 Architect 的真正终产物
- `blueprint` 是共享同一份生成结果的次级展示产物
- 普通用户默认只感知到：
  - Landing 结束
  - 世界成形中
  - 蓝图展示页
- 只有硬核用户通过二级入口查看和复制完整 `system_prompt`

注意：

- 当前代码中不存在单独的 `BlueprintView` 组件
- “蓝图结果层”是产品概念层，当前由 `CompleteView` 承载

### 4.4 已拍板 Task 决议

以下事项均已完成拍板，作为 vNext 一次性整迭代实现的正式基线保留在此处，避免后续讨论再次漂移。

#### Task 1：状态模型粒度

本轮决议范围：

- `WorldDossier` 是否保持最小字段集，还是继续补充更细世界理解字段
- `PlayerDossier` 是否保持最小字段集，还是补更多用户偏好字段
- `CompileOutput` 是否只保留最小 5 字段，还是补 tone / style 派生字段

主要考量：

- 优先看对 UX 的影响：理解是否更准、问题是否更贴心、Mirror 和蓝图是否更打动人
- 性能与代码稳定性作为辅助约束

当前结论：

- `WorldDossier` 维持中轻量字段集
- 原 `core_tension` 正式改名为 `tension_guess`
- `PlayerDossier` 额外新增 `user_no_go_zones`
- 当前版本不新增 `stakes_model / conflict_source / power_shape`
- `CompileOutput` 继续保持最小 5 字段
- 新增 `FrozenCompilePackage` 承载冻结后的下游输入，不把 `ForgeContext / AssemblerContext` 塞回 `CompileOutput`

#### Task 2：上下文输入策略

本轮决议范围：

- `DossierUpdater` 吃全量历史，还是窗口化历史
- `InterviewComposer` 吃 dossier 为主，还是仍大量吃原始历史
- 是否引入“摘要化历史”这一中间层

主要考量：

- 优先看对 UX 的影响：系统是否持续记得用户、是否出现前后失忆或跑偏
- 性能与上下文稳定性作为辅助约束

当前结论：

- `DossierUpdater` 输入：
  - 上一版 `WorldDossier`
  - 上一版 `PlayerDossier`
  - 上一版 `RoutingSnapshot`
  - 最近 3 轮完整问答
  - 最新用户输入
- `InterviewComposer` 输入：
  - 最新 twin dossier
  - 最近 1-2 轮必要语境
  - 当前 phase
  - `dossier_update_status`
  - 轻量 follow-up 信号（如 `mirror_rejected`）
- 当前版本不采用“全量历史直喂”
- 当前版本不引入单独的“摘要化历史”层

决策原因：

- 全量历史虽然不容易失忆，但会明显增加上下文窗口压力，并放大“被早期一句话绑死”的 UX 风险
- `DossierUpdater` 需要看到足够近的演化过程，才能稳定修正理解
- `InterviewComposer` 的任务是表达当前理解，不是重新阅读整段人生史

#### Task 3：Bubble 策略

本轮决议范围：

- 泡泡继续并入 `InterviewComposer`，还是这版就拆独立调用
- `bubble_candidates` 是否只保留 `text + kind`
- `answer / advance` 的比例是否固定

主要考量：

- 优先看对 UX 的影响：泡泡是否像用户会顺手点下去的回答，而不是系统标签
- 性能与解析复杂度作为辅助约束

当前结论：

- 泡泡从 `InterviewComposer` 中独立，正式新增 `BubbleComposer`
- `BubbleComposer` 扮演“当前 dossier 所描绘出的这个用户”
- 输入：
  - `PlayerDossier`
  - `WorldDossier`
  - `RoutingSnapshot`
  - 当前 `question`
  - 最近 1 轮用户输入
  - 必要时最近 1 轮 assistant 输出
- 输出结构只保留：
  - `text`
  - `kind`
- 类型固定为：
  - `answer`
  - `advance`
- 数量规则固定为：
  - `1-2 answer`
  - `0-1 advance`
- 允许 fallback，但 fallback 只能作为兜底，不能继续作为主路径

决策原因：

- 如果 bubble 定义为“用户可能会如何回答”，那它与纯系统侧 `InterviewComposer` 存在天然角色冲突
- 独立后的 `BubbleComposer` 才能从用户心智视角生成候选回答，而不是继续输出系统想推进的话题
- `advance` 的职责是比用户当前显性表达更清晰半步，而不是越界替用户发明欲望

#### Task 4：Mirror 策略

本轮决议范围：

- Mirror 这版是否继续作为 `InterviewComposer` 的 phase mode
- reject 后是否必须先修正 dossier，再重新生成问题
- Mirror 是否只输出文本，还是附带轻量结构信号

主要考量：

- 优先看对 UX 的影响：Mirror 是否真正像“你被理解后的世界回声”
- 运行时复杂度作为辅助约束

当前结论：

- Mirror 继续作为 `InterviewComposer` 的 phase mode
- Mirror 以 twin dossier 为主输入，不允许只看最近一轮临场生成
- Mirror 当前版本只输出文本，不附带额外结构信号
- 用户点击 reject 后：
  - 不重新生成 Mirror
  - 不立即重写核心 dossier
  - 只写入一次轻量 `mirror_rejected` follow-up 信号
  - 回到 Interview 阶段
  - 由 `InterviewComposer` 生成 1 个具体、场景化、非 meta 的校正问题
  - 用户回答后，再由 `DossierUpdater` 修正 twin dossier
  - 至少再进行 1-2 轮访谈后，才允许再次进入 Mirror

决策原因：

- Mirror 本质上仍然是系统侧回声，不必在本轮继续拆成独立调用
- reject 后直接重出 Mirror，只会让系统再猜一轮，无法真正提升理解
- 重型 recovery mode 会增加 prompt 负担，并让问题变得更 meta
- 轻量 recovery flag + 单轮校正问题，在成品质量与即时沉浸感之间更平衡

#### Task 5：Compile 触发与 `/api/generate` 策略

本轮决议范围：

- `CompileOutput` 在 Landing 后立即生成，还是在 `/generate` 时懒生成
- `/api/generate` 是否只接受 `session_id`
- 是否允许前端显式传入 `CompileOutput`

主要考量：

- 优先看对 UX 的影响：生成体验是否稳定、失败恢复是否清晰、用户是否会遇到“前后不一致”
- 状态管理复杂度作为辅助约束

当前结论：

- `CompileOutput` 在 Landing 完成后立即生成并冻结
- `FrozenCompilePackage` 在 `CompileOutput` 生成后立即构造并冻结
- 系统在 Landing 结束后自动进入内部 `generating` 阶段
- `/api/generate` 是内部生成接口，不是用户显式感知的功能按钮
- `/api/generate` 只接受 `session_id`
- 前端不允许显式传入 `CompileOutput`
- `/api/generate` 的主职责是基于已冻结的 `FrozenCompilePackage` 生成：
  - `SystemPrompt`
  - `Blueprint`
- 其中：
  - `SystemPrompt` 是主产物
  - `Blueprint` 是共享同一份结果的展示层副产物
- 生成失败时默认只重试生成链，不重新 compile
- 仅当 session 中缺失 `FrozenCompilePackage` 时，后端才允许一次“重新 freeze”级别兜底

决策原因：

- 如果 `CompileOutput / FrozenCompilePackage` 不在 Landing 后冻结，后续每次生成都有机会重新解释用户，最终 `SystemPrompt` 会漂
- 用户不应感知“系统提示词生成”这层内部细节，只应感知世界正在成形并最终看到蓝图
- `/api/generate` 若允许前端传入 `CompileOutput`，会重新制造双真相源
- 重试时若重新 compile，会让用户感到系统每次失败都在重新理解自己

#### Task 6：Delivery 层消费深度

本轮决议范围：

- `Assembler` 是否只吃 `CompileOutput`
- `Blueprint` 是否只吃 `CompileOutput`
- dossier 是否允许作为 delivery 层的补充上下文

主要考量：

- 优先看对 UX 的影响：最终蓝图和 system prompt 是不是只有结构正确，还是能真正贴近用户
- 边界清晰度作为辅助约束

当前结论：

- Delivery 层只读 `FrozenCompilePackage`，不读 live dossier
- `Conductor` 继续只吃 `FrozenCompilePackage.compile_output`
- `Forge` 采用：
  - `FrozenCompilePackage.compile_output`
  - `FrozenCompilePackage.forge_context`
- `Assembler` 采用：
  - `FrozenCompilePackage.compile_output`
  - `FrozenCompilePackage.assembler_context`
- `Blueprint` 当前版本定位为轻度摘要，只吃 `CompileOutput`
- 不允许任何 delivery 层模块直接吃完整 dossier

`ForgeContext` 白名单：

- `world_dossier.world_premise`
- `world_dossier.tension_guess`
- `world_dossier.scene_anchor`
- `player_dossier.fantasy_vector`
- `player_dossier.emotional_seed`
- `player_dossier.taste_bias`
- `player_dossier.language_register`
- `player_dossier.user_no_go_zones`

`AssemblerContext` 白名单：

- `world_dossier.world_premise`
- `world_dossier.tension_guess`
- `world_dossier.scene_anchor`
- `world_dossier.soft_signals.notable_imagery`
- `player_dossier.fantasy_vector`
- `player_dossier.emotional_seed`
- `player_dossier.taste_bias`
- `player_dossier.language_register`
- `player_dossier.user_no_go_zones`
- `player_dossier.soft_signals.notable_phrasing`
- `player_dossier.soft_signals.style_notes`

明确不进入 delivery 层的 dossier 字段：

- `world_dossier.open_threads`
- `world_dossier.soft_signals.unstable_hypotheses`
- `player_dossier.soft_signals.subtext_hypotheses`

决策原因：

- `Conductor` 是纯路由层，若引入 dossier 会污染模块选择逻辑
- `Forge` 需要一点冻结 flavor 来让 pack 改写更像这次用户的世界，但不应在生成时再读取 live dossier
- `Assembler` 负责全局体验层与统一气质，最有必要读取受控 dossier flavor，但这些 flavor 必须先被冻结
- `Blueprint` 战略地位较低，当前不值得为其引入更复杂的 dossier 消费

#### Task 7：失败恢复策略

当前结论：

- 失败恢复按层级区分，不允许“一刀切”
- 总原则：
  - 理解层失败，不能带着脏理解继续推进
  - 表达层失败，允许只重试表达，不回滚已获得的真实理解
  - 辅助层失败，优先降级，不阻断主流程
  - 生成层失败，只重试生产，不重新理解用户

事务语义：

- 每一轮用户输入都按一次 turn transaction 处理：
  1. 接收用户输入
  2. 标记 pending turn
  3. 运行 `DossierUpdater`
  4. 运行 `InterviewComposer` / `Mirror`
  5. 运行 `BubbleComposer`
  6. 根据成功、降级或失败决定提交 / 阻断 / 重试
- 这不是额外用户可见阶段，而是服务端内部执行语义

`DossierUpdater` 恢复策略：

- 先内部重试 `1` 次
- 若仍然不稳，先区分：
  - 软失败：
    - 典型情况是证据不足、冲突过强、只适合保守更新
    - 不前端报错
    - 不覆盖核心 dossier 字段
    - 标记本轮为 `update_skipped` 或等价低置信状态
    - 继续沿用旧 dossier 进入下一问
  - 硬失败：
    - 典型情况是超时、无可解析 JSON、schema 不成立、关键字段缺失
    - 若无安全 fallback，则阻断本轮
    - 不推进 phase
    - 不覆盖旧 dossier
    - 保留当前 user turn 为 pending，可重试

`InterviewComposer` 恢复策略：

- 若 `DossierUpdater` 已成功，本轮新 dossier 必须保留
- `InterviewComposer` 失败时先内部重试 `1` 次
- 若仍失败：
  - 不要求用户重输
  - 不回滚本轮 dossier 更新
  - 标记 `pending_response_generation`
  - 前端显示可恢复错误
  - 用户重试时只重试 `InterviewComposer`
- 不允许降级成通用问题，否则会明显损伤“系统懂我”的体验

`BubbleComposer` 恢复策略：

- 先内部重试 `1` 次
- 若仍失败：
  - 不阻断主流程
  - 当前轮允许无 bubbles
  - 不再使用低质量 heuristic 结果冒充正常 bubbles

`CompileOutput` 冻结失败恢复策略：

- Landing 完成后冻结 `CompileOutput` 时先内部重试 `1` 次
- 若仍失败：
  - 不进入生成链
  - 保留 twin dossier
  - 前端进入可恢复的生成失败态
  - 重试优先重新执行 `CompileOutput -> FrozenCompilePackage` freeze，再继续 `/api/generate`

`/api/generate` 后半生成链恢复策略：

- `Conductor / Forge / Assembler / ResultPackager` 任一环节失败时：
  - 默认只重试生成链
  - 不重新 compile
  - 不重新理解用户
- 只有 session 中缺失 `FrozenCompilePackage` 时，才允许一次后端重新 freeze 兜底

设计原因：

- 真正伤核心 UX 的不是显式报错，而是系统带着错误理解一路滑进最终 `SystemPrompt`
- 真正伤即时 UX 的也不是所有失败，而是把“正常不确定”直接升级成前端 Fatal Error
- 因此 vNext 必须明确区分：
  - 正常更新
  - 保守更新
  - update skipped
  - hard failed

## 5. 仍需推进的实施项

### 5.1 高优先级

1. 为访谈链路引入 Twin Dossier 维护层
2. 用 twin dossier 重构 `Call 2` 的问题生成
3. 引入 `BubbleComposer`，让泡泡从用户心智视角生成
4. 用 twin dossier 重构 Mirror、Compile Output、蓝图与 system prompt 链路
5. 为真正的 token-by-token 流式输出接入 SSE
6. 为 repair pass 增加观测与告警统计
7. 评估是否需要把 DeepSeek 专属 Prompt 进一步拆成独立模板文件
8. 明确 Runtime 对 `system_prompt` 的消费协议

### 5.2 中优先级

1. 明确 `Blueprint` 的字段生成规则和可维护标准（当前代码中的旧实现名为 `BlueprintSummary`）
2. 给 `Forge` 和 `Assembler` 增加更可读的观测/日志接口
3. 让关键运行参数具备配置入口，而不是只靠模块常量
4. 视质量决定是否继续细拆 Bubble / Mirror 的生成职责

### 5.3 低优先级

1. Session 持久化
2. 更细的 Prompt/Pack 版本管理
3. 更丰富的世界模板库

## 6. 与 Runtime 的边界

本文件只覆盖 `Architect`。

当前明确不在本计划内宣称完成的内容：

- Runtime 长期记忆系统
- Runtime 世界状态容器
- Architect -> Runtime 程序级接线
- Runtime 的会话循环与事件引擎

与 Runtime 的当前真实边界只有：

- 当前代码中的 `BlueprintSummary`（vNext 对应 `Blueprint`）
- `system_prompt`

下一阶段如果要推进 Runtime，应该新增独立实施计划，而不是继续把 Runtime 融进本文件冒充已实现。

## 7. 验证基线

### 已完成验证

- 后端自动化测试：`23/23`
- 前端自动化测试：`3/3`
- 前端构建：通过

### 当前测试覆盖点

- 访谈状态机
- steering 路由
- Conductor 映射
- mock pipeline 全链路
- `Blueprint` 打包（当前代码中的旧实现名为 `BlueprintSummary`）
- service / API 契约

### 仍需补的验证

- Live LLM 条件下的质量回归样本
- 更明确的失败分类与恢复路径测试
- “问题/泡泡/Mirror/最终蓝图”语义连续性的质量回归样本

## 8. 本功能迭代计划

本节只覆盖“基于两份 dossier 重构 Architect 四个核心功能”这条功能线。

### Iteration 1：引入 Twin Dossier 基建

目标：

- 让 `Interviewer` 每轮维护两份 dossier
- 其中至少包含：
  - `routing_snapshot`
  - `world_dossier`
  - `player_dossier`
  - `change_log`

范围：

- 扩展 interview turn JSON schema
- 会话态中新增 twin dossier
- 拆出 `Dossier Updater` 调用
- 接入 `prompts/dossier_updater_system_prompt.md`
- steering prompt / composer prompt 注入 twin dossier 核心字段
- 不改前端展示

验收标准：

- 每轮都有可解析的 twin dossier
- repair pass 能补 twin dossier 核心字段
- 不破坏现有 Mirror/Landing/Complete 主链路

### Iteration 2：让访谈员基于 Twin Dossier 生成问题

目标：

- `Call 2` 真正基于 twin dossier 生成问题
- 让问题本身先稳定贴近 dossier 中的理解

范围：

- `InterviewComposer` 正式切到 dossier-driven
- 当前问题生成不再依赖全量历史
- `suggested_tags` 直接从 vNext 协议中删除

验收标准：

- 问题本身开始更稳定地贴合 dossier 中的理解
- 同一用户多轮后，问题不再明显回退到早期误判

### Iteration 3：引入 BubbleComposer

目标：

- 将泡泡从 `InterviewComposer` 中独立出来
- 让泡泡从“系统方向提示”升级为“当前用户心智下的候选回答”

范围：

- 新增 `Call 3: BubbleComposer`
- 新增专用 `bubble_composer_system_prompt.md` 编写与接线任务
- 后端按 `answer/advance` 分类校验
- 前端优先消费 `bubble_candidates[].text`
- 引入 bubble fallback，但不再以 deterministic 规则作为主路径

验收标准：

- 同一题面下的泡泡明显更贴题
- 泡泡不再大量出现题干残片
- 泡泡与 world/player dossier 的一致性提升
- `advance` 类型不会明显越界重写用户意图

### Iteration 4：Mirror、Compile Output 与 system prompt 链路改为 dossier-aware

目标：

- Mirror、最终 `narrative_briefing/player_profile`、`Compile Output` 和最终 system prompt 都开始显式消费 twin dossier

范围：

- Mirror prompt 注入 dossier
- `_complete_interview()` 生成 `Compile Output` 时显式消费 dossier
- `result_packager` 改为严格只消费 `Compile Output`
- 引入 `FrozenCompilePackage`，将 `CompileOutput + dossier 白名单上下文` 一次性冻结
- `Forge` / `Assembler` 的输入语义与 `FrozenCompilePackage` 对齐
- 增加“世界理解是否持续稳定”的质量回归样本

验收标准：

- Mirror 与最终蓝图前总结的击中率提升
- 问题、泡泡、Mirror、`Compile Output` 之间语义连续
- `SystemPrompt` 不再只是“题材正确”，而是更贴近 dossier 累积出的内核
- `Blueprint` 继续保持轻摘要，但与 `Compile Output` 保持稳定一致

### Iteration 5：评估是否需要进一步拆分 Bubble / Mirror 生成

目标：

- 只在前 4 个迭代仍不足以稳定质量时，评估是否继续拆更细的生成职责

评估标准：

- `BubbleComposer` 是否仍长期不稳
- Mirror 是否需要进一步独立 prompt / 调用
- 额外一次调用带来的时延是否值得
- fallback 与恢复机制是否足够清晰

默认结论：

- 先不继续拆更多调用
- 先把“Twin Dossier + DossierUpdater + InterviewComposer + BubbleComposer”做到位

## 9. 下一阶段顺序

建议按以下顺序推进，而不是并行摊大饼：

1. 落地 `Call 1: Dossier Updater` 与 twin dossier session state
2. 升级 `Call 2`，让问题生成先消费 twin dossier
3. 落地 `Call 3: BubbleComposer`
4. 用 twin dossier 重做 Mirror、交付物与蓝图链路
5. 再评估是否需要进一步拆分 Bubble / Mirror
6. 再评估 SSE 与 Runtime 接线
7. 单开 Runtime 计划文档并启动实现

## 10. 结论

`implementation_plan.md` 的职责不是证明项目“已经完成”，而是把开发真实位置标出来。

截至 2026-03-12：

- `Architect` 已经是可运行的世界编译器
- 它下一阶段的核心不是“再堆功能”，而是把访谈理解从隐式记忆升级成 twin dossier 驱动的显式认知架构
- `Runtime` 还不能写进“已实现”栏

后续维护本文件时，任何新增条目都必须先回答一句话：

`这是代码事实，还是开发计划？`
