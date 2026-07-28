from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="晶灵插件",
    description="移植自 crystelf-plugin 的多功能群娱乐插件：60s 早报、新人验证、入群欢迎、表情回应、戳一戳、早晚安",
    usage=(
        "60s / 早报 - 获取每日早报图片\n"
        "#开启验证 / #关闭验证 / #切换验证模式 - 新人入群验证管理\n"
        "#设置欢迎文案 / #设置欢迎图片 / #查看欢迎 / #清除欢迎 - 入群欢迎管理\n"
        "#回应+emoji - 查看表情类型及 id\n"
        "早安 / 晚安 - 早晚安问候\n"
        "戳一戳 bot - 随机回复"
    ),
    type="application",
    homepage="https://github.com/TonyLiangP2010405/nonebot-plugin-crystelf",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

from .apps import auth, face_reply, poke, sixties, welcome, zwa  # noqa: E402, F401
