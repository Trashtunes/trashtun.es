import json
import os

from handlers.start import start_callback
from handlers.track import track_callback
from telegram import Bot, Update
from telegram.ext import CommandHandler, Dispatcher

token = ""
url = ""

bot = Bot(token)

dispatcher = Dispatcher(bot, None, use_context=True)
dispatcher.add_handler(CommandHandler("start", start_callback))
dispatcher.add_handler(CommandHandler("track", track_callback))


def lambda_handler(event, context):
    try:
        dispatcher.process_update(Update.de_json(json.loads(event["body"]), bot))

    except Exception as e:
        print(e)
        return {"statusCode": 500}

    return {"statusCode": 200}
