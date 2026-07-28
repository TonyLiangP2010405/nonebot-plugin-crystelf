import copy
import json
import threading
from pathlib import Path
from typing import Any, Optional

from nonebot import get_plugin_config

from .config import Config

_lock = threading.Lock()

# 原项目 auth.json 的默认群配置，保持结构一致
DEFAULT_AUTH_GROUP_CFG: dict[str, Any] = {
    "enable": False,
    "carbon": {
        "enable": False,
        "hint": True,
        "hard-mode": False,
    },
    "timeout": 180,
    "recall": True,
    "frequency": 5,
}

# 验证通过后待发送的入群欢迎缓存: {(group_id, user_id): (timestamp, Message)}
# 对应原项目 redis 中的 Yz:pendingWelcome，过期时间 300 秒
pending_welcome: dict[tuple[int, int], tuple[float, Any]] = {}

WELCOME_CACHE_EXPIRE = 300


def _data_root() -> Path:
    cfg = get_plugin_config(Config)
    root = Path(cfg.crystelf_data_path)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _read_json(name: str, default: Any) -> Any:
    path = _data_root() / f"{name}.json"
    if not path.exists():
        return copy.deepcopy(default)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(default)


def _write_json(name: str, data: Any) -> None:
    path = _data_root() / f"{name}.json"
    with _lock, open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_auth_config() -> dict[str, Any]:
    """读取整份验证配置（含 default 与 groups），结构与原项目 auth.json 一致"""
    cfg = _read_json("auth", {})
    cfg.setdefault("default", copy.deepcopy(DEFAULT_AUTH_GROUP_CFG))
    cfg.setdefault("groups", {})
    return cfg


def save_auth_config(cfg: dict[str, Any]) -> None:
    _write_json("auth", cfg)


def get_group_auth_cfg(group_id: int) -> dict[str, Any]:
    """获取某群的验证配置，未设置时返回默认配置的深拷贝"""
    cfg = get_auth_config()
    group_cfg = cfg["groups"].get(str(group_id))
    if group_cfg is None:
        return copy.deepcopy(cfg["default"])
    return group_cfg


def save_group_auth_cfg(group_id: int, group_cfg: dict[str, Any]) -> None:
    cfg = get_auth_config()
    cfg["groups"][str(group_id)] = group_cfg
    save_auth_config(cfg)


def get_newcomer_config() -> dict[str, Any]:
    """读取入群欢迎配置，结构与原项目 newcomer.json 一致: {群号: {text, image}}"""
    return _read_json("newcomer", {})


def save_newcomer_config(cfg: dict[str, Any]) -> None:
    _write_json("newcomer", cfg)


def newcomer_dir(group_id: int) -> Path:
    path = _data_root() / "newcomer" / str(group_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_welcome(group_id: int, user_id: int, message: Any) -> None:
    import time

    pending_welcome[(group_id, user_id)] = (time.time(), message)


def pop_welcome(group_id: int, user_id: int) -> Optional[Any]:
    """取出缓存的欢迎消息，过期（300 秒）或不存在时返回 None"""
    import time

    item = pending_welcome.pop((group_id, user_id), None)
    if item is None:
        return None
    ts, message = item
    if time.time() - ts > WELCOME_CACHE_EXPIRE:
        return None
    return message
