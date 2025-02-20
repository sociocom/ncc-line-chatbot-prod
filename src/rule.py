import os
import sys
from fastapi import FastAPI, Request, HTTPException
from linebot.exceptions import InvalidSignatureError
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
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

from src.find_answer import find_option
from src.utils import (
    get_user_state,
    update_user_state,
    save_message_to_db,
    generate_random_string,
    reply,
    send_confirm_message,
    confirm_callback,
    start_loading_animation,
)
from src.send_reminders import check_reminders

# LINE API の認証情報
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

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

# 1分ごとにチェック
scheduler = BackgroundScheduler()
scheduler.add_job(check_reminders, "interval", minutes=1)
scheduler.start()


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
        user_id = event.source.user_id
        user_message = event.message.text.strip()

        step, research_id, last_question = get_user_state(user_id)

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

        # **ステップ 0: 初回メッセージ**
        # 導入文・研究IDの入力の依頼
        # if step == 0:
        #     messages = [
        #         "初めまして！私の名前はBRECOBOTです。お友達登録していただきありがとうございます。",
        #         "これから一か月間、あなたが知りたいことの答えを探すお手伝いをさせていただきます。",
        #         "ではさっそく、あなたの研究IDを教えてください。",
        #     ]
        #     await line_bot_api.reply_message(
        #         ReplyMessageRequest(
        #             reply_token=event.reply_token,
        #             messages=[TextMessage(text=message) for message in messages],
        #         )
        #     )
        #     update_user_state(user_id, 1, None, None, jst_dt)

        # 使用前アンケート回答への依頼
        if step == 1:
            message = f"""{user_message}さんですね。私に質問をする前に下記のURLにアクセスし、アンケートにお答えください。\nhttp:// …\n（回答の際に研究IDが必要です）
    """
            # await start_loading_animation(user_id)
            # await reply(event, message)
            await line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token, messages=[TextMessage(text=message)]
                )
            )
            send_confirm_message(user_id)
            update_user_state(user_id, 2, user_message, None, jst_dt)

        # 本入力の依頼
        if step == 2:
            # await confirm_callback(user_message)
            if user_message == "はい":
                message = "入力ありがとうございました。乳がんに関して知りたいこと（知りたかったこと）を入力してください。「がん情報サービス」「乳がん診療ガイドライン」から情報を提供します。"
                update_user_state(user_id, 3)
                await line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=message)],
                    )
                )
            else:
                message = f"""{research_id}さんですね。私に質問をする前に下記のURLにアクセスし、アンケートにお答えください。\nhttp:// …\n（回答の際に研究IDが必要です）
                        """
                await line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=message)],
                    )
                )
                # 使用前アンケート回答の確認
                send_confirm_message(user_id)
                update_user_state(user_id, 2)

        # 質問の回答
        if step >= 3 and step < 5:
            answer, option, again_user_choice, index = find_option(user_message)
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
                )
                reply_id = generate_random_string(10)
                again_user_choice = [reply_id] + again_user_choice
                again_user_choice = "\t".join(again_user_choice)
                update_user_state(user_id, step, None, again_user_choice)

            else:
                await line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=ans) for ans in answer],
                    )
                )
                if last_question:
                    last_question = last_question.split("\t")
                    reply_id = last_question[0]
                    again_user_choice = last_question[1:]
                    if user_message not in again_user_choice:
                        reply_id = ""
                    update_user_state(user_id, step)
                else:
                    reply_id = ""

            save_message_to_db(
                user_id,
                event.message.id,
                user_message,
                str(index),
                reply_id,
                jst_dt,
                version="sample",
            )

        if step == 5:
            if user_message == "はい":
                messages = [
                    "ご入力ありがとうございました。これにて私、BRECOBOTのご利用は終了とさせていただきます。インタビュー調査に参加してくださる方には、後ほど個別に研究者より連絡が参りますので、もうしばらくお待ちください。",
                    "ご意見などがございましたら、研究事務局までお気軽にご連絡ください。ncc-ganchatbot＠ml.res.ncc.go.jp",
                    "ご協力ありがとうございました。",
                ]
                await line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=m) for m in messages],
                    )
                )
                update_user_state(user_id, 10)
            else:
                messages = [
                    """本日で利用期間が終了です。ご利用ありがとうございました。最後に、下記のURLにアクセスし、アンケートにお答えください。\nhttp:// …\n（回答の際に研究IDが必要です）""",
                    "また、さらに詳しいご感想を聞かせていただきたく、インタビュー調査も予定しています。ご協力くださる方は、アンケートの最後の同意確認欄と、個人情報をご入力ください。",
                ]
                await line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text=message) for message in messages],
                    )
                )
                send_confirm_message(user_id)
