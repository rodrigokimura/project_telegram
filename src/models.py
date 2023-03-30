from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Literal, Optional, Union

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


class HasImage(ABC):
    has_image: bool = True

    @property
    @abstractmethod
    def image_data(self) -> Optional[bytes]:
        pass


class HasDownloadableImage(ABC):
    has_downloadable_image: bool = True

    @property
    @abstractmethod
    def downloadable_image_id(self) -> int:
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


class MessageContactRegistered(BaseModel, MessageContent):
    tdlib_type: Literal["messageContactRegistered"] = Field(..., alias="@type")

    @property
    def renderable_text(self):
        return "Contact registered."


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


class LocalFile(BaseModel):
    path: str


class File(BaseModel):
    id: int
    size: int
    expected_size: int
    local: LocalFile


class Document(BaseModel):
    file_name: str
    mime_type: str
    minithumbnail: Optional[MiniThumbnail]
    thumbnail: Optional[Thumbnail]
    document: File


class MessageDocument(BaseModel, MessageContent, HasImage):
    tdlib_type: Literal["messageDocument"] = Field(..., alias="@type")
    document: Document
    caption: FormattedText

    @property
    def renderable_text(self):
        return self.caption.text

    @property
    def image_data(self) -> Optional[bytes]:
        return self.document.minithumbnail.data if self.document.minithumbnail else None


class Sizes(BaseModel):
    type: str
    photo: File
    width: int
    height: int
    progressive_sizes: List[int]


class Photo(BaseModel):
    minithumbnail: Optional[MiniThumbnail]
    sizes: List[Sizes]


class MessagePhoto(BaseModel, MessageContent, HasImage, HasDownloadableImage):
    tdlib_type: Literal["messagePhoto"] = Field(..., alias="@type")
    photo: Photo
    caption: FormattedText

    @property
    def renderable_text(self):
        return "Photo"

    @property
    def image_data(self) -> Optional[bytes]:
        return self.photo.minithumbnail.data if self.photo.minithumbnail else None

    @property
    def downloadable_image_id(self) -> int:
        return self.photo.sizes[-1].photo.id


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
    date: datetime
    edit_date: int
    interaction_info: Optional[MessageInteractionInfo]

    content: Union[
        MessageText,
        MessageDocument,
        MessageSticker,
        MessageAnimatedEmoji,
        MessagePhoto,
        MessageContactRegistered,
    ] = Field(..., discriminator="tdlib_type")

    @property
    def renderable_text(self):
        if isinstance(self.content, MessagePhoto):
            return self.content.renderable_text
        return f"{self.content.__class__.__name__}: {self.content.renderable_text}"
