import requests
import json
import argparse
import time

# 서버 URL (기본값은 localhost)
BASE_URL = "http://localhost:8000"

def test_workflow(server_url):
    """워크플로우 API 테스트"""
    url = f"{server_url}/api/workflow"
    payload = {
        "query": "태블릿 추천해줘",
        "user_preferences": {
            "budget": 500000,
            "purpose": "영상 시청",
            "brand_preference": "상관없음"
        }
    }
    
    print(f"워크플로우 API 호출 중: {url}")
    start_time = time.time()
    response = requests.post(url, json=payload)
    elapsed_time = time.time() - start_time
    
    print(f"상태 코드: {response.status_code}")
    print(f"응답 시간: {elapsed_time:.2f}초")
    
    if response.status_code == 200:
        print(f"응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"오류: {response.text}")
    
    return response.status_code == 200

def test_question(server_url):
    """질문 API 테스트"""
    url = f"{server_url}/api/question"
    payload = {
        "question": "아이패드와 갤럭시 탭의 차이점은 무엇인가요?"
    }
    
    print(f"질문 API 호출 중: {url}")
    start_time = time.time()
    response = requests.post(url, json=payload)
    elapsed_time = time.time() - start_time
    
    print(f"상태 코드: {response.status_code}")
    print(f"응답 시간: {elapsed_time:.2f}초")
    
    if response.status_code == 200:
        print(f"응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"오류: {response.text}")
    
    return response.status_code == 200

def test_review(server_url):
    """리뷰 분석 API 테스트"""
    url = f"{server_url}/api/review"
    payload = {
        "product_id": "galaxy_tab_s9",
        "review_count": 5
    }
    
    print(f"리뷰 분석 API 호출 중: {url}")
    start_time = time.time()
    response = requests.post(url, json=payload)
    elapsed_time = time.time() - start_time
    
    print(f"상태 코드: {response.status_code}")
    print(f"응답 시간: {elapsed_time:.2f}초")
    
    if response.status_code == 200:
        print(f"응답: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"오류: {response.text}")
    
    return response.status_code == 200

def main():
    parser = argparse.ArgumentParser(description='SmartPick API 테스트')
    parser.add_argument('--url', default=BASE_URL, help='서버 URL (기본값: http://localhost:8000)')
    parser.add_argument('--test', choices=['all', 'workflow', 'question', 'review'], default='all', 
                        help='실행할 테스트 (기본값: all)')
    
    args = parser.parse_args()
    server_url = args.url
    
    print(f"SmartPick API 테스트 시작 - 서버: {server_url}")
    
    results = {}
    
    if args.test in ['all', 'workflow']:
        print("\n===== 워크플로우 API 테스트 =====")
        results['workflow'] = test_workflow(server_url)
    
    if args.test in ['all', 'question']:
        print("\n===== 질문 API 테스트 =====")
        results['question'] = test_question(server_url)
    
    if args.test in ['all', 'review']:
        print("\n===== 리뷰 분석 API 테스트 =====")
        results['review'] = test_review(server_url)
    
    print("\n===== 테스트 결과 요약 =====")
    for test_name, result in results.items():
        status = "성공" if result else "실패"
        print(f"{test_name}: {status}")

if __name__ == "__main__":
    main() 