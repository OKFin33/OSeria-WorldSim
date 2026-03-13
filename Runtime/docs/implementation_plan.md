# OSeria Runtime vNext — 实施计划与冻结决策

> 版本：v0.4
> 日期：2026-03-14
> 性质：Runtime 主实施文档
> 规则：本文件用于冻结 Runtime 的产品语义、边界与实现决策。后续如果代码与本文冲突，以 Runtime 当前代码为准，但必须及时回写本文。

## 0. 文档定位

本文件只负责三件事：

1. 明确 Runtime 在系统中的职责
2. 冻结已经拍板的 Runtime 产品与技术决策
3. 给后续实现与复盘提供统一口径

Architect 与 Runtime 是平级模块：

- `Architect/`：世界编译器
- `Runtime/`：世界运行器

## 1. 当前系统边界

当前正式链路：

```text
User
  -> Architect
  -> blueprint + system_prompt
  -> Runtime
  -> 持续互动叙事
```

Runtime 的正式职责：

1. 承接 Architect 生成的 `system_prompt`
2. 以单 Agent 聊天式叙事推进故事
3. 维护世界会话状态
4. 维护短期记忆与 lorebook
5. 支持多个世界切换与恢复

Runtime 当前不做：

- 双 Agent sim / narr 架构
- 插件系统
- 手工 prompt 导入工具
- 可编辑 lorebook 工作台

## 2. 已冻结的 Runtime 决策

### 2.1 Handoff 与 Authority

Runtime v1 只支持一种入口：

- 从 Architect 完成页直接进入 Runtime

当前 handoff 字段：

- `system_prompt`
- `title`
- `world_summary`
- `tone_keywords`
- `confirmed_dimensions`
- `emergent_dimensions`
- `player_profile`

冻结原则：

- `system_prompt` 是 Runtime 的唯一世界 authority
- Runtime 不重新定义世界观、风格和角色边界
- Runtime 只补充极薄的 turn 执行协议

### 2.2 UI/UX 语义

主视图：

- 中央聊天区
- 左上角打开世界列表
- 右上角打开当前状态

左抽屉：

- 只承担世界列表语义
- 世界卡片只显示标题与极简相对时间
- 底部固定 `新建世界`
- `新建世界` 打开 Architect，不在 Runtime 内造空世界
- 支持备注名，但只改前台显示，不改底层世界名

右抽屉：

- 顶部主卡只展示：主角、时间、地点
- 下方只保留 `短期记忆` 和 `Lorebook`
- 不展示 Architect 维度、玩家侧写、JSON、调试统计

### 2.3 Bootstrap 生命周期

Runtime 启动拆成两段：

1. `create_session`
2. `bootstrap_session`

正式 `boot_status`：

- `pending`
- `booting`
- `ready`
- `failed`

冻结规则：

- `create_session` 立即返回，不阻塞开场生成
- `bootstrap_session` 在 Runtime 页内异步完成开场
- 同一世界在 `booting` 状态下不得重复调用 LLM
- 开场 assistant message 只能写入一次
- `failed` 世界只允许手动重试

### 2.4 短期记忆

短期记忆的正式来源是主回合返回的 `turn_summary`。

冻结规则：

- 每回合刷新
- 不新增第二次 LLM 调用
- 只展示系统实际持有的 short memory 文本

## 3. v0.4 新冻结结论

### 3.1 当前主瓶颈

基于真实审计，Runtime 当前的主瓶颈不是 bootstrap 状态机，而是主生成超时风险。

已确认事实：

- 普通单轮主生成实测约 `41.6s`
- 当前 LLM timeout 原为 `45s`
- 普通 turn 当前只有 1 次主 LLM 调用
- 当前首轮运行态上下文基线接近 `1.4w` 字符级

因此 v0.4 的优先级固定为：

1. timeout 止血
2. prompt/context budget 收口
3. lorebook 异步队列化
4. 真实审计复跑

### 3.2 Timeout 止血

冻结规则：

- 新增环境变量 `RUNTIME_LLM_TIMEOUT_SECONDS`
- 默认值固定为 `75`
- 保留 `max_retries = 2`

说明：

- 这是止血，不是性能优化
- 本轮不切换 provider，不更换 model

### 3.3 流式主回复

DeepSeek 主回复链路现已接入 streaming。

冻结规则：

- 主 turn 通过独立流式 endpoint 返回 SSE 事件
- 前台可先显示 `assistant_text` 的流式增量，再等待最终结构化 turn 结果落盘
- streaming 只改善首字时间，不等于缩短总推理时间
- lorebook 仍不进入主回复流式链路

### 3.3 Runtime Prompt Budget 收口

当前 Runtime 上下文预算必须收紧。

冻结规则：

- runtime contract 继续收薄，只保留 JSON 执行契约
- 新增环境变量：
  - `RUNTIME_RECENT_MESSAGES_LIMIT`
  - `RUNTIME_RECENT_SUMMARY_LIMIT`
