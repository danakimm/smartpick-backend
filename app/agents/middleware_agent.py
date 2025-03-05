import asyncio
import logging
import json
from typing import Dict, Any, List

# 에이전트 모듈 임포트 (실제 구현 필요)
from spec_agent import SpecRecommender
from review_agent import ReviewRecommender

# 로깅 설정
logger = logging.getLogger("smartpick.agents.middleware_agent")

class BaseAgent:
    async def run(self, state: Dict[str, Any]):
        raise NotImplementedError("run method must be implemented")

class MiddlewareAgent(BaseAgent):
    """
    run 입력 포멧 dict
    {"middleware": {"query" : "유저 요청 사항",                                     <- str
            "product name" : "제품명",                                            <- srt
            "question" : ["질문에이전트 결과 리스트에 감싸서 입력"],                <- 길이 1 List 안에 dict
            "youtube" : ["유튜브 에이전트 결과 리스트에 감싸서 입력"],               <- 길이 1 List 안에 dict
            "review" : ["리뷰 에이전트 결과 리스트에 감싸서 입력"],                 <- 길이 1 List 안에 dict
            "specification" : ["제품 정보 분석 에이전트 결과 리스트에 감싸서 입력"],  <- 길이 1 List 안에 dict
            }
        }
    """
    
    
    def __init__(self):
        self.spec_agent = SpecRecommender()
        self.review_agent = ReviewRecommender()

    async def gather_recommendations(self, state: Dict[str, Any]) -> Dict[str, List]:
        """ 스펙 및 리뷰 에이전트에서 추천 제품 리스트를 수집 """
        spec_input = state.get("spec_agent_state", {}).get("spec_analysis", {})
        review_input = state["review_agent_state"]["review_analysis"]

        spec_future = self.spec_agent.run(spec_input)
        review_future = self.review_agent.run(review_input)

        spec_result, review_result = await asyncio.gather(
            spec_future, review_future
        )

        return {
            "spec": spec_result.get("추천 제품", []),
            "review": review_result.get("추천 제품", []),
        }

    def compute_final_scores(self, recommendations: Dict[str, List], spec_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ 가중치를 적용하여 최종 제품을 선정 """
        product_scores = {}
        
        # 기본 가중치 설정
        spec_weight = 0.7
        review_weight = 0.3
        
        # 스펙 입력이 비어 있으면 가중치를 0.5로 조정
        if not spec_input:
            spec_weight = 0.5
            review_weight = 0.5
        
        weights = {"spec": spec_weight, "review": review_weight}
        
        for source, weight in weights.items():
            for product in recommendations[source]:
                product_name = product["제품명"]
                if product_name not in product_scores:
                    product_scores[product_name] = {"제품명": product_name, "점수": 0, "출처": []}
                product_scores[product_name]["점수"] += weight
                product_scores[product_name]["출처"].append(source)

        sorted_products = sorted(product_scores.values(), key=lambda x: x["점수"], reverse=True)
        return sorted_products

    async def fetch_additional_info(self, final_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ 최종 추천된 제품에 대해 각 에이전트에서 추가 정보 요청 """
        additional_info_tasks = []
        for product in final_products:
            product_name = product["제품명"]
            additional_info_tasks.append(self.spec_agent.get_product_info(product_name))
            additional_info_tasks.append(self.review_agent.get_product_info(product_name))
        
        additional_infos = await asyncio.gather(*additional_info_tasks)
        for i, product in enumerate(final_products):
            product["추가 정보"] = additional_infos[i * 2: (i + 1) * 2]
        
        return final_products

    async def run(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ 전체 추천 파이프라인 실행 """
        recommendations = await self.gather_recommendations(state)
        spec_input = state.get("spec_agent_state", {}).get("spec_analysis", {})
        final_products = self.compute_final_scores(recommendations, spec_input)
        detailed_products = await self.fetch_additional_info(final_products[:5])
        return detailed_products

# examples
if __name__ == "__main__":
    async def main():
        agent = MiddlewareAgent()
        state = {
            "spec_agent_state": {
                "spec_analysis": {
                    "필수_스펙": {"성능": ["우수한 펜 반응속도"], "하드웨어": ["13인치 화면"], "기능": ["드로잉 앱 지원"]},
                    "가격_범위": {"최소": "50만원", "최대": "100만원"}
                }
            },
            "review_agent_state": {
                "review_analysis": {
                    "사용_시나리오": {"주요_활동": ["드로잉"], "사용_환경": ["실내"], "사용_시간": "장시간", "사용자_수준": "전문가"},
                    "주요_관심사": {"브랜드_선호도": ["애플"], "불편사항": ["배터리 수명"], "만족도_중요항목": ["화면 품질"]}
                }
            }
        }
        results = await agent.run(state)
        for product in results:
            print(json.dumps(product, indent=4, ensure_ascii=False))

    asyncio.run(main())
