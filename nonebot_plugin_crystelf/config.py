from pydantic import BaseModel


class Config(BaseModel):
    """crystelf 插件配置"""

    # 机器人昵称（用于戳一戳等文案中的名字替换）
    crystelf_nickname: str = "馒头"
    # 数据存储路径
    crystelf_data_path: str = "data/crystelf"

    # 功能开关
    crystelf_60s: bool = True
    crystelf_auth: bool = True
    crystelf_welcome: bool = True
    crystelf_face_reply: bool = True
    crystelf_poke: bool = True
    crystelf_zwa: bool = True

    # 60s 早报 API
    crystelf_60s_url: str = "https://60s.crystelf.top"
    # 手性碳验证 API
    crystelf_auth_url: str = "https://carbon.crystelf.top"
    # 早晚安随机图片 API（默认使用 pc_wallpaper 壁纸分类，尺度更安全）
    crystelf_image_api: str = "https://uapis.cn/api/v1/random/image?category=pc_wallpaper"
    # 戳一戳回戳概率
    crystelf_reply_poke: float = 0.4
