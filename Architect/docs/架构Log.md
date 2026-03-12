# OSeria Architect vNext — 架构上下文 Log（线程复盘稿）

> 生成时间：2026-03-12
> 用途：作为后续内部对照、学习与复盘材料。
> 性质：**基于本线程记忆重建**，不是逐字逐句聊天导出；但尽可能覆盖关键对话轮、关键分歧、关键拍板与其上下文。
> 阅读方式：优先看「阶段时间线」，再看文末「vNext 当前冻结结论」。

---

## 0. 本 Log 的作用边界

这份文档不是 PR 说明，也不是最终技术说明书。

它记录的是：

- 本线程里为什么会从“当前可运行原型”走到“vNext twin dossier 架构”
- 哪些分歧曾经出现
- 每一步拍板的理由是什么
- 哪些旧概念被废弃或降级
- 为什么某些方案最后没有采用

它不保证：

- 覆盖每一句闲聊
- 保留每一次表达上的细微差异
- 与 Git 历史一一对应

但它尽量保证：

- 关键架构意图不丢
- 后续接手者在零上下文下能读懂“为什么今天会是这样”

---

## 1. 阶段时间线（按本线程主题推进顺序重建）

## 阶段 A：先把 Architect 原型跑起来

### A1. 计划驱动的第一迭代开发

起点：

- 用户最初要求：按 `implementation_plan.md` 完成第一迭代版本。

执行结果：

- 先完成了第一版后端主链：
  - 访谈状态机
  - `Conductor`
  - `Forge`
  - `Assembler`
  - CLI 主入口
  - 最初测试

这一步的重要性：

- 它确立了 **Architect 不是静态说明书，而是能跑的编译链**
- 但这时系统仍然偏后端运行时，不是前后端一体产品原型

---

### A2. 主线前端是否存在、是否需要

关键对话：

- 用户确认当前是否已有前端代码
- 随后讨论：后续要做 UI/UX 设计时，现在是否要先有一个可扩展的前端底座

中间判断：

- 仓库里当时没有正式主线前端，只是有旧参考
- 一开始给出的建议是：若没有更成熟设计，至少应先做“骨架版前端”

随后又发生修正：

- 用户提出：如果先给完整前端设计方案，再针对性开发，会不会更好
- 结论改为：**如果设计方案足够具体并包含交互逻辑，先做设计方案更优**

这一步的重要性：

- 奠定了后续“先 spec，再实现”的工作风格
- 明确了：UI 不是随便搭壳，而是要围绕状态机和契约做

---

## 阶段 B：UI/UX 方案反复 review，并反向约束后端

### B1. `ui_ux_design_thinking_v2.md` 的多轮 review

用户动作：

- 提供 UI/UX 方案文档，要求 review，不执行开发

多轮 review 中暴露的核心问题：

1. 自动重试与有状态访谈冲突  
2. 完成态定义缺失  
3. Mirror 回退后用户缺乏纠错支点  
4. 移动端布局对 `100vh` / 输入法场景不成立  
5. 泡泡布局和随机定位不靠谱  
6. Mirror 交互依赖 magic string  
7. 错误契约不统一  

后续逐步拍板的 UI/UX 决策：

- Mirror 主协议改为 `mirror_action`
- `message` 降级为 optional fallback
- 前端维护独立 `UiPhase`，由后端 phase 派生
- 完成态改为双层结果页：
  - 面向普通用户的 `Blueprint`
  - 面向硬核用户的可展开 `SystemPrompt`
- `/generate` 失败允许保留访谈成果重试
- 完成态 / 错误态 / Prompt Inspector 的产品定义逐步清晰

这一步的重要性：

- 前端 spec 开始不再只是视觉稿
- 它对后端提出了新的结构化约束：
  - session
  - phase
  - `/api/generate`
  - error contract

---

### B2. reject / Mirror 的来源追溯

关键问题：

- 用户确认 reject 是否就是历史 `Decision 14.11`
- 并核实 interview prompt 里是否真有对应逻辑

结论：

- 是，Mirror 的两个泡泡源自旧决策：
  - `推门`
  - `我得再想想`
- 访谈员 prompt 里确实存在 reject 的柔和接住逻辑

这一步的重要性：

- 证明 reject 不是临时拍脑袋，而是已有产品设计脉络
- 也为后面重构 reject 流程提供了历史依据

---

## 阶段 C：从纯 backend prototype 升级为可接前端的系统

### C1. 检查后端是否适配前端 spec

用户问题：

