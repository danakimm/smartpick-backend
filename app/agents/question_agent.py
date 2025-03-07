import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from typing import Dict, Any, List
from .base import BaseAgent
import json
from app.utils.logger import logger

load_dotenv()

class QuestionAgent(BaseAgent):
    def __init__(self):
        super().__init__("question_agent")
        self.llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.prompts = {
            'initial': "안녕하세요! 어떤 태블릿을 찾고 계신지 편하게 말씀해 주세요 😊",
            'analyze_response': """당신은 사용자의 태블릿 구매 요구사항을 분석하는 AI 시스템입니다.
            아래 사용자의 응답을 분석하여 정확히 다음 JSON 형식으로만 응답해주세요.
            다른 어떤 설명이나 텍스트도 포함하지 마세요.
            
            사용자 응답: {user_input}
            
            {{
                "included_info": {{
                    "budget": {{
                        "included": false,
                        "value": ""
                    }},
                    "preferred_brand": {{
                        "included": false,
                        "value": ""
                    }},
                    "purpose": {{
                        "included": false,
                        "value": ""
                    }}
                }},
                "missing_info": ["budget", "preferred_brand", "purpose"]
            }}""",
            'follow_up': {
                "budget": "💰 예산은 어느 정도로 생각하고 계신가요?",
                "preferred_brand": "✨ 특별히 선호하시는 브랜드가 있으신가요?",
                "purpose": "📱 태블릿으로 주로 어떤 걸 하실 계획이신가요?"
            }
            ,
            'ask_additional': """✨ 기본적인 내용은 잘 알겠습니다!
                혹시 추가로 원하시는 기능이나 고려사항이 있으신가요?
                (예: 사용 환경, 만족도 중요 항목 등)

                💡 다음과 같은 내용을 참고해서 말씀해 주시면 더 자세한 추천이 가능합니다:
                • 주로 어디서 사용하실 계획인가요? (예: 카페, 이동 중, 실내 등)
                • 하루 평균 사용 시간은 어느 정도로 예상하시나요?
                • 특별히 신경 쓰시는 부분이 있나요? (예: 발열, 배터리 등)
                • 걱정되는 부분이 있다면 무엇인가요? (AS, 내구성 등)

                없으시다면 '없음'이라고 답변해 주시면 됩니다 😊"""
                ,
            'requirements': """
                당신은 태블릿 전문가입니다. 사용자의 태블릿 구매 요구사항을 분석해주세요.
                
                사용자 설명: {user_input}
                
                다음 형식으로 키워드 중심으로 요약해서 출력해주세요:
                
                1. 핵심 요구사항 (각 항목 50자 이내):
                - 사용자가 명시적으로 언급한 필수 기능과 선호사항
                - 사용 목적과 관련된 잠재적 요구사항
                - 사용자가 표현한 우려사항이나 기대

                2. 예산 범위 (각 항목 30자 이내):
                - 명시된 예산 정보
                - 예산 관련 우려사항이나 기대
                
                3. 기술 스펙 (각 항목 50자 이내):
                - 언급된 구체적인 하드웨어 요구사항
                - 사용 목적을 고려했을 때 필요한 최소 사양
                - 호환성이나 확장성 관련 요구사항
                
            """,
            'confirmation': """지금까지 말씀해 주신 내용을 정리해보았어요:

{requirements}

💡 요구사항이 맞으시다면
"ok", "네", "좋아요", "맞아요" 중에 편하게 답변해 주세요.

✍️ 수정이 필요하시다면
어떤 부분을 수정하면 좋을지 알려주세요.
다시 정리해드릴게요!""",
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
        positive_responses = ['ok', 'yes', '응', '네', '맞아', '좋습니다', '괜찮습니다']
        return response.lower().strip() in positive_responses

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if "conversation_history" not in state:
                return {
                    "response": self.prompts['initial'],
                    "conversation_history": [],
                    "requirements": None,
                    "collected_info": {},
                    "status": "collecting_initial"
                }
            
            user_input = state.get("user_input", "").strip()
            conversation_history = state.get("conversation_history", [])
            current_status = state.get("status", "collecting_initial")
            collected_info = state.get("collected_info", {})

            if current_status == "collecting_initial":
                analysis_prompt = self.prompts['analyze_response'].format(user_input=user_input)
                analysis_response = await self.llm.ainvoke(analysis_prompt)
                content = analysis_response.content if hasattr(analysis_response, 'content') else str(analysis_response)
                
                try:
                    content = content.strip()
                    content = content.replace('```json', '').replace('```', '').strip()
                    analysis = json.loads(content)
                    
                    # 수집된 정보 저장
                    for key, info in analysis['included_info'].items():
                        if info['included']:
                            collected_info[key] = info['value']

                    # 누락된 정보가 있는 경우
                    missing_info = analysis.get('missing_info', [])
                    if missing_info:
                        next_question = self.prompts['follow_up'][missing_info[0]]
                        return {
                            "response": next_question,
                            "conversation_history": conversation_history + [
                                {"role": "user", "content": user_input},
                                {"role": "assistant", "content": next_question}
                            ],
                            "collected_info": collected_info,
                            "missing_info": missing_info,
                            "current_question": missing_info[0],
                            "status": "collecting_missing"
                        }
                    else:
                        return await self._proceed_to_requirements(collected_info, conversation_history, user_input)

                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error: {e}")
                    return self._handle_error("응답 분석 중 오류가 발생했습니다.")

            elif current_status == "collecting_missing":
                # 현재 질문에 대한 답변 저장
                current_question = state.get("current_question")
                missing_info = state.get("missing_info", [])
                
                if current_question:
                    collected_info[current_question] = user_input
                    # 현재 질문을 missing_info에서 제거
                    missing_info = [info for info in missing_info if info != current_question]

                # 남은 질문이 있는지 확인
                if missing_info:
                    next_question = self.prompts['follow_up'][missing_info[0]]
                    return {
                        "response": next_question,
                        "conversation_history": conversation_history + [
                            {"role": "user", "content": user_input},
                            {"role": "assistant", "content": next_question}
                        ],
                        "collected_info": collected_info,
                        "missing_info": missing_info,
                        "current_question": missing_info[0],
                        "status": "collecting_missing"
                    }
                else:
                    # 모든 필수 정보가 수집되면 추가 요구사항 확인
                    return {
                        "response": self.prompts['ask_additional'],
                        "conversation_history": conversation_history + [
                            {"role": "user", "content": user_input},
                            {"role": "assistant", "content": self.prompts['ask_additional']}
                        ],
                        "collected_info": collected_info,
                        "status": "asking_additional"
                    }

            elif current_status == "asking_additional":
                if user_input.lower().strip() != "없음":
                    # 추가 요구사항을 collected_info에 저장
                    collected_info["additional_requirements"] = user_input
                
                # 요구사항 분석으로 진행
                return await self._proceed_to_requirements(collected_info, conversation_history, user_input)

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
                        "status": "requirements_collected"
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
        try:
            spec_agent_state = await self._prepare_spec_agent_state(requirements)
            review_agent_state = await self._prepare_review_agent_state(requirements)
            youtube_agent_state = await self._prepare_youtube_agent_state(requirements)

            return {
                "youtube_agent_state": youtube_agent_state,
                "review_agent_state": review_agent_state,
                "spec_agent_state": spec_agent_state
            }
        except Exception as e:
            logger.error(f"Error in _prepare_agent_states: {e}")
            # 에러 발생 시 빈 상태 반환하여 워크플로우가 계속 진행될 수 있도록 함
            return {
                "youtube_agent_state": {"youtube_analysis": {}},
                "review_agent_state": {"review_analysis": {}},
                "spec_agent_state": {"spec_analysis": {}}
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
                    "최소": {{"value": 최소 가격, "unit": "KRW"}},
                    "최대": {{"value": 최대 가격, "unit": "KRW"}}
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
        content = None  # content 변수를 미리 정의
        try:
            prompt = f"""
다음 정보를 바탕으로 태블릿 사용자의 요구사항을 분석하고, 리뷰 검색에 최적화된 형태로 정리해주세요.

분석 시 다음 원칙을 지켜주세요:
1. 사용자가 직접 언급한 내용은 그대로 포함
2. 검색 가능한 키워드 중심으로 구체적이고 간결하게 정리
3. 불확실한 내용은 추측하지 말고 생략
4. 각 항목은 최대 3단어 이내의 간결한 키워드로 표현

각 카테고리별 지침:

[주요_활동]
- 태블릿으로 실제 수행할 구체적인 작업이나 용도를 포함
- 예시: "영상 편집", "디지털 드로잉", "문서 작업", "게임", "영화 시청"
- 추상적 표현("엔터테인먼트") 대신 구체적 활동("넷플릭스 시청")으로 표현

[사용_환경]
- 태블릿을 주로 사용할 물리적 장소나 상황
- 예시: "실내", "카페", "이동 중", "침대에서", "야외"

[사용_시간]
- 일일 또는 주간 예상 사용 시간
- 예시: "하루 2시간", "5시간 이상", "간헐적 사용"

<<<<<<< HEAD
[사용자_수준]
- 사용자의 기술적 숙련도나 전문성
- 예시: "초보자", "전문가", "취미 작가", "학생"

[브랜드_선호도]
- 선호하는 특정 제조사나 브랜드 이름
- 예시: "애플", "삼성", "레노버"
=======
[브랜드_선호도]
- 선호하는 특정 제조사나 브랜드 이름
- 예시: "애플", "삼성"
>>>>>>> origin/main

[불편사항]
- 기존 제품 사용시 경험했거나 우려되는 문제점
- 예시: "발열", "배터리", "무거움", "지연시간"

[만족도_중요항목]
- 사용자가 중요하게 생각하는 기능이나 특성
- 예시: "펜 지원", "화면 크기", "프로세서 성능", "베젤 두께"

[디자인_선호도]
- 미적 선호도나 물리적 디자인 요소
- 예시: "얇은 디자인", "메탈 재질", "가벼운 무게"

[가격대_심리]
- 가격에 대한 태도나 예산 범위
- 예시: "가성비", "프리미엄", "상관없음"

[사용자_우려사항]
- 구매나 사용시 걱정되는 구체적 문제들
- 예시: "AS 품질", "내구성", "호환성", "업데이트 지원"

{requirements}

다음 JSON 형식으로만 응답해주세요 (다른 텍스트는 포함하지 마세요):
{{
    "사용_시나리오": {{
        "주요_활동": ["간결한 키워드1", "간결한 키워드2"],
        "사용_환경": ["간결한 키워드1", "간결한 키워드2"],
        "사용_시간": "간결한 표현",
<<<<<<< HEAD
        "사용자_수준": "간결한 표현"
=======
>>>>>>> origin/main
    }},
    "주요_관심사": {{
        "브랜드_선호도": ["브랜드1", "브랜드2"],
        "불편사항": ["간결한 키워드1", "간결한 키워드2"],
        "만족도_중요항목": ["간결한 키워드1", "간결한 키워드2"]
    }},
    "감성적_요구사항": {{
        "디자인_선호도": ["간결한 키워드1", "간결한 키워드2"],
        "가격대_심리": "간결한 표현"
    }},
    "사용자_우려사항": ["간결한 키워드1", "간결한 키워드2"],
<<<<<<< HEAD
    "검색_키워드_가중치": {{
        "높은_중요도": ["가장 중요한 키워드1", "가장 중요한 키워드2"],
        "중간_중요도": ["중요한 키워드1", "중요한 키워드2"],
        "낮은_중요도": ["부가적 키워드1", "부가적 키워드2"]
    }}
=======
>>>>>>> origin/main
}}"""
            
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
            if content:  # content가 존재할 때만 로그
                logger.error(f"Failed content: {content}")
            raise

    async def _prepare_youtube_agent_state(self, requirements: str) -> Dict[str, Any]:
        try:
            prompt = f"""
            다음 요구사항을 바탕으로 유튜브 리뷰 검색을 위한 정보를 생성해주세요:
            
            {requirements}
            
            다음 JSON 형식으로만 응답해주세요 (다른 텍스트는 포함하지 마세요):
            {{   "query": ["사용자의 요청사항을 자연어로 상세히 기술"],
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
        
    def _combine_collected_info(self, collected_info: Dict[str, str]) -> str:
        base_info = f"""
        사용 목적: {collected_info.get('purpose', '')}
        선호 브랜드: {collected_info.get('preferred_brand', '')}
        예산: {collected_info.get('budget', '')}
        """
        
        # 추가 요구사항이 있는 경우 포함
        if additional_req := collected_info.get('additional_requirements'):
            base_info += f"\n추가 요구사항: {additional_req}"
            
        return base_info
        
    async def _proceed_to_requirements(self, collected_info: Dict[str, str], 
                                     conversation_history: List[Dict[str, str]], 
                                     user_input: str) -> Dict[str, Any]:
        combined_input = self._combine_collected_info(collected_info)
        prompt = self.prompts['requirements'].format(user_input=combined_input)
        requirements_response = await self.llm.ainvoke(prompt)
        requirements = requirements_response.content if hasattr(requirements_response, 'content') else str(requirements_response)
        
        return {
            "response": self.prompts['confirmation'].format(requirements=requirements),
            "conversation_history": conversation_history + [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": self.prompts['confirmation'].format(requirements=requirements)}
            ],
            "requirements": requirements,
            "collected_info": collected_info,
            "status": "confirming_requirements"
        }
        

