import os
from dotenv import load_dotenv

import json
import requests
import re

# .env 파일 로드
load_dotenv()

# 환경 변수 가져오기
API_KEY = os.getenv("X-NCP-CLOVASTUDIO-API-KEY")
APIGW_API_KEY = os.getenv("X-NCP-APIGW-API-KEY")
REQUEST_ID_FOR_COMPLETION = os.getenv("X-NCP-CLOVASTUDIO-REQUEST-ID-FOR-COMPLETION2")


class CompletionExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self._host = host
        self._api_key = api_key
        self._api_key_primary_val = api_key_primary_val
        self._request_id = request_id

    def execute(self, completion_request):
        headers = {
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        with requests.post(
            self._host + '/testapp/v1/chat-completions/HCX-003',
            headers=headers, 
            json=completion_request, 
            stream=True
        ) as r:
            longest_line = ""
            for line in r.iter_lines():
                if line:
                    decoded_line = line.decode("utf-8")
                    if decoded_line.startswith("data:"):
                        event_data = json.loads(decoded_line[len("data:"):])
                        message_content = event_data.get("message", {}).get("content", "")
                        if len(message_content) > len(longest_line):
                            longest_line = message_content
            final_answer = longest_line
        
        return final_answer
    

def sentence_refine(request_text):
    completion_executor = CompletionExecutor(
        host='https://clovastudio.stream.ntruss.com',
        api_key = API_KEY,
        api_key_primary_val = APIGW_API_KEY,
        request_id = REQUEST_ID_FOR_COMPLETION
    )

    preset_text = [
        {"role":"system","content":"[작업]\n- 맞춤법 교정을 교정해줘\n- 문장의 주술 구조 교정, 문법 교정 등 문장 교정을 해줘\n- 만약 한 문장에 여러 질문이 섞여있으면 내용상 중복을 제거하고 한 문장에 한 질문만 들어가도록 분리해줘\n- 질문에 없는 문장을 추가하면 절대 안돼\n\n[결과물]\n- 한 문장에 한 질문만 들어가도록 하고 문장 교정을 맞춘 결과 문장이 총 몇 개인지\n- 결과 문장은 무엇인지 아래 형식으로 출력해줘\n\"\"\"\n질문 수 : []개\n질문 : []//[]//[]\n\"\"\""},
        {"role":"user","content":"중간산출물은 day5 자정까지만 제출하면 되는 건가요?"},
        {"role":"assistant","content":"질문 수 : 1개\n질문 : 중간산출물은 day5 자정까지만 제출하면 되는 건가요?"},
        {"role":"user","content":"팀 빌딩은 언제까지 하고 한 팀 당 최대 인원은 몇 명인가요?"},
        {"role":"assistant","content":"질문 수 : 2개\n질문 : 팀 빌딩은 언제까지 하나요? \n질문 : 한 팀 당 최대 인원은 몇 명인가요?"},
        {"role":"user","content":request_text}
    ]

    request_data = {
        'messages': preset_text,
        'topP': 0.8,
        'topK': 0,
        'maxTokens': 256,
        'temperature': 0.5,
        'repeatPenalty': 5.0,
        'stopBefore': [],
        'includeAiFilters': True,
        'seed': 0
    }

    response_data = completion_executor.execute(request_data)

    # 질문 수 추출 (정규 표현식을 사용하여 숫자 추출)
    question_count = int(re.search(r'질문 수\s*:\s*(\d+)', response_data).group(1))

    # 질문들 추출 (정규 표현식으로 '질문 :' 뒤에 나오는 텍스트들 추출)
    questions = re.findall(r'질문\s*:\s*(.+)', response_data)

    return question_count, questions