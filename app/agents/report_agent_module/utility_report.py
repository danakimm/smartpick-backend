import os
import warnings
from openai import OpenAI
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_upstage import ChatUpstage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.callbacks import get_openai_callback
from pprint import pprint
warnings.filterwarnings("ignore")



class APIcontroller:
    def __init__(self):
        load_dotenv()
        self.UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY")
        self.OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
        self.model=None
        if not self.UPSTAGE_API_KEY:
            self.UPSTAGE_API_KEY = None
            print("Upstage API is None")
        else:
            print("Upstage API key is successfully set.")
        if not self.OPENAI_API_KEY:
            self.OPENAI_API_KEY = None
            print("OpenAi API is None")
        else:
            print("<<::STATE::api_initialized>>OpenAi API key is successfully set.")

    def get_llm_model(self,llmmodel,model='openai'):
        if model == 'upstage' and self.UPSTAGE_API_KEY:
            if llmmodel:
                llm = ChatUpstage(model=llmmodel)
                self.model =[model,llmmodel]
                return llm
        elif model == 'openai' and self.OPENAI_API_KEY:
            if llmmodel:
                llm = ChatOpenAI(model=llmmodel)
                self.model =[model,llmmodel]
                return llm
        elif model == 'endnode':
            llm = 'endnode'
            self.model =[model,llmmodel]
            return llm
        else:
            print("Not available any model")
            return None
        print("Not available any model")
        return None
    def get_prompt_raw(self,input_prompt) -> ChatPromptTemplate:
        """
        시스템과 사용자 메시지를 포함한 ChatPromptTemplate을 생성하여 반환합니다.
        
        시스템 메시지에는 {context} 플레이스홀더가 있고,
        인간 메시지에는 {input} 플레이스홀더가 존재합니다.
        """
        if isinstance(input_prompt, list):
            input_prompt = " ".join(map(str, input_prompt)).replace("\\","").replace("\n","").replace("}","").replace("{","")
        prompt = ChatPromptTemplate.from_messages([input_prompt])
        return prompt 
    def get_prompt(self,input_prompt) -> ChatPromptTemplate:
        """
        시스템과 사용자 메시지를 포함한 ChatPromptTemplate을 생성하여 반환합니다.
        
        시스템 메시지에는 {context} 플레이스홀더가 있고,
        인간 메시지에는 {input} 플레이스홀더가 존재합니다.
        """
        if isinstance(input_prompt, list):
            input_prompt = " ".join(map(str, input_prompt)).replace("\\","").replace("\n","").replace("}","").replace("{","")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system",input_prompt+" {context}"),("human", "{input}"),
            ]
            )
        return prompt 
    def get_answer(self,llm,prompt:ChatPromptTemplate ,query: str,context="") -> str:
        """
        주어진 query(사용자 질문)와 context(문맥 또는 문서 내용)를 바탕으로
        최종 답변을 반환하는 함수입니다.
        
        내부적으로 get_prompt()와 get_llm()를 사용하여 체인을 구성한 후, 
        StrOutputParser()를 통해 문자열 형태의 응답을 추출합니다.
        """
        if llm == 'endnode':
            return query
        # 3. 체인 구성: 프롬프트 → LLM → 출력 파서
        chain = prompt | llm | StrOutputParser()

        # 4. 체인 실행: 플레이스홀더에 실제 값 전달
        with get_openai_callback() as cb:
            response = chain.invoke({'context': context, 'input': query},return_only_outputs=False)
        return response,cb.total_tokens,cb.prompt_tokens,cb.completion_tokens



apicon=APIcontroller()

