import asyncio
import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from app.utils.logger import logger
from app.agents.graph import AgentState 

load_dotenv()

class MiddlewareAgent:
    def __init__(self, spec_agent, review_agent):#, youtube_agent):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=self.openai_api_key)

        # ✅ Initialize agents
        self.spec_agent = spec_agent
        self.review_agent = review_agent
        #self.youtube_agent = youtube_agent

    async def run(self, state: AgentState) -> Dict[str, Any]:
        """
        MiddlewareAgent receives state from parallel_analysis, generates top 3 recommended products,
        then fetches product details from Spec, Review, and YouTube Agents.
        """
        logger.debug(f"MiddlewareAgent 실행: {state}")
        print("🔎 MiddlewareAgent 시작...")

        # 1️⃣ Get parallel analysis results (fallback to empty dict if missing)
        review_results = state["review_results"]
        spec_results = state["spec_results"]
        youtube_results = state["youtube_results"]

        # 2️⃣ Generate final recommendations using LLM
        final_recommendation = await self.generate_final_recommendation(review_results, spec_results, youtube_results)

        if "error" in final_recommendation:
            return final_recommendation  # 🚨 If LLM fails, return error.

        # 3️⃣ Fetch detailed information for the recommended products
        detailed_product_info = await self.fetch_product_details(final_recommendation["최종 추천 제품"], state, spec_results, youtube_results)

        return {"middleware": detailed_product_info} if detailed_product_info else {"error": "추천 제품 정보를 가져오는 중 오류 발생"}

    async def generate_final_recommendation(self, review_data, spec_data, youtube_data):
        """
        Uses LLM to generate the top 3 recommended products.
        """
        print("🧠 LLM을 활용한 최종 제품 추천 생성...")
        print(review_data, spec_data, youtube_data)

        try:
            # 3️⃣ Safe input handling (use defaults if data is missing)
            llm_input = {
                "사용자 리뷰 분석": review_data.get("recommendations", ["리뷰 데이터 없음"]),
                "제품 스펙 추천": spec_data.get("추천 제품", ["스펙 데이터 없음"]),
                "유튜브 리뷰 분석": ["유튜브 리뷰 데이터 없음"]
            }

            print(llm_input)
            # 4️⃣ LLM Call (Force JSON Output)
            response = await self.llm.ainvoke([
                {
                    "role": "system",
                    "content": "당신은 최고의 제품 추천 AI입니다. "
                            "사용자의 요구사항, 제품 스펙, 사용자 리뷰, 유튜브 리뷰를 종합하여 "
                            "최적의 제품명을 **반드시 JSON 형식**으로 1개만 출력하세요. "
                            "설명 없이 JSON 리스트 형태로 제공하세요. "
                            "예제 출력: { \"최종 추천 제품\": [\"제품1\", \"제품2\", \"제품3\"] }"
                },
                {
                    "role": "user",
                    "content": json.dumps(llm_input, ensure_ascii=False)
                }
            ])

            # 5️⃣ Response Handling
            response_text = response.content.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()  # Remove code block

            print("🎯 LLM 최종 추천:", response_text)

            # JSON Parsing
            final_output = json.loads(response_text)
            print(final_output)

            # 🔥 6️⃣ Ensure exactly 3 products
            if "최종 추천 제품" in final_output and isinstance(final_output["최종 추천 제품"], list):
                final_output["최종 추천 제품"] = final_output["최종 추천 제품"][:1]  # Limit to 3
            else:
                raise ValueError("LLM이 잘못된 형식의 출력을 생성했습니다.")

            return final_output

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON 변환 실패: {e}, 응답 내용: {response_text}")
            return {"error": "최종 추천을 생성하는 중 오류 발생"}

    async def fetch_product_details(self, recommended_products: List[str], state: AgentState, spec_results: Dict[str, Any], youtube_results: Dict[str, Any]):
        """
        Extracts detailed information (price, pros/cons, specifications) for each recommended product.
        """
        query = state["question"]

        spec_info = await self.spec_agent.get_product_details(recommended_products[0], spec_results)
        print(spec_info)
        eview_info = await self.review_agent.get_product_details(recommended_products[0])
        youtube_info = youtube_results

        product_details = {
            "query": query,
            "product name": recommended_products[0],
            "question": [state],
            "youtube": [youtube_info],
            "review": [review_info],
            "specification": [spec_info]
        }

        return product_details  
