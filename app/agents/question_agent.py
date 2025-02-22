import os
from dotenv import load_dotenv
# from langchain_anthropic import ChatAnthropic 
from langchain_openai import ChatOpenAI
from typing import Dict, Any
from .base import BaseAgent
import logging
import json

logger = logging.getLogger("smartpick.agents.question_agent")

load_dotenv()

class QuestionAgent(BaseAgent):
    def __init__(self):
        super().__init__("question_agent")
        # self.llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=os.getenv("OPENAI_API_KEY"))
        self.prompts = {
            'initial': "태블릿을 주로 어떤 용도로 사용하시나요? ",
            'requirements': """
                당신은 태블릿 전문가입니다. 사용자의 태블릿 구매 요구사항을 분석해주세요.
                
                사용자 설명: {user_input}
                
                다음 형식으로 응답해주세요:
                
                1. 핵심 요구사항:
                - 사용자가 명시적으로 언급한 필수 기능과 선호사항
                - 사용 목적과 관련된 잠재적 요구사항
                - 사용자가 표현한 우려사항이나 기대
                
                2. 기술 스펙:
                - 언급된 구체적인 하드웨어 요구사항
                - 사용 목적을 고려했을 때 필요한 최소 사양
                - 호환성이나 확장성 관련 요구사항
                
                3. 예산 범위:
                - 명시된 예산 정보
                - 예산 관련 우려사항이나 기대
            """,
            'confirmation': """
                제가 이해한 요구사항은 다음과 같습니다:
                
                {requirements}
                
                이러한 이해가 정확한가요? 맞다면 'OK'나 '네', '맞습니다' 등을 입력해주시고, 
                수정이 필요하다면 수정이 필요한 부분을 설명해주세요.
            """,
            'update_requirements': """
                기존 요구사항: {previous_requirements}
                사용자 피드백: {user_feedback}
                
                다음 형식으로 응답해주세요:
                1. 제품 카테고리:
                2. 핵심 요구사항:
                3. 기술 스펙:
                4. 예산 범위:
            """
        }
        logger.debug("QuestionAgent initialized")

    def _is_confirmation_response(self, response: str) -> bool:
        positive_responses = ['ok', 'yes', '응', '네', '맞습니다', '좋습니다', '괜찮습니다']
        return response.lower().strip() in positive_responses

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.debug(f"Running QuestionAgent with state: {state}")

            if "conversation_history" not in state:
                return {
                    "response": self.prompts['initial'],
                    "conversation_history": [],
                    "requirements": None,
                    "status": "collecting_input"
                }
            
            user_input = state.get("user_input", "").lower()
            conversation_history = state.get("conversation_history", [])
            current_status = state.get("status", "collecting_input")
            
            if current_status == "collecting_input":
                prompt = self.prompts['requirements'].format(user_input=user_input)
                requirements_response = await self.llm.ainvoke(prompt)
                requirements = requirements_response.content if hasattr(requirements_response, 'content') else str(requirements_response)
                
                return {
                    "response": self.prompts['confirmation'].format(requirements=requirements),
                    "conversation_history": conversation_history + [
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": self.prompts['confirmation'].format(requirements=requirements)}
                    ],
                    "requirements": requirements,
                    "status": "confirming_requirements"
                }
            
            elif current_status == "confirming_requirements":
                # 사용자 확인 응답 체크
                if self._is_confirmation_response(user_input):
                    # 다음 단계로 진행
                    return {
                        "response": state.get("requirements"),
                        "conversation_history": conversation_history + [
                            {"role": "user", "content": user_input}
                        ],
                        "requirements": state.get("requirements"),
                        "status": "completed"
                    }
                else:
                    # 수정 요청 처리
                    previous_requirements = state.get("requirements", "")
                    prompt = self.prompts['update_requirements'].format(
                        previous_requirements=previous_requirements,
                        user_feedback=user_input
                    )
                    updated_requirements_response = await self.llm.ainvoke(prompt)
                    updated_requirements = updated_requirements_response.content if hasattr(updated_requirements_response, 'content') else str(updated_requirements_response)
                    
                    return {
                        "response": self.prompts['confirmation'].format(requirements=updated_requirements),
                        "conversation_history": conversation_history + [
                            {"role": "user", "content": user_input},
                            {"role": "assistant", "content": self.prompts['confirmation'].format(requirements=updated_requirements)}
                        ],
                        "requirements": updated_requirements,
                        "status": "confirming_requirements"
                    }
        
        except Exception as e:
            logger.error(f"Error in run: {e}")
            return self._handle_error(f"오류가 발생했습니다: {e}")
        
    def _handle_error(self, message: str) -> Dict[str, Any]:
        return {
            "response": message,
            "status": "error",
            "conversation_history": [],
            "requirements": None
        }
    
    async def _prepare_agent_states(self, requirements: str) -> Dict[str, Any]:
        spec_agent_state = await self._prepare_spec_agent_state(requirements)
        review_agent_state = await self._prepare_review_agent_state(requirements)
        youtube_agent_state = await self._prepare_youtube_agent_state(requirements)
        
        return {
            "youtube_agent_state": youtube_agent_state,
            "review_agent_state": review_agent_state,
            "spec_agent_state": spec_agent_state
        }
    
    async def _prepare_spec_agent_state(self, requirements: str) -> Dict[str, Any]:
        try:
            prompt = f"""
            다음 요구사항을 바탕으로 제품의 기술 스펙을 구체적으로 분석해주세요:
            
            {requirements}
            
            다음 JSON 형식으로만 응답해주세요 (다른 텍스트는 포함하지 마세요):
            {{
                "필수_스펙": {{
                    "성능": ["필수적인 성능 요구사항들"],
                    "하드웨어": ["필수적인 하드웨어 요구사항들"],
                    "기능": ["필수적인 기능 요구사항들"]
                }},
                "선호_스펙": {{
                    "성능": ["선호하는 성능 특성들"],
                    "하드웨어": ["선호하는 하드웨어 특성들"],
                    "기능": ["선호하는 기능들"]
                }},
                "제외_스펙": ["피해야 할 특성들"],
                "가격_범위": {{
                    "최소": "최소 가격",
                    "최대": "최대 가격"
                }}
            }}
            """
            
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 디버깅을 위한 로그
            logger.debug(f"LLM Response content: {content}")
            
            # JSON 문자열 정제
            content = content.strip()
            if content.startswith("```json"):
                content = content.split("```json")[1]
            if content.startswith("```"):
                content = content.split("```")[1]
            content = content.strip()
            
            parsed_content = json.loads(content)
            return {"spec_analysis": parsed_content}
        except Exception as e:
            logger.error(f"Error in _prepare_spec_agent_state: {e}")
            logger.error(f"Failed content: {content}")
            raise

    async def _prepare_review_agent_state(self, requirements: str) -> Dict[str, Any]:
        try:
            prompt = f"""
            다음 요구사항을 바탕으로 리뷰 분석을 위한 구조를 생성해주세요:
            
            {requirements}
            
            다음 JSON 형식으로만 응답해주세요 (다른 텍스트는 포함하지 마세요):
            {{
                "분석_관점": {{
                    "사용성": ["확인해야 할 사용성 측면들"],
                    "내구성": ["확인해야 할 내구성 측면들"],
                    "가성비": ["확인해야 할 가격 대비 가치 측면들"]
                }},
                "주요_검토사항": ["중점적으로 살펴봐야 할 사항들"],
                "사용자_시나리오": ["검토해야 할 실제 사용 상황들"],
                "비교_항목": ["경쟁 제품과 비교해야 할 항목들"]
            }}
            """
            
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # JSON 문자열 정제
            content = content.strip()
            if content.startswith("```json"):
                content = content.split("```json")[1]
            if content.startswith("```"):
                content = content.split("```")[1]
            content = content.strip()
            
            parsed_content = json.loads(content)
            return {"review_analysis": parsed_content}
        except Exception as e:
            logger.error(f"Error in _prepare_review_agent_state: {e}")
            logger.error(f"Failed content: {content}")
            raise

    async def _prepare_youtube_agent_state(self, requirements: str) -> Dict[str, Any]:
        try:
            prompt = f"""
            다음 요구사항을 바탕으로 유튜브 리뷰 검색을 위한 정보를 생성해주세요:
            
            {requirements}
            
            다음 JSON 형식으로만 응답해주세요 (다른 텍스트는 포함하지 마세요):
            {{
                "검색_키워드": {{
                    "필수_포함": ["반드시 포함되어야 할 키워드들"],
                    "선택_포함": ["포함되면 좋을 키워드들"],
                    "제외": ["제외해야 할 키워드들"]
                }},
                "리뷰_유형": ["찾아야 할 리뷰 영상 유형들"],
                "중점_확인사항": ["영상에서 중점적으로 확인해야 할 내용들"],
                "최소_조회수": "필요한 최소 조회수",
                "업로드_기간": "검색할 기간 범위"
            }}
            """
            
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # JSON 문자열 정제
            content = content.strip()
            if content.startswith("```json"):
                content = content.split("```json")[1]
            if content.startswith("```"):
                content = content.split("```")[1]
            content = content.strip()
            
            parsed_content = json.loads(content)
            return {"youtube_analysis": parsed_content}
        except Exception as e:
            logger.error(f"Error in _prepare_youtube_agent_state: {e}")
            logger.error(f"Failed content: {content}")
            raise
        

