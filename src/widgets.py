from __future__ import annotations

from typing import ClassVar, List

from textual import log
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, VerticalScroll
from textual.message import Message as _Message
from textual.widgets import Input, Label, ListItem, ListView, Static

from client import Client


class ChatListItem(ListItem):
    def __init__(self, tg: Client, chat_id: int, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg
        self.chat_id = chat_id


class ChatListView(ListView):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select_cursor", "Select", show=False),
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
    ]

    class Highlighted(_Message, bubble=True):
        def __init__(self, list_view: ChatListView, item: ChatListItem | None) -> None:
            super().__init__()
            self.list_view = list_view
            self.item: ChatListItem | None = item

    class Selected(_Message, bubble=True):
        def __init__(self, list_view: ChatListView, item: ChatListItem) -> None:
            super().__init__()
            self.list_view = list_view
            self.item: ChatListItem = item

    def __init__(self, tg: Client, **kwargs) -> None:
        self.tg = tg

        items: List[ChatListItem] = []
        for chat in self.tg.get_chats():
            items.append(
                ChatListItem(
                    self.tg,
                    chat.get("id"),
                    Label(chat.get("title")),
                    id=f"chat_id__{chat.get('id')}",
                )
            )
        super().__init__(*items, **kwargs)


class ChatPane(VerticalScroll):
    def __init__(self, tg: Client, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg
        self.messages_ids = set()

    def load_messages(self, chat_id: int, me: int):
        r = self.tg.get_chat_history(chat_id)
        message_ids = set(m.get("id", 0) for m in r)
        if self.messages_ids == message_ids:
            return
        self.messages_ids = message_ids

        self.query(Message).remove()
        for m in r:
            log(m)
            self.mount(Message(self.tg, m, me))
        self.scroll_end(animate=False)
        # self.refresh()


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
