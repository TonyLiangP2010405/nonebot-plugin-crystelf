"""核心函数单元测试（不依赖机器人连接）"""

import nonebot

nonebot.init()


def test_extract_emojis():
    from nonebot_plugin_crystelf.utils import extract_emojis

    assert extract_emojis("你好") == []
    assert "😀" in extract_emojis("你好😀啊")
    # ZWJ 序列应作为一个整体提取
    family = extract_emojis("看👨‍👩‍👧这个")
    assert len(family) == 1


def test_js_parse_int():
    from nonebot_plugin_crystelf.apps.auth import _js_parse_int

    assert _js_parse_int("42") == 42
    assert _js_parse_int("-7") == -7
    assert _js_parse_int("42abc") == 42
    assert _js_parse_int("  13  ") == 13
    assert _js_parse_int("abc") is None
    assert _js_parse_int("") is None


def test_words_pick_and_params():
    from nonebot_plugin_crystelf import words

    word = words.get_word("poke", "poke")
    assert isinstance(word, str) and word

    # 名字替换逻辑
    assert words._apply_params("{name}真可爱", name="馒头") == "馒头真可爱"
    assert words._apply_params("馒头不知道哦", name="鸡气人") == "鸡气人不知道哦"
    assert words._apply_params("没有名字") == "没有名字"

    # 早晚安词库可读
    assert words.get_word("MN-hello", "good-morning")
    assert words.get_word("MN-hello", "good-night")


def test_data_store_auth_cfg(tmp_path, monkeypatch):
    from nonebot_plugin_crystelf import data_store

    monkeypatch.setattr(data_store, "_data_root", lambda: tmp_path)

    # 默认配置结构与原项目 auth.json 一致
    group_cfg = data_store.get_group_auth_cfg(123456)
    assert group_cfg["enable"] is False
    assert group_cfg["carbon"]["hint"] is True
    assert group_cfg["carbon"]["hard-mode"] is False
    assert group_cfg["timeout"] == 180
    assert group_cfg["recall"] is True
    assert group_cfg["frequency"] == 5

    # 修改并保存后能读回，且不影响默认配置
    group_cfg["enable"] = True
    group_cfg["frequency"] = 3
    data_store.save_group_auth_cfg(123456, group_cfg)

    loaded = data_store.get_group_auth_cfg(123456)
    assert loaded["enable"] is True
    assert loaded["frequency"] == 3

    other = data_store.get_group_auth_cfg(654321)
    assert other["enable"] is False
    assert other["frequency"] == 5


def test_data_store_newcomer(tmp_path, monkeypatch):
    from nonebot_plugin_crystelf import data_store

    monkeypatch.setattr(data_store, "_data_root", lambda: tmp_path)

    assert data_store.get_newcomer_config() == {}
    data_store.save_newcomer_config({"123": {"text": "欢迎", "image": "/tmp/1.jpg"}})
    assert data_store.get_newcomer_config()["123"]["text"] == "欢迎"


def test_welcome_cache(tmp_path, monkeypatch):
    import time

    from nonebot_plugin_crystelf import data_store

    data_store.pending_welcome.clear()
    data_store.cache_welcome(1, 2, "msg")
    assert data_store.pop_welcome(1, 2) == "msg"
    # 取出后即删除
    assert data_store.pop_welcome(1, 2) is None
    # 过期返回 None
    data_store.pending_welcome[(1, 2)] = (time.time() - 400, "msg")
    assert data_store.pop_welcome(1, 2) is None


def test_carbon_answer_logic():
    """手性碳答案判定：普通模式任一命中即可，困难模式需全部命中"""

    def check(msg, regions, hard):
        msg_regions = [s.strip() for s in msg.upper().replace("，", ",").split(",") if s.strip()]
        right = [str(r).upper() for r in regions]
        if hard:
            return all(r in msg_regions for r in right)
        return any(r in msg_regions for r in right)

    assert check("A", ["A", "C"], hard=False)
    assert check("a，c", ["A", "C"], hard=True)
    assert not check("A", ["A", "C"], hard=True)
    assert not check("B", ["A", "C"], hard=False)
