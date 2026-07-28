from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.log import logger
from nonebot.plugin import get_plugin_config

from .. import words
from ..config import Config
from ..utils import is_master

# 与原项目 zwa.js 一致的正则
night_cmd = on_regex(
    r"^(#|/)?晚上好$|^(#|/)?安$|^(#|/)?晚安$|^(#|/)?睡了$|^(#|/)?睡觉$|^(#|/)?睡咯$",
    priority=10,
    block=True,
)
morning_cmd = on_regex(
    r"^(#|/)?早$|^(#|/)?早安$|^(#|/)?起床(了)$|^(#|/)?早上好$|^(#|/)?早上好！$|^(#|/)?早！$|^(#|/)?早啊$",
    priority=10,
    block=True,
)


def _image_api() -> str:
    return get_plugin_config(Config).crystelf_image_api


def _nickname() -> str:
    return get_plugin_config(Config).crystelf_nickname


def _pick(word_list: list[str]) -> str:
    return words.pick_random(word_list)


@night_cmd.handle()
async def handle_night(event: MessageEvent):
    if not get_plugin_config(Config).crystelf_zwa:
        return
    import datetime

    hour = datetime.datetime.now().hour
    if (20 <= hour <= 23) or (0 <= hour <= 2):
        if is_master(event.user_id):
            await night_cmd.finish(Message(_pick(words.word2_list) + MessageSegment.image(_image_api())))
        else:
            try:
                text = words.get_word("MN-hello", "good-night", _nickname())
                await night_cmd.finish(Message(text + MessageSegment.image(_image_api())))
            except Exception as e:
                logger.error(f"[crystelf] 早晚安出现错误: {e}")
    elif 3 <= hour < 7:
        if is_master(event.user_id):
            await night_cmd.finish(_pick(words.word7_list) + MessageSegment.image(_image_api()))
        else:
            await night_cmd.finish(_pick(words.word8_list))
    else:
        await night_cmd.finish(_pick(words.word9_list))


@morning_cmd.handle()
async def handle_morning(event: MessageEvent):
    if not get_plugin_config(Config).crystelf_zwa:
        return
    import datetime

    hour = datetime.datetime.now().hour
    if 0 <= hour <= 4:
        await morning_cmd.finish(_pick(words.word4_list))
    elif 5 <= hour <= 11:
        if is_master(event.user_id):
            await morning_cmd.finish(Message(_pick(words.word3_list) + MessageSegment.image(_image_api())))
        else:
            try:
                text = words.get_word("MN-hello", "good-morning", _nickname())
                await morning_cmd.finish(Message(text + MessageSegment.image(_image_api())))
            except Exception as e:
                logger.error(f"[crystelf] 早晚安出现错误: {e}")
    elif 12 <= hour <= 18:
        if is_master(event.user_id):
            await morning_cmd.finish(Message(_pick(words.word10_list) + MessageSegment.image(_image_api())))
        else:
            await morning_cmd.finish(_pick(words.word5_list))
    else:
        await morning_cmd.finish(_pick(words.word6_list))
