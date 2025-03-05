from konlpy.tag import Okt
import h5py
import json
import os
import numpy as np
from collections import defaultdict
import hashlib
from konlpy.tag import Okt
from app.agents.report_agent_module.bsae_reporter import CacheManager
class KeywordExtractor:
    """
    텍스트에서 키워드를 추출하고 분류하는 클래스
    """
    def __init__(self):
        self.okt = Okt()
        # 기능(Features) 키워드
        self.features = [
            "성능", "배터리", "화면", "무게", "휴대성", "저장용량", "속도", "램", "칩셋", "화질",
            "해상도", "주사율", "발열", "멀티태스킹", "충전", "키보드", "카메라", "스피커", "음질", "밝기",
            "디자인", "내구성", "방수"
        ]

        # 사용 용도(Usage) 키워드
        self.usage = [
            "공부", "필기", "그림", "영상", "영화", "게임", "웹서핑", "독서", "전자책", "웹툰","드로잉",
            "애니메이션", "프로그래밍", "인터넷",
            "인강", "유튜브", "넷플릭스", "OTT", "카카오톡", "문서", "어린이", "영상통화", "학습", "노트북"
        ]

        # 브랜드/플랫폼(Brands/Platform) 키워드
        self.brands = [
            "아이패드", "갤럭시탭", "애플", "삼성", "레노버", "샤오미", "화웨이", "LG", "서피스",
            "안드로이드", "iOS"
        ]

        # 기타(Others) 키워드
        self.others = [
            "가성비", "가격", "S펜", "애플펜슬", "생태계", "연동", "호환성", "업데이트",
            "AS", "Wi-Fi", "LTE", "SD카드", "USB-C", "필압", "필기감", "인치", "크기", "메모리", "렉", "터치"
        ]

        # 위 네 리스트를 합쳐 총 80개(중복 검사 필요)
        self.keywords_top80 = self.features + self.usage + self.brands + self.others

        # Tier별 키워드 (중요도/빈도 순으로 구성했다고 가정)
        self.keywords_top20 = [
            "성능", "배터리", "화면", "가격", "가성비", "무게", "휴대성", "저장용량",
            "공부", "필기", "그림", "영상", "게임", "아이패드", "갤럭시탭", "삼성",
            "애플", "영화", "유튜브", "펜"
        ]

        # Top 40 = Top 20 + 추가 20
        self.keywords_top40 = self.keywords_top20 + [
            "화질", "해상도", "주사율", "램", "칩셋", "발열", "멀티태스킹", "충전",
            "키보드", "디스플레이", "디자인", "S펜", "애플펜슬", "레노버", "샤오미",
            "서피스", "안드로이드", "iOS", "넷플릭스", "인강"
        ]

        # Top 80 = Top 40 + 추가 40
        self.keywords_top80 = self.keywords_top40 + [
            "화웨이", "LG", "웹서핑", "독서", "전자책", "웹툰", "카카오톡", "내구성",
            "연동", "SD카드", "USB-C", "스피커", "생태계", "속도", "밝기", "호환성",
            "업데이트", "노트북", "LTE", "OTT", "카메라", "인치", "AMOLED", "IPS",
            "크기", "메모리", "음질", "렉", "터치", "필압", "이북", "AS", "Wi-Fi",
            "방수", "필기감", "강의", "어린이", "문서", "학습", "영상통화"
        ]

        # (참고) 카테고리별로도 정리해두면 추후 확장성↑
        self.keywords_by_category = {
            "features": self.features,
            "usage": self.usage,
            "brands": self.brands,
            "others": self.others
        }
    
    def extract_keywords(self, text):
        """
        텍스트에서 키워드 추출
        
        Args:
            text (str): 키워드를 추출할 텍스트
            
        Returns:
            list: 추출된 키워드 목록
        """
        tokens = self.okt.pos(text, stem=True)
        keywords = [word for word, pos in tokens if pos in ('Noun', 'Verb', 'Adjective')]
        return keywords
    
    def match_category(self, text_or_keywords):
        """
        텍스트나 키워드 목록을 카테고리별로 매칭
        
        Args:
            text_or_keywords (str or list): 텍스트 또는 키워드 목록
            
        Returns:
            dict: 카테고리별 키워드 목록
        """
        # 입력이 문자열인 경우 키워드 추출
        if isinstance(text_or_keywords, str):
            keywords = self.extract_keywords(text_or_keywords)
        else:
            keywords = text_or_keywords
            
        category = {
            "features": [],
            "usage": [],
            "brands": [],
            "others": []
        }
        
        for kw in keywords:
            if kw in self.features:
                category["features"].append(kw)
            elif kw in self.usage:
                category["usage"].append(kw)
            elif kw in self.brands:
                category["brands"].append(kw)
            elif kw in self.others:
                category["others"].append(kw)
                
        return category
    
    def match_tier(self, keywords):
        """
        키워드를 티어별로 매칭
        
        Args:
            keywords (list): 매칭할 키워드 목록
            
        Returns:
            dict: 티어별 키워드 목록
        """
        tier = {}
        keywords_top80_row = []
        
        for kw in keywords:
            if kw in self.keywords_top80:
                keywords_top80_row.append(kw)
                
        tier["top80"] = keywords_top80_row.copy()
        
        # Top40에 없는 키워드 제거
        iterser = list(set(self.keywords_top80) - set(self.keywords_top40))
        keywords_top40_row = keywords_top80_row.copy()
        for kw in iterser:
            if kw in keywords_top40_row:
                keywords_top40_row.remove(kw)
                
        tier["top40"] = keywords_top40_row.copy()
        
        # Top20에 없는 키워드 제거
        iterser = list(set(self.keywords_top40) - set(self.keywords_top20))
        keywords_top20_row = keywords_top40_row.copy()
        for kw in iterser:
            if kw in keywords_top20_row:
                keywords_top20_row.remove(kw)
                
        tier["top20"] = keywords_top20_row.copy()
        return tier
    
    def get_keyword_weight(self, keyword):
        """
        키워드의 가중치 반환 (카테고리 기반 + 티어 기반)
        
        Args:
            keyword (str): 가중치를 계산할 키워드
            
        Returns:
            int: 키워드 가중치
        """
        weight = 0
        
        # 카테고리 기반 가중치 (모든 카테고리에 동일한 가중치 3 적용)
        if (keyword in self.features or keyword in self.usage or 
            keyword in self.brands or keyword in self.others):
            weight += 3
        
        # 티어 기반 가중치 (기존대로 유지)
        if keyword in self.keywords_top20:
            weight += 3
        elif keyword in self.keywords_top40:
            weight += 2
        elif keyword in self.keywords_top80:
            weight += 1
        
        return max(weight, 1)  # 최소 가중치는 1 (어떤 카테고리에도 속하지 않는 키워드)
    
    def print_keyword_info(self):
        """키워드 정보 출력"""
        print("===== Top 20 키워드 =====")
        print(self.keywords_top20)
        print("\n===== Top 40 키워드 =====")
        print(self.keywords_top40)
        print("\n===== Top 80 키워드 =====")
        print(self.keywords_top80)
        print("\n===== 카테고리별 키워드 =====")
        for category, kw_list in self.keywords_by_category.items():
            print(f"[{category}] : {kw_list}")


