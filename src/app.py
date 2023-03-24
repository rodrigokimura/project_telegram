from typing import Type

from dotenv import load_dotenv
from textual import log
from textual.app import App, ComposeResult, CSSPathType
from textual.containers import Horizontal
from textual.driver import Driver
from textual.widgets import Footer, Header

from client import Client
from utils import notify
from widgets import ChatListView, ChatPane, MainPane


class TelegramClient(App):
    CSS_PATH = "main.css"
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
        self.current_chat_id = 0
        self.me = self.tg.get_me()

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Horizontal(id="app-grid"):
            yield ChatListView(self.tg, id="chat-list-pane")
            yield MainPane(id="main-pane", tg=self.tg)
        yield Footer()

    def on_chat_list_view_selected(self, message: ChatListView.Selected):
        chat_pane = self.query_one(ChatPane)
        chat_pane.load_messages(message.item.chat_id, self.me)

    def action_toggledark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def new_message_handler(self, update):
        log(update.get("message"))
        message_content = update["message"]["content"].get("text", {})
        user_id = update["message"]["sender_id"].get("user_id", 0)
        r = self.tg.get_user(user_id)
        name = f"{r.get('first_name')} {r.get('last_name')}"
        message_text = message_content.get("text", "")
        notify(f"From: {name}", message_text)


if __name__ == "__main__":
    load_dotenv()
    app = TelegramClient()
    app.run()
