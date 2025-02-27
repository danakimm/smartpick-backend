from langgraph.graph import Graph
from typing import Dict, TypedDict, Annotated, Sequence
import operator
import logging
import asyncio

class AgentState(TypedDict):
    question: str
    sub_questions: list[str]
    youtube_results: dict
    review_results: dict
    spec_results: dict
    middleware_results: dict
    final_report: str

# 에이전트 인스턴스 가져오기
from .question_agent import QuestionAgent
from .review_agent import ProductRecommender
# from .spec_agent import SpecAgent
from .youtube_agent import YouTubeAgent
# from .middleware_agent import MiddlewareAgent
# from .report_agent import ReportAgent

question_agent = QuestionAgent()
review_agent = ProductRecommender()
# spec_agent = SpecAgent()
youtube_agent = YouTubeAgent()
# middleware_agent = MiddlewareAgent()
# report_agent = ReportAgent()

logger = logging.getLogger("smartpick.agents.graph")

def define_workflow():
    logger.debug("Defining workflow")
    workflow = Graph()

    async def parallel_analysis(state: AgentState) -> Dict:
        #
        #youtube_results=await youtube_agent.run(state["youtube_agent_state"]["youtube_analysis"]),
        #print("youtube_results", youtube_results)
        #review_results=await review_agent.run(state["review_agent_state"]["review_analysis"]),    
        #print("review_results", review_results)
        spec_results=[]
        # 병렬로 실행하기 위해 asyncio.gather 사용
        youtube_results, review_results,spec_results = await asyncio.gather(
            # YouTube 분석은 아직 구현되지 않음
            # 임시 placeholder
            # Review 분석 실행
            youtube_agent.run(state["youtube_agent_state"]["youtube_analysis"]),
            review_agent.run(state["review_agent_state"]["review_analysis"]),
            asyncio.sleep(0)

        )
        
        logger.debug(f"Review results: {review_results}")  # 로깅 추가
        
        results = {
            "youtube_results": youtube_results or {},
            "review_results": review_results,
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

    # 노드 추가
    workflow.add_node("parallel_analysis", parallel_analysis)
    workflow.add_node("middleware_processing", middleware_processing)
    workflow.add_node("report_generation", report_generation)

    # 엣지 정의
    workflow.set_entry_point("parallel_analysis")
    workflow.add_edge("parallel_analysis", "middleware_processing")
    workflow.add_edge("middleware_processing", "report_generation")

    # 최종 노드 설정
    workflow.set_finish_point("report_generation")

    return workflow

def clean_agent():
    youtube_agent.clean()
