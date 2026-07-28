import asyncio
import random
import re
from typing import Any, Optional

import httpx
from nonebot import on_message, on_notice, on_regex
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupDecreaseNoticeEvent,
    GroupIncreaseNoticeEvent,
    GroupMessageEvent,
    Message,
    MessageSegment,
)
from nonebot.log import logger
from nonebot.plugin import get_plugin_config

from .. import data_store
from ..config import Config
from ..utils import can_manage, is_master

# 进行中的验证会话: {(group_id, user_id): session}
# session: {"type": "math"|"carbon", "answer": Any, "tries": int, "cfg": dict}
pending: dict[tuple[int, int], dict[str, Any]] = {}

# 答案监听，对应原项目 Bot.on('message.group')
answer_listener = on_message(priority=5, block=False)

# 加群 / 退群事件
increase_notice = on_notice(priority=10, block=False)
decrease_notice = on_notice(priority=10, block=False)

# 管理命令，对应原项目 auth.js
bypass_cmd = on_regex(r"^#绕过验证([\s\S]*)?$", priority=10, block=True)
revalidate_cmd = on_regex(r"^#重新验证([\s\S]*)?$", priority=10, block=True)

# 设置命令，对应原项目 auth-set.js
enable_cmd = on_regex(r"^#开启验证$", priority=10, block=True)
disable_cmd = on_regex(r"^#关闭验证$", priority=10, block=True)
switch_mode_cmd = on_regex(r"^#切换验证模式$", priority=10, block=True)
carbon_mode_cmd = on_regex(r"^#设置验证(提示|困难)模式(开启|关闭)$", priority=10, block=True)
frequency_cmd = on_regex(r"^#设置验证次数(\d+)$", priority=10, block=True)
recall_cmd = on_regex(r"^#设置撤回(开启|关闭)$", priority=10, block=True)


