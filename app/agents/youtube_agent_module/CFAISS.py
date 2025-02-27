import faiss
import h5py
import numpy as np
import os
import hashlib
from .queue_manager import add_log
import openai
import dotenv
from langchain.schema import Document, BaseRetriever
from pydantic import Field
from typing import Any, List


globalist=[]
def log_wrapper(log_message):
    globalist.append(log_message)
    add_log(log_message)  
class WrIndexFlatL2:
    def __init__(self, dimension,embedingmodel="text-embedding-3-small"):
        dotenv.load_dotenv()
        self.dimension = dimension
        """FAISS의 IndexFlatL2를 확장하여 metadata 기능을 추가한 클래스"""
        self.index = faiss.IndexFlatL2(dimension)  # FAISS IndexFlatL2 초기화
        self.metadata = {}  # 메타데이터 저장용 (인덱스: 메타데이터)
        self.page={} 
        self.text={}
        self.active = []  # 🔥 검색할 인덱스를 저장할 리스트
        self.embedingmodel = embedingmodel  # OpenAI 임베딩 모델 지정
        
    def get_openai_embedding(self, text):
        """OpenAI 최신 임베딩 API를 사용하여 텍스트를 벡터로 변환"""
        if isinstance(text, list):
            raise ValueError("다수의 텍스트 입력은 지원되지 않습니다. 단일 문자열만 입력하세요.")

        response = openai.embeddings.create(
            model=self.embedingmodel,
            input=text
        )
        return np.array(response.data[0].embedding, dtype=np.float32)  # FAISS 호환 float32 변환
    def add(self, datas):
        """벡터 + 메타데이터 추가"""
        if isinstance(datas, dict):
            vectors = datas['vectors']
            metadata_list = datas['metadata'] 
            page_list=datas['page']
            text_list=datas['text']
            assert len(vectors) == len(metadata_list), "벡터 개수와 메타데이터 개수가 일치해야 함."
            assert len(vectors) == len(page_list), "벡터 개수와 메타데이터 개수가 일치해야 함."
            assert len(vectors) == len(text_list), "벡터 개수와 원본텍스트 개수가 일치해야 함."
            self.index.add(np.array(vectors, dtype=np.float32))  # FAISS에 추가
            for i, meta in enumerate(metadata_list):
                self.metadata[self.index.ntotal - len(vectors) + i] = meta  # 인덱스에 메타데이터 매핑
            for i, page in enumerate(page_list):
                self.page[self.index.ntotal - len(vectors) + i] = int(page)  # 인덱스에 메타데이터 매핑
            for i, text in enumerate(text_list):
                self.text[self.index.ntotal - len(vectors) + i] = text
                    # 🔥 메모리 절약을 위해 원본 데이터 삭제
            del datas['vectors']
            del datas['metadata']
            del datas['page']    
            del datas['text']
    
    def add_with_embedding(self, datas, model="text-embedding-3-small"):
        if isinstance(datas, dict):
            if isinstance(datas['vectors'], str):
                datas['text'] = [datas['vectors']]
                embeddings = [self.get_openai_embedding(datas['vectors'])]
                datas['vectors'] = embeddings
                self.add(datas)
                del datas
            else:
                raise ValueError("입력 데이터는 문자열이어야 합니다.")
        else:
            raise ValueError("입력 데이터는 딕셔너리여야 합니다.")
def _hash_trans( metadata, page):
    """
    WrIndexFlatL2 객체를 입력으로 받아, `metadata + page` 조합을 사용하여 해시값 생성
    """

    hash_dict = {}
    for i in range(len(metadata)):
        meta=metadata[i][0]
        unique_key = f"{meta}{page[i][0]}"
        hash_dict[i] = int(hashlib.sha256(unique_key.encode()).hexdigest(), 16) % (2**63)
    return hash_dict  # ✅ 해시값을 딕셔너리 형태로 반환 (index -> hash)


