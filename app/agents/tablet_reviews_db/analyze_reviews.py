import asyncio
import os
from datetime import datetime
from review_db_manager import ReviewDBManager
import pandas as pd

async def analyze_and_save_reviews():
    """모든 제품의 리뷰를 분석하고 결과를 저장하는 스크립트"""
    
    # 시작 시간 기록
    start_time = datetime.now()
    print(f"리뷰 분석 시작: {start_time}")
    
    # DB 매니저 초기화
    # db_path = os.getenv("REVIEW_DB_PATH", "tablet_reviews_db")
    db_path = r'C:\Users\USER\Desktop\inner\SmartPick\git\smartpick-backend\app\agents\tablet_reviews_db'
    print(db_path)
    db_manager = ReviewDBManager(db_path)
    
    try:
        # 1. 전체 제품 목록 가져오기
        products = db_manager.get_all_products()
        print(f"\n총 {len(products)}개 제품의 리뷰를 분석합니다.")
        
        # 2. 각 제품별 분석 수행
        for idx, product in enumerate(products, 1):
            print(f"\n[{idx}/{len(products)}] {product} 분석 중...")
            
            try:
                # 리뷰 분석 및 DB 업데이트만 수행
                print("- 리뷰 분석 및 DB 업데이트 중...")
                await db_manager.update_review_analysis(product)
                print("- 완료")
            except Exception as e:
                print(f"- 분석 중 오류 발생: {str(e)}")
                
        # 3. 완료 시간 및 소요 시간 출력
        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n분석 완료!")
        print(f"시작 시간: {start_time}")
        print(f"종료 시간: {end_time}")
        print(f"총 소요 시간: {duration}")
        
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        raise

async def check_analysis_results():
    """모든 리뷰의 감성분석 및 품질 평가 상태를 확인하는 함수"""
    
    db_path = r'C:\Users\USER\Desktop\inner\SmartPick\git\smartpick-backend\app\agents\tablet_reviews_db'
    db_manager = ReviewDBManager(os.getenv('REVIEW_DB_PATH'))
    
    print("\n=== 리뷰 분석 상태 확인 ===")
    
    # 전체 제품 목록 가져오기
    products = db_manager.get_all_products()
    
    total_reviews = 0
    reviews_with_sentiment = 0
    reviews_with_quality = 0
    
    for product in products:
        print(f"\n제품명: {product}")
        
        # 제품의 모든 리뷰 가져오기
        reviews = db_manager.get_reviews_by_product(product)
        print(reviews[:5])
        product_total = len(reviews)
        product_sentiment = sum(1 for r in reviews if r.get('sentiment') is not None)
        product_quality = sum(1 for r in reviews if r.get('quality') is not None)
        
        print(f"전체 리뷰 수: {product_total}")
        print(f"감성점수 있는 리뷰: {product_sentiment} ({product_sentiment/product_total*100:.1f}%)")
        print(f"품질점수 있는 리뷰: {product_quality} ({product_quality/product_total*100:.1f}%)")
        
        if product_sentiment < product_total or product_quality < product_total:
            print("⚠️ 누락된 분석 결과가 있습니다!")
            
        total_reviews += product_total
        reviews_with_sentiment += product_sentiment
        reviews_with_quality += product_quality
    
    print("\n=== 전체 통계 ===")
    print(f"총 리뷰 수: {total_reviews}")
    print(f"감성분석 완료: {reviews_with_sentiment} ({reviews_with_sentiment/total_reviews*100:.1f}%)")
    print(f"품질평가 완료: {reviews_with_quality} ({reviews_with_quality/total_reviews*100:.1f}%)")


async def update_excel_ratings(excel_path: str, platform: str):
    db_path = r'C:\Users\USER\Desktop\inner\SmartPick\git\smartpick-backend\app\agents\tablet_reviews_db'
    db_manager = ReviewDBManager(db_path)
    
    # 엑셀 파일 읽기
    df = pd.read_excel(excel_path)
    
    # 전체 제품 목록 가져오기
    products = db_manager.get_all_products()
    
    for product in products:
        # 제품의 모든 리뷰 가져오기
        reviews = db_manager.get_reviews_by_product(product)
        # 플랫폼별 리뷰 필터링
        platform_reviews = [r for r in reviews if r.get('platform') == platform]
        
        # rating 평균 계산
        if platform_reviews:
            valid_ratings = [r.get('rating', 0) for r in platform_reviews if r.get('rating') is not None]
            if valid_ratings:
                avg_rating = round(sum(valid_ratings) / len(valid_ratings), 1)
                # 해당 제품과 플랫폼의 빈 rating 채우기
                mask = (df['product_name'] == product) & (df['platform'] == platform) & (df['rating'].isna())
                df.loc[mask, 'rating'] = avg_rating
    
    # 수정된 데이터프레임 저장
    df.to_excel(excel_path, index=False)
    # print(f"평균 rating이 반영된 파일이 저장되었습니다: {excel_path.replace('.xlsx', '_updated.xlsx')}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='태블릿 리뷰 분석 도구')
    parser.add_argument('--mode', choices=['analyze', 'check'],
                       default='check',
                       help='실행 모드 선택 (analyze: 새로 분석, check: 결과 확인)')
    
    args = parser.parse_args()
    
    if args.mode == 'analyze':
        print("전체 제품 리뷰 분석을 시작합니다...")
        asyncio.run(analyze_and_save_reviews())
    else:
        print("저장된 분석 결과를 확인합니다...")
        asyncio.run(check_analysis_results())

    # asyncio.run(update_excel_ratings(r'C:\Users\USER\Desktop\inner\SmartPick\git\smartpick-backend\app\agents\spec_documents\purchase_info_updated.xlsx', 'naver'))
