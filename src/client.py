import os
from typing import Dict, Optional, Union

from telegram.client import AuthorizationState, Telegram


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
