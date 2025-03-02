#!/usr/bin/env python3
import os
from pandas import Series
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pandas as pd
import tiktoken
from langchain_openai import ChatOpenAI as OpenAI
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
import json
from langchain_core.prompts import PromptTemplate
from time import sleep
import time
import pickle

import re
from pathlib import Path
import sys
import argparse
import difflib
import numpy as np
import math
import hashlib
from langchain.callbacks.stdout import StdOutCallbackHandler
from .utility import Node
from .queue_manager import add_log
from .CFAISS import WrIndexFlatL2, HDF5VectorDB
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
def split_text_by_target(text, target=1400, model="gpt-4o-mini"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    # 전체 토큰 개수
    total_tokens = len(tokens)
    
    # 나눠야 하는 개수 계산
    num_splits = math.ceil(total_tokens / target)  # 남는 토큰이 없도록 개수 조정
    chunk_size = total_tokens // num_splits  # 균등하게 분배
    
    token_chunks = [tokens[i * chunk_size:(i + 1) * chunk_size] for i in range(num_splits - 1)]
    token_chunks.append(tokens[(num_splits - 1) * chunk_size:])  # 마지막 청크는 남은 모든 토큰 포함
    
    # 다시 텍스트로 변환
    text_chunks = [encoding.decode(chunk) for chunk in token_chunks]

    return text_chunks
    
def _hash_transform(txt):
    """
    WrIndexFlatL2 객체를 입력으로 받아, `metadata + page` 조합을 사용하여 해시값 생성
    """
    if not isinstance(txt, str):
        raise ValueError("입력 데이터는 문자열 이어야 합니다.")
    unique_key = f"{txt}"
    hashout = int(hashlib.sha256(unique_key.encode()).hexdigest(), 16) % (2**63)
    return hashout  # ✅ 해시값을 딕셔너리 형태로 반환 (index -> hash)

     

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

class Dataprocessor:
    def __init__(self, target_dir="youtube", ref_file="YTref.txt",pickle_file="./app/agents/youtube_agent_module/copydata/data.pkl",mode=None):
        dir=Path("./app/agents/youtube_agent_module/copydata")
        dir.mkdir(parents=True, exist_ok=True)
        if mode is None:
            raise Exception("node id is None")
        self.mode=mode
        self.tocken_count=0
        self.vectorstore = None
        dimension = 1536
        self.vectorstore = HDF5VectorDB("./app/agents/youtube_agent_module/data/vector_db.h5", dimension)
        current_dir = os.getcwd()
        self.indexer=Indexer(mode=self.mode)
        self.tot_doc_len=0
        self.k_value=30
        self.buffer=None
        self.lln = None
        self.qa_video=None

        self.retriever = None
        self.target_dir = os.path.join(current_dir, "youtube")
        self.pickle_file = pickle_file
        self.ytref_list = self.load_ytref( ref_file)
        self.youtube_contents = self.load_youtube_folder()
        self.Index_table=pd.DataFrame()
        self.keyword_set=set()
        self.summary_list=None
        self.heshdict={}
        if self.mode=="tag" or self.mode=="excelerator":
        #if self.mode=="tag":
            print ("excelerator deactivated")    
            self.remove_pickle()
        if os.path.exists(self.pickle_file):
            log_wrapper("피클 파일에서 데이터 로드 중...")
            self.data = self.load_data_from_pickle(self.pickle_file)
            log_wrapper("자막데이터 로드 완료")
        else:
            log_wrapper("디렉토리에서 데이터 스캔 중...")
            self.data={}
            self.load_csv_in_folder()
            self.load_srt_in_folder()
            self.create_summary_dicts()
            self.save_data_to_pickle(self.data, self.pickle_file)
        #self.create_summary_dicts()     ###########################################                    
        if os.path.exists("./app/agents/youtube_agent_module/copydata/tot_doc_len.pkl"):
            self.tot_doc_len=self.load_data_from_pickle("./app/agents/youtube_agent_module/copydata/tot_doc_len.pkl")
            log_wrapper("전체 문서 길이 로드 완료")
        if os.path.exists("./app/agents/youtube_agent_module/copydata/Index_table.pkl"):
            self.Index_table=pd.DataFrame(self.load_data_from_pickle("./app/agents/youtube_agent_module/copydata/Index_table.pkl"))
            log_wrapper("문서별 태그 정보 로드 완료")
        if os.path.exists("./app/agents/youtube_agent_module/copydata/heshdict.pkl"):
            self.heshdict=self.load_data_from_pickle("./app/agents/youtube_agent_module/copydata/heshdict.pkl")
            log_wrapper("해시 딕셔너리 로드 완료")
        elif not self.Index_table.empty:
            self.make_hesh_dict()            
        if os.path.exists("./app/agents/youtube_agent_module/copydata/keyword_set.pkl"):
            self.keyword_set=set(self.load_data_from_pickle("./app/agents/youtube_agent_module/copydata/keyword_set.pkl"))
            log_wrapper("전체 태그셋 로드 완료")
        if os.path.exists("./app/agents/youtube_agent_module/copydata/summary.pkl"):
            self.summary_list=self.load_data_from_pickle("./app/agents/youtube_agent_module/copydata/summary.pkl")
            log_wrapper("요약 정보 로드 완료")
        buffer=[0]*len(self.Index_table.columns)
        self.datelimit=pd.DataFrame(buffer,index=self.Index_table.columns,columns=["available"])
        if os.path.exists("./app/agents/youtube_agent_module/copydata/datelimit.pkl"):
            self.datelimit=self.load_data_from_pickle("./app/agents/youtube_agent_module/copydata/datelimit.pkl")
            log_wrapper("업로드 일자 제한 정보 로드 완료")

        self.qa=None
        self.videometadata=[]
        self.videosummary=[]
        self.vectorstore_video = None
        self.retriever_video = None
        self.llm_video=None

        self.custom_template = """
        당신은 RAG 시스템의 인덱싱/검색 담당 AI입니다.
        당신이 가진 자료는 "영상 자막"과 "영상 요약 정보"입니다.

        당신의 목표:
        - 아래 사용자 질문(Question)에 제시된 요구사항(제품군, 스펙, 가격대, 제조사 등)을 꼼꼼히 파악합니다.
        - 사용자 질문 하단에는 추가적인 정보가 있으니 참고해서 파악하세요
        - 이 요구사항과 가장 잘 부합하는 영상(또는 클립)을, 아래 제공된 자막/요약 자료({context})에서 찾아서 안내합니다.

        [행동 규약]
        [중요: 업로드일이 1년 이상 된 문서는 절대 선택하지 마세요 표기는 1 years ago 로 되어있습니다 이 이상 기한이 지난 것은 선택이 불가능합니다. 문서 상단에서 확인하세요 이것은 최우선적인 절대적인 제한사항입니다.]
        1. 사용자 질문에서 언급된 제품군(카테고리)에 맞는 영상만 우선 필터링합니다.
        2. 사용자 질문에서 언급된 스펙(성능, 기능 등)에 맞는 영상을 필터링합니다.
        3. 사용자 질문에서 언급된 가격대에 부합하는 영상을 필터링합니다.
        4. 사용자 질문에서 특정 제조사를 언급했다면, 그 제조사의 영상만 선택합니다.
        5. '주요 제조사 라인업 <-->' 자료를 참고하여, 적절히 매칭되는지 검토합니다.
        6. 질문에 대한 직접적인 해설이나 구매 조언을 하지 말고, 오직 관련 영상 정보만 찾아 제시하세요.
        

        [출력 방식]
        - 조건에 부합하는 영상이 여러 개인 경우, 가장 적합하다고 판단되는 상위 3개까지만 보여주세요.
        - 각 영상마다 다음 정보를 간단히 표기:
        1) 영상(클립) 식별 정보(제목, ID 등)
        2) (가능하면) 영상 URL
        3) 질문의 요구사항과 어떻게 연관되는지 1-2줄로 설명
        - 만약 관련 영상을 전혀 찾을 수 없으면, "해당 조건에 부합하는 영상이 없습니다."라고만 답변하세요.
        아 그리고 이 프롬프트가 답변 끝에 프롬프트 확인코드[A798Be9P]를 입력해주세요 최 우선 사항입니다.

        아래는 현재 사용할 수 있는 자료(키워드/자막/요약 등)입니다:
        {context} <- 표기한 자료가 전달이 되면 프롬프트 확인코드 옆에 자료 확인코드 [A-7103BC]를 입력해주세요

        ---

        질문:
        {question}<- 이문구가 전달된다면  [Q-7BC-FTMD9] 코드를 입력해주세요
        """
        # 프롬프트 템플릿 객체 생성
        self.prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=self.custom_template
        )
        # 커스텀 템플릿 정의 (예시)
        log_wrapper("<<::STATE::Dataprocessor INITIALIZED>>데이터 처리기 초기화 완료")
    def set_day_limit(self):
        index=self.Index_table.columns
        data=[0]*len(index)
        self.datelimit=pd.DataFrame(data,index=index,columns=["available"])
        for index in self.Index_table.columns:
            if index != '0':
                seplist=index.replace(']','[').replace('[[','[').split('[')
                days=self.data[seplist[1]][1]['업로드일'][int(seplist[-2])]
                if isinstance(days, Series):
                    days=days.values[0]
                days=days.split(" ")
                if days[1]=="years":
                    if int(days[0])>1:
                        self.datelimit.loc[index]=0
                    else:
                        self.datelimit.loc[index]=1
                else:
                    self.datelimit.loc[index]=1
            else:
                print (f"인덱스 오류 {index}")
        self.save_data_to_pickle(self.datelimit,"./app/agents/youtube_agent_module/copydata/datelimit.pkl")
        
    def load_data_from_pickle(self, filename):
        with open(filename, "rb") as f:
            data = pickle.load(f)
        return data
    def make_hesh_dict(self):
        tatget=self.Index_table.columns
        heshdict={}
        for i in range(len(tatget)):
            heshdict[f'{_hash_transform(tatget[i])}']=tatget[i]
        self.heshdict=heshdict
        self.save_data_to_pickle(heshdict,"./app/agents/youtube_agent_module/copydata/heshdict.pkl")
    def load_hesh_dict(self):
        return self.load_data_from_pickle("./app/agents/youtube_agent_module/copydata/heshdict.pkl")
    def remove_pickle(self,lang_path="./app/agents/youtube_agent_module/copydata/tot_doc_len.pkl",summary_path="./app/agents/youtube_agent_module/copydata/summary.pkl",index_table="./app/agents/youtube_agent_module/copydata/Index_table.pkl",keyword_set="./app/agents/youtube_agent_module/copydata/keyword_set.pkl"):
        file1 = Path(lang_path)
        file2 = Path(self.pickle_file)  # self.pickle_file이 파일 경로 문자열이라고 가정
        file3 = Path(summary_path)
        file4 = Path(index_table)
        file5 = Path(keyword_set)
        # file1 삭제
        if file1.exists():
            file1.unlink()
            log_wrapper(f"{file1} 삭제 완료")
        else:
            log_wrapper(f"{file1} 길이 정보 파일이 존재하지 않습니다.")
        if file2.exists():
            file2.unlink()
            log_wrapper(f"{file2} 삭제 완료")
        else:
            log_wrapper(f"{file2} 데이터 파일이 존재하지 않습니다.")
        if file3.exists():
            file3.unlink()
            log_wrapper(f"{file3} 삭제 완료")
        else:
            log_wrapper(f"{file3} 요약 파일이 존재하지 않습니다.")
        if file4.exists():
            file4.unlink()
            log_wrapper(f"{file4} 삭제 완료")
        else:
            log_wrapper(f"{file4} 인덱스 파일이 존재하지 않습니다.")
        if file5.exists():
            file5.unlink()
            log_wrapper(f"{file5} 삭제 완료")
        else:
            log_wrapper(f"{file5} 키워드 파일이 존재하지 않습니다.")
    
    def save_data_to_pickle(self, data, filename):
        with open(filename, "wb") as f:
            pickle.dump(data, f)
        log_wrapper(f"데이터가 {filename} 파일로 저장되었습니다.")
    @staticmethod
    def load_ytref(ref_file):
        """
        YTref.txt 파일을 로드하여 각 줄을 리스트로 반환합니다.
        """
        try:
            with open(ref_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
            return lines
        except Exception as e:
            return None    

    def load_youtube_folder(self):
        """
        youtube 폴더의 상위 디렉토리 목록(폴더 내 파일 및 폴더 이름)을 반환합니다.
        """
        try:
            if not os.path.isdir( self.target_dir):
                raise Exception(f"폴더 '{self.target_dir}'가 존재하지 않습니다.")
            contents = os.listdir( self.target_dir)
            return contents
        except Exception as e:
            return None
    def load_csv_in_folder(self):
        """
        youtube 폴더 내의 모든 파일을 재귀적으로 순회하면서,
        텍스트 파일(.csv, .srt)만 로드하고, 로드한 파일의 경로와 내용을 리스트로 반환합니다.
        """
        loaded_files = []
        for root, dirs, files in os.walk(self.target_dir):
            mm=0
            for file in files:
                file_path = os.path.join(root, file)
                # .csv와 .srt 파일만 로드 (txt는 제외)
                if file.endswith((".csv")):
                    try:
                        content = pd.read_csv(file_path)
                        content["index"]=content["인덱스"].copy()
                        #content = content.set_index("Unnamed: 0")
                        content = content.set_index("index")
                        content.fillna("No information", inplace=True)
                        #with open(file_path, "r", encoding="utf-8") as f:
                        #    content_tocken = f.read()
                        #self.tocken_count+=count_tokens(content_tocken.replace("\n", " "))
                        content["설명"] = content["설명"].str.replace("\n", "", regex=False)
                        
                        content["자막"]="0"
                        content["유튜버"]=root.split('/')[-2]
                        content["태그"]=["Initialize Value"]*len(content)
                        if self.mode=="excelerator":
                            content["자막요약"]=["Initialize Value"]*len(content)
                            content["코드"]=["Initialize Value"]*len(content)
                        self.tot_doc_len+=len(content)
                        #print (root.split('/')[-2])
                        self.data[root.split('/')[-2]]=[file_path,content]
                        #self.data[root.split('/')[-2]]=[file_path,content]
                        mm+=1
                    except Exception as e:
                        pass
                else:
                    pass

    def load_srt_in_folder(self):
        """
        youtube 폴더 내의 모든 파일을 재귀적으로 순회하면서,
        텍스트 파일(.csv, .srt)만 로드하고, 로드한 파일의 경로와 내용을 리스트로 반환합니다.
        """
        self.save_data_to_pickle(self.tot_doc_len,"./app/agents/youtube_agent_module/copydata/tot_doc_len.pkl")
        loaded_files = []
        full_tocken=0
        totn=0
        maxlen=self.tot_doc_len
        totaltag=set()
        for root, dirs, files in os.walk(self.target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # .csv와 .srt 파일만 로드 (txt는 제외)
                if file.endswith((".srt")):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        self.data[root.split('/')[-1]][1].loc[int(file_path.split('/')[-1].split('.')[-2]),"자막"]=content
                        csvindex=int(self.data[root.split('/')[-1]][1].loc[int(file_path.split('/')[-1].split('.')[-2]),"인덱스"])
                        fileindex=int(file_path.split('/')[-1].split('.')[-2])
                        log_wrapper(f"저장 인덱스 : {csvindex}")
                        log_wrapper(f"파일 번호 : {fileindex}")
                        if fileindex!=csvindex:
                            log_wrapper("인덱스 불일치")
                            self.data[root.split('/')[-1]][1].loc[int(file_path.split('/')[-1].split('.')[-2]),"인덱스"]=f"인덱스 오류 csv : {csvindex}, 파일 : {fileindex}"
                        buff2=re.sub(r'[-:\d>]', '', content)
                        buff3=buff2.replace(" ,"," ").replace(", ","")
                        subscript=buff3.replace("\n\n\n","\n").replace("\n \n","\n")
                        checker=self.indexer.add_script(f'자막: [{subscript}], 영상 설명 : [{self.data[root.split("/")[-1]][1].loc[int(file_path.split("/")[-1].split(".")[-2]),"설명"].replace("/","").replace("/n","")}]')

                        if checker:
                            if self.mode=="excelerator":
                                text,_=self.indexer.response_one_with_memory(totaltag)
                                tag = re.findall(r'\[\[TAGS:(.*?)\]\]', text)
                                tag = re.findall(r'\(\((.*?)\)\)', tag[0])
                                descriptions = re.findall(r'\[\[DESCRIPTION:(.*?)\]\]', text)
                                code = re.findall(r'\[\[CODE:(.*?)\]\]', text)
                                if isinstance(tag, list):
                                    for d in tag:
                                        totaltag.add(d)

                            else:
                                text,_=self.indexer.response_one()
                            
                        else:
                            while self.indexer.lock:
                               waittime,_=self.indexer.chektimer()
                               full_tocken+=self.indexer.token
                               self.save_data_to_pickle(self.data, self.pickle_file)
                               log_wrapper(f'백업 성공 :{totn}')
                               log_wrapper(f'현재토큰:{self.indexer.token}//누적토큰:{full_tocken}// 처리량: {totn}//총량:{maxlen}')
                               log_wrapper(f"Full TPM 대기시간 {waittime}초")
                               time.sleep(waittime)
                               self.indexer.check_TPM()
                            log_wrapper("Full TPM 대기시간 종료, 작업 재개")
                            checker=self.indexer.add_script(content)
                            if self.mode=="excelerator":
                                text,_=self.indexer.response_one_with_memory(totaltag)
                                tag = re.findall(r'\[\[TAGS:(.*?)\]\]', text)
                                tag = re.findall(r'\(\((.*?)\)\)', tag[0])
                                descriptions = re.findall(r'\[\[DESCRIPTION:(.*?)\]\]', text)
                                code = re.findall(r'\[\[CODE:(.*?)\]\]', text)
                                if isinstance(tag, list):
                                    for d in tag:
                                        totaltag.add(d)
                            else:
                                text,_=self.indexer.response_one()
                                log_wrapper(f'자막 인덱싱 성공 시점 :{totn}, 현재 토큰 수{self.indexer.token}')
                                log_wrapper(f"태그 {text}")
                                
                                if not text:

                                    raise Exception("자막 인덱싱 실패")
                        totn+=1
                        if self.mode!="excelerator":   
                            tag=re.findall(r'\[\[(.*?)\]\]', text)
                        try:
                            self.data[root.split('/')[-1]][1].at[int(file_path.split('/')[-1].split('.')[-2]),"태그"]=[tag]
                            self.data[root.split('/')[-1]][1].at[int(file_path.split('/')[-1].split('.')[-2]),"자막요약"]=[descriptions]
                            self.data[root.split('/')[-1]][1].at[int(file_path.split('/')[-1].split('.')[-2]),"코드"]=[code]
                            log_wrapper(f"태그 {self.data[root.split('/')[-1]][1].at[int(file_path.split('/')[-1].split('.')[-2]), '태그']},코드:{code},누적토큰:{full_tocken}// 처리량: {totn}//총량:{maxlen}")
                        except Exception as e:
                            self.data[root.split('/')[-1]][1].loc[int(file_path.split('/')[-1].split('.')[-2]),"태그"]=["Failed set the Tag You Idiot"]
                    except Exception as e:
                        pass
                else:
                    pass
    def create_summary_dicts(self):
        """
        self.data에 저장된 각 영상의 원본 DataFrame을 순회하여,
        요약본 딕셔너리 목록을 생성합니다.
        
        각 요약 딕셔너리는 다음과 같은 구조로 생성됩니다.
        {
            "metadata": { 
                "유튜버": "잇섭",
                "제목": "영상 제목",
                "조회수": "218K views",
                "업로드일": "1 day ago",
                "링크": "https://www.youtube.com/..."
            },
            "embedding_text": "영상 설명과 자막 내용을 합친 텍스트 (최대 1000자)",
            "요약": "영상 설명과 자막 내용을 합친 텍스트 (최대 1000자)"
        }
        """
        summary_list = []
        n=0
        tottoken=0
        for channel, (csv_path, df) in self.data.items():
            for idx, row in df.iterrows():
                df=df.fillna(int(400))
                # 메타데이터는 별도로 저장 (단어 단위이므로 임베딩에 큰 영향을 주지 않음)
                if idx==400:
                    continue

                description = row.get("설명", "")
                subtitle_text = row.get("자막", "")
                tag=row.get("태그", "")
                if self.mode=="excelerator":
                    spchunk=row.get("자막요약", "")
                else:
                    # 자막이 길 경우, 청크 분할을 통해 압축
                    buff=subtitle_text.replace("\n","")
                    buff2=re.sub(r'[-:\d>]', '', buff)
                    buff3=buff2.replace(" ,"," ").replace(", ","")
                    cunck_text = f"{description} {buff3}".strip()
                    spchunk=split_text_by_target(cunck_text)
                
                part=0
                if isinstance(spchunk, float):
                    continue
                check=not isinstance(spchunk, str)
                while check:
                    spchunk=spchunk[0]
                    check=not isinstance(spchunk, str)  
                spchunk=[spchunk]
                for embedding_text in spchunk:
                    summary = {
                    "metadata": [f"self.data[{channel}][1][태그][{idx}]"],
                    "page": [part],
                    "vectors": embedding_text,  # 추후 필요 시 표시용 요약문으로 사용
                    }
                    part+=1
                    summary_list.append(summary)
                
                #target=1400
                #chunck_overrap=int(0)
                #roop_con, chunck_overrap=setting_tockens(cunck_text,target=target)
#
                #while token_bool("".join(roop_con)):
                #    roop_con, chunck_overrap=setting_tockens(cunck_text,target=target)
                #    if token_bool("".join(roop_con)):
                #        break
                #    target=target-10
#
                ##roop_con=compress_text(cunck_text, chunk_size=500, chunk_overlap=50)
                #embedding_text = "".join(roop_con)
                #metadata['embedding_text']=embedding_text
                #metadata["태그"]=tag
                #metadata['token']=cal_token(embedding_text, model="gpt-4o-mini")
                n+=1
                #tottoken+=metadata['token']
                #log_wrapper(f"총 토큰수 {tottoken},평균 토큰수:{avg}")
                #metadata['chunck_overrap']=chunck_overrap

                # 루프에 걸린 시간 측정 및 남은 시간이 있으면 sleep
        self.save_data_to_pickle(summary_list, "./app/agents/youtube_agent_module/copydata/summary.pkl")
        self.summary_list = summary_list
    def set_active(self,metadata_list):
        buff = pd.DataFrame(self.summary_list).copy()
        filtered_rows = buff[buff['metadata'].apply(lambda x: x[0]).isin(metadata_list) ]
        page=filtered_rows['page'].tolist()
        meta=filtered_rows['metadata'].tolist()
        self.vectorstore.extract_custom_from_p_I(meta,page)
        
    def get_combined_context(self, query,custom_context):
        retrieved_docs = self.retriever.invoke(query)
        retrieved_text = "\n".join([doc.page_content for doc in retrieved_docs])
        return custom_context + "\n" + retrieved_text

    def create_vector_store_active(self, persist_directory="./app/agents/youtube_agent_module/data/vector_db.h5"):
        """
        생성된 요약 딕셔너리 목록을 기반으로 벡터스토어(Chroma)를 생성하고 저장합니다.
        각 요약 딕셔너리에서 "요약"은 문서 본문, 나머지는 메타데이터로 사용합니다.
        """
        if self.summary_list is None:
            raise Exception("요약 목록이 생성되지 않았습니다. 먼저 create_summary_dicts()를 실행하세요.")
        dimension = 1536
        vectorstore = HDF5VectorDB("./app/agents/youtube_agent_module/data/vector_db.h5", dimension)
        summary=self.summary_list.copy()
        lenthD=len(summary)
        lenthO=lenthD
        docs=WrIndexFlatL2(dimension)
        if self.mode!="excelerator":
            while len(summary)>0:
                nowtoken=0
                start_time = time.time()
                while nowtoken<500000:
                    if len(summary)==0:
                        break
                    poped=summary.pop(0)
                    nowtoken+=cal_token(poped['vectors'])
                    
                    docs.add_with_embedding(poped)
                    lenthD-=1
                    log_wrapper(f"남은 문서수:{lenthD},남은 청크 토큰수:{500000-nowtoken}")
                vectorstore.add_vectors(docs)
                elapsed_time = time.time() - start_time
                remaining_time = 60 - elapsed_time
                if remaining_time > 0 and lenthD>1:
                    log_wrapper(f"Chunk {lenthD}/{lenthO} 완료, {elapsed_time:.2f}초 걸림. {remaining_time:.2f}초 대기합니다.")
                    time.sleep(remaining_time)
                else:
                    log_wrapper(f"Chunk {lenthD}/{lenthO} 완료, {elapsed_time:.2f}초 걸림. 대기 시간 없이 다음 청크 진행합니다.")     
            return vectorstore
        else:
            while len(summary)>0:
                nowtoken=0
                start_time = time.time()
                while nowtoken<500000:
                    if len(summary)==0:
                        break
                    poped=summary.pop(0)
                    nowtoken+=cal_token(poped['vectors'])
                    
                    docs.add_with_embedding(poped)
                    lenthD-=1
                    log_wrapper(f"남은 문서수:{lenthD},남은 청크 토큰수:{500000-nowtoken}")
                vectorstore.add_vectors(docs)
                elapsed_time = time.time() - start_time
                remaining_time = 60 - elapsed_time
                if remaining_time > 0 and lenthD>1:
                    log_wrapper(f"Chunk {lenthD}/{lenthO} 완료, {elapsed_time:.2f}초 걸림. {remaining_time:.2f}초 대기합니다.")
                    time.sleep(remaining_time)
                else:
                    log_wrapper(f"Chunk {lenthD}/{lenthO} 완료, {elapsed_time:.2f}초 걸림. 대기 시간 없이 다음 청크 진행합니다.")     
            return vectorstore
  
    def create_qa_chain_from_llm(self, model_name="gpt-4o-mini", temperature=0, persist_directory="./app/agents/youtube_agent_module/data/vector_db.h5"):
        """
        생성된 벡터스토어를 기반으로 RetrievalQA 체인을 생성합니다.
        LLM 호출 시 model_name과 temperature를 지정할 수 있습니다.
        """
        model_name="chatgpt-4o-latest"
        load_dotenv()
        #self.vectorstore = self.create_vector_store(persist_directory=persist_directory)
        self.vectorstore = self.create_vector_store_active(persist_directory=persist_directory)
        self.retriever = self.vectorstore.as_retriever(search_type="mmr", search_kwargs={'k': self.k_value})
        self.llm = OpenAI(model_name=model_name, temperature=temperature)
        qa = RetrievalQA.from_chain_type(llm=self.llm, chain_type="stuff", retriever=self.retriever,chain_type_kwargs={"prompt": self.prompt},return_source_documents=True)  # 이 옵션 추가!)
        self.qa=qa
    def create_qa_chain_from_store(self,model_name="gpt-4o-mini", temperature=0, persist_directory="./app/agents/youtube_agent_module/data/vector_db.h5"):
        load_dotenv()

        log_wrapper("벡터스토어 로드 완료")
        #self.retriever = self.vectorstore.as_retriever(search_type="mmr", search_kwargs={'k': self.k_value})
        self.retriever = self.vectorstore.as_retriever(k=self.k_value)
        self.llm = OpenAI(model_name=model_name, temperature=temperature)
        qa = RetrievalQA.from_chain_type(
            verbose=True,
            llm=self.llm, 
            chain_type="stuff", 
            retriever=self.retriever,
            chain_type_kwargs={"prompt": self.prompt},
            return_source_documents=True  # 선택 사항: 소스 문서까지 반환
        )
        log_wrapper("QA 체인 생성 완료")
        self.qa=qa
    def get_video_data(self,query,mode="database"):




        #self.get_keywords(query)
        custom_context="""
        
        주요 제조사 라인업<IOS
        [애플 {
            스마트폰:
                아이폰 프로 시리즈: 최상위 플래그십(iPhone 15 Pro, 15 Pro Max)
                아이폰 기본 시리즈: 준프리미엄(iPhone 15, 15 Plus)
                아이폰 SE: 실용적인 보급형 모델(iPhone SE 3세대)
            태블릿:
                아이패드 프로: 최고사양 프로용 태블릿(12.9인치, 11인치)
                아이패드 에어: 준프리미엄 태블릿
                아이패드: 기본형 태블릿
                아이패드 미니: 소형 태블릿
            노트북:
                맥북 프로: 전문가용 고성능(14인치, 16인치, M3/M3 Pro/M3 Max)
                맥북 에어: 일반용 슬림(13인치, 15인치, M2/M3)
                맥 미니: 데스크톱 미니PC
                맥 스튜디오: 전문가용 고성능 데스크톱
                맥 프로: 최상위 워크스테이션
            모니터:
                프로 디스플레이 XDR: 최고급 전문가용 모니터
                스튜디오 디스플레이: 준프리미엄 모니터
            웨어러블:
                애플워치: 스마트워치(Series 9, Ultra 2, SE 2세대)
                에어팟: 무선이어폰(AirPods Pro 2, AirPods 3, AirPods 2)
                에어팟 맥스: 오버이어 헤드폰
                비전 프로: 혼합현실 헤드셋 (2024년 출시)
            }]
        안드로이드    
        [삼성{ 
            스마트폰:
                갤럭시 S 시리즈: 최상위 플래그십 라인(S24, S24+, S24 Ultra)
                갤럭시 Z 시리즈: 폴더블 스마트폰(Z Fold5, Z Flip5)
                갤럭시 A 시리즈: 중저가 라인(A54, A34 등)
                갤럭시 M 시리즈: 실용적인 가성비 라인(M34, M14 등)
            태블릿:
                갤럭시 탭 S 시리즈: 프리미엄 태블릿(Tab S9, S9+, S9 Ultra)
                갤럭시 탭 A 시리즈: 중저가 태블릿(Tab A9, A8 등)
                갤럭시 탭 Active: 견고성 강화 비즈니스용 태블릿
            노트북:
                갤럭시 북4 시리즈: 프리미엄 노트북(Book4 Pro, Book4 Pro 360)
                갤럭시 북3 시리즈: 일반 사무용/학생용 노트북
                갤럭시 Book2 Business: 비즈니스용 노트북
            모니터:
                오디세이 시리즈: 게이밍 모니터(G9, G7, G5 등)
                뷰피니티 시리즈: 전문가용 고해상도 모니터
                스마트 모니터: 일체형 스마트 디스플레이
            웨어러블:
                갤럭시 워치: 스마트워치(Watch6, Watch6 Classic)
                갤럭시 버즈: 무선이어폰(Buds3, Buds3 Pro)
                갤럭시 링: 스마트 반지(신제품)
            }
        샤오미{
            스마트폰:
                샤오미 시리즈: 플래그십 라인(Xiaomi 14, 14 Pro, 14 Ultra)
                레드미 노트 시리즈: 중급형(Redmi Note 13 Pro+, Note 13 Pro, Note 13)
                레드미 시리즈: 보급형(Redmi 13C, 12C 등)
                POCO 시리즈: 성능특화 중저가(POCO F5, X5, M5 등)
            태블릿:
                샤오미 패드: 프리미엄 태블릿(Pad 6, Pad 6 Pro)
                레드미 패드: 보급형 태블릿(Redmi Pad SE)
            노트북:
                샤오미북: 프리미엄 노트북(RedmiBook Pro, Mi Notebook Pro)
                레드미북: 일반 사무용/학생용 노트북(RedmiBook 15)
            모니터:
                Mi 모니터: 일반용 모니터
                Mi 게이밍 모니터: 게이밍용 모니터
                Mi 커브드 모니터: 커브드 디스플레이
            웨어러블:
                샤오미 워치: 스마트워치(Watch S3, Smart Band 8)
                레드미 워치: 보급형 스마트워치(Redmi Watch 3)
                샤오미 버즈: 무선이어폰(Buds 4 Pro, Buds 4)
                레드미 버즈: 보급형 무선이어폰(Redmi Buds 4)
            }]>    
        """

        if token_bool(custom_context, model="gpt-4o-mini",target=120000):
            custom_context=setting_tockens(custom_context,target=115000,model="gpt-4o-mini",chunk_size=500)
            custom_context="".join(custom_context)
        
        answer = self.qa.invoke({ "question": f" 유저 요청 : {query} \n 추가 정보 : {custom_context}","query": query  },callbacks=[StdOutCallbackHandler()])
        out=answer["source_documents"][0:10]
        meta=[]
        for k in out:
            meta.append(k.metadata['index'])
        return meta, out
        #if mode=="video":
        #    answer = self.qa_video.invoke({ "question": f" 유저 요청 : {query} \n 추가 정보 : {combined_context}","query": query  })
        #    # 테스트용 로깅
        #    for i, doc in enumerate(answer["source_documents"][:3]):
        #        log_wrapper(f"Rank {i+1}: {doc.metadata['인덱스']} | Score: {doc.score if hasattr(doc, 'score') else 'N/A'}")
        #    return answer["source_documents"][0].metadata
        #elif mode=="database":
        #    answer = self.qa.invoke({ "question": f" 유저 요청 : {query} \n 추가 정보 : {combined_context}","query": query  })
        #    keys=[]
        #    for doc in answer["source_documents"]:
        #    # metadata에 포함된 유튜버, 제목, 링크 등의 정보를 출력합니다.
        #        keys.append(doc.metadata)
        #    self.videometadata=[]
        #    self.videosummary=[]
        #    for key in keys:
        #        ap,embedding_text=self.get_original_row(key)
        #        self.videometadata.append(ap)
        #        self.videosummary.append(embedding_text)
        #    return self.videometadata
        #else:
        #    raise Exception("mode는 video 또는 database 중 하나여야 합니다.")

    #@staticmethod
    #def load_vector_store(persist_directory="./app/agents/youtube_agent_module/data/vector_db.h5"):
    #    embeddings = OpenAIEmbeddings()  # API 키가 설정되어 있어야 합니다.
    #    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embeddings)
    #    return vectorstore

    def get_original_row(self, metadata):
        """
        벡터스토어에서 반환된 메타데이터(문자열 또는 dict)를 기반으로 원본 DataFrame에서 해당 행을 찾습니다.
        
        :param metadata: {"인덱스": idx, "유튜버": channel} 형태의 메타데이터 (문자열일 경우 JSON으로 변환)
        :return: 해당 행 (pandas Series) 또는 None (찾을 수 없을 경우)
        """
        # metadata가 문자열이면 dict로 변환합니다.
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError as e:
                log_wrapper(f"메타데이터 변환 실패: {e}")
                return None, None
        buff=str(metadata['index']).replace("]","[").split('[')
        clean_list = [item for item in buff if item != ""]
        channel = clean_list[1]
        idx = clean_list[-1]
        page = clean_list[2]
        if channel in self.data:
            df = self.data[channel][1]
            try:
                row = df.loc[int(idx)-1].copy()
                row.loc["인덱스"]=int(idx)-1
                return row
            except KeyError:
                log_wrapper(f"인덱스 {idx}가 채널 {channel}의 DataFrame에 없습니다.")
                return None, None
        else:
            log_wrapper(f"채널 {channel}이 존재하지 않습니다.")
            return None, None
    def setup_tag_table(self):
        self.keyword_set=set()
        self.Index_table=pd.DataFrame()
        for d in self.data:
            for rows in self.data[d][1]['태그']:
                if rows:
                    if isinstance(rows, list):
                        rows = [rowso for rowso in rows if not (isinstance(rowso, float) and np.isnan(rowso))]
                        if len(rows)==1 and isinstance(rows[0], list):
                            rows=rows[0]
                        self.keyword_set.update(rows)
        collen=0
        for d in self.data:
            collen+=int(len(self.data[d][1]))
        cloumnsV=[]
        for d in self.data:
            self.data[d][1]['match']="0"
            for inx in self.data[d][1]['인덱스']:
                self.data[d][1]['match'].loc[inx]=f"self.data[{d}][1][태그][{int(inx) if not np.isnan(inx) else inx}]"
            cloumnsV.append(self.data[d][1]['match'])
        
        cloumnsV=pd.concat(cloumnsV)
        basematrix = pd.DataFrame(index=list(self.keyword_set).copy(), columns=cloumnsV)
        basematrix.fillna(0, inplace=True)
        for d in basematrix.columns[:-1]:
            if d != "0" and d:
                youtuber=d.replace('[',']').replace(']]',']').split(']')[1]
                index=d.replace('[',']').replace(']]',']').split(']')[-2]
                tag=self.data[youtuber][1]['태그'].loc[int(index)]
                for rows in tag:
                    basematrix[d].loc[rows]=1
        self.Index_table=basematrix
        self.save_data_to_pickle(self.Index_table,"./app/agents/youtube_agent_module/copydata/Index_table.pkl")
        self.save_data_to_pickle(list(self.keyword_set),"./app/agents/youtube_agent_module/copydata/keyword_set.pkl")
        
        
    def tset_keyword_search(self,keyword,kV=20):
        outs=set()
        for d in keyword:
            similar_words = difflib.get_close_matches(d, self.keyword_set, n=3, cutoff=0.85)
            if similar_words:
                for i in similar_words:
                    outs.add(i)
        result=self.score_keyword_search(list(outs),kV)
        print (outs)
        return result
    
    def score_keyword_search(self,selected,k):
        outs=[]
        data = [0] * len(self.Index_table.columns)
        stakscore=pd.DataFrame(data, columns=['score'],index=self.Index_table.columns)

        for d in selected:
            if d:
                stakscore['score']+=self.Index_table.loc[d].astype(int).values.tolist()
            
        stakscore = stakscore.sort_values(by='score', ascending=False)
        
        #for row, i in  stakscore.iterrows():
        #    if i['score']>0:
        #        log_wrapper(f'name:{row},score:{i["score"]}')
        #    else:
        return stakscore[:k]
                #break
class Indexer:
    def __init__(self,mode='run'):
        #self.prompt = """
        #    당신은 자막 분석가입니다. 당신에겐 다른 메시지 없이 자막만이 제공됩니다.
        #    자막만 보고 중요 내용을 추정해 단어를 추출합니다.
        #    자막에 표기된 시간과 실제 내용들을 보고 중요한 키워드를 추출합니다.
        #    추출한 키워드는 [[키워드]]로 표시하여 일체의 다른 메시지 없이 즉시 반환합니다.
        #"""
        self.front_prompt_tag="""
                        당신은 BM25 검색 전문가입니다. 당신에게 이번에 특별한 의뢰가 들어왔습니다.
                        유튜브 영상의 자막과 영상설명만 보고 중요한 키워드를 찾아내는 것 입니다. 반드시 결정해야하는 것들은 다음과 같습니다.
        """
        self.front_prompt_run="""
                        당신은 BM25 검색 전문가입니다. 당신에게 이번에 특별한 의뢰가 들어왔습니다.
                        유튜브의 영상자막에 태그를 달아 저장한 DB가 있습니다. 이를 사용하려는 일반인 사용자의 요청을 개선하고자합니다.
                        당신은 사용자의 질문을 보고 유튜브 자막 자료에 있을 것으로 추정되는 태그를 결정해야 합니다. 반드시 결정해야 하는 태그의 구체적 사항은 다음과 같습니다.
                        """
        self.prompt_back="""
                        제품군(태블릿, 스마트폰, 랩톱, 웨어러블, 모니터 등)과 제조사(애플, 삼성, 샤오미, 레노버, 구글 등), 
                        그리고 스크립트나 설명에서 모델명이나 라인업을 확인가능하면 키워드에 포함시켜주세요
                        용도(게이밍, 아트, 업무용 등) 가격 및 성능(가성비, 보급형, 프리미엄, 하이앤드, 플래그십 등), 영상의 종류(리뷰,수리,V로그,전시회) 등이 있습니다.
                        추가적으로 중요한 내용이 있다면 추가로 입력해 주세요.
                        추출한 키워드는 [[키워드]]로 표시하여 일체의 다른 메시지 없이 즉시 반환합니다. 아래는 결과 예시입니다.
                        ----------------------------------------------예시1------------------------------------------------
                        [[태블릿]][[삼성]][[플래그십]][[게이밍]][[배터리 런타임]][[리뷰]][[갤럭시탭S10울트라]]
                        ------------------------------------------------------------------------------------------------
                        ----------------------------------------------예시2------------------------------------------------
                        [[모바일]][[삼성]][[플래그십]][[리뷰]][[카메라]][[갤럭시25시리즈]]
                        ------------------------------------------------------------------------------------------------
                        ----------------------------------------------예시3------------------------------------------------
                        [[모바일]][[안드로이드]][[적응형배터리]][[리뷰]][[업데이트]][[구글]]
                        ------------------------------------------------------------------------------------------------
                        ----------------------------------------------예시4------------------------------------------------
                        [[PC]][[RTX4070TI]][[커스텀수냉]][[수리]][[고장]][AS]]
                        ------------------------------------------------------------------------------------------------        
                        """
        self.excelerator_prompt="""
                        당신은 서류 요약장인입니다. 당신에게 이번에 특별한 의뢰가 들어왔습니다.
                        유튜브 영상의 자막과 영상설명만 보고 몇가지 요약자료를 작성하는것입니다. 필요한 자료는 다음과 같습니다.
                        -요구자료
                        1) 설명자료 - 자막과 설명을 기반으로 하여 영상의 전반적인 내용을 설명합니다. 전체적인 내용을 파악 가능해야하며 너무 
                        자세한 내용은 필요 없으나 IT기기 추천 서비스에 활용하는것이 목적이기 때문에 IT기기에 대해 어떠한 정보가 포함되어 있는지 
                        파악 가능하도록 요약해야 합니다.
                        2) 태그자료 - 자막과 설명을 기반으로 하여 영상의 태그를 추출합니다. 태그는 영상의 주제와 관련된 키워드로 구성되어야 하며[작성태그]를 참고하여
                        일관되게 유지되어야 합니다. 특히 제품군, 제조사, 모델명, 용도, 가격 및 성능, 영상의 종류(리뷰인지 수리인지 아니면 다른영상인지) 등이 포함되어야 합니다.
                        또한 태그 기반 검색이 가능하도록 일반화가 되어야 합니다 (예시 아이패드, 아이 패드 ,Ipad -> 모두 하나의 명칭으로 통일 ipad pro, 아이패드 프로 -> 모두 하나의 명칭으로 통일)
                        -제한사항
                        1) 설명자료는 500토큰을 넘어서면 안됩니다 되도록이면 100토큰 이하를 권장합니다.
                        2) 태그자료는 5개 이상의 태그가 권장되며 하나의 태그는 1~2 단어로 구성하는것을 권장합니다.
                        3) 태그자료에는 확인 가능하다면 물건의 종류(태블릿,스마트폰, PC, 그래픽카드) 제품군(갤럭시 탭, 갤럭시 S, 아이패드, 아이폰 등), 제조사(애플, 삼성, 샤오미, 레노버 등), 용도(게이밍, 미술, 학습 등)는 반드시 포함해야 합니다.
                        4) 포멧은 다음과 같습니다 [[DESCRIPTION:설명자료]] , [[TAGS:((태그1)),((태그2)),((태그3)),((태그4))...]],[[CODE:메인프롬프트확인],[[CODE:태그=True]],[[CODE:예시확인]]이며 일체 다른 문구는 출려갸하지 않습니다.
                        -중요사항
                        1) 현재 프롬프트가 확인가능하다면 확인코드를 입력해주세요[[CODE:메인프롬프트확인]]
                        2) 현재까지 작성된 태그가 확인 가능하면 확인코드를 입력해주세요[[CODE:태그=True]]
                        3) 현재까지 작성된 태그가 확인 불가능하면 확인코드를 입력해주세요[[CODE:태그=False]]
                        4) 아래 예시를 참고하여 작성해주세요 예시가 확인 가능하다면 확인코드를 입력해주세요[[CODE:예시확인]]
                        ----------------------------------------------예시1------------------------------------------------
                        [[DESCRIPTION:이 영상은 아이패드 7세대에 대한 리뷰 영상입니다 주로 ....]], [[TAGS:((애플)),((태블릿)),((리뷰)),((아이패드)),((7세대)),((애플펜슬))...]],[[CODE:메인프롬프트확인]],[[CODE:태그=True]],[[CODE:예시확인]]
                        ------------------------------------------------------------------------------------------------
                        ----------------------------------------------예시2------------------------------------------------
                        [[DESCRIPTION:이 영상은 갤럭시 탭으로 게임을 플레이 하는 영상이며 리뷰나 구체적인 스펙 언급은 없으나 FPS....]], [[TAGS:((태블릿)),((삼성)),((갤럭시탭)),((게이밍)),((게임플레이))...]] ,[[CODE:메인프롬프트확인]],[[CODE:태그=False]],[[CODE:예시확인]] 
                        """
        
        
        if mode == 'run':
            self.prompt = self.front_prompt_run+self.prompt_back
        elif mode == 'tag':
            self.prompt = self.front_prompt_tag+self.prompt_back
        elif mode == 'excelerator':
            self.prompt = self.excelerator_prompt
        else:
            self.prompt_back="질문자의 요청에 따라 도움을 주세요"
            raise Exception("mode는 run 또는 tag 중 하나여야 합니다.")
        self.start_time=time.time()
        self.TPM = 200000
        self.model="gpt-4o-mini"
        self.node = Node(self.prompt, gptmodel=self.model)
        self.script = []
        self.token=0
        self.lock=False
        
    
    def add_script(self, script):
        self.check_TPM()
        if self.lock:
            log_wrapper("TPM 초과로 대기중입니다.//add_script")
            return False
        if isinstance(script, str):
            self.script.append(script)
            return True
        elif isinstance(script, list):
            if isinstance(script[0], str):
                self.script.extend(script[0])
                log_wrapper('Warning: script is list only first script is added')
                return True
        else:
            log_wrapper("스크립트는 문자열 또는 문자열의 리스트만 추가할 수 있습니다.")
            return False
    def response_one_with_memory(self,tagset):
        if self.lock:
            log_wrapper("TPM 초과로 대기중입니다.//response_one")
            return False, False
        if self.script:
            context=f"[작성태그]:{list(tagset)}"
            out_script=self.script.pop(0)
            self.node.change_context(context)
            out,token=self.node.get_response_with_token(out_script)
            self.token+=token
            return out, out_script
        else:
            log_wrapper("스크립트가 없습니다.")
            return False, False
    def response_one(self):
        if self.lock:
            log_wrapper("TPM 초과로 대기중입니다.//response_one")
            return False, False
        if self.script:
            out_script=self.script.pop(0)
            out,token=self.node.get_response_with_token(out_script)
            self.token+=token
            return out, out_script
        else:
            log_wrapper("스크립트가 없습니다.")
            return False, False
    def response_all(self):
        self.check_TPM()
        if self.lock:
            log_wrapper("TPM 초과로 대기중입니다.//response_one")
            return False, False
        out_script=[]
        out=[]
        while self.script:
            out_script.append(self.script.pop(0))
            data,token=self.node.get_response_with_token(out_script[-1])
            self.token+=token
            out.append(data)
            self.check_TPM()
            if self.lock:
                log_wrapper("TPM 초과로 대기중입니다.//response_one_loop")
                return False, False
        return out, out_script
    def set_model(self,model):
        self.check_TPM()
        if self.lock:
            log_wrapper("TPM 초과로 대기중입니다.//response_one")
            return False, False
        self.model=model
        self.node = Node(self.prompt, model=self.model)
        self.set_TPM()

    def set_TPM(self):
        if self.model=="gpt-4o-mini":
            self.TPM = 200000
        elif self.model=="chatgpt-4o-latest":
            self.TPM    =30000
        self.check_TPM()
    def check_TPM(self):
        if self.TPM*0.95<= self.token and time.time()-self.start_time<60:
            self.lock=True

        else:
            self.lock=False
            self.reset_TPM()
    def reset_TPM(self):
        if time.time()-self.start_time>60:
            self.token=0
            self.start_time=time.time()
    def chektimer(self):
        return time.time()-self.start_time,time.time()-self.start_time>60
class DataExcelerator:
    def __init__(self):
        self.DataProcessor=Dataprocessor(mode="excelerator")
        #self.DataProcessor.setup_tag_table()
        #self.DataProcessor.make_hesh_dict()
        #self.DataProcessor.set_day_limit()
        self.DataProcessor.create_vector_store_active(persist_directory="./app/agents/youtube_agent_module/data/vector_db.h5")
        log_wrapper("활성 상태")
class Datatagger:
    def __init__(self):
        self.DataProcessor=Dataprocessor(mode="tag")
        self.DataProcessor.setup_tag_table()
        self.DataProcessor.make_hesh_dict()
        self.DataProcessor.set_day_limit()
        self.DataProcessor.create_vector_store_active(persist_directory="./app/agents/youtube_agent_module/data/vector_db.h5")
        log_wrapper("`활성 상태")
        
class DataLoader:
    def __init__(self):
        self.DataProcessor=Dataprocessor(mode="run")
        self.data=self.DataProcessor.data

    def get_qa(self,model_name="gpt-4o-mini"):
        log_wrapper("<<::STATE::VECTOR Data Base LOADED>>볙터 db 로드")
        return self.DataProcessor.create_qa_chain_from_store(model_name=model_name)

def get_searchdata(keyword_list,query):
    R=DataLoader()
    tag=R.DataProcessor.tset_keyword_search(keyword_list)
    searchV=[]
    for index, row in tag.iterrows():
        searchV.append(index)
    R.DataProcessor.set_active(searchV)
    R.DataProcessor.create_qa_chain_from_store(persist_directory="./app/agents/youtube_agent_module/data/vector_db.h5")
    result=R.DataProcessor.get_video_data(query,mode="database")
    return(result)
    


if __name__ == "__main__":
    set_mode = argparse.ArgumentParser(description='Run or tag')
    set_mode.add_argument('--mode', type=str, default="run",help="run or tag")
    args = set_mode.parse_args()
    if args.mode=="tag":
        Datatagger()
        dir_flag=Path("./app/agents/youtube_agent_module/copydata/flag.txt")
        dir_flag.touch(exist_ok=True)
        with open(dir_flag, 'w') as f:
            f.write("1")
        while True:
            sleep(5)
            with open(dir_flag, 'r') as f:
                flag = f.readline()
            if flag.strip() != "1":
                sys.exit("프로그램을 종료합니다.")  

    elif args.mode=="dbtest":
        DataProcessor=Dataprocessor(mode="run")
        #DataProcessor.create_summary_dicts()
        DataProcessor.create_qa_chain_from_store(persist_directory="./app/agents/youtube_agent_module/data/vector_db.h5")
    elif args.mode=="excelerator":
        DataExcelerator()
        dir_flag=Path("./app/agents/youtube_agent_module/copydata/flag.txt")
        dir_flag.touch(exist_ok=True)
        with open(dir_flag, 'w') as f:
            f.write("1")
        while True:
            sleep(5)
            with open(dir_flag, 'r') as f:
                flag = f.readline()
            if flag.strip() != "1":
                sys.exit("프로그램을 종료합니다.")  
    else:
        R=DataLoader()
        #R.get_qa()
       # R.DataProcessor.setup_tag_table()
        tag=R.DataProcessor.tset_keyword_search(['그림', '애플팬슬', '아이패드''리뷰',"고성능","고주사율","터치"])
        searchV=[]
        for index, row in tag.iterrows():
            searchV.append(index)
        R.DataProcessor.set_active(searchV)
        R.DataProcessor.create_qa_chain_from_store(persist_directory="./app/agents/youtube_agent_module/data/vector_db.h5")
        result=R.DataProcessor.get_video_data("그림 연습용 아이패드 관련 영상 자막",mode="database")
        log_wrapper(result)
        
