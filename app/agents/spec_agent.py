import os
import json
import re
import logging
import pandas as pd
import asyncio
from typing import Dict, Any, Tuple
from openai import OpenAI
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger("product_recommender")

class SpecRecommender:
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.product_csv = os.path.join(base_dir, "documents", "product_details.csv")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = OpenAI(api_key=self.openai_api_key)
        logger.debug(f"SpecRecommender initialized with CSV file: {self.product_csv}")

    def extract_price(self, features_text: str) -> int:
        """ 제품의 출시가를 추출하는 함수 """
        features_text = str(features_text)
        match = re.search(r"출시가:\s*([\d,]+)원", features_text)
        if match:
            return int(match.group(1).replace(",", ""))
        return None

    def parse_price(self, price_text: str) -> int:
        """ 가격을 숫자로 변환하는 함수 (예: 50만원 -> 500000) """
        match = re.search(r"(\d+)만원", price_text)
        if match:
            return int(match.group(1)) * 10000
        return None

    def convert_user_price(self, price: Any) -> int:
        """ 사용자 입력 가격을 변환하는 함수 (예: 50만원 -> 500000) """
        if isinstance(price, str):
            return self.parse_price(price) or 0
        return price

    async def summarize_features(self, context, user_input):
        """ 제품 추천 시 장점(pros) 및 핵심 사항을 요약하는 함수 """
        if not context:
            return None

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 제품 추천 AI입니다."},
                {"role": "user", "content": f"""
                사용자가 원하는 조건: {json.dumps(user_input, ensure_ascii=False, indent=4)}
                제품 목록:
                ```json
                {json.dumps(context, ensure_ascii=False, indent=4)}
                ```
                """}
            ],
            temperature=0.3,
        )

        try:
            response_text = response.choices[0].message.content.strip()
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("JSON 변환 실패: 응답 내용을 확인하세요.")
            return None

    async def generate_recommendations(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        df = pd.read_csv(self.product_csv)
        logger.info(f"제품 데이터 로드 완료: {df.shape[0]}개 제품")

        # 사용자 입력 가격 변환
        user_min_price = self.convert_user_price(user_input["가격_범위"].get("최소", 0))
        user_max_price = self.convert_user_price(user_input["가격_범위"].get("최대", 50000000))

        context = []
        for _, row in df.iterrows():
            product_name = row["name"]
            features_text = row.get("features_규격", "")
            product_price = self.extract_price(features_text)
            
            if product_price is None:
                parsed_price = self.parse_price(features_text)
                product_price = parsed_price if parsed_price else 0
            
            if not isinstance(product_price, int):
                logger.warning(f"잘못된 가격 형식 감지: {product_name}, 가격 정보: {features_text}")
                continue

            if not (user_min_price <= product_price <= user_max_price):
                continue
            if any(excluded in product_name for excluded in user_input.get("제외_스펙", [])):
                continue

            core_specs = [{"항목": key.replace("features_", ""), "사양": value} for key, value in row.items() if key.startswith("features_") and pd.notna(value)]

            context.append({
                "제품명": product_name,
                "가격": f"{product_price:,}원",
                "핵심 사항": core_specs
            })

        recommendations = await self.summarize_features(context, user_input)
        return recommendations if recommendations else {"추천 제품": []}

    async def run(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """ 워크플로우 실행 메서드 """
        return await self.generate_recommendations(user_input)

if __name__ == "__main__":
    async def main():
        recommender = SpecRecommender()
        user_input = {
            '필수_스펙': {  
                            '성능': ['우수한 펜 반응속도'], 
                            '하드웨어': ['13인치 화면'], 
                            '기능': ['드로잉 앱 지원']
                            },
            '가격_범위': {  
                            '최소': '50만원', 
                            '최대': '100만원'
                            }
        }
        recommendations = await recommender.run(user_input)
        print(json.dumps(recommendations, indent=4, ensure_ascii=False))

    asyncio.run(main())