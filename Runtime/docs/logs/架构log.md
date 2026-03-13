# OSeria Runtime — 架构上下文 Log

> 生成时间：2026-03-14
> 用途：作为 Runtime 后续内部对照、学习与复盘材料。
> 性质：基于 Runtime 侧实施、排障与验证过程持续维护，不是聊天逐字导出。
> 阅读方式：优先看新增增量条目，再回看冻结结论与风险提示。

> 维护规则：
> 1. 从当前条目开始，新增增量记录至少写清：`触发背景`、`问题判断/决策形成过程`、`具体执行动作`、`预期效果`、`是否达成`。
> 2. 没有确凿上下文时，不补写、不推断、不脑补这些元信息；宁可保留缺口，也不伪造复盘细节。
> 3. 如果某些元信息当前无法确认，可以留空，或明确标注为 `待观察` / `尚无法判断`；不要为了格式完整而硬填。
> 4. 本 Log 只记录 Runtime 范围内的架构判断、故障定位、执行动作与验证结果；Architect 侧独立维护其自身 Log。

---

## 2026-03-14 · v0.4 第一轮稳定性收口

### 触发背景

- Runtime 实测普通单轮主生成耗时约 `41.6s`
- 当前 provider timeout 原配置为 `45s`
- 线上已出现 `generate_failed: LLM request failed after retries: The read operation timed out`
- 原实现里第 `5/10/15...` 轮 lorebook extractor 仍挂在主回复同步链路上，存在把整轮叙事连坐打失败的风险

### 问题判断 / 决策形成过程

- 审计确认当前主瓶颈不是 bootstrap，而是主生成本身已逼近 timeout 上限
- 当前 prompt/context 体积中，大头来自 Architect `system_prompt` 与 Runtime 注入上下文叠加
- lorebook 的产品定位应是后台长期记忆同步层，而不是阻塞主叙事的强依赖
- 因此拍板 v0.4 方向为：
  - 先提高 timeout 裕量止血
  - 收薄 Runtime 执行协议与 injected context
  - 将 lorebook 改为 Runtime 内部异步任务队列
  - 将 lorebook failure 改为非致命

### 具体执行动作

- 新增并启用 `RUNTIME_LLM_TIMEOUT_SECONDS`，默认值提升到 `75`
- 新增并启用：
  - `RUNTIME_RECENT_MESSAGES_LIMIT=6`
  - `RUNTIME_RECENT_SUMMARY_LIMIT=6`
- 收薄 `runtime_turn_system_prompt.md`
- 将 injected `state_snapshot` 裁剪为运行态高价值字段
- 将 lorebook 从同步 inline extractor 改为 Runtime 内部异步任务队列
- 为 lorebook 增加 per-session 去重 / 覆盖式 pending turn 语义
- 保留并扩展 debug diagnostics，新增 lorebook 任务状态与错误可观测性
- 更新 Runtime 实施文档，补齐 Runtime 自身架构 log

### 预期效果

- 降低普通 turn 因 read timeout 被误杀的概率
- 减少 Runtime 每轮 prompt/context 体积
- 第 `5/10/15...` 轮不再因 lorebook extractor 失败而让整轮前台报错
- 后续排查可直接看到：
  - 主 turn 错误
  - bootstrap 错误
  - lorebook job 错误

### 是否达成

- 已达成：
  - 代码层已完成 timeout env 化、context 收口、lorebook 异步化、非致命失败、debug 扩展
  - 自动化测试通过
- 待继续观察：
  - 真实 provider 下的平均耗时是否显著下降
  - 第 `5` 轮 lorebook queue 在长链试玩中的稳定性
  - Architect 产出的 `system_prompt` 是否仍需继续做 runtime-facing 压缩

### 验证结果

- `python3 -m unittest Runtime.tests.test_service_api -v` 通过
- `npm test -- --run src/App.test.tsx` 通过
- `npm run build` 通过
- 真实审计基线：
  - 普通单轮主生成曾测得约 `41.6s`
  - 该数据构成 v0.4 收口的直接动因

