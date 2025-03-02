from typing import Dict, Any, List
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json
from app.agents.tablet_reviews_db.review_db_manager import ReviewDBManager
from dotenv import load_dotenv
from .base import BaseAgent
import logging

logger = logging.getLogger("smartpick.agents.review_agent")

load_dotenv()

class ProductRecommender(BaseAgent):
    def __init__(self, persist_directory: str = None):
        super().__init__(name="ProductRecommender")
        if persist_directory is None:
            persist_directory = os.getenv("REVIEW_DB_PATH", os.path.join(
                os.path.dirname(__file__),
                "tablet_reviews_db"
            ))
        self.db_manager = ReviewDBManager(persist_directory)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        logger.debug(f"ProductRecommender initialized with db path: {persist_directory}")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug(f"Running ProductRecommender with state: {state}")
        return self.generate_recommendations(state)

    @staticmethod
    def _format_user_requirements(requirements: Dict[str, Any]) -> tuple[str, str, str]:
        """사용자 요구사항을 자연스러운 문장으로 변환"""
        scenario = f"""디지털 기기 사용 시나리오:
    - 주요 활동: {', '.join(requirements['사용_시나리오']['주요_활동'])}
    - 사용 환경: {', '.join(requirements['사용_시나리오']['사용_환경'])}
    - 사용 시간: {requirements['사용_시나리오']['사용_시간']}
    - 사용자 수준: {requirements['사용_시나리오']['사용자_수준']}"""

        concerns = f"""제품 관련 주요 고려사항:
    - 선호 브랜드: {', '.join(requirements['주요_관심사']['브랜드_선호도'])}
    - 불편사항: {', '.join(requirements['주요_관심사']['불편사항'])}
    - 중요 고려사항: {', '.join(requirements['주요_관심사']['만족도_중요항목'])}
    - 디자인 선호도: {', '.join(requirements['감성적_요구사항']['디자인_선호도'])}
    - 가격대: {requirements['감성적_요구사항']['가격대_심리']}"""

        worries = f"""주요 우려사항:
    - {' '.join(requirements['사용자_우려사항'])}"""

        return scenario, concerns, worries

    def generate_recommendations(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        search_queries = []
        
        # 주요 활동 관련 리뷰
        search_queries.extend(requirements['사용_시나리오']['주요_활동'])
        
        # 사용 환경 관련 리뷰
        search_queries.extend(requirements['사용_시나리오']['사용_환경'])
        
        # 사용 시간 관련 리뷰
        search_queries.append(requirements['사용_시나리오']['사용_시간'])

        # 사용자 수준 관련 리뷰
        search_queries.append(requirements['사용_시나리오']['사용자_수준'])
        
        # 브랜드 선호도 관련 리뷰
        search_queries.extend(requirements['주요_관심사']['브랜드_선호도'])
        
        # 불편사항 관련 리뷰
        search_queries.extend(requirements['주요_관심사']['불편사항'])
        
        # 만족도 중요항목 관련 리뷰
        search_queries.extend(requirements['주요_관심사']['만족도_중요항목'])
        
        # 디자인 선호도 관련 리뷰
        search_queries.extend(requirements['감성적_요구사항']['디자인_선호도'])
        
        # 가격대 관련 리뷰 - '상관없음'이 아닐 때만 포함
        if requirements['감성적_요구사항']['가격대_심리'] != "상관없음":
            search_queries.append(requirements['감성적_요구사항']['가격대_심리'])
        
        # 우려사항 관련 리뷰
        search_queries.extend(requirements['사용자_우려사항'])
        
        # 빈 문자열이나 None 값 제거
        search_queries = [query for query in search_queries if query and query.strip()]

        # 각 관점별로 리뷰 검색
        all_reviews = []
        for query in search_queries:
            relevant_reviews = self.db_manager.search_reviews(
                query=query,
                similarity_threshold=0.6,
                max_results=20,
                exact_product_match=False
            )
            all_reviews.extend(relevant_reviews)

        # 중복 리뷰 제거 및 품질 필터링
        filtered_reviews = []
        seen_reviews = set()
        for review in all_reviews:
            review_text = review['text']
            if review_text not in seen_reviews and len(review_text) > 20:  # 최소 길이 필터
                filtered_reviews.append(review)
                seen_reviews.add(review_text)
        
        # 제품별로 상위 리뷰들을 모두 수집
        product_reviews = {}
        for review in filtered_reviews:
            product = review['product']
            if product not in product_reviews:
                product_reviews[product] = []
            # 리뷰 품질 점수 계산
            quality_score = (
                review['similarity_score'] * 0.4 +  # 검색 관련성
                (len(review['text']) / 1000) * 0.3 +  # 리뷰 길이
                (review.get('rating', 3) / 5) * 0.3  # 평점
            )
            review['quality_score'] = quality_score
            product_reviews[product].append(review)
        
        # 각 제품별로 리뷰들을 similarity_score 기준으로 정렬하고 상위 5개 선택
        analyzed_products = {}
        for product, reviews in product_reviews.items():
            sorted_reviews = sorted(reviews, key=lambda x: x['similarity_score'], reverse=True)
            analyzed_products[product] = {
                'reviews': sorted_reviews[:10],  # 상위 10개 리뷰 선택
                'avg_rating': sum(r['rating'] for r in reviews) / len(reviews),
                'avg_similarity': sum(r['similarity_score'] for r in reviews) / len(reviews),
                'avg_quality': sum(r['quality_score'] for r in reviews) / len(reviews),
                'review_count': len(reviews)
            }

        # 평균 유사도와 평점을 기준으로 제품들을 정렬
        relevant_products = sorted(
            analyzed_products.items(),
            key=lambda x: (
                x[1]['avg_similarity'] * 0.8 +  # 검색 관련성 80%
                x[1]['avg_quality'] * 0.2       # 리뷰 품질 20%
            ),
            reverse=True
        )

        if not relevant_products:
            return {
                "recommendations": "주어진 조건에 맞는 제품을 찾을 수 없습니다.",
                "reason": "검색된 리뷰가 없습니다."
            }

        # 리뷰 컨텍스트 생성 - 각 제품별로 여러 리뷰 종합
        review_contexts = []
        for product, data in relevant_products[:5]:  # 상위 5개 제품만 선택
            product_context = f"""
            제품명: {product}
            전체 검토된 리뷰 수: {data['review_count']}
            평균 평점: {data['avg_rating']:.1f}
            
            주요 리뷰들:
            """
            
            for idx, review in enumerate(data['reviews'], 1):
                sentiment = self._analyze_review_sentiment(review['text'])
                platform = review.get('platform', '플랫폼 정보 없음')
                product_context += f"""
                [리뷰 {idx} - {platform}]
                - 사용 기간: {review.get('usage_period', '정보 없음')}
                - 만족도: {review['rating']}
                - 감성 분석: {sentiment}
                - 상세 내용: {review['text']}
                - 장점: {review.get('pros', '정보 없음')}
                - 단점: {review.get('cons', '정보 없음')}
                """
            
            review_contexts.append(product_context)

        # 사용자 요구사항 포맷팅
        scenario_text, concerns_text, worries_text = self._format_user_requirements(requirements)
        logger.debug(scenario_text)
        logger.debug(concerns_text)
        logger.debug(worries_text)


        # 추천 생성을 위한 프롬프트 개선
        system_template = """당신은 태블릿 제품 추천 전문가입니다. 
        아래 주어진 실제 사용자 요구사항과 실제 리뷰 데이터만을 기반으로 태블릿을 추천해주세요.

        [사용자 요구사항]
        {scenario_text}

        [주요 고려사항]
        {concerns_text}

        [우려사항]
        {worries_text}

        [검색된 제품 리뷰들]
        {review_contexts}

        다음 규칙을 반드시 지켜주세요:
        1. 반드시 제공된 리뷰에 언급된 제품만 추천해야 합니다
        2. 실제 리뷰 내용만 인용해야 합니다
        3. 리뷰에 없는 기능이나 특징을 임의로 추가하면 안됩니다
        4. 사용자의 구체적인 요구사항(사용 환경, 사용 시간 등)에 맞춰 추천해주세요
        5. 추천할 때는 반드시 관련된 실제 리뷰를 인용하고, 해당 리뷰의 출처 플랫폼을 명시해주세요
        6. 제시된 형식을 정확히 따라주세요
        7. 응답은 반드시 JSON 형식으로 제공해야 합니다"""

        human_template = """다음 JSON 형식으로 정확히 추천해주세요:
        ```json
        {
          "recommendations": [
            {
              "rank": 1,
              "product_name": "최우선 추천 태블릿 이름",
              "reasons": [
                "추천 이유 1 (실제 리뷰 인용 포함)",
                "추천 이유 2 (실제 리뷰 인용 포함)"
              ],
              "suitability": [
                "사용자 요구사항과의 적합성 1",
                "사용자 요구사항과의 적합성 2"
              ],
              "review_sources": ["플랫폼1", "플랫폼2"]
            },
            {
              "rank": 2,
              "product_name": "차선책 추천 태블릿 이름",
              "reasons": [
                "추천 이유 1 (실제 리뷰 인용 포함)",
                "추천 이유 2 (실제 리뷰 인용 포함)"
              ],
              "suitability": [
                "사용자 요구사항과의 적합성 1",
                "사용자 요구사항과의 적합성 2"
              ],
              "differences": [
                "첫 번째 추천 제품과의 차이점 1",
                "첫 번째 추천 제품과의 차이점 2"
              ],
              "review_sources": ["플랫폼1", "플랫폼2"]
            }
          ]
        }
        ```
        
        반드시 유효한 JSON 형식으로 응답해야 합니다. 추가 설명이나 마크다운 포맷은 사용하지 마세요."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("human", human_template)
        ])

        # 실제 프롬프트 내용 확인을 위한 데이터 준비
        prompt_data = {
            "scenario_text": scenario_text,
            "concerns_text": concerns_text,
            "worries_text": worries_text,
            "review_contexts": "\n\n".join(review_contexts)
        }

        # 실제 프롬프트 내용 확인
        formatted_prompt = prompt.format_prompt(**prompt_data)
        logger.debug("\n=== 실제 프롬프트 내용 ===")
        logger.debug(formatted_prompt.to_string())  # 직접 포맷된 내용 출력
        logger.debug("\n=== 프롬프트 끝 ===\n")

        # ChatGPT를 통한 추천 생성
        chain = prompt | ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=self.openai_api_key)
        result = chain.invoke(prompt_data)
        
        # JSON 파싱 시도
        try:
            recommendations_json = json.loads(result.content)
            return recommendations_json
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 원본 텍스트 반환
            logger.warning("Failed to parse recommendation as JSON, returning raw text")
            return {
                "recommendations": result.content,
                "format_error": "Failed to parse as JSON"
            }

    def _analyze_review_sentiment(self, review_text: str) -> Dict[str, Any]:
        """리뷰 텍스트의 감성 분석"""
        system_template = """태블릿 제품 리뷰의 감성을 다음 기준으로 분석해주세요:
            1. 전반적 만족도: 매우불만/불만/중립/만족/매우만족
            2. 주요 만족 요소: 성능/디자인/가격/휴대성/화면/배터리 등 구체적 항목
            3. 주요 불만족 요소: 성능/디자인/가격/휴대성/화면/배터리 등 구체적 항목
            
            다음 JSON 형식으로 응답해주세요:
            {{
                "overall_sentiment": "만족도 레벨",
                "satisfaction_points": ["만족 요소1", "만족 요소2"],
                "dissatisfaction_points": ["불만족 요소1", "불만족 요소2"]
            }}"""

        human_template = "다음 리뷰를 분석해주세요: {review}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("human", human_template)
        ])
        
        chain = prompt | ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0, 
            api_key=self.openai_api_key
        )
        result = chain.invoke({"review": review_text})
        
        try:
            # 문자열을 딕셔너리로 변환
            sentiment_dict = json.loads(result.content)
            return sentiment_dict
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 기본값 반환
            return {
                "overall_sentiment": "중립",
                "satisfaction_points": [],
                "dissatisfaction_points": []
            }
            
###---------- 최종 제품 추천 이후 제품 통계 정보 수집 ----------###
    def get_product_insights(self, product_name: str) -> Dict[str, Any]:
        """특정 제품에 대한 종합적인 리뷰 인사이트를 제공합니다."""
        logger.debug(f"Retrieving comprehensive insights for product: {product_name}")
        
        # 제품명으로 리뷰 검색
        reviews = self.db_manager.search_reviews(
            query=product_name,
            similarity_threshold=0.7,
            max_results=200,  # 충분한 리뷰 확보
            exact_product_match=True
        )
        
        if not reviews:
            logger.warning(f"No reviews found for product: {product_name}")
            return {
                "product_name": product_name,
                "error": "제품에 대한 리뷰를 찾을 수 없습니다."
            }
        
        # 기본 통계 계산
        total_reviews = len(reviews)
        ratings = [review.get('rating', 0) for review in reviews if 'rating' in review]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # 긍정/부정 리뷰 분류
        positive_reviews = [review for review in reviews if review.get('rating', 0) >= 4]
        negative_reviews = [review for review in reviews if review.get('rating', 0) <= 3]
        
        # 긍/부정 리뷰 비율 계산
        positive_ratio = len(positive_reviews) / total_reviews * 100 if total_reviews > 0 else 0
        negative_ratio = len(negative_reviews) / total_reviews * 100 if total_reviews > 0 else 0
        
        # 리뷰 데이터 준비
        review_data = {
            "product_name": product_name,
            "total_reviews": total_reviews,
            "average_rating": round(avg_rating, 1),
            "positive_ratio": round(positive_ratio, 1),
            "negative_ratio": round(negative_ratio, 1),
            "positive_reviews": positive_reviews[:10],  # 상위 10개 긍정 리뷰
            "negative_reviews": negative_reviews[:10]   # 상위 10개 부정 리뷰
        }
        
        # LLM에게 리뷰 분석 요청
        return self._analyze_reviews_with_llm(review_data)
    
    def _analyze_reviews_with_llm(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """LLM을 사용하여 리뷰 데이터를 종합적으로 분석합니다."""
        
        # 리뷰 텍스트 준비
        positive_review_texts = []
        for idx, review in enumerate(review_data["positive_reviews"][:4], 1):
            platform = review.get('platform', '알 수 없음')
            usage_period = review.get('usage_period', '알 수 없음')
            text = review.get('text', '')
            positive_review_texts.append(f"[긍정 리뷰 {idx} - {platform}, 사용기간: {usage_period}]\n{text}")
        
        negative_review_texts = []
        for idx, review in enumerate(review_data["negative_reviews"][:4], 1):
            platform = review.get('platform', '알 수 없음')
            usage_period = review.get('usage_period', '알 수 없음')
            text = review.get('text', '')
            negative_review_texts.append(f"[부정 리뷰 {idx} - {platform}, 사용기간: {usage_period}]\n{text}")
        
        # 프롬프트 템플릿
        system_template = """당신은 제품 리뷰 분석 전문가입니다. 
        주어진 제품 리뷰 데이터를 분석하여 종합적인 인사이트를 제공해주세요.
        
        다음 정보를 포함해야 합니다:
        1. 긍정적 리뷰 요약 (최대 3개)
        2. 부정적 리뷰 요약 (최대 3개)
        3. 장점에 해당하는 리뷰 (최소 3개)
        4. 단점에 해당하는 리뷰 (최소 3개)
        
        응답은 반드시 JSON 형식으로 제공해야 합니다."""

        human_template = """다음은 {product_name}에 대한 리뷰 데이터입니다:
        
        총 리뷰 수: {total_reviews}개
        평균 평점: {average_rating}점
        긍정 리뷰 비율: {positive_ratio}%
        부정 리뷰 비율: {negative_ratio}%
        
        [긍정적 리뷰 샘플]
        {positive_reviews}
        
        [부정적 리뷰 샘플]
        {negative_reviews}
        
        위 데이터를 분석하여 다음 JSON 형식으로 응답해주세요:
        ```json
        {{
          "positive_review_summaries": [
            "긍정 리뷰 1 요약",
            "긍정 리뷰 2 요약",
            "긍정 리뷰 3 요약",
            "긍정 리뷰 4 요약"
          ],
          "negative_review_summaries": [
            "부정 리뷰 1 요약",
            "부정 리뷰 2 요약",
            "부정 리뷰 3 요약",
            "부정 리뷰 4 요약"
          ],
          "key_strengths": [
            "주요 장점 1",
            "주요 장점 2",
            "주요 장점 3"
          ],
          "key_weaknesses": [
            "주요 단점 1",
            "주요 단점 2",
            "주요 단점 3"
          ]
        }}
        ```"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("human", human_template)
        ])
        
        # LLM 호출
        chain = prompt | ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2, 
            api_key=self.openai_api_key
        )
        
        # 프롬프트 데이터 준비
        prompt_data = {
            "product_name": review_data["product_name"],
            "total_reviews": review_data["total_reviews"],
            "average_rating": review_data["average_rating"],
            "positive_ratio": review_data["positive_ratio"],
            "negative_ratio": review_data["negative_ratio"],
            "positive_reviews": "\n\n".join(positive_review_texts),
            "negative_reviews": "\n\n".join(negative_review_texts)
        }
        
        # LLM 호출 및 결과 파싱
        result = chain.invoke(prompt_data)
        
        try:
            # JSON 파싱
            insights = json.loads(result.content)
            
            # 기본 통계 정보 추가
            insights["product_name"] = review_data["product_name"]
            insights["total_reviews"] = review_data["total_reviews"]
            insights["average_rating"] = review_data["average_rating"]
            insights["positive_ratio"] = review_data["positive_ratio"]
            insights["negative_ratio"] = review_data["negative_ratio"]
            
            # 원본 리뷰 추가
            insights["original_positive_reviews"] = [
                {
                    "text": review.get('text', ''),
                    "rating": review.get('rating', 0),
                    "platform": review.get('platform', '알 수 없음'),
                    "usage_period": review.get('usage_period', '알 수 없음')
                }
                for review in review_data["positive_reviews"][:4]
            ]
            
            insights["original_negative_reviews"] = [
                {
                    "text": review.get('text', ''),
                    "rating": review.get('rating', 0),
                    "platform": review.get('platform', '알 수 없음'),
                    "usage_period": review.get('usage_period', '알 수 없음')
                }
                for review in review_data["negative_reviews"][:4]
            ]
            
            return insights
            
        except json.JSONDecodeError:
            # JSON 파싱 실패 시
            logger.warning("Failed to parse LLM response as JSON")
            return {
                "product_name": review_data["product_name"],
                "error": "리뷰 분석 결과를 JSON으로 파싱할 수 없습니다.",
                "raw_response": result.content
            }
    
    async def get_final_product_review_insights(self, product_name: str) -> Dict[str, Any]:
        """최종 추천 제품에 대한 리뷰 인사이트를 비동기적으로 제공합니다."""
        logger.debug(f"Retrieving review insights for final product: {product_name}")
        
        # 비동기 처리를 위한 래핑
        import asyncio
        
        # 리뷰 분석 실행 (CPU 바운드 작업이므로 스레드 풀에서 실행)
        return await asyncio.to_thread(self.get_product_insights, product_name)

# 사용 예시
if __name__ == "__main__":

    import time
    st=time.time()
    recommender = ProductRecommender("tablet_reviews_db")
    
    # 사용자 요구사항 예시
    user_review_requirements = {
        "사용_시나리오": {
            "주요_활동": ["디지털 드로잉"],
            "사용_환경": ["카페", "이동 중", "실내"],
            "사용_시간": "하루 5시간 이상",
            "사용자_수준": "취미 작가"
        },
        "주요_관심사": {
            "브랜드_선호도": ["애플"],
            "불편사항": ["발열", "배터리"],
            "만족도_중요항목": ["필기감", "휴대성", "화면 반응속도"]
        },
        "감성적_요구사항": {
            "디자인_선호도": ["심플한 디자인"],
            "가격대_심리": "상관없음"
        },
        "사용자_우려사항": [
            "장시간 사용시 피로도",
            "AS 및 내구성",
        ]
    }
    
    # 추천 받기
    mt = time.time()
    print(mt-st)
    result = recommender.generate_recommendations(user_review_requirements)
    print("\n=== 제품 추천 결과 ===")
    print(result["recommendations"])
    print(time.time()-mt)
