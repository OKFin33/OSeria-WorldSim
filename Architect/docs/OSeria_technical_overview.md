# OSeria 项目技术说明（总览版）

> 版本：v0.1 stable  
> 日期：2026-03-13  
> 用途：黑客松交付物、团队内部对账文档、Runtime 设计输入  
> 方法：代码优先；当 spec、日志与实现冲突时，以 `Architect/` 当前代码为准

## 1. 文档定位

本文档描述的是 OSeria 的当前正式技术架构、设计动机、实现方案、实现边界与预期效果。

它不是开发过程记录，也不是路线图。  
过程性决策、分歧和线程复盘，统一下沉到：

- `Architect/docs/implementation_plan.md`
- `Architect/docs/logs/架构Log.md`

OSeria 是一个两段式系统：

1. `Architect`
   负责访谈、状态收束、世界编译和交付物生成。
2. `Runtime`
   负责承接 `system_prompt` 进入持续互动小说 / SillyTavern 式运行。

当前仓库里真正落地的主要是 `Architect`。  
因此本文档对两段系统的书写深度不同：

- `Architect`：写到实现级别
- `Runtime`：只写职责边界和当前可确认的交接面

## 2. OSeria 当前正式架构

```mermaid
flowchart LR
    U["User"] --> FE["Architect Frontend<br/>React + Vite"]
    FE --> API["Architect API / Service<br/>FastAPI + Session"]
    API --> ST["Architect State Layer"]
    ST --> CP["Architect Compile Layer"]
    CP --> DL["Architect Delivery Layer"]
    DL --> OUT["BlueprintSummary + system_prompt"]
    OUT -. handoff boundary .-> RT["Runtime (not implemented)"]
```

其中，`Architect` 的正式功能架构已经收口为三层：

1. `State Layer`
   负责访谈状态、用户理解和世界理解的持续收束。
2. `Compile Layer`
   负责把稳定语义摘要编译为下游可消费的模块化规则系统。
3. `Delivery Layer`
   负责把编译结果交付为面向人读的 `blueprint` 与面向 Runtime 的 `system_prompt`。

当前代码中完整跑通的主链路是：

`Interviewer -> Conductor -> Forge -> Assembler -> ResultPackager`

这条链路已经证明 `Architect` 不是一段一次性 Prompt，而是一条可运行的世界编译链。  
同时，三层正式架构中的部分对象和接口已经拍板，但尚未全部接入当前运行主链路；这一点会在第 6 节明确写出。

## 3. Architect：为什么采用这种设计

`Architect` 的分层不是为了把模块名写得更漂亮，而是为了解决当前系统已经暴露出的四类工程问题。

### 3.1 避免“理解用户”与“编译规则”混成一层

如果访谈过程、语义收束、模块路由和最终拼装都在一个单体流程里完成，系统会不断重新解释用户，最终让：

- 访谈阶段和生成阶段各自保留一套理解
- 同一语义被重复命名、重复总结、重复漂移
- `/generate` 变成一次新的“再理解用户”

因此正式架构强制把：

- 长期状态
- 编译摘要
- 下游交付

拆开处理。

### 3.2 避免下游世界化深度分配失衡

当前主链路已经能根据维度 pack 生成世界规则，但问题也很明确：

- 少数 forged section 很像这次用户的世界
- 部分 `meta / eng` 模块仍保留较强模板口吻
- 如果继续只靠“命中 pack 就 forge”这一种开关，后续只会放大拼装感和 section 粘连

因此正式架构把下游目标定义为“模块分层世界化”：

- 不是所有模块都 full forge
- 而是整份 `system_prompt` 都参与世界化，只是深度不同

### 3.3 避免 Assembler 退化为补锅层

如果模块策略不清、上下文冻结不清、输入边界不清，最后所有脏活都会堆到 `Assembler`：

- 去重
- 修补语气
- 掩盖模板残渣
- 替别人做二次创作

这会让编译链越来越不可控。  
因此 `Assembler` 的正式定位被固定为轻编译器，而不是重型补锅层。

## 4. Architect：具体技术实现方案

### 4.1 State Layer

正式对象边界如下：

- `routing_snapshot`
- `world_dossier`
- `player_dossier`

它们的职责分别是：

- `routing_snapshot`：访谈流程控制、维度覆盖和阶段判断
- `world_dossier`：系统对用户想进入什么世界的持续理解
- `player_dossier`：系统对用户偏好、语言气质和禁区的持续理解

当前实现中的落地点主要在访谈运行时：

