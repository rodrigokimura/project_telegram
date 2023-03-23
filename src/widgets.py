from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.message import Message as _Message
from textual.widgets import Input, Static

from client import Client
from utils import notify


class ChatListPane(VerticalScroll):
    def __init__(self, tg: Client, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg

    def compose(self) -> ComposeResult:
        for chat in self.tg.get_chats():
            yield ChatListItem(
                self.tg,
                chat.get("id"),
                chat.get("title"),
                id=f"chat_id__{chat.get('id')}",
            )


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

    def load_messages(self, chat_id: int, me: int):
        r = self.tg.get_chat_history(chat_id)
        for m in r:
            self.mount(Message(self.tg, m, me))
        # self.scroll_end(animate=False)


class Message(Static):
    def __init__(self, tg: Client, msg: dict, me: int, *args, **kwargs) -> None:
        self.tg = tg
        self.me = me
        self.msg = msg
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        msg_text = self.msg.get("content", {}).get("text", {}).get("text", "")
        s = Static(msg_text, classes="content")
        author_id = self.msg.get("sender_id", {}).get("user_id", 0)
        is_author_me = author_id == self.me
        if is_author_me:
            self.add_class("author-me")
        author = self.tg.get_user(author_id)
        s.border_title = f"{author.get('first_name')} {author.get('last_name')}"
        yield s


class MainPane(Container):
    def __init__(self, tg: Client, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg

    def compose(self) -> ComposeResult:
        yield ChatPane(id="chat-pane", tg=self.tg)
        yield Input()