class IndexStorage:
    """
    H5 파일을 사용한 역인덱스 저장소
    """
    def __init__(self, file_path):
        """
        파일 경로를 입력받아 초기화하고, 파일이 없으면 생성함
        
        Args:
            file_path (str): HDF5 파일의 경로 (확장자 포함)
        """
        self.file_path = file_path
        
        # 확장자가 h5인지 확인
        if not file_path.endswith('.h5'):
            raise ValueError("파일 확장자는 반드시 .h5여야 합니다.")
            
        # 파일 열기 또는 생성
        self._open_file()
        
        # 기본 그룹 생성 확인
        self._ensure_groups()
    
    def _open_file(self, mode='a'):
        """파일을 지정된 모드로 열기"""
        if os.path.exists(self.file_path):
            self.file = h5py.File(self.file_path, mode)
        else:
            self.file = h5py.File(self.file_path, 'w')
    
    def _ensure_groups(self):
        """기본 그룹 존재 확인 및 생성"""
        if 'queries' not in self.file:
            self.file.create_group('queries')
        if 'keywords' not in self.file:
            self.file.create_group('keywords')
    
    def close(self):
        """H5 파일 닫기"""
        if hasattr(self, 'file') and self.file:
            self.file.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _encode_keyword(self, keyword):
        """키워드를 안전한 형식으로 인코딩"""
        return keyword.encode('utf-8').hex()
    
    def _decode_keyword(self, encoded):
        """인코딩된 키워드를 원래 형식으로 복원"""
        return bytes.fromhex(encoded).decode('utf-8')
    
    def add_query(self, query_id, query_data):
        """
        쿼리 정보 저장
        
        Args:
            query_id (str): 쿼리 ID
            query_data (dict): 저장할 쿼리 데이터
                {
                    'query_text': str,
                    'keywords': list,
                    'category': dict,
                    'tier': dict,
                    ...
                }
        
        Returns:
            bool: 성공 여부
        """
        query_id = str(query_id)
        
        # 기존 쿼리 삭제 (덮어쓰기)
        if query_id in self.file['queries']:
            del self.file['queries'][query_id]
            
        # 쿼리 그룹 생성
        query_group = self.file['queries'].create_group(query_id)
        
        # 쿼리 정보 저장
        for key, value in query_data.items():
            if isinstance(value, (str, int, float, bool)):
                query_group.attrs[key] = value
            else:
                # 복잡한 구조는 JSON으로 저장
                query_group.attrs[f"{key}_json"] = json.dumps(value)
        
        self.file.flush()
        return True
    def open_if_closed(self, mode='a'):
        """파일이 닫혔다면 다시 여는 메서드"""
        # self.file이 존재하지 않거나, 닫힌 경우 재오픈
        if not hasattr(self, 'file') or self.file is None or self.file.id.valid!=1:
            self._open_file(mode)
    
    def add_keyword_to_index(self, keyword, query_id):
        self.open_if_closed()
        """
        역인덱스에 키워드-쿼리 연결 추가
        
        Args:
            keyword (str): 키워드
            query_id (str): 쿼리 ID
            
        Returns:
            bool: 성공 여부
        """
        if not keyword:
            return False
            
        query_id = str(query_id)
        encoded_key = self._encode_keyword(keyword)
        
        # 키워드 데이터셋이 없으면 생성
        if encoded_key not in self.file['keywords']:
            keyword_dataset = self.file['keywords'].create_dataset(
                encoded_key,
                data=np.array([query_id], dtype='S100'),
                maxshape=(None,),
                chunks=True
            )
            keyword_dataset.attrs['keyword'] = keyword
        else:
            # 이미 있으면 쿼리 ID 추가 (중복 방지)
            dataset = self.file['keywords'][encoded_key]
            existing_ids = [qid.decode('utf-8') for qid in dataset[:]]
            
            if query_id not in existing_ids:
                existing_ids.append(query_id)
                dataset.resize((len(existing_ids),))
                dataset[:] = np.array(existing_ids, dtype='S100')
        
        self.file.flush()
        return True
    
    def get_queries_by_keyword(self, keyword):
        self.open_if_closed()
        """
        키워드로 연결된 쿼리 ID 목록 가져오기
        
        Args:
            keyword (str): 검색할 키워드
            
        Returns:
            list: 쿼리 ID 목록
        """
        encoded_key = self._encode_keyword(keyword)
        
        if encoded_key not in self.file['keywords']:
            return []
            
        dataset = self.file['keywords'][encoded_key]
        return [qid.decode('utf-8') for qid in dataset[:]]
    
    def get_query_info(self, query_id):
        """
        쿼리 ID로 쿼리 정보 가져오기
        
        Args:
            query_id (str): 쿼리 ID
            
        Returns:
            dict: 쿼리 정보 또는 None
        """
        query_id = str(query_id)
        
        if query_id not in self.file['queries']:
            return None
            
        query_group = self.file['queries'][query_id]
        query_info = {'query_id': query_id}
        
        # 속성 정보 수집
        for attr_name, attr_value in query_group.attrs.items():
            if attr_name.endswith('_json'):
                # JSON 문자열 파싱
                key = attr_name[:-5]  # '_json' 제거
                query_info[key] = json.loads(attr_value)
            else:
                query_info[attr_name] = attr_value
                
        return query_info
    
    def get_all_queries(self):
        """저장된 모든 쿼리 ID 목록 반환"""
        return list(self.file['queries'].keys())
    
    def get_all_keywords(self):
        """인덱싱된 모든 키워드 목록 반환"""
        keywords = []
        for encoded_key in self.file['keywords']:
            dataset = self.file['keywords'][encoded_key]
            if 'keyword' in dataset.attrs:
                keywords.append(dataset.attrs['keyword'])
        return keywords


