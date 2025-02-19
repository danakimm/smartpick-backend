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
# from .youtube_agent import YouTubeAgent
# from .middleware_agent import MiddlewareAgent
# from .report_agent import ReportAgent

question_agent = QuestionAgent()
review_agent = ProductRecommender()
# spec_agent = SpecAgent()
# youtube_agent = YouTubeAgent()
# middleware_agent = MiddlewareAgent()
# report_agent = ReportAgent()

logger = logging.getLogger("smartpick.agents.graph")

def define_workflow():
    logger.debug("Defining workflow")
    # 워크플로우 그래프 정의
    workflow = Graph()

    # 노드 정의
    @workflow.node()
    async def question_decomposition(state: AgentState) -> AgentState:
        sub_questions = await question_agent.run(state)
        return {"sub_questions": sub_questions}

    @workflow.node()
    async def parallel_analysis(state: AgentState) -> Dict:
        youtube_task = youtube_agent.analyze(state["youtube_agent_state"])
        review_task = review_agent.run(state["review_agent_state"])
        spec_task = spec_agent.analyze(state["spec_agent_state"]))
        
        youtube_results, review_results, spec_results = await asyncio.gather(
            youtube_task,
            review_task,
            spec_task
        )
        
        results = {
            "youtube_results": youtube_results,
            "review_results": review_results,
            "spec_results": spec_results
        }
        return results

    @workflow.node()
    async def middleware_processing(state: AgentState) -> Dict:
        combined_results = {**state["youtube_results"], 
                          **state["review_results"], 
                          **state["spec_results"]}
        processed = await middleware_agent.process(combined_results)
        return {"middleware_results": processed}

    @workflow.node()
    async def report_generation(state: AgentState) -> Dict:
        final_report = await report_agent.generate(state["middleware_results"])
        return {"final_report": final_report}

    # 엣지 정의
    workflow.set_entry_point("question_decomposition")
    workflow.add_edge("question_decomposition", "parallel_analysis")
    workflow.add_edge("parallel_analysis", "middleware_processing")
    workflow.add_edge("middleware_processing", "report_generation")

    return workflow