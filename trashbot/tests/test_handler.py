import datetime
import json
from unittest.mock import MagicMock

import pytest
from telegram import Bot, Chat, Message, Update, User

from trashbot.handlers.start import start_callback
from trashbot.handlers.track import track_callback


def mock_bot():
    bot = Bot("2310068804:AAFH3RcNVQ1HvuLDu9WUTKkZaZKgbiVBXN0")
    bot.send_message = MagicMock()
    return bot


def mock_chat():
    return Chat(id=1, type="private")


def mock_user():
    return User(id="1", first_name="Boggy", is_bot=False)

def message(text):
    return Message(
        bot=mock_bot(),
        id=1,
        chat=mock_chat(),
        date=datetime.datetime.now(),
        from_user=mock_user(),
        message_id="1",
        text=text,
    )

