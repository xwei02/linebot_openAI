from flask import Flask, request, abort, jsonify

from linebot import LineBotApi, WebhookHandler


from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import TextMessage, MessageEvent, TextSendMessage
from flask import Flask, request, render_template, redirect, url_for
import mysql.connector
from mysql.connector import Error
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction


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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text
    app.logger.info(f"Received message: {user_message} from user: {user_id}")

    # 生成绑定账户的URL
    bind_url = f"{request.url_root}bind_account?line_id={user_id}"

    # 构建回复消息
    reply_text = f"请点击以下链接绑定您的账号：\n{bind_url}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

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

@app.route('/bind_account', methods=['GET', 'POST'])
def bind_account():
    if request.method == 'POST':
        line_id = request.form['line_id']
        user_idNumber = request.form['user_idNumber']
        birthdate = request.form['birthdate']
        app.logger.info(f"line_id: {line_id}, user_idNumber: {user_idNumber}, birthdate: {birthdate}")

        try:
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM user WHERE user_idNumber = %s AND birthdate = %s", (user_idNumber, birthdate))
            user = cursor.fetchone()
            if user:
                cursor.execute("UPDATE user SET line_id = %s WHERE user_idNumber = %s", (line_id, user_idNumber))
                connection.commit()
                cursor.close()
                connection.close()

                # 返回成功页面
                return redirect(url_for('bind_success'))
            else:
                app.logger.info("用户信息不匹配")
                return "用戶資訊不匹配，請檢查您的身分證號碼和生日。"
        except mysql.connector.Error as e:
            app.logger.error(f"Database error: {e}")
            return f"An error occurred: {e}"
        except Exception as e:
            app.logger.error(f"An error occurred: {e}")
            return f"An error occurred: {e}"

    return render_template('bind_account.html')

@app.route('/bind_success')
def bind_success():
       return "綁定成功！"

        
@app.route('/')
def index():
    return 'Hello, World!'

@app.route('/send_reminder', methods=['GET'])
def send_reminder():
    line_id = request.args.get('line_id')
    if not line_id:
        return jsonify({"error": "Missing line_id"}), 400

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute("SELECT user_id FROM user WHERE line_id = %s", (line_id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        user_id = user[0]
        cursor.execute("""
            SELECT appointment_division, appointment_date, appointment_timeperiod, doctor_name
            FROM medical_appointment
            WHERE user_id = %s
        """, (user_id,))
        appointments = cursor.fetchall()
        cursor.close()
        connection.close()

        if not appointments:
            line_bot_api.push_message(line_id, TextSendMessage(text="没有找到任何预约信息。"))
        else:
            messages = []
            for appt in appointments:
                message = (
                    f"预约科别: {appt[0]}\n"
                    f"预约日期: {appt[1]}\n"
                    f"预约时段: {appt[2]}\n"
                    f"医生姓名: {appt[3]}"
                )
                messages.append(TextSendMessage(text=message))

            # 发送所有消息
            line_bot_api.push_message(line_id, messages)

        return jsonify({"status": "success"}), 200
    except mysql.connector.Error as e:
        app.logger.error(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        app.logger.error(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500

@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    if data == 'send_reminder':
        send_reminder({'line_id': event.source.user_id})

    
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 80))
    app.run(host='0.0.0.0', port=port)