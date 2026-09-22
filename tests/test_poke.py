"""戳一戳与馒头好感度联动单元测试（不依赖机器人连接）"""

import sys
from types import ModuleType, SimpleNamespace

import nonebot

nonebot.init()

POKE_SOURCE = "nonebot_plugin_crystelf:poke"
NEGATIVE_SCENE = "crystelf.poke.negative"
POSITIVE_SCENE = "crystelf.poke"


def poke_event(user_id=2, group_id=10001, self_id="99"):
    return SimpleNamespace(group_id=group_id, user_id=user_id, target_id=int(self_id), self_id=self_id)


def use_config(monkeypatch, **overrides):
    """固定插件配置，避免受真实环境配置影响"""
    from nonebot_plugin_crystelf.apps import poke
    from nonebot_plugin_crystelf.config import Config

    config = Config(**overrides)
    monkeypatch.setattr(poke, "get_plugin_config", lambda model: config)
    return config


def install_affection_stub(
    monkeypatch,
    *,
    negative_text="馒头有点不高兴了",
    positive_text="馒头很开心",
    with_new_api=False,
    new_api_text="馒头被戳得不想说话",
    new_api_error=False,
    legacy_error=False,
):
    """注入假的馒头好感度插件，记录加减好感、取文案场景与新版接口调用

    with_new_api 为真时模块带上新版 poke 接口（契约：PokeResult(delta, text, count, annoyed)）。
    """
    from nonebot_plugin_crystelf.apps import poke

    module = ModuleType("nonebot_plugin_mantou_affection")
    calls = {"add": [], "change": [], "scenes": [], "poke": []}

    async def poke_api(group_id, user_id, *, nickname=""):
        calls["poke"].append((group_id, user_id, nickname))
        if new_api_error:
            raise RuntimeError("新版戳一戳接口不可用")
        return SimpleNamespace(delta=-1, text=new_api_text, count=3, annoyed=True)

    async def add_affection(group_id, user_id, delta, *, nickname="", source=""):
        if legacy_error:
            raise RuntimeError("旧版联动接口不可用")
        calls["add"].append((group_id, user_id, delta, source))
        return delta

    async def change_affection(group_id, user_id, delta, *, nickname="", source=""):
        if legacy_error:
            raise RuntimeError("旧版联动接口不可用")
        calls["change"].append((group_id, user_id, delta, source))
        return delta

    async def get_affection_response(scene, group_id, user_id, *, seed=""):
        if legacy_error:
            raise RuntimeError("旧版联动接口不可用")
        calls["scenes"].append(scene)
        text = negative_text if scene == NEGATIVE_SCENE else positive_text
        return SimpleNamespace(affection=1, level=2, title="有点眼熟", band="neutral", text=text)

    if with_new_api:
        module.poke = poke_api
    module.add_affection = add_affection
    module.change_affection = change_affection
    module.get_affection_response = get_affection_response
    monkeypatch.setitem(sys.modules, "nonebot_plugin_mantou_affection", module)
    monkeypatch.setattr(poke, "get_plugin_by_module_name", lambda name: module)
    return calls


def patch_words(monkeypatch, text="词库回复"):
    """替换戳一戳词库，记录调用参数"""
    from nonebot_plugin_crystelf import words

    calls = []

    def fake_get_word(*args):
        calls.append(args)
        return text

    monkeypatch.setattr(words, "get_word", fake_get_word)
    return calls


def patch_send(monkeypatch):
    """替换戳一戳回复发送，记录发出的文本"""
    from nonebot_plugin_crystelf.apps import poke

    sent = []

    async def fake_send(text):
        sent.append(text)

    monkeypatch.setattr(poke.poke_notice, "send", fake_send)
    return sent


