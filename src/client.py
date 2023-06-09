import os
from typing import Any, Dict

from telegram.client import AuthorizationState, Telegram

from models import Chat, File, Message, User


class Client(Telegram):
    def __init__(self) -> None:
        super().__init__(
            api_id=int(os.getenv("TELEGRAM_API_ID", 0)),
            api_hash=os.getenv("TELEGRAM_API_HASH", ""),
            phone=os.getenv("TELEGRAM_PHONE", ""),
            database_encryption_key=os.getenv("TELEGRAM_DATABASE_ENCRYPTION_KEY", ""),
            device_model="project_telegram",
            application_version="1.0",
        )

    def login(self):
        state = super().login(blocking=False)

        if state == AuthorizationState.WAIT_CODE:
            code = input("Code: ")
            super().send_code(code)
            state = super().login(blocking=False)

        if state == AuthorizationState.WAIT_PASSWORD:
            password = input("Password: ")
            super().send_password(password)
            state = super().login(blocking=False)

    def download_file(self, file_id: int):
        r = super().call_method(
            "downloadFile",
            {
                "file_id": file_id,
                "priority": 32,
                "offset": 0,
                "limit": 0,
                "synchronous": True,
            },
            block=True,
        )
        if r.update is None:
            raise ValueError("No download response")
        result: Dict[Any, Any] = r.update
        return File(**result)

    def get_me(self):
        r = super().get_me()
        r.wait()
        if not r.update:
            return 0
        return r.update.get("id", 0)

    def get_user(self, user_id: int) -> User:
        r = super().get_user(user_id)
        r.wait()
        if not r.update:
            raise User.NotFound
        return User(**r.update)

    def get_chat(self, chat_id: int):
        r = super().get_chat(chat_id)
        r.wait()
        if not r.update:
            raise Chat.NotFound
        return Chat(**r.update)

    def get_chats(self):
        r = super().get_chats()
        r.wait()
        if not r.update:
            raise Chat.NotFound
        chat_ids = r.update.get("chat_ids", [])
        for chat_id in chat_ids:
            yield self.get_chat(chat_id)

    def get_chat_history(self, chat_id: int):
        r = super().get_chat_history(chat_id)
        r.wait()
        if not r.update:
            return []
        messages = r.update.get("messages", [])
        messages.reverse()
        return [Message(**m) for m in messages]

    def send_message(self, chat_id: int, text: str):
        r = super().send_message(chat_id, text)
        r.wait()
        if not r.update:
            return "no update"
        return r
