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
            product_name = row["rename"]
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
    
    async def summarize_features(self, context, user_input):
        """제품 추천을 요약하는 함수 (최적화 버전)."""
        try:
            # ✅ 1️⃣ 최대 3개 제품 추천 (user_input 기반 필터링)
            recommended_products = []
            for item in context[:3]:  # 최대 3개 제품 사용
                product_name = item["제품명"]
                product_price = item["가격"]
                product_specs = item["핵심 사항"]  # 기존의 features_* 데이터 활용

                # ✅ 3️⃣ LLM을 호출하여 단점 + 최종 JSON 정리를 한 번에 수행!
                refined_product = await self.generate_final_product_json(
                    product_name, product_price, product_specs, user_input
                )

                recommended_products.append(refined_product)

            # ✅ 4️⃣ 최종 JSON 반환
            return {"추천 제품": recommended_products}

        except Exception as e:
            logger.error(f"❌ summarize_features 오류: {e}")
            return {"error": "추천 생성 중 오류 발생"}
        

    async def generate_final_product_json(self, product_name, product_price, product_specs, user_input):
        """LLM을 사용하여 '장점 + 단점 + 설명'을 자연스럽게 생성하는 함수."""
        try:
            response = await ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3,
                api_key=self.openai_api_key
            ).ainvoke([
                {
                    "role": "system",
                    "content": """
                    당신은 제품 추천 AI입니다. 사용자의 요청과 제품의 스펙을 바탕으로 제품의 장점과 단점을 분석하고, 핵심 사항의 설명을 자연스럽게 생성하세요.

                    - **장점**:
                    - 사용자의 입력(`사용자 입력`)과 제품의 스펙(`핵심 사항`)을 분석하여 중요한 장점을 3가지 생성하세요.
                    - 사용자가 강조한 사항(예: "배터리 오래 가는 제품")이 있다면 이를 반영하세요.
                    - 무작위로 장점을 생성하지 마세요.
                    - 장점은 간결하고, 실제 사용자가 제품을 사용할 때 유용한 점을 강조하세요.

                    - **단점**:
                    - 제품의 한계를 반영하여 현실적인 단점 3개를 생성하세요.
                    - 예를 들어, 가성비 제품이라면 "고급 기능 부족" 같은 단점이 있을 수 있습니다.


                    - **핵심 사항 정리**:
                        - 모든 `features_*` 항목을 그대로 `항목`으로 사용하세요. **새로운 카테고리를 생성하지 마세요.**
                        - "사양"은 해당 항목의 정보를 자연스럽고 짧은 한 문장으로 변환하세요.
                        - "사양"은 단순 나열하지 말고, 숫자나 단위를 포함하더라도 완전한 문장으로 변환하세요.
                        
                        - "사양" 작성 시 다음 규칙을 반드시 따르세요:
                            병렬 나열 금지 → "A17 Pro / 6코어 / 램 / : 8GB / 용량 / 128GB / microSD미지원" ❌
                            완전한 문장으로 변환 → "A17 Pro 칩과 6코어 CPU, 8GB RAM을 탑재하여 빠른 속도를 제공합니다. 단, microSD 확장이 불가능합니다." ✅
                            숫자와 단위가 자연스럽게 표현되도록 변경
                            "가로: 134.8mm / 세로: 195.4mm / 두께: 6.3mm / 무게: 293g" ❌
                            "134.8mm 너비와 195.4mm 높이를 갖춘 슬림한 디자인이며, 무게는 293g으로 가볍습니다." ✅
                            완전한 문장이되, 요약 느낌으로 부탁

                        - `"설명"`은 `"사양"`의 내용을 기반으로 사용자 경험에 초점을 맞춰 **자연스럽고 상세한 문장으로 제품의 활용 방식, 실생활에서의 유용성 등**으로 작성하세요.
                        - "설명"은 반드시 "사양"보다 길어야 합니다. 

                
                    응답은 반드시 **JSON 형식**으로 출력하세요. 예시는 다음과 같습니다:

                    ```json
                    {
                        "제품명": "APPLE iPad Air M2",
                        "가격": 1099000,
                        "추천 이유": {
                            "장점": ["M2 칩으로 강력한 성능", "Apple Pencil 2세대 지원", "고급스러운 디자인"],
                            "단점": ["비싼 가격", "SD 카드 미지원", "충전기가 별도 구매"]
                        },
                        "핵심 사항": [
                            {
                                "항목": "디스플레이",
                                "사양": "Liquid Retina 10.9인치",
                                "설명": "10.9인치 Liquid Retina 디스플레이를 탑재하여 선명한 색감과 넓은 시야각을 제공합니다. 색 재현율이 뛰어나 영상 감상이나 디자인 작업에 적합합니다."
                            },
                            {
                                "항목": "배터리 & 충전",
                                "사양": "USB-C 충전 지원, 최대 30W 고속 충전 가능",
                                "설명": "C타입 단자로 충전이 가능하며 USB3.1을 지원하여 데이터 전송 속도가 빠릅니다. 배터리는 약 8,900mAh(28.93WH) 용량으로 최대 30W 고속 충전을 지원하여 짧은 시간 내에 충전할 수 있습니다."
                            }
                        ]
                    }
                    ```
                    
                    **반드시 코드 블록(```json ... ```) 없이 JSON만 출력하세요.**
                    """
                }
                ,
                {
                    "role": "user",
                    "content": json.dumps({
                        "제품명": product_name,
                        "가격": product_price,
                        "핵심 사항": product_specs,
                        "사용자 입력": user_input
                    }, ensure_ascii=False)
                }
            ])

            response_text = response.content.strip()
            response_text = self.clean_json_response(response_text)  # JSON 정제

            # ✅ JSON 파싱
            parsed_response = json.loads(response_text)
            return parsed_response

        except json.JSONDecodeError:
            logger.error(f"❌ LLM JSON 변환 실패: {response_text}")
            return {
                "제품명": product_name,
                "가격": product_price,
                "추천 이유": {
                    "장점": ["제품의 장점을 분석하는 중 오류 발생"],
                    "단점": ["단점 생성 실패"]
                },
                "핵심 사항": [
                    {
                        "항목": spec["항목"],
                        "사양": spec["사양"],
                        "설명": f"{spec['항목']}은(는) {spec['사양']}의 사양을 갖춘 제품입니다."
                    } for spec in product_specs
                ]
            }

    def clean_json_response(self, text):
        """
        JSON에서 깨진 문자 제거
        """
        # 🔹 JSON 외부의 텍스트 제거
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        
        # 🔹 깨진 문자(공백, 특수 문자) 제거
        text = re.sub(r"\s+", " ", text)  # 연속된 공백 제거
        text = re.sub(r",\s*}", "}", text)  # 잘못된 쉼표 제거
        text = re.sub(r",\s*\]", "]", text)  # 잘못된 쉼표 제거

        return text


    def extract_price(self, features_text):
        """제품의 출시가를 추출하는 함수."""
        match = re.search(r"출시가:\s*([\d,]+)원", str(features_text))
        return int(match.group(1).replace(",", "")) if match else None



    async def get_product_details(self, product_name: str, spec_results: Dict[str, Any]) -> dict:
        """
        Returns detailed specifications and price of the given product.
        """
        df = pd.read_csv(self.product_csv)
        product_row = df[df["name"] == product_name]

        logger.info(f"🔍 검색된 제품명: {product_name}, 결과 개수: {len(product_row)}")

        if product_row.empty:
            return {
                "제품명": product_name,
                "가격": "정보 없음",
                "추천 이유": {"장점": ["장점 정보 없음"], "단점": ["단점 정보 없음"]},
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

        logger.info(f"🔍 핵심 사항 확인: {core_specs}")

        # LLM 호출하여 장점 & 단점 생성
        return await self.fetch_product_details(product_name, price, core_specs, spec_results)

    async def fetch_product_details(self, product_name: str, price: Any, core_specs: list, spec_results: dict):
        """
        Calls LLM to generate product pros/cons and returns full product details.
        먼저 spec_results에서 product_name을 찾아보고, 존재하면 해당 값을 반환한다.
        없을 경우 LLM을 호출하여 추천 이유 및 핵심 사항을 생성한다.
        """
        try:
            # ✅ 1️⃣ spec_results에서 product_name 확인 (key error 방지)
            recommended_products = spec_results.get("추천 제품", [])
            for product in recommended_products:
                if product.get("제품명") == product_name:
                    logger.info(f"🔍 spec_results에서 '{product_name}'을 찾았습니다. 기존 결과 반환.")
                    return {
                        "specifications": {
                            "추천 이유": product["추천 이유"],
                            "핵심 사항": product["핵심 사항"]
                        },
                        "purchase_info": self.purchase_inform(product_name)
                    }

            # ✅ 2️⃣ spec_results에 없다면 LLM 호출
            logger.info(f"🔍 spec_results에서 '{product_name}'을 찾지 못함. LLM 호출 진행.")

            response = await ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=self.openai_api_key).ainvoke([
                {
                    "role": "system",
                    "content": """
                    당신은 제품 추천 AI입니다. 제품의 장점(pros)과 단점(cons)을 3개씩 요약하고 JSON으로 반환하세요.
                    또한, '핵심 사항'에 대해 '항목'과 '사양'을 참고하여 반드시 각 사양에 대한 구체적인 '설명'을 생성하세요.
                    응답 예시는 아래와 같습니다:
                    ```json
                    {
                        "추천 이유": {
                            "장점": ["장점 1", "장점 2", "장점 3"],
                            "단점": ["단점 1", "단점 2", "단점 3"]
                        },
                        "핵심 사항": [
                            {
                                "항목": "카메라",
                                "사양": "50MP",
                                "설명": "이 카메라는 저조도에서도 선명한 사진을 촬영할 수 있음."
                            }
                        ]
                    }
                    ```
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

            # ✅ 3️⃣ JSON 변환 오류 대비
            try:
                product_summary = json.loads(response_text)
            except json.JSONDecodeError:
                logger.error(f"❌ JSON 변환 실패: {response_text}")
                product_summary = {"추천 이유": {"장점": ["정보 없음"], "단점": ["정보 없음"]}, "핵심 사항": core_specs}

            # ✅ 4️⃣ "추천 이유"가 없으면 기본값 추가
            product_summary.setdefault("추천 이유", {"장점": ["정보 없음"], "단점": ["정보 없음"]})

            specifications = {
                "추천 이유": product_summary["추천 이유"],
                "핵심 사항": product_summary.get("핵심 사항", core_specs)  # LLM 응답이 없으면 기존 데이터 유지
            }

            return {
                "specifications": specifications,
                "purchase_info": self.purchase_inform(product_name)
            }

        except Exception as e:
            logger.error(f"❌ LLM 호출 실패: {e}")
            return {
                "specifications": {
                    "추천 이유": {"장점": ["정보 없음"], "단점": ["정보 없음"]},
                    "핵심 사항": core_specs
                },
                "purchase_info": self.purchase_inform(product_name)
            }

    def purchase_inform(self, product_name):
        """
        purchase csv에서 다나와, 네이버, 쿠팡에 대한 정보 추출
        """
        df = pd.read_excel(self.purchase_info)
        df_final = df[df["product_name"] == product_name].reset_index(drop=True)

        purchase_details = {"store": []}
        for _, row in df_final.iterrows():
            purchase_details["store"].append({
                "site": row["platform"],
                "price": row.get("price", "정보 없음"),  # ✅ 가격 동적 반영
                "purchase_link": row["purchase_link"],
                "rating": row["rating"]
            })

        return purchase_details





