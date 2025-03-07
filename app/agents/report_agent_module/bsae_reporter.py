from app.agents.report_agent_module.utility_report import Node
import re
from .template_generator import ResultTemplate, Product, Reviews, Purchase_Info_Stores
import os
import h5py
import hashlib
import json
class CacheManager:
    """
    HDF5 파일을 사용하여 해시화된 키-값 쌍을 저장하고 검색하는 클래스
    """
    def __init__(self, file_path):
        """
        파일 경로를 입력받아 초기화하고, 파일이 없으면 생성함
        
        Args:
            file_path (str): HDF5 파일의 경로 (확장자 포함)
        """
        self.file_path = file_path
        self.get_dict = {}  # 검색 결과를 저장할 딕셔너리
        # 확장자가 h5인지 확인
        if not file_path.endswith('.h5'):
            raise ValueError("파일 확장자는 반드시 .h5여야 합니다.")
        # 파일이 존재하는지 확인
        if os.path.exists(file_path):
            # 파일이 존재하면 읽기 모드로 열기
            self.file = h5py.File(file_path, 'r+')
        else:
            # 파일이 존재하지 않으면 생성
            self.file = h5py.File(file_path, 'w')
    def _hash_key(self, key):
        """
        키 값을 SHA-256 해시로 변환
        Args:
            key: 해시화할 키 (문자열로 변환 가능해야 함)
            
        Returns:
            str: 해시 문자열
        """
        key_str = str(key)
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()
    def add_hash(self, input_dict, reject_key=None, require_key=None):
        """
        input_dict의 각 key에 대해, 해당 value가 딕셔너리들의 리스트여야 하며,
        각 리스트 요소(딕셔너리)에 대해 require_key 및 reject_key 조건을 적용하여
        조건을 만족하는 요소들만 필터링한 결과를 H5 파일에 저장합니다.
        
        Args:
            input_dict (dict): 저장할 키-값 쌍이 있는 딕셔너리.
                            각 key의 value는 딕셔너리들의 리스트여야 합니다.
            reject_key (str or list, optional): 
                - 문자열인 경우, 각 리스트 요소의 딕셔너리에 해당 키가 존재하면 그 요소는 제외.
                - 리스트인 경우, 각 리스트 요소의 딕셔너리에 리스트 내 모든 키가 존재하면 그 요소는 제외.
                - None이면 조건 없이 모두 포함.
            require_key (list, optional): 
                - 리스트 형태로 필수 키들을 지정.
                - 각 리스트 요소의 딕셔너리에 이 리스트의 모든 키가 존재할 때만 해당 요소를 포함.
                - None이면 조건 없이 포함.
                
        Returns:
            bool: 적어도 하나의 항목이 새로 추가되면 True, 아니면 False.
        """
        if not input_dict:
            return False

        success = False

        # input_dict의 각 key와 그에 해당하는 리스트 처리
        for key, value_list in input_dict.items():
            # value가 리스트가 아닌 경우 건너뜁니다.
            if not isinstance(value_list, list):
                continue

            # 리스트 내 각 요소가 딕셔너리라고 가정하고, 조건에 따라 필터링
            filtered_list = []
            for item in value_list:
                if not isinstance(item, dict):
                    continue

                # require_key 조건 처리: 각 item 딕셔너리에 require_key의 모든 키가 있어야 함
                if require_key is not None:
                    if not isinstance(require_key, list):
                        print("require_key는 리스트여야 합니다.")
                        return False
                    if not all(req_key in item for req_key in require_key):
                        continue  # 필수 키 중 하나라도 없으면 제외

                # reject_key 조건 처리: 조건이 만족되면 제외
                if reject_key is not None:
                    if isinstance(reject_key, str):
                        if reject_key in item:
                            continue
                    elif isinstance(reject_key, list):
                        if all(rk in item for rk in reject_key):
                            continue
                    else:
                        print("reject_key는 문자열 또는 리스트여야 합니다.")
                        return False

                filtered_list.append(item)

            # 필터링 결과가 없으면 저장하지 않음
            if not filtered_list:
                continue

            # HDF5에 저장할 키 생성 및 이미 존재하는지 확인
            hashed_key = self._hash_key(key)
            if hashed_key in self.file:
                continue

            # 원본 key와 필터링된 리스트를 JSON 문자열로 직렬화하여 저장
            value_str = json.dumps({"key": key, "value": filtered_list})
            self.file.create_dataset(hashed_key, data=value_str.encode('utf-8'))
            success = True

        self.file.flush()
        return success



    def get_value(self, input_dict):
        """
        딕셔너리의 키를 해시화하여 H5 파일에서 검색
        
        Args:
            input_dict (dict): 검색할 키가 있는 딕셔너리
            
        Returns:
            bool: 모든 키가 파일에서 발견되면 True, 하나라도 없으면 False
        """
        if not input_dict:
            return False
        # 결과 딕셔너리 초기화
        self.get_dict = {}
        found_all = True
        for key in input_dict.keys():
            hashed_key = self._hash_key(key)
            
            # 해시 키가 H5 파일에 있는지 확인
            if hashed_key in self.file:
                # 데이터셋에서 값 읽기
                value_bytes = self.file[hashed_key][()]
                value_str = value_bytes.decode('utf-8')
                value_data = json.loads(value_str)
                
                # 원본 키와 값으로 결과 딕셔너리 구성
                self.get_dict[value_data["key"]] = value_data["value"]
            else:
                found_all = False
        return found_all
    def clean(self):
        if self.file is not None:
            try:
                self.file.close()
            except Exception as e:
                print("파일 닫는 중 에러 발생:", e)
            self.file = None
    def __del__(self):
        """
        객체가 소멸될 때 clean 메서드 호출
        """
        self.clean()


