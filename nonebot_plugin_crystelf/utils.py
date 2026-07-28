from typing import Union

import regex
from nonebot import get_driver
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.log import logger

# 与原项目 exEmojis 一致的正则（JS \p{...} -> Python regex 模块）
EMOJI_REGEX = regex.compile(
    r"(?:\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?(?:\u200D\p{Extended_Pictographic}(?:\uFE0F|\uFE0E)?)*"
    r"|\p{Emoji_Presentation}|\p{Emoji}\uFE0F)"
)


def extract_emojis(text: str) -> list[str]:
    """从文本中提取 emoji，对应原项目 exEmojis"""
    return EMOJI_REGEX.findall(text)


def is_master(user_id: Union[int, str]) -> bool:
    """是否为主人（NoneBot SUPERUSER），对应原项目 e.isMaster / cfg.masterQQ"""
    uid = str(user_id)
    return any(s == uid or s.endswith(f":{uid}") for s in get_driver().config.superusers)


def is_group_admin(event: GroupMessageEvent) -> bool:
    """是否为群主或管理员"""
    return event.sender.role in ("owner", "admin")


def can_manage(event: GroupMessageEvent) -> bool:
    """主人 / 群主 / 管理员，对应原项目 e.isMaster || role 检查"""
    return is_group_admin(event) or is_master(event.user_id)


async def emoji_like(bot: Bot, message_id: int, emoji_id: Union[int, str]) -> bool:
    """
    给消息贴表情回应（NapCat / Lagrange 扩展 API）。
    原项目默认走 NapCat 的 set_msg_emoji_like，失败时尝试 Lagrange 的 set_group_reaction。
    """
    try:
        await bot.call_api("set_msg_emoji_like", message_id=message_id, emoji_id=str(emoji_id), set=True)
        return True
    except Exception as e:
        logger.debug(f"[crystelf] set_msg_emoji_like 失败: {e}")
    return False


async def group_poke(bot: Bot, group_id: int, user_id: int) -> bool:
    """群戳一戳（NapCat / Lagrange 扩展 API）"""
    try:
        await bot.call_api("group_poke", group_id=group_id, user_id=user_id)
        return True
    except Exception as e:
        logger.warning(f"[crystelf] group_poke 失败: {e}")
        return False