- 现有后端基础是否真的能接前端 spec

结论：

- 底层运行时可复用
- 但 API/BFF/session/result packaging 还不够
- 当前后端只能算“运行时原型”，不是正式可接前端接口层

因此新增计划：

- `FastAPI`
- session 管理
- `api_models`
- `service`
- `result_packager`

这一步的重要性：

- 明确“CLI runtime”和“产品级 API”不是同一层东西

---

### C2. 一次性完成后端迭代 + 第一版前端骨架

用户要求：

- 一次性完成后端迭代与第一版可供 UI 微调的前端骨架

结果：

- 落地了前后端第一版可运行闭环
- 前端覆盖：
  - Q1
  - Interviewing
  - Mirror
  - Landing
  - Generating
  - Complete
- 后端补齐：
  - API
  - session
  - `BlueprintSummary + system_prompt`

这一步的重要性：

- 仓库从“概念工程”进入“可演示工程”

---

## 阶段 D：仓库整理与主线边界收口

### D1. 所有主线内容收入 `Architect/`

用户要求：

- 真正的 architect prototype 内容都放在 `Architect` 文件夹里

结果：

- `frontend/`
- `tests/`
- `docs/`
- 运行时代码
全部收进 `Architect/`

后续又决定：

- `archive` 不再长期保留，最终删除

这一步的重要性：

- 清理了目录边界
- 避免了旧参考实现继续污染主线

---

### D2. 解释 `.venv`

用户提问：

- `.venv` 是什么

结论：

- 它只是项目级 Python 虚拟环境
- 不是 Architect prototype 本体

这件事虽小，但帮助后续区分：

- 业务代码
- 运行环境

---

## 阶段 E：第一次全库 review 与“可进入 UI 敏捷迭代吗”

### E1. Review 当前代码库进展

第一次系统性评估结果：

- 架构完成度较高
- 可演示性较强
- 但错误契约、协议严格性、前端错误态、测试等仍有明显缺口

主要问题包括：

- 结果页失败态混杂
- 422 错误契约未统一
- `message + mirror_action` 仍可双传
- 前端 API client 非 JSON 错误兜底不够
- 文档和目录整理仍有残留
- 前端缺少自动化测试

这一步的重要性：

- 确认项目还不是“生产稳健”，但已经不是空壳

---

### E2. 以功能语言向用户解释 UX 决策

用户表示不懂代码，希望用功能方式解释所有影响 UX 的决策。

因此我们把技术问题翻译成 6 类产品决策：

1. 错误后到底显示“重试生成”还是“重新开始”
2. 错误提示是否统一成产品语言
3. Mirror 是否只允许明确二选一
4. 非标准网络错误是否统一兜底
5. 结果页是否拆分成功/失败/致命故障
6. 是否补最小前端自动化测试

用户最后拍板：

- 错误不做一个统治一切的大错误页
- 错误文案风格与正文统一
- Mirror 继续只有两个选项
- 结果页拆成三类
- 非标准网络错误需要兜底
- 前端补最小测试集

这一步的重要性：

- 后续修 Bug 不再只是工程清理，而是明确服务于 UX 目标

---

### E3. 收掉已知技术债，开放 UI 敏捷迭代

后续完成：

- 严格互斥的 `message / mirror_action`
- Bubble key 和复制兜底
- 422 统一包装
- 三类结果/故障视图
- 前端最小测试
- 依赖安全告警清理

最终判断：

- 当前代码库已经可以进入“人类 UI 敏捷迭代阶段”

这一步的重要性：

- 主链基础设施基本站稳

---

## 阶段 E+：几段后来证明很关键、但容易被忽略的前史

### E+1. “先写技术说明文档”不是偏题，而是为了防止上下文蒸发

曾经出现的分支讨论：

- 用户意识到最终还需要交一份针对整个 OSeria 的技术说明
- 这份说明不只覆盖 Architect，还要覆盖后半段 Runtime

一开始的犹豫点：

- 现在 Runtime 还没真正落地，是否应该现在就写

最终形成的判断：

- 应该现在开始搭文档骨架
- 但不能装作 Runtime 已经实现
- 正确做法是：
  - 现在写系统目标、两段式架构、职责边界、为什么这样拆
  - 以后再补实现细节

因此后来新增了：

- `OSeria_technical_overview.md`

这段对话的重要性：

- 它明确了 **Architect 与 Runtime 是两段式系统**
- 也明确了“文档不只是交付物，也是未来防遗忘的记忆层”

---