def _js_parse_int(text: str) -> Optional[int]:
    """模拟 JS parseInt：解析前导整数部分，失败返回 None"""
    m = re.match(r"^\s*([+-]?\d+)", text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _plain_text(event: GroupMessageEvent) -> str:
    return "".join(seg.data.get("text", "") for seg in event.message if seg.type == "text")


def _at_target(event: GroupMessageEvent) -> Optional[int]:
    for seg in event.message:
        if seg.type == "at":
            try:
                return int(seg.data["qq"])
            except (KeyError, ValueError):
                return None
    return None


async def _kick(bot: Bot, group_id: int, user_id: int) -> None:
    await bot.set_group_kick(group_id=group_id, user_id=user_id, reject_add_request=False)


async def _pass(bot: Bot, event: GroupMessageEvent, key: tuple[int, int]) -> None:
    """验证通过：发送缓存的欢迎消息或默认欢迎"""
    pending.pop(key, None)
    group_id, user_id = key
    cached = data_store.pop_welcome(group_id, user_id)
    if cached is not None:
        await answer_listener.send(cached)
    else:
        await answer_listener.send(Message(MessageSegment.at(user_id) + MessageSegment.text("验证通过,欢迎加入本群~")))


async def _fail_try(bot: Bot, event: GroupMessageEvent, key: tuple[int, int], session: dict) -> None:
    """回答错误：撤回 / 提示剩余次数 / 超次踢出，与原项目一致"""
    cfg = session["cfg"]
    if session["tries"] >= cfg["frequency"]:
        pending.pop(key, None)
        if cfg.get("recall"):
            await _try_delete(bot, event.message_id)
        await answer_listener.send(
            Message(MessageSegment.at(event.user_id) + MessageSegment.text("验证失败,你错太多次辣!"))
        )
        await _kick(bot, event.group_id, event.user_id)
        return
    if cfg.get("recall"):
        await _try_delete(bot, event.message_id)
    await answer_listener.send(
        Message(
            MessageSegment.at(event.user_id)
            + MessageSegment.text(f"回答错了呢,你还有{cfg['frequency'] - session['tries']}次机会,再试试看?")
        )
    )


async def _try_delete(bot: Bot, message_id: int) -> None:
    try:
        await bot.delete_msg(message_id=message_id)
    except Exception as e:
        logger.debug(f"[crystelf] 撤回消息失败: {e}")


@answer_listener.handle()
async def handle_answer(bot: Bot, event: GroupMessageEvent):
    key = (event.group_id, event.user_id)
    session = pending.get(key)
    if not session:
        return
    session["tries"] += 1

    if session["type"] == "math":
        num = _js_parse_int(_plain_text(event).strip())
        if num is not None and num == session["answer"]:
            await _pass(bot, event, key)
            return
        await _fail_try(bot, event, key, session)
        return

    if session["type"] == "carbon":
        msg_regions = [
            s.strip()
            for s in _plain_text(event).upper().replace("，", ",").split(",")
            if s.strip()
        ]
        right_regions = [str(r).upper() for r in session["answer"]]
        if session["cfg"]["carbon"]["hard-mode"]:
            correct = all(r in msg_regions for r in right_regions)
        else:
            correct = any(r in msg_regions for r in right_regions)
        if correct:
            await _pass(bot, event, key)
            return
        await _fail_try(bot, event, key, session)


@increase_notice.handle()
async def handle_increase(bot: Bot, event: GroupIncreaseNoticeEvent):
    if not get_plugin_config(Config).crystelf_auth:
        return
    if is_master(event.user_id) or event.user_id == int(event.self_id):
        return
    key = (event.group_id, event.user_id)
    if key in pending:
        return
    logger.info(f"[crystelf] 群[{event.group_id}]开始对用户[{event.user_id}]的加群验证")
    await start_auth(bot, event.group_id, event.user_id)


@decrease_notice.handle()
async def handle_decrease(bot: Bot, event: GroupDecreaseNoticeEvent):
    key = (event.group_id, event.user_id)
    if key in pending:
        pending.pop(key, None)
        data_store.pop_welcome(*key)
        logger.info(f"[crystelf] 用户 {event.user_id} 主动退群，验证流程结束..")
        await decrease_notice.send("害,怎么跑路了")


async def start_auth(bot: Bot, group_id: int, user_id: int) -> None:
    """发起验证，对应原项目 auth()"""
    group_cfg = data_store.get_group_auth_cfg(group_id)
    if not group_cfg.get("enable"):
        return
    key = (group_id, user_id)
    timeout = group_cfg["timeout"]

    if group_cfg["carbon"]["enable"]:
        try:
            url = f"{get_plugin_config(Config).crystelf_auth_url}/captcha/chiralCarbon/getChiralCarbonCaptcha"
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    url, json={"answer": True, "hint": group_cfg["carbon"]["hint"]}, timeout=30
                )
                resp.raise_for_status()
            captcha = resp.json().get("data", {}).get("data")
            if not captcha:
                await bot.send_group_msg(group_id=group_id, message="获取验证图失败，请稍后重试..")
                return
            base64_img = captcha["base64"]
            regions = captcha["regions"]
            pending[key] = {"type": "carbon", "answer": regions, "tries": 0, "cfg": group_cfg}
            if "base64," in base64_img:
                base64_img = base64_img.split("base64,", 1)[1]
            hard = group_cfg["carbon"]["hard-mode"]
            target = "全部含有手性碳的区域" if hard else "其中任意一块包含手性碳的区域"
            msg = Message(
                MessageSegment.at(user_id)
                + MessageSegment.image(f"base64://{base64_img}")
                + MessageSegment.text(
                    f"上图中有一块或多块区域含有手性碳原子\n"
                    f"为了加入本群,你需要在{timeout}秒内正确找出{target}\n"
                    f"回答的话,直接回复区域代号即可,多个区域用逗号隔开\n"
                    f"提示一下,本图共有{len(regions)}块手性碳区域噢.."
                )
            )
            await bot.send_group_msg(group_id=group_id, message=msg)
        except Exception as e:
            logger.error(f"[crystelf] 请求手性碳验证API失败: {e}")
            await bot.send_group_msg(group_id=group_id, message="手性碳api出现异常,已暂时切换至数字验证模式..")
            await number_auth(bot, key, group_cfg, group_id, user_id)
    else:
        await asyncio.sleep(0.5)
        await number_auth(bot, key, group_cfg, group_id, user_id)

    if key not in pending:
        return

    if timeout > 60:
        asyncio.create_task(_remind_later(bot, key, group_id, user_id, timeout - 60))
    asyncio.create_task(_timeout_later(bot, key, group_id, user_id, timeout))


async def number_auth(bot: Bot, key: tuple[int, int], group_cfg: dict, group_id: int, user_id: int) -> None:
    """数字验证逻辑，对应原项目 numberAuth()"""
    a = random.randint(0, 99)
    b = random.randint(0, 99)
    op = "+" if random.random() > 0.5 else "-"
    ans = a + b if op == "+" else a - b
    pending[key] = {"type": "math", "answer": ans, "tries": 0, "cfg": group_cfg}
    await bot.send_group_msg(
        group_id=group_id,
        message=Message(
            MessageSegment.at(user_id)
            + MessageSegment.text(f"请在{group_cfg['timeout']}秒内发送{a} {op} {b}的计算结果..")
        ),
    )


async def _remind_later(bot: Bot, key: tuple[int, int], group_id: int, user_id: int, delay: int) -> None:
    await asyncio.sleep(delay)
    if key in pending:
        await bot.send_group_msg(
            group_id=group_id,
            message=Message(MessageSegment.at(user_id) + MessageSegment.text("小朋友,你还有1分钟的时间完成验证噢~")),
        )


async def _timeout_later(bot: Bot, key: tuple[int, int], group_id: int, user_id: int, timeout: int) -> None:
    await asyncio.sleep(timeout)
    if key in pending:
        pending.pop(key, None)
        data_store.pop_welcome(*key)
        await bot.send_group_msg(
            group_id=group_id,
            message=Message(
                MessageSegment.at(user_id) + MessageSegment.text("小朋友,验证超时啦!请重新申请入群~")
            ),
        )
        await _kick(bot, group_id, user_id)