class Node:
    def __init__(self, prompt,model='openai',context="",gptmodel=None):
        self.controller = apicon
        if model == 'upstage':
            llmmodel= "solar-pro"
        elif model == 'openai':
            if gptmodel:
                llmmodel = gptmodel
            else:
                llmmodel = "gpt-4o-mini"
                #llmmodel = "chatgpt-4o-latest"
        elif model == 'endnode':
            llmmodel = 'endnode'

        self.llm = self.controller.get_llm_model(llmmodel,model=model)
        if self.llm == 'endnode':
            self.prompt = "end_or_start_node"
            self.context = context
        else:
            self.prompt = self.controller.get_prompt(prompt)
            self.context = context

    def get_response(self,query):
        if self.llm == 'endnode':
            return query
        out,_,_,_=self.controller.get_answer(self.llm,self.prompt,query,self.context)
        return out
    def get_response_with_token(self,query):
        if self.llm == 'endnode':
            return query
        out,token,_,_=self.controller.get_answer(self.llm,self.prompt,query,self.context)
        return out, token
    def change_context(self,context):
        if self.llm == 'endnode':
            print("This is endnode if you change context, it is not working")
        self.context = context
    def change_raw_prompt(self,prompt):
        if self.llm == 'endnode':
            print("This is endnode so you can't change prompt")
        self.prompt = self.controller.get_prompt_raw(prompt)
    def change_prompt(self,prompt):
        if self.llm == 'endnode':
            print("This is endnode so you can't change prompt")
        self.prompt = self.controller.get_prompt(prompt)
    def change_llm(self,llm):
        if self.llm == 'endnode':
            print("This is endnode so you can't change llm")
        self.llm = llm
    def get_prompt(self):
        if self.llm == 'endnode':
            return "end or start node"
        return self.prompt
    def get_llm(self):
        if self.llm == 'endnode':
            return "endnode"
        return self.llm
    def get_context(self):

        return self.context
    def get_controller(self):
        if self.llm == 'endnode':
            return "endnode"
        return self.controller




