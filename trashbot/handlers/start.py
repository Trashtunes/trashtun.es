from telegram import Update


def start_callback(update, context):
    update.message.reply_text("Test Start")
