from typing import Type

from dotenv import load_dotenv
from textual import log
from textual.app import App, ComposeResult, CSSPathType
from textual.containers import Container, Horizontal, VerticalScroll
from textual.driver import Driver
from textual.message import Message as _Message
from textual.widgets import Footer, Header, Static

from client import Client
from utils import notify


class ChatListPane(VerticalScroll):
    def __init__(self, tg: Client, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg

    def compose(self) -> ComposeResult:
        for chat in self.tg.get_chats():
            yield ChatListItem(self.tg, chat.get("id"), chat.get("title"))


class ChatListItem(Static):
    class Selected(_Message):
        def __init__(self, chat_id: int) -> None:
            self.chat_id = chat_id
            super().__init__()

    def __init__(self, tg: Client, chat_id: int, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg
        self.chat_id = chat_id

    def on_click(self):
        notify("Loading chat", f"chat id: {self.chat_id}")
        self.post_message(self.Selected(self.chat_id))


class ChatPane(VerticalScroll):
    def __init__(self, tg: Client, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg


class Message(Static):
    pass


class MainPane(Container):
    def __init__(self, tg: Client, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg

    def compose(self) -> ComposeResult:
        yield ChatPane(id="chat-pane", tg=self.tg)


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

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Horizontal(id="app-grid"):
            yield ChatListPane(id="chats-pane", tg=self.tg)
            yield MainPane(id="main-pane", tg=self.tg)
        yield Footer()

    def on_chat_list_item_selected(self, message: ChatListItem.Selected):
        self.query(Message).remove()
        chat_pane = self.query_one(ChatPane)
        r = self.tg.get_chat_history(message.chat_id)
        for m in r:
            chat_pane.mount(
                Message(m.get("content", {}).get("text", {}).get("text", ""))
            )

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
