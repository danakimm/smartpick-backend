import os
from dotenv import load_dotenv
from typing import Literal, Dict, Any, List
from .base import BaseAgent
import json
from app.utils.logger import logger
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

class FeedbackAgent(BaseAgent):
    def __init__(self, name: str = "FeedbackAgent"):
        super().__init__(name)
        self.llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=os.getenv("OPENAI_API_KEY"))

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        피드백을 처리하고 적절한 응답을 반환
        """
        feedback = state.get("feedback", "")
        original_requirements = state.get("original_requirements", {})
        current_recommendations = state.get("current_recommendations", {})

        feedback_type = await self._classify_feedback(feedback)
        
        if feedback_type == "refinement":
            result = await self._refine_requirements(
                original_requirements,
                feedback,
                current_recommendations
            )
            return {
                "feedback_type": "refinement",
                "refined_requirements": result
            }
        else:
            response = await self._generate_direct_response(
                feedback,
                current_recommendations
            )
            return {
                "feedback_type": "question",
                "response": response
            }

    async def _classify_feedback(self, feedback: str) -> Literal["refinement", "question"]:
        prompt = f"""사용자의 피드백을 분석하여 피드백 유형을 분류해주세요.

피드백 유형:
1. refinement: 제품 추천 결과를 수정하거나 개선하기 위한 피드백
   예시: 
   - "이 가격대는 너무 비싸요"
   - "게임용으로는 부적합한 것 같아요"
   - "배터리 용량이 더 큰 제품으로 추천해주세요"

2. question: 제품이나 특정 기능에 대한 단순 질문
   예시:
   - "이 제품의 배터리 용량이 얼마인가요?"
   - "두 제품의 차이점이 뭔가요?"
   - "이 기능은 어떤 의미인가요?"

사용자 피드백: "{feedback}"

위 피드백이 어떤 유형인지 "refinement" 또는 "question" 중 하나로만 답변해주세요.
"""
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        feedback_type = response.content.strip().lower()
        
        if feedback_type not in ["refinement", "question"]:
            return "question"
            
        return feedback_type

    async def _refine_requirements(self, original_requirements: dict, feedback: str, current_recommendations: dict) -> dict:
        prompt = f"""기존 요구사항과 사용자의 새로운 피드백을 바탕으로 수정된 요구사항을 생성해주세요.

기존 요구사항:
{original_requirements}

현재 추천된 제품:
{current_recommendations}

사용자 피드백:
{feedback}

위 정보를 바탕으로 다음을 수행해주세요:
1. 사용자의 피드백에서 새로운 제약조건이나 선호도를 파악
2. 기존 요구사항에 새로운 조건을 자연스럽게 통합
3. 수정된 요구사항을 원본과 동일한 형식으로 출력

수정된 요구사항만을 JSON 형식으로 출력해주세요.
"""
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        try:
            refined_requirements = json.loads(response.content)
            return refined_requirements
        except json.JSONDecodeError:
            logger.error("Failed to parse refined requirements")
            return original_requirements

    async def _generate_direct_response(self, feedback: str, current_recommendations: dict) -> str:
        prompt = f"""사용자의 질문에 대해 현재 추천된 제품 정보를 바탕으로 답변을 생성해주세요.

현재 추천된 제품 정보:
{current_recommendations}

사용자 질문:
{feedback}

다음 가이드라인에 따라 답변을 생성해주세요:
1. 질문과 직접적으로 관련된 정보만 제공
2. 객관적이고 정확한 정보 위주로 답변
3. 모르는 정보에 대해서는 솔직히 모른다고 답변
4. 필요한 경우 제품 간 비교 정보 제공
5. 답변은 친절하고 이해하기 쉽게 작성

답변:"""
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content.strip() 