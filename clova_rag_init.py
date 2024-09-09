from datetime import datetime

import clova_rag_module as rag

# ---------------------------
# RAG 초기 설정 : 벡터화 후 적재
# ---------------------------

# HTML 로딩
potendaydatas_flattened = rag.load_html_files_and_replace_source()

# 텍스트 문단 나누기
chunked_html = rag.chunking(potendaydatas_flattened)

# 텍스트 벡터화
chunked_html_vector = rag.embedding(chunked_html)

# Milvus 컬렉션 삭제
collection_name = "potenday_faq"
rag.drop_collection_if_exists(collection_name)

# Milvus 벡터 적재
rag.save_vector_in_collection(collection_name, chunked_html_vector)

# Milvus 인덱스 생성
rag.indexing(collection_name)

print(f"-------------------- RAG 초기 설정 완료({datetime.now()}) -------------------- ")