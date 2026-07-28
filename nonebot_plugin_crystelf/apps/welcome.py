import asyncio
import time

import httpx
from nonebot import on_notice, on_regex
from nonebot.adapters.onebot.v11 import Bot, GroupIncreaseNoticeEvent, GroupMessageEvent, Message, MessageSegment
from nonebot.log import logger
from nonebot.plugin import get_plugin_config

from .. import data_store
from ..config import Config
from ..utils import can_manage

welcome_notice = on_notice(priority=10, block=False)

set_welcome_cmd = on_regex(r"^#设置欢迎(文案|图片)([\s\S]*)?$", priority=10, block=True)
view_welcome_cmd = on_regex(r"^#查看欢迎$", priority=10, block=True)
clear_welcome_cmd = on_regex(r"^#清除欢迎$", priority=10, block=True)

# 每群 30 秒欢迎冷却，对应原项目 redis Yz:newcomers:{groupId}
_welcome_cd: dict[int, float] = {}
WELCOME_CD_SECONDS = 30


def build_welcome_message(group_id: int, user_id: int) -> Message:
    """构建入群欢迎消息，与原项目 welcome.js 逻辑一致"""
    welcome_cfg = data_store.get_newcomer_config().get(str(group_id), {})
    msg = Message(MessageSegment.at(user_id))
    if welcome_cfg.get("text"):
        msg += MessageSegment.text(welcome_cfg["text"])
    if welcome_cfg.get("image"):
        msg += MessageSegment.image(welcome_cfg["image"])
    if not welcome_cfg.get("text") and not welcome_cfg.get("image"):
        msg += MessageSegment.text("欢迎新人~！")
    return msg


@welcome_notice.handle()
async def handle_newcomer(bot: Bot, event: GroupIncreaseNoticeEvent):
    if not get_plugin_config(Config).crystelf_welcome:
        return
    try:
        await asyncio.sleep(0.6)
        if event.user_id == int(event.self_id):
            return
        group_id = event.group_id
        now = time.time()
        if now - _welcome_cd.get(group_id, 0) < WELCOME_CD_SECONDS:
            return
        _welcome_cd[group_id] = now

        msg = build_welcome_message(group_id, event.user_id)

        group_auth_cfg = data_store.get_group_auth_cfg(group_id)
        if group_auth_cfg.get("enable"):
            # 开启验证的群：缓存欢迎消息，验证通过后再发送
            data_store.cache_welcome(group_id, event.user_id, msg)
            return
        await welcome_notice.send(msg)
    except Exception as e:
        logger.error(f"[crystelf] 加群欢迎出现错误: {e}")
        await welcome_notice.send("加群欢迎出现错误，请重新设置加群欢迎")


async def _get_image_url(bot: Bot, event: GroupMessageEvent) -> str | None:
    """获取命令附带或引用消息中的图片，对应原项目 YunzaiUtils.getImages"""
    reply = getattr(event, "reply", None)
    if reply:
        for seg in reply.message:
            if seg.type == "image":
                return seg.data.get("url")
    for seg in event.message:
        if seg.type == "image":
            return seg.data.get("url")
    # 与原项目一致：没有图片时退回到发送者头像
    return f"https://q1.qlogo.cn/g?b=qq&s=640&nk={event.user_id}"


@set_welcome_cmd.handle()
async def handle_set_welcome(bot: Bot, event: GroupMessageEvent):
    if not can_manage(event):
        await set_welcome_cmd.finish("只有群主或管理员可以设置欢迎消息哦~")
    group_id = event.group_id
    raw = event.raw_message
    # 与原项目一致：整句包含「文案」则为设置文案，否则为设置图片
    welcome_type = "text" if "文案" in raw else "image"
    all_cfg = data_store.get_newcomer_config()
    cfg = all_cfg.get(str(group_id), {})

    if welcome_type == "text":
        import re

        text = re.sub(r"^#设置欢迎文案", "", raw).strip()
        if not text:
            await set_welcome_cmd.finish("请在命令后输入欢迎文案..")
        cfg["text"] = text
        all_cfg[str(group_id)] = cfg
        data_store.save_newcomer_config(all_cfg)
        await set_welcome_cmd.finish(f"欢迎文案设置成功：\n{text}..")

    # 图片
    img_url = await _get_image_url(bot, event)
    if not img_url:
        await set_welcome_cmd.finish("未检测到图片..")

    group_dir = data_store.newcomer_dir(group_id)
    try:
        for old in group_dir.glob("1.*"):
            old.unlink()
        async with httpx.AsyncClient() as client:
            resp = await client.get(img_url, timeout=30)
            resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        ext = "gif" if "gif" in content_type else "jpg"
        full_path = group_dir / f"1.{ext}"
        full_path.write_bytes(resp.content)
        cfg["image"] = str(full_path)
        all_cfg[str(group_id)] = cfg
        data_store.save_newcomer_config(all_cfg)
        await set_welcome_cmd.finish("欢迎图片设置成功..")
    except Exception as e:
        logger.error(f"[crystelf] 设置欢迎图片出错: {e}")
        await set_welcome_cmd.finish("保存图片时出错了..")


@view_welcome_cmd.handle()
async def handle_view_welcome(event: GroupMessageEvent):
    cfg = data_store.get_newcomer_config().get(str(event.group_id))
    if not cfg:
        await view_welcome_cmd.finish("该群尚未设置欢迎内容..")
    msg = Message(MessageSegment.text("当前欢迎: "))
    if cfg.get("text"):
        msg += MessageSegment.text(cfg["text"])
    if cfg.get("image"):
        msg += MessageSegment.image(cfg["image"])
    await view_welcome_cmd.finish(msg)


@clear_welcome_cmd.handle()
async def handle_clear_welcome(event: GroupMessageEvent):
    if not can_manage(event):
        await clear_welcome_cmd.finish("只有群主或管理员可以设置欢迎消息哦~")
    group_id = event.group_id
    all_cfg = data_store.get_newcomer_config()
    if str(group_id) not in all_cfg:
        await clear_welcome_cmd.finish("该群没有设置欢迎消息..")
    del all_cfg[str(group_id)]
    data_store.save_newcomer_config(all_cfg)
    await clear_welcome_cmd.finish(f"已清除群{group_id}的欢迎设置..")
