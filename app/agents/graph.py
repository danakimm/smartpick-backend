from langgraph.graph import Graph, END
from typing import Dict, TypedDict, Annotated, Sequence
import operator
import logging
import asyncio

class AgentState(TypedDict):
    question: str
    sub_questions: list[str]
    review_agent_state: dict  # review_agent 상태 정보
    spec_agent_state: dict  # spec_agent 상태 정보
    youtube_agent_state: dict  # youtube_agent 상태 정보
    youtube_results: dict
    review_results: dict
    spec_results: dict
    middleware_results: dict
    final_report: str
    feedback: str  # 사용자 피드백
    feedback_type: str  # 'refinement' 또는 'question'
    refined_requirements: dict  # 피드백 기반 수정된 요구사항
    feedback_response: str  # 피드백에 대한 응답

# 에이전트 인스턴스 가져오기
from .question_agent import QuestionAgent
from .review_agent import ProductRecommender
from .spec_agent import SpecRecommender
from .youtube_agent import YouTubeAgent
# from .middleware_agent import MiddlewareAgent
# from .report_agent import ReportAgent
from .feedback_agent import FeedbackAgent

question_agent = QuestionAgent()
review_agent = ProductRecommender()
spec_agent = SpecRecommender()
youtube_agent = YouTubeAgent()
# middleware_agent = MiddlewareAgent()
# report_agent = ReportAgent()
feedback_agent = FeedbackAgent()

logger = logging.getLogger("smartpick.agents.graph")

def define_workflow():
    logger.debug("Defining workflow")
    workflow = Graph()

    async def parallel_analysis(state: AgentState) -> Dict:
        # 병렬로 실행하기 위해 asyncio.gather 사용
        youtube_results, review_results, spec_results = await asyncio.gather(
            # Review 분석 실행
            youtube_agent.run(state["youtube_agent_state"]["youtube_analysis"]),
            review_agent.run(state["review_agent_state"]["review_analysis"]),
            spec_agent.run(state["spec_agent_state"]["spec_analysis"]),
        )
        
        #logger.debug(f"Review results: {review_results}")  # 로깅 추가
        logger.debug(f"Spec results: {spec_results}")
        
        results = {
            "youtube_results": youtube_results or {},
            "review_results": review_results or {},
            "spec_results": spec_results or {},
        }
        logger.debug(f"Parallel analysis results: {results}")  # 로깅 추가
        return results

    async def middleware_processing(state: AgentState) -> Dict:
        logger.debug(f"Middleware input state: {state}")  # 입력 상태 로깅
        
        try:
            middleware_results = {
                "recommendations": state["review_results"].get("recommendations", ""),
                "analysis": {
                    "youtube": state.get("youtube_results", {}),
                    "review": state.get("review_results", {}),
                    "spec": state.get("spec_results", {})
                }
            }
            logger.debug(f"Middleware results: {middleware_results}")  # 결과 로깅
            return {"middleware_results": middleware_results}
            
        except Exception as e:
            logger.error(f"Error in middleware processing: {e}")
            return {
                "middleware_results": {
                    "recommendations": "미들웨어 처리 중 오류가 발생했습니다.",
                    "analysis": {}
                }
            }

    async def report_generation(state: AgentState) -> Dict:
        logger.debug(f"Report input state: {state}")  # 입력 상태 로깅
        
        try:
            final_result = {
                "final_report": state["middleware_results"]["recommendations"],
                "analysis": state["middleware_results"]["analysis"]
            }
            logger.debug(f"Final result: {final_result}")  # 결과 로깅
            return final_result
            
        except Exception as e:
            logger.error(f"Error in report generation: {e}")
            return {
                "final_report": "최종 보고서 생성 중 오류가 발생했습니다.",
                "analysis": {}
            }

    async def handle_feedback(state: AgentState) -> Dict:
        logger.debug(f"Processing feedback: {state['feedback']}")
        
        feedback_result = await feedback_agent.run({
            "feedback": state["feedback"],
            "original_requirements": state["question"],
            "current_recommendations": state["middleware_results"]
        })
        
        feedback_type = feedback_result["feedback_type"]
        
        if feedback_type == "refinement":
            # 기존 분석 결과와 새로운 요구사항으로 재분석 실행
            new_state = {
                **state,
                "question": feedback_result["refined_requirements"],
                "feedback_type": feedback_type,  # feedback_type 추가
                "refined_requirements": feedback_result["refined_requirements"]  # refined_requirements 추가
            }
            result = await parallel_analysis(new_state)
            result["feedback_type"] = feedback_type  # 결과에도 feedback_type 추가
            return result
        else:
            # 단순 질문에 대한 직접 응답
            return {
                "feedback_response": feedback_result["response"],
                "feedback_type": feedback_type  # feedback_type 추가
            }

    # 노드 추가
    workflow.add_node("parallel_analysis", parallel_analysis)
    workflow.add_node("middleware_processing", middleware_processing)
    workflow.add_node("report_generation", report_generation)
    workflow.add_node("handle_feedback", handle_feedback)

    # 엣지 정의
    workflow.set_entry_point("parallel_analysis")
    workflow.add_edge("parallel_analysis", "middleware_processing")
    workflow.add_edge("middleware_processing", "report_generation")
    

    workflow.add_conditional_edges(
        "report_generation",
        path=lambda x: "feedback" in x,
        path_map={
            True: "handle_feedback",  # 피드백이 있으면 피드백 처리로
            False: END  # None 대신 END 사용
        }
    )
    
    # 피드백 처리 후의 조건부 엣지
    workflow.add_conditional_edges(
        "handle_feedback",
        path=lambda x: x["feedback_type"] == "refinement",
        path_map={
            True: "parallel_analysis",  # 재분석 필요시
            False: "report_generation"  # 단순 질문시
        }
    )

    return workflow

def clean_agent():
    youtube_agent.clean()
