"""
Interview Controller — 访谈流程的代码层控制器

职责：
1. 管理访谈轮次
2. 解析每轮 LLM 输出的 routing_snapshot
3. 判定是否触发 Mirror（终止条件）
4. 管理 Mirror → Landing → Final Deliverables 的状态流转
"""

from enum import Enum
from typing import Optional


class InterviewPhase(Enum):
    """访谈阶段状态机"""
    INTERVIEWING = "interviewing"    # 正常访谈中（Q1 静态，Q2+ 动态）
    MIRROR = "mirror"                # 触发 Mirror，等待用户确认
    LANDING = "landing"              # Mirror 确认后，询问性别
    COMPLETE = "complete"            # 全部完成，输出三大交付物


# ─── 可调参数 ───────────────────────────────────────────────
MAX_TURNS = 6                # 硬性上限：最多 6 轮对话（不含 Mirror 和 Landing）
UNTOUCHED_THRESHOLD = 2      # untouched 维度 ≤ 此值时触发 Mirror
# ────────────────────────────────────────────────────────────


class InterviewController:
    """
    代码层的访谈流程控制器。
    
    LLM 负责：生成问题、回声、routing_snapshot
    代码层负责：判定何时终止、状态流转
    """

    def __init__(self):
        self.turn: int = 0
        self.phase: InterviewPhase = InterviewPhase.INTERVIEWING
        self.history: list[dict] = []  # 每轮的 routing_snapshot 记录

    def should_trigger_mirror(self, routing_snapshot: dict) -> bool:
        """
        根据 routing_snapshot 判定是否触发 Mirror。
        
        触发条件（任一满足即触发）：
        1. untouched 维度数量 ≤ UNTOUCHED_THRESHOLD
        2. 当前轮次 ≥ MAX_TURNS
        
        Args:
            routing_snapshot: LLM 输出的实时路由快照，格式：
                {
                    "confirmed": ["dim:xxx", ...],
                    "exploring": ["dim:xxx", ...],
                    "excluded": ["dim:xxx", ...],
                    "untouched": ["dim:xxx", ...]
                }
        
        Returns:
            bool: 是否应触发 Mirror
        """
        untouched_count = len(routing_snapshot.get("untouched", []))

        # 条件 1：维度探索基本覆盖
        if untouched_count <= UNTOUCHED_THRESHOLD:
            return True

        # 条件 2：硬性轮次上限（防止用户疲劳）
        if self.turn >= MAX_TURNS:
            return True

        return False

    def process_turn(self, llm_response: dict) -> InterviewPhase:
        """
        处理一轮访谈的 LLM 输出，推进状态机。
        
        Args:
            llm_response: LLM 的系统侧 JSON 输出
        
        Returns:
            InterviewPhase: 下一阶段
        """
        if self.phase == InterviewPhase.INTERVIEWING:
            self.turn += 1
            routing_snapshot = llm_response.get("routing_snapshot", {})
            self.history.append(routing_snapshot)

            if self.should_trigger_mirror(routing_snapshot):
                self.phase = InterviewPhase.MIRROR

        elif self.phase == InterviewPhase.MIRROR:
            # Mirror 确认后进入 Landing
            self.phase = InterviewPhase.LANDING

        elif self.phase == InterviewPhase.LANDING:
            # Landing 回复后，输出最终交付物
            self.phase = InterviewPhase.COMPLETE

        return self.phase

    def get_system_instruction(self) -> Optional[str]:
        """
        根据当前阶段，返回注入给 LLM 的系统指令。
        
        Returns:
            str | None: 注入到下一轮 LLM 调用的系统指令，None 表示无需额外指令
        """
        if self.phase == InterviewPhase.MIRROR:
            return (
                "[系统指令] 信号已充分。请停止提问，"
                "立即生成 The Mirror（世界缩影）。"
                "200 字以内，叙事性语言，必须让他起鸡皮疙瘩。"
            )

        if self.phase == InterviewPhase.LANDING:
            return (
                "[系统指令] 用户已确认 Mirror。进入 The Landing 阶段。"
                "以刻意简单冷漠的语气问出两个性别问题。"
            )

        if self.phase == InterviewPhase.COMPLETE:
            return (
                "[系统指令] 用户已回答性别问题。"
                "请输出最终的三个交付物 JSON："
                "confirmed_dimensions / emergent_dimensions / excluded_dimensions、"
                "narrative_briefing、player_profile。"
            )

        return None

    def finalize_routing(self) -> dict:
        """
        将最终的 routing_snapshot 中的 untouched 转为 emergent。
        
        在输出最终交付物前调用。
        untouched 中剩余的维度 → emergent（留白涌现）
        
        Returns:
            dict: 最终的三态路由标签
        """
        if not self.history:
            return {"confirmed": [], "emergent": [], "excluded": []}

        last_snapshot = self.history[-1]
        return {
            "confirmed_dimensions": last_snapshot.get("confirmed", []),
            "emergent_dimensions": last_snapshot.get("untouched", []),
            "excluded_dimensions": last_snapshot.get("excluded", []),
        }
