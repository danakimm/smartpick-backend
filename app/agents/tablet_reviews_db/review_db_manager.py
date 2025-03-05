import os
import pandas as pd
import re
import emoji
from typing import List, Dict, Any
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from dotenv import load_dotenv
import json
from datetime import datetime
from pathlib import Path
import asyncio

load_dotenv()

class ReviewDBManager:
    def __init__(self, persist_directory: str="tablet_reviews_db"):
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
        self.persist_directory = persist_directory
        
        # 기존 벡터 DB가 있으면 로드, 없으면 None
        try:
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        except:
            self.vector_store = None

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.2,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    def build_vector_store(self, file_path: str) -> None:
        """제품 리뷰 데이터로 벡터 DB를 구축합니다"""
        # 파일 확장자 확인
        if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path, encoding='utf-8')
        
        # 리뷰 데이터 전처리
        reviews = []
        for _, row in df.iterrows():
            # 텍스트 전처리
            text = str(row['review_text'])
            text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로
            text = emoji.replace_emoji(text, '')  # 이모지 제거
            text = text.strip()
            
            # 성의없는 리뷰 필터링
            if self._is_valid_review(text):
                reviews.append({
                    'text': text,
                    'product': row['product_name'],
                    'price': float(row['price']),
                    'rating': float(row['rating']),
                    'platform': row.get('platform', '플랫폼 정보 없음')  # 플랫폼 정보 추가
                })
        
        total_reviews = len(reviews)
        print(f"전처리 완료: 총 {total_reviews}개의 유효한 리뷰")

        # 기존 DB 확인
        existing_reviews = set()
        if self.vector_store:
            results = self.vector_store.get()
            existing_reviews = {doc for doc in results['documents']}
            print(f"기존 DB에서 {len(existing_reviews)}개의 리뷰를 발견했습니다.")
        
        # 중복 제거를 위해 새로운 리뷰만 필터링
        new_reviews = []
        for r in reviews:
            if r['text'] not in existing_reviews:
                new_reviews.append(r)
        
        print(f"추가될 새로운 리뷰: {len(new_reviews)}개")
        
        if not new_reviews:
            print("추가할 새로운 리뷰가 없습니다.")
            return
        
        # 벡터 DB 생성 (진행률 표시 추가)
        texts = [r['text'] for r in new_reviews]
        metadatas = [{
            'product': r['product'],
            'price': float(r['price']),
            'rating': float(r['rating']),
            'platform': r['platform'],
            'sentiment': r.get('sentiment', None),  # 감성 분석 결과 추가
            'quality': r.get('quality', None)       # 품질 분석 결과 추가
        } for r in new_reviews]
        
        batch_size = 100  # 한 번에 처리할 리뷰 수
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            
            if self.vector_store is None:  # DB가 없는 경우에만 새로 생성
                self.vector_store = Chroma.from_texts(
                    texts=batch_texts,
                    embedding=self.embeddings,
                    metadatas=batch_metadatas,
                    persist_directory=self.persist_directory
                )
            else:  # DB가 있으면 추가
                self.vector_store.add_texts(
                    texts=batch_texts,
                    metadatas=batch_metadatas
                )
            
            progress = min((i + batch_size) / len(texts) * 100, 100)
            print(f"진행률: {progress:.1f}% ({i + len(batch_texts)}/{len(texts)})")
        
        print(f"벡터 DB 구축 완료: {len(texts)}개의 리뷰가 추가되었습니다.")

    def _is_valid_review(self, text: str) -> bool:
        """리뷰의 유효성을 검사합니다"""
        if len(text) < 10:  # 너무 짧은 리뷰
            return False
            
        # 성의없는 리뷰 패턴
        low_quality_patterns = [
            r'^[ㄱ-ㅎㅏ-ㅣ]+$',  # 자음/모음만 있는 경우
            r'^[.!?]+$',  # 문장부호만 있는 경우
            r'^(좋아요|굿|최고|별로|싫어요|보통|그냥)$',  # 한 단어 리뷰
            r'^[ㅋㅎㅉㅃㅌ]+$',  # ㅋㅋㅋ, ㅎㅎㅎ 등
        ]
        
        # 패턴 매칭
        for pattern in low_quality_patterns:
            if re.match(pattern, text):
                return False
                
        # 중복 문자 체크 (예: 굿굿굿굿굿)
        if re.search(r'(.)\1{3,}', text):
            return False
            
        # 실제 내용이 있는 단어 수 체크
        meaningful_words = [w for w in text.split() if len(w) > 1]
        if len(meaningful_words) < 3:  # 의미있는 단어가 3개 미만
            return False
            
        return True

    def get_all_products(self) -> List[str]:
        """저장된 모든 제품 목록을 반환합니다"""
        if not self.vector_store:
            return []
        results = self.vector_store.get()

        # 제품별 리뷰 수 계산
        product_review_counts = {}
        for meta in results['metadatas']:
            product = meta['product']
            product_review_counts[product] = product_review_counts.get(product, 0) + 1
        
        # 리뷰 수 기준으로 정렬 (내림차순)
        sorted_products = sorted(
            product_review_counts.keys(),
            key=lambda x: product_review_counts[x],
            reverse=False
        )
        return sorted_products

    def get_reviews_by_product(self, product_name: str) -> List[Dict]:
        """특정 제품의 리뷰들을 반환합니다"""
        if not self.vector_store:
            return []

        results = self.vector_store.get(
            where={"product": product_name}
        )

        reviews = []
        for i in range(len(results['documents'])):
            reviews.append({
                'text': results['documents'][i],
                'product': results['metadatas'][i]['product'],
                'price': results['metadatas'][i].get('price', float('nan')),
                'rating': results['metadatas'][i]['rating'],
                'platform': results['metadatas'][i].get('platform', '플랫폼 정보 없음'),
                'sentiment': results['metadatas'][i].get('sentiment', None),
                'quality': results['metadatas'][i].get('quality', None)
            })

        return reviews

    def get_db_stats(self) -> Dict:
        """DB 통계 정보를 반환합니다"""
        if not self.vector_store:
            return {"error": "DB가 구축되지 않았습니다."}

        results = self.vector_store.get()
        products = set(meta['product'] for meta in results['metadatas'])

        return {
            "총 리뷰 수": len(results['documents']),
            "총 제품 수": len(products),
            "제품 목록": sorted(list(products))
        }

    def search_reviews(
        self, 
        query: str, 
        similarity_threshold: float = 0.7, 
        max_results: int = 20,
        exact_product_match: bool = False
    ) -> List[Dict[str, Any]]:
        """
        리뷰 검색 메서드
        
        Args:
            query: 검색 쿼리 또는 제품명
            similarity_threshold: 유사도 임계값
            max_results: 최대 결과 수
            exact_product_match: 정확한 제품명 일치 검색 여부
        """
        if not self.vector_store:
            return []
        
        try:
            # 정확한 제품명 일치 검색인 경우
            if exact_product_match:
                # 제품명으로 직접 필터링하여 검색
                results = self.vector_store.get(
                    where={"product": query},
                    limit=max_results
                )
                
                reviews = []
                for i in range(len(results['documents'])):
                    review_data = {
                        'text': results['documents'][i],
                        'product': results['metadatas'][i].get('product', ''),
                        'rating': results['metadatas'][i].get('rating', 0),
                        'platform': results['metadatas'][i].get('platform', ''),
                        'similarity_score': 1.0  # 정확히 일치하므로 최대 유사도
                    }
                    reviews.append(review_data)
                
                return reviews
            
            # 유사도 기반 검색인 경우
            else:
                results = self.vector_store.similarity_search_with_relevance_scores(
                    query,
                    k=max_results * 2  # 필터링 후 충분한 결과를 얻기 위해 더 많은 결과 검색
                )
                
                # 유사도 임계값 기반 필터링 (높을수록 더 유사)
                filtered_results = [
                    (doc, score) for doc, score in results
                    if score >= similarity_threshold
                ]
                
                reviews = []
                for doc, score in filtered_results[:max_results]:  # 최대 결과 수 제한
                    review_data = {
                        'text': doc.page_content,
                        'product': doc.metadata.get('product', ''),
                        'rating': doc.metadata.get('rating', 0),
                        'platform': doc.metadata.get('platform', ''),
                        'similarity_score': score
                    }
                    reviews.append(review_data)
                
                return reviews
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error searching for reviews: {str(e)}")
            return []

    async def _analyze_reviews_batch(self, reviews: List[Dict]) -> List[Dict]:
        """리뷰들을 배치로 분석하여 감성과 품질을 분류"""
        batch_size = 20
        analyzed_reviews = []
        
        for i in range(0, len(reviews), batch_size):
            print(i, len(reviews))
            batch = reviews[i:i+batch_size]
            batch_texts = "\n\n".join([
                f"리뷰 {j+1}:\n{review['text']}"
                for j, review in enumerate(batch)
            ])
            
            prompt = f"""다음 리뷰들의 감성(긍정/부정)과 품질을 분석해주세요.
            
            품질 기준:
            - high: 구체적인 사용 경험과 장단점이 잘 설명된 리뷰
            - medium: 기본적인 평가는 있으나 세부 내용이 부족한 리뷰
            - low: 단순 감정 표현이나 짧은 코멘트만 있는 리뷰
            
            각 리뷰에 대해 다음 형식으로 답해주세요:
            리뷰 1: [감성] positive/negative, [품질] high/medium/low
            
            {batch_texts}
            
            분석:
            리뷰 1: 
            리뷰 2: 
            ...
            """
            
            response = await self.llm.ainvoke(prompt)
            analysis_results = self._parse_analysis_response(response.content)
            
            # 분석 결과를 원본 리뷰와 합치기
            for review, analysis in zip(batch, analysis_results):
                review_copy = review.copy()
                review_copy["sentiment"] = analysis["sentiment"]
                review_copy["quality"] = analysis["quality"]
                print(review_copy)
                analyzed_reviews.append(review_copy)
                
        return analyzed_reviews
            
    def _parse_analysis_response(self, response: str) -> List[Dict]:
        """LLM 응답에서 감성과 품질 분석 결과를 파싱"""
        results = []
        for line in response.split('\n'):
            if ':' in line and '[' in line:
                try:
                    sentiment = re.search(r'\[감성\]\s*(positive|negative)', line)
                    quality = re.search(r'\[품질\]\s*(high|medium|low)', line)
                    
                    if sentiment and quality:
                        results.append({
                            "sentiment": sentiment.group(1),
                            "quality": quality.group(1)
                        })
                except:
                    continue
        return results

    async def get_product_analysis_stats(self, product_name: str) -> Dict:
        """제품의 리뷰 통계를 계산"""
        reviews = self.get_reviews_by_product(product_name)
        if not reviews:
            return {
                "product_name": product_name,
                "error": "리뷰를 찾을 수 없습니다."
            }
        
        # 긍정/부정 리뷰 수 계산
        positive_reviews = [r for r in reviews if r.get('sentiment') == 'positive']
        negative_reviews = [r for r in reviews if r.get('sentiment') == 'negative']
        
        total_reviews = len(reviews)
        positive_ratio = (len(positive_reviews) / total_reviews) * 100
        negative_ratio = (len(negative_reviews) / total_reviews) * 100
        
        # 대표 리뷰 선정
        selected_positive = self._select_representative_reviews(positive_reviews, count=10)
        selected_negative = self._select_representative_reviews(negative_reviews, count=10)
        
        return {
            "product_name": product_name,
            "total_reviews": total_reviews,
            "positive_percentage": round(positive_ratio, 1),
            "negative_percentage": round(negative_ratio, 1),
            "positive_reviews": [
                {
                    "text": review["text"],
                    "platform": review["platform"],
                    "quality": review["quality"]
                }
                for review in selected_positive
            ],
            "negative_reviews": [
                {
                    "text": review["text"],
                    "platform": review["platform"],
                    "quality": review["quality"]
                }
                for review in selected_negative
            ]
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
            
            # 배송 관련 내용 감점은 유지
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
        
        review_texts = "\n\n".join([
            f"리뷰 {i+1}:\n{review['text']}"
            for i, review in enumerate(reviews[:10])  # 상위 10개 리뷰만 사용
        ])
        
        # 1. 핵심 요약 포인트 추출
        summary_prompt = f"""다음은 제품에 대한 {sentiment_type} 리뷰들입니다.
        가장 자주 언급되는 핵심 포인트 4개를 추출해주세요.
        각 포인트는 실제 리뷰에서 사용된 표현을 최대한 살려서 한 줄로 작성해주세요.
        
        {review_texts}
        
        형식:
        - 포인트1
        - 포인트2
        - 포인트3
        - 포인트4
        """
        
        # 2. 대표 리뷰 선정
        review_prompt = f"""위 리뷰들 중에서 제품의 {sentiment_type}적인 특징을 가장 잘 보여주는
        실제 리뷰 4개를 선택해주세요. 너무 길지 않고 구체적인 리뷰를 선택해주세요.
        
        선택한 리뷰의 번호만 알려주세요.
        예시: 리뷰 1, 리뷰 3, 리뷰 5, 리뷰 8
        """
        
        # 두 작업 병렬 실행
        summary_response, review_selection = await asyncio.gather(
            self.llm.ainvoke(summary_prompt),
            self.llm.ainvoke(review_prompt)
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
                    "text": reviews[idx]['text'],
                    "platform": reviews[idx]['platform']
                }
                for idx in selected_indices
            ]
        }
                    
    async def update_review_analysis(self, product_name: str) -> None:
        """리뷰 분석 결과를 DB에 업데이트"""
        # 제품의 모든 리뷰 가져오기
        results = self.vector_store.get(
            where={"product": product_name}
        )
        if not results['ids']:
            return
        
        # 리뷰 데이터 구성
        reviews = []
        for i in range(len(results['ids'])):
            reviews.append({
                'id': results['ids'][i],
                'text': results['documents'][i],
                'product': results['metadatas'][i]['product'],
                'price': results['metadatas'][i].get('price', 0.0),
                'rating': results['metadatas'][i].get('rating', 0.0),
                'platform': results['metadatas'][i].get('platform', '플랫폼 정보 없음')
            })
        
        # 리뷰 분석
        analyzed_reviews = await self._analyze_reviews_batch(reviews)
        
        # DB 업데이트
        # 1. 기존 리뷰 삭제
        self.vector_store.delete(
            ids=results['ids']
        )
        
        # 2. 분석된 리뷰 다시 추가
        texts = [r['text'] for r in analyzed_reviews]
        metadatas = [{
            'product': r['product'],
            'price': float(r['price']),
            'rating': float(r['rating']),
            'platform': r['platform'],
            'sentiment': r['sentiment'],
            'quality': r['quality']
        } for r in analyzed_reviews]
        
        # 3. 벡터 DB에 다시 추가
        self.vector_store.add_texts(
            texts=texts,
            metadatas=metadatas,
            ids=results['ids']  # 기존 ID 재사용
        )

