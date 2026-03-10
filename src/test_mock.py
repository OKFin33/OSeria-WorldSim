"""
Mock测试 - 简化版本
"""

import asyncio
from architect_agent import ArchitectAgent


class MockArchitectAgent(ArchitectAgent):
    """Mock版本"""
    
    async def _call_llm(self, prompt: str, system: str = None) -> str:
        """Mock LLM调用"""
        await asyncio.sleep(0.1)
        
        if "分析用户的8轮回答" in prompt:
            return '{"world_type": "仙侠", "core_themes": ["复仇", "成长"], "tone": "严肃诗意", "key_elements": {}}'
        
        if "生成定制化的世界观" in prompt:
            return "## 世界观\n仙侠世界\n\n## 叙事风格\n- 诗意语言\n\n## 特殊规则\n- 输出world_stats"
        
        if "静态问题模板" in prompt:
            # 根据已有回答数量判断目标步骤
            answer_count = prompt.count("Q:")
            questions = [
                None,
                "那么在这个仙侠世界中，你将成为谁？",
                "在这个世界里，是什么让你无法安于现状？",
                "这段旅程的基调是什么？",
                "在复仇的路上，你希望遇见什么样的人？",
                "在这个世界里，力量意味着什么？",
                "你的选择将带来什么？",
                "最后，你最想体验什么？"
            ]
            target = answer_count + 1
            return questions[target] if target < len(questions) else "继续..."
        
        return "Mock"


async def test():
    agent = MockArchitectAgent(api_key="mock")
    
    print("=== 测试开始 ===\n")
    session_id = "test_001"
    result = agent.start_session(session_id)
    print(f"✓ Q1: {result['question'][:40]}...\n")
    
    answers = ["仙侠", "剑客", "师门", "严肃", "伙伴", "修为", "格局", "复仇"]
    
    for i, answer in enumerate(answers, 1):
        result = await agent.submit_answer(session_id, answer)
        
        if result.get("is_complete"):
            print("✓ 完成\n")
            break
        
        print(f"✓ Q{result['step']}: {result['question'][:40]}...")
        
        if result['step'] <= 5:
            await agent.preload_question(session_id, result['step'] + 3)
    
    print("\n=== 蓝图 ===")
    blueprint = await agent.generate_blueprint(session_id)
    print(f"✓ 类型: {blueprint['intent']['world_type']}")
    print(f"✓ 提示词: {len(blueprint['system_prompt'])} 字符")
    
    await agent.close()
    print("\n✅ 测试通过！")


if __name__ == "__main__":
    asyncio.run(test())
