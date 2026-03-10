"""
会话管理 - 记录用户回答和进度
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import json


@dataclass
class ArchitectSession:
    """Architect会话"""
    session_id: str
    current_step: int = 1
    total_steps: int = 8
    collected_answers: Dict[str, str] = field(default_factory=dict)
    preloaded_questions: Dict[int, str] = field(default_factory=dict)
    
    def add_answer(self, question_id: str, answer: str):
        """记录用户回答"""
        self.collected_answers[question_id] = answer
        self.current_step += 1
    
    def is_complete(self) -> bool:
        """是否完成所有问题"""
        return self.current_step > self.total_steps
    
    def get_answer(self, question_id: str) -> Optional[str]:
        """获取指定问题的回答"""
        return self.collected_answers.get(question_id)
    
    def to_dict(self) -> dict:
        """序列化"""
        return {
            "session_id": self.session_id,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "collected_answers": self.collected_answers,
            "preloaded_questions": self.preloaded_questions
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ArchitectSession":
        """反序列化"""
        return cls(
            session_id=data["session_id"],
            current_step=data["current_step"],
            total_steps=data["total_steps"],
            collected_answers=data["collected_answers"],
            preloaded_questions=data.get("preloaded_questions", {})
        )