if __name__ == "__main__":
    db_manager = ReviewDBManager('tablet_reviews_db')
    # db_manager.build_vector_store(r"C:\Users\USER\Desktop\inner\SmartPick\crawling\csv_files\final\tablet_reviews_no_duplicates.xlsx")

    # 1. DB 통계 확인
    stats = db_manager.get_db_stats()
    print("DB 통계:", stats)

    # 2. (조회, 일치) 전체 제품 목록 조회
    products = db_manager.get_all_products()
    print("제품 목록:", products)

    # 3. (조회, 일치) 특정 제품의 리뷰 조회
    product_reviews = db_manager.get_reviews_by_product("Apple iPad Air 10.9 5세대", limit=5)
    for review in product_reviews:
        print(f"리뷰: {review['text']}")
        print(f"평점: {review['rating']}")
        print("---")

    # 4. (조회, 일치) 조건별 리뷰 필터링 조회
    filtered_reviews = db_manager.get_reviews_by_criteria(
        min_rating=4.0
    )
    print(f"\n필터링된 리뷰 수: {len(filtered_reviews)}")

    # 5. (검색, 유사도) 키워드로 리뷰 검색
    search_results = db_manager.search_reviews(
        query="배터리 성능이 좋아요",
        similarity_threshold=0.7,
        max_results=5
    )
    print("\n유사한 리뷰들:")
    for review in search_results:
        print(review)

    # 쿠팡 리뷰만 조회
    coupang_reviews = db_manager.get_reviews_by_criteria(platform="coupang")
    print(f"쿠팡 리뷰 수: {len(coupang_reviews)}")
    
    # 리뷰 샘플 출력
    for review in coupang_reviews[:5]:
        print(f"\n제품: {review['product']}")
        print(f"리뷰: {review['text']}")
        print(f"평점: {review['rating']}")
        print("---")



    for product in products:
        print(len(db_manager.get_reviews_by_product(product, limit=10000)))