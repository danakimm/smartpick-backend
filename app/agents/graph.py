from langgraph.graph import Graph
from typing import Dict, TypedDict, Annotated, Sequence
import operator

class AgentState(TypedDict):
    question: str
    sub_questions: list[str]
    youtube_results: dict
    review_results: dict
    spec_results: dict
    middleware_results: dict
    final_report: str

def define_workflow():
    # 워크플로우 그래프 정의
    workflow = Graph()

    # 노드 정의
    @workflow.node()
    async def question_decomposition(state: AgentState) -> AgentState:
        sub_questions = await claude_agent.decompose_question(state["question"])
        return {"sub_questions": sub_questions}

    @workflow.node()
    async def parallel_analysis(state: AgentState) -> Dict:
        results = {
            "youtube_results": await youtube_agent.analyze(state["sub_questions"]),
            "review_results": await review_agent.analyze(state["sub_questions"]),
            "spec_results": await spec_agent.analyze(state["sub_questions"])
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