from abc import ABC, abstractmethod
from typing import Any, List, Literal, Optional

from pydantic import BaseModel as _BaseModel
from pydantic import Field


class BaseModel(_BaseModel):
    class NotFound(Exception):
        pass


class User(BaseModel):
    id: int
    first_name: str
    last_name: str

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Chat(BaseModel):
    id: int
    title: str


class MessageSender(BaseModel):
    user_id: int


class Reaction(BaseModel):
    reaction: str
    total_count: int


class MessageInteractionInfo(BaseModel):
    view_count: int
    forward_count: int
    reactions: list[Reaction]


class TextEntity(BaseModel):
    offset: int
    length: int


class FormattedText(BaseModel):
    text: str
    entities: list[TextEntity]


class MessageContent(ABC):
    @property
    @abstractmethod
    def renderable_text(self):
        pass


class MessageText(BaseModel, MessageContent):
    tdlib_type: Literal["messageText"] = Field(..., alias="@type")
    text: FormattedText
    # web_page: str

    @property
    def renderable_text(self):
        return self.text.text


class Thumbnail(BaseModel):
    width: int
    height: int


class MiniThumbnail(BaseModel):
    width: int
    height: int
    data: bytes


class Sticker(BaseModel):
    set_id: int
    width: int
    height: int
    emoji: str
    thumbnail: Thumbnail


class MessageSticker(BaseModel, MessageContent):
    tdlib_type: Literal["messageSticker"] = Field(..., alias="@type")
    sticker: Sticker
    is_premium: bool

    @property
    def renderable_text(self):
        return self.sticker.emoji


class AnimatedEmoji(BaseModel):
    sticker: Sticker
    fitzpatrick_type: int


class MessageAnimatedEmoji(BaseModel, MessageContent):
    tdlib_type: Literal["messageAnimatedEmoji"] = Field(..., alias="@type")
    animated_emoji: AnimatedEmoji
    emoji: str

    @property
    def renderable_text(self):
        return self.emoji


class Document(BaseModel):
    file_name: str
    mime_type: str
    minithumbnail: MiniThumbnail
    # document: File


class MessageDocument(BaseModel, MessageContent):
    tdlib_type: Literal["messageDocument"] = Field(..., alias="@type")
    document: Document
    caption: FormattedText

    @property
    def renderable_text(self):
        return self.caption.text


class Sizes(BaseModel):
    type: str
    # photo: File
    width: int
    height: int
    progressive_sizes: List[int]


class Photo(BaseModel):
    minithumbnail: MiniThumbnail
    sizes: List[Sizes]


class MessagePhoto(BaseModel, MessageContent):
    tdlib_type: Literal["messagePhoto"] = Field(..., alias="@type")
    photo: Photo
    caption: FormattedText

    @property
    def renderable_text(self):
        return self.caption.text


class Message(BaseModel):
    id: int
    sender_id: MessageSender
    is_outgoing: bool
    is_pinned: bool
    can_be_edited: bool
    can_be_forwarded: bool
    can_be_saved: bool
    can_be_deleted_only_for_self: bool
    can_be_deleted_for_all_users: bool
    can_get_statistics: bool
    can_get_message_thread: bool
    can_get_viewers: bool
    can_get_media_timestamp_links: bool
    has_timestamped_media: bool
    is_channel_post: bool
    contains_unread_mention: bool
    date: int
    edit_date: int
    interaction_info: Optional[MessageInteractionInfo]

    content: MessageText | MessageDocument | MessageSticker | MessageAnimatedEmoji | MessagePhoto = Field(
        ..., discriminator="tdlib_type"
    )

    @property
    def renderable_text(self):
        return f"{self.content.__class__.__name__}: {self.content.renderable_text}"
