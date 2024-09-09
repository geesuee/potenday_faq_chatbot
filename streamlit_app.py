import streamlit as st

import clova_rag_module as rag

# 하이퍼 클로바 X
def call_hyper_clovax(user_message):
    collection_name = "potenday_faq"
    return rag.chat_with_rag(user_message, collection_name)

# Streamlit 페이지 제목 설정
st.title("CLOVA Studio 포텐데이 FAQ 테스트")

# 세션 상태에서 입력 필드와 채팅 기록을 관리
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

if 'input_text' not in st.session_state:
    st.session_state['input_text'] = ""

# 콜백 함수: 사용자가 텍스트를 입력할 때마다 호출됨
def submit_message():
    # 사용자가 입력한 메시지를 불러옴
    user_message = st.session_state.input_text
    
    if user_message:
        # API 호출하여 응답 받기
        response = call_hyper_clovax(user_message)
        
        # 채팅 기록에 사용자 메시지와 AI 응답 추가
        st.session_state.chat_history.append({"user": user_message, "bot": response})

        # 입력 필드 비우기
        st.session_state['input_text'] = ""

# 대화 내역을 초기화하는 함수
def clear_chat():
    st.session_state['chat_history'] = []

# 채팅 입력을 위한 텍스트 박스
st.text_input("질문을 입력하세요:", 
              key="input_text", 
              on_change=submit_message)

# 대화 내역을 지우는 버튼
if st.button("대화 내역 지우기"):
    clear_chat()

# 채팅 기록을 출력하는 부분
for chat in st.session_state.chat_history:
    st.write(f"**👤 사용자:** {chat['user']}")
    st.write(f"**🍀 CLOVA:** {chat['bot']}")
    st.divider()
