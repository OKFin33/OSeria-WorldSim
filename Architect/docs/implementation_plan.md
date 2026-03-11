# OSeria Architect Engine — 实施计划与开发路径图

> 版本：v0.1  
> 日期：2026-03-11  
> 性质：实时开发路径图  
> 规则：本文件保留“计划性”，但所有条目必须显式标注 `已实现 / 部分实现 / 计划中`

## 0. 使用说明

这不是归档文档，也不是宣传稿。  
它的职责是同时回答三件事：

1. 当前代码已经做到哪里
2. 还缺什么
3. 下一步应该先做什么

状态图例：

- `已实现`：代码存在，且已通过当前仓库中的基本验证
- `部分实现`：主链路存在，但边界、测试或契约尚未收口
- `计划中`：方向已定，但仓库中尚无对应落地

## 0.1 当前实现检查点

截至 2026-03-11，当前仓库中已经成立的能力：

- `Interviewer -> Conductor -> Forge -> Assembler -> ResultPackager` 主链路已落地
- FastAPI API 层已落地：
  - `POST /api/interview/start`
  - `POST /api/interview/message`
  - `POST /api/generate`
  - `GET /api/health`
- Session 管理、`mirror_action` 结构化入口、`BlueprintSummary` 打包已落地
- React + TypeScript + Vite 前端骨架已落地于 `Architect/frontend/`
- 后端测试当前 `15/15` 通过
- 前端构建当前 `npm run build` 通过

仍未收口的点：

- 体验维度 registry 仍主要内嵌在 prompt 中
- 422 validation error 仍未统一包装进 `ErrorResponse`
- 前端错误态仍集中在单一 `CompleteView` 分支
- Runtime 尚未独立实现

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

## 2. 目标架构与当前状态

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

## 3. 组件实施矩阵

### 3.1 数据层

| 组件 | 状态 | 当前事实 | 后续任务 |
| --- | --- | --- | --- |
| `data/core/*.json` | 已实现 | 当前实际为 2 个 meta + 3 个 constitution law + 8 个 engine 文件 | 保持模块内容稳定，避免在代码中硬编码正文 |
| `data/packs/*.json` | 已实现 | 当前 Pack 文件由 `Conductor` 读取并分发给 Forge | 后续可补充更多 Pack，但不影响现链路 |
| `data/dimension_map.json` | 已实现 | 当前为维度到 Pack 的主映射表 | 未来抽出显式 registry，并补充可维护元数据 |
| 显式维度 registry | 计划中 | 当前大量维度知识仍在 `interviewer_system_prompt.md` | 从 prompt 抽离为结构化注册表 |

### 3.2 Prompt 层

| 组件 | 状态 | 当前事实 | 后续任务 |
| --- | --- | --- | --- |
| `prompts/interviewer_system_prompt.md` | 已实现 | 定义访谈人格、输出格式、Mirror/Landing 约束 | 继续与代码 phase 保持同步 |
| `prompts/subagent_system_prompt.md` | 已实现 | Forge 子代理模板已接线 | 未来可增强 Pack 间一致性约束 |

### 3.3 运行时层

| 组件 | 状态 | 当前事实 | 后续任务 |
| --- | --- | --- | --- |
| `interview_controller.py` | 已实现 | 4 阶段状态机；Mirror 条件为 `untouched <= 2` 或 `turn >= 6` | 参数后续可配置化 |
| `interviewer.py` | 已实现 | 负责多轮访谈、Mirror/Landing/Complete 流转与 artifacts 输出 | 后续减少 prompt 内隐知识 |
| steering hint | 已实现 | 基于上一轮 snapshot 和最新输入长度调整 probing 顺序 | 未来如需更重策略，再单独设计 |
| `conductor.py` | 已实现 | 纯代码路由，不是二次 LLM 指挥层 | 明确未知维度的处理元数据 |
| `forge.py` | 已实现 | 并发生成规则片段 | 后续补更多失败重试与观测 |
| `assembler.py` | 已实现 | `generate_json()` 提取 8 个 core 变量后组装 | 后续可把变量 schema 独立出来 |

### 3.4 API / Session / Packaging 层

