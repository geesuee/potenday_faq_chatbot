import os
from dotenv import load_dotenv

import json
from tqdm import tqdm
from pathlib import Path
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain_community.document_loaders import UnstructuredHTMLLoader
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility

import clova_executor as executor



# .env 파일 로드
load_dotenv()

# 환경 변수 가져오기
API_KEY = os.getenv("X-NCP-CLOVASTUDIO-API-KEY")
APIGW_API_KEY = os.getenv("X-NCP-APIGW-API-KEY")
REQUEST_ID_FOR_SEGMENTATION = os.getenv("X-NCP-CLOVASTUDIO-REQUEST-ID-FOR-SEGMENTATION")
REQUEST_ID_FOR_EMBEDDING = os.getenv("X-NCP-CLOVASTUDIO-REQUEST-ID-FOR-EMBEDDING")
REQUEST_ID_FOR_COMPLETION = os.getenv("X-NCP-CLOVASTUDIO-REQUEST-ID-FOR-COMPLETION")



# ---------------------------
# LangChain 활용 HTML 로딩
# ---------------------------
def load_html_files_and_replace_source():
    # HTML 파일이 저장된 디렉토리
    html_files_dir = Path('./potendayguide')
    html_files = list(html_files_dir.glob("*.html"))

    # filename-to-URL 매핑 정보 로드
    with open("filename_to_url_map.json", "r") as map_file:
        filename_to_url_map = json.load(map_file)
    
    potendaydatas = []
    
    # HTML 파일 로딩하고, 'source' 값 대체
    for html_file in html_files:
        loader = UnstructuredHTMLLoader(str(html_file))
        document_data = loader.load()

        # 각 Document의 'source' 값을 URL로 대체
        for doc in document_data:
            extracted_filename = doc.metadata["source"].split("/")[-1]
            if extracted_filename in filename_to_url_map:
                doc.metadata["source"] = filename_to_url_map[extracted_filename]
            else:
                print(f"Warning: {extracted_filename}에 해당하는 URL을 찾을 수 없습니다.")

        potendaydatas.append(document_data)
        print(f"Processed {html_file}")
    
    # 데이터 플래튼(flatten) 처리
    potendaydatas_flattened = [item for sublist in potendaydatas for item in sublist]

    return potendaydatas_flattened

# ---------------------------
# Chunking : 문단 나누기
# ---------------------------
def chunking(potendaydatas_flattened):
    segmentation_executor = executor.SegmentationExecutor(
        host='clovastudio.apigw.ntruss.com',
        api_key=API_KEY,
        api_key_primary_val=APIGW_API_KEY,
        request_id=REQUEST_ID_FOR_SEGMENTATION
    )

    chunked_html = []

    for htmldata in tqdm(potendaydatas_flattened):
        try:
            request_data = {
                "postProcessMaxSize": 100,
                "alpha": -100,
                "segCnt": -1,
                "postProcessMinSize": -1,
                "text": htmldata.page_content,
                "postProcess": True
            }
             
            request_json_string = json.dumps(request_data)
            request_data = json.loads(request_json_string, strict=False)
            response_data = segmentation_executor.execute(request_data)
            result_data = [' '.join(segment) for segment in response_data]
 
        except json.JSONDecodeError as e:
            print(f"JSON decoding failed: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")
         
        for paragraph in result_data:
            chunked_document = {
                "source": htmldata.metadata["source"],
                "text": paragraph
            }
            chunked_html.append(chunked_document)
    
    return chunked_html

# ---------------------------
# Embedding : 벡터화
# ---------------------------
def embedding(chunked_html):
    embedding_executor = executor.EmbeddingExecutor(
        host='clovastudio.apigw.ntruss.com',
        api_key=API_KEY,
        api_key_primary_val=APIGW_API_KEY,
        request_id=REQUEST_ID_FOR_EMBEDDING
    )

    for i, chunked_document in enumerate(tqdm(chunked_html)):
        try:
            request_json = {
                "text": chunked_document['text']
            }
            request_json_string = json.dumps(request_json)
            request_data = json.loads(request_json_string, strict=False)
            response_data = embedding_executor.execute(request_data)
        except ValueError as e:
            print(f"Embedding API Error. {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
         
        chunked_document["embedding"] = response_data
    
    return chunked_html

# ---------------------------
# Vector DB : Milvus 벡터 DB에 벡터 저장 및 사용
# ---------------------------
def drop_collection_if_exists(collection_name):
    # Milvus 서버 연결
    connections.connect("default", host="localhost", port="19530")

    # 컬렉션이 존재하는지 확인
    if utility.has_collection(collection_name):
        # 컬렉션을 가져옴
        collection = Collection(name=collection_name)
        
        # 컬렉션 드롭 (모든 데이터 삭제)
        collection.drop()
        print(f"컬렉션 '{collection_name}'이 삭제되었습니다.")

    else:
        print(f"컬렉션 '{collection_name}'이 존재하지 않습니다. 삭제를 건너뜁니다.")

def save_vector_in_collection(collection_name, chunked_html):
    connections.connect("default", host="localhost", port="19530")

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=3000),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=9000),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024)
    ]

    # 스키마
    schema = CollectionSchema(fields, description="포텐데이 FAQ")

    # 컬렉션
    collection = Collection(name=collection_name, schema=schema, using='default', shards_num=2)

    for item in chunked_html:
        source_list = [item['source']]
        text_list = [item['text']]
        embedding_list = [item['embedding']]
        
        entities = [
            source_list,
            text_list,
            embedding_list
        ]
        
        insert_result = collection.insert(entities)
        print("데이터 Insertion이 완료된 ID:", insert_result.primary_keys)

    print("데이터 Insertion이 전부 완료되었습니다")

