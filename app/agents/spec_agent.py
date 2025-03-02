import asyncio
import os
import json
import pandas as pd
import re
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph
from app.agents.base import BaseAgent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

logger = logging.getLogger("smartpick.agents.spec_agent")
load_dotenv()

class SpecRecommender(BaseAgent):
    def __init__(self, persist_directory: str = None):
        super().__init__(name="SpecRecommender")
        self.product_csv = os.getenv("SPEC_DB_PATH")
        self.persist_directory = persist_directory
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        logger.debug(f"SpecRecommend initialized with db path: {self.product_csv}")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"Running ProductRecommender with state: {state}")
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
        
        return context[:15]  # 최대 15개 제품만 전달
    
    async def summarize_features(self, context, user_input):
        """제품 추천을 요약하는 함수."""
        
        try:
            # 최대 3개 제품 추천
            recommended_products = [
                {
                    "제품명": item["제품명"],
                    "가격": item["가격"],
                    "추천 이유": {
                        "pros": ["장점 1", "장점 2", "장점 3"],
                        "cons": ["단점 1", "단점 2", "단점 3"]
                    },
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

            response = await ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=self.openai_api_key).ainvoke([
                {"role": "system", "content": "당신은 제품 추천 AI입니다. 문서에서 '항목'과 '사양'을 가져오되, 사양을 보기 좋게 요약하고, 이를 기반으로 설명을 생성하여 JSON으로 반환하세요."},
                {"role": "user", "content": json.dumps({"추천 제품": recommended_products}, ensure_ascii=False)}
            ])
            
            response_text = response.content.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()  # 코드 블록 제거
            print("LLM 응답:", response_text)
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 변환 실패: {e}, 응답 내용: {response_text}")
            return None
    
    def extract_price(self, features_text):
        """제품의 출시가를 추출하는 함수."""
        match = re.search(r"출시가:\s*([\d,]+)원", str(features_text))
        return int(match.group(1).replace(",", "")) if match else None