#!/usr/bin/env python3
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken
from dotenv import load_dotenv
import json
import time

import re
import difflib
import pandas as pd
import random
from .queue_manager import add_log
from .dataloader import DataLoader
from .utility import Node
#app.agents.youtube_agent_module
globalist=[]

def log_wrapper(log_message):
    globalist.append(log_message)

    add_log(log_message) 
     
def truncate_text_by_tokens(text, max_tokens, model="gpt-4o-mini"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    if len(tokens) > max_tokens:
        tokens = tokens[:max_tokens]
        return encoding.decode(tokens)
    return text

def token_bool(text, model="gpt-4o-mini",target=1500):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    length=len(tokens)
    return length>target

def cal_token(text, model="gpt-4o-mini"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)

def simple_filter(metadata):
    simple_metadata = {}
    for k, v in metadata.items():
        if isinstance(v, (str, int, float, bool)):
            simple_metadata[k] = v
        else:
            # 복잡한 타입은 JSON 문자열로 변환하여 저장
            simple_metadata[k] = json.dumps(v, ensure_ascii=False)
    return simple_metadata

def compress_subtitles(text, chunk_size=500, overlap=50):  # overlap이 +/-
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=abs(overlap) if overlap > 0 else 0  # 양수면 overlap 적용
    )
    chunks = text_splitter.split_text(text)
    if overlap < 0:  # 음수면 각 청크를 자름
        trimmed_chunks = []
        for chunk in chunks:
            if len(chunk) > abs(overlap) * 2:
                trimmed = chunk[abs(overlap):-abs(overlap)]
                trimmed_chunks.append(trimmed)
        return trimmed_chunks
    return chunks 

def setting_tockens(text,target=1600,model="gpt-4o-mini",chunk_size=500):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    chunck_overrap= int(round((target-len(tokens))/2/target*chunk_size,0))
    if -chunck_overrap > chunk_size/4:
        #n=1
        while -chunck_overrap > chunk_size/4:
            words = text.split(" ")
            # 홀수 인덱스만 가져오기 (1,3,5...)
            filtered_words = words[1::2]
            text = "".join(filtered_words)
            tokens = encoding.encode(text)
            chunck_overrap= int(round((target-len(tokens))/2/target*chunk_size,0))
            #print (f"chunck_overrap:{n}번째 청크 제거")
            #n+=1
    compresed_txt=compress_subtitles(text, chunk_size=chunk_size, overlap=chunck_overrap)
    return compresed_txt, chunck_overrap

def compress_text(subtitle_text, chunk_size=500, chunk_overlap=50):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return text_splitter.split_text(subtitle_text)

def count_tokens(text, model="gpt-4o-"):
    # 모델에 맞는 인코딩 방식을 가져옵니다.
    encoding = tiktoken.encoding_for_model(model)
    # 텍스트를 토큰으로 인코딩합니다.
    tokens = encoding.encode(text)
    # 토큰의 개수를 반환합니다.
    return len(tokens)

def load_file(filename):
    with open(filename, "r", encoding="utf-8") as f:
        # splitlines()는 각 줄을 리스트로 반환하면서 줄바꿈 문자는 제거합니다.
        file = f.read().splitlines()
    return file
