from langgraph.graph import Graph, END
from typing import Dict, TypedDict, Annotated, Sequence, Any, List
import operator
import asyncio
from app.utils.logger import logger

class AgentState(TypedDict):
    question: str
    review_agent_state: dict  # review_agent 상태 정보
    spec_agent_state: dict  # spec_agent 상태 정보
    youtube_agent_state: dict  # youtube_agent 상태 정보
    youtube_results: dict 
    review_results: dict
    spec_results: dict
    middleware_results: dict
    report_results: str
    feedback: str  # 사용자 피드백
    feedback_type: str  # 'refinement' 또는 'question'
    refined_requirements: dict  # 피드백 기반 수정된 요구사항
    feedback_response: str  # 피드백에 대한 응답

# 에이전트 인스턴스 가져오기
from .question_agent import QuestionAgent
from .review_agent import ProductRecommender
from .spec_agent import SpecRecommender
from .youtube_agent import YouTubeAgent
from .middleware_agent import MiddlewareAgent
from .report_agent import ReportAgent
from .feedback_agent import FeedbackAgent

question_agent = QuestionAgent()
review_agent = ProductRecommender()
spec_agent = SpecRecommender()
youtube_agent = YouTubeAgent()
middleware_agent = MiddlewareAgent(review_agent=review_agent, spec_agent=spec_agent) #, youtube_agent=youtube_agent)
report_agent = ReportAgent()
feedback_agent = FeedbackAgent()

async def parallel_analysis(state: AgentState) -> Dict:
    try:
        youtube_results, review_results, spec_results = await asyncio.gather(
<<<<<<< HEAD
            youtube_agent.run(state["youtube_agent_state"]['youtube_analysis']), #asyncio.sleep(0)
=======
            asyncio.sleep(0),#youtube_agent.run(state["youtube_agent_state"]['youtube_analysis']),
>>>>>>> origin/main
            review_agent.run(state["review_agent_state"]['review_analysis']),
            spec_agent.run(state["spec_agent_state"]['spec_analysis']),
            return_exceptions=True
        )
<<<<<<< HEAD
        #youtube_results["youtube"]["raw_meta_data"]["자막"]="자막 생략"
=======

>>>>>>> origin/main
        results = {
            **state,
            "youtube_results": {} if isinstance(youtube_results, Exception) else youtube_results,
            "review_results": {} if isinstance(review_results, Exception) else review_results,
            "spec_results": {} if isinstance(spec_results, Exception) else spec_results,
        }
        
        logger.debug(f'Parallel analysis review_results: {review_results}')
        logger.debug(f'Parallel analysis spec_results: {spec_results}')
        return results
    except Exception as e:
        logger.error(f"Error in parallel analysis: {e}")
        return {**state, "error": "병렬 분석 중 오류 발생"}

async def middleware_processing(state: AgentState) -> Dict:
    try:
        result = await middleware_agent.run(state)
        return {
            **state,  # 기존 state 유지
            "middleware_results": result
        }
    except Exception as e:
        logger.error(f"Error in middleware processing: {e}")
        return {**state, "error": "미들웨어 처리 중 오류 발생"}

async def report_generation(state: AgentState) -> Dict:
    logger.debug(f"Report input state: {state}")
<<<<<<< HEAD
   # try:
    report_result = await report_agent.run(state['middleware_results'])
    logger.debug(f"Final result: {report_result}")
    return {
        **state,  # 기존 state 유지
        "report_results": report_result
    }
#except Exception as e:
    #    logger.error(f"Error in report generation: {e}")
    #    return {**state, "error": "리포트 생성 중 오류 발생"}
=======
    try:
        report_result = await report_agent.run(state['middleware_results'])
        logger.debug(f"Final result: {report_result}")
        return {
            **state,  # 기존 state 유지
            "report_results": report_result
        }
    except Exception as e:
        logger.error(f"Error in report generation: {e}")
        return {**state, "error": "리포트 생성 중 오류 발생"}
>>>>>>> origin/main

async def handle_feedback(state: AgentState) -> Dict:
    logger.debug(f"Processing feedback: {state['feedback']}")

    feedback_result = await feedback_agent.run({
        "feedback": state["feedback"],
        "original_requirements": state["question"],
        "current_recommendations": state["middleware_results"]
    })

    feedback_type = feedback_result["feedback_type"]

    if feedback_type == "refinement":
        combined_requirements = f"""
        기존 요구사항: {state['question']}
        추가/수정된 요구사항: {feedback_result['refined_requirements']}
        """

        new_agent_states = await question_agent._prepare_agent_states(combined_requirements)

        return {
            **state,  # 기존 state 유지
            "question": combined_requirements,
            "feedback_type": feedback_type,
            "refined_requirements": feedback_result["refined_requirements"],
            "youtube_agent_state": new_agent_states["youtube_agent_state"],
            "review_agent_state": new_agent_states["review_agent_state"],
            "spec_agent_state": new_agent_states["spec_agent_state"]
        }
    else:
        return {
            **state,  # 기존 state 유지
            "feedback_response": feedback_result["response"],
            "feedback_type": feedback_type
        }

def define_initial_workflow():
    """초기 분석을 위한 워크플로우 정의"""
    logger.debug("Defining initial workflow")
    workflow = Graph()

    # 노드 추가
    workflow.add_node("parallel_analysis", parallel_analysis)
    workflow.add_node("middleware_processing", middleware_processing)
    workflow.add_node("report_generation", report_generation)

    # 엣지 정의
    workflow.set_entry_point("parallel_analysis")
    workflow.add_edge("parallel_analysis", "middleware_processing")
    workflow.add_edge("middleware_processing", "report_generation")
    workflow.add_edge("report_generation", END)

    return workflow

def define_feedback_workflow():
    """피드백 처리를 위한 워크플로우 정의"""
    logger.debug("Defining feedback workflow")
    workflow = Graph()

    # 노드 추가 (동일한 외부 함수 참조)
    workflow.add_node("handle_feedback", handle_feedback)
    workflow.add_node("parallel_analysis", parallel_analysis)
    workflow.add_node("middleware_processing", middleware_processing)
    workflow.add_node("report_generation", report_generation)

    # 피드백 워크플로우 엣지 정의
    workflow.set_entry_point("handle_feedback")
    
    # 피드백 타입에 따른 조건부 엣지
    workflow.add_conditional_edges(
        "handle_feedback",
        path=lambda x: x["feedback_type"] == "refinement",
        path_map={
            True: "parallel_analysis",  # 재분석 필요시
            False: END  # 단순 질문시
        }
    )

    # refinement인 경우의 추가 흐름
    workflow.add_edge("parallel_analysis", "middleware_processing")
    workflow.add_edge("middleware_processing", "report_generation")
    workflow.add_edge("report_generation", END)

    return workflow
<<<<<<< HEAD


=======
>>>>>>> origin/main
