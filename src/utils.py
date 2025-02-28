import json
import os
import random
import sqlite3
import string
import requests
import httpx
import datetime
import pytz
from fastapi import FastAPI, Request
from linebot.models import TextMessage
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
)
from dotenv import load_dotenv


load_dotenv()

channel_secret = os.getenv("LINE_CHANNEL_SECRET", None)
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)


configuration = Configuration(access_token=channel_access_token)

app = FastAPI()
async_api_client = AsyncApiClient(configuration)
line_bot_api = AsyncMessagingApi(async_api_client)

DB_PATH = "./data/outputs/chatbot.db"


def get_jst_now(event):

    utc_timestamp = event.timestamp
    utc_dt = datetime.datetime.utcfromtimestamp(
        utc_timestamp / 1000
    )  # UTCのタイムスタンプをミリ秒から秒に変換してから変換
    jst_timezone = datetime.timezone(
        datetime.timedelta(hours=9)
    )  # 日本時間のタイムゾーンオブジェクトを作成
    jst_dt = utc_dt.replace(tzinfo=datetime.timezone.utc).astimezone(
        jst_timezone
    )  # UTCを日本時間に変換
    return jst_dt


# SQLite データベース（初回起動時にテーブルを作成）
def initialize_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # テーブル作成
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            user_message TEXT NOT NULL,
            response_id TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            reply_id TEXT NOT NULL,
            version TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_state (
            user_id TEXT PRIMARY KEY,
            research_id TEXT,
            step INTEGER NOT NULL,
            last_question TEXT,
            registration_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            reminder_3days TEXT,
            reminder_7days TEXT,
            reminder_14days TEXT,
            reminder_21days TEXT,
            before_the_last_day TEXT,
            after_use_ends TEXT
        )
        """
    )

    conn.commit()
    conn.close()


initialize_db()


# メッセージをデータベースに保存
def save_message_to_db(
    user_id, message_id, user_message, response_id, reply_id, timestamp, version
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO chat_logs (user_id, message_id, user_message, response_id, reply_id, timestamp, version) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, message_id, user_message, response_id, reply_id, timestamp, version),
    )

    conn.commit()
    conn.close()


# ユーザーの状態を取得
def get_user_state(user_id):
    conn = sqlite3.connect(DB_PATH)  # 各関数ごとに接続を作成
    cursor = conn.cursor()

    cursor.execute(
        "SELECT step, research_id, last_question FROM user_state WHERE user_id=?",
        (user_id,),
    )
    row = cursor.fetchone()

    conn.close()
    return row if row else (0, None, None)


# ユーザーの状態を更新
def update_user_state(
    user_id,
    step,
    research_id=None,
    last_question=None,
    registration_time=None,
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 既存の research_id, registration_time, reminder_3days, reminder_7days を取得
    cursor.execute(
        "SELECT research_id, registration_time, reminder_3days, reminder_7days, reminder_14days, reminder_21days, before_the_last_day, after_use_ends FROM user_state WHERE user_id=?",
        (user_id,),
    )
    row = cursor.fetchone()

    existing_research_id = None
    existing_registration_time = None
    existing_reminder_3days = None
    existing_reminder_7days = None
    existing_reminder_14days = None
    existing_reminder_21days = None
    existing_before_the_last_day = None
    existing_after_use_ends = None

    if row is not None:
        (
            existing_research_id,
            existing_registration_time,
            existing_reminder_3days,
            existing_reminder_7days,
            existing_reminder_14days,
            existing_reminder_21days,
            existing_before_the_last_day,
            existing_after_use_ends,
        ) = row

        # research_id の更新ロジック（すでにある場合は変更しない）
        if step == 1:
            pass  # 新しい research_id を適用
        elif existing_research_id is None and research_id is not None:
            pass  # 新しい research_id を適用
        else:
            research_id = existing_research_id  # 既存の値を保持

    # registration_time の更新ロジック（すでにある場合は変更しない）
    if registration_time is not None:
        registration_time = registration_time
        # 3日後と1週間後のリマインダーを計算
        reminder_3days = registration_time + datetime.timedelta(days=3)
        reminder_7days = registration_time + datetime.timedelta(days=7)
        reminder_14days = registration_time + datetime.timedelta(days=14)
        reminder_21days = registration_time + datetime.timedelta(days=21)
        before_the_last_day = registration_time + datetime.timedelta(days=31)
        after_use_ends = registration_time + datetime.timedelta(days=31+31)

    elif existing_registration_time is not None:
        registration_time = existing_registration_time
        reminder_3days = existing_reminder_3days
        reminder_7days = existing_reminder_7days
        reminder_14days = existing_reminder_14days
        reminder_21days = existing_reminder_21days
        before_the_last_day = existing_before_the_last_day
        after_use_ends = existing_after_use_ends

    # データが存在するか確認
    cursor.execute(
        "SELECT 1 FROM user_state WHERE user_id=?",
        (user_id,),
    )
    exists = cursor.fetchone()

    if exists:
        # 既存のデータを更新（reminder_3days, reminder_7days は保持）
        cursor.execute(
            """UPDATE user_state 
               SET step=?, last_question=?, research_id=?, registration_time=?, reminder_3days=?, reminder_7days=?, reminder_14days=?, reminder_21days=?, before_the_last_day=?, after_use_ends=?
               WHERE user_id=?""",
            (
                step,
                last_question,
                research_id,
                registration_time,
                reminder_3days,
                reminder_7days,
                reminder_14days,
                reminder_21days,
                before_the_last_day,
                after_use_ends,
                user_id,
            ),
        )
    else:
        # 初回登録時のみリマインダーを設定
        cursor.execute(
            """INSERT INTO user_state (user_id, step, research_id, last_question, registration_time, reminder_3days, reminder_7days, reminder_14days, reminder_21days, before_the_last_day, after_use_ends)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                step,
                research_id,
                last_question,
                registration_time,
                reminder_3days,
                reminder_7days,
                reminder_14days,
                reminder_21days,
                before_the_last_day,
                after_use_ends,
            ),
        )

    conn.commit()
    conn.close()