class keyword_finder:
    def __init__(self, keyworkds_set):
        self.keywords = keyworkds_set
        self.positive_prompt = """
            너는 이 데이터 저장소의 배테랑 검색 도우미야 특히 필요한 키워드를 추출하는데 최고의 전문가야 너는 조용한 성격에 필요한 문구만 조용히 적어내리는 성격이지
            너의 임무는 사용자의 요구를 보고 필요한 키워드를 아래 원칙에 맞게 적어주는 거야.
            0. 제공하는 키워드는 "데이터 저장소의 자료들의 키워드 전체 키워드 목록 내의 키워드 중에서만 선택해야 한다.
            1. 사용자가 요구한 키워드와 관련된 키워드를 찾아서 포함한다.
            2. 사용자가 요구한 제품군 중 가장 명확한 키워드를 선정해서 포함한다.
            3. 사용자가 특별히 요구하는 제조사가 있다면 관련 키워드를 포함한다 없다면 따로 포함하지 않는다.
            4. 사용자가 명확히 요구한 장면의 키워드가 있다면 가장 관련된 키워드를 포함한다.
            5. 다음 사항은 단서가 있다면 반드시 포함해서 키워드를 제공할 것 1) 제품군[스마트폰/태블릿/컴퓨터/전기차 등] 2)제조사[삼성/애플/테슬라/현대 등] 3)모델명[갤럭시S21/아이폰12/모델3/소울EV 등] 4)특징[고성능/하이앤드/가성비/고급형 등]
            6. 답변은 다음 양식을 따른다 [[키워드1]], [[키워드2]], [[키워드3]], ...]]
            7. 아래는 예시이므로 참고(예시이기 때문에 실제 키워드 리스트에 없는것이 있을 수 있음 하지만 실제 작업중에는 반드시 키워드 목록을 참고할것)
            ----------------------------예시1 요청 : 미술 전공인데 수채화 느낌 디지털 드로잉 연습에 최고 성능 아이패드 찾고 있어. 
            프로크리에이트 잘 돌아가고 색감 정확한 디스플레이 가진 모델로 추천해줘. ------------------------------------------
            
            [[아이패드]],[[애플]],[[M3]],[[M4]] ,[[프로크리에이트]], [[수채화]], [[디지털 드로잉]], [[색감 정확한 디스플레이]].....]]
            
            ----------------------------예시2 요청 : 배틀그라운드 모바일, 콜 오브 듀티 모바일 처럼 FPS 게임 렉 없이 즐기기 좋은 태블릿 없을까?------------------------------------------
            [[FPS 게임]], [[배틀그라운드 모바일]], [[콜 오브 듀티 모바일]], [[하이앤드]], [[고성능]], [[태블릿]].....]]
        """
        self.negative_prompt = """
            너는 이 데이터 저장소의 배테랑 검색 도우미야 특히 필요없는 자료를 제외하는데 최고의 전문가야 너는 조용한 성격에 필요한 문구만 조용히 적어내리는 성격이지
            너의 임무는 입력 키워드를 보고 상반되는 키워드를 아래 원칙에 맞게 적어주는 거야. 
            0. 너가 적어줄 키워드는 "전체 키워드 목록" 내의 키워드 중에서만 선택해야 한다.
            1. 입력된 키워드 및 명백한 하위 분류는 제외하지 않는다. (입력[[갤럭시]]-> 갤럭시, 갤럭시S, 갤럭시노트, 갤럭시탭 등은 제외 불가)
            2. 입력 키워드에서 명시된 제조사가 있다면 다른 제조사는 제외한다. (입력[[삼성]]-> 애플, LG, 샤오미 등은 제외)
                2-1. 입력 키워드에서 명시된 제조사/모델이 있다면 다른 제조사/모델은 제외하며, 같은 모델/제조사 및 특징은 제외하지 않는다(입력[[갤럭시]]-> 갤럭시, 삼성, Samsung, 갤럭시탭, 갤럭시 탭, 갤럭시 시리즈, 안드로이드 등은 제외 불가)
            3. 입력 키워드에서 명시된 제품군이 있다면 다른 제품군은 제외한다.([[태블릿]]-> '스마트폰','노트북','데스크탑','키보드','자동차','전기차' 등 필수 제외)
                3-1. 입력 키워드에서 명시된 제품군의 하위 분류 (입력[[태블릿]]-> '안드로이드 태블릿','태블릿PC','아이패드(제조사 정보가 없거나 애플인경우),'갤럭시 탭(제조사 정보가 없거나 삼성인경우)' 등)는 제외하지 않는다.
            4. 입력 키워드에서 명시된 장면/상황 키워드가 있다면 관련없는 장면/상황의 키워드는 제외한다.
                4-1. 입력 키워드에서 명시된 장면/상황 키워드의 "동일 분류" (입력[[게이밍]]-> '액션 게임','VR 게임','FPS 게임','모바일 게임','게이밍용' 등)는 제외하지 않는다.
                4-2. 입력 키워드에서 명시된 장면/상황 키워드와 비슷한 키워드가 포함되지만 다른 "물건" (입력[[게이밍]]-> '게이밍 노트북','게이밍 모니터','게이밍 키보드' 등)는 제외한다.
                4-3. 입력 키워드에서 명시된 장명/상황 키워드와 연관관계가 없는 키워드는 (입력[[게이밍]]-> '공부', '미술', '그림' 등)는 따로 제외하지 않는다.
            5. 제외할 키워드를 선정할 때 일부 상식적인 면을 고려할 것 예를 들어 게이밍이 입력되었을 경우 게이밍이 필요한 하이앤드 고성능 등의 키워드는 제외하지 않으며 그림 키워드가 있으면 디스플레이 컬러감 색감 등 상식 범위 내에서 연관된 키워드는 제외하지 않는다.
            6. 앞서 설명한것은 카테고리에 관한 설명이다 각 키워드는 카테고리별로 하나가 선택되도록 유도해야한다 예를들어 PC가 주요 키워드면 같은 카테고리 내의 키워드인 랩탑, 데스크탑, 모니터, 그래픽카드, 자동차,태블릿 등 물건의 종류는 되도록 상반된 키워드로 제공해야한다.
            7. 답변은 다음 양식을 따른다 [[키워드1]], [[키워드2]], [[키워드3]], ...]]
            8. 아래는 예시이므로 참고(예시이기 때문에 실제 키워드 리스트에 없는것이 있을 수 있음 하지만 실제 작업중에는 반드시 키워드 목록을 참고할것)
            키워드가 부정적이다 아니다가 중요한게 아니라 그 키워드를 포함된 자료를  보지 않기 위함임을 명심해야 한다.
            ----------------------------예시1 [[삼성]], [[고성능]] [[하이앤드]], [[태블릿]] 키워드 입력 시------------------------------------------
            [[샤오미]], [[보급형]], [[[가성비]]], [[중국산]], [[애플]], [[모바일]], [[랩탑]], [[PC]], [[그래픽카드]], [[RTX 5090]].....]]
            ----------------------------예시2 [[애플]], [[아이패드]] 키워드 입력 시------------------------------------------
            [[샤오미]], [[삼성]], [[갤럭시]], [[중국산]], [[아이폰]], [[맥북]], [[랩탑]], [[PC]], [[갤럭시탭S7]], [[갤럭시탭S8울트라]], [[RTX 5090]].....]]
        """
        self.context=f"데이터 저장소의 자료들의 키워드 전체 키워드:{self.keywords} "
        self.llm_n = Node(self.negative_prompt,context=self.keywords , gptmodel="gpt-4o")
        self.llm_p = Node(self.positive_prompt,context=self.keywords ,gptmodel="gpt-4o-mini")
        self.recent_keywords_n = None
        self.recent_keywords_p = None
        
    def find_negative_keywords(self, query):
        self.recent_keywords_n=re.findall(r'\[\[(.*?)\]\]', self.llm_n.get_response(query))
        return self.recent_keywords_n
    
    def find_positive_keywords(self, query):
        self.recent_keywords_p=self.llm_p.get_response(query)
        return self.recent_keywords_p
    
    def get_keywords_sametime(self, query):
        self.find_positive_keywords(query)
        self.find_negative_keywords(self.recent_keywords_p)
        self.recent_keywords_p=re.findall(r'\[\[(.*?)\]\]', self.recent_keywords_p)
        self.filtter_keywords()
        return self.recent_keywords_n, self.recent_keywords_p
    def filtter_keywords(self):
        p_buffer=[]
        n_buffer=[]
        for keyword in self.recent_keywords_p:
            for k in keyword.split(" "):
                p_buffer.append(k)
        for keyword in self.recent_keywords_n:
            for k in keyword.split(" "):
                n_buffer.append(k)
        n_buffer=list(set(n_buffer)-set(p_buffer))
        self.recent_keywords_p=p_buffer
        self.recent_keywords_n=n_buffer
        log_wrapper(f"positive_keywords:{self.recent_keywords_p}")
        log_wrapper(f"negative_keywords:{self.recent_keywords_n}")
    
    def enhance_query(self,query):
        system_message=f"""
            roles:system
            당신은 벡터 검색(RAG) 시스템에 들어갈 자연어 쿼리를 개선하는 전문가입니다. 저희 RAG에는 영상의 자막과 설명이 저장되어 있습니다.
            원본 쿼리 :{query}
            해당 쿼리만으로는 RAG에 저장된 자막 자료로 원하는 영상을 제대로 찾지 못할것으로 예상됩니다.
            목표:
            쿼리의 목적을 보다 명확히 표현해야 합니다.또한 벡터 공간 상에서 더욱 강력한 방향성을 가져 검색이 용이하도록 해주세요.
            RAG가 실제로 ‘{query}’ 와 관련된 정보를 담은 영상을 잘 찾을 수 있도록 관련 키워드를 추가해 주세요.
            사용자가 궁극적으로 원하는 것은 “{query}와 관련된 특징을 요약하거나 인상적인 부분을 보여주는 클립 영상”임을 반영하세요.
            이후에는 context에 태그를 추가하는 llm도 있습니다 그에 도움이되게 제조사나 목적을 명확히 파악 할 수 있는 문구를 추가해주세요
            [중요사항]
            이것은 절대적으로 지켜야할 사항입니다 답변에는 어떠한 "부가설명이 있어서는 안됩니다" 반드시 "쿼리만을 포함"하세요
        """
        user_message= f"""
            [원본 쿼리]
            {query}

            [실패 예측]
            - 쿼리가 너무 짧고 맥락이 부족하여, RAG가 원하는 영상을 제대로 찾지 못합니다.
            - 영상의 어떤부분을 원하는지 명확한 구체화가 필요합니다.

            [목표]
            1. 쿼리가 목표를 명확히 표현하되, 어떤 영상을 원하는지(기능 요약, 리뷰, etc.) 추가 설명
            2. RAG가 더 정확히 '{query}' 관련 클립을 찾도록, 적절한 키워드를 보강
            3. 사용자가 원하는 것은 '{query}'의 핵심적·인상적인 장면을 담은 영상임을 반영
            4. 원하는 장면을 구체적으로 머리에 그려지듯이 설명
            5. 확실한 제조사 정보와 정량적인 스펙을 제시
            
            위 사항을 고려하여, 개선된 자연어 쿼리를 작성해 주세요.
        """
        if isinstance(system_message, list):
            system_message = " ".join(map(str, system_message)).replace("}","").replace("{","")  # 리스트를 문자열로 변환
        if isinstance(user_message, list):
            user_message = " ".join(map(str, user_message)).replace("}","").replace("{","")  # 리스트를 문자열로 변환
        message=[("system",system_message+"{context}"),("human",user_message),("developer","{input}")]
        rellm=Node("",gptmodel="gpt-4o-mini")
        rellm.change_raw_prompt(message)
        rellm.change_context("""
                            [스마트폰]
                            삼성전자
                            - 갤럭시 S 시리즈: 기본형 플래그십
                            - 갤럭시 S+ 시리즈: 대화면 프리미엄
                            - 갤럭시 S Ultra 시리즈: 최상급 카메라/S펜
                            - 갤럭시 A 시리즈: 중저가 실속형
                            - 갤럭시 Z Fold: 메인 폴더블
                            - 갤럭시 Z Flip: 컴팩트 폴더블

                            애플
                            - 아이폰 Pro Max: 최상급 플래그십
                            - 아이폰 Pro: 프리미엄 컴팩트
                            - 아이폰 기본형: 보급형 플래그십
                            - 아이폰 Plus: 대화면 보급형
                            - 아이폰 SE: 실속형 컴팩트

                            [노트북]
                            애플
                            - 맥북 Pro: 전문가용 고성능
                            - 맥북 Air: 휴대성 중심 일반용

                            삼성
                            - 갤럭시 북 Pro: 프리미엄 비즈니스
                            - 갤럭시 북: 일반 사무용
                            - 갤럭시 Book2/3 시리즈: 360도 회전형

                            LG
                            - 그램: 초경량 장시간 배터리
                            - 울트라PC: 일반 사무용
                            - 울트라기어: 게이밍 특화

                            [태블릿]
                            애플
                            - 아이패드 Pro: 전문가용 고성능
                            - 아이패드 Air: 중급형 범용
                            - 아이패드: 보급형 기본
                            - 아이패드 미니: 소형 휴대용

                            삼성
                            - 갤럭시 탭 S: 프리미엄 안드로이드
                            - 갤럭시 탭 A: 보급형 실속

                            [무선이어버드]
                            애플
                            - 에어팟 Pro: 프리미엄 ANC
                            - 에어팟: 기본형
                            - 에어팟 맥스: 오버이어 최상급

                            삼성
                            - 갤럭시 버즈 Pro: 프리미엄 ANC
                            - 갤럭시 버즈: 기본형
                            - 갤럭시 버즈 Live: 오픈형

                            소니
                            - WF 시리즈: 프리미엄 사운드
                            - WH 시리즈: 오버이어 프리미엄

                            [제품 라인별 공통 특징]
                            - Ultra/Pro/Max: 최고급 성능/기능 집중
                            - Air/Plus: 보급형 프리미엄
                            - 기본형: 핵심 기능 중심
                            - SE/A/Lite: 실속형 entry
                            [스마트폰]
                            샤오미/레드미
                            - 샤오미 시리즈: 플래그십
                            - 레드미 노트: 중급형 베스트셀러
                            - POCO: 성능특화 중저가
                            - 레드미: 보급형 실속

                            OPPO/원플러스
                            - 파인드 시리즈: 최상급 플래그십
                            - 레노 시리즈: 중상급 
                            - 원플러스: 성능특화 플래그십

                            구글
                            - 픽셀 Pro: 카메라특화 플래그십
                            - 픽셀: 준플래그십
                            - 픽셀 a: 중급형

                            [노트북]
                            레노버
                            - ThinkPad X1: 프리미엄 비즈니스
                            - ThinkPad T: 정통 비즈니스
                            - ThinkPad E: 보급형 비즈니스
                            - Legion: 게이밍 전문
                            - Yoga: 컨버터블 프리미엄
                            - IdeaPad: 일반 소비자용

                            HP
                            - Spectre: 프리미엄 컨버터블
                            - ENVY: 준프리미엄
                            - Pavilion: 일반 소비자용
                            - Omen: 게이밍 라인
                            - EliteBook: 비즈니스 프리미엄
                            - ProBook: 비즈니스 보급형

                            Dell
                            - XPS: 프리미엄 컨버터블
                            - Latitude: 비즈니스용
                            - Inspiron: 일반 소비자용
                            - Alienware: 고급 게이밍
                            - G시리즈: 보급형 게이밍

                            MSI
                            - Stealth: 슬림 게이밍
                            - Raider: 고성능 게이밍
                            - Creator: 크리에이터용
                            - Modern: 일반 사무용

                            [이어폰/헤드폰]
                            Bose
                            - QuietComfort: 프리미엄 노이즈캔슬링
                            - Sport: 운동특화
                            - SoundLink: 범용 무선

                            젠하이저
                            - Momentum: 프리미엄 사운드
                            - HD/HD Pro: 스튜디오용
                            - CX: 일반 소비자용

                            [스마트워치]
                            애플
                            - 워치 Ultra: 아웃도어/프로
                            - 워치: 일반형
                            - 워치 SE: 보급형

                            삼성
                            - 갤럭시 워치 프로: 프리미엄
                            - 갤럭시 워치: 일반형
                            - 갤럭시 핏: 피트니스 밴드

                            가민
                            - Fenix: 프리미엄 아웃도어
                            - Forerunner: 러닝특화
                            - Venu: 일반 스마트워치
                            - Instinct: 견고성 강화

                            [게이밍 모니터]
                            LG
                            - UltraGear: 게이밍 프리미엄
                            - UltraWide: 울트라와이드
                            - UltraFine: 전문가용

                            삼성
                            - 오디세이: 게이밍 프리미엄
                            - 뷰피트: 사무용
                            - 스마트 모니터: 올인원형

                            [공통 특성]
                            - Pro/Ultra/Premium: 최상급 라인
                            - Plus/Advanced: 업그레이드 모델
                            - Lite/SE/Neo: 실속형 라인
                            - Gaming/Creator: 용도특화 라인
                             """)
        developer_query="""
            개발자 요청 : 나는 개발자로써 첨언을 할게 유저들은 사용법을 잘 모르니까 좀더 쿼리를 구체화 해서 좋은 답변을 받을 수 있도록 도와줘 부탁할게 그리고 뒤에는 작은 모델들도 많으니 동작을 잘 할 수있도록 하는 너의 역활이 매우 중요하단다
            그리고 이건 최중요 사항인데 "절대 응답에 어떠한 부가설명이나 문구 이모지를 포함하지마 무조건 쿼리만을 응답해"
        """
        query=rellm.get_response(developer_query)
        log_wrapper(query)
        return query
