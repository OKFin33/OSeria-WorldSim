spec_version: "2.0"
spec_name: "fosun_tourism_group_full_strategy_consulting_research_spec"
language: "zh-CN"
intended_runner: "ChatGPT Agent"
project_type: "战略咨询级完整调研"
project_mode: "full_diagnostic_and_strategy_recommendation"
target_company:
  name_cn: "复星旅游文化集团"
  name_en: "Fosun Tourism Group"
  aliases:
    - "复星旅文"
    - "FTG"
  current_status_note: "2025年3月已完成私有化并退市；研究时不得按持续上市公司常规覆盖逻辑处理"

mission:
  primary_goal: >
    围绕复星旅文开展一项接近战略咨询公司标准的完整调研，
    从行业吸引力、客户需求、业务组合、产品、市场、销售、运营、组织与战略路径等维度形成系统判断，
    最终输出能够支持管理层或课程汇报场景进行战略讨论的结论、选项比较与实施建议。
  final_question: >
    在中国及全球文旅消费结构演变、资产模式重构和竞争格局变化背景下，
    复星旅文未来应采取何种业务组合与增长战略，以实现更可持续的竞争优势、更高的资本效率与更强的运营韧性？

project_context:
  use_case:
    - "课程任务可参考，但本spec按专业完整调研标准设计"
    - "适用于希望让agent产出接近战略咨询分析底稿的场景"
  expected_time_horizon:
    short_term: "0-12个月"
    medium_term: "1-3年"
    long_term: "3-5年"
  expected_output_style:
    - "结论先行"
    - "问题导向"
    - "证据支撑"
    - "可比较的战略选项"
    - "可执行的实施路径"

hard_requirements:
  - "所有涉及2025年及之后的事实必须优先使用最新可得官方或高质量权威来源确认"
  - "不得将复星旅文误写为当前港股持续上市公司"
  - "若关键事实仅有低质量来源支撑，则只能列为线索，不得形成强结论"
  - "所有结论必须区分：已验证事实、基于证据的判断、待验证推断"
  - "输出不得退化成百科式公司介绍"
  - "输出必须包含战略选项比较，而非单一路径口号"
  - "所有分析都要说明对战略含义（implication）"

source_policy:
  source_priority:
    tier_1_must_use:
      - "复星旅文官方网站（中英文）"
      - "复星国际投资者关系网站（IR）"
      - "港交所历史公告/私有化方案/退市相关文件"
      - "公司正式新闻稿、官方公众号、官方发布会资料"
      - "政府主管部门/统计部门/文旅主管部门公开文件"
    tier_2_high_quality:
      - "Reuters"
      - "主流财经媒体（财新、界面、证券时报、第一财经等，以原始采访或明确引述为优先）"
      - "头部咨询/研究机构公开报告摘要"
      - "行业协会和权威数据库公开材料"
    tier_3_supporting:
      - "OTA公开页面和规则"
      - "地图平台/点评平台公开信息"
      - "社交媒体公开内容（仅用于洞察用户心智、传播话术和高频体验反馈）"
    prohibited_as_primary_evidence:
      - "无来源转载"
      - "论坛传言"
      - "单篇自媒体观点"
      - "聚合站未标原始出处的内容"
  freshness_rules:
    company_status_and_structure:
      max_age_preferred: "12个月"
      mandatory_check: true
    industry_trends:
      max_age_preferred: "18个月"
      mandatory_check: true
    strategy_or_management_changes:
      max_age_preferred: "6个月"
      mandatory_check: true
    user_feedback_and_channel_observation:
      max_age_preferred: "6个月"
      mandatory_check: false
  validation_rules:
    - "公司定义、业务结构、品牌矩阵、退市状态必须至少由1个官方来源确认"
    - "关键战略变化至少由1个官方来源和1个高质量外部来源交叉验证"
    - "涉及经营表现的强判断，尽量用至少2类来源支撑"
    - "点评/社媒只能支持体验观察类洞察，不能单独支撑战略结论"