| 组件 | 状态 | 当前事实 | 后续任务 |
| --- | --- | --- | --- |
| `api_models.py` | 已实现 | 已定义 `BackendPhase`、请求/响应模型、`ErrorResponse` | 保持与前端 `types.ts` 同步 |
| `session_store.py` | 已实现 | 当前仅内存态 `InMemorySessionStore` | 若要长期运行，再考虑持久化 |
| `service.py` | 已实现 | 已承接 `start / message / generate` 业务逻辑 | 继续收口错误语义 |
| `api.py` | 已实现 | FastAPI 路由与 `ArchitectServiceError` 包装已落地 | 增加 422 统一错误包装 |
| `result_packager.py` | 已实现 | 输出产品展示用 `BlueprintSummary` | 后续提升摘要质量与字段解释性 |

### 3.5 前端骨架

| 组件 | 状态 | 当前事实 | 后续任务 |
| --- | --- | --- | --- |
| `frontend/src/App.tsx` | 已实现 | 维护 `UiPhase` 与生成流程 | 后续拆更清晰的结果/错误层 |
| `MirrorView` / `LandingView` / `GenerationView` | 已实现 | 对应主流程关键节点 | 继续收口细节文案和交互动画 |
| `CompleteView` + `PromptInspector` | 已实现 | 当前蓝图结果层由 `CompleteView` 承载，Prompt 查看器为独立组件 | 后续如需更细，可再拆内部子组件 |
| 前端自动化测试 | 计划中 | 当前只有 build 校验 | 增加关键交互路径测试 |

## 4. 当前正式契约

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

### 4.2 InterviewArtifacts 契约

当前正式字段：

- `confirmed_dimensions`
- `emergent_dimensions`
- `excluded_dimensions`
- `narrative_briefing`
- `player_profile`

实施原则：

- `/api/generate` 的正式输入以这组字段为准
- 不让前端从 `system_prompt` 反解析这些信息

### 4.3 结果页契约

当前正式输出：

- `blueprint`
- `system_prompt`

其中：

- `blueprint` 面向产品展示
- `system_prompt` 面向下游系统或专业用户检查

注意：

- 当前代码中不存在单独的 `BlueprintView` 组件
- “蓝图结果层”是产品概念层，当前由 `CompleteView` 承载

## 5. 仍需推进的实施项

### 5.1 高优先级

1. 统一 422 validation error 的响应包装
2. 把体验维度系统从 prompt 内隐菜单抽成显式 registry
3. 拆清前端成功页 / 可重试生成失败页 / 致命错误页
4. 补前端关键交互测试

### 5.2 中优先级

1. 明确 `BlueprintSummary` 的字段生成规则和可维护标准
2. 给 `Forge` 和 `Assembler` 增加更可读的观测/日志接口
3. 让关键运行参数具备配置入口，而不是只靠模块常量

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

- `BlueprintSummary`
- `system_prompt`

下一阶段如果要推进 Runtime，应该新增独立实施计划，而不是继续把 Runtime 融进本文件冒充已实现。

## 7. 验证基线

### 已完成验证

- 后端自动化测试：`15/15`
- 前端构建：通过

### 当前测试覆盖点

- 访谈状态机
- steering 路由
- Conductor 映射
- mock pipeline 全链路
- `BlueprintSummary` 打包
- service / API 契约

### 仍需补的验证

- 前端交互自动化测试
- Live LLM 条件下的质量回归样本
- 更明确的失败分类与恢复路径测试

## 8. 下一阶段顺序

建议按以下顺序推进，而不是并行摊大饼：

1. 收口 Architect 文档和 API 错误语义
2. 抽出显式维度 registry
3. 收口前端错误分层
4. 定义 `Architect -> Runtime` 正式协议
5. 单开 Runtime 计划文档并启动实现

## 9. 结论

`implementation_plan.md` 的职责不是证明项目“已经完成”，而是把开发真实位置标出来。

截至 2026-03-11：

- `Architect` 已经是可运行的世界编译器
- 它仍有若干工程收口项
- `Runtime` 还不能写进“已实现”栏

后续维护本文件时，任何新增条目都必须先回答一句话：

`这是代码事实，还是开发计划？`
