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

app = Flask(__name__)
static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')
# Channel Access Token
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
# Channel Secret
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))
# OPENAI API Key初始化設定
openai.api_key = os.getenv('OPENAI_API_KEY')


def GPT_response(text):
    # 接收回應
    response = openai.Completion.create(model="gpt-3.5-turbo", prompt=text, temperature=0.5, max_tokens=500)
    print(response)
    # 重組回應
    answer = response['choices'][0]['text'].replace('。','')
    return answer

# 設定 MySQL 連接資訊
db_config = {
    'host': 'localhost',
    'user': 'admin',
    'password': 'wei920116',
    'database': 'newschema',
    'charset': 'utf8'
}

#test
# 監聽所有來自 /callback 的 Post Request
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


# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    try:
        GPT_answer = GPT_response(msg)
        print(GPT_answer)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(GPT_answer))
    except Exception as e:  # 捕捉具體的異常
        error_message = str(e)  # 將異常轉換為字符串
        print('發生錯誤:', error_message)  # 在後台日誌中打印錯誤
        print(traceback.format_exc())  # 打印錯誤堆疊追踪
        # 向用戶發送錯誤信息
        line_bot_api.reply_message(event.reply_token, TextSendMessage('發生錯誤: ' + error_message))

    # 獲取使用者傳來的文字訊息
    user_input = event.message.text

    # 檢查是否輸入了有效的使用者名稱
    if user_input.lower() == "使用者名稱":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入您要查詢的使用者名稱，例如：JohnDoe")
        )
        return

    # 連接 MySQL 資料庫
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    try:
        # 使用參數化查詢
        query = "SELECT * FROM user WHERE user_name = %s"
        cursor.execute(query, (user_input,))
        result = cursor.fetchone()

        # 回覆使用者
        if result:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"使用者名稱: {result[0]}, 其他資訊: {result[1]}")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="找不到該使用者名稱的資料。")
            )
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # 關閉 MySQL 連接
        cursor.close()
        connection.close()

        


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
        
        
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