### E+2. 文档维护线程被单独拆出

后续又发生一件很容易被低估的事：

- 用户担心主线开发会不断推进，而文档逐渐失真
- 因此专门讨论了是否要把文档维护放进单独线程持续对账

最后的做法是：

- 将以下文档视为同一知识面，需要一起维护：
  - `OSeria_technical_overview.md`
  - `implementation_plan.md`
  - `ui_ux_design_thinking_v2.md`

这段对话的重要性：

- 它建立了一个重要纪律：
  - **代码优先，文档持续对账**
- 也帮助后来识别“系统层级重影”时，不是只盯代码，而是连文档一起看

---

### E+3. 显式维度 registry 曾经是一个中间过渡阶段

在 twin dossier 架构被提出之前，还有一段重要演化：

- 用户追问 `dim:social_friction`、`dim:quest_system` 这些维度到底从哪里来
- 最初系统解释为：
  - Prompt 里有体验维度菜单
  - LLM 主要从这份菜单里识别

随后又发生收口：

- 把这套隐式菜单迁成显式 registry
- 新增 `interview_dimensions.json`
- 并让 steering 逻辑显式读 registry

这一步后来又被 twin dossier 超越，但仍然重要，因为它说明了一个中间认知：

> 我们先意识到“体验维度不该只活在 prompt 文本里”，
> 然后才继续意识到“即便有维度 registry，系统仍然没有真正固化对世界和用户的理解”。

这段对话的重要性：

- 它是从纯 prompt heuristic 走向更强状态系统的第一步
- 也解释了为什么后来 `routing_snapshot` 能成为 dossier 的一部分，而不是彻底废弃

---

### E+4. DeepSeek 兼容性问题迫使我们区分“可靠性修复”和“体验增强”

用户后续补充了一个非常关键的真实问题：

- DeepSeek 在多轮后偶尔会忘记输出包裹路由信息的 JSON
- 会只吐一段自然语言，导致 parse_error / Fatal Error

当时出现的讨论不是单纯修 bug，而是两个方向的取舍：

1. 增强后端稳健解析逻辑，允许 repair / fallback
2. 为 DeepSeek 单独优化更强的格式约束 prompt

最终判断是：

- 两者都要做
- 但顺序上必须先做后端稳健性兜底，再做模型定制 prompt

后来还引出另一条产品/工程分界：

- 前端已经用 typewriter effect 先模拟了流式体验
- 真正的 SSE 不应先于格式稳定性进入主线

这段对话的重要性：

- 它帮助后续形成一个更稳定的原则：
  - **先保结构可靠，再追求表现增强**
- 这对 vNext 仍然有效，因为 dossier / compile / bubble 三次调用同样需要这个原则

---

## 阶段 F：Bubble 彻底暴露问题，开始从“提示标签”转向“候选回答”

### F1. 泡泡先后经历的几次失败形态

用户多次反馈泡泡有严重问题：

- 有时不生成
- 有时过多
- 会冒英文、`dim:*`
- 内容和题面不贴
- 系统标签味过强
- 最终“推门 / 我得再想想”布局也曾出现挤在一起

最初修补动作：

- 清洗 `suggested_tags`
- 过滤脏词
- 布局从随机定位改为稳定流式布局
- 从 registry 回填中文短语

这些修补只能解决“脏”和“乱”，不能解决“对不对”。

---

### F2. 重新定义 bubble 的本体

经过多轮讨论，bubble 的定义发生了根本变化：

旧理解：

- 系统下一步想继续问什么
- 或系统内部体验维度的前台翻译

新理解：

- **用户在当前问题下最可能顺手点下去的候选回答**

这一改变非常关键，因为它使得 bubble：

- 从系统视角转向用户视角
- 从“方向提示”转向“候选回答”

这一步的重要性：

- 直接催生了后面 `BubbleComposer` 独立调用的决定

---

## 阶段 G：开始意识到“理解没有被固化”

### G1. 用户主观体验反馈：问题和 Mirror 仍不够“像我”

用户指出：

- 有时问题和“我（用户）”真正想要的不太一致
- 蓝图前的那段描述也常常不够打到心里

经过分析，形成核心判断：

> 当前系统“路由稳定，理解不稳定”。

也就是说：

- `routing_snapshot` 持续维护得相对稳定
- 但“世界理解”“用户理解”“情绪理解”大多还停留在 LLM 的隐式记忆中
- 最后再由一次性总结收束成 `narrative_briefing / player_profile`

这意味着：

