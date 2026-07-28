from nonebot import on_regex
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.plugin import get_plugin_config

from ..config import Config

# 与原项目一致: ^(#|/)?60s|(#|/)?早报$
six_cmd = on_regex(r"^(#|/)?60s|^(#|/)?早报$", priority=10, block=True)


@six_cmd.handle()
async def handle_six():
    cfg = get_plugin_config(Config)
    if not cfg.crystelf_60s:
        return
    await six_cmd.finish(MessageSegment.image(f"{cfg.crystelf_60s_url}/v2/60s?encoding=image"))
