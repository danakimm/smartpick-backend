import pytest
from app.agents.graph import create_workflow

async def test_basic_workflow():
    workflow = create_workflow()
    
    initial_state = {
        "question": "LG gram 17인치 노트북의 배터리 수명과 성능은 어떤가요?",
        "sub_questions": [],
        "youtube_analysis": {},
        "review_analysis": {},
        "spec_analysis": {},
        "final_report": ""
    }
    
    final_state = await workflow.run(initial_state)
    
    assert "sub_questions" in final_state
    assert len(final_state["sub_questions"]) > 0 