class BaseReporter:
    def __init__(self,data,section1,section2,query,table_content,prompt,model,script,selfquestion,selfanswer,context,cachepath,find_dict,cache_key,require_key,reject_key):

        self.data=data
        self.section1=section1
        self.section2=section2
        self.table_content=table_content
        self.prompt=prompt
        self.query=query
        self.model=model
        self.script=script
        self.selfquestion=selfquestion
        self.selfanswer=selfanswer
        self.N=0
        self.context=context
        self.cachepath=cachepath
        self.cache=CacheManager(self.cachepath)
        self.find_dict=find_dict
        self.cache_key=cache_key
        self.require_key=require_key
        self.reject_key=reject_key
    def get_response(self):
        if self.cache.get_value(self.find_dict):
            return list(self.cache.get_dict.values())[0],["cached output"]
        else:
            result, response=self.get_response_with_llm()
            if not self.cache_key:
                inpitdict={self.cache_key:result}
                self.cache.add_hash(inpitdict,reject_key=self.reject_key,require_key=self.require_key)
                
            return result, response
    def try_get_response(self,query,num):
        if len(self.selfanswer)>0:
            nm=1
            stack=[]
            for q in self.selfanswer:
                stack.append(f'{nm}번째 질문 : {self.selfquestion[nm-1]}, {nm}번째 답변 : {q}')
                nm+=1
            char="\n".join(stack)
            new_context=self.script[num]+char+self.context

        else:    
            new_context=self.script[num]+self.context
        self.model.change_context(new_context)
        if len(self.selfquestion)>0:
            if isinstance(self.selfquestion[-1],list):
                inputquestion=" ,질문 : ".join(self.selfquestion[-1])
            else:
                inputquestion=self.selfquestion[-1]
            Nquery="스스로 하는 질문 : " + inputquestion+" 유저 요청 : "+query + "Rule : "+self.script[num]
            self.selfquestion.append("스스로 하는 질문 : " + inputquestion)
            response=self.model.get_response(Nquery)

        else:
            response=self.model.get_response("유저 요청 : "+query)
        return response
    def parse_youtuber_output(self,text):
        # [[키::값]] 또는 [[키:값]] 형태의 항목을 찾는 정규표현식
        pattern = r"\[\[([^:\]]+)(?:::|:)(.*?)\]\]"
        matches = re.findall(pattern, text, re.DOTALL)
        
        result = {}
        for key, value in matches:
            key = key.strip()
            value = value.strip()
            # 동일한 키가 이미 존재하면 리스트에 추가
            if key in result:
                if isinstance(result[key], list):
                    result[key].append(value)
                else:
                    result[key] = [result[key], value]
            else:
                result[key] = value
        if result:
            success = True
            for key in result.keys():
                    if key=="selfquestion":
                        if self.N==0:
                            self.selfquestion.append(result['selfquestion'])
                        success = False
                        break
        else:
            success = False
            return result, success    
        return result, success
    
    def get_response_with_llm(self):
        self.N=0
        for i in range(4):
            print(f"현재 {i+1}번째 시도중입니다.")
            response=self.try_get_response(self.query,i)
            result,success=self.parse_youtuber_output(response)
            self.N+=1
            if self.N==4:
                return [result],[response]
            if success:
                return [result],[response]
            else:
                if result:
                    if len( self.selfquestion)>0:
                        try:
                            print (f"질문 : {result['selfquestion']}")
                            if "answer" in result.keys():
                                print (f"답변 : {result['answer']}")
                            self.selfanswer.append(result['answer'])
                            
                        except Exception as e:
                            self.selfquestion.append(f"오류래 오류.... 대체 뭐야 답변 포멧이 잘못된거야...error:{e}")
                else:
                    self.selfquestion.append("왜 대답이 없어? 답을 해줄래? 진짜 그러다 죽는수가 있어....")
        return [result],[response]

        
        
if __name__ == "__main__":
    input=0