class QueryMatcher:
    """
    키워드 기반 쿼리 매칭 알고리즘 클래스
    """
    def __init__(self, keyword_extractor, index_storage):
        """
        초기화
        
        Args:
            keyword_extractor (KeywordExtractor): 키워드 추출 객체
            index_storage (IndexStorage): 인덱스 저장소 객체
        """
        self.keyword_extractor = keyword_extractor
        self.index_storage = index_storage
    
    def find_matching_queries(self, text_or_keywords, min_score=0.5, max_results=3):
        """
        텍스트 또는 키워드 목록으로 매칭되는 쿼리 검색
        
        Args:
            text_or_keywords (str or list): 검색할 텍스트 또는 키워드 목록
            min_score (float): 최소 매치 점수 (0.0 ~ 1.0)
            max_results (int): 반환할 최대 결과 수
            
        Returns:
            list: 매치된 쿼리 정보 목록 (매치 점수로 정렬됨)
        """
        # 입력이 문자열인 경우 키워드 추출
        if isinstance(text_or_keywords, str):
            keywords = self.keyword_extractor.extract_keywords(text_or_keywords)
        else:
            keywords = text_or_keywords
            
        if not keywords:
            return []
            
        # 키워드별 매칭 쿼리 검색
        query_matches = defaultdict(int)
        keywords_set = set(keywords)  # 중복 제거
        
        # 총 가중치 계산
        total_weight = sum(self.keyword_extractor.get_keyword_weight(kw) for kw in keywords_set)
        
        # 각 키워드에 대한 역인덱스 검색
        for keyword in keywords_set:
            # 키워드 가중치 계산
            weight = self.keyword_extractor.get_keyword_weight(keyword)
            
            # 키워드에 매칭되는 쿼리 검색
            query_ids = self.index_storage.get_queries_by_keyword(keyword)
            
            # 매칭 점수 누적
            for query_id in query_ids:
                query_matches[query_id] += weight
        
        if not query_matches:
            return []
            
        # 매치 결과 정리
        matches = []
        for query_id, match_weight in query_matches.items():
            match_score = match_weight / total_weight if total_weight > 0 else 0
            
            if match_score >= min_score:
                query_info = self.index_storage.get_query_info(query_id)
                if query_info:
                    query_info['match_score'] = match_score
                    matches.append(query_info)
        
        # 매치 점수로 정렬 및 결과 수 제한
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        if len(matches) > 1:
            top_score = matches[0]['match_score']
            second_score = matches[1]['match_score']
            
            # 최고 점수가 충분히 높고(0.8 이상) 또는 두 번째 점수와의 차이가 충분히 큰 경우(0.2 이상)
            if top_score >= 0.75 or (top_score - second_score >= 0.15):
                return [matches[0]]  # 최고 점수만 반환
            elif top_score < 0.6:  # 최고 점수가 충분히 높지 않고 차이도 미미하면
                return []  # 충분히 확실하지 않으면 결과 반환하지 않음
            # 결과가 하나만 있는 경우나, 상위 결과들이 충분히 높은 점수를 가진 경우
        return matches[:max_results]    