### 剩余风险

- 当前仍未上 streaming，TTFB 仍接近总生成时间
- Architect `system_prompt` 体积仍可能是下一阶段主要优化对象
- lorebook 任务在 Runtime 进程重启时允许丢失，这是原型阶段有意接受的折中

---

## 2026-03-14 · v0.4 真实复测回写

### 触发背景

- v0.4 代码改动与自动化测试已经完成
- 需要确认 timeout 止血、context 收口、lorebook 异步队列化是否真的在活链路生效
- 复测对象使用既有 Runtime world，会话 id 为 `254a077e0922474eb46a8163efd997f3`

### 问题判断 / 决策形成过程

- 仅靠单测无法证明 provider 真实耗时是否回落，也无法证明 lorebook 已经和第 `5` 轮主回复真正解耦
- 因此需要在活 backend 上重启新代码，并用真实 session 连续推进到第 `5` 轮
- 核心观察点固定为：
  - 普通 turn 总耗时
  - 第 `5` 轮是否等待 lorebook
  - debug diagnostics 是否能看到 lorebook 任务状态流转

### 具体执行动作

- 重启 Runtime backend，使 `8001` 加载 v0.4 新代码
- 运行：
  - `python3 -m unittest Runtime.tests.test_service_api -v`
  - `npm test -- --run src/App.test.tsx`
  - `npm run build`
- 对指定 session 连续推进至第 `5` 轮
- 通过 session/debug API 观察：
  - `last_turn_error`
  - `last_lorebook_job_status`
  - `last_lorebook_job_turn`
  - lorebook 条目数量变化

### 预期效果

- 普通 turn 不再贴着旧 `45s` timeout 上限危险游走
- 第 `5` 轮主回复先返回，lorebook 在后台继续执行
- lorebook 任务状态可以通过 diagnostics 直接看到

### 是否达成

- 已达成

### 验证结果

- 自动化测试：
  - `python3 -m unittest Runtime.tests.test_service_api -v` 通过 `16/16`
  - `npm test -- --run src/App.test.tsx` 通过 `6/6`
  - `npm run build` 通过
- 真实 turn 复测：
  - 第 `2` 轮：`38.88s`
  - 第 `3` 轮：`34.32s`
  - 第 `4` 轮：`41.78s`
  - 第 `5` 轮：`35.45s`
- 第 `5` 轮返回当下：
  - `last_lorebook_job_status = running`
  - `lorebook_count = 0`
- 约 `20s` 后再次检查：
  - `last_lorebook_job_status = ok`
  - `last_lorebook_job_turn = 5`
  - `lorebook_count = 5`

### 剩余风险

- timeout 风险已缓解，但普通 turn 仍在 `34s-42s` 区间，TTFB 依旧偏长
- 真正的下一阶段优化重点仍然是 runtime-facing prompt budget，尤其是 Architect 成品 `system_prompt`
- lorebook 队列当前是单进程内存任务，进程重启时未完成任务仍会丢失

---

## 2026-03-14 · DeepSeek 主回复 Streaming 接入

### 触发背景

- v0.4 已经把 lorebook 从主回复链路拆出，但用户仍需盯着空白等待完整 turn 返回
- 真实复测表明主回复总耗时仍在 `34s-42s` 区间，体感延迟仍然过高
- 官方文档确认 `deepseek-chat` 支持 `stream=true` 的 SSE 输出

### 问题判断 / 决策形成过程

- 现阶段真正该先解决的是首字时间，而不是继续空谈“异步化已完成”
- 当前 Runtime 的主回复仍依赖结构化 JSON，所以不能粗暴改成纯文本聊天
- 最小侵入方案是：
  - 后端新增流式 turn endpoint
  - 仍让模型产出完整 JSON
  - 在流式过程中增量提取 `assistant_text`
  - 最后再一次性提交结构化 turn 结果

### 具体执行动作