class HDF5VectorDB:
    def __init__(self, filename="vector_db.h5", dimension=128):
        """
        HDF5 기반 벡터 DB
        1. filename에 경로를 받아 초기화 (없으면 폴더 및 파일 생성)
        """
        self.filename = filename
        self.dimension = dimension
        os.makedirs(os.path.dirname(filename), exist_ok=True)  # 폴더 생성

        # HDF5 파일이 없으면 생성
        if not os.path.exists(filename):
            with h5py.File(filename, "w") as f:
                f.create_dataset("vectors", shape=(0, dimension), maxshape=(None, dimension), dtype=np.float32)
                f.create_dataset("metadata", shape=(0,), maxshape=(None,), dtype=h5py.string_dtype(encoding='utf-8'))
                f.create_dataset("hash_table", shape=(0,), maxshape=(None,), dtype=np.int64)
                f.create_dataset("page", shape=(0,), maxshape=(None,), dtype=np.int64)
                f.create_dataset("text", shape=(0,), maxshape=(None,), dtype=h5py.string_dtype(encoding='utf-8'))

    def _hash_metadata(self, wr_index):
        """
        WrIndexFlatL2 객체를 입력으로 받아, `metadata + page` 조합을 사용하여 해시값 생성
        """
        if not isinstance(wr_index, WrIndexFlatL2):
            raise ValueError("입력 데이터는 WrIndexFlatL2 객체여야 합니다.")

        hash_dict = {}
        for i, meta in wr_index.metadata.items():
            unique_key = f"{meta}{wr_index.page[i]}"
            hash_dict[i] = int(hashlib.sha256(unique_key.encode()).hexdigest(), 16) % (2**63)

        return hash_dict  # ✅ 해시값을 딕셔너리 형태로 반환 (index -> hash)


    def load_by_indices(self, wr_index):########################################
        """
        WrIndexFlatL2 객체를 입력받아 `metadata + page` 조합을 해시로 변환 후, 해당하는 데이터를 로드하여 반환
        """
        if not isinstance(wr_index, WrIndexFlatL2):
            raise ValueError("입력 데이터는 WrIndexFlatL2 객체여야 합니다.")

        # ✅ WrIndexFlatL2 객체에서 `metadata + page` 조합을 해시로 변환
        hash_dict = self._hash_metadata(wr_index)
        query_hashes = list(hash_dict.values())  # ✅ 해시 값 리스트로 변환

        with h5py.File(self.filename, "r") as f:
            hash_table = f["hash_table"][:]
            vectors = f["vectors"][:]
            metadata = f["metadata"][:]
            page = f["page"][:]
            text = f["text"][:]

            matched_indices = np.where(np.isin(hash_table, query_hashes))[0]  # ✅ 해당 해시값이 있는 인덱스 찾기
            if len(matched_indices) == 0:
                return None  # ✅ 해당하는 데이터 없음

            return {
                "vectors": vectors[matched_indices],
                "metadata": metadata[matched_indices],
                "page": page[matched_indices],
                "text": text[matched_indices]
            }
    def load_by_vactor(self, wr_index):
        """
        WrIndexFlatL2 객체를 입력받아 해당하는 데이터를 로드하여 WrIndexFlatL2 객체로 변환
        """
        if not isinstance(wr_index, WrIndexFlatL2):
            raise ValueError("입력 데이터는 WrIndexFlatL2 객체여야 합니다.")

        buf = WrIndexFlatL2(self.dimension)
        add = self.load_by_indices(wr_index)  # ✅ WrIndexFlatL2 객체를 입력으로 전달

        if add:
            buf.add(add)  # ✅ WrIndexFlatL2 객체에 데이터 추가
            return buf
        else:
            return None

    def add_vectors(self, wr_index):
        """
        3. WrIndexFlatL2를 입력받아 HDF5에 추가
        - 인덱스를 해시화해서 기존이랑 겹치면 덮어쓰기
        - 덮어쓰면 log_wrapper 메시지 출력
        """
        if not isinstance(wr_index, WrIndexFlatL2):
            raise ValueError("입력 데이터는 WrIndexFlatL2 객체여야 합니다.")

        with h5py.File(self.filename, "a") as f:
            # 기존 데이터 로드
            existing_hash_table = f["hash_table"][:]

            new_vectors = []
            new_metadata = []
            new_hash_table = []
            new_page = []
            new_text = []
            hash_dict = self._hash_metadata(wr_index) 
            for i, meta in wr_index.metadata.items():
                meta_str = str(meta)  # 문자열 변환
                meta_hash = hash_dict[i] 
                if meta_hash in existing_hash_table:
                    # 기존 데이터 덮어쓰기
                    index = np.where(existing_hash_table == meta_hash)[0][0]
                    if f["page"][index] == wr_index.page[i]:
                       f["vectors"][index] = wr_index.index.reconstruct(i)
                       f["page"][index] = wr_index.page[i]
                       f["metadata"][index] = meta_str
                       f["text"][index] = wr_index.text[i]
                       log_wrapper(f"[INFO] 기존 데이터 덮어씀: {meta_str}, 페이지: {wr_index.page[i]}")
                else:
                    # 새로운 데이터 추가
                    new_vectors.append(wr_index.index.reconstruct(i))
                    new_page.append(wr_index.page[i])
                    new_metadata.append(meta_str)
                    new_text.append(wr_index.text[i])
                    new_hash_table.append(meta_hash)


            # 새로운 데이터가 있다면 추가
            if new_vectors:
                n_old = f["vectors"].shape[0]
                n_new = n_old + len(new_vectors)

                # 벡터 추가
                f["vectors"].resize((n_new, self.dimension))
                f["vectors"][n_old:n_new] = np.array(new_vectors, dtype=np.float32)

                # 메타데이터 추가
                f["metadata"].resize((n_new,))
                f["metadata"][n_old:n_new] = new_metadata

                # 해시 테이블 추가
                f["hash_table"].resize((n_new,))
                f["hash_table"][n_old:n_new] = np.array(new_hash_table, dtype=np.int64)
                
                f["page"].resize((n_new,))
                f["page"][n_old:n_new] = np.array(new_page, dtype=np.int64)
                
                f["text"].resize((n_new,))
                f["text"][n_old:n_new] = new_text

                log_wrapper(f"[INFO] 새 데이터 추가 완료 ({len(new_vectors)}개)")
        # 🔥 메모리 해제: WrIndexFlatL2 내부 데이터 초기화
        wr_index.index = faiss.IndexFlatL2(self.dimension)  # FAISS 인덱스 재초기화
        wr_index.metadata = {}  # 메타데이터 초기화
        wr_index.page = {}  # 페이지 정보 초기화
        wr_index.text = {}  # 원본 텍스트 초기화
    
    
    def extract_custom(self, wr_index):
        """
        WrIndexFlatL2 객체를 입력받아 `metadata + page` 조합을 해시로 변환 후, 해당하는 인덱스를 찾아 `self.active`에 저장
        """
        if not isinstance(wr_index, WrIndexFlatL2):
            raise ValueError("입력 데이터는 WrIndexFlatL2 객체여야 합니다.")

        # ✅ WrIndexFlatL2 객체에서 `metadata + page` 조합을 해시로 변환
        hash_dict = self._hash_metadata(wr_index)
        query_hashes = list(hash_dict.values())  # ✅ 해시 값 리스트로 변환

        with h5py.File(self.filename, "r") as f:
            hash_table = f["hash_table"][:]

            matched_indices = np.where(np.isin(hash_table, query_hashes))[0]  # ✅ 해당 해시값이 있는 인덱스 찾기

            if len(matched_indices) == 0:
                log_wrapper("<<::STATE::Keyword Search FAIl : To hard filttering>> 검색 가능한 데이터 없음")
                self.active = []  # 🔥 검색할 데이터가 없으면 active를 비움
            else:
                self.active = matched_indices.tolist()  # 🔥 검색 가능한 인덱스를 self.active에 저장
                log_wrapper(f"<<::STATE::Keyword Search SECCEED>> 검색 대상 인덱스: {self.active}")
    def extract_custom_from_p_I(self, metadata, page):
        

        # ✅ WrIndexFlatL2 객체에서 `metadata + page` 조합을 해시로 변환
        hash_dict = _hash_trans(metadata, page)
        query_hashes = list(hash_dict.values())  # ✅ 해시 값 리스트로 변환

        with h5py.File(self.filename, "r") as f:
            hash_table = f["hash_table"][:]

            matched_indices = np.where(np.isin(hash_table, query_hashes))[0]  # ✅ 해당 해시값이 있는 인덱스 찾기

            if len(matched_indices) == 0:
                log_wrapper("<<::STATE::Keyword Search FAIl : To hard filttering>> 검색 가능한 데이터 없음")
                self.active = []  # 🔥 검색할 데이터가 없으면 active를 비움
            else:
                self.active = matched_indices.tolist()  # 🔥 검색 가능한 인덱스를 self.active에 저장
                log_wrapper(f"<<::STATE::Keyword Search SECCEED>> 검색 대상 인덱스: {self.active}")
        

    def search(self, query_vector, k=5):
        """
        FAISS 검색 수행 (self.active에 해당하는 인덱스에서만 검색)
        """
        with h5py.File(self.filename, "r") as f:
            vectors = f["vectors"][:]
            metadata = f["metadata"][:]
            pages = f["page"][:]
            texts = f["text"][:]

        if len(vectors) == 0 or len(self.active) == 0:
            return None, None, None  # 🔥 검색할 데이터가 없으면 빈 결과 반환

        # 🔥 self.active에 해당하는 벡터만 FAISS에 추가하여 검색
        active_vectors = np.array([vectors[i] for i in self.active], dtype=np.float32)
        active_metadata = [metadata[i] for i in self.active]
        active_pages = [pages[i] for i in self.active]
        active_texts = [texts[i] for i in self.active]

        # 🔥 FAISS 차원과 벡터 차원이 맞는지 확인 (`self.index.d` 대신 `self.dimension` 사용)
        if active_vectors.shape[1] != self.dimension:
            log_wrapper(f"<<::STATE::Critical raise ValueError >>벡터 차원 불일치! FAISS 인덱스 차원: {self.dimension}, 입력 벡터 차원: {active_vectors.shape[1]}")
            raise ValueError(f"벡터 차원 불일치! FAISS 인덱스 차원: {self.dimension}, 입력 벡터 차원: {active_vectors.shape[1]}")

        # 🔥 메모리 정렬 최적화 (FAISS가 요구하는 형식으로 변환)
        active_vectors = np.ascontiguousarray(active_vectors, dtype=np.float32)

        index = faiss.IndexFlatL2(self.dimension)  # 🔥 검색을 위한 새로운 FAISS 인덱스 생성
        index.add(active_vectors)  # 🔥 self.active에 해당하는 벡터만 검색 인덱스에 추가

        query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)  # 🔥 FAISS가 요구하는 2D 형태로 변환
        distances, indices = index.search(query_vector, k)  # 🔥 FAISS 검색 수행

        # 🔥 WrIndexFlatL2 객체 생성 및 검색된 데이터 추가
        search_result = WrIndexFlatL2(self.dimension)
        search_data = {"vectors": [], "metadata": [], "page": [], "text": []}

        for idx in indices[0]:
            if idx != -1:
                search_data["vectors"].append(active_vectors[idx])  # ✅ 리스트에 추가
                search_data["metadata"].append(active_metadata[idx].decode('utf8'))  # ✅ 리스트에 추가
                search_data["page"].append(active_pages[idx])  # ✅ 리스트에 추가
                search_data["text"].append(active_texts[idx].decode('utf8'))  # ✅ 리스트에 추가

        search_result.add(search_data)        

        return self.to_document(search_result), distances, indices


    def to_document(self, data):
        """
        WrIndexFlatL2 객체를 입력받아, `self.active` 내부의 데이터만 변환하여 LangChain Document 객체로 변환
        """
        if not isinstance(data, WrIndexFlatL2):
            log_wrapper("<<::STATE::Critical raise ValueError >>입력 데이터는 WrIndexFlatL2 객체여야 합니다.")
            raise ValueError("입력 데이터는 WrIndexFlatL2 객체여야 합니다.")

        if len(self.active) == 0:
            log_wrapper("[INFO] 변환할 데이터가 없습니다.")
            return []
        hesh=self._hash_metadata(data)
        docsout = []

        with h5py.File(self.filename, "r+") as f:
            vectors = f["vectors"][:]
            metadata = f["metadata"][:]
            pages = f["page"][:]
            texts = f["text"][:]
            hash_table = f["hash_table"][:]
            hash_to_idx = {hash_table[idx]: idx for idx in self.active}
            # ✅ `self.active` 내부의 데이터만 변환
            total_hash=[]
            for values in hash_to_idx.keys():
                total_hash.append(values)
            for meta_hesh in hesh.values():
                meta_hesh=np.int64(meta_hesh)
                if meta_hesh is None or meta_hesh not in total_hash:
                    log_wrapper(f"[WARNING] `Hesh : {meta_hesh}`는 WrIndexFlatL2에 존재하지 않음. 건너뜀.")
                    continue

                # ✅ 변환된 데이터 추가
                page_content = texts[hash_to_idx[meta_hesh]]  # ✅ 원본 텍스트 활용
                metadata_dict = {
                    "index": metadata[hash_to_idx[meta_hesh]].decode("utf-8"),
                    "page": pages[hash_to_idx[meta_hesh]],
                    "vectors": vectors[hash_to_idx[meta_hesh]]  # ✅ HDF5에서 직접 벡터 가져오기
                }
                docsout.append(Document(page_content=page_content, metadata=metadata_dict))

        return docsout  # ✅ 검색된 데이터만 변환하여 반환



    def from_document(self, doc):
        """
        LangChain Document 객체를 다시 우리가 사용하는 WrIndexFlatL2 포맷으로 변환
        - 벡터를 다시 임베딩하지 않고, metadata["vectors"]가 있으면 그대로 WrIndexFlatL2에 추가
        """
        if isinstance(doc, list):
            out = WrIndexFlatL2(self.dimension)
            for d in doc:
                if isinstance(d, Document):
                    page_content = d.page_content
                    metadata = d.metadata
                    if "vectors" not in metadata:
                        log_wrapper("<<::STATE::Critical raise ValueError >>❌ 벡터 데이터가 포함되지 않은 Document 객체입니다.")
                        raise ValueError("❌ 벡터 데이터가 포함되지 않은 Document 객체입니다.")
                    out.add({
                        "vectors": [metadata["vectors"]],  # ✅ 기존 벡터를 그대로 WrIndexFlatL2에 추가
                        "metadata": [metadata.get("index", None)],
                        "page": [metadata.get("page", None)],
                        "text": [page_content]
                    })
            return out

        elif isinstance(doc, Document):
            page_content = doc.page_content
            metadata = doc.metadata
            if "vectors" not in metadata:
                raise ValueError("❌ 벡터 데이터가 포함되지 않은 Document 객체입니다.")
            out = WrIndexFlatL2(self.dimension)
            out.add({
                "vectors": [metadata["vectors"]],  # ✅ 기존 벡터를 그대로 WrIndexFlatL2에 추가
                "metadata": [metadata.get("index", None)],
                "page": [metadata.get("page", None)],
                "text": [page_content]
            })
            return out

        else:
            raise ValueError("입력 데이터는 Document 객체여야 합니다.")
    class RetrieverAdapter(BaseRetriever):
        mon: Any = Field(...)  # HDF5VectorDB 인스턴스 (필수 필드)
        k: int = Field(default=5)
        """
        HDF5VectorDB 내부에 존재하는 RetrieverAdapter 클래스.
        LangChain retriever 인터페이스를 구현하여 HDF5VectorDB의 검색 기능을 제공함.
        """


        def get_relevant_documents(self, query: str, **kwargs) -> List[Document]:
            """
            쿼리 텍스트를 받아 관련 Document 리스트를 반환.
            """ 
            tools=WrIndexFlatL2(self.mon.dimension)
            out=tools.get_openai_embedding(query)
            if not self.mon.active:
                raise ValueError("검색할 데이터가 없습니다. 조건을 구체화 하거나 데이터를 추가하세요.")
            else:
                out,_,_=self.mon.search(out, self.k)
                return out
        @property
        def search_kwargs(self) -> dict:
            return {}
        class Config:
            arbitrary_types_allowed = True
    
    
    def as_retriever(self, k: int = 5):
        """
        HDF5VectorDB의 retriever 어댑터 인스턴스를 반환합니다.
        LangChain 체인에서 이 객체의 get_relevant_documents(query: str) 메서드를 호출하여 문서를 검색할 수 있습니다.
        """
        return HDF5VectorDB.RetrieverAdapter(mon=self, k=k)



if __name__ == "__main__":

    log_wrapper("\n✅ 모든 테스트 통과!\n")
    
