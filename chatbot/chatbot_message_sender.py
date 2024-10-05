import os
from dotenv import load_dotenv

import hashlib
import hmac
import base64
import time
import requests
import json

# .env 파일 로드
load_dotenv()

# 환경 변수 가져오기
CLOVA_CHATBOT_URL = os.getenv("CLOVA-CHATBOT-URL")
SECRET_KEY = os.getenv("SECRET-KEY")


class ChatbotMessageSender:

    # chatbot api gateway url
    ep_path = CLOVA_CHATBOT_URL
    # chatbot custom secret key
    secret_key = SECRET_KEY

    def req_message_send(self, message):

        timestamp = self.get_timestamp()
        request_body = {
            'userId': 'U47b00b58c90f8e47428af8b7bddcda3d1111111',
            'timestamp': timestamp,
            'content': [
                {
                    'type': 'text',
                    'data': {
                        'details': message
                    }
                }
            ],
            'event': 'send'
        }
        json_request_body = json.dumps(request_body)

        ## make signature
        signature = self.make_signature(self.secret_key, json_request_body)

        ## headers
        custom_headers = {
            'Content-Type': 'application/json;UTF-8',
            'X-NCP-CHATBOT_SIGNATURE': signature
        }

        # print("## Timestamp : ", timestamp)
        # print("## Signature : ", signature)
        # print("## headers ", custom_headers)
        # print("## Request Body : ", json_request_body)

        ## POST Request
        response = requests.post(headers=custom_headers, url=self.ep_path, data=json_request_body)

        return response

    @staticmethod
    def get_timestamp():
        timestamp = int(time.time() * 1000)
        return timestamp

    @staticmethod
    def make_signature(secret_key, json_request_body):
        encode_secret_key = secret_key.encode('utf-8')
        encode_request_body = json_request_body.encode('utf-8')

        signature = hmac.new(encode_secret_key, encode_request_body,hashlib.sha256).digest()
        signing_key = base64.b64encode(signature).decode('utf-8')

        return signing_key


# if __name__ == '__main__':

#     message = "상금이 얼마인가요?"
#     res = ChatbotMessageSender().req_message_send(message)

#     print(res.status_code)
#     print(res.json()['content'][0]['data']['details'])