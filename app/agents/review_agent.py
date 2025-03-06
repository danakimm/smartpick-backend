from typing import Dict, Any, List
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json
from app.agents.tablet_reviews_db.review_db_manager import ReviewDBManager
from dotenv import load_dotenv
from .base import BaseAgent
from app.utils.logger import logger
import asyncio

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
        search_queries.extend([f"{activity} 사용 경험" for activity in requirements['사용_시나리오']['주요_활동']])
        
        # 사용 환경 관련 리뷰
        search_queries.extend([f"{env}에서 사용" for env in requirements['사용_시나리오']['사용_환경']])
        
        # 사용 시간 관련 리뷰
        search_queries.append(f"사용 시간 {requirements['사용_시나리오']['사용_시간']}")

        # 사용자 수준 관련 리뷰
        search_queries.append(f"{requirements['사용_시나리오']['사용자_수준']} 사용자")
        
        # 브랜드 선호도 관련 리뷰
        search_queries.extend(requirements['주요_관심사']['브랜드_선호도'])
        
        # 불편사항 관련 리뷰
        search_queries.extend([f"{issue} 문제" for issue in requirements['주요_관심사']['불편사항']])
        
        # 만족도 중요항목 관련 리뷰
        search_queries.extend([f"{item} 만족" for item in requirements['주요_관심사']['만족도_중요항목']])
        
        # 디자인 선호도 관련 리뷰
        search_queries.extend([f"디자인 {pref}" for pref in requirements['감성적_요구사항']['디자인_선호도']])
        
        # 가격대 관련 리뷰 - '상관없음'이 아닐 때만 포함
        price_sentiment = requirements['감성적_요구사항']['가격대_심리']
        if price_sentiment != "상관없음":
            if "저렴" in price_sentiment:
                search_queries.extend(["가격 저렴", "가성비", "합리적인 가격"])
            elif "비싸" in price_sentiment:
                search_queries.extend(["가격이 비싸", "고가", "프리미엄"])
            else:
                search_queries.append(f"가격 {price_sentiment}")
        
        # 우려사항 관련 리뷰
        search_queries.extend([f"{worry} 경험" for worry in requirements['사용자_우려사항']])
        
        # 빈 문자열이나 None 값 제거 및 중복 제거
        search_queries = list(set([
            query.strip() 
            for query in search_queries 
            if query and query.strip()
        ]))

        logger.debug(f"Generated search queries: {search_queries}")

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
                "recommendations": [
                    {
                        "rank": 1,
                        "product_name": "추천 가능한 제품 없음",
                        "reasons": ["주어진 조건에 맞는 제품을 찾을 수 없습니다."],
                        "suitability": ["검색된 리뷰가 없습니다."],
                        "review_sources": []
                    }
                ]
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
                - 만족도: {review['rating']}
                - 감성 분석: {sentiment}
                - 상세 내용: {review['text']}
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
        4. 사용자의 구체적인 요구사항과 제품의 특성을 매칭하여 추천 이유를 설명하세요
        5. 각 추천 이유는 반드시 구체적인 리뷰 인용과 해당 리뷰의 출처 플랫폼을 포함해야 합니다
        6. 제시된 형식을 정확히 따라주세요
        7. 응답은 반드시 파싱 가능한 JSON 형식이어야 하며, JSON 외의 다른 텍스트를 포함하지 마세요"""

        human_template = """다음 형식으로 정확히 추천해주세요:
{"recommendations": [{"rank": 1,"product_name": "최우선 추천 태블릿 이름","reasons": ["추천 이유 1 (실제 리뷰 인용 포함)","추천 이유 2 (실제 리뷰 인용 포함)"],"suitability": ["사용자 요구사항과의 적합성 1","사용자 요구사항과의 적합성 2"],"review_sources": ["플랫폼1","플랫폼2"]},{"rank": 2,"product_name": "차선책 추천 태블릿 이름","reasons": ["추천 이유 1 (실제 리뷰 인용 포함)","추천 이유 2 (실제 리뷰 인용 포함)"],"suitability": ["사용자 요구사항과의 적합성 1","사용자 요구사항과의 적합성 2"],"differences": ["첫 번째 추천 제품과의 차이점 1","첫 번째 추천 제품과의 차이점 2"],"review_sources": ["플랫폼1","플랫폼2"]}]}"""

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
            # 앞뒤 공백 제거 및 불필요한 이스케이프 문자 제거
            cleaned_content = result.content.strip().replace('\n', '').replace('\\', '')
            recommendations_json = json.loads(cleaned_content)
            return recommendations_json
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            logger.debug(f"Raw content: {result.content}")
            return {
                "recommendations": [],
                "error": "추천 생성 중 오류가 발생했습니다",
                "details": str(e)
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

    async def get_product_details(self, product_name: str) -> Dict[str, Any]:
        """제품 상세 정보 가져오기"""
        # 제품 이름에 따른 제품 정보 가져오기
        product_reviews = self.db_manager.get_reviews_by_product(product_name)

        if not product_reviews:
            return {"product_name": product_name, "error": "리뷰를 찾을 수 없습니다."}

        # 긍정/부정 리뷰 수 계산
        positive_reviews = [r for r in product_reviews if r.get('sentiment') == 'positive']
        negative_reviews = [r for r in product_reviews if r.get('sentiment') == 'negative']

        total_reviews = len(product_reviews)
        positive_ratio = (len(positive_reviews) / total_reviews) * 100
        negative_ratio = (len(negative_reviews) / total_reviews) * 100

        # 대표 리뷰 선정
        selected_positive = self._select_representative_reviews(positive_reviews, count=8)
        selected_negative = self._select_representative_reviews(negative_reviews, count=8)

        # 긍정/부정 리뷰 분석 병렬 실행
        positive_analysis, negative_analysis = await asyncio.gather(
            self._generate_review_analysis(selected_positive, "긍정"),
            self._generate_review_analysis(selected_negative, "부정")
        )

        return {
            "product_name": product_name,
            "total_reviews": total_reviews,
            "positive_percentage": round(positive_ratio, 0),
            "negative_percentage": round(negative_ratio, 0),
            "positive_reviews": {
                "key_points": positive_analysis["key_points"],
                "reviews": positive_analysis["selected_reviews"]
            },
            "negative_reviews": {
                "key_points": negative_analysis["key_points"],
                "reviews": negative_analysis["selected_reviews"]
            }
        }

    def _select_representative_reviews(self, reviews: List[Dict], count: int = 2) -> List[Dict]:
        """대표 리뷰 선정"""
        # 품질 점수로 변환
        quality_scores = {
            'high': 3,
            'medium': 2,
            'low': 1
        }

        scored_reviews = []
        for review in reviews:
            score = quality_scores.get(review['quality'], 0)  # LLM이 분석한 품질 점수

            # 배송 관련 내용 감점
            if '배송' in review['text']:
                score -= 1

            # 플랫폼 다양성 가중치도 유지
            platform_counts = {}
            for r in scored_reviews:
                platform_counts[r['platform']] = platform_counts.get(r['platform'], 0) + 1

            if platform_counts.get(review['platform'], 0) == 0:
                score += 1

            scored_reviews.append({
                **review,
                'selection_score': score
            })

        # 점수로 정렬하고 상위 n개 선택
        scored_reviews.sort(key=lambda x: x['selection_score'], reverse=True)
        return scored_reviews[:count]

    async def _generate_review_analysis(self, reviews: List[Dict], sentiment_type: str) -> Dict:
        """리뷰들의 핵심 요약 포인트와 대표 리뷰들을 추출"""

        # 1. 먼저 각 리뷰를 요약
        summary_reviews = []
        for i, review in enumerate(reviews[:10]):
            summarize_prompt = ChatPromptTemplate.from_messages([
                ("system", """태블릿 리뷰를 요약하는 전문가입니다.
                원본 리뷰의 말투와 어조를 정확히 일치시켜 요약해주세요.
                예시)
                - 원본: "~합니다/습니다" → 요약: "~합니다/습니다"
                - 원본: "~했어요/에요" → 요약: "~했어요/에요"
                - 원본: "~임/함" → 요약: "~임/함"
                - 원본: "~한다/이다" → 요약: "~한다/이다"
                말투가 바뀌면 안됩니다."""),
                ("human", f"""다음 리뷰를 원본과 정확히 같은 말투로 40자 이내로 간단히 요약해주세요:
                - 제품의 주요 특징과 실제 사용 경험 중심
                - 배송/포장 관련 내용 제외
                - 장단점 포함
                - 구체적인 수치나 비교 정보 유지
                - 원본 리뷰의 어투 보존

                원본 리뷰: {review['text']}
                """)
            ])
            
            chat_05 = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.5,  # 어투 유지를 위해 적당한 temperature 설정
                api_key=os.getenv("OPENAI_API_KEY")
            )
            
            # summary_result = await (summarize_prompt | chat).ainvoke({})
            summary_result = (summarize_prompt | chat_05).invoke({})
            summary_reviews.append({
                "original": review,
                "summary": summary_result.content,
                "index": i + 1
            })

        # 요약된 리뷰들로 텍스트 구성
        review_texts = "\n\n".join([
            f"리뷰 {review['index']}:\n{review['summary']}"
            for review in summary_reviews
        ])

        # 2. 핵심 요약 포인트 추출
        review_type = "장점" if sentiment_type == "긍정" else "단점"
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""태블릿 리뷰 분석 전문가로서, 주요 {review_type}을 짧은 키워드로 추출해주세요.
            각 키워드는 3-5단어 이내의 간결한 구로 표현하고, 이모지나 아이콘을 사용하지 마세요."""),
            ("human", f"""다음은 태블릿 전자제품에 대한 {sentiment_type} 리뷰들입니다.
            가장 자주 언급되는 핵심 포인트 4-5개를 키워드 형태로 추출해주세요.
            
            각 키워드는:
            - 3-5단어 이내의 명사구나 짧은 구문으로 작성
            - 구체적인 제품 특성에 집중 (예: "배터리 오래감", "USB-C라서 너무 편함")
            
            {review_texts}
            
            다음과 같은 결과물을 원합니다:
            장점인 경우:
            - 디자인 진짜 예뻐요
            - 영상 볼 때 진짜 최고
            - 배터리 오래가요
            - USB-C라서 너무 편함
            
            단점인 경우:
            - 애플펜슬 1세대만 되는 거 실화?
            - 가격이 너무 비싸졌어요
            - 주사율이 60Hz라 아쉬움
            - 애매한 포지션...
                        
            위 예시처럼 결과를 생성해주되, 실제 리뷰 내용을 기반으로 키워드를 추출해주세요.
            원하는 형식:
            - 키워드1
            - 키워드2 
            - 키워드3
            - 키워드4
            """)
        ])

        # 3. 대표 리뷰 선정
        review_prompt = ChatPromptTemplate.from_messages([
            ("system", "태블릿 리뷰 분석 전문가로서, 대표적인 리뷰를 선정해주세요."),
            ("human", f"""위 리뷰들 중에서 제품의 {sentiment_type}적인 특징을 가장 잘 보여주는
            실제 리뷰 4개를 선택해주세요. 
             
            {review_texts}

            선택한 리뷰의 번호만 알려주세요.
            예시: 리뷰 1, 리뷰 3, 리뷰 5, 리뷰 8
            """)
        ])

        # ChatOpenAI 인스턴스 생성
        chat_0 = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        # 두 작업 병렬 실행
        summary_chain = summary_prompt | chat_05
        review_chain = review_prompt | chat_0
        
        summary_response, review_selection = await asyncio.gather(
            summary_chain.ainvoke({"text": review_texts}),
            review_chain.ainvoke({"text": review_texts})
        )

        # 선택된 리뷰 번호 파싱
        selected_indices = [
            int(num.strip()) - 1
            for num in review_selection.content.replace('리뷰', '').split(',')
        ]

        # 포인트 파싱
        key_points = [
            point.strip('- ').strip()
            for point in summary_response.content.split('\n')
            if point.strip().startswith('-')
        ]

        return {
            "key_points": key_points,
            "selected_reviews": [
                {
                    "text": summary_reviews[idx]["summary"],  # 요약된 텍스트 사용
                    "platform": summary_reviews[idx]["original"]["platform"]
                }
                for idx in selected_indices
            ]
        }


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

    
    # from app.agents.tablet_reviews_db.review_db_manager import ReviewDBManager
    # db_path = r'C:\Users\USER\Desktop\inner\SmartPick\git\smartpick-backend\app\agents\tablet_reviews_db'
    # db_manager = ReviewDBManager(db_path)
    # product_name = 'Apple iPad Pro 11 3세대'
    # product_reviews = db_manager.get_reviews_by_product(product_name)
    # count= 10
    # reviews=positive_reviews
    # selected_positive = scored_reviews[:count]

    # reviews=negative_reviews
    # selected_negative = scored_reviews[:count]

    # sentiment_type = "긍정"
    # sentiment_type = "부정"

    # reviews = selected_positive
    # reviews = selected_negative