class KeywordQueryManager:
    """
    키워드 기반 쿼리 인덱싱 및 검색 통합 관리 클래스
    """
    def __init__(self, file_path):
        """
        초기화
        
        Args:
            file_path (str): HDF5 파일 경로
        """
        self.keyword_extractor = KeywordExtractor()
        self.index_storage = IndexStorage(file_path)
        self.query_matcher = QueryMatcher(self.keyword_extractor, self.index_storage)
    
    def add_query(self, query_text, query_id=None):
        """
        쿼리 추가 및 키워드 인덱싱
        
        Args:
            query_text (str): 쿼리 텍스트
            query_id (str, optional): 쿼리 ID (없으면 자동 생성)
            
        Returns:
            str: 생성된 쿼리 ID
        """
        # 쿼리 ID 생성 (제공되지 않은 경우)
        if not query_id:
            query_id = hashlib.sha256(query_text.encode('utf-8')).hexdigest()[:12]
        
        query_id = str(query_id)
        
        # 키워드 분석
        keywords = self.keyword_extractor.extract_keywords(query_text)
        category = self.keyword_extractor.match_category(keywords)
        tier = self.keyword_extractor.match_tier(keywords)
        
        # 쿼리 데이터 생성
        query_data = {
            'query_text': query_text,
            'keywords': keywords,
            'category': category,
            'tier': tier
        }
        
        # 쿼리 저장
        self.index_storage.add_query(query_id, query_data)
        
        # 역인덱스 업데이트
        for keyword in set(keywords):
            self.index_storage.add_keyword_to_index(keyword, query_id)
        
        return query_id
    
    def find_matching_queries(self, text, min_score=0.0, max_results=10):
        """
        텍스트와 매칭되는 쿼리 검색
        
        Args:
            text (str): 검색할 텍스트
            min_score (float): 최소 매치 점수 (0.0 ~ 1.0)
            max_results (int): 반환할 최대 결과 수
            
        Returns:
            list: 매치된 쿼리 정보 목록
        """
        return self.query_matcher.find_matching_queries(text, min_score, max_results)
    
    def get_query_info(self, query_id):
        """쿼리 ID로 쿼리 정보 조회"""
        return self.index_storage.get_query_info(query_id)
    
    def print_keyword_info(self):
        """키워드 정보 출력"""
        self.keyword_extractor.print_keyword_info()
    
    def close(self):
        """저장소 닫기"""
        self.index_storage.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class CacheKeywors:
    def __init__(self):

        # 기능(Features) 키워드
        self.features = [
            "성능", "배터리", "화면", "무게", "휴대성", "저장용량", "속도", "램", "칩셋", "화질",
            "해상도", "주사율", "발열", "멀티태스킹", "충전", "키보드", "카메라", "스피커", "음질", "밝기",
            "디자인", "내구성", "방수"
        ]

        # 사용 용도(Usage) 키워드
        self.usage = [
            "공부", "필기", "그림", "영상", "영화", "게임", "웹서핑", "독서", "전자책", "웹툰","드로잉",
            "애니메이션", "프로그래밍", "인터넷",
            "인강", "유튜브", "넷플릭스", "OTT", "카카오톡", "문서", "어린이", "영상통화", "학습", "노트북"
        ]

        # 브랜드/플랫폼(Brands/Platform) 키워드
        self.brands = [
            "아이패드", "갤럭시탭", "애플", "삼성", "레노버", "샤오미", "화웨이", "LG", "서피스",
            "안드로이드", "iOS"
        ]

        # 기타(Others) 키워드
        self.others = [
            "가성비", "가격", "S펜", "애플펜슬", "생태계", "연동", "호환성", "업데이트",
            "AS", "Wi-Fi", "LTE", "SD카드", "USB-C", "필압", "필기감", "인치", "크기", "메모리", "렉", "터치"
        ]

        # 위 네 리스트를 합쳐 총 80개(중복 검사 필요)
        self.keywords_top80 = self.features + self.usage + self.brands + self.others

        # Tier별 키워드 (중요도/빈도 순으로 구성했다고 가정)
        self.keywords_top20 = [
            "성능", "배터리", "화면", "가격", "가성비", "무게", "휴대성", "저장용량",
            "공부", "필기", "그림", "영상", "게임", "아이패드", "갤럭시탭", "삼성",
            "애플", "영화", "유튜브", "펜"
        ]

        # Top 40 = Top 20 + 추가 20
        self.keywords_top40 = self.keywords_top20 + [
            "화질", "해상도", "주사율", "램", "칩셋", "발열", "멀티태스킹", "충전",
            "키보드", "디스플레이", "디자인", "S펜", "애플펜슬", "레노버", "샤오미",
            "서피스", "안드로이드", "iOS", "넷플릭스", "인강"
        ]

        # Top 80 = Top 40 + 추가 40
        self.keywords_top80 = self.keywords_top40 + [
            "화웨이", "LG", "웹서핑", "독서", "전자책", "웹툰", "카카오톡", "내구성",
            "연동", "SD카드", "USB-C", "스피커", "생태계", "속도", "밝기", "호환성",
            "업데이트", "노트북", "LTE", "OTT", "카메라", "인치", "AMOLED", "IPS",
            "크기", "메모리", "음질", "렉", "터치", "필압", "이북", "AS", "Wi-Fi",
            "방수", "필기감", "강의", "어린이", "문서", "학습", "영상통화"
        ]

        # (참고) 카테고리별로도 정리해두면 추후 확장성↑
        self.keywords_by_category = {
            "features": self.features,
            "usage": self.usage,
            "brands": self.brands,
            "others": self.others
        }
    
    @staticmethod
    def extract_keywords(text):
        okt = Okt()
        tokens = okt.pos(text, stem=True)
        
        # 동의어 처리 추가
        keywords = [word for word, pos in tokens if pos in ('Noun', 'Verb', 'Adjective')]
        
        # 동의어 매핑 적용
        synonym_dict = {
            '그림': '드로잉',
            '드로잉': '드로잉',
            '그리기': '드로잉',
            '디지털': '디지털',
            '태블릿': '태블릿',
            '아이패드': '아이패드',
            '패드': '아이패드',
            '디스플레이': '화면',
            '화면': '화면',
            '모니터': '화면',
            '노트북': '노트북',
            '랩탭': '노트북',
            '게임': '게임',
            '게이밍': '게임',
            '아트': '드로잉',
            '스크린': '화면',
            '프로그래밍': '개발',
            '코딩': '개발',
            '작은': '소형',
            '전자책': '독서',
            '이북': '독서'
        }

        
        normalized_keywords = []
        for kw in keywords:
            if kw in synonym_dict:
                normalized_keywords.append(synonym_dict[kw])
            else:
                normalized_keywords.append(kw)
        
        return list(set(normalized_keywords))  # 중복 제거
    def print_keyword_info(self):
        print("===== Top 20 키워드 =====")
        print(self.keywords_top20)
        print("\n===== Top 40 키워드 =====")
        print(self.keywords_top40)
        print("\n===== Top 80 키워드 =====")
        print(self.keywords_top80)
        print("\n===== 카테고리별 키워드 =====")
        for category, kw_list in self.keywords_by_category.items():
            print(f"[{category}] : {kw_list}")
    def math_category(self,text):
        keywords = self.extract_keywords(text)
        category = {}
        feture_row=[]
        usage_row=[]
        brands_row=[]
        others_row=[]
        for kw in keywords:
            if kw in self.features:
                feture_row.append(kw)
            elif kw in self.usage:
                usage_row.append(kw)
            elif kw in self.brands:
                brands_row.append(kw)
            elif kw in self.others:
                others_row.append(kw)
        category["features"]=feture_row
        category["usage"]=usage_row
        category["brands"]=brands_row
        category["others"]=others_row
        return category
    def match_tier(self,keywords):
        tier = {}
        keywords_top80_row=[]
        for kw in keywords:
            if kw in self.keywords_top80:
                keywords_top80_row.append(kw)
        tier["top80"]=keywords_top80_row.copy()
        iterser=list(set(self.keywords_top80)-set(self.keywords_top40))
        for kw in iterser:
            if kw in keywords:
                keywords_top80_row.remove(kw)
        tier["top40"]=keywords_top80_row.copy()
        iterser=list(set(self.keywords_top40)-set(self.keywords_top20))
        for kw in iterser:
            if kw in keywords:
                keywords_top80_row.remove(kw)
        tier["top20"]=keywords_top80_row.copy()
        return tier
    

