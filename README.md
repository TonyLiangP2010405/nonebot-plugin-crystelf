<div align="center">

# nonebot-plugin-crystelf

_✨ 移植自 [crystelf-plugin](https://github.com/Jerryplusy/crystelf-plugin) 的 NoneBot2 多功能群娱乐插件 ✨_

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/TonyLiangP2010405/nonebot-plugin-crystelf.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-crystelf">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-crystelf.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">

</div>

## 功能

- **60s 早报**：发送 `60s` 或 `早报`，获取每日早报图片
- **新人入群验证**：支持数字验证（100 以内加减法）与手性碳验证两种模式，超时 / 超限自动踢出，错误答案自动撤回
- **自定义入群欢迎**：按群设置欢迎文案与欢迎图片，可与入群验证联动（验证通过后发送）
- **表情回应**：自动给群消息中的 QQ 表情 / emoji 贴上表情回应（需 NapCat 等支持扩展 API 的协议端）
- **戳一戳**：戳 bot 随机回复并按概率回戳；戳主人会被警告并回戳；主人戳人时 bot 跟着戳
- **早晚安**：早晚安关键词按时段随机回复，主人有专属词库

> 移植范围说明：原项目的「晶灵智能 AI 对话」「点歌」「RSS 订阅」功能不在本插件范围内。

## 安装

### 使用 nb-cli 安装

```bash
nb plugin install nonebot-plugin-crystelf
```

### 使用 pip 安装

```bash
pip install nonebot-plugin-crystelf
```

### 使用 poetry 安装

```bash
poetry add nonebot-plugin-crystelf
```

## 配置

在 NoneBot 项目的 `.env` 文件中添加（均有默认值，可零配置使用）：

```env
# 机器人昵称（用于戳一戳等文案中的名字替换）
CRYSTELF_NICKNAME=馒头
# 数据存储路径
CRYSTELF_DATA_PATH=data/crystelf

# 功能开关
CRYSTELF_60S=true
CRYSTELF_AUTH=true
CRYSTELF_WELCOME=true
CRYSTELF_FACE_REPLY=true
CRYSTELF_POKE=true
CRYSTELF_ZWA=true

# 60s 早报 API
CRYSTELF_60S_URL=https://60s.crystelf.top
# 手性碳验证 API
CRYSTELF_AUTH_URL=https://carbon.crystelf.top
# 戳一戳回戳概率（0~1）
CRYSTELF_REPLY_POKE=0.4
```

「主人」使用 NoneBot 的 `SUPERUSERS` 配置。

## 使用方法

### 60s 早报

| 指令 | 权限 | 范围 | 说明 |
|---|---|---|---|
| 60s / 早报 | 所有人 | 群聊/私聊 | 获取每日早报图片 |

### 新人入群验证

> bot 需要为群管理及以上，操作者需为主人或群管理员

| 指令 | 权限 | 范围 | 说明 |
|---|---|---|---|
| #开启验证 | 群主/管理/主人 | 群聊 | 在本群开启验证，默认为数字验证（100 以内加减法） |
| #关闭验证 | 群主/管理/主人 | 群聊 | 在本群关闭验证 |
| #切换验证模式 | 群主/管理/主人 | 群聊 | 在数字验证和手性碳验证模式之间切换 |
| #重新验证@某人 | 群主/管理/主人 | 群聊 | 让这个人重新验证一次 |
| #绕过验证@某人 | 群主/管理/主人 | 群聊 | 直接通过验证 |
| #设置验证提示模式开启/关闭 | 群主/管理/主人 | 群聊 | 提示模式开启时图上用 `*` 标记手性碳位置 |
| #设置验证困难模式开启/关闭 | 群主/管理/主人 | 群聊 | 困难模式需回答出全部手性碳位置 |
| #设置验证次数+次数 | 群主/管理/主人 | 群聊 | 设置最大验证次数 |
| #设置撤回开启/关闭 | 群主/管理/主人 | 群聊 | 是否撤回错误答案 |

### 自定义入群欢迎

| 指令 | 权限 | 范围 | 说明 |
|---|---|---|---|
| #设置欢迎文案+欢迎词 | 群主/管理/主人 | 群聊 | 设置本群欢迎文案 |
| #设置欢迎图片+图片（或引用图片） | 群主/管理/主人 | 群聊 | 设置本群欢迎图片 |
| #查看欢迎 | 所有人 | 群聊 | 查看当前群欢迎内容 |
| #清除欢迎 | 群主/管理/主人 | 群聊 | 清除当前群欢迎设置 |

### 表情回应

| 指令 | 权限 | 范围 | 说明 |
|---|---|---|---|
| （自动） | - | 群聊 | 监听群消息中的表情并贴表情回应 |
| #回应+emoji | 所有人 | 群聊 | 查看 emoji 对应类型及 id，并贴表情回应 |

### 早晚安

| 指令 | 权限 | 范围 | 说明 |
|---|---|---|---|
| 早 / 早安 / 早上好 / 早啊 等 | 所有人 | 群聊/私聊 | 早安问候（按时段随机回复） |
| 晚安 / 安 / 睡了 / 睡觉 等 | 所有人 | 群聊/私聊 | 晚安问候（按时段随机回复） |

## 示例

```
用户：早报
机器人：[早报图片]

新人加入群聊
机器人：@新人 请在180秒内发送 42 + 37 的计算结果..
新人：79
机器人：@新人 验证通过,欢迎加入本群~

用户：戳一戳 bot
机器人：被戳晕了……轻一点啦！
```

## 与原项目的对应关系

| 原项目功能 (Yunzai) | 本插件实现位置 | 是否完成 | 备注 |
|---|---|---|---|
| 60s 早报 (apps/60s.js) | apps/sixties.py | 是 | - |
| 手性碳/数字验证 (apps/auth.js) | apps/auth.py | 是 | redis 欢迎缓存改为内存缓存（300 秒过期） |
| 验证设置 (apps/auth-set.js) | apps/auth.py | 是 | 配置改为 JSON 文件持久化，结构一致 |
| 入群欢迎 (apps/welcome.js) | apps/welcome.py | 是 | redis 群冷却改为内存冷却（30 秒） |
| 欢迎设置 (apps/welcome-set.js) | apps/welcome.py | 是 | - |
| 表情回应 (apps/face-reply*.js) | apps/face_reply.py | 是 | 统一走 NapCat set_msg_emoji_like |
| 戳一戳 (apps/poke.js) | apps/poke.py | 是 | masterQQ 改为 SUPERUSERS |
| 早晚安 (apps/zwa.js) | apps/zwa.py | 是 | - |
| 晶灵智能 (apps/ai.js) | - | 否 | 不在移植范围内 |
| 点歌 (apps/music.js) | - | 否 | 不在移植范围内 |
| RSS 订阅 (apps/rssPush.js) | - | 否 | 不在移植范围内 |

## 许可证

MIT