- 默认值固定为：
  - `RUNTIME_RECENT_MESSAGES_LIMIT=6`
  - `RUNTIME_RECENT_SUMMARY_LIMIT=6`

发给模型的 injected state 只保留：

- `protagonist_name`
- `protagonist_gender`
- `current_timestamp`
- `current_location`
- `current_situation`
- `active_threads`
- `important_assets`

默认不注入：

- `status_flags`
- `last_scene`
- 其他低收益字段

session 存储结构不因此改变，变化只发生在 prompt 注入视图。

### 3.4 Lorebook 的正式定位升级

lorebook 的正式产品定位改为：

- 后台长期记忆同步层
- 独立异步执行
- 与主叙事成功/失败解耦

冻结规则：

- 主回复先完成并返回前台
- lorebook 提取任务随后异步入队
- lorebook 成功与否，只影响 lorebook 是否更新
- 不再让 lorebook 失败连坐主 turn

### 3.5 Lorebook 异步任务模型

本轮采用：

- Runtime 内部独立异步任务队列

本轮不采用：

- 同步 inline extractor
- Redis / Celery / 外部 broker

正式规则：

1. 每 `5` 轮触发一次 lorebook 提取任务
2. 第 `5/10/15...` 轮主叙事先返回，再异步入队 lorebook job
3. 队列任务最小数据只携带：
   - `runtime_session_id`
   - `target_turn_number`
4. worker 执行时重新读取 session 当前状态
5. 同一世界同一时刻最多 1 个 lorebook worker 在跑
6. 若同世界已有 pending/running job，新触发 turn 只更新为更高的 `target_turn_number`

当前原型阶段的持久化策略：

- 允许任务在 Runtime 进程重启时丢失
- 不做任务恢复

### 3.6 Lorebook 非致命化

lorebook extractor 失败后，主 turn 仍视为成功。

冻结规则：

- assistant turn 正常写入
- `turn_count` 正常增加
- 前台正常看到故事回复
- lorebook 若失败：
  - 不更新 lorebook
  - 记录 debug diagnostics
  - 不向普通前台抛“这一轮没有成功展开”

### 3.7 Dev Diagnostics 保留

v0.4 保留并扩展 dev diagnostics，作为原型阶段排障脚手架。

当前至少保留：

- `last_turn_error`
- `last_bootstrap_error`
- `last_lorebook_error`
- `last_lorebook_job_status`
- `last_lorebook_job_turn`

普通前台不展示这些信息，仅 debug 模式或 debug API 可见。

## 4. 当前实现基线

截至 2026-03-14，当前 Runtime 主线已经包含：

- 独立 `Runtime/` 顶层模块
- 独立 FastAPI API
- 独立 Runtime frontend
- Architect -> Runtime handoff
- 两段式 bootstrap
- 多世界切换
- JSON session 持久化
- debug diagnostics
- lorebook 闭环
- v0.4 的 timeout 与上下文预算收口
- v0.4 的 lorebook 异步队列化与非致命失败
- v0.4 的 DeepSeek 主回复 streaming

同日真实复测补充结论：

- 指定 world 的普通 turn 复测耗时出现 `34.32s`、`38.88s`、`41.78s`
- 第 `5` 轮主回复在约 `35.45s` 返回，未等待 lorebook 完成
- 第 `5` 轮返回当下 debug 状态为 `last_lorebook_job_status = running`
- 约 `20s` 后 lorebook job 完成，状态变为 `ok`
- 该次异步任务完成后，lorebook 条目数从 `0` 增长到 `5`
- DeepSeek 流式 turn 实测：
  - `time_starttransfer ≈ 0.0058s`
  - `time_total ≈ 37.24s`
  - SSE 已能连续返回 `assistant_delta`

这说明 v0.4 的 lorebook 解耦已经在真实链路中生效：

- 用户先拿到前台故事回复
- lorebook 在后台继续同步
- lorebook 不再同步阻塞第 `5` 轮主回复
- 主回复现在也能在 provider 仍在生成时先把首字推到前台

## 5. 仍需继续收口的点

1. 持续复测普通 turn 的真实耗时
2. 持续观察第 `5/10/15...` 轮的 lorebook queue 行为
3. 评估是否需要进一步压缩 Architect 产出的 runtime-facing `system_prompt`
4. streaming 仍未落地，TTFB 依然等于总时长
5. 虽然 DeepSeek streaming 已落地，但主 turn 仍需要继续观察 JSON 流式解析在长文本下的稳定性
6. 主角命名来源仍需由 Architect 侧补齐

## 6. 维护纪律

后续任何 Runtime 迭代，如果触及以下问题，必须先更新本文件：

- Runtime 的正式入口是否变化
- timeout / retry 策略是否变化
- Runtime prompt budget 是否变化
- lorebook 的触发频率或执行模型是否变化
- lorebook 是否重新回到同步主链路
- debug diagnostics 是否下线或改形
- Runtime 是否开始支持多 worker 或外部队列