- 对应文件：
  - `interviewer.py`
  - `interview_controller.py`
  - `dimension_registry.py`
  - `bubble_suggester.py`
  - `data/interview_dimensions.json`
  - `prompts/interviewer_system_prompt.md`
- 当前职责：
  - 固定开场问题
  - 维护 `interviewing / mirror / landing / complete` 四态
  - 加载显式维度 registry
  - 将维度菜单注入访谈 prompt
  - 生成问题文本与系统 JSON
  - 解析并维护 `routing_snapshot`
  - 通过 `BubbleSuggester` 生成 deterministic 泡泡
  - 在模型格式失真时执行 repair pass

当前访谈状态机的代码事实：

- 后端 phase 只有 4 个：`interviewing / mirror / landing / complete`
- `Mirror` 触发由代码控制，不由模型自行拍板
- 触发条件为：
  - `untouched <= 2`
  - 或 `turn >= 6`

### 4.2 Compile Layer

正式对象边界如下：

- `CompileOutput`
- `FrozenCompilePackage`

正式模块边界如下：

- `Conductor`
- `Forge`
- `Assembler`

这层的正式职责是：  
先把访谈结果收束为唯一编译语义摘要，再把冻结后的编译输入交给下游模块编译，不允许在生成时回读 live state。

#### Conductor

对应文件：

- `conductor.py`
- `data/dimension_map.json`

当前实现职责：

- 接收访谈产物
- 将 `confirmed_dimensions` 映射到 Pack
- 处理 `requires` 和 `also_consider`
- 保留未知维度任务
- 输出 `ForgeManifest`

正式定位：

- `Conductor` 是代码路由层，不是二次 LLM 指挥层
- 它负责决定哪些模块执行、以什么模式执行
- 它不负责重新理解用户

#### Forge

对应文件：

- `forge.py`
- `prompts/subagent_system_prompt.md`

当前实现职责：

- 为每个维度任务渲染子代理 prompt
- 使用 `asyncio.gather()` 并发生成规则片段
- 为无模板维度提供 fallback 生成路径
- 输出 `dict[dimension, forged_rule_text]`

正式定位：

- `Forge` 负责模块级世界化
- 它不是“凡是下游内容都重写一遍”的总生成器

根据最新实施计划，Compile Layer 的正式世界化策略已经固定为四档：

1. `Hard Lock`
2. `Parameterized`
3. `Soft-Forged`
4. `Full-Forged`

这表示下游模块会按深度参与世界化，而不是只有“进 forge / 不进 forge”两态。

#### Assembler

对应文件：

- `assembler.py`
- `data/core/*.json`

当前实现职责：

- 固定加载 Core 模块
- 从 `narrative_briefing + player_profile` 提取 8 个 Core 变量
- 替换 Core 模板占位符
- 按固定章节顺序拼装最终 `system_prompt`

当前实现中的最终 Prompt 结构为 7 段：

- `I. System Role`
- `II. Experience Standard`
- `III. Immutable Constitution`
- `IV. Engine Protocols`
- `V. World-Specific Rules`
- `VI. Emergent Dimensions`
- `VII. Player Calibration`

正式定位：

- `Assembler` 只负责轻编译
- 它负责固定顺序、标题归一、轻量清洗、轻量去噪
- 它不负责替代模块策略设计，也不应承担重型二次创作

### 4.3 Delivery Layer

对应文件：

- `result_packager.py`

当前职责：

- 把编译结果转成前端结果页可读对象
- 输出 `BlueprintSummary`
- 同时返回最终 `system_prompt`

这里必须区分两种交付物：

- `blueprint`：产品展示层摘要，面向人读
- `system_prompt`：Runtime handoff 边界，面向下游运行时

`BlueprintSummary` 当前是轻摘要，不是第二次完整造世界。

### 4.4 API 与前后端契约

对应文件：

- `api.py`
- `api_models.py`
- `service.py`

当前已落地端点：

- `POST /api/interview/start`
- `POST /api/interview/message`
- `POST /api/generate`
- `GET /api/health`

当前关键契约：

- `/api/interview/start`
  - 返回 `session_id`
  - 返回 `phase = interviewing`
  - 返回固定开场问题
- `/api/interview/message`
  - 支持普通 `message`
  - 支持结构化 `mirror_action: "confirm" | "reconsider"`
- `/api/generate`
  - 以 session 内已有访谈产物为主输入
  - 当前返回 `blueprint + system_prompt`

当前前后端 phase 边界需要明确区分：

