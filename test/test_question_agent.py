import asyncio
import json
from app.agents.question_agent import QuestionAgent

async def simulate_conversation():
    agent = QuestionAgent()
    state = {}
    
    # 초기 상태
    response = await agent.run(state)
    print("\n🤖 Assistant:", response['response'])
    
    while True:
        # 사용자 입력 받기
        user_input = input("\n👤 User: ")
        
        # 현재 상태에 따라 state 업데이트
        if response.get('status') == "collecting_input":
            state = {
                "user_input": user_input,
                "conversation_history": response.get('conversation_history', []),
                "status": "collecting_input"
            }
        elif response.get('status') == "confirming_requirements":
            state = {
                "user_input": user_input,
                "conversation_history": response.get('conversation_history', []),
                "requirements": response.get('requirements'),
                "status": "confirming_requirements"
            }
        
        # 에이전트 실행
        response = await agent.run(state)
        print("\n🤖 Assistant:", response['response'])
        
        # completed 상태면 최종 결과 출력하고 종료
        if response.get('status') == "completed":
            # 추가 agent states 준비
            agent_states = await agent._prepare_agent_states(response['requirements'])
            
            print("\n📊 Spec Analysis:")
            print(json.dumps(agent_states['spec_agent_state'], indent=2, ensure_ascii=False))
            
            print("\n📝 Review Analysis:")
            print(json.dumps(agent_states['review_agent_state'], indent=2, ensure_ascii=False))
            
            print("\n🎥 YouTube Analysis:")
            print(json.dumps(agent_states['youtube_agent_state'], indent=2, ensure_ascii=False))
            break

if __name__ == "__main__":
    asyncio.run(simulate_conversation()) 