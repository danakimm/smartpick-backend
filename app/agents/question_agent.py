import logging
from langchain.chat_models import ChatAnthropic
from typing import Dict, Any
from .base import BaseAgent

logger = logging.getLogger("smartpick.agents.question_agent")

class QuestionAgent(BaseAgent):
    def __init__(self):
        super().__init__("question_agent")
        self.llm = ChatAnthropic()
        self.initial_question = "어떤 용도로 사용할 계획이야? 그림 그리기, 필기, 영상 감상, 게임, 문서 작업 등.." # 사용자의 요구사항을 정확히 파악하기 위해 사용자의 사용 목적을 물어봄 (첫번째 질문이 중요함)
        logger.debug("QuestionAgent initialized")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"Running QuestionAgent with state: {state}")
        if "conversation_history" not in state:
            # 초기 대화 시작
            return {
                "response": self.initial_question,
                "conversation_history": [],
                "requirements": None,
                "status": "collecting_input"
            }
        
        user_input = state.get("user_input", "")
        conversation_history = state.get("conversation_history", [])
        
        if state.get("status") == "collecting_input":
            # 사용자 입력을 구체적인 요구사항으로 변환 TODO - 구체적인 변환 규칙 정의 필요 / 사용자가 불분명할 답변을 한 경우에는 사용자가 필요한 스펙을 예상해줘 
            prompt = f""" 
            다음 사용자의 제품 설명을 구체적인 기술 스펙과 요구사항으로 변환해주세요:
            
            사용자 설명: {user_input}
            
            다음 형식으로 응답해주세요:
            1. 제품 카테고리:
            2. 핵심 요구사항:
            3. 기술 스펙:
            4. 예산 범위:
            """
            
            requirements = await self.llm.apredict(prompt)
            
            # 변환된 요구사항을 사용자에게 확인 요청
            confirmation_message = f"""
            제가 이해한 요구사항은 다음과 같습니다:
            
            {requirements}
            
            이러한 이해가 정확한가요? 맞다면 'OK'를 입력해주시고, 
            수정이 필요하다면 수정이 필요한 부분을 설명해주세요.
            """
            
            return {
                "response": confirmation_message,
                "conversation_history": conversation_history + [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": confirmation_message}
                ],
                "requirements": requirements,
                "status": "confirming_requirements"
            }
        
        elif state.get("status") == "confirming_requirements":
            if user_input.upper() == "OK": # TODO 다른 대답 예시 추가 필요 
                # 각 에이전트가 원하는 상태 구조로 변환하여 반환 (TODO - 구체적인 구조 정의 필요)
                # TODO 각 에이전트 input 방식으로 변환 필요  
                
                # 1. 스펙 분석 에이전트 질문 생성
                spec_prompt = f"""
                다음 요구사항을 바탕으로 제품의 기술 스펙을 구체적으로 나열해주세요:
                
                요구사항: {state.get('requirements')}
                """
                spec_agent_state = await self.llm.apredict(spec_prompt)

                # 2. 리뷰 분석 에이전트 질문 생성
                review_prompt = f"""
                다음 사용자 요구사항을 바탕으로 리뷰 수집을 위한 분석 구조를 생성해주세요:
                
                요구사항: {requirements}
                
                아래 JSON 형식으로 구성해주세요. 각 필드는 사용자의 요구사항에 맞게 구체적으로 채워주세요:
                {{
                    "사용_시나리오": {{
                        "주요_활동": "사용자의 주요 용도",
                        "사용_환경": ["주요 사용 장소나 환경들"],
                        "사용_시간": "예상 사용 시간대나 패턴",
                        "사용자_수준": "사용자의 전문성 수준"
                    }},
                    "주요_관심사": {{
                        "불편사항": ["사용자가 우려할 만한 잠재적 문제점들"],
                        "만족도_중요항목": ["사용자가 중요하게 생각할 특성들"]
                    }},
                    "감성적_요구사항": {{
                        "디자인_선호도": "선호하는 디자인 특성",
                        "가격대_심리": "가격에 대한 기대치"
                    }},
                    "사용자_우려사항": [
                        "구체적인 우려사항들"
                    ]
                }}

                요구사항에서 명시되지 않은 부분은 비워주세요. 
                """
                review_agent_state = await self.llm.apredict(review_prompt)

                # 3. 유튜브 에이전트 질문 생성
                youtube_prompt = f"""
                다음 요구사항을 바탕으로 유튜브 리뷰를 수집해주세요:
                
                요구사항: {state.get('requirements')}
                """
                youtube_agent_state = await self.llm.apredict(youtube_prompt)

                return {
                    "response": "요구사항 확인이 완료되었습니다.",
                    "conversation_history": conversation_history + [
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": "요구사항 확인이 완료되었습니다."}
                    ],
                    "requirements": state.get("requirements"),
                    "status": "completed",
                    "youtube_agent_state": youtube_agent_state,
                    "review_agent_state": review_agent_state,
                    "spec_agent_state": spec_agent_state
                }
            else:
                # 사용자가 수정을 요청한 경우, 다시 입력 수집 단계로 돌아감
                return {
                    "response": "수정사항을 반영하여 다시 제품에 대해 설명해주세요.",
                    "conversation_history": conversation_history + [
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": "수정사항을 반영하여 다시 제품에 대해 설명해주세요."}
                    ],
                    "requirements": None,
                    "status": "collecting_input"
                }