class YouTubeCacheSystem:
    def __init__(self,data_path=".quary_to_data.h5",qary_path=".keyword_to_quary.h5"):
        self.cache = CacheManager(data_path)
        self.cache_manager = KeywordQueryManager(qary_path)
    def add_query(self,query_text,data,query_id=None):
        self.cache_manager.add_query(query_text,query_id)
        inpitdict={query_text.replace(" ",""):data}
        self.cache.add_hash(inpitdict)
    def find_matching_queries(self,text,min_score=0.0,max_results=10):
        matches= self.cache_manager.find_matching_queries(text,min_score,max_results)
        if matches:
            find_dict={matches[0]['query_text'].replace(" ",""):""}
            out=self.cache.get_value(find_dict)
            return out, matches[0]['query_text']
        else:
            return False
    def get_query_info(self,query_id):
        return self.cache_manager.get_query_info(query_id)
    def print_keyword_info(self):
        return self.cache.print_keyword_info()
    def math_category(self,text):
        return self.cache.match_category(text)
    def match_tier(self,keywords):
        return self.cache.match_tier(keywords)
    def close(self):
        self.cache_manager.close()
        self.cache.close()
    def __enter__(self):
        return self
    def __exit__(self,exc_type,exc_val,exc_tb):
        self.close()

    """
    # 인덱스 매니저 인스턴스 생성
manager = KeywordIndexManager('query_index.h5')

# 쿼리 추가 (자동 ID 생성)
query_id = manager.add_query('디지털 드로잉용 아이패드 태블릿 추천')

# 또는 ID를 직접 지정
query_id = manager.add_query('노트북 배터리 오래가는 모델 추천', query_id='notebook_battery')

# 파일 닫기 
manager.close()
    등록 예시
    """
    """
    # 키워드 검색으로 유사 쿼리 찾기
user_query = "아이패드 그림 그리기용 추천해주세요"
matches = manager.find_matching_queries(user_query)

if matches:
    best_match = matches[0]
    original_query_text = best_match['query_text']
    query_id = best_match['query_id']
    
    print(f"원본 쿼리: {original_query_text}")
    print(f"쿼리 ID: {query_id}")
    """

