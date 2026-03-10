"""
测试完整流程
"""

import asyncio
import os
from architect_agent import ArchitectAgent


async def test_full_flow():
    """测试完整的Q1-Q8流程"""
    
    api_key = os.getenv("MODELSCOPE_API_KEY", "test")
    agent = ArchitectAgent(api_key=api_key)
    
    # 1. 启动会话
    print("=== 启动会话 ===")
    session_id = "test_session_001"
    result = agent.start_session(session_id)
    print(f"Q1: {result['question']}\n")
    
    # 2. 模拟用户回答Q1-Q8
    test_answers = [
        "一个仙侠世界，飞剑划破云霄，修真门派林立",
        "一个复仇的剑客，曾经的天才弟子",
        "师门被灭，必须找出真相并复仇",
        "严肃而诗意，充满江湖恩怨",
        "一个神秘的剑灵，一个亦敌亦友的魔道高手",
        "剑道修为，从炼气到化神",
        "个人命运与江湖格局交织",
        "一场惊心动魄的复仇之战"
    ]
    
    for i, answer in enumerate(test_answers, 1):
        print(f"=== 用户回答 Q{i} ===")
        print(f"A: {answer}\n")
        
        # 提交回答
        result = await agent.submit_answer(session_id, answer)
        
        if result.get("is_complete"):
            print("=== 所有问题完成 ===\n")
            break
        
        # 显示下一题
        print(f"Q{result['step']}: {result['question']}\n")
        
        # 预生成Q(step+3)
        if result['step'] <= 5:
            target = result['step'] + 3
            print(f"[后台] 预生成 Q{target}...")
            await agent.preload_question(session_id, target)
            print()
    
    # 3. 生成蓝图
    print("=== 生成蓝图 ===")
    blueprint = await agent.generate_blueprint(session_id)
    
    print("\n用户意图：")
    print(blueprint['intent'])
    
    print("\n系统提示词：")
    print(blueprint['system_prompt'])
    
    await agent.close()


if __name__ == "__main__":
    asyncio.run(test_full_flow())