@bypass_cmd.handle()
async def handle_bypass(bot: Bot, event: GroupMessageEvent):
    if not can_manage(event):
        await bypass_cmd.finish("只有群主或管理员可以使用此命令..")
    target_id = _at_target(event)
    if target_id is None:
        await bypass_cmd.finish("你想绕过谁?")
    key = (event.group_id, target_id)
    pending.pop(key, None)
    cached = data_store.pop_welcome(event.group_id, target_id)
    if cached is not None:
        await bypass_cmd.finish(cached)
    await bypass_cmd.finish(Message(MessageSegment.at(target_id) + MessageSegment.text("欢迎加入本群~")))


@revalidate_cmd.handle()
async def handle_revalidate(bot: Bot, event: GroupMessageEvent):
    if not can_manage(event):
        await revalidate_cmd.finish("只有群主或管理员可以使用此命令..")
    target_id = _at_target(event)
    if target_id is None:
        await revalidate_cmd.finish("你要验证谁?")
    try:
        member = await bot.get_group_member_info(group_id=event.group_id, user_id=target_id)
    except Exception:
        await revalidate_cmd.finish("获取群成员信息失败..")
    if member.get("role") in ("owner", "admin"):
        await revalidate_cmd.finish("这对吗")
    key = (event.group_id, target_id)
    if key in pending:
        await revalidate_cmd.finish("这孩子已经在验证了..")
    await start_auth(bot, event.group_id, target_id)


@enable_cmd.handle()
async def handle_enable(bot: Bot, event: GroupMessageEvent):
    if not can_manage(event):
        await enable_cmd.finish("只有群主或管理员可以设置验证..")
    try:
        bot_member = await bot.get_group_member_info(group_id=event.group_id, user_id=int(event.self_id))
    except Exception:
        bot_member = {}
    if bot_member.get("role") not in ("admin", "owner"):
        nickname = get_plugin_config(Config).crystelf_nickname
        await enable_cmd.finish(f"{nickname}不是管理,没法帮你验证啦..")
    group_cfg = data_store.get_group_auth_cfg(event.group_id)
    group_cfg["enable"] = True
    data_store.save_group_auth_cfg(event.group_id, group_cfg)
    await enable_cmd.finish("本群已开启入群验证,验证模式为数字验证..")


@disable_cmd.handle()
async def handle_disable(event: GroupMessageEvent):
    if not can_manage(event):
        await disable_cmd.finish("只有群主或管理员可以设置验证..")
    group_cfg = data_store.get_group_auth_cfg(event.group_id)
    group_cfg["enable"] = False
    data_store.save_group_auth_cfg(event.group_id, group_cfg)
    await disable_cmd.finish("已关闭本群新人验证..")


@switch_mode_cmd.handle()
async def handle_switch_mode(event: GroupMessageEvent):
    if not can_manage(event):
        await switch_mode_cmd.finish("只有群主或管理员可以设置验证..")
    group_cfg = data_store.get_group_auth_cfg(event.group_id)
    group_cfg["carbon"]["enable"] = not group_cfg["carbon"]["enable"]
    data_store.save_group_auth_cfg(event.group_id, group_cfg)
    await switch_mode_cmd.finish("已切换为手性碳验证模式.." if group_cfg["carbon"]["enable"] else "已切换为数字验证模式..")


@carbon_mode_cmd.handle()
async def handle_carbon_mode(event: GroupMessageEvent):
    if not can_manage(event):
        await carbon_mode_cmd.finish("只有群主或管理员可以设置验证..")
    m = re.match(r"^#设置验证(提示|困难)模式(开启|关闭)$", event.raw_message)
    mode_type, state = m.group(1), m.group(2) == "开启"
    group_cfg = data_store.get_group_auth_cfg(event.group_id)
    if mode_type == "提示":
        group_cfg["carbon"]["hint"] = state
    if mode_type == "困难":
        group_cfg["carbon"]["hard-mode"] = state
    data_store.save_group_auth_cfg(event.group_id, group_cfg)
    await carbon_mode_cmd.finish(f"已{'开启' if state else '关闭'}手性碳{mode_type}模式..")


@frequency_cmd.handle()
async def handle_frequency(event: GroupMessageEvent):
    if not can_manage(event):
        await frequency_cmd.finish("只有群主或管理员可以设置验证..")
    m = re.match(r"^#设置验证次数(\d+)$", event.raw_message)
    num = int(m.group(1))
    group_cfg = data_store.get_group_auth_cfg(event.group_id)
    group_cfg["frequency"] = num
    data_store.save_group_auth_cfg(event.group_id, group_cfg)
    await frequency_cmd.finish(f"已将最大尝试次数设置为 {num}..")


@recall_cmd.handle()
async def handle_recall(event: GroupMessageEvent):
    if not can_manage(event):
        await recall_cmd.finish("只有群主或管理员可以设置验证..")
    m = re.match(r"^#设置撤回(开启|关闭)$", event.raw_message)
    state = m.group(1)
    group_cfg = data_store.get_group_auth_cfg(event.group_id)
    group_cfg["recall"] = state == "开启"
    data_store.save_group_auth_cfg(event.group_id, group_cfg)
    await recall_cmd.finish(f"已{state}错误回答自动撤回功能..")