- 后端 `BackendPhase`：`interviewing / mirror / landing / complete`
- 前端 `UiPhase`：`idle / q1 / interviewing / mirror / landing / generating / complete`

其中：

- `q1` 是前端对启动态的本地映射
- `generating` 是前端等待态，不是后端 phase

当前错误契约边界：

- `ArchitectServiceError` 已统一包装为 `ErrorResponse`
- FastAPI 422 validation error 已统一包装
- 错误体包含 `code / message / retryable`

### 4.5 前端结果层与验证基线

前端位于 `Architect/frontend/`，技术栈为 `React 18 + TypeScript + Vite`。

当前真实组件边界：

- `CompleteView`
- `CompleteSuccessView`
- `GenerateFailureView`
- `FatalErrorView`
- `PromptInspector`

需要明确：

- 当前不存在 `BlueprintView`
- 蓝图展示由 `CompleteView` 承载
- 完整 Prompt 查看器是 `PromptInspector`

截至 2026-03-13，本仓库已核验通过：

- 后端测试：`23/23`
- 前端测试：`3/3`
- 前端构建：`npm run build`

## 5. Architect：当前实现边界

正式架构已经拍板，不等于所有对象都已落地。当前边界必须明确区分。

| 范围 | 状态 | 当前事实 |
| --- | --- | --- |
| `Interviewer -> Conductor -> Forge -> Assembler -> ResultPackager` 主链路 | 已实现 | 可运行、可测试、可演示 |
| 显式维度 registry | 已实现 | `dimension_registry.py` + `data/interview_dimensions.json` 已接线 |
| deterministic 泡泡生成 | 已实现 | `BubbleSuggester` 已替代直接信任模型标签 |
| repair pass | 已实现 | 访谈解析失败时可内部回补 |
| `BlueprintSummary + system_prompt` 交付 | 已实现 | `/api/generate` 可返回最终结果 |
| `routing_snapshot` | 已实现 | 当前唯一长期存在的访谈状态账本 |
| `world_dossier / player_dossier` | 部分实现 | 术语、prompt 和结构方向已定，尚未进入主链路 session |
| `CompileOutput` | 部分实现 | 正式语义边界已定，当前运行中仍以 `InterviewArtifacts` 为中间输入 |
| `FrozenCompilePackage` | 未实现 | 当前下游尚未以冻结包为唯一输入 |
| `Conductor` 模块执行计划 | 未实现 | 当前仍输出 `ForgeManifest`，不是更通用的 module execution plan |
| `Forge` 多模式执行器 | 未实现 | 当前仍是维度 pack 并发生成，不区分四档执行模式 |
| `Assembler` 轻编译清洗增强 | 部分实现 | 固定顺序与模板替换已落地，更系统的清洗/去噪仍未完成 |
| Session 持久化 | 未实现 | 当前仍为 `InMemorySessionStore` |

对 Architect 当前状态的准确表述应是：

- 正式功能架构已经收口为 `State Layer -> Compile Layer -> Delivery Layer`
- 当前代码完整实现的是这套架构的可运行基线
- 三层中若干关键对象与接口已经定名，但尚未全部进入运行主链路

## 6. Runtime：当前边界

当前仓库内没有 `Runtime` 独立实现。  
因此，不能把以下内容写成既成事实：

- 长期记忆系统已经存在
- 世界状态循环已经存在
- SillyTavern 式运行容器已经存在
- Architect 与 Runtime 已完成程序级接线

从当前代码可确认的 Runtime handoff 只有：

- `GenerateResponse.blueprint`
- `GenerateResponse.system_prompt`

其中：

- `blueprint` 面向人读
- `system_prompt` 面向下游运行时

除此之外，Runtime 的启动协议、记忆模型、状态结构和事件循环接口，目前都还不能写成已定实现。

## 7. 预期效果

按当前正式架构推进，OSeria 的 `Architect` 预期达到的不是“更复杂”，而是“更稳定、更可控、更容易交接”：

1. 访谈理解、编译摘要和下游交付不再互相重影
2. `system_prompt` 的世界化不再集中在少数 section，而是整体一致、深度分层
3. `Assembler` 保持轻编译器定位，编译链更容易维护和扩展
4. `Architect -> Runtime` 的交接边界会更稳定，后续 Runtime 落地时不需要重新发明上游语义

截至 2026-03-13，真正被代码证明成立的结论仍然只有一条：

`Architect` 已经是一条可运行、可测试、可演示的世界编译链；  
`Runtime` 仍是后半段系统职责，不是当前仓库中的既成实现。