async def reply(event, message):
    await line_bot_api.reply_message(
        ReplyMessageRequest(
            reply_token=event.reply_token, messages=[TextMessage(text=message)]
        )
    )


def generate_random_string(length):
    letters = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choice(letters) for _ in range(length))


# メッセージ送信関数
def send_confirm_message(user_id):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}",
    }
    data = {
        "to": user_id,  # 送信先のユーザーID
        "messages": [
            {
                "type": "template",
                "altText": "確認メッセージ",
                "template": {
                    "type": "confirm",
                    "text": "アンケートの回答は終了しましたか？",
                    "actions": [
                        {"type": "message", "label": "はい", "text": "はい"},
                        {"type": "message", "label": "いいえ", "text": "いいえ"},
                    ],
                },
            }
        ],
    }

    requests.post(url, headers=headers, data=json.dumps(data))


@app.post("/callback")
async def confirm_callback(request: Request):
    raw_body = await request.body()
    body = json.loads(raw_body)
    events = body.get("events", [])

    for event in events:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_id = event["source"]["userId"]
            user_message = event["message"]["text"]

            # 選択肢に応じて異なるメッセージを送信
            if user_message == "はい":
                await reply_text(
                    user_id,
                    "入力ありがとうございました。乳がんに関して知りたいこと（知りたかったこと）を入力してください。「がん情報サービス」「乳がん診療ガイドライン」から情報を提供します。",
                )
            elif user_message == "いいえ":
                await reply_text(user_id, "アンケートの回答をお願いします。")

    return {"status": "ok"}


# LINE に返信を送る関数
async def reply_text(user_id: str, message: str):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}",
    }
    data = {"to": user_id, "messages": [{"type": "text", "text": message}]}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)


# ローディングアニメーションを表示する関数
async def start_loading_animation(user_id: str, loading_seconds: int = 5):
    url = "https://api.line.me/v2/bot/chat/loading/start"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {channel_access_token}",
    }
    data = {
        "chatId": user_id,  # ユーザーの ID（event["source"]["userId"] で取得）
        "loadingSeconds": loading_seconds,  # ローディングの秒数 (最大 10秒)
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