def indexing(collection_name):
    connections.connect("default", host="localhost", port="19530")

    index_params = {
        "metric_type": "IP",
        "index_type": "HNSW",
        "params": {
            "M": 8,
            "efConstruction": 200
        }
    }

    collection = Collection(collection_name)
    collection.create_index(field_name="embedding", index_params=index_params)
    utility.index_building_progress(collection_name)
    
    print([index.params for index in collection.indexes])

def get_collection_from_milvus(collection_name):
    connections.connect("default", host="localhost", port="19530")
    collection = Collection(collection_name)

    return collection

# ---------------------------
# Retrieval -> HyperCLOVA X
# ---------------------------
def query_embed(text: str):
    request_data = {"text": text}

    embedding_executor = executor.EmbeddingExecutor(
        host='clovastudio.apigw.ntruss.com',
        api_key=API_KEY,
        api_key_primary_val=APIGW_API_KEY,
        request_id=REQUEST_ID_FOR_EMBEDDING
    )

    response_data = embedding_executor.execute(request_data)

    return response_data

def clova_chat(collection, realquery: str) -> str:
    query_vector = query_embed(realquery)

    collection.load()

    search_params = {"metric_type": "IP", "params": {"ef": 64}}
    results = collection.search(
        data=[query_vector],  # 검색할 벡터 데이터
        anns_field="embedding",  # 검색을 수행할 벡터 필드 지정
        param=search_params,
        limit=10,
        output_fields=["source", "text"]
    )
 
    reference = []
 
    for hit in results[0]:
        distance = hit.distance
        source = hit.entity.get("source")
        text = hit.entity.get("text")
        reference.append({"distance": distance, "source": source, "text": text})
 
    completion_executor = executor.CompletionExecutor(
        host='https://clovastudio.stream.ntruss.com',
        api_key=API_KEY,
        api_key_primary_val=APIGW_API_KEY,
        request_id=REQUEST_ID_FOR_COMPLETION
    )

    preset_texts = [
        {"role":"system","content":"- 너의 역할은 사용자의 질문에 reference를 바탕으로 답변하는거야.\n- 상냥하고 친절하고 귀여운 어투로 대답해줘.\n- 반드시 너가 가지고 있는 지식은 모두 배제하고, 주어진 reference의 내용만을 바탕으로 답변해야해.\n- 답변의 출처가 되는 'source'도 답변과 함께 {출처: }의 형태로 제공해야해.\n- 만약 사용자의 질문이 reference와 관련이 없다면, {오잉님, 도와주세요.}라고만 반드시 말해야해.\n- 네가 가진 지식은 반드시 다 배제하고 주어진 reference에 있는 내용만을 바탕으로 대답해."},
    ]
 
    for ref in reference:
        preset_texts.append(
            {
                "role": "system",
                "content": f"reference: {ref['text']}, url: {ref['source']}"
            }
        )
 
    preset_texts.append({"role": "user", "content": realquery})
 
    request_data = {
        "messages": preset_texts,
        "topP": 0.6,
        "topK": 0,
        "maxTokens": 1024,
        "temperature": 0.5,
        "repeatPenalty": 1.2,
        "stopBefore": [],
        "includeAiFilters": False
    }
 
    # LLM 생성 답변 반환
    response_data = completion_executor.execute(request_data)
 
    return response_data

# ---------------------------
# 최종 RAG 기반 AI 응답 반환
# ---------------------------
def chat_with_rag(user_message, collection_name):
    collection = get_collection_from_milvus(collection_name)
    clova_message = clova_chat(collection, user_message)

    return clova_message