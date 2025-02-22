import asyncio
import json
from app.agents.question_agent import QuestionAgent

async def simulate_conversation():
    try:
        print("\n=== 태블릿 추천 시스템 ===")
        print("종료하려면 'quit' 또는 'exit'를 입력하세요.\n")
        
        agent = QuestionAgent()
        state = {}
        
        # 초기 상태
        response = await agent.run(state)
        print("\n🤖 Assistant:", response['response'])
        
        while True:
            # 사용자 입력 받기
            user_input = input("\n👤 User: ")
            
            # 종료 명령 체크
            if user_input.lower() in ['quit', 'exit']:
                print("\n프로그램을 종료합니다.")
                break
            
            # 현재 상태 유지하면서 사용자 입력 추가
            state = {
                "user_input": user_input,
                "conversation_history": response.get('conversation_history', []),
                "requirements": response.get('requirements'),
                "collected_info": response.get('collected_info', {}),
                "missing_info": response.get('missing_info', []),
                "current_question": response.get('current_question'),
                "status": response.get('status'),
                "additional_requirements": response.get('additional_requirements')
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
    except Exception as e:
        print(f"\n❌ 오류가 발생했습니다: {e}")
    finally:
        print("\n엔터 키를 눌러 종료하세요...")
        input()

if __name__ == "__main__":
    asyncio.run(simulate_conversation()) 