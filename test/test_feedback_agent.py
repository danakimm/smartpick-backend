import pytest
import pytest_asyncio
from app.agents.feedback_agent import FeedbackAgent
from app.agents.graph import define_workflow


@pytest.fixture
def feedback_agent():
    return FeedbackAgent()

@pytest.fixture
def sample_state():
    return {
        "question": "게임용 태블릿 추천해주세요. 예산은 200만원 이내입니다.",
        "middleware_results": {
            "recommendations": "1. 레노버 리전 5 Pro\n2. ASUS ROG Strix G15",
            "analysis": {
                "review": {
                    "pros": ["성능이 좋음", "가성비 우수"],
                    "cons": ["배터리 수명이 짧음"]
                }
            }
        }
    }

@pytest.mark.asyncio
async def test_feedback_refinement(feedback_agent, sample_state):
    """요구사항 수정 피드백 테스트"""
    feedback = "배터리 수명이 더 긴 제품으로 추천해주세요"
    
    result = await feedback_agent.run({
        "feedback": feedback,
        "original_requirements": sample_state["question"],
        "current_recommendations": sample_state["middleware_results"]
    })
    
    assert result["feedback_type"] == "refinement"
    assert "refined_requirements" in result
    assert "배터리" in str(result["refined_requirements"])

@pytest.mark.asyncio
async def test_feedback_question(feedback_agent, sample_state):
    """단순 질문 피드백 테스트"""
    feedback = "레노버 리전 5 Pro의 배터리 용량이 얼마인가요?"
    
    result = await feedback_agent.run({
        "feedback": feedback,
        "original_requirements": sample_state["question"],
        "current_recommendations": sample_state["middleware_results"]
    })
    
    assert result["feedback_type"] == "question"
    assert "response" in result
    assert len(result["response"]) > 0

@pytest.mark.asyncio
async def test_feedback_workflow_integration():
    """전체 워크플로우 통합 테스트"""
    workflow = define_workflow()
    
    initial_state = {
        "question": "게임용 노트북 추천해주세요. 예산은 200만원 이내입니다.",
        "sub_questions": [],
        "youtube_results": {},
        "review_results": {
            "recommendations": "1. 레노버 리전 5 Pro\n2. ASUS ROG Strix G15"
        },
        "spec_results": {},
        "middleware_results": {
            "recommendations": "1. 레노버 리전 5 Pro\n2. ASUS ROG Strix G15",
            "analysis": {"review": {"pros": ["성능이 좋음"], "cons": ["배터리 수명이 짧음"]}}
        },
        "final_report": "추천 제품:\n1. 레노버 리전 5 Pro\n2. ASUS ROG Strix G15",
        "feedback": "배터리 수명이 더 긴 제품으로 추천해주세요",
        "feedback_type": None,
        "feedback_response": ""
    }
    
    final_state = await workflow.invoke(initial_state)
    
    # 피드백 처리 결과 검증
    assert "feedback_type" in final_state
    if final_state["feedback_type"] == "refinement":
        assert "refined_requirements" in final_state
        assert final_state["middleware_results"] != initial_state["middleware_results"]
    else:
        assert "feedback_response" in final_state
        assert len(final_state["feedback_response"]) > 0

@pytest.mark.asyncio
async def test_websocket_feedback_flow():
    """WebSocket 피드백 처리 테스트"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    with client.websocket_connect("/ws/test_client") as websocket:
        # 초기 메시지 수신
        response = websocket.receive_json()
        assert response["type"] == "message"
        
        # 피드백 전송
        websocket.send_json({
            "type": "feedback",
            "content": "배터리 수명이 더 긴 제품으로 추천해주세요"
        })
        
        # 피드백 응답 수신
        response = websocket.receive_json()
        assert response["type"] == "feedback_response"
        assert "response" in response["data"]
        assert "analysis" in response["data"] 