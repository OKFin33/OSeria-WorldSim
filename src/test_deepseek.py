"""
真实API测试 - DeepSeek
"""

import asyncio
import os
from architect_agent import ArchitectAgent


async def test_real_api():
    """使用真实API测试"""
    
    # DeepSeek API
    api_key = "sk-44fb372031204870aa6cdac146191093"
    api_base = "https://api.deepseek.com/v1"
    
    agent = ArchitectAgent(api_key=api_key, api_base=api_base)
    
    print("=== 启动会话 ===")
    session_id = "real_test_001"
    result = agent.start_session(session_id)
    print(f"Q1: {result['question']}\n")
    
    # 真实用户回答
    test_answers = [
        "一个仙侠世界，飞剑划破云霄，修真门派林立，灵气充盈天地",
        "一个复仇的剑客，曾经是天才弟子，因师门被灭而踏上复仇之路",
        "师门被灭，必须找出真相并复仇，同时面对正邪两道的追杀",
        "严肃而诗意，充满江湖恩怨，有温度但不失残酷",
        "一个神秘的剑灵作为导师，一个亦敌亦友的魔道高手",
        "剑道修为的精进，从炼气到化神，每一步都需要顿悟",
        "个人命运与江湖格局交织，选择影响正邪两道的走向",
        "一场惊心动魄的复仇之战，揭开师门被灭的真相"
    ]
    
    for i, answer in enumerate(test_answers, 1):
        print(f"=== 用户回答 Q{i} ===")
        print(f"A: {answer}\n")
        
        result = await agent.submit_answer(session_id, answer)
        
        if result.get("is_complete"):
            print("=== 所有问题完成 ===\n")
            break
        
        print(f"Q{result['step']}: {result['question']}\n")
        
        # 预生成
        if result['step'] <= 5:
            target = result['step'] + 3
            print(f"[后台预生成 Q{target}]")
            await agent.preload_question(session_id, target)
            print()
    
    print("=== 生成蓝图 ===")
    blueprint = await agent.generate_blueprint(session_id)
    
    print("\n【意图分析】")
    import json
    print(json.dumps(blueprint['intent'], ensure_ascii=False, indent=2))
    
    print("\n【系统提示词】")
    print(blueprint['system_prompt'])
    
    await agent.close()
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    asyncio.run(test_real_api())