class Keyword_filter():
    def __init__(self):
        load_dotenv()
        self.dataloader=DataLoader()
        keywordset=list(self.dataloader.DataProcessor.keyword_set)
        self.keywordset="["+"], [".join(list( keywordset))+"]"
        self.keylist=list( keywordset)
        self.finder=keyword_finder(self.keywordset)
        self.enhanced_query=""
        self.filtter_list={}
        self.recent_selected_keywords=[]
        self.RAG_available=False
        
    def enhance_query(self,query):
        self.enhanced_query = self.finder.enhance_query(query)
        return self.enhanced_query
    
    def get_keywords_sametime(self):
        return self.finder.get_keywords_sametime(self.enhanced_query)
    
    def keyword_filter(self,k=50):
        outs=set()
        for d in self.finder.recent_keywords_p:
            similar_words = difflib.get_close_matches(d, self.dataloader.DataProcessor.keyword_set, n=5, cutoff=0.85)
            if similar_words:
                for i in similar_words:
                    outs.add(i)
        negset=set()
        for d in self.finder.recent_keywords_n:
            similar_words = difflib.get_close_matches(d, self.dataloader.DataProcessor.keyword_set, n=5, cutoff=0.85)
            if similar_words:
                for i in similar_words:
                    negset.add(i)
        self.recent_selected_keywords=list(outs)
        result=self._keyword_score(list(outs),list(negset),k)
        self.filtter_list[self.enhanced_query]=result
        self.RAG_available=True
        return result, outs
        
    def _keyword_score(self,selected,remove,k):
        data = [0] * len(self.dataloader.DataProcessor.Index_table.columns)
        galaxy_keywords = [k for k in self.keylist if "갤럭시" in k]
        samdung_keywords = [k for k in self.keylist if "삼성" in k]
        appple_keywords= [k for k in self.keylist if "애플" in k]
        i_product_keywords = [k for k in self.keylist if "아이" in k]
        dayinform=self.dataloader.DataProcessor.datelimit.copy()
        ref_table=[]
        pre_table=self.dataloader.DataProcessor.Index_table.copy()
        available_columns = dayinform[dayinform['available'] == 1].index
        pre_table = pre_table[available_columns]
        if  galaxy_keywords in selected or samdung_keywords in selected or 'Galaxy' in selected or '갤럭시' in selected:
            galaxy_keywords.extend(samdung_keywords)
            selected_rows = pre_table.loc[ pre_table.index.isin(galaxy_keywords) ]
            cols_to_keep = selected_rows.eq(1).any(axis=0)
            ref_table = pre_table.loc[:, cols_to_keep]
        if appple_keywords in selected or i_product_keywords in selected or 'Apple' in selected or '애플' in selected or  '아이패드' in selected:
            appple_keywords.extend(i_product_keywords)
            selected_rows = pre_table.loc[ pre_table.index.isin(appple_keywords) ]
            cols_to_keep = selected_rows.eq(1).any(axis=0)
            ref_table = pre_table.loc[:, cols_to_keep]
        if len(ref_table)<1:
            cols_to_keep = pre_table.eq(1).any(axis=0)
            ref_table = pre_table.loc[:, cols_to_keep]
        data = [0] * len(ref_table.columns)
        stakscore=pd.DataFrame(data, columns=['score'],index=ref_table.columns)
        for d in selected:
            if d:
                stakscore['score']+=ref_table.loc[d].astype(int).values.tolist()
                if d  == '태블릿':
                    for i in range(5):
                        stakscore['score']+=ref_table.loc[d].astype(int).values.tolist()
        stakscore = stakscore.sort_values(by='score', ascending=False)
        resultscore=stakscore[:k]

        dayinform=self.dataloader.DataProcessor.datelimit.copy()

        pre_table=self.dataloader.DataProcessor.Index_table.copy()
        available_columns = dayinform[dayinform['available'] == 1].index
        ref_table = pre_table[available_columns]
        if  galaxy_keywords in selected or samdung_keywords in selected or 'Galaxy' in selected or '갤럭시' in selected:
            ref_table=[]
            galaxy_keywords.extend(samdung_keywords)
            selected_rows = pre_table.loc[ pre_table.index.isin(galaxy_keywords) ]
            cols_to_keep = selected_rows.eq(1).any(axis=0)
            ref_table = pre_table.loc[:, cols_to_keep]
        if appple_keywords in selected or i_product_keywords in selected or 'Apple' in selected or '애플' in selected:
            ref_table=[]
            appple_keywords.extend(i_product_keywords)
            selected_rows = pre_table.loc[ pre_table.index.isin(appple_keywords) ]
            cols_to_keep = selected_rows.eq(1).any(axis=0)
            ref_table = pre_table.loc[:, cols_to_keep]
        data = [0] * len(ref_table.columns)
        removeindex=pd.DataFrame(data, columns=['score'],index=ref_table.columns)
        for d in remove:
            if d:
                removeindex['score']+=ref_table.loc[d].astype(int).values.tolist()
        removeindex[removeindex['score']>=int(1)]=int(1)
        removeindex=removeindex[removeindex['score']==int(1)]
        resultscore_filtered = resultscore[~resultscore.index.isin(removeindex.index)]
        resultscore_filtered=resultscore_filtered[resultscore_filtered['score']>=int(1)]
        
        log_wrapper(f"최종 필터 : {resultscore_filtered}")
        return resultscore_filtered
    def RAG_search(self):
        searchV=[]
        keyword_findert=self.filtter_list[self.enhanced_query]
        for index, row in keyword_findert.iterrows():
            searchV.append(index)
        self.dataloader.DataProcessor.set_active(searchV)
        self.dataloader.DataProcessor.create_qa_chain_from_store(persist_directory="data/vector_db.h5")
        self.RAG_available=False
        index,result=self.dataloader.DataProcessor.get_video_data(self.enhanced_query,mode="database")
        return index,result
    
