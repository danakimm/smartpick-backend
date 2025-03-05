import asyncio
from app.agents.graph import define_workflow, clean_agent
from app.agents.question_agent import QuestionAgent
import logging
import os
import pytest
from app.utils.logger import logger

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_workflow():
    # QuestionAgent 초기화
    question_agent = QuestionAgent()
    
    # 초기 상태로 대화 시작
    state = await question_agent.run({})
    print("\n=== 초기 응답 ===")
    print(state['response'])
    
    # 사용자 입력 시뮬레이션
    test_inputs = [
        "디지털 드로잉용 태블릿을 찾고 있어요",  # 목적
        "100만원 정도",  # 예산
        "애플",  # 선호 브랜드
        "펜 반응속도가 좋고 화면이 13인치 정도로 좋겠어요",  # 추가 요구사항
        "ok"
    ]
    
    for user_input in test_inputs:
        print("\n=== 사용자 입력 ===")
        print(user_input)
        
        state = await question_agent.run({
            "user_input": user_input,
            "conversation_history": state.get("conversation_history", []),
            "status": state.get("status"),
            "collected_info": state.get("collected_info", {}),
            "requirements": state.get("requirements"),
            "current_question": state.get("current_question"),
            "missing_info": state.get("missing_info", [])
        })
        
        print("\n=== 시스템 응답 ===")
        print(state['response'])
        
        # requirements가 생성되면 워크플로우 실행
        if state.get('status') == 'completed':
            print("\n=== 워크플로우 실행 ===")
            workflow = define_workflow()
            
            # 에이전트 상태 준비
            agent_states = await question_agent._prepare_agent_states(state['requirements'])
            
            # 초기 상태 설정
            initial_state = {
                "question": state["requirements"],
                "sub_questions": [],
                "youtube_agent_state": agent_states["youtube_agent_state"],
                "review_agent_state": agent_states["review_agent_state"],
                "spec_agent_state": agent_states["spec_agent_state"],
                "youtube_results": {},
                "review_results": {},
                "spec_results": {},
                "middleware_results": {},
                "final_report": ""
            }
            
            # 워크플로우 실행
            app = workflow.compile()
            try:
                result = await app.ainvoke(initial_state)
                print("\n=== 최종 추천 결과 ===")
                print("DEBUG - Result type:", type(result))  # result의 타입 확인
                print("DEBUG - Result value:", result)       # result의 값 확인
                
                if result is None:
                    print("워크플로우 실행 결과가 없습니다.")
                    clean_agent()
                else:
                    print(result.get("final_report", "추천 결과를 생성할 수 없습니다."))
                    clean_agent()
            except Exception as e:
                print(f"워크플로우 실행 중 오류 발생: {e}")
                print("현재 상태:", initial_state)
                clean_agent()
            break

if __name__ == "__main__":
    asyncio.run(test_workflow())