- 系统像一个聪明但记性不稳的访谈者
- 不是一个在持续编译用户意图的系统

---

### G2. 提出并接受“持续维护的共享档案”概念

关键提问：

- 是否应该有一份被访谈员持续维护的工作文档
- 该文档是否应同时服务：
  - 访谈员
  - 泡泡生成器
  - Mirror
  - 蓝图 / 最终 system prompt 生成链路

结论：

- 需要
- 但不能只是自由 prose 文档
- 应该是：
  - **结构化骨架**
  - 配合少量自由文本弱信号

于是形成 twin dossier 架构方向：

- `WorldDossier`
- `PlayerDossier`

再加：

- `RoutingSnapshot`

这三者共同构成长期状态层。

这一步的重要性：

- 这是从“访谈式 LLM 应用”转向“认知状态驱动系统”的分水岭

---

## 阶段 H：从隐式记忆走向 twin dossier 架构

### H1. 为什么不是纯结构化 / 纯散文

曾经讨论过：

- 如果 dossier 完全结构化，会不会漏掉字里行间的细节？

结论：

- 会
- 所以应该是：
  - 结构化主骨架
  - 少量 `soft_signals`
  - 证据锚点意识

这一步决定了 dossier 最终不是死表格，也不是抒情日记。

---

### H2. `DossierUpdater` 与 `InterviewComposer` 的角色拆分

经过多轮推理，明确两者不是“两个都在产文本的 LLM 调用”，而是：

- `DossierUpdater` = 理解层 / 记忆层
- `InterviewComposer` = 表达层 / 前台交互层

并明确：

- `DossierUpdater` 必须独立
- `InterviewComposer` 不能再顺手更新 dossier

理由：

- 否则记忆更新和创作表达会互相污染

这一步的重要性：

- 为整个 vNext 架构定下了最重要的二段式认知链

---

### H3. Bubble 是否也应该独立

起初曾经保守地认为：

- Bubble 可以先并入 `InterviewComposer`

后来用户指出一个实质性问题：

> 如果 bubble 的定义是“用户最可能会怎么回答”，那它本质上是用户心智视角，不是系统心智视角。

最终结论：

- Bubble 应独立为 `BubbleComposer`
- `InterviewComposer` 继续站在系统侧
- `BubbleComposer` 扮演当前用户心智投影

这是一次重要修正。

---

## 阶段 I：系统层级重影被系统性识别

### I1. 用户提出整体性怀疑

用户指出：

- dossier、briefing、artifacts、blueprint、system prompt 层层相叠
- 可能不是 dossier 单点的问题，而是整个系统层级开始互相重影

经过全库与多份文档检查，确认这一判断成立。

识别出的系统性症状：

- Prompt 层、runtime 层、文档层在描述不同的 Architect
- 长期状态、编译接口、交付结果混在一起
- 同一语义被重复总结、重复再解释

这一步非常关键，因为它直接触发了：

- 对整套 vNext 架构的**重新收口**

---

### I2. 架构强制压回 3 层

最终收口为：

1. `State Layer`
   - `WorldDossier`
   - `PlayerDossier`
   - `RoutingSnapshot`

2. `Compile Layer`
   - `CompileOutput`
   - 后续新增 `FrozenCompilePackage`

3. `Delivery Layer`
   - `Blueprint`
   - `SystemPrompt`

这个决定的价值在于：

- 不再允许继续发明并列真相源
- 后续所有模块必须回答：
  - 你属于哪一层？
  - 你读什么？
  - 你不能碰什么？

---

## 阶段 J：`implementation_plan.md` 变成真正的 vNext 主实施文档

### J1. 文档定位的变化

曾经的问题：

- `implementation_plan.md` 同时混着旧计划和新计划
- `OSeria_technical_overview.md`、UI/UX spec 和代码现实有口径漂移

后来的收口：

- `implementation_plan.md` 被提升为：
  - **Architect vNext 的唯一实施基线**
- 顶部增加整改说明：
  - 为什么整改
  - 怎么整改
  - 预期如何
- 明确区分：
  - 当前代码基线
  - vNext 目标架构

这一步的重要性：

- 后续所有 Task 决议都落到了这份文档里

---

## 阶段 K：对 vNext 做 7 轮 Task 拍板

> 这是本线程后半段最核心的收口过程。

### K1. Task 1：状态模型粒度

讨论问题：

- Dossier 要轻还是重？
- `core_tension` 是否应该显性化？
- `stakes_model / conflict_source / power_shape / user_no_go_zones` 是否加入？