async def test_negative_chance_one_always_loses_affection(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    use_config(monkeypatch, crystelf_poke_negative_chance=1.0)
    calls = install_affection_stub(monkeypatch)

    texts = [await poke._mantou_poke_text(poke_event()) for _ in range(5)]

    assert texts == ["馒头有点不高兴了"] * 5
    assert calls["change"] == [(10001, 2, -1, POKE_SOURCE)] * 5
    assert calls["add"] == []
    assert calls["scenes"] == [NEGATIVE_SCENE] * 5


async def test_negative_chance_zero_always_adds_affection(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    use_config(monkeypatch, crystelf_poke_negative_chance=0.0)
    calls = install_affection_stub(monkeypatch)

    texts = [await poke._mantou_poke_text(poke_event()) for _ in range(20)]

    assert texts == ["馒头很开心"] * 20
    assert calls["change"] == []
    assert calls["add"] == [(10001, 2, 1, POKE_SOURCE)] * 20
    assert calls["scenes"] == [POSITIVE_SCENE] * 20


async def test_missing_affection_plugin_returns_none(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    use_config(monkeypatch, crystelf_poke_negative_chance=1.0)
    monkeypatch.setattr(poke, "get_plugin_by_module_name", lambda name: None)

    assert await poke._mantou_poke_text(poke_event()) is None


async def test_negative_poke_without_text_keeps_affection_loss(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    use_config(monkeypatch, crystelf_poke_negative_chance=1.0)
    calls = install_affection_stub(monkeypatch, negative_text=None)

    assert await poke._mantou_poke_text(poke_event()) is None
    assert calls["change"] == [(10001, 2, -1, POKE_SOURCE)]
    assert calls["scenes"] == [NEGATIVE_SCENE]


async def test_blank_poke_text_returns_none(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    use_config(monkeypatch, crystelf_poke_negative_chance=1.0)
    install_affection_stub(monkeypatch, negative_text="   ")

    assert await poke._mantou_poke_text(poke_event()) is None


async def test_handler_falls_back_to_words_without_affection_plugin(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    use_config(monkeypatch, crystelf_poke_negative_chance=1.0, crystelf_reply_poke=0.0)
    monkeypatch.setattr(poke, "get_plugin_by_module_name", lambda name: None)
    word_calls = patch_words(monkeypatch)
    sent = patch_send(monkeypatch)

    await poke.handle_poke(SimpleNamespace(), poke_event())

    assert sent == ["词库回复"]
    assert word_calls == [("poke", "poke", "馒头")]


async def test_handler_falls_back_to_words_when_negative_text_missing(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    use_config(monkeypatch, crystelf_poke_negative_chance=1.0, crystelf_reply_poke=0.0)
    calls = install_affection_stub(monkeypatch, negative_text=None)
    patch_words(monkeypatch)
    sent = patch_send(monkeypatch)

    await poke.handle_poke(SimpleNamespace(), poke_event())

    assert sent == ["词库回复"]
    assert calls["change"] == [(10001, 2, -1, POKE_SOURCE)]
    assert calls["scenes"] == [NEGATIVE_SCENE]


async def test_new_poke_api_takes_over(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    # 新版接口接管时，本地的负面概率配置不参与
    use_config(monkeypatch, crystelf_poke_negative_chance=1.0)
    calls = install_affection_stub(
        monkeypatch,
        with_new_api=True,
        new_api_text="馒头往旁边挪了挪，假装没被戳到。",
    )

    text = await poke._mantou_poke_text(poke_event())

    assert text == "馒头往旁边挪了挪，假装没被戳到。"
    assert calls["poke"] == [(10001, 2, "")]
    assert calls["add"] == []
    assert calls["change"] == []
    assert calls["scenes"] == []


async def test_blank_new_poke_text_falls_back_to_legacy(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    use_config(monkeypatch, crystelf_poke_negative_chance=0.0)
    calls = install_affection_stub(monkeypatch, with_new_api=True, new_api_text="")

    text = await poke._mantou_poke_text(poke_event())

    assert text == "馒头很开心"
    assert calls["poke"] == [(10001, 2, "")]
    assert calls["add"] == [(10001, 2, 1, POKE_SOURCE)]
    assert calls["scenes"] == [POSITIVE_SCENE]


async def test_new_poke_api_error_falls_back_to_legacy(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    # 回退到旧逻辑时，crystelf_poke_negative_chance 依然生效
    use_config(monkeypatch, crystelf_poke_negative_chance=1.0)
    calls = install_affection_stub(monkeypatch, with_new_api=True, new_api_error=True)

    text = await poke._mantou_poke_text(poke_event())

    assert text == "馒头有点不高兴了"
    assert calls["poke"] == [(10001, 2, "")]
    assert calls["change"] == [(10001, 2, -1, POKE_SOURCE)]
    assert calls["scenes"] == [NEGATIVE_SCENE]


async def test_old_plugin_without_poke_api_uses_legacy_logic(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    use_config(monkeypatch, crystelf_poke_negative_chance=0.0)
    calls = install_affection_stub(monkeypatch)
    assert not hasattr(sys.modules["nonebot_plugin_mantou_affection"], "poke")

    text = await poke._mantou_poke_text(poke_event())

    assert text == "馒头很开心"
    assert calls["poke"] == []
    assert calls["add"] == [(10001, 2, 1, POKE_SOURCE)]
    assert calls["scenes"] == [POSITIVE_SCENE]


async def test_handler_falls_back_to_words_when_all_apis_fail(monkeypatch):
    from nonebot_plugin_crystelf.apps import poke

    use_config(monkeypatch, crystelf_poke_negative_chance=1.0, crystelf_reply_poke=0.0)
    calls = install_affection_stub(monkeypatch, with_new_api=True, new_api_error=True, legacy_error=True)
    patch_words(monkeypatch)
    sent = patch_send(monkeypatch)

    await poke.handle_poke(SimpleNamespace(), poke_event())

    assert sent == ["词库回复"]
    assert calls["poke"] == [(10001, 2, "")]
    assert calls["add"] == []
    assert calls["change"] == []
