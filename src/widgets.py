from __future__ import annotations

import base64
import io
import subprocess
from typing import ClassVar, List

from PIL import Image
from rich.color import Color
from rich.color_triplet import ColorTriplet
from rich.console import RenderableType
from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container
from textual.message import Message as _Message
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Input, Label, ListItem, ListView, Static, TextLog

from client import Client
from models import HasDownloadableImage, HasImage, Message


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
                    chat.id,
                    Label(chat.title),
                    id=f"chat_id__{chat.id}",
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
        Binding("enter", "select_item", "Select item", show=False),
        Binding("escape", "deselect_item", "Deselect item", show=False),
        Binding("k", "cursor_up", "Cursor Up", show=False),
        Binding("j", "cursor_down", "Cursor Down", show=False),
        Binding("h", "select_left", "Cursor Left", show=False),
        Binding("l", "select_right", "Show details", show=True),
        Binding("i", "enter_input_mode", "Enter input mode", show=True),
    ]

    class Highlighted(_Message, bubble=True):
        def __init__(self, list_view: MessageListView, item: MessageItem) -> None:
            super().__init__()
            self.list_view = list_view
            self.item: MessageItem = item

    class Selected(_Message, bubble=True):
        def __init__(self, list_view: MessageListView, item: MessageItem) -> None:
            super().__init__()
            self.list_view = list_view
            self.item: MessageItem = item

    def __init__(self, tg: Client, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tg = tg
        self.messages_ids = set()

    @property
    def highlighted_child(self) -> MessageItem | None:
        if self.index is not None and 0 <= self.index < len(self._nodes):
            list_item = self._nodes[self.index]
            assert isinstance(list_item, MessageItem)
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

    def action_select_item(self) -> None:
        item = self.highlighted_child
        if item is not None:
            item.action_select_item()

    def action_deselect_item(self) -> None:
        item = self.highlighted_child
        if item is not None:
            item.action_deselect_item()

    async def load_messages(self, chat_id: int):
        me = self.tg.get_me()
        messages = self.tg.get_chat_history(chat_id)
        message_ids = set(m.id for m in messages)
        if self.messages_ids == message_ids:
            return
        self.messages_ids = message_ids
        self.clear()

        await self.mount_all(MessageItem(self.tg, m, me) for m in messages)
        self.index = len(self.children)

    def on_mount(self) -> None:
        r = super().on_mount()
        self.scroll_end(animate=False)
        return r


class MessageItem(ListItem):
    def __init__(self, tg: Client, msg: Message, me: int, *args, **kwargs) -> None:
        self.tg = tg
        self.me = me
        self.msg = msg
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        msg_text = self.msg.renderable_text

        if isinstance(self.msg.content, HasImage) and self.msg.content.image_data:
            s = ImagePreview(self.msg.content.image_data, classes="content")
        else:
            s = Static(msg_text, classes="content")

        author_id = self.msg.sender_id.user_id
        is_author_me = author_id == self.me
        if is_author_me:
            self.add_class("author-me")
        author = self.tg.get_user(author_id)

        s.border_title = author.full_name

        if self.msg.interaction_info:
            reactions = self.msg.interaction_info.reactions
            sub = ""
            for r in reactions:
                sub += r.reaction
                c = r.total_count
                if c > 1:
                    sub += f": {c}"
                sub += " "
            s.border_subtitle = sub.strip()
        yield s

    def action_select_item(self):
        if isinstance(self.msg.content, HasDownloadableImage):
            file = self.tg.download_file(self.msg.content.downloadable_image_id)
            subprocess.Popen(["kitten", "icat", file.local.path])

    def action_deselect_item(self):
        if isinstance(self.msg.content, HasImage):
            subprocess.Popen(["kitten", "icat", "--clear"])
            self.app.refresh()


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
        title = self.tg.get_chat(chat_id).title
        self.header.update(title)


class ImagePreview(Widget):
    def __init__(self, data: bytes, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        data = base64.decodebytes(data)
        image = Image.open(io.BytesIO(data)).convert("RGB")

        self.width = 32
        self.height = int(image.height / (image.width / self.width)) // 2

        self.image = image.resize((self.width, self.height))

        self.styles.width = self.width
        self.styles.height = self.height

    def render_line(self, y: int) -> Strip:
        full_block = "█"
        return Strip(
            Segment(
                full_block,
                Style(
                    color=Color.from_triplet(ColorTriplet(*self.image.getpixel((x, y))))
                ),
            )
            for x in range(self.width)
        )
