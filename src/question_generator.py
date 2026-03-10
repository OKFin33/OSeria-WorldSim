"""
问题生成器 - 静态问题 + 动态定制
"""

import json
from pathlib import Path
from typing import Dict, Optional


class QuestionGenerator:
    """问题生成器"""
    
    def __init__(self, questions_path: str):
        self.questions_path = Path(questions_path)
        self.static_questions = self._load_static_questions()
    
    def _load_static_questions(self) -> Dict[str, dict]:
        """加载静态问题"""
        with open(self.questions_path, 'r', encoding='utf-8') as f:
            questions = json.load(f)
        return {q["id"]: q for q in questions}
    
    def get_static_question(self, step: int) -> Optional[str]:
        """获取静态问题"""
        question_ids = ["setting", "protagonist", "conflict", "tone", 
                       "companions", "power", "stakes", "dream"]
        if 1 <= step <= 8:
            q_id = question_ids[step - 1]
            return self.static_questions[q_id]["text"]
        return None
    
    async def generate_custom_question(
        self, 
        llm_caller,
        step: int, 
        collected_answers: Dict[str, str]
    ) -> str:
        """生成定制问题"""
        
        # 获取静态问题作为基础
        static_q = self.get_static_question(step)
        
        # 构建已有回答的上下文
        context = self._build_context(collected_answers)
        
        prompt = f"""你是OSeria的Architect。用户已经回答了前面的问题，现在需要生成下一个问题。

已有回答：
{context}

静态问题模板：
{static_q}

要求：
1. 保持问题的核心目的不变
2. 顺着用户的话说，让用户感觉被重视
3. 例如："那么在这个仙侠世界中..."
4. 保持诗意和引导性

直接输出定制问题，不要其他内容。"""
        
        return await llm_caller(prompt, system="你是OSeria的Architect")
    
    def _build_context(self, collected_answers: Dict[str, str]) -> str:
        """构建回答上下文"""
        if not collected_answers:
            return "（暂无）"
        
        lines = []
        for q_id, answer in collected_answers.items():
            q_text = self.static_questions[q_id]["text"]
            lines.append(f"Q: {q_text}\nA: {answer}\n")
        
        return "\n".join(lines)