class RAGOUT():
    def __new__(cls, filtter: Keyword_filter,outs):
        if not filtter.RAG_available:
            return None  # 객체 생성 자체를 하지 않음 ❌
        return super().__new__(cls)  # 정상적인 경우에만 객체 생성 ✅
    
    def __init__(self, filtter:Keyword_filter,outs):
        self.marker=False
        self.filtter = filtter 
        
        self.enhanced_query=filtter.enhanced_query
        
        self.RAG_out, self.result = self.filtter.RAG_search()  # 튜플 언패킹
        data=[0]*len(self.RAG_out)
        #filtter.dataloader.DataProcessor.data['테크몽'][1]['링크'][32]
        sorted_result =  pd.DataFrame(data, columns=['score'],index=self.RAG_out)
        self.data = self.filtter.dataloader.DataProcessor.data 
        self.fomatted_data={}
        for index in self.RAG_out:
            sorted_result.loc[index]=int(outs[outs.index==index].values[0][0])
        self.sorted_result=sorted_result.sort_values(by='score', ascending=False)
        self.cummunucation_buffer=[]
        self.index=0
        self.video_extraction={}
        self.rerank= self.sorted_result.index[self.index]
        self.get(self.index)
        self.output={}
        self.second_procesed=False

        self.retry_templates = [
                            "이 영상에서 원하는 정보를 찾을 수 없는 것 같다고?. 그럼 여기서 다시 한번 확인해줘.",
                            "필요한 구간이 빠져있는 것 같은데, 다른 영상을 확인할 수 있을까?",
                            "다른 관련 영상에서 비슷한 내용을 찾을 수 있을까?주의사항과 세부규칙은 항상 잘 지키고!!",
                            "이 영상이 아니라면 비슷한 이번 영상에서 답을 찾을 수 있을까?",
                            "이 영상이 적절하지 않다면 이 영상에서 추천해줘.",
                            "더 정확한 답변이 필요해. 다시 한 번 이 영상을 분석해봐.",
                            "정보가 부족한 것 같아. 이 영상을 분석해줄 수 있어?",
                            "추가적인 힌트가 필요해. 이 영상 말고 다른 곳에서도 검색해줘.",
                            "결과가 만족스럽지 않아. 더 나은 정보를 찾아봐. 주의사항과 세부규칙은 항상 잘 지키고!!",
                            "이 영상에서 찾을 수 없다면, 다음 순위 영상을 확인할 수 있을까?",
                            "다른 영상을 가져왔어 다시한번 도와줄거지? 주의사항과 세부규칙은 항상 잘 지키고!!",
                            
                        ] 
        
    def get_random_retry_message(self):
        return random.choice(self.retry_templates)    
           
        
        
    def next(self):
        self.index+=1
        self.get_ranked_data()
        userlog=f'{self.index}번째 유저의 요청 : '+self.get_random_retry_message()
        self.cummunucation_buffer.append(userlog)
        log_wrapper(userlog)
        return self.fomatted_data
    
    def get(self,index):
        self.index=index
        self.get_ranked_data()
        return self.fomatted_data
    
    def get_ranked_data(self):
        self.rerank=self.sorted_result.index[self.index].replace(']','[').replace('[[','[').split('[')
        self.format_data()
        return self.rerank   
    
    def format_data(self):
        self.fomatted_data['data']={}
        self.fomatted_data['srt']={}
        self.fomatted_data['data']['링크']=self.data[self.rerank[1]][1]['링크'][int(self.rerank[-2])]
        self.fomatted_data['data']['태그']=self.data[self.rerank[1]][1]['태그'][int(self.rerank[-2])]
        self.fomatted_data['data']['조회수']=self.data[self.rerank[1]][1]['조회수'][int(self.rerank[-2])]
        self.fomatted_data['data']['제목']=self.data[self.rerank[1]][1]['제목'][int(self.rerank[-2])]
        self.fomatted_data['data']['유튜버']=self.data[self.rerank[1]][1]['유튜버'][int(self.rerank[-2])]
        self.fomatted_data['data']['업로드일']=self.data[self.rerank[1]][1]['업로드일'][int(self.rerank[-2])]
        self.fomatted_data['data']['설명']=self.data[self.rerank[1]][1]['설명'][int(self.rerank[-2])]
        try:
            self.fomatted_data['data']['자막요약']=self.data[self.rerank[1]][1]['자막요약'][int(self.rerank[-2])]
            self.fomatted_data['data']['코드']=self.data[self.rerank[1]][1]['코드'][int(self.rerank[-2])]
        except:
            self.fomatted_data['data']['자막요약']=""
            self.fomatted_data['data']['코드']=""
        self.fomatted_data['자막']=self.data[self.rerank[1]][1]['자막'][int(self.rerank[-2])]
    def make_clip(self):
        if self.second_procesed:
            base_link=self.fomatted_data['data']['링크']
            link_text=self.video_extraction['seconds']
            outlink=""
            if link_text and isinstance(link_text, list):
                link_text_f=re.sub(r'[^0-9s]', '', link_text[0])
                outlink=base_link+"&t="+link_text_f
            elif isinstance(link_text, str):
                link_text_f=re.sub(r'[^0-9s]', '', link_text)
            else:
                outlink=base_link
            self.video_extraction['clip']=outlink        
            return outlink
        else:
            return None
    def get_second(self,OUTPUT):
        self.video_extraction['timestamps']=OUTPUT['timestamps']
        self.video_extraction['timestampsdiscriptions']=OUTPUT['timestampsdiscriptions']
        self.video_extraction['seconds']=OUTPUT['seconds']
        self.video_extraction['descriptions']=OUTPUT['descriptions']
        self.video_extraction['codes']=OUTPUT['codes']
        if self.second_procesed:
            return self.outputsort()
            

            
    def outputsort(self):
        self.make_clip()
        self.output['raw_meta_data']={}
        self.output['llm_process_data']={}
        self.marker=True
        try:
            self.output['raw_meta_data']['링크']=self.fomatted_data['data']['링크']
            self.output['raw_meta_data']['태그']=self.fomatted_data['data']['태그']
            self.output['raw_meta_data']['조회수']=self.fomatted_data['data']['조회수']
            self.output['raw_meta_data']['제목']=self.fomatted_data['data']['제목']
            self.output['raw_meta_data']['유튜버']=self.fomatted_data['data']['유튜버']
            self.output['raw_meta_data']['업로드일']=self.fomatted_data['data']['업로드일']
            self.output['raw_meta_data']['설명']=self.fomatted_data['data']['설명']
            self.output['raw_meta_data']['자막']=self.fomatted_data['자막']
            self.output['llm_process_data']['자막요약']=self.fomatted_data['data']['자막요약']
            self.output['llm_process_data']['코드']=self.fomatted_data['data']['코드']
            
        except:
            self.output['raw_meta_data']['링크']="인덱싱 오류로 적합한 데이터 추출 실패"
            self.output['raw_meta_data']['태그']="인덱싱 오류로 적합한 데이터 추출 실패"
            self.output['raw_meta_data']['조회수']="인덱싱 오류로 적합한 데이터 추출 실패"
            self.output['raw_meta_data']['제목']="인덱싱 오류로 적합한 데이터 추출 실패"
            self.output['raw_meta_data']['유튜버']="인덱싱 오류로 적합한 데이터 추출 실패"
            self.output['raw_meta_data']['업로드일']="인덱싱 오류로 적합한 데이터 추출 실패"
            self.output['raw_meta_data']['설명']="인덱싱 오류로 적합한 데이터 추출 실패"
            self.output['raw_meta_data']['자막']="인덱싱 오류로 적합한 데이터 추출 실패"
            self.output['llm_process_data']['자막요약']="인덱싱 오류로 적합한 데이터 추출 실패"
            self.output['llm_process_data']['코드']="인덱싱 오류로 적합한 데이터 추출 실패"
            self.marker=False
        try:
            self.output['llm_process_data']['timestamps']=self.video_extraction['timestamps']
            self.output['llm_process_data']['timestampsdiscriptions']=self.video_extraction['timestampsdiscriptions']
            self.output['llm_process_data']['seconds']=self.video_extraction['seconds']
            self.output['llm_process_data']['descriptions']=self.video_extraction['descriptions']
            self.output['llm_process_data']['codes']=self.video_extraction['codes']
            self.output['llm_process_data']['clip']=self.video_extraction['clip']
        except:
            self.output['llm_process_data']['timestamps']="적합한 데이터 추론 실패"
            self.output['llm_process_data']['timestampsdiscriptions']="적합한 데이터 추론 실패"
            self.output['llm_process_data']['seconds']="적합한 데이터 추론 실패"
            self.output['llm_process_data']['descriptions']="적합한 데이터 추론 실패"
            self.output['llm_process_data']['codes']="적합한 데이터 추론 실패"
            self.output['llm_process_data']['clip']="적합한 데이터 추론 실패"
            self.marker=False
        #log_wrapper("----------------------------------------------예시 출력----------------------------------------------")
        #log_wrapper("----------------------------------------------raw_meta_data----------------------------------------------")
        #log_wrapper(f'링크 : {self.output["raw_meta_data"]["링크"]}')
        #log_wrapper(f'태그 : {self.output["raw_meta_data"]["태그"]}')
        #log_wrapper(f'조회수 : {self.output["raw_meta_data"]["조회수"]}')
        #log_wrapper(f'제목 : {self.output["raw_meta_data"]["제목"]}')
        #log_wrapper(f'유튜버 : {self.output["raw_meta_data"]["유튜버"]}')
        #log_wrapper(f'업로드일 : {self.output["raw_meta_data"]["업로드일"]}')
        #log_wrapper(f'설명 : {self.output["raw_meta_data"]["설명"]}')
        #log_wrapper('자막 생략----------------------------------------------')
        #log_wrapper("----------------------------------------------llm_process_data----------------------------------------------")
        #log_wrapper(f'자막요약 : {self.output["llm_process_data"]["자막요약"]}')
        #log_wrapper(f'코드 : {self.output["llm_process_data"]["코드"]}')
        #log_wrapper(f'timestamps : {self.output["llm_process_data"]["timestamps"]}')
        #log_wrapper(f'timestampsdiscriptions : {self.output["llm_process_data"]["timestampsdiscriptions"]}')
        #log_wrapper(f'seconds : {self.output["llm_process_data"]["seconds"]}')
        #log_wrapper(f'descriptions : {self.output["llm_process_data"]["descriptions"]}')
        #log_wrapper(f'codes : {self.output["llm_process_data"]["codes"]}')
        #log_wrapper(f'clip : {self.output["llm_process_data"]["clip"]}')
        #log_wrapper("----------------------------------------------예시 출력----------------------------------------------")
        return self.output



    