import os
import random
from pprint import pprint

# 테스트 파일 경로
TEST_FILE_PATH = "keyword_index_test.h5"

# 기존 테스트 파일 삭제 (테스트 전 초기화)
if os.path.exists(TEST_FILE_PATH):
    os.remove(TEST_FILE_PATH)
# 테스트용 원본 쿼리 5개
original_queries = [
    "디지털 드로잉용 아이패드 태블릿 추천, 13인치, 반응속도 좋은 펜, 그래픽 작업에 적합한 디스플레이",
    "노트북 배터리 오래가는 모델 추천, 가벼운 무게, 프로그래밍 작업용, 15인치 이상",
    "갤럭시탭 S7 vs 아이패드 프로 비교, 영상 시청과 문서 작업에 적합한 태블릿",
    "가성비 좋은 게이밍 노트북 추천, 램 16GB 이상, 발열 적은 모델, 고사양 게임 가능",
    "휴대성 좋은 미니 태블릿 추천, 독서 및 웹서핑용, 가볍고 배터리 오래가는 모델"
]

# 각 원본 쿼리당 3개씩 유사 쿼리 생성 (총 15개)
similar_queries = [
    # 디지털 드로잉용 아이패드 관련 유사 쿼리 3개
    "아이패드 그림 그리기 용도로 추천해주세요, 펜 반응속도가 좋은 것",
    "디지털 드로잉 태블릿 추천, 디스플레이가 좋은 모델 알려주세요",
    "아이패드 디지털 아트용 어떤게 좋을까요? 애플펜슬 호환되는 모델",
    
    # 배터리 오래가는 노트북 관련 유사 쿼리 3개
    "프로그래밍 작업용 가벼운 노트북 추천 배터리 수명 긴것",
    "개발 작업용 배터리 오래가는 노트북은 어떤게 좋을까요?",
    "코딩용 15인치 노트북 추천, 무게 가볍고 배터리 오래가는 제품",
    
    # 갤럭시탭 vs 아이패드 관련 유사 쿼리 3개
    "태블릿 비교 갤럭시탭과 아이패드 중 영상보기에 좋은 것은?",
    "문서 작업용 태블릿 추천, 삼성과 애플 제품 중 어느게 나을까요?",
    "아이패드와 갤럭시탭 비교 리뷰 부탁드려요, 동영상 시청용",
    
    # 게이밍 노트북 관련 유사 쿼리 3개
    "고사양 게임 돌아가는 노트북 추천, 가성비 좋고 발열 적은 모델",
    "게이밍용 노트북 램 16GB 이상 추천해주세요",
    "발열 적고 게임 잘 돌아가는 가성비 노트북 추천",
    
    # 미니 태블릿 관련 유사 쿼리 3개
    "가벼운 미니 태블릿 추천, 전자책 읽기 좋은 제품",
    "웹서핑용 소형 태블릿 뭐가 좋을까요? 배터리 오래가는 모델",
    "독서용 작은 태블릿 가벼운 제품 추천해주세요"
]

