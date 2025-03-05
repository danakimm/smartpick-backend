import asyncio
import os
from datetime import datetime
from review_db_manager import ReviewDBManager

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
    """저장된 분석 결과를 확인하는 함수"""
    
    db_path = os.getenv("REVIEW_DB_PATH", "tablet_reviews_db")
    db_path = r'C:\Users\USER\Desktop\inner\SmartPick\git\smartpick-backend\app\agents\tablet_reviews_db'
    db_manager = ReviewDBManager(db_path)
    
    # 전체 분석 결과 로드
    products = db_manager.get_all_products()

    print("\n=== 저장된 분석 결과 ===")
    for product_name, analysis in analyses.items():
        print(f"\n제품명: {product_name}")
        print(f"마지막 업데이트: {analysis.get('last_updated', '정보 없음')}")
        print(f"전체 리뷰 수: {analysis.get('total_reviews', 0)}")
        print(f"긍정 리뷰 비율: {analysis.get('positive_ratio', 0)}%")
        print(f"부정 리뷰 비율: {analysis.get('negative_ratio', 0)}%")
        
        print("\n[긍정적 요약]")
        for summary in analysis.get('positive_summaries', []):
            print(f"- {summary}")
            
        print("\n[부정적 요약]")
        for summary in analysis.get('negative_summaries', []):
            print(f"- {summary}")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='태블릿 리뷰 분석 도구')
    parser.add_argument('--mode', choices=['analyze', 'check'], 
                       default='analyze',
                       help='실행 모드 선택 (analyze: 새로 분석, check: 결과 확인)')
    
    args = parser.parse_args()
    
    if args.mode == 'analyze':
        print("전체 제품 리뷰 분석을 시작합니다...")
        asyncio.run(analyze_and_save_reviews())
    else:
        print("저장된 분석 결과를 확인합니다...")
        asyncio.run(check_analysis_results())