class Video_extractor():
    def __init__(self,RGAout:RAGOUT):
        self.RGAout=RGAout
        
        self.query=self.RGAout.enhanced_query
        self.input=self.RGAout.fomatted_data
        self.ueer_query_prompt = """
                                    너의 역할: 
                                    - 유저 요청에서 **핵심 조건**을 뽑아내고, 이를 LLM이 이해하기 좋은 형태로 요약/정리하는 것.
                                    작업 지시:
                                    - 유저 요청(abstract)을 분석하고, 그 안에 담긴 요구사항(조건)들을 우선순위대로 정리한다.
                                    - 최종 출력은 **우선순위대로 번호를 붙여** 상세 설명 형태로 작성한다. 
                                    - 중간 단계(조건 개수 파악, 우선순위 결정 등)는 절대 출력하지 말 것.
                                    - 오직 “우선순위별 조건 설명”만 출력하라.
                                """
        self.slave_prompt = """
                            너의 역할:
                            - 제공된 '리뷰 스크립트'에서, 사용자(구매 고려자)가 중요하게 여길 만한 문구(중요사항과 관련)에 주목하고, 
                            해당 문구가 몇 번째 라인에 있는지 찾는다.
                            - 최종적으로 다음 세 가지를 **한 번에** 출력하라:
                            1) 원문(스크립트 그대로),
                            2) 몇 번째 라인인지,
                            3) 이를 표준어로 교정한 문장.

                            주의 사항:
                            - 리뷰 스크립트는 실제 발화 내용 그대로라서 문법이 다소 불규칙할 수 있음. 
                            - 중간 과정(1번, 2번 단계 탐색)은 절대 출력하지 말고, 최종 결과만 출력할 것.
                            - 만약 중요사항과 직접 관련 없는 문구라면, 답변하지 말고 다시 스크립트를 확인해(내부적으로) 
                            ‘직접 관련이 있는 문구’만 최종 결과에 포함하라.
                        """
        self.slave_prompt_srt = """
                                너의 역할:
                                - 자막 스크립트(시간 정보 포함)를 바탕으로, '요약 정보(중요사항)'와 가장 밀접하게 연결된 장면을 찾는다.
                                - 찾아낸 장면의 시작~끝 시간을 결정하고, 다음 포맷으로 한 번에 출력한다.
                                출력 형식(4줄 고정):
                                1) "사유 내용"
                                2) [;HH:MM:SS,HH:MM:SS;]
                                3) [NNNs]
                                4) /?;'원문 내용';?/
                                세부 규칙:
                                - 1번 줄: 큰따옴표("") 안에 들어갈 내용(사유).
                                - 2번 줄: 시작~끝 시간, 예: `[;00:01:23,00:01:45;]`. (밀리초가 필요하면 `00:01:23.456`처럼 추가 가능)
                                - 3번 줄: 시작 시간을 초단위로 환산 + 's' 붙인 형태 예: `[83s]`, `[135s]` 등.
                                - 4번 줄: /?;'   ';?/ 사이에 추출한 부분의 원문 내용. 예: `/?;'이 제품은 가성비가 뛰어나요';?/`.
                                주의 사항:
                                - 절대 이 4줄 이외의 내용(문장, 기호, 해설)을 추가 출력하지 마라.
                                - 단 하나의 시간대(클립)만 결정해야 한다.
                                - 만약 ‘중요사항’과 정확히 연결된 구간이 없다고 판단되면, 답변을 하지 말거나 “연관 구간이 없습니다.”라고만 출력.
                                - 중간 단계(0,1,2,3 등)는 절대 출력하지 말고, 요구된 최종 포맷만 반환할 것.
                            """ 
        self.short_cut_prompt = """
                                너의 역할:
                                - 사용자의 요청과 보유한 [자막자료],[설명자료]를 확인해서 다음의 내용을 출력한다
                                1) 영상에서 주요 하이라이트 부분의 시간의 시작시간을 5구간 이상찾는다 포멧은 다음과 같다 [[TIMESTAMP:00:00:00]]
                                1-1) 각 타임스탬프는 10단어 이하로 간단한 설명이 필요하다 포멧은 다음과 같다 [[TIMESTAMPDESCRIPTION:00:00:00:여기에 설명 텍스트]]
                                2) 1번중 가장 중요하다고 생각하는 부분중 하나를 찾아서 초단위로 환산하여 [[SECONDS:120]] 포멧으로 출력한다. 환산식은 다음과 같다(HH*3600+MM*60+SS)
                                2-1) 가장 중요함의 기준은 사용자의 요청을 달성하는데 중요한 정보의 제공을 의미한다.
                                3) 설명자료에서 주요 내용 요약본
                                4) 자막의 전체 내용 요약본
                                세부규칙:
                                - 위의 역할을 수행함에 있어 아래의 규칙을 절대적으로 지켜야 한다
                                1) 사용자의 요청을 달성하는데 도움이 되는 방향의 자료를 수집해야한다.
                                1-1) 사용자의 요청에서 어떤 "제품" 인지 유심히 보고 영상의 중요성을 결정한다.(예시1 요청->애플 2024 "아이패드 에어" 11 M2 리뷰 인 경우 애플 "비전프로", 애플 "아이패드 프로", 삼성 "갤럭시 탭" 등은 중요도가 없다.)
                                    (예시2 요청-> 삼성전자 "갤럭시탭"S9  리뷰 인 경우 삼성 "갤럭시 S"25, 애플 "아이패드 프로", 삼성 "갤럭시 북", 샤오미 "미 패드" 등은 중요도가 없다.)
                                    상기의 예시 외에도 각 제조사별 제품군에 대해 동일한 규칙을 적용한다.
                                2) 모든 자료는 [[]] 안에 배치해서 구분한다 예시 [[TIMESTAMP:00:00:00]],[[TIMESTAMPDESCRIPTION:00:00:00:여기에 설명 텍스트]] ,[[SECONDS:120]],[[DESCRIPTION:여기에 설명 텍스트]], [[DESCRIPTION:자막자료 요약내용]]
                                3) 요청한 내용 외에 일체 다른 텍스트는 출력하지 않는다.
                                4) 중간과정은 절대적으로 출력하지 않는다.
                                5) 만약 요청한 내용을 달성할 수 없다고 판단되면 [[DESCRIPTION:연관 구간이 없습니다.]]와 주의사항의 "모든" 확인코드와 함께 출력한다.
                                주의사항
                                -이것은 해당 프롬프트의 전달이 정확한지 확인하기 위한 규칙으로 반드시 지켜야 한다.
                                1) 너의 역할: 이하의 1~4의 내용이 보인다면 출력의 끝에 [[CODE:역할확인]]을 출력한다.
                                2) 세부 규칙: 이하의 1~5의 내용이 보인다면 출력의 끝에 [[CODE:세부규칙확인]]을 출력한다.
                                3) 주의사항: 이하의 1~5의 내용이 보인다면 출력의 끝에 [[CODE:주의사항확인]]을 출력한다.
                                4) [자막자료],[설명자료]가 확인 가능하다면 출력의 끝에 [[CODE:추가자료확인]]을 출력한다.
                                5) 해당 코드가 누락되거나 출력되지 않을 시 시스템에 치명적인 오류가 발생할 수 있으니 주의한다.
        """

        
        self.responset={}
        self.succeed=[]
        self.result=False
        self.OUTPUT ={}

    def short_process(self):
        data=self.input['data']
        input_srt=self.input['자막']
        context = {f"[자막자료]:\n{input_srt}\n\n"\
                    f"[설명자료]:\n{data['설명']}"}
        llm=Node(self.short_cut_prompt,gptmodel='gpt-4o-mini')
        llm.change_context(context)
        log_wrapper(f'유저 쿼리 : {self.query}')
        self.RGAout.cummunucation_buffer.append(f'첫번째 유저 요청 : {self.query}')
        log_wrapper(f'첫번째 유저 요청 : {self.query}')
        respons=llm.get_response(self.query)
        #pattern = r'\[\[(.*?)\]\]'
        #matches = re.findall(pattern, respons)
        timestamps = re.findall(r'\[\[TIMESTAMP:(.*?)\]\]', respons)
        seconds = re.findall(r'\[\[SECONDS:(.*?)\]\]', respons)
        descriptions = re.findall(r'\[\[DESCRIPTION:(.*?)\]\]', respons)
        codes = re.findall(r'\[\[CODE:(.*?)\]\]', respons)
        timestampsdiscriptions = re.findall(r'\[\[TIMESTAMPDESCRIPTION:(.*?)\]\]', respons)
        self.RGAout.cummunucation_buffer.append(f'첫번째 너의 답변 : {respons}')
        log_wrapper(f'첫번째 너의 답변 : {respons}')
        self.OUTPUT['timestamps'] = timestamps
        self.OUTPUT['timestampsdiscriptions'] = timestampsdiscriptions
        self.OUTPUT['seconds'] = seconds
        self.OUTPUT['descriptions'] = descriptions
        self.OUTPUT['codes'] = codes
        if len(self.OUTPUT['seconds'])<1 and not self.OUTPUT['descriptions']=='연관 구간이 없습니다.':
            self.RGAout.second_procesed=False
            out=self.retry_event_loop()
            return out
        else:
            self.RGAout.second_procesed=True
        self.RGAout.get_second(self.OUTPUT)
        return self.RGAout.outputsort()
    def memory_process(self):
        data=self.input['data']
        input_srt=self.input['자막']
        context = {f"[자막자료]:\n{input_srt}\n\n"\
                    f"[설명자료]:\n{data['설명']}"\
                     f"[지난대화]:\n{self.RGAout.cummunucation_buffer}"}  
        llm=Node(self.short_cut_prompt,gptmodel='gpt-4o-mini')
        llm.change_context(context)
        log_wrapper(f'유저 쿼리 : {self.RGAout.cummunucation_buffer[-1]}') 
        respons=llm.get_response(self.RGAout.cummunucation_buffer[-1])
        self.RGAout.cummunucation_buffer.append(f"{self.RGAout.index} 번째 너의 대답 : {respons}")
        log_wrapper(f"{self.RGAout.index} 번째 너의 대답 : {respons}")
        timestamps = re.findall(r'\[\[TIMESTAMP:(.*?)\]\]', respons)
        seconds = re.findall(r'\[\[SECONDS:(.*?)\]\]', respons)
        descriptions = re.findall(r'\[\[DESCRIPTION:(.*?)\]\]', respons)
        codes = re.findall(r'\[\[CODE:(.*?)\]\]', respons)
        timestampsdiscriptions = re.findall(r'\[\[TIMESTAMPDESCRIPTION:(.*?)\]\]', respons)
        self.OUTPUT['timestamps'] = timestamps
        self.OUTPUT['timestampsdiscriptions'] = timestampsdiscriptions
        self.OUTPUT['seconds'] = seconds
        self.OUTPUT['descriptions'] = descriptions
        self.OUTPUT['codes'] = codes
        if not self.OUTPUT['seconds'] and not self.OUTPUT['descriptions']=='연관 구간이 없습니다.':
            self.RGAout.second_procesed=False
        else:
            self.RGAout.second_procesed=True
            self.RGAout.get_second(self.OUTPUT)
        
        
    def retry_event_loop(self,limit=3):
        lim=0
        while not self.RGAout.second_procesed:
            self.memory_process()
            if self.RGAout.second_procesed:
                break
            self.RGAout.next()
            lim+=1
            if lim>limit:
                break
        return self.RGAout.outputsort()
    
    def process(self):
        self.extract_yt_str()
        self.getoutput()
        return self.result
    def select_one_viedo(video_list):
        select_prompt = "5개의 영상 정보 중 요청자의 질문과 가장 관련있는 하나를 선택해줘"
        select_node=Node(select_prompt)
        video_list[0]  
        
    def extract_yt_str(self):
        abckupresopons={}
        data=self.input['data']
        input_srt=self.input['자막']
        buff=input_srt.replace("\n","")
        buff2=re.sub(r'[-:\d>]', '', input_srt)
        input_txt=buff2.replace(" ,"," ").replace(", ","")
        user_query_extractor = Node(self.ueer_query_prompt)
        user_query_extractor_response = user_query_extractor.get_response(self.query)
        abckupresopons["1차"]=user_query_extractor_response
        log_wrapper(user_query_extractor_response)
        context = {f"중요사항:\n{user_query_extractor_response}"}
        slave_node = Node(self.slave_prompt)
        slave_node.change_context(context)
        slave_node_srt = Node(self.slave_prompt_srt,gptmodel='gpt-4o-mini')
        respons=slave_node.get_response(input_txt)
        #log_wrapper(respons)
        abckupresopons["2차"]=respons
        context_srt = {f"자막:\n{input_srt}\n\n"\
                        f"요약:\n{respons}\n\n"}
        slave_node_srt.change_context(context_srt)
        respons_srt=slave_node_srt.get_response(user_query_extractor_response)
        abckupresopons["3차"]=respons_srt
        self.responset=abckupresopons

    def getoutput(self):
        text=self.responset["3차"]
        data=self.input['data']
        base_link=data['링크']
        # 1. 원문: 큰따옴표("") 사이의 내용
        original_match = re.search(r'"(.*?)"', text, re.DOTALL)
        original_text = original_match.group(1) if original_match else ""
        # 2. 시간: [; ;] 사이의 내용
        time_match = re.search(r'\[\;(.*?)\;\]', text, re.DOTALL)
        time_text = time_match.group(1) if time_match else ""
        # 3. 링크: 단, [] 안에 있지만 시간 형식([; ;])은 제외 (여기서는 간단히 [로 시작하고 ;가 없는 경우)
        link_match = re.search(r'\[(?!;)([^\[\]]*?)\]', text)
        link_text = link_match.group(1) if link_match else ""
        outlink=""
        if link_text:
            link_text_f=re.sub(r'[^0-9s]', '', link_text)
            outlink=base_link+"&t="+link_text_f
        else:
            outlink=base_link
        # 4. 사유: /??/ 사이의 내용  
        # 예시에서는 "/?" 로 시작하고 "/"로 끝남. 내부의 ?는 고정이 아니라 필요에 따라 변동 가능하므로
        reason_match = re.search(r"/\?;'(.*?)';\?/", text, re.DOTALL)
        reason_text = reason_match.group(1) if reason_match else ""
        # 결과를 딕셔너리로 저장
        result = {
            "사유": original_text,
            "시간": time_text,
            "링크": outlink,
            "원문": reason_text
        }
        if not link_text_f:
            retry=True
        elif len(link_text_f)<1:
            retry=True
        else:
            retry=False
        self.succeed=retry
        self.result=result