# 전혀 다른 쿼리 5개 (테스트용)
unrelated_queries = [
    "차량용 블루투스 이어폰 추천, 노이즈 캔슬링 기능 있는 제품",
    "가성비 좋은 커피머신 추천, 원두 분쇄기능 있는 제품",
    "여행용 디지털 카메라 추천, 4K 동영상 촬영 가능한 모델",
    "스마트 홈 시스템 구축 방법, IoT 기기 연동 방법",
    "헬스장 운동기구 추천, 초보자에게 좋은 기구"
]
def run_test():
    # 인덱스 매니저 생성
    manager = KeywordQueryManager(TEST_FILE_PATH)
    extractor = KeywordExtractor()  # 직접 키워드 확인용
    
    print("=== 키워드 분류기 테스트 ===\n")
    
    # 1. 원본 쿼리 등록 및 키워드 분석
    print("1. 원본 쿼리 등록 및 키워드 분석")
    print("-" * 50)
    
    original_query_ids = []
    for i, query in enumerate(original_queries):
        query_id = f"original_{i+1}"
        manager.add_query(query, query_id)
        original_query_ids.append(query_id)
        
        keywords = extractor.extract_keywords(query)
        category = extractor.match_category(keywords)
        tier = extractor.match_tier(keywords)
        
        print(f"쿼리 ID: {query_id}")
        print(f"쿼리: {query}")
        print(f"추출된 키워드 ({len(keywords)}개): {keywords[:10]}{'...' if len(keywords) > 10 else ''}")
        
        print("카테고리별 분류:")
        for cat_name, cat_kws in category.items():
            if cat_kws:  # 비어있지 않은 경우만 출력
                print(f"  - {cat_name}: {cat_kws}")
        
        print("티어별 분류:")
        for tier_name, tier_kws in tier.items():
            if tier_kws:  # 비어있지 않은 경우만 출력
                print(f"  - {tier_name}: {tier_kws}")
        print("-" * 50)
    
    print("\n2. 유사 쿼리 매칭 테스트")
    print("-" * 50)
    
    # 2. 유사 쿼리 15개에 대한 매칭 테스트
    match_results = []
    for i, query in enumerate(similar_queries):
        print(f"유사 쿼리 {i+1}: '{query}'")
        
        # 키워드 추출
        keywords = extractor.extract_keywords(query)
        print(f"추출된 키워드 ({len(keywords)}개): {keywords}")
        
        # 유사 쿼리 검색
        matches = manager.find_matching_queries(query, min_score=0.1)
        
        if matches:
            print("매칭된 원본 쿼리:")
            for idx, match in enumerate(matches):
                print(f"  {idx+1}. 쿼리 ID: {match['query_id']}")
                print(f"     원본 쿼리: {match['query_text'][:70]}{'...' if len(match['query_text']) > 70 else ''}")
                print(f"     매치 점수: {match['match_score']:.2f}")
                
                # 결과 기록 (나중에 정확도 계산용)
                correct_group = i // 3  # 0, 1, 2, 3, 4 중 하나 (원본 쿼리 그룹)
                expected_id = f"original_{correct_group+1}"
                actual_top_id = match['query_id']
                
                match_results.append({
                    'query': query,
                    'expected_id': expected_id,
                    'actual_top_id': actual_top_id,
                    'is_correct': expected_id == actual_top_id,
                    'score': match['match_score']
                })
        else:
            print("매칭된 쿼리가 없습니다.")
        print("-" * 50)
    
    # 3. 전혀 다른 쿼리 5개에 대한 테스트
    print("\n3. 관련 없는 쿼리 테스트")
    print("-" * 50)
    
    for i, query in enumerate(unrelated_queries):
        print(f"관련 없는 쿼리 {i+1}: '{query}'")
        
        # 키워드 추출
        keywords = extractor.extract_keywords(query)
        print(f"추출된 키워드 ({len(keywords)}개): {keywords}")
        
        # 유사 쿼리 검색
        matches = manager.find_matching_queries(query, min_score=0.1)
        
        if matches:
            print("매칭된 원본 쿼리:")
            for idx, match in enumerate(matches[:2]):  # 상위 2개만 표시
                print(f"  {idx+1}. 쿼리 ID: {match['query_id']}")
                print(f"     원본 쿼리: {match['query_text'][:70]}{'...' if len(match['query_text']) > 70 else ''}")
                print(f"     매치 점수: {match['match_score']:.2f}")
                
            # 낮은 매치 점수를 기대함
            match_results.append({
                'query': query,
                'expected_id': 'none',
                'actual_top_id': matches[0]['query_id'] if matches else 'none',
                'is_correct': matches[0]['match_score'] < 0.3 if matches else True,  # 매치 점수가 낮으면 정상
                'score': matches[0]['match_score'] if matches else 0
            })
        else:
            print("매칭된 쿼리가 없습니다. (정상)")
            match_results.append({
                'query': query,
                'expected_id': 'none',
                'actual_top_id': 'none',
                'is_correct': True,
                'score': 0
            })
        print("-" * 50)
    
    # 4. 정확도 계산 및 결과 요약
    correct_count = sum(1 for r in match_results if r['is_correct'])
    total_count = len(match_results)
    accuracy = correct_count / total_count
    
    print("\n4. 테스트 결과 요약")
    print("-" * 50)
    print(f"총 테스트 쿼리 수: {total_count}")
    print(f"정확히 매칭된 쿼리 수: {correct_count}")
    print(f"정확도: {accuracy:.2%}")
    
    # 유사 쿼리 그룹별 정확도
    similar_results = match_results[:15]  # 처음 15개는 유사 쿼리
    similar_correct = sum(1 for r in similar_results if r['is_correct'])
    similar_accuracy = similar_correct / len(similar_results)
    print(f"유사 쿼리 매칭 정확도: {similar_accuracy:.2%}")
    
    # 관련 없는 쿼리 테스트 결과
    unrelated_results = match_results[15:]  # 마지막 5개는 관련 없는 쿼리
    unrelated_correct = sum(1 for r in unrelated_results if r['is_correct'])
    unrelated_accuracy = unrelated_correct / len(unrelated_results)
    print(f"관련 없는 쿼리 정확한 분류: {unrelated_accuracy:.2%}")
    
    # 개선 제안
    print("\n5. 성능 개선 제안")
    print("-" * 50)
    if accuracy < 0.8:
        low_scores = [r for r in match_results if not r['is_correct']]
        print("개선이 필요한 매칭 사례:")
        for r in low_scores[:3]:  # 상위 3개 실패 사례만
            print(f"- 쿼리: '{r['query']}'")
            print(f"  예상 매칭: {r['expected_id']}, 실제 매칭: {r['actual_top_id']}, 점수: {r['score']:.2f}")
        
        print("\n개선 제안:")
        print("1. 키워드 추출 알고리즘 개선 (형태소 분석 방식 변경)")
        print("2. 티어별 가중치 조정 (티어 점수 가중치 변경)")
        print("3. 최소 매치 점수 임계값 조정 (현재: 0.1)")
    else:
        print("매칭 성능이 우수합니다!")
    
    # 파일 닫기
    manager.close()


    
