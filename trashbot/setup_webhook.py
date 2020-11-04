from telegram import Bot

from app import token, url

bot = Bot(token)

result = bot.set_webhook(url)

print(result)

print(bot.get_webhook_info())