def retrun_fail_result():
    out={}
    out['llm_process_data']={}
    out['raw_meta_data']={}
    out['raw_meta_data']['링크']="인덱싱 오류로 적합한 데이터 추출 실패"
    out['raw_meta_data']['태그']="인덱싱 오류로 적합한 데이터 추출 실패"
    out['raw_meta_data']['조회수']="인덱싱 오류로 적합한 데이터 추출 실패"
    out['raw_meta_data']['제목']="인덱싱 오류로 적합한 데이터 추출 실패"
    out['raw_meta_data']['유튜버']="인덱싱 오류로 적합한 데이터 추출 실패"
    out['raw_meta_data']['업로드일']="인덱싱 오류로 적합한 데이터 추출 실패"
    out['raw_meta_data']['설명']="인덱싱 오류로 적합한 데이터 추출 실패"
    out['raw_meta_data']['자막']="인덱싱 오류로 적합한 데이터 추출 실패"
    out['llm_process_data']['자막요약']="인덱싱 오류로 적합한 데이터 추출 실패"
    out['llm_process_data']['코드']="인덱싱 오류로 적합한 데이터 추출 실패"
    out['llm_process_data']['timestamps']="적합한 데이터 추론 실패"
    out['llm_process_data']['timestampsdiscriptions']="적합한 데이터 추론 실패"
    out['llm_process_data']['seconds']="적합한 데이터 추론 실패"
    out['llm_process_data']['descriptions']="적합한 데이터 추론 실패"
    out['llm_process_data']['codes']="적합한 데이터 추론 실패"
    out['llm_process_data']['clip']="적합한 데이터 추론 실패"
    log_wrapper("<<::STATE::INFERENCE FAILL>>")
    outputdict={}
    outputdict['youtube']=out
    return outputdict, ['youtube','llm_process_data','raw_meta_data'],None
    