'''
미사용 컨셉만 있는거
class Link():
    def __init__(self,from_node,to_node:Node):
        self.propagation_query=[None] * 3
        self.from_node_user_query = None
        self.from_node_context = None
        self.from_node_prompt = None 
        if isinstance(from_node,Node):
            self.from_node_user_query = from_node
            self.from_node_context = None
            self.from_node_prompt = None
        elif isinstance(from_node,list):
            if len(from_node)==2:
                self.from_node_user_query =from_node[0]
                self.from_node_context = from_node[1]
            elif len(from_node)==3:
                self.from_node_user_query = from_node[0]
                self.from_node_context = from_node[1]
                self.from_node_prompt = from_node[2]
            else:
                self.from_node_user_query = None
                self.from_node_context = None
                self.from_node_prompt = None
                raise ValueError("from_node must be a Node or a list of Nodes")
        else:
            raise ValueError("from_node must be a Node or a list of Nodes")
        if isinstance(to_node,Node):
            self.to_node = to_node
        else:
            raise ValueError("to_node must be a Node")
    def check_Link(self):
        return [self.from_node_user_query is not None,self.from_node_context is not None,self.from_node_prompt is not None]

    def set_propagation_query(self,query):
        if isinstance(query,str):
            self.propagation_query=[None] * 3 
            self.propagation_query[0] = query
        elif isinstance(query,list):
            for i in query:
                if not isinstance(i,str):
                    if i is None:
                        continue
                    else:
                        raise ValueError("set_propagation_query need a str or a list of str")
            self.propagation_query=[None] * 3 
            if len(query)==1:
                self.propagation_query[0] = query[0]
                self.propagation_query[1] = None
                self.propagation_query[2] = None
            if len(query)==2:
                self.propagation_query[0] =query[0]
                self.propagation_query[1] = query[1]
                self.propagation_query[2] = None
            elif len(query)==3:
                self.propagation_query[0]  = query[0]
                self.propagation_query[1]  = query[1]
                self.propagation_query[2]  = query[2]
            elif len(query)<1:
                self.propagation_query[0] = None
                self.propagation_query[1] = None
                self.propagation_query[2] = None
                raise ValueError("set_propagation_query need a str or a list of str")
        elif self.from_node_prompt is not None:
            self.propagation_query=[None] * 3 
            self.propagation_query[2] = True
        elif self.from_node_context is not None:
            self.propagation_query=[None] * 3 
            self.propagation_query[1] = True
        else:
            raise ValueError("set_propagation_query need a str or a list of str")        
    def stream(self,query=None):
        try:
            if (self.propagation_query  != [None] * 3) or (query is not None):
                if self.propagation_query[1] is not None:
                    if isinstance(self.propagation_query[1],str):
                        self.to_node.change_context(self.from_node_context.get_response(self.propagation_query[1]))
                    else:
                        self.to_node.change_context(self.from_node_context.get_response(query))
                if self.propagation_query[2] is not None:
                    if isinstance(self.propagation_query[2],str):
                        self.to_node.change_prompt(self.from_node_prompt.get_response(self.propagation_query[2]))
                    else:
                        self.to_node.change_prompt(self.from_node_prompt.get_response(query))
                if self.propagation_query[0] is not None:
                    return self.to_node.get_response(self.from_node_user_query.get_response(self.propagation_query[0]))
                elif query is not None:
                    return self.to_node.get_response(query) 
            else:
                raise ValueError("first set the input query")
        except ValueError:
            raise ValueError("Link stream error")
class iterator():
    def __init__(self,link_list,next):
        self.link_list = link_list
        self.index = 0
        self.length = len(link_list)
        self.loopcontrol = False
        self.maxindex=None
        self.next=next
        self.limitation = 20
        self.mode=None

        if not self.check_Linkstructure():
            raise ValueError("Link structure is not correct")

    def define_loop(self,constraint):
        if isinstance(constraint,int):
            self.maxindex = constraint
            self.mode = 'for'
        elif callable(constraint):
            self.loopcontrol = constraint
            self.mode = 'while'
        elif isinstance(constraint,bool):
            self.loopcontrol = lambda: constraint
            self.mode = 'while'
        else:
            raise ValueError("constraint must be a integer or a boolean")
    def set_limitation(self,limit):
        if isinstance(limit,int):
            self.limitation = limit
        else:
            raise ValueError("limit must be a integer")
    def check_Linkstructure(self):
        for i in range(self.length-1):
            if not self.match_Link(self.link_list[i],self.link_list[i+1])[3]:
                return False
        return True
    @staticmethod
    def match_Link(Link_i,Link_f):
        if isinstance(Link_i,Link) and isinstance(Link_f,Link):
            out=[0,0,0,True]
            if Link_i.to_node == Link_f.from_node_user_query:
                out[0]=1
            elif Link_i.to_node == Link_f.from_node_context:
                out[1]=1
            elif Link_i.to_node == Link_f.from_node_prompt:
                out[2]=1

            else:
                return [0,0,0,False]
        else:
            raise ValueError("Link_i and Link_i must be a Link")
        return out
    def propagation_unit(self,Link_i,Link_f,input_query,query_bk=None):
        if isinstance(Link_i,Link) and isinstance(Link_f,Link):
            Ic=Link_i.check_Link()
            Fc=Link_f.check_Link()
            S=0
            for i in Ic:
               S+=i
            if len(input_query) != S:
                raise ValueError("input_query must be a list of str")
            Link_i.set_propagation_query(input_query)
            respons=Link_i.stream()
            mat=[None]*3
            index=0
            for i in self.match_Link(Link_i,Link_f):
                if i==1:
                    mat[index]=respons
                index+=1
                if index==3:
                    break
            Link_f.set_propagation_query(mat)
            out=Link_f.stream(query_bk)
            return out            
        else:
            raise ValueError("Link_i and Link_i must be a Link") 


    def run(self):
        if self.mode == 'for':
            for i in range(self.maxindex):
                if self.index >= self.length:
                    break
                response = self.link_list[self.index].stream()
                self.index += 1
                if not self.next(response):
                    break
                
                '''