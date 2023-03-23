from typing import Type

from dotenv import load_dotenv
from textual import log
from textual.app import App, ComposeResult, CSSPathType
from textual.containers import Container
from textual.driver import Driver
from textual.widgets import Footer, Header

from client import Client
from utils import notify


class TelegramClient(App):
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(
        self,
        driver_class: Type[Driver] | None = None,
        css_path: CSSPathType | None = None,
        watch_css: bool = False,
    ):
        super().__init__(driver_class, css_path, watch_css)

        self.tg = Client()
        self.tg.login()
        self.tg.add_message_handler(self.new_message_handler)

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Footer()
        yield Container()

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def new_message_handler(self, update):
        log(update.get("message"))
        message_content = update["message"]["content"].get("text", {})
        user_id = update["message"]["sender_id"].get("user_id", 0)
        r = self.tg.get_user(user_id)
        r.wait()

        if not r.update:
            return

        name = f"{r.update.get('first_name')} {r.update.get('last_name')}"

        message_text = message_content.get("text", "")
        notify(f"From: {name}", message_text)


if __name__ == "__main__":
    load_dotenv()
    app = TelegramClient()
    app.run()
