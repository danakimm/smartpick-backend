import pandas as pd
import re
import emoji
from typing import List, Dict
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from config import OPENAI_API_KEY  

class ReviewDBManager:
    def __init__(self, persist_directory: str = "product_reviews_db"):
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY) 
        self.persist_directory = persist_directory
        
        # 기존 벡터 DB가 있으면 로드, 없으면 None
        try:
            self.vector_store = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embeddings
            )
        except:
            self.vector_store = None

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
            'platform': r['platform']  # 플랫폼 정보 추가
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
        products = set(meta['product'] for meta in results['metadatas'])
        return sorted(list(products))

    def get_reviews_by_product(self, product_name: str, limit: int = 10) -> List[Dict]:
        """특정 제품의 리뷰들을 반환합니다"""
        if not self.vector_store:
            return []

        results = self.vector_store.get(
            where={"product": product_name},
            limit=limit
        )

        reviews = []
        for i in range(len(results['documents'])):
            reviews.append({
                'text': results['documents'][i],
                'product': results['metadatas'][i]['product'],
                'price': results['metadatas'][i].get('price', float('nan')),
                'rating': results['metadatas'][i]['rating'],
                'platform': results['metadatas'][i].get('platform', '플랫폼 정보 없음')
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

    def search_reviews(self,
                       query: str,
                       filter_conditions: Dict = None,
                       similarity_threshold: float = 0.7,
                       max_results: int = 20) -> List[Dict]:
        """키워드로 리뷰를 검색합니다"""
        if not self.vector_store:
            return []

        # score 포함하여 검색
        results = self.vector_store.similarity_search_with_relevance_scores(
            query,
            k=max_results,
            filter=filter_conditions
        )

        # 유사도 임계값 기반 필터링
        filtered_results = [
            (doc, score) for doc, score in results
            if score >= similarity_threshold
        ]

        reviews = []
        for doc, score in filtered_results:
            reviews.append({
                'text': doc.page_content,
                'product': doc.metadata['product'],
                'price': doc.metadata.get('price', float('nan')),
                'rating': doc.metadata['rating'],
                'platform': doc.metadata.get('platform', '플랫폼 정보 없음'),
                'similarity_score': score
            })

        return reviews

    def get_reviews_by_criteria(self,
                              min_rating: float = None,
                              max_price: float = None,
                              brands: List[str] = None,
                              platform: str = None) -> List[Dict]:
        """특정 조건에 맞는 리뷰들을 반환합니다"""
        if not self.vector_store:
            return []

        # 필터 조건 설정
        filter_conditions = {}
        if min_rating is not None:
            filter_conditions['rating'] = {"$gte": float(min_rating)}
        if max_price is not None:
            filter_conditions['price'] = {"$lte": float(max_price)}
        if brands:
            filter_conditions['product'] = {"$in": brands}
        if platform:  # 플랫폼 필터 추가
            filter_conditions['platform'] = platform

        results = self.vector_store.get(
            where=filter_conditions
        )

        reviews = []
        for i in range(len(results['documents'])):
            review = {
                'text': results['documents'][i],
                'product': results['metadatas'][i]['product'],
                'price': results['metadatas'][i].get('price', float('nan')),
                'platform': results['metadatas'][i].get('platform', '플랫폼 정보 없음'),
                'rating': results['metadatas'][i]['rating']
            }
            reviews.append(review)

        return reviews

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

