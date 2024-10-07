import streamlit as st

from chatbot.chatbot_message_sender import ChatbotMessageSender
from clovastudio.clovastudio_completion_executor import sentence_refine

# 하이퍼 클로바 X
def call_hyper_clovax(user_message):
    # rag 방식
    # collection_name = "potenday_faq"
    # return rag.chat_with_rag(user_message, collection_name)

    # chatbot 방식
    chatbotMessageSender = ChatbotMessageSender()
    res = chatbotMessageSender.req_message_send(user_message)
    reply = res.json()['content'][0]['data']['details']

    # 실패 메세지 반환 시, clova studio 문장 교정 후 재요청
    if reply == "제가 알지 못하는 내용이에요. 도와주세요 오잉님!":
        # 문장 교정
        st.text("1차 요청에 실패해서 문장 교정을 시작합니다.")
        question_count, questions = sentence_refine(user_message)
        st.text(questions)

        # chatbot 재요청
        answers = []
        for q in questions:
            q = q.strip()
            res = chatbotMessageSender.req_message_send(user_message)
            reply = res.json()['content'][0]['data']['details']
            answers.append(reply)
            st.text(reply)

        # 답변 중복 제거 후 통합
        final_reply = '\n'.join(set(answers))

        return final_reply
    
    # 성공 메세지 반환 시, 그대로 리턴
    else:
        return reply


# Streamlit 페이지 제목 설정
st.title("포텐데이 FAQ 테스트")

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

# 채팅 기록을 출력하는 부분 (최근 대화가 위에 표시되도록 chat_history 역순으로 출력)
for chat in reversed(st.session_state.chat_history):
    st.write(f"**👤 사용자:** {chat['user']}")
    st.write(f"**🍀 CLOVA:** {chat['bot']}")
    st.divider()
