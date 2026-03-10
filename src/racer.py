"""
竞赛机制 - 静态/预生成 vs 定制
"""

import asyncio
from typing import Optional, Callable


class QuestionRacer:
    """问题竞赛器"""
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
    
    async def race(
        self,
        fallback_question: str,
        custom_generator: Callable[[], asyncio.Task]
    ) -> tuple[str, str]:
        """
        竞赛：保底版本 vs 定制版本
        
        返回: (question, source)
        - source: "fallback" 或 "custom"
        """
        
        # 启动定制版本生成
        custom_task = custom_generator()
        
        # 竞赛：定制版本 vs 超时
        try:
            custom_question = await asyncio.wait_for(custom_task, timeout=self.timeout)
            return (custom_question, "custom")
        except asyncio.TimeoutError:
            return (fallback_question, "fallback")
        except Exception as e:
            print(f"定制版本生成失败: {e}")
            return (fallback_question, "fallback")
