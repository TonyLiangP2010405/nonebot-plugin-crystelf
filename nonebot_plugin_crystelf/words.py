import json
import random
from pathlib import Path
from typing import Optional

WORDS_ROOT = Path(__file__).parent / "resources" / "words"

# 原项目 constants/zwa/wordlist.js，保持内容一致
word2_list = [" 主人安安啦", " 主人好梦哦", " 主人晚安", " 晚安，主人～", " 主人安安"]

word3_list = [
    " 主人早安呀！",
    " 早上好，主人～",
    " 主人早呀",
    " 祝主人今日运气满满",
    " 主人早啊",
]

word4_list = [
    " 笨蛋！现在确实早过头了！",
    " 好早...(哈欠~)",
    " 这么早就起来忙了吗 强啊",
    " 早什么早 起床玩原神吗！",
    " 睡了吗就早早早（白眼）",
    " 这么早是为了原神吧",
]

word5_list = [
    " 笨蛋！几点了还早",
    " 原神玩多了就这样，起这么晚",
    " 不早了，（玩原神玩的）",
    " 你无敌了孩子",
    " 太阳都晒屁股了还早啊~",
    " 笨蛋笨蛋笨蛋笨蛋笨蛋！",
    " 早？（都怪原神）",
]

word6_list = [
    " 大晚上的，你是不是美国作息",
    " 晚上了都，还早啊？",
    " 少玩点原神，白天黑夜都分不清了",
    " 你无敌了孩子",
    " 6",
    " 这个点说早上好，你是不是刚睡醒？昼夜颠倒了吧",
    " 早？（都怪原神）",
]

word7_list = [
    " 主人快点睡觉吧，很晚了哦",
    " 不要通宵了主人赶紧睡觉吧",
    " 笨蛋主人快点睡觉，明天又起不来了",
    " 主人要猝死了，呜呜呜~~~",
    " 这么晚没睡觉，深夜emo了吧",
]

word8_list = [
    " 这么晚睡觉，头发掉光光哦~",
    " 大晚上的玩原神不睡觉是啊",
    " 好，吃完早餐再睡觉",
    " 熬夜等着秃头吧",
    " 不好好睡觉的都是坏孩子",
]

word9_list = [
    " 啊？你要这个点睡觉吗？那晚安好梦",
    " 傻傻分不清白天黑夜，（玩原神导致的）",
    " 大白天的，想做白日梦吗",
    " 笨呐~~",
    " 睡这么早吗，晚安咯~",
    " 通宵可不好哦",
    " 这个点睡觉吗，那晚安",
    " 晚安？现在？",
    " 现在是白天哦，昨晚是不是没睡觉啊",
]

word10_list = [
    " 笨蛋！都几点了还早早早！",
    " 懒猪终于起床了呢",
    " 懒虫，没救了~",
    " 太阳都晒屁股了还早啊~",
    " 摊上你这么懒的主人我也没办法~",
    " 晚睡可不好哦~",
    " 主人你昨晚通宵玩原神了吧",
]


def _read_word_file(word_type: str, name: str) -> list[str]:
    path = WORDS_ROOT / word_type / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"文案文件必须是数组: {path}")
    return data


def _apply_params(text: str, name: Optional[str] = None, default_name: str = "真寻") -> str:
    """与原项目 applyParams 一致：替换默认名与 {name} 占位"""
    if not name:
        return text
    return (
        text.replace(default_name, name)
        .replace("{name}", name)
        .replace("{{name}}", name)
        .replace("%name%", name)
    )


def pick_random(words: list) -> str:
    if not words:
        return ""
    return random.choice(words)


def get_word(word_type: str, name: str, nickname: Optional[str] = None) -> str:
    """从词库中随机取一条文案并替换名字"""
    words = _read_word_file(word_type, name)
    return _apply_params(pick_random(words), nickname)