# 테스트 출력
if __name__ == "__main__":
    run_test()

        # 테스트용 파일 경로 (기존 파일이 있다면 삭제)
    CACHE_FILE = "youtube_cache_test.h5"
    QUERY_INDEX_FILE = "youtube_query_index_test.h5"
    for f in [CACHE_FILE, QUERY_INDEX_FILE]:
        if os.path.exists(f):
            os.remove(f)

    # 예시 데이터셋: 각 쿼리와 연결된 YouTube 영상 데이터
    youtube_data = [
        {
            "query": "디지털 드로잉용 아이패드 태블릿 추천",
            "data": {
                "video_id": "video123",
                "title": "디지털 드로잉용 아이패드 태블릿 추천 영상",
                "description": "이 영상에서는 디지털 드로잉에 최적화된 아이패드 태블릿을 소개합니다."
            }
        },
        {
            "query": "노트북 배터리 오래가는 모델 추천",
            "data": {
                "video_id": "video456",
                "title": "배터리 수명이 긴 노트북 리뷰",
                "description": "최신 노트북 중 배터리 성능이 뛰어난 모델들을 비교합니다."
            }
        },
        {
            "query": "갤럭시탭 S7 vs 아이패드 프로 비교",
            "data": {
                "video_id": "video789",
                "title": "갤럭시탭 S7 vs 아이패드 프로, 어느 태블릿이 좋을까?",
                "description": "두 태블릿의 성능과 사용성을 상세 비교한 리뷰 영상입니다."
            }
        }
    ]

    # YouTubeCacheSystem 인스턴스 생성 (파일 경로 지정)
    youtube_cache = YouTubeCacheSystem(data_path=CACHE_FILE, qary_path=QUERY_INDEX_FILE)

    # 데이터셋의 각 쿼리와 관련 데이터를 시스템에 추가
    for item in youtube_data:
        query_text = item["query"]
        data = item["data"]
        youtube_cache.add_query(query_text, data)
        print(f"쿼리 추가: {query_text}")

    print("\n--- 추가된 쿼리들 ---")
    # 등록된 쿼리 ID들을 확인 (내부 인덱스에 저장된 query_id 리스트)
    with youtube_cache.cache_manager.index_storage as storage:
        all_queries = storage.get_all_queries()
        print("등록된 쿼리 ID:", all_queries)

    # 검색 테스트: 비슷한 쿼리로 매칭 확인
    search_query = "아이패드 드로잉 태블릿 추천"
    result = youtube_cache.find_matching_queries(search_query, min_score=0.1, max_results=10)

    print("\n--- 검색 결과 ---")
    if result:
        matched_data, matched_query_id = result
        print("매칭된 데이터:")
        pprint(matched_data)
        print("매칭된 쿼리 ID:", matched_query_id)
    else:
        print("매칭되는 쿼리가 없습니다.")

    # 시스템 닫기
    youtube_cache.close()
    
    
