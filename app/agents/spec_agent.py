import asyncio
import os
import json
import pandas as pd
import re
from typing import Dict, Any, List
from langgraph.graph import StateGraph
from app.agents.base import BaseAgent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from app.utils.logger import logger

logger.debug(f"SpecRecommender initialized with filepath: {os.getenv('SPEC_DB_PATH')}")
load_dotenv()

class SpecRecommender(BaseAgent):
    def __init__(self, persist_directory: str = None):
        super().__init__(name="SpecRecommender")
        self.product_csv = os.getenv("SPEC_DB_PATH")
        self.purchase_info = os.getenv("PURCHASE_INFO_PATH")
        self.persist_directory = persist_directory
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"Running SpecRecommender with state: {state}")
        return await self.generate_recommendations(state)

    async def generate_recommendations(self, user_input: Dict[str, Any]) -> dict:
        """제품 추천을 생성하는 함수."""
        print("recommend 요구사항 : ", user_input)
        context = await self.filter_products(user_input)
        if not context:
            return {"error": "적절한 제품을 찾을 수 없습니다."}
        
        recommendations = await self.summarize_features(context, user_input)
        return recommendations if recommendations else {"error": "추천 생성 실패"}

    async def filter_products(self, user_input: dict) -> list:
        """사용자의 요구 사항에 맞는 제품 필터링"""
        df = pd.read_csv(self.product_csv)

        context = []
        for _, row in df.iterrows():
            product_name = row["name"]
            features_text = row.get("features_규격", "")
            product_price = self.extract_price(features_text)
            
            
            if product_price is None or not (user_input["가격_범위"]["최소"]["value"] <= product_price <= user_input["가격_범위"]["최대"]["value"]):
                continue
            if any(excluded in product_name for excluded in user_input.get("제외_스펙", [])):
                continue

            core_specs = [
                {"항목": key.replace("features_", ""), "사양": value, "설명": "LLM이 해당 사양을 기반으로 설명을 생성합니다."}
                for key, value in row.items() if key.startswith("features_") and pd.notna(value)
            ]

            context.append({"제품명": product_name, "가격": product_price, "핵심 사항": core_specs})
        
        return context
    
    import json
    import json
    import re
    import logging
    #from openai import ChatOpenAI

    logger = logging.getLogger(__name__)

    async def summarize_features(self, context, user_input):
        """제품 추천을 요약하는 함수."""

        try:
            # 최대 3개 제품 추천
            recommended_products = [
                {
                    "제품명": item["제품명"],
                    "가격": item["가격"],
                    "핵심 사항": [
                        {
                            "항목": spec["항목"],
                            "사양": spec["사양"],
                            "설명": spec["설명"]
                        } for spec in item["핵심 사항"]
                    ]
                }
                for item in context[:3]  # 최대 3개 제품 사용
            ]

            # LLM 호출
            response = await ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3,
                api_key=self.openai_api_key
            ).ainvoke([
                {
                    "role": "system",
                    "content": """
                    당신은 제품 추천 AI입니다. 사용자의 요구 사항과 제품 정보를 분석하여, 제품의 장점(pros)과 단점(cons)을 3개씩 요약하고 JSON 형식으로 반환하세요.
                    응답은 반드시 **아래 JSON 형식만 포함해야 합니다.**
                    ```json
                    {
                        "추천 제품": [
                            {
                                "제품명": "제품명",
                                "장점": ["장점 1", "장점 2", "장점 3"],
                                "단점": ["단점 1", "단점 2", "단점 3"]
                            }
                        ]
                    }
                    ```
                    **코드 블록(```json ... ```) 없이 JSON만 출력하세요.**
                    """
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "사용자 입력": user_input,
                        "추천 제품": recommended_products
                    }, ensure_ascii=False)
                }
            ])

            response_text = response.content.strip()
            logger.info(f"LLM 응답: {response_text}")

            # ✅ JSON만 추출하는 함수
            def extract_json(text):
                match = re.search(r"\{.*\}", text, re.DOTALL)
                return match.group(0) if match else None

            # ✅ JSON 응답 정제
            response_text = extract_json(response_text)
            if response_text is None:
                logger.error(f"❌ JSON을 찾을 수 없음, 응답 내용: {response.content}")
                return {"error": "올바른 JSON을 찾을 수 없음"}

            # ✅ JSON 파싱
            try:
                parsed_response = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON 변환 실패: {e}, 응답 내용: {response_text}")
                return {"error": "JSON 형식 오류 발생"}

            # ✅ JSON 내부 구조 검증
            if not isinstance(parsed_response, dict) or "추천 제품" not in parsed_response:
                logger.error(f"❌ 예상된 JSON 구조가 아님: {parsed_response}")
                return {"error": "LLM 응답이 예상된 구조가 아님"}

            return parsed_response

        except Exception as e:
            logger.error(f"❌ summarize_features 오류: {e}")
            return {"error": "추천 생성 중 오류 발생"}

    





    def extract_price(self, features_text):
        """제품의 출시가를 추출하는 함수."""
        match = re.search(r"출시가:\s*([\d,]+)원", str(features_text))
        return int(match.group(1).replace(",", "")) if match else None


    async def get_product_details(self, product_name: str) -> dict:
        """
        Returns detailed specifications and price of the given product.
        """
        df = pd.read_csv(self.product_csv)
        product_row = df[df["name"] == product_name]

        print(f"🔍 검색된 제품명: {product_name}, 결과: {product_row}")

        if product_row.empty:
            return {
                "제품명": product_name,
                "가격": "정보 없음",
                "추천 이유": {"pros": ["장점 정보 없음"], "cons": ["단점 정보 없음"]},
                "핵심 사항": []
            }

        product_data = product_row.iloc[0]
        price = product_data.get("price", "정보 없음")

        # 핵심 사항 리스트 추출 및 데이터 검증
        core_specs = []
        for key, value in product_data.items():
            if key.startswith("features_") and pd.notna(value):
                항목 = key.replace("features_", "")
                사양 = value
                설명 = "LLM이 해당 사양을 기반으로 설명을 생성합니다."
                core_specs.append({"항목": 항목, "사양": 사양, "설명": 설명})

        print(f"🔍 핵심 사항 확인: {core_specs}")

        # LLM 호출하여 장점 & 단점 생성
        return await self.fetch_product_analysis(product_name, price, core_specs)

    async def fetch_product_analysis(self, product_name: str, price: Any, core_specs: list):
        """
        Calls LLM to generate product pros/cons and returns full product details.
        """
        try:
            # LLM 호출
            response = await ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=self.openai_api_key).ainvoke([
                {
                    "role": "system",
                    "content": """
                    당신은 제품 추천 AI입니다. 사용자의 요구 사항과 제품 정보를 분석하여, 제품의 장점(pros)과 단점(cons)을 3개씩 요약하고 JSON으로 반환하세요.
                    또한, '핵심 사항'에 대해 '항목'과 '사양'을 참고하여 반드시 각 사양에 대한 구체적인 '설명'을 생성하세요.
                    예를 들어:
                    - '카메라' 사양이 주어지면, 카메라의 해상도, 영상 촬영 가능 여부, 조도 환경에서의 성능 등을 분석하여 설명하세요.
                    - '배터리' 사양이 주어지면, 대기 시간, 고속 충전 지원 여부 등을 포함하세요.
                    - '화면' 사양이 주어지면, 디스플레이 기술, 주사율, 색상 표현력 등을 포함하세요.
                    설명이 부족하면 상세한 정보를 기반으로 의미 있는 문장을 작성하세요.
                    """
                },
                {
                    "role": "user",
                    "content": json.dumps({
                        "제품명": product_name,
                        "가격": price,
                        "핵심 사항": core_specs
                    }, ensure_ascii=False)
                }
            ])

            response_text = response.content.strip()
            print(f"🔍 LLM 응답 원본: {response_text}")

            # JSON 응답 코드 블록 제거
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()

            product_summary = json.loads(response_text)

            # 응답 데이터 확인
            # if "추천 이유" not in product_summary:
                #logger.error(f"❌ '추천 이유'가 LLM 응답에 없음: {product_summary}")
                #product_summary["추천 이유"] = {"pros": ["LLM 응답 오류"], "cons": ["LLM 응답 오류"]}

            # if "핵심 사항" not in product_summary:
                #logger.error(f"❌ '핵심 사항'이 LLM 응답에 없음: {product_summary}")
                #product_summary["핵심 사항"] = []

            # LLM 응답에 설명이 없으면 보완
            updated_core_specs = []
            for spec in core_specs:
                llm_spec = next((s for s in product_summary["핵심 사항"] if s["항목"] == spec["항목"]), None)

                # 설명이 없는 경우 템플릿 설명 추가
                설명 = llm_spec["설명"] if llm_spec and "설명" in llm_spec else self.generate_fallback_description(spec["항목"], spec["사양"])

                updated_core_specs.append({
                    "항목": spec["항목"],
                    "사양": spec["사양"],
                    "설명": 설명
                })

            # 최종 정제된 제품 정보 반환
            print(product_summary)
            specifications = {
                "추천 이유": product_summary["추천 이유"],
                "핵심 사항": updated_core_specs
            }

            return {
                "specifications": specifications,
                "purchase_info": self.purchase_inform(product_name)
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON 변환 실패: {e}, 응답 내용: {response_text}")
            return {
                "제품명": product_name,
                "가격": price,
                "추천 이유": {"pros": ["LLM 응답 오류"], "cons": ["LLM 응답 오류"]},
                "핵심 사항": core_specs
            }



    def purchase_inform(self, product_name):
        """
        purchase csv에서 다나와, 네이버, 쿠팡에 대한 정보 추출
        """

        df = pd.read_excel(self.purchase_info)
        df_final = df[df["product_name"] == product_name].reset_index(drop=True)

        purchase_details = {"store":[]}
        for _, row in df_final.iterrows() :
            purchase_details["store"].append({
                            "site" : row["platform"],
                            "price" : 800000,
                            "purchase_link": row["purchase_link"],
                            "rating" : row["rating"]
                            })

        return purchase_details

