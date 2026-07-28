from nonebot import on_message, on_regex
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.plugin import get_plugin_config

from ..config import Config
from ..utils import emoji_like, extract_emojis

# 监听群消息中的表情并贴回应，对应原项目 face-reply.js
face_listener = on_message(priority=99, block=False)

# 主动回应表情，查看类型及 id，对应原项目 face-reply-message.js
face_reply_cmd = on_regex(r"^(#|/)?回应([\s\S]*)?$", priority=10, block=True)


def _extract_faces(event: GroupMessageEvent) -> list[dict]:
    """提取消息中的 QQ 表情与 emoji，对应原项目两个模块共用的提取逻辑"""
    faces: list[dict] = []
    for seg in event.message:
        if seg.type == "face":
            faces.append({"id": seg.data["id"], "type": "face1"})
        elif seg.type == "text":
            for emoji in extract_emojis(seg.data.get("text", "")):
                faces.append({"id": ord(emoji[0]), "type": "face2"})
    return faces


@face_listener.handle()
async def handle_face(bot: Bot, event: GroupMessageEvent):
    if not get_plugin_config(Config).crystelf_face_reply:
        return
    if not event.message_id or len(event.message) == 0:
        return
    for face in _extract_faces(event):
        await emoji_like(bot, event.message_id, face["id"])


@face_reply_cmd.handle()
async def handle_face_reply(bot: Bot, event: GroupMessageEvent):
    if not get_plugin_config(Config).crystelf_face_reply:
        return
    if not event.message_id or len(event.message) == 0:
        return
    for face in _extract_faces(event):
        await face_reply_cmd.send(f"类型: {face['type']},ID: {face['id']}")
        await emoji_like(bot, event.message_id, face["id"])