- 为 `OpenAICompatibleLLMClient` 增加 `stream_chat`
- 新增 Runtime 流式 endpoint：`POST /api/runtime/turn/stream`
- 前端发送链路切到 streaming，并增加占位 assistant message
- 后端在流式阶段增量发出 `assistant_delta`，最终发出 `turn_complete`
- 保持 lorebook 异步队列与最终落盘逻辑不变

### 预期效果

- 首字时间显著提前
- 用户在总推理尚未结束前即可看到故事开始展开
- 不破坏现有 Runtime 结构化 turn 协议

### 是否达成

- 已达成

### 验证结果

- 自动化测试：
  - `python3 -m unittest Runtime.tests.test_service_api -v` 通过 `17/17`
  - `npm test -- --run src/App.test.tsx` 通过 `6/6`
  - `npm run build` 通过
- 真实流式探针：
  - `POST /api/runtime/turn/stream`
  - `time_starttransfer = 0.005761s`
  - `time_total = 37.235153s`
  - 返回体中可见连续 `assistant_delta` SSE 事件

### 剩余风险

- 当前是“JSON 文本流 + 后端增量提取 assistant_text”，仍需继续观察长文本和异常 JSON 下的稳定性
- 总耗时并未因 streaming 本身下降，真正的下一阶段瓶颈仍是 Architect 成品 prompt 体积

---

## 2026-03-14 · Streaming 后 UI 收口与运行态恢复

### 触发背景

- DeepSeek 主回复接入 streaming 后，前台体感明显改善，但出现两个新的前台问题：
  - 文本已经输出完成，底部 `正在编织后果...` 仍会继续停留一小段时间
  - Runtime 输入区和主题开关的视觉形态偏重，和 Architect 既有输入体验不一致
- 同期还出现过一次 Runtime 前后端 dev 服务均已退出，导致 `5174/8001` 无法访问

### 问题判断 / 决策形成过程

- `正在编织后果...` 残留不是模型问题，而是前端把 sending 状态绑到了后续的世界列表刷新与 debug 刷新上
- 输入区和主题开关问题属于 UI 收口，而不是功能缺失：
  - 发送按钮不应再占据独立按钮位
  - 主题切换不应覆盖右抽屉内容
  - 输入框宽度不应因为小改动被拉到过满
- dev server 不可访问则属于运行态问题，但原型开发阶段仍需要在 log 中留下恢复记录，避免误判成代码故障

### 具体执行动作

- 调整 Runtime 前端 sending 状态切换时机：
  - `turn_complete` 到达时立即结束 loading 态
  - 不再等待 `refreshWorlds()` 和 debug 刷新
- 将底部文案从 `正在编织后果...` 改为更柔和的 `世界正在回应...`
- 将 Runtime composer 改为：
  - 输入框右下角小箭头提交
  - 去掉独立“发送”按钮
  - 宽度回收至较短版本，不再撑满
  - 箭头去掉圆形背景
- 将主题切换改为：
  - 右抽屉右下角固定图标按钮
  - 用太阳/月亮图标代替文字
- 运行态恢复：
  - 重启 Runtime backend `8001`
  - 重启 Runtime frontend `5174`
  - 重新验证 health 与页面可访问性

### 预期效果

- 文本流结束后，loading 提示立即消失，不再拖尾
- 输入区视觉语言和 Architect 更统一
- 右抽屉中的主题切换不再与短期记忆/Lorebook 内容重叠
- Runtime 无法访问时，可明确区分“服务已退出”和“代码逻辑故障”

### 是否达成

- 已达成

### 验证结果

- 前端回归：
  - `npm test -- --run src/App.test.tsx` 通过 `6/6`
  - `npm run build` 通过
- 运行态恢复验证：
  - `GET /api/health` on `8001` 返回 `{"status":"ok"}`
  - `GET /` on `5174` 返回 `HTTP 200`

### 剩余风险

- 当前 composer 和右抽屉仍在持续收口阶段，后续若继续调整移动端或小屏体验，仍需同步回写本 log
- dev server 退出仍是原型阶段常见情况，不应被误判为 Runtime 主线逻辑故障
