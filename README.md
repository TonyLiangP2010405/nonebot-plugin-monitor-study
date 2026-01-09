<div align="center">
  <a href="https://v2.nonebot.dev/store"><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/nbp_logo.png" width="180" height="180" alt="NoneBotPluginLogo"></a>
  <br>
  <p><img src="https://github.com/A-kirami/nonebot-plugin-template/blob/resources/NoneBotPlugin.svg" width="240" alt="NoneBotPluginText"></p>
</div>

<div align="center">

# nonebot-plugin-monitor-study

_✨ 劝阻群友水群 / 自动提醒插件 ✨_

<a href="./LICENSE">
  <img src="https://img.shields.io/github/license/<你的GitHub用户名>/<你的仓库名>.svg" alt="license">
</a>
<!-- 如果你发布到 PyPI，把下面两行改成你的包名并取消注释 -->
<!--
<a href="https://pypi.python.org/pypi/nonebot-plugin-monitor-study">
  <img src="https://img.shields.io/pypi/v/nonebot-plugin-monitor-study.svg" alt="pypi">
</a>
-->
<img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="python">

</div>

一个基于 **NoneBot2 + OneBot v11** 的群聊监控插件：当指定 QQ 在群里发言时，自动调用 OneAPI / OpenAI 兼容接口生成回复进行“劝阻”。  
插件开关状态会写入本地 **JSON 状态文件**，重启后依然生效；其余配置从 `.env` 读取。

---

## 📖 介绍

`nonebot-plugin-monitor-study` 用于在群聊中监控指定 QQ 号的发言：

- 仅当消息发送者在 `MONITOR_QQ_NUMBERS` 配置名单里时触发
- 自动调用大模型接口生成回复
- 支持指令 **开启/关闭**（仅影响插件开关），开关状态会持久化到 JSON 文件

> 当前实现：每次触发只回复 1 次（你的代码中已改为单次回复）。

---

## 💿 安装

<details open>
<summary>使用 nb-cli 安装</summary>

在 nonebot2 项目的根目录下打开命令行, 输入以下指令即可安装（包名以你实际发布为准）

    nb plugin install nonebot_plugin_monitor_study

</details>

<details>
<summary>使用包管理器安装</summary>

<details>
<summary>pip</summary>

    pip install nonebot-plugin-monitor-study

</details>

然后在 nonebot2 项目根目录下的 `pyproject.toml` 文件, 在 `[tool.nonebot]` 部分追加：

    plugins = ["nonebot_plugin_monitor_study"]

</details>

---

## 📦 依赖

- `nonebot2`
- `nonebot-adapter-onebot`
- `httpx`
- `nonebot-plugin-localstore`（用于保存 JSON 状态文件）

安装 localstore：

    pip install nonebot-plugin-localstore

---

## ⚙️ 配置

在 nonebot2 项目的 `.env` 文件中添加配置（变量名可按你项目实际映射调整）。

| 配置项 | 必填 | 默认值 | 说明 |
|:--:|:--:|:--:|:--|
| `MONITOR_STATUS` | 否 | `true` | 默认监控开关（仅首次运行/无状态文件时使用） |
| `MONITOR_QQ_NUMBERS` | 是 | `[]` | 需要监控的 QQ 列表（示例：`[123,456]`） |
| `PROMPT` | 否 | `""` | system prompt |
| `ONE_API_URL` | 是 | `""` | OneAPI/OpenAI 兼容接口地址（示例：`https://xxx/v1`） |
| `ONE_API_TOKEN` | 是 | `""` | 接口 Token |
| `ONE_API_MODEL` | 是 | `""` | 模型名（如 `gpt-4o-mini` / `qwen2.5` 等，以你的 OneAPI 配置为准） |

### 关于状态持久化（JSON）
插件只会把 **开关状态** 写入本地文件：

- 文件名：`monitor_study_state.json`
- 位置：由 `nonebot_plugin_localstore` 管理（通常在 bot 的数据目录下）

JSON 内容示例：

```json
{
  "monitor_status": true
}