最终决议：

- `WorldDossier` 保持中轻量
- `core_tension` 改名为 `tension_guess`
- 新增 `user_no_go_zones`
- 不引入：
  - `stakes_model`
  - `conflict_source`
  - `power_shape`
- `CompileOutput` 继续保持最小 5 字段

UX 理由：

- 需要足够理解力
- 但不能太早让系统自信地误解用户

---

### K2. Task 2：上下文输入策略

讨论问题：

- `DossierUpdater` 和 `InterviewComposer` 应该吃多少上下文？

最终决议：

- `DossierUpdater` 吃：
  - 上一版 twin dossier
  - 上一版 `RoutingSnapshot`
  - 最近 3 轮问答
  - 最新用户输入
- `InterviewComposer` 吃：
  - 最新 twin dossier
  - 最近 1-2 轮必要语境
  - 当前 phase
  - 后来补入：
    - `dossier_update_status`
    - 轻量 follow-up signal
- 不采用全量历史直喂
- 不引入单独 summary memory 层

UX 理由：

- 避免失忆
- 也避免被早期一句话绑死

---

### K3. Task 3：Bubble 策略

讨论问题：

- Bubble 是否独立调用？
- Bubble 的视角到底是谁？

最终决议：

- Bubble 独立为 `Call 3: BubbleComposer`
- 输入：
  - `PlayerDossier`
  - `WorldDossier`
  - `RoutingSnapshot`
  - 当前问题
  - 最近用户输入
  - 必要时最近一轮 assistant 输出
- 输出：
  - `bubble_candidates`
  - `text + kind`
- `kind` 只有：
  - `answer`
  - `advance`
- 比例固定：
  - `1-2 answer`
  - `0-1 advance`

并明确：

- `advance` 只能比用户当前显性表达更清晰半步
- 不能替用户发明新欲望

---

### K4. Task 4：Mirror 策略

讨论问题：

- Mirror 要不要独立 prompt / 独立调用？
- reject 后怎么办？

最终决议：

- Mirror 继续作为 `InterviewComposer` 的 phase mode
- Mirror 本身是 dossier-driven 的高浓度理解回声
- 只输出文本
- reject 后：
  - 不重新生成 Mirror
  - 不立即重写核心 dossier
  - 只写一次轻量事件信号：`mirror_rejected`
  - 下一问直接作为正式下一轮问题出现
  - 该问题必须：
    - 具体
    - 场景化
    - 非 meta
  - 用户回答后，再由 `DossierUpdater` 修 dossier
  - 至少再进行 1-2 轮，才允许再次进入 Mirror

额外决议：

- 校正问题占用正常轮次，不是免费附加题

---

### K5. Task 5：Compile 触发与 `/api/generate`

讨论问题：

- `CompileOutput` 何时冻结？
- `/api/generate` 是否是用户可感知动作？
- 用户到底感知什么？

最终决议：

- Landing 完成后，立刻冻结 `CompileOutput`
- 系统自动进入内部 generating 阶段
- `/api/generate` 是内部接口，不是用户心智中的按钮
- `/api/generate` 只接受 `session_id`
- 前端不允许传 `CompileOutput`
- 真正的主产物是：
  - `SystemPrompt`
- `Blueprint` 是次级展示产物
- 生成失败只重试生成链，不重新 compile

后续在外部 review 后又追加一条关键收口：

- `CompileOutput` 保持最小 5 字段
- 新增：
  - `FrozenCompilePackage`
- Delivery 层只读冻结包，不读 live dossier

---

### K6. Task 6：Delivery 层消费深度

讨论问题：

- `Conductor / Forge / Assembler / Blueprint` 谁该吃 dossier？

最终决议：

- `Conductor`：只吃 `CompileOutput`
- `Forge`：吃 `FrozenCompilePackage.compile_output + forge_context`
- `Assembler`：吃 `FrozenCompilePackage.compile_output + assembler_context`
- `Blueprint`：当前版本保持轻度摘要，只吃 `CompileOutput`
- 不允许任何 delivery 模块直接读 live dossier

这里也补出两个重要对象：

- `ForgeContext`
- `AssemblerContext`

它们都不直接等于 dossier，而是 compile 阶段从 dossier 白名单字段一次性冻结出来。

---

### K7. Task 7：失败恢复策略

起初的过粗方案：

- 理解层失败就硬阻断

后来用户指出：

- 如果理解层一有问题就前端报错，即时 UX 会被打穿

于是策略细化为：

