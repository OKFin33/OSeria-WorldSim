"""
独立Architect Agent - 完整实现

功能：
1. 深度访谈（Q1-Q8）- 静态+动态定制+竞赛机制
2. 蓝图生成 - 分析回答生成系统提示词
"""

import json
import asyncio
import httpx
from typing import Dict, Optional
from pathlib import Path

from session import ArchitectSession
from question_generator import QuestionGenerator
from racer import QuestionRacer


class ArchitectAgent:
    """完整的Architect Agent"""
    
    def __init__(self, api_key: str, api_base: str = "https://api-inference.modelscope.cn/v1"):
        self.api_key = api_key
        self.api_base = api_base
        self.client = httpx.AsyncClient(timeout=60.0)
        
        # 加载问题生成器
        questions_path = Path(__file__).parent.parent / "data" / "questions.json"
        self.question_gen = QuestionGenerator(str(questions_path))
        
        # 竞赛器
        self.racer = QuestionRacer(timeout=5.0)
        
        # 会话存储
        self.sessions: Dict[str, ArchitectSession] = {}
    
    async def _call_llm(self, prompt: str, system: str = None) -> str:
        """调用LLM"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.post(
            f"{self.api_base}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    # === 会话管理 ===
    
    def start_session(self, session_id: str) -> dict:
        """启动新会话"""
        session = ArchitectSession(session_id=session_id)
        self.sessions[session_id] = session
        
        # 返回Q1（静态）
        q1 = self.question_gen.get_static_question(1)
        return {
            "session_id": session_id,
            "step": 1,
            "total_steps": 8,
            "question": q1
        }
    
    async def submit_answer(self, session_id: str, answer: str) -> dict:
        """提交用户回答"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"会话不存在: {session_id}")
        
        # 记录回答
        question_ids = ["setting", "protagonist", "conflict", "tone", 
                       "companions", "power", "stakes", "dream"]
        current_q_id = question_ids[session.current_step - 1]
        session.add_answer(current_q_id, answer)
        
        # 检查是否完成
        if session.is_complete():
            return {
                "step": session.current_step,
                "total_steps": 8,
                "is_complete": True
            }
        
        # 获取下一题
        next_step = session.current_step
        next_question = await self._get_next_question(session, next_step)
        
        return {
            "step": next_step,
            "total_steps": 8,
            "is_complete": False,
            "question": next_question
        }
    
    async def _get_next_question(self, session: ArchitectSession, step: int) -> str:
        """获取下一题（竞赛机制）"""
        
        # Q2-Q3: 静态 vs 定制
        if step in [2, 3]:
            fallback = self.question_gen.get_static_question(step)
            
            async def generate_custom():
                return await self.question_gen.generate_custom_question(
                    self._call_llm, step, session.collected_answers
                )
            
            question, source = await self.racer.race(fallback, generate_custom)
            print(f"Q{step} 竞赛结果: {source}")
            return question
        
        # Q4-Q8: 预生成 vs 定制
        elif step >= 4:
            # 检查预生成缓存
            fallback = session.preloaded_questions.get(step)
            if not fallback:
                # 没有预生成，生成一个
                fallback = await self.question_gen.generate_custom_question(
                    self._call_llm, step, session.collected_answers
                )
            
            async def generate_custom():
                return await self.question_gen.generate_custom_question(
                    self._call_llm, step, session.collected_answers
                )
            
            question, source = await self.racer.race(fallback, generate_custom)
            print(f"Q{step} 竞赛结果: {source}")
            return question
        
        # Q1: 直接返回静态
        else:
            return self.question_gen.get_static_question(step)
    
    async def preload_question(self, session_id: str, target_step: int):
        """预生成问题（Q4-Q8）"""
        session = self.sessions.get(session_id)
        if not session:
            return
        
        # 只预生成Q4-Q8
        if target_step < 4 or target_step > 8:
            return
        
        try:
            # 基于当前已有回答生成
            question = await self.question_gen.generate_custom_question(
                self._call_llm, target_step, session.collected_answers
            )
            
            # 缓存
            session.preloaded_questions[target_step] = question
            print(f"预生成 Q{target_step} 完成")
        except Exception as e:
            print(f"预生成 Q{target_step} 失败: {e}")
    
    # === 蓝图生成 ===
    
    async def generate_blueprint(self, session_id: str) -> dict:
        """生成最终蓝图"""
        session = self.sessions.get(session_id)
        if not session or not session.is_complete():
            raise ValueError("会话未完成")
        
        # 分析用户意图
        intent = await self._analyze_intent(session.collected_answers)
        
        # 生成系统提示词
        system_prompt = await self._generate_system_prompt(intent, session.collected_answers)
        
        return {
            "intent": intent,
            "system_prompt": system_prompt
        }
    
    async def _analyze_intent(self, collected_answers: Dict[str, str]) -> dict:
        """分析用户意图"""
        
        answers_text = "\n".join([
            f"{q_id}: {answer}" 
            for q_id, answer in collected_answers.items()
        ])
        
        prompt = f"""分析用户的8轮回答，提取核心意图。

用户回答：
{answers_text}

提取：
1. 世界类型（武侠/赛博朋克/魔法/现代等）
2. 核心主题（冒险/情感/策略/成长等）
3. 风格基调（严肃/轻松/黑暗/温暖等）
4. 关键元素（重要的设定、角色、冲突等）

必须输出纯JSON格式，不要任何其他文字：
{{
    "world_type": "...",
    "core_themes": ["...", "..."],
    "tone": "...",
    "key_elements": {{}}
}}"""
        
        response = await self._call_llm(prompt, system="你是OSeria的首席架构师。只输出JSON，不要其他内容。")
        
        # 清理可能的markdown代码块
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1])
        
        return json.loads(response)
    
    async def _generate_system_prompt(self, intent: dict, collected_answers: Dict[str, str]) -> str:
        """生成系统提示词"""
        
        core_prompt = """你是互动叙事AI，根据用户行动推进故事。

核心原则：
1. 保持角色扮演沉浸感
2. 根据用户行动合理推进剧情
3. 每轮输出包含叙事文本和元数据

输出格式：
{
  "text": "叙事文本（200-400字）",
  "meta": {
    "world_stats": {
      "name": "主角姓名",
      "location": "当前位置",
      "status": "当前状态"
    },
    "short_term_memory": "最近3轮的关键事件"
  }
}

叙事要求：
- 文字优美，有画面感
- 节奏适中，张弛有度
- 尊重用户选择，合理推进
- 保持世界观一致性"""
        
        # 生成定制内容
        custom_content = await self._generate_custom_content(intent)
        
        return f"""{core_prompt}

---

{custom_content}"""
    
    async def _generate_custom_content(self, intent: dict) -> str:
        """生成定制内容"""
        
        prompt = f"""根据用户需求生成定制化的世界观和规则。

用户意图：
{json.dumps(intent, ensure_ascii=False, indent=2)}

生成内容：
1. 世界观描述（200-300字，具体生动）
2. 叙事风格指导（3-5条）
3. 特殊规则（如果需要）

直接输出内容，不要JSON包装。"""
        
        return await self._call_llm(prompt, system="你是系统提示词设计师")
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
