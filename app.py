from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler


from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import TextMessage, MessageEvent, TextSendMessage


#======python的函數庫==========
import tempfile, os
import datetime
import openai
import time
import traceback
import mysql.connector
import json
#======python的函數庫==========
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')

def GPT_response(text):
    response = openai.ChatCompletion.create(
        model="gpt-4",  # 确保使用正确的模型名称
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": text}
        ],
        temperature=0.5,
        max_tokens=500
    )
    answer = response['choices'][0]['message']['content'].strip()
    return answer


# 設定 MySQL 連接資訊
db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'wei920116',
    'database': 'newschema',
    'charset': 'utf8'
}

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

# 測試資料庫連接函數
def test_database_connection():
    try:
        # 連接 MySQL 資料庫
        connection = mysql.connector.connect(**db_config)
        return connection
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def test_openai_connection():
    try:
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "Hello, world!"}]
        )
        
        print("OpenAI API test response:", response['choices'][0]['message']['content'].strip())
        return True
    except Exception as e:
        print("Failed to connect to OpenAI API:", str(e))
        return False

if test_openai_connection():
    print("Connection to OpenAI API is successful.")
else:
    print("Failed to connect to OpenAI API.")


# 调用测试函数
if test_openai_connection():
    print("Connection to OpenAI API is successful.")
else:
    print("Failed to connect to OpenAI API.")



@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    app.logger.info(f"Received message: {user_message}")

    # 检测是否为手术相关的问题
    if '手術' in user_message or '治療方法' in user_message or '注意事項' in user_message:
        prompt_text = f"身為醫生，請用繁體中文回答以下手術相關的問題：\n{user_message}"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt_text}]
            )
            answer = response['choices'][0]['message']['content'].strip()
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=answer)
            )
            app.logger.info(f"Sent reply: {answer}")
        except LineBotApiError as e:
            app.logger.error(f"Failed to reply message: {str(e)}")
        except Exception as e:
            app.logger.error(f"OpenAI error: {str(e)}")
    else:
        # 如果不是手术相关的问题，可以选择不回答或给予通用回答
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="您好！請問您有什麼手術相關的問題嗎？")
        )

@handler.add(PostbackEvent)
def handle_message(event):
    print(event.postback.data)


@handler.add(MemberJoinedEvent)
def welcome(event):
    uid = event.joined.members[0].user_id
    gid = event.source.group_id
    profile = line_bot_api.get_group_member_profile(gid, uid)
    name = profile.display_name
    message = TextSendMessage(text=f'{name}歡迎加入')
    line_bot_api.reply_message(event.reply_token, message)
        
@app.route('/')
def index():
    return 'Hello, World!'

    
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 80))
    app.run(host='0.0.0.0', port=port)