research_design:
  top_issue_tree:
    level_1:
      - "赛道是否仍具足够吸引力"
      - "复星旅文当前竞争位置如何"
      - "其核心优势与核心约束分别是什么"
      - "未来有哪些可行战略路径"
      - "推荐路径是什么以及如何落地"
    level_2:
      market_attractiveness:
        - "文旅消费趋势是否支持目的地度假和家庭休闲需求"
        - "轻重资产模式的行业演化方向是什么"
        - "利润池集中在哪些环节"
      customer_and_demand:
        - "核心客群是谁"
        - "关键消费场景是什么"
        - "未满足需求在哪里"
      company_diagnostic:
        - "业务组合是否合理"
        - "产品力是否具备差异化"
        - "市场定位是否清晰"
        - "销售与渠道是否高效"
        - "运营能力是否可复制"
        - "组织与能力是否支持未来扩张"
      strategy_choice:
        - "重资产深耕是否仍然成立"
        - "轻资产输出是否具备现实基础"
        - "双轮驱动是否可行"
        - "哪些业务该加码、优化或收缩"

analysis_framework:
  phase_structure:
    - phase_id: "phase_1"
      name: "问题定义与快速扫描"
      objective: "明确战略命题、界定研究边界、识别关键模块和优先级"
      outputs:
        - "项目问题树"
        - "研究边界说明"
        - "关键数据缺口表"
    - phase_id: "phase_2"
      name: "外部环境与行业吸引力分析"
      objective: "判断赛道机会、行业演化和竞争逻辑"
      outputs:
        - "宏观与政策趋势分析"
        - "行业结构与利润池分析"
        - "竞争格局与关键成功因素"
    - phase_id: "phase_3"
      name: "客户与需求洞察"
      objective: "识别核心客群、场景和增长机会"
      outputs:
        - "客群分层"
        - "场景矩阵"
        - "需求迁移与机会地图"
    - phase_id: "phase_4"
      name: "公司现状诊断"
      objective: "从业务组合到一线运营系统性评估复星旅文"
      outputs:
        - "业务组合诊断"
        - "产品/市场/销售/运营诊断"
        - "组织与能力评估"
        - "关键瓶颈归纳"
    - phase_id: "phase_5"
      name: "战略选项设计与比较"
      objective: "形成2-3个可比战略路径并评估优先级"
      outputs:
        - "战略选项定义"
        - "选项比较矩阵"
        - "推荐方案"
    - phase_id: "phase_6"
      name: "实施路径与管理建议"
      objective: "将推荐路径落到分阶段动作、能力建设和风险管理"
      outputs:
        - "路线图"
        - "关键举措包"
        - "组织与能力保障"
        - "关键风险与前提条件"

macro_meso_micro_mapping:
  macro:
    focus:
      - "消费趋势"
      - "政策趋势"
      - "文旅与文创融合趋势"
      - "旅游休闲与目的地消费演变"
    key_questions:
      - "文旅消费升级和体验经济如何影响复星旅文"
      - "政策是否支持其重点模式与重点区域"
  meso:
    focus:
      - "行业定义"
      - "价值链"
      - "利润池"
      - "竞争格局"
      - "细分赛道吸引力"
    key_questions:
      - "复星旅文更接近哪类企业：度假平台、综合体运营商、品牌运营平台或混合型"
      - "行业关键成功因素是什么"
  micro:
    focus:
      - "业务组合"
      - "产品"
      - "市场"
      - "销售"
      - "运营"
      - "组织与能力"
      - "资本与资产模式"
    key_questions:
      - "复星旅文真正强的是什么"
      - "其增长瓶颈在哪里"
      - "其模式的可复制性和资本效率如何"

micro_diagnostic_modules:
  business_portfolio:
    questions:
      - "集团有哪些核心业务单元"
      - "各业务单元的战略角色是什么：增长引擎、利润来源、样板资产还是资源消耗项"
      - "业务组合是否存在分散或协同不足"
  product:
    questions:
      - "核心产品究竟是什么：住宿、度假体验、娱乐内容、综合目的地还是生活方式场景"
      - "文创内容如何嵌入：IP、叙事、活动、空间、服务"
      - "差异化是品牌驱动、资源驱动还是运营驱动"
      - "产品标准化与复制性如何"
  market:
    questions:
      - "目标客群与消费场景如何分层"
      - "品牌在消费者心智中的位置是什么"
      - "与竞品相比的定位差异是什么"
      - "区域布局与市场机会是否匹配"
  sales:
    questions:
      - "销售触点有哪些：官方、会员、OTA、旅行社、异业合作、目的地流量"
      - "价格与套餐结构如何"
      - "获客与复购逻辑如何"
      - "是否有有效的会员经营和二次消费机制"
  operations:
    questions:
      - "现场运营的核心能力是什么"
      - "在服务流程、空间动线、人流组织、活动运营、家庭友好度上表现如何"
      - "存量项目提效空间在哪里"
      - "运营能力是否能支撑轻资产复制"
  organization_and_capabilities:
    questions:
      - "总部能力是什么"
      - "项目端能力是什么"
      - "组织架构与激励是否支持未来战略"
      - "管理复杂度是否超过组织承载能力"
  capital_and_asset_model:
    questions:
      - "轻重资产结构如何影响战略选择"
      - "哪些资产是样板、哪些资产是现金流来源、哪些资产可能拖累资本效率"
      - "战略自由度与资本约束如何平衡"

