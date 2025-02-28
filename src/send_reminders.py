import os
import sqlite3
import datetime
import pytz
from linebot import LineBotApi
from linebot.models import TextSendMessage
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from src.utils import send_confirm_message, update_user_state

DB_PATH = "./data/outputs/chatbot.db"
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)


def check_reminders():
    """リマインダーを確認し、送信する"""
    now = datetime.datetime.now(pytz.timezone("Asia/Tokyo"))
    one_day_ago = now - datetime.timedelta(days=1)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # 3日後リマインダーの送信
        cursor.execute(
            "SELECT user_id FROM user_state WHERE reminder_3days BETWEEN ? AND ?",
            (
                one_day_ago.strftime("%Y-%m-%d %H:%M:%S"),
                now.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        users_3days = cursor.fetchall()

        for user in users_3days:
            user_id = user[0]
            line_bot_api.push_message(
                user_id,
                TextSendMessage(
                    text="調子はいかがですか？何か乳がんについて知りたいことがありましたら私までお気軽におたずねください。"
                ),
            )
            print("3日後リマインダーの送信")
            update_user_state(user_id, 4.3)

        # 1週間後リマインダーの送信
        cursor.execute(
            "SELECT user_id FROM user_state WHERE reminder_7days BETWEEN ? AND ?",
            (
                one_day_ago.strftime("%Y-%m-%d %H:%M:%S"),
                now.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        users_7days = cursor.fetchall()

        for user in users_7days:
            user_id = user[0]
            line_bot_api.push_message(
                user_id,
                TextSendMessage(
                    text="調子はいかがですか？何か乳がんについて知りたいことがありましたら私までお気軽におたずねください。"
                ),
            )
            print("1週間後リマインダーの送信")
            update_user_state(user_id, 4.7)

        # 2週間後リマインダーの送信
        cursor.execute(
            "SELECT user_id FROM user_state WHERE reminder_14days BETWEEN ? AND ?",
            (
                one_day_ago.strftime("%Y-%m-%d %H:%M:%S"),
                now.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        users_14days = cursor.fetchall()

        for user in users_14days:
            user_id = user[0]
            line_bot_api.push_message(
                user_id,
                TextSendMessage(
                    text="調子はいかがですか？何か乳がんについて知りたいことがありましたら私までお気軽におたずねください。"
                ),
            )
            print("2週間後リマインダーの送信")
            update_user_state(user_id, 4.14)

        # 3週間後リマインダーの送信
        cursor.execute(
            "SELECT user_id FROM user_state WHERE reminder_21days BETWEEN ? AND ?",
            (
                one_day_ago.strftime("%Y-%m-%d %H:%M:%S"),
                now.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        users_21days = cursor.fetchall()

        for user in users_21days:
            user_id = user[0]
            line_bot_api.push_message(
                user_id,
                TextSendMessage(
                    text="調子はいかがですか？何か乳がんについて知りたいことがありましたら私までお気軽におたずねください。"
                ),
            )
            print("3週間後リマインダーの送信")
            update_user_state(user_id, 4.21)

        # 利用日の前日リマインダーの送信
        cursor.execute(
            "SELECT user_id FROM user_state WHERE before_the_last_day BETWEEN ? AND ?",
            (
                one_day_ago.strftime("%Y-%m-%d %H:%M:%S"),
                now.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        users_before_the_last_day = cursor.fetchall()

        for user in users_before_the_last_day:
            user_id = user[0]
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text="明日で私のお手伝いできる期間が終了します。"),
            )
            print("利用日の前日リマインダーの送信")
            update_user_state(user_id, 4.9)

        # 利用終了日1ヶ月後リマインダーの送信
        cursor.execute(
            "SELECT user_id FROM user_state WHERE after_use_ends BETWEEN ? AND ?",
            (
                one_day_ago.strftime("%Y-%m-%d %H:%M:%S"),
                now.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        users_after_use_ends = cursor.fetchall()

        messages = [
            """本日で利用期間が終了です。ご利用ありがとうございました。最後に、下記のURLにアクセスし、アンケートにお答えください。\nhttp:// …\n（回答の際に研究IDが必要です）
    """,
            "また、さらに詳しいご感想を聞かせていただきたく、インタビュー調査も予定しています。ご協力くださる方は、アンケートの最後の同意確認欄と、個人情報をご入力ください。",
        ]
        for user in users_after_use_ends:
            user_id = user[0]
            line_bot_api.push_message(
                user_id, [TextSendMessage(text=message) for message in messages]
            )
            send_confirm_message(user_id)
            print("利用終了日1ヶ月後リマインダーの送信")
            update_user_state(user_id, 5)

        # 送信済みのリマインダーを削除（再送防止）
        cursor.execute(
            "UPDATE user_state SET reminder_3days = NULL WHERE reminder_3days = ?",
            (now,),
        )
        cursor.execute(
            "UPDATE user_state SET reminder_7days = NULL WHERE reminder_7days = ?",
            (now,),
        )
        cursor.execute(
            "UPDATE user_state SET reminder_14days = NULL WHERE reminder_14days = ?",
            (now,),
        )
        cursor.execute(
            "UPDATE user_state SET reminder_21days = NULL WHERE reminder_21days = ?",
            (now,),
        )
        cursor.execute(
            "UPDATE user_state SET before_the_last_day = NULL WHERE before_the_last_day = ?",
            (now,),
        )
        cursor.execute(
            "UPDATE user_state SET after_use_ends = NULL WHERE after_use_ends = ?",
            (now,),
        )

        conn.commit()


# # 1分ごとにチェック
# scheduler.add_job(check_reminders, "interval", minutes=1)
# scheduler.start()
