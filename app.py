from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

#======python的函數庫==========
import tempfile, os
import datetime
import openai
import time
import traceback
import mysql.connector
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



# def GPT_response(text):
#     # 接收回應
#     response = openai.Completion.create(model="gpt-3.5-turbo", prompt=text, temperature=0.5, max_tokens=500)
#     print(response)
#     # 重組回應
#     answer = response['choices'][0]['text'].replace('。','')
#     return answer


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



@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    try:
        # 檢查資料庫連線是否成功
        db_connection = test_database_connection()
        if db_connection is not None:
            db_connection.close()
            print("資料庫連接成功！")
            # 回復用戶訊息
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='收到您的訊息'))
        else:
            print("資料庫連接失敗。")
            # 如果資料庫連線失敗，向用戶發送錯誤信息
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='資料庫連接失敗'))
    except Exception as e:
        # 捕捉具體的異常
        error_message = str(e)
        print('發生錯誤:', error_message)
        print(traceback.format_exc())
        # 向用戶發送錯誤信息
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='發生錯誤: ' + error_message))

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
