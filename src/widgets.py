from __future__ import annotations

from typing import ClassVar, List

from rich.console import RenderableType
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.message import Message as _Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Header, Input, Label, ListItem, ListView, Static, TextLog

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
        Binding("l", "select_right", "Cursor Right", show=False),
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

    @property
    def highlighted_child(self) -> ChatListItem | None:
        if self.index is not None and 0 <= self.index < len(self._nodes):
            list_item = self._nodes[self.index]
            assert isinstance(list_item, ChatListItem)
            return list_item

    async def action_select_right(self):
        self.collapse()
        main_pane = self.app.query_one(MainPane)
        main_pane.chat_pane.focus()

    def collapse(self):
        self.display = False

    def expand(self):
        self.display = True

    def _on_focus(self, event: events.Focus) -> None:
        r = super()._on_focus(event)
        self.expand()
        return r

    def _on_blur(self, event: events.Blur) -> None:
        r = super()._on_blur(event)
        self.collapse()
        return r


class ChatHeader(Label):
    def update(self, renderable: RenderableType = "") -> None:
        return super().update(renderable)


class MessageListView(ListView):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("enter", "select_cursor", "Select", show=False),
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
        Binding("h", "select_left", "Cursor Left", show=False),
        Binding("l", "select_right", "Show details", show=True),
        Binding("i", "enter_input_mode", "Enter input mode", show=True),
    ]

    class Highlighted(_Message, bubble=True):
        def __init__(self, list_view: MessageListView, item: Message) -> None:
            super().__init__()
            self.list_view = list_view
            self.item: Message = item

    class Selected(_Message, bubble=True):
        def __init__(self, list_view: MessageListView, item: Message) -> None:
            super().__init__()
            self.list_view = list_view
            self.item: Message = item

    def __init__(self, tg: Client, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg
        self.messages_ids = set()

    @property
    def highlighted_child(self) -> Message | None:
        if self.index is not None and 0 <= self.index < len(self._nodes):
            list_item = self._nodes[self.index]
            assert isinstance(list_item, Message)
            return list_item

    def action_select_left(self):
        self.app.query_one(ChatListView).focus()

    def action_enter_input_mode(self):
        self.app.query_one(MessageInput).focus()

    def action_select_right(self):
        details_pane = self.app.query_one(DetailsPane)
        details_pane.clear()
        item = self.highlighted_child
        if item is not None:
            details_pane.write(item.msg)
        details_pane.focus()

    async def load_messages(self, chat_id: int):
        me = self.tg.get_me()
        r = self.tg.get_chat_history(chat_id)
        message_ids = set(m.get("id", 0) for m in r)
        if self.messages_ids == message_ids:
            return
        self.messages_ids = message_ids
        self.clear()

        await self.mount_all(Message(self.tg, m, me) for m in r)
        self.index = len(self.children)

    def on_mount(self) -> None:
        r = super().on_mount()
        self.scroll_end(animate=False)
        return r


class Message(ListItem):
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

        reactions = self.msg.get("interaction_info", {}).get("reactions", [])
        sub = ""
        for r in reactions:
            sub += r.get("reaction", "")
            c = r.get("total_count", 1)
            if c > 1:
                sub += f": {c}"
            sub += " "
        s.border_subtitle = sub.strip()
        yield s


class MessageInput(Input):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "leave_input_mode", "Leave input mode", show=True),
    ]

    class Submitted(_Message, bubble=True):
        def __init__(self, input: Input, value: str) -> None:
            super().__init__()
            self.input: Input = input
            self.value: str = value

    def action_leave_input_mode(self):
        self.app.query_one(MessageListView).focus()

    async def action_submit(self) -> None:
        self.post_message(self.Submitted(self, self.value))
        self.app.bell()
        self.value = ""


class DetailsPane(TextLog):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("h", "select_left", "Leave", show=True),
        Binding("escape", "select_left", "Leave", show=True),
    ]

    def hide(self):
        self.display = False

    def show(self):
        self.display = True

    def _on_focus(self, event: events.Focus) -> None:
        r = super()._on_focus(event)
        self.show()
        return r

    def _on_blur(self, event: events.Blur) -> None:
        r = super()._on_blur(event)
        self.hide()
        return r

    def action_select_left(self):
        self.app.query_one(MessageListView).focus()


class MainPane(Container):
    def __init__(self, tg: Client, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg

    def compose(self) -> ComposeResult:
        self.header = ChatHeader("No chat selected")
        self.chat_pane = MessageListView(id="chat-pane", tg=self.tg)
        self.message_input = MessageInput()
        yield self.header
        yield self.chat_pane
        yield self.message_input

    async def load_messages(self, chat_id: int):
        await self.chat_pane.load_messages(chat_id)
        self.message_input.value = ""
        title = self.tg.get_chat(chat_id).get("title", "")
        self.header.update(title)