def print_with_output(filtter,query):
    # 환경변수(.env 파일) 로드: OPENAI_API_KEY 등이 설정되어 있어야 합니다.
    log_wrapper("<<::STATE::START INFERENCE>>")
    start_time=time.time()
    filtter.enhance_query(query)
    neg,pos=filtter.get_keywords_sametime()
    outs,_=filtter.keyword_filter()
    log_wrapper(f"<<::STATE::KEYWORD FILTTERED>>키워드 필터링 결과 : {outs}")
    if outs.empty:
        log_wrapper("추천 영상이 없습니다.")
        log_wrapper("재시도 로직 필요함")
        return retrun_fail_result() 
    log_wrapper(f"<<::STATE:: RETRIEVAL START>>")
    RAG_out=RAGOUT(filtter,outs)
    log_wrapper(f"<<::STATE:: RETRIEVAL FNISH>>")
    log_wrapper(f"RAG 출력 : {RAG_out.sorted_result}")
    extractor=Video_extractor(RAG_out)
    log_wrapper(f"<<::STATE::CLIP EXTRACTION START>>")
    out=extractor.short_process()
    log_wrapper(f"<<::STATE::CLIP EXTRACTION FINISH>>")
    spend_time=time.time()-start_time

    log_wrapper(f"소모시간 : {spend_time}")
    LLMO=out['llm_process_data']
    RAW=out['raw_meta_data']
    if LLMO['seconds']:
        q=0
        for i in LLMO['timestampsdiscriptions']:
            log_wrapper(f'주요 장면 {q} : {i}')
    else:
        log_wrapper(f'{LLMO["descriptions"]}')
    log_wrapper(f' 클립 : {LLMO['clip']}')
    log_wrapper(f'테스트 완료 추출 영상-> 제목 : {RAW['제목']}\n 입력 쿼리 :{RAG_out.enhanced_query}')
    log_wrapper(f'테스트 완료 추출 영상-> 링크 : {RAW['링크']}\n 입력 쿼리 :{RAG_out.enhanced_query}')
    log_wrapper(f' 키워드 : {RAW['태그']} 업로드일 :{RAW['업로드일']}')
    if RAG_out.marker:
        log_wrapper("<<::STATE::INFERENCE SUCCESSED>>")
    outputdict={}
    outputdict['youtube']=out
    return outputdict, ['youtube','llm_process_data','raw_meta_data'],RAG_out
    


