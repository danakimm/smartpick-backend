import asyncio
import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

logger = logging.getLogger("smartpick.agents.middleware_agent")
load_dotenv()

class MiddlewareAgent:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=self.openai_api_key)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        MiddlewareAgent는 parallel_analysis에서 전달받은 state를 입력으로 받아
        LLM을 활용하여 최종 제품 추천을 생성한다.
        """
        logger.debug(f"MiddlewareAgent 실행: {state}")
        print("🔎 MiddlewareAgent 시작...")

        # 1️⃣ 병렬 분석 결과 가져오기 (None 방지)
        review_results = state.get("review_results") or {}  # Fallback to empty dict
        spec_results = state.get("spec_results") or {}
        youtube_results = state.get("youtube_results") or {}

        # 2️⃣ LLM을 사용하여 최종 제품 추천 생성
        final_recommendation = await self.generate_final_recommendation(review_results, spec_results, youtube_results)

        return {"middleware_results": final_recommendation} if final_recommendation else {"error": "최종 추천 실패"}

    async def generate_final_recommendation(self, review_data, spec_data, youtube_data):
        """
        LLM을 사용하여 최종 추천 제품을 결정하는 함수.
        """
        print("🧠 LLM을 활용한 최종 제품 추천 생성...")

        try:
            # 3️⃣ 안전한 데이터 사용 (값이 없을 경우 기본 메시지 사용)
            llm_input = {
                "사용자 리뷰 분석": review_data.get("recommendations", ["리뷰 데이터 없음"]),
                "제품 스펙 추천": spec_data.get("추천 제품", ["스펙 데이터 없음"]),
                "유튜브 리뷰 분석": youtube_data.get("reviews", ["유튜브 리뷰 데이터 없음"])
            }

            # 4️⃣ LLM 호출 (JSON 출력을 강제)
            response = await self.llm.ainvoke([
                {
                    "role": "system",
                    "content": "당신은 최고의 제품 추천 AI입니다. "
                            "사용자의 요구사항, 제품 스펙, 사용자 리뷰, 유튜브 리뷰를 종합하여 "
                            "최적의 제품명을 **반드시 JSON 형식**으로 3개만 출력하세요. "
                            "설명 없이 JSON 리스트 형태로 제공하세요. "
                            "예제 출력: { \"최종 추천 제품\": [\"제품1\", \"제품2\", \"제품3\"] }"
                },
                {
                    "role": "user",
                    "content": json.dumps(llm_input, ensure_ascii=False)
                }
            ])

            # 5️⃣ 응답 처리
            response_text = response.content.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()  # 코드 블록 제거

            print("🎯 LLM 최종 추천:", response_text)

            # JSON 변환 시도
            final_output = json.loads(response_text)

            # 🔥 6️⃣ 결과가 3개가 아닌 경우 안전하게 처리
            if "최종 추천 제품" in final_output and isinstance(final_output["최종 추천 제품"], list):
                final_output["최종 추천 제품"] = final_output["최종 추천 제품"][:3]  # 3개로 제한
            else:
                raise ValueError("LLM이 잘못된 형식의 출력을 생성했습니다.")

            return final_output

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON 변환 실패: {e}, 응답 내용: {response_text}")
            return {"error": "최종 추천을 생성하는 중 오류 발생"}