- 区分软失败 / 硬失败
- 引入 turn transaction 语义

最终决议：

#### `DossierUpdater`
- 先内部重试 1 次
- 软失败：
  - 不前端报错
  - 不覆盖核心 dossier
  - 可标记 `update_skipped` 或保守状态
  - 用旧 dossier 继续下一问
- 硬失败：
  - 才阻断本轮

#### `InterviewComposer`
- 若 dossier 已更新成功，则保留新 dossier
- 自己失败时只重试表达层
- 不要求用户重输

#### `BubbleComposer`
- 失败不阻断主流程
- 优先允许空 bubbles

#### compile / generate
- compile freeze 失败，不进入生成链，但保留 dossier
- `/api/generate` 后半生成链失败：
  - 只重试生产
  - 不重新理解用户

这一步的重要性：

- 明确了“哪一层失败不能装作没事，哪一层失败可以优雅降级”

---

## 阶段 L：外部 review 介入，补拍最后几处关键决策

外部 review 提出的关键补拍项包括：

1. `CompileOutput` 到底是不是唯一下游接口  
2. bubble 到底是不是独立 `Call 3`  
3. `RoutingSnapshot` 的唯一写入者是谁  
4. API 改造是否原子发布  
5. 三次调用的失败降级策略  
6. prompt 文件与新 schema 是否一致  

最终收口结果：

- `CompileOutput` 保持最小 5 字段
- 新增 `FrozenCompilePackage`
- `BubbleComposer` 独立为 `Call 3`
- 只有 `DossierUpdater` 可以写 `RoutingSnapshot`
- 前后端 schema 采用原子切换，不留 `suggested_tags` 长兼容尾巴
- `dossier_updater_system_prompt.md` 需要同步到 vNext schema

这一步的重要性：

- 把此前可能仍有灰区的地方全拍死了

---

## 阶段 M：Prompt 层成为 vNext 开发前的最后前置阻塞

在确认可以进入 vNext 一次性开发之前，又识别出一类必须收口的问题：

- `BubbleComposer` prompt 其实还没写
- `InterviewComposer` prompt 还藏在旧 monolith 里
- 如果 compile 继续走 LLM，也缺独立 prompt 归属
- `dossier_updater_system_prompt.md` 旧 schema 也必须修

于是又发生一轮 prompt 层收口：

### 新增 / 收口的 prompt 文件

- `dossier_updater_system_prompt.md`
  - 对齐到：
    - `world_dossier`
    - `player_dossier`
    - `tension_guess`
    - 分层 `soft_signals`
- `interview_composer_system_prompt.md`
  - 作为 `Call 2` 第一版独立 prompt
- `bubble_composer_system_prompt.md`
  - 作为 `Call 3` 第一版独立 prompt
- `compile_output_system_prompt.md`
  - 作为 compile 阶段第一版独立 prompt
- 旧 `interviewer_system_prompt.md`
  - 被标记为当前基线 monolith，不再继续扩写新职责

这一步的重要性：

- prompt 归属终于和 vNext 架构一致
- 这之后才真正达到“可以开始 vNext 一次性开发”的状态

---

## 2. 本线程中逐步废弃或降级的旧概念

以下概念不是全都消失了，但其地位发生了变化：

### 1. `InterviewArtifacts`

- 旧代码中的主要访谈终产物对象
- 在 vNext 中不再作为长期主概念继续扩写
- 被 `CompileOutput` 取代其正式中间接口角色

### 2. `suggested_tags`

- 旧泡泡字段
- 早期承担过：
  - tag
  - heuristic bubble
  - 后端清洗泡泡
- 在 vNext 中应被 `bubble_candidates` 彻底取代

### 3. monolith `interviewer_system_prompt`

- 旧系统里的“大一统访谈员 prompt”
- 在 vNext 中被拆分为：
  - `DossierUpdater`
  - `InterviewComposer`
  - `BubbleComposer`
  - `CompileOutput`

### 4. “蓝图主导架构”

- 早期容易让人把 `Blueprint` 当主结果
- 后来明确：
  - `SystemPrompt` 才是 Architect 真正主产物
  - `Blueprint` 只是次级展示层

---

## 3. vNext 当前冻结结论（供零上下文快速进入）

## 3.1 架构总览

```text
User input
  -> Call 1: DossierUpdater
  -> WorldDossier + PlayerDossier + RoutingSnapshot
  -> Call 2: InterviewComposer
  -> visible_text + question / Mirror
  -> Call 3: BubbleComposer
  -> bubble_candidates
  -> Landing complete
  -> CompileOutput
  -> FrozenCompilePackage
  -> /api/generate
  -> Blueprint + SystemPrompt
```

