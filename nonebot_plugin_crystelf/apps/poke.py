import asyncio
import random

from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Bot, PokeNotifyEvent
from nonebot.log import logger
from nonebot.plugin import get_plugin_config

from .. import words
from ..config import Config
from ..utils import group_poke, is_master

poke_notice = on_notice(priority=10, block=False)


@poke_notice.handle()
async def handle_poke(bot: Bot, event: PokeNotifyEvent):
    cfg = get_plugin_config(Config)
    if not cfg.crystelf_poke:
        return
    if event.group_id is None:
        return

    operator_id = event.user_id
    target_id = event.target_id
    self_id = int(event.self_id)

    # 戳主人
    if is_master(target_id) and operator_id != target_id:
        if is_master(operator_id) or self_id == operator_id:
            return
        logger.info("[crystelf] 谁戳主人了..")
        msg = await poke_notice.send("小嘿子不许戳!")
        asyncio.create_task(_recall_later(bot, msg, 60))
        await asyncio.sleep(1)
        await group_poke(bot, event.group_id, operator_id)
        return

    # 主人戳别人，跟着戳
    if is_master(operator_id) and target_id != self_id:
        logger.info("[crystelf] 跟主人一起戳!")
        await group_poke(bot, event.group_id, target_id)
        return

    # 戳 bot
    if target_id == self_id:
        try:
            text = words.get_word("poke", "poke", cfg.crystelf_nickname)
            await poke_notice.send(text)
            if random.random() < cfg.crystelf_reply_poke:
                await asyncio.sleep(1)
                await group_poke(bot, event.group_id, operator_id)
        except Exception as e:
            logger.error(f"[crystelf] 戳一戳请求失败: {e}")
            msg = await poke_notice.send(f"戳一戳出错了!{cfg.crystelf_nickname}不知道该说啥好了..")
            asyncio.create_task(_recall_later(bot, msg, 60))


async def _recall_later(bot: Bot, msg, delay: int) -> None:
    """对应原项目 e.reply(..., { recallMsg: 60 })，延时撤回"""
    try:
        message_id = msg.get("message_id") if isinstance(msg, dict) else None
        if message_id is None:
            return
        await asyncio.sleep(delay)
        await bot.delete_msg(message_id=message_id)
    except Exception as e:
        logger.debug(f"[crystelf] 撤回消息失败: {e}")