benchmarking:
  required_peer_types:
    direct_peers:
      - "同类型度假品牌或综合文旅平台"
    substitute_peers:
      - "同客群/同场景竞争者"
    reference_peers:
      - "模式更成熟或资本效率更优的国内外标杆"
  benchmarking_dimensions:
    - "产品定位"
    - "客群"
    - "价格带"
    - "渠道结构"
    - "运营模式"
    - "资产模式"
    - "增长逻辑"
  peer_selection_rule: >
    不要求强行选择完全相同公司，但必须说明为什么这个对标对象有参考价值。
    对标对象需覆盖中国本土案例与全球/国际参考案例。

tooling:
  enabled_capabilities:
    - "联网搜索"
    - "官方网页阅读"
    - "PDF/公告阅读"
    - "结构化摘录"
    - "表格归纳"
    - "对比分析"
    - "问题树生成"
    - "战略选项矩阵生成"
  required_tool_behavior:
    - "先官方后媒体，再辅助平台"
    - "先确认状态和定义，再分析业务"
    - "对PDF公告优先读取原文或官方版本"
    - "在输出前做一次事实回检，尤其是2025年后的状态、组织和业务口径"

search_plan:
  sequence:
    - step: "确认当前状态与一手入口"
      queries:
        - "复星旅文 官网"
        - "Fosun Tourism Group official"
        - "复星旅文 港交所 退市 2025"
        - "Fosun Tourism Group delisting HKEX 2025"
        - "复星国际 IR tourism FTG 2024 2025"
    - step: "提取官方业务结构与品牌信息"
      queries:
        - "复星旅文 业务 品牌 Club Med Atlantis"
        - "Fosun Tourism Group business portfolio Club Med Atlantis"
        - "复星旅文 官网 品牌 度假村"
    - step: "获取行业与趋势证据"
      queries:
        - "中国 文旅消费 趋势 2025 2026"
        - "中国 亲子度假 高端度假 趋势"
        - "文创 文旅 融合 趋势 中国"
        - "destination resort China trend 2025"
    - step: "获取高质量外部评价与交易/战略变化"
      queries:
        - "Reuters Fosun Tourism 2024 2025"
        - "复星旅文 轻资产 路透 界面 财新"
        - "Atlantis Sanya Fosun Reuters"
    - step: "获取用户体验与渠道侧辅助线索"
      queries:
        - "Club Med 评论 攻略 中国"
        - "三亚亚特兰蒂斯 评论 攻略"
        - "Club Med OTA 会员 套餐"
        - "亚特兰蒂斯 套票 会员 门票"

search_filters_and_rules:
  official_first: true
  must_check_date_on_every_source: true
  must_record_source_type: true
  preferred_regions:
    - "中国"
    - "全球业务相关国家/地区（仅在涉及Club Med等国际业务时）"
  freshness_bias:
    - "2025-2026优先"
    - "如使用更早材料，必须说明仅作历史背景"

evidence_extraction_schema:
  for_each_finding:
    fields:
      - "finding_statement"
      - "source_type"
      - "source_name"
      - "date"
      - "relevance_to_issue"
      - "confidence_level"
      - "implication"
  confidence_levels:
    - "high: 官方或多方高质量交叉验证"
    - "medium: 单一高质量来源或多条辅助来源一致"
    - "low: 仅辅助平台或推断"
  mandatory_labels:
    - "fact"
    - "judgment"
    - "hypothesis"
    - "to_be_validated"

consulting_analysis_rules:
  style_rules:
    - "先回答问题，再展示材料"
    - "每个模块先给核心结论，再给支持证据"
    - "每个模块最后必须写战略含义（implication）"
    - "避免纯描述，不允许只做信息罗列"
  synthesis_rules:
    - "从宏观、中观、微观归纳出3-6个真正关键的战略问题"
    - "关键问题必须能连接到后续战略选项"
    - "每个结论都要尽量说明对增长、竞争力或资本效率的影响"
  decision_rules:
    - "不要默认轻资产一定更优，必须分析前提和能力要求"
    - "不要默认品牌即壁垒，必须分析是否转化为定价、复购或渠道效率"
    - "不要默认大项目即优势，必须分析其资本占用与运营复杂度"
  anti_patterns:
    - "禁止将调研写成公司简介"
    - "禁止泛泛罗列PEST、SWOT而无落地结论"
    - "禁止大量复制新闻原文"
    - "禁止将单个项目体验直接等同于集团整体能力"