## 3.2 三层模型

### State Layer

- `WorldDossier`
- `PlayerDossier`
- `RoutingSnapshot`

### Compile Layer

- `CompileOutput`
- `FrozenCompilePackage`

### Delivery Layer

- `Blueprint`
- `SystemPrompt`

## 3.3 四大核心功能

1. 问题生成：`InterviewComposer`
2. 泡泡生成：`BubbleComposer`
3. Mirror：`InterviewComposer` phase mode
4. 最终系统提示词生成：
   - `CompileOutput`
   - `FrozenCompilePackage`
   - `Conductor`
   - `Forge`
   - `Assembler`

## 3.4 当前最关键的硬规则

1. 只有 `DossierUpdater` 可以写 `RoutingSnapshot`
2. `BubbleComposer` 必须独立，不再并入 `InterviewComposer`
3. `CompileOutput` 保持最小 5 字段
4. Delivery 层只读 `FrozenCompilePackage`，不读 live dossier
5. `Blueprint` 当前是轻摘要，不反向主导架构
6. `/api/generate` 是内部接口，不是用户心智里的按钮
7. 失败时优先：
   - 保住理解
   - 只重试表达或生产
   - 不让系统偷偷带着错理解继续走

---

## 4. 本线程中最重要的几次认知跃迁

如果只看少量“真正影响方向”的变化，本线程最重要的跃迁是这些：

1. 从“后端原型是否能跑”转向“产品级前后端系统如何对齐”
2. 从“泡泡是标签/提示”转向“泡泡是用户候选回答”
3. 从“LLM 靠上下文隐式记住你”转向“系统显式维护 twin dossier”
4. 从“所有模块都可能再理解一次用户”转向“三层架构 + 冻结接口”
5. 从“文档讨论稿”转向“implementation_plan 作为 vNext 主实施基线”

---

## 5. 概念演化索引（旧概念 -> 新概念）

这部分的价值在于：

- 帮后续接手者快速识别“哪些概念已经被替换”
- 避免在实现时把旧名字当成旧功能继续扩写
- 也帮助理解：今天的名词不是凭空出现，而是从旧系统一步步长出来的

### 5.1 访谈主链相关

- 旧：`interviewer_system_prompt.md`（monolith）
- 新：
  - `dossier_updater_system_prompt.md`
  - `interview_composer_system_prompt.md`
  - `bubble_composer_system_prompt.md`
  - `compile_output_system_prompt.md`

含义变化：

- 从“一份 prompt 同时负责理解、提问、泡泡、最终总结”
- 变成“按职责分拆的多调用架构”

### 5.2 访谈结果相关

- 旧：`InterviewArtifacts`
- 新：
  - `CompileOutput`
  - `FrozenCompilePackage`

含义变化：

- `InterviewArtifacts` 曾经是访谈结束后直接交给后续编译链的对象
- 在 vNext 中，它不再是主概念
- `CompileOutput` 负责最小稳定语义摘要
- `FrozenCompilePackage` 负责下游冻结输入

### 5.3 泡泡相关

- 旧：`suggested_tags`
- 中间：规则清洗后的 bubble / heuristic bubble
- 新：`bubble_candidates`

含义变化：

- 从“系统标签 / 提示方向”
- 变成“当前用户心智下的候选回答”

### 5.4 世界理解相关

- 旧：
  - `provisional_world_model`
  - `provisional_player_model`
  - `core_tension`
- 新：
  - `WorldDossier`
  - `PlayerDossier`
  - `tension_guess`

含义变化：

- 从“草稿式临时中间态”
- 变成“长期维护的认知状态层”

### 5.5 结果页相关

- 旧：`CompleteView` 承担几乎所有结果和错误情况
- 新：
  - `Blueprint` 作为普通用户摘要层
  - `SystemPrompt` 作为真正主产物

含义变化：

- 从“结果页 = 一切的终点”
- 变成“结果页只是主产物的一层展示面”

### 5.6 Runtime 边界相关

- 旧：更容易把 `BlueprintSummary + system_prompt` 视作同级主结果
- 新：
  - `SystemPrompt` 是 Architect 真正主产物
  - `Blueprint` 是次级展示物
  - Runtime 真正应主要消费的是 `SystemPrompt`

---

## 6. 典型失败样本索引（问题是如何一步步逼出今天架构的）

