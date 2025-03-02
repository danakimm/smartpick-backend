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
async def test_feedback_workflow_branching():
    """워크플로우 그래프 분기 테스트"""
    workflow = define_workflow()
    
    # 그래프 컴파일
    compiled_workflow = workflow.compile()
    
    # 1. 요구사항 수정(refinement) 케이스 테스트
    refinement_state = {
        "question": "게임용 노트북 추천해주세요. 예산은 200만원 이내입니다.",
        "sub_questions": [],
        "youtube_agent_state": {},
        "review_agent_state": {"review_analysis": {"query": "게임용 노트북 리뷰"}},
        "spec_agent_state": {},
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
        "feedback_type": "",
        "refined_requirements": {},
        "feedback_response": ""
    }
    
    # 컴파일된 워크플로우 실행
    refinement_result = await compiled_workflow.ainvoke(refinement_state)
    print(refinement_result)
    
    # 요구사항 수정 분기 검증
    assert refinement_result["feedback_type"] == "refinement"
    assert "refined_requirements" in refinement_result
    # parallel_analysis가 다시 실행되었는지 확인 (review_results가 업데이트되었는지)
    assert refinement_result["review_results"] != refinement_state["review_results"]
    
    # 2. 단순 질문(question) 케이스 테스트
    question_state = {
        "question": "게임용 노트북 추천해주세요. 예산은 200만원 이내입니다.",
        "sub_questions": [],
        "youtube_agent_state": {},
        "review_agent_state": {"review_analysis": {"query": "게임용 노트북 리뷰"}},
        "spec_agent_state": {},
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
        "feedback": "레노버 리전 5 Pro의 배터리 용량이 얼마인가요?",
        "feedback_type": "",
        "refined_requirements": {},
        "feedback_response": ""
    }
    
    # 컴파일된 워크플로우 실행
    question_result = await compiled_workflow.ainvoke(question_state)
    
    # 단순 질문 분기 검증
    assert question_result["feedback_type"] == "question"
    assert "feedback_response" in question_result
    assert len(question_result["feedback_response"]) > 0
    # parallel_analysis가 다시 실행되지 않았는지 확인 (review_results가 그대로인지)
    assert question_result["review_results"] == question_state["review_results"]