if __name__ == "__main__":
    # 환경변수(.env 파일) 로드: OPENAI_API_KEY 등이 설정되어 있어야 합니다.
    start_time=time.time()
    filtter=Keyword_filter()
    #filtter.dataloader.DataProcessor.set_day_limit()
    #filtter.dataloader.DataProcessor.make_hesh_dict()
    query="갤럭시 탭 s10 리뷰"
    filtter.enhance_query(query)
    neg,pos=filtter.get_keywords_sametime()
    outs,_=filtter.keyword_filter()
    if outs.empty:
        log_wrapper("추천 영상이 없습니다.")
        log_wrapper("재시도 로직 필요함")
    #RAG_out,result=filtter.RAG_search()
    RAG_out=RAGOUT(filtter)
    log_wrapper(f"RAG 출력 : {RAG_out.sorted_result}")

    extractor=Video_extractor(RAG_out)
    out=extractor.short_process()
    spend_time=time.time()-start_time

    log_wrapper(f"소모시간 : {spend_time}")
    LLMO=out['llm_process_data']
    RAW=out['raw_meta_data']
    if LLMO['seconds']:
        q=0
        for i in LLMO['timestampsdiscriptions']:
            log_wrapper(f'주요 장면 {q} : {i}')
    else:
        log_wrapper(f'{LLMO["descriptions"]}')
    log_wrapper(f' 클립 : {LLMO['clip']}')
    log_wrapper(f'테스트 완료 추출 영상-> 제목 : {RAW['제목']}\n 입력 쿼리 :{RAG_out.enhanced_query}')
    log_wrapper(f'테스트 완료 추출 영상-> 링크 : {RAW['링크']}\n 입력 쿼리 :{RAG_out.enhanced_query}')
    log_wrapper(f' 키워드 : {RAW['태그']} 업로드일 :{RAW['업로드일']}')
    
    