这部分不是错误日志，而是“典型失败模式 -> 催生的架构修正”。

### 6.1 泡泡内容像系统标签，不像用户会点的话

典型表现：

- 输出英文
- 输出 `dim:*`
- 输出抽象体验维度中文翻译
- 输出题干残片
- 内容和当前题面牛头不对马嘴

催生的修正：

- 先做输出清洗
- 但最终迫使系统承认：
  - bubble 不能再由系统视角顺手生成
  - 需要独立 `BubbleComposer`

### 6.2 Mirror 有文风，但不打心里

典型表现：

- Mirror 看起来文学化
- 但用户会觉得“不是我想要的那个世界”
- reject 后如果只是重出一版 Mirror，价值极低

催生的修正：

- Mirror 改为 dossier-driven
- reject 后不重出 Mirror
- 改为：
  - 标记 `mirror_rejected`
  - 回到访谈
  - 用下一问进行校正

### 6.3 问题方向对，但“不是我”

典型表现：

- 问题并非完全错题材
- 但更像在问“一个合理用户”
- 不是在问“这个用户”

催生的修正：

- 从“routing 足够”转向“需要持续维护 world/player understanding”
- twin dossier 概念因此被正式提出

### 6.4 最终蓝图 / 蓝图前描述像综合作文

典型表现：

- 结构有了
- 题材也对
- 但缺少“这是我一路说出来的那个世界”的感觉

催生的修正：

- 开始区分：
  - `WorldDossier / PlayerDossier`
  - `CompileOutput`
  - `FrozenCompilePackage`
- delivery 层不再允许各自重新理解用户

### 6.5 DeepSeek 漏 JSON，直接把系统打成 parse_error

典型表现：

- 模型多轮后偶尔只吐自然语言
- parse 不到 JSON
- 前端直接 Fatal Error

催生的修正：

- 引入 repair pass
- 区分：
  - 格式稳健性问题
  - 模型指令遵循问题
- 后续也加强了对“多调用架构必须先稳结构，再谈体验增强”的认识

### 6.6 文档、代码、prompt 同时描述三个不同的 Architect

典型表现：

- spec 讲一套
- runtime 跑一套
- prompt 里还写旧 schema

催生的修正：

- `implementation_plan.md` 升级为唯一实施基线
- Prompt 层被重新拆分和补齐
- 开始强调“代码优先、文档持续对账”

### 6.7 系统层级开始互相重影

典型表现：

- dossier、briefing、artifacts、blueprint、system prompt 全都像在总结同一件事
- 同一个语义被反复命名、反复提炼、反复再解释

催生的修正：

- 强制压回：
  - `State Layer`
  - `Compile Layer`
  - `Delivery Layer`
- 并后来增加：
  - `FrozenCompilePackage`

---

## 7. 仍应注意的后续风险（为下一线程准备）

即使当前已经允许进入 vNext 一次性开发，后续实现时仍要盯住这些风险：

1. 不要在实现中偷偷发明第四层对象  
2. 不要留 `suggested_tags` 和 `bubble_candidates` 双轨兼容太久  
3. 不要让 `Forge` / `Assembler` 回头读 live dossier  
4. 不要让 `InterviewComposer` 重新长回 monolith  
5. 不要让 compile / generate 失败后重新理解用户  
6. 不要为了“少报错”而把脏 dossier 悄悄带到最终 `SystemPrompt`

---

## 8. 建议的使用方式

如果后续有人在零上下文下接手本项目，建议按这个顺序读：

1. 先读本 Log 的：
   - `阶段 G ~ M`
2. 再读：
   - `implementation_plan.md`
3. 再看 prompt 文件：
   - `dossier_updater_system_prompt.md`
   - `interview_composer_system_prompt.md`
   - `bubble_composer_system_prompt.md`
   - `compile_output_system_prompt.md`
4. 最后再去读当前代码

否则很容易出现：

- 看了代码，以为旧 monolith 就是未来方向
- 看了 plan，却不知道为什么会设计成 twin dossier
- 看了 prompt，却不知道哪些是当前基线、哪些是 vNext 初版

---

## 9. 最后一句给后续接手者

这条线程最后真正得到的，不只是一个“更复杂”的架构，而是一个更清晰的判断：

> Architect 的核心不是多问几句，也不是多生成几个组件，
> 而是让系统真正把“对用户和世界的理解”变成可积累、可冻结、可交付的状态。

如果未来的改动破坏了这件事，那么无论界面多漂亮、模块多整齐，方向都已经错了。
