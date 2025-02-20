"""
参考にしたプログラムは以下
https://github.com/line/line-bot-sdk-python/tree/master/examples/fastapi-echo
"""

import os
import csv
import sys
from dotenv import load_dotenv
import random
import string

import pandas as pd
from datetime import datetime, timezone, timedelta
from fastapi import Request, FastAPI, HTTPException
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from src.find_answer import find_answer, find_option

load_dotenv()

channel_secret = os.getenv("LINE_CHANNEL_SECRET", None)
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)
if channel_secret is None:
    print("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)

configuration = Configuration(access_token=channel_access_token)

app = FastAPI()
async_api_client = AsyncApiClient(configuration)
line_bot_api = AsyncMessagingApi(async_api_client)
parser = WebhookParser(channel_secret)


def save_chat(
    user_id,
    messege_id,
    user_message,
    response_id,
    timestamp,
    reply_id,
    version,
    file_name="./data/outputs/line_chat_history.csv",
):
    # CSVファイルが存在しない場合は、ヘッダーを含む新しいファイルを作成
    if not os.path.exists(file_name):
        with open(file_name, "w", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "user_id",
                    "messege_id",
                    "user_message",
                    "response_id",
                    "timestamp",
                    "reply_id",
                    "version",
                ]
            )

    # CSVファイルにデータを追記
    with open(file_name, "a", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                user_id,
                messege_id,
                user_message,
                response_id,
                timestamp,
                reply_id,
                version,
            ]
        )


def generate_random_string(length):
    letters = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choice(letters) for _ in range(length))


last_chat = {
    "user_id": "",
    "messege_id": "",
    "user_message": "",
    "response_id": "",
    "timestamp": "",
    "reply_id": "",
}


@app.post("/callback")
async def handle_callback(request: Request):
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = await request.body()
    body = body.decode()

    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessageContent):
            continue
        answer, option, again_user_choice, index = find_option(event.message.text)

        last_chat["user_id"] = event.source.user_id
        last_chat["messege_id"] = event.message.id
        last_chat["user_message"] = event.message.text
        last_chat["response_id"] = index

        utc_timestamp = event.timestamp
        utc_dt = datetime.utcfromtimestamp(
            utc_timestamp / 1000
        )  # UTCのタイムスタンプをミリ秒から秒に変換してから変換
        jst_timezone = timezone(
            timedelta(hours=9)
        )  # 日本時間のタイムゾーンオブジェクトを作成
        jst_dt = utc_dt.replace(tzinfo=timezone.utc).astimezone(
            jst_timezone
        )  # UTCを日本時間に変換
        last_chat["timestamp"] = jst_dt

        if option != "" or option is None:
            quick_reply_items = []
            for opt, choice in zip(option, again_user_choice):
                quick_reply_items.append(
                    QuickReplyItem(action=MessageAction(label=opt, text=choice))
                )
            quick_reply = QuickReply(items=quick_reply_items)
            replymessease = await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=answer[0], quick_reply=quick_reply)],
                )
            )  # レスポンスからメッセージIDを取得
            # message_id = replymessease.message.id
            # print("replymessage_id", message_id)
            last_chat["user_message"] = event.message.text
            last_chat["response_id"] = index
            last_chat["reply_id"] = generate_random_string(10)
            save_chat(
                last_chat["user_id"],
                last_chat["messege_id"],
                last_chat["user_message"],
                last_chat["response_id"],
                last_chat["timestamp"],
                last_chat["reply_id"],
                version="sample",
            )
        else:
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=ans) for ans in answer],
                )
            )
            last_chat["user_message"] = event.message.text
            last_chat["response_id"] = index
            save_chat(
                last_chat["user_id"],
                last_chat["messege_id"],
                last_chat["user_message"],
                last_chat["response_id"],
                last_chat["timestamp"],
                last_chat["reply_id"],
                version="sample",
            )
            last_chat["reply_id"] = ""

    return "OK"