strategic_options_module:
  minimum_option_count: 3
  required_option_types:
    - "旗舰重资产深耕型"
    - "轻资产/管理输出优先型"
    - "旗舰样板+轻资产复制的双轮型"
  evaluation_dimensions:
    - "市场吸引力"
    - "客户契合度"
    - "竞争优势匹配度"
    - "资本效率"
    - "组织可执行性"
    - "风险"
    - "实施周期"
  output_requirements:
    - "每个选项的定义"
    - "优点"
    - "缺点"
    - "成立前提"
    - "关键风险"
    - "适用条件"
    - "不选的代价"

implementation_module:
  required_horizons:
    short_term:
      label: "0-12个月"
      include:
        - "优先举措"
        - "快速见效动作"
        - "组织调整起点"
    medium_term:
      label: "1-3年"
      include:
        - "重点能力建设"
        - "产品与渠道优化"
        - "复制与扩张机制"
    long_term:
      label: "3-5年"
      include:
        - "平台能力形成"
        - "业务组合重塑"
        - "长期竞争壁垒"
  must_include:
    - "关键前提条件"
    - "组织与人才要求"
    - "KPI/里程碑建议"
    - "主要风险与应对"

deliverables:
  required_sections:
    - "一、执行摘要（结论先行）"
    - "二、项目目标与战略命题"
    - "三、外部环境与行业吸引力"
    - "四、客户与需求洞察"
    - "五、复星旅文现状诊断"
    - "六、核心战略问题归纳"
    - "七、战略选项设计与比较"
    - "八、推荐路径与实施路线图"
    - "九、主要风险、前提条件与信息缺口"
    - "十、附录：关键证据、来源说明、对标表"
  section_requirements:
    "一、执行摘要（结论先行）":
      must_include:
        - "3-5条核心判断"
        - "推荐战略方向"
        - "关键原因"
    "三、外部环境与行业吸引力":
      must_include:
        - "宏观趋势"
        - "政策影响"
        - "行业演化"
        - "利润池与竞争格局"
    "四、客户与需求洞察":
      must_include:
        - "客群细分"
        - "场景矩阵"
        - "需求迁移"
        - "机会地图"
    "五、复星旅文现状诊断":
      must_include:
        - "业务组合"
        - "产品"
        - "市场"
        - "销售"
        - "运营"
        - "组织与能力"
        - "资产/资本模式"
    "七、战略选项设计与比较":
      must_include:
        - "至少3个选项"
        - "比较矩阵"
        - "推荐逻辑"
    "八、推荐路径与实施路线图":
      must_include:
        - "短中长期路线图"
        - "关键举措包"
        - "组织与能力要求"
  preferred_appendices:
    - "来源清单（按优先级分类）"
    - "时间线"
    - "竞品对标表"
    - "关键术语定义"

quality_bar:
  must_pass_checks:
    - "是否使用了官方和高质量最新来源"
    - "是否清晰说明了复星旅文已退市及由此带来的信息边界"
    - "是否真正形成战略问题，而非信息罗列"
    - "是否对产品/市场/销售/运营做了专业诊断"
    - "是否形成了可比较的战略选项"
    - "是否给出了实施路线图"
    - "是否明确指出证据强弱和信息缺口"
    - "是否每一章都有明确implication"
  scoring_dimensions:
    source_quality: 25
    analytical_depth: 25
    strategic_value: 25
    execution_clarity: 15
    structure_and_readability: 10

output_style:
  tone: "专业、克制、结论先行、接近咨询汇报"
  language: "中文"
  formatting_rules:
    - "多用小标题和分层结构"
    - "尽量使用矩阵、表格和问题树"
    - "避免冗长叙述"
    - "每章开头给结论，每章结尾给含义"
  forbidden_output_types:
    - "百科全书式长文"
    - "空泛套话式SWOT"
    - "未标注证据强弱的结论"

final_instruction: >
  你的任务不是写一篇“关于复星旅文的介绍”，
  而是像战略咨询项目一样，利用最新且可靠的公开信息，
  识别关键商业问题，完成专业诊断，形成可比较的战略选项，
  并给出具有现实约束意识的推荐路径与实施建议。