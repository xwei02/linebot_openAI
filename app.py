import logging
from flask import Flask, request, abort, jsonify,send_from_directory

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
import schedule
import time
import threading
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.DEBUG)



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

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('/Users/wuxinwei/linebot_openai3', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

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

def send_reminders():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        next_week = datetime.datetime.now() + timedelta(days=7)
        next_week_str = next_week.strftime('%Y-%m-%d')

        # 获取需要提醒的医疗预约信息
        cursor.execute("""
            SELECT user.line_id, medical_appointment.appointment_division, medical_appointment.appointment_date, medical_appointment.appointment_timeperiod, medical_appointment.doctor_name
            FROM medical_appointment
            JOIN user ON medical_appointment.user_id = user.user_id
            WHERE medical_appointment.appointment_date = %s
        """, (next_week_str,))
        medical_reminders = cursor.fetchall()
        app.logger.info("獲取到的醫療訊息: %s", medical_reminders)

        # 获取需要提醒的检查预约信息
        cursor.execute("""
            SELECT user.line_id, inspection_appointment.inspection_item, inspection_appointment.appointment_date, inspection_appointment.chicking_location, inspection_appointment.test_preparation, inspection_appointment.inspection_precautions, inspection_appointment.inspection_availableTime
            FROM inspection_appointment
            JOIN user ON inspection_appointment.user_id = user.user_id
            WHERE inspection_appointment.appointment_date = %s
        """, (next_week_str,))
        inspection_reminders = cursor.fetchall()
        app.logger.info("獲取到的醫療訊息: %s", inspection_reminders)

        # 发送医疗预约提醒
        for reminder in medical_reminders:
            line_id, division, date, timeperiod, doctor = reminder
            message = (
                f"提醒您，您在下個禮拜有一個醫療預約：\n"
                f"預約科別: {division}\n"
                f"預約日期: {date}\n"
                f"預約時段: {timeperiod}\n"
                f"醫生姓名: {doctor}"
            )
            line_bot_api.push_message(line_id, TextSendMessage(text=message))

        # 发送检查预约提醒
        for reminder in inspection_reminders:
            line_id, item, date, location, preparation, precautions, available_time = reminder
            message = (
                f"提醒您，您在下個禮拜有一個檢查預約：\n"
                f"檢查項目: {item}\n"
                f"預約日期: {date}\n"
                f"檢查地點: {location}\n"
                f"檢查準備: {preparation}\n"
                f"檢查注意事項: {precautions}\n"
                f"可用檢查時間: {available_time}"
            )
            line_bot_api.push_message(line_id, TextSendMessage(text=message))

        cursor.close()
        connection.close()
    except mysql.connector.Error as e:
        app.logger.error("數據庫錯誤: %s", e)
    except Exception as e:
        app.logger.error("發生錯誤: %s", e)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)

# 設置每天運行一次的定時任務
schedule.every().day.at("17:19").do(send_reminders)


# 在一個單獨的線程中運行定時任務
threading.Thread(target=run_schedule).start()

@app.route("/callback", methods=['POST'])
def callback():
    try:
        # get X-Line-Signature header value
        signature = request.headers['X-Line-Signature']

        # get request body as text
        body = request.get_data(as_text=True)
        app.logger.info("Request body: " + body)

        # handle webhook body
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    except Exception as e:
        app.logger.error(f"Exception in callback: {e}")
        abort(500)
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
# def test_database_connection():
#     try:
#         # 連接 MySQL 資料庫
#         connection = mysql.connector.connect(**db_config)
#         return connection
#     except Exception as e:
#         print(f"Error connecting to database: {e}")
#         return None

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_id = event.source.user_id  # 獲取用戶的line_id
    user_message = event.message.text
    app.logger.info(f"Received message: {user_message} from user: {line_id}")

    if user_message == "約診/檢查事項":
        # 獲取預約信息並回覆
        reminder_response = get_appointment_reminders(line_id)
        line_bot_api.reply_message(
            event.reply_token,
            reminder_response
        )
    else:
        # 其他消息的處理邏輯
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="您好！請問您有什麼手術相關的問題嗎？")
        )

def get_appointment_reminders(line_id):
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        cursor.execute("SELECT user_id FROM user WHERE line_id = %s", (line_id,))
        user = cursor.fetchone()

        if not user:
            app.logger.info("沒有找到line_id為 %s 的用戶", line_id)
            return [TextSendMessage(text="沒有找到您的信息，請先綁定賬戶。")]

        user_id = user[0]
        app.logger.info("找到line_id為 %s 的用戶，user_id為 %s", line_id, user_id)

        # 獲取醫療預約信息
        cursor.execute("""
            SELECT appointment_division, appointment_date, appointment_timeperiod, doctor_name
            FROM medical_appointment
            WHERE user_id = %s
        """, (user_id,))
        medical_appointments = cursor.fetchall()
        app.logger.info("醫療預約信息: %s", medical_appointments)

        # 獲取檢查預約信息
        cursor.execute("""
            SELECT inspection_item, appointment_date, chicking_location, test_preparation, inspection_precautions, inspection_availableTime
            FROM inspection_appointment
            WHERE user_id = %s
        """, (user_id,))
        inspection_appointments = cursor.fetchall()
        app.logger.info("檢查預約信息: %s", inspection_appointments)

        cursor.close()
        connection.close()

        messages = []

        # 構建醫療預約信息消息
        if medical_appointments:
            for appt in medical_appointments:
                message = (
                    f"醫療預約信息\n"
                    f"預約科別: {appt[0]}\n"
                    f"預約日期: {appt[1]}\n"
                    f"預約時段: {appt[2]}\n"
                    f"醫生姓名: {appt[3]}"
                )
                messages.append(TextSendMessage(text=message))
        else:
            messages.append(TextSendMessage(text="沒有找到任何醫療預約信息。"))

        # 構建檢查預約信息消息
        if inspection_appointments:
            for insp in inspection_appointments:
                message = (
                    f"檢查預約信息\n"
                    f"檢查項目: {insp[0]}\n"
                    f"預約日期: {insp[1]}\n"
                    f"檢查地點: {insp[2]}\n"
                    f"檢查準備: {insp[3]}\n"
                    f"檢查注意事項- {insp[4]}\n"
                    f"可用檢查時間: {insp[5]}"
                )
                messages.append(TextSendMessage(text=message))
        else:
            messages.append(TextSendMessage(text="沒有找到任何檢查預約信息。"))

        return messages
    except mysql.connector.Error as e:
        app.logger.error("數據庫錯誤: %s", e)
        return [TextSendMessage(text=f"數據庫錯誤，請稍後再試。錯誤詳情：{e}")]
    except Exception as e:
        app.logger.error("發生錯誤: %s", e)
        return [TextSendMessage(text=f"發生錯誤，請稍後再試。錯誤詳情：{e}")]
    

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
                app.logger.info("用戶信息不匹配")
                return "用戶資訊不匹配，請檢查您的身分證號碼和生日。"
        except mysql.connector.Error as e:
            app.logger.error(f"Database error: {e}")
            return f"An error occurred: {e}"
        except Exception as e:
            app.logger.error(f"An error occurred: {e}")
            return f"An error occurred: {e}"

    return render_template('bind_account.html')
        
@app.route('/')
def index():
    return 'Hello, World!'

@app.route('/bind_success')
def bind_success():
    return "綁定成功！"

    
import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 80))
    app.run(host='0.0.0.0', port=port)