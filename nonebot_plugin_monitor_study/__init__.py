from pydantic import BaseModel
from nonebot import get_driver, on_message, on_command
from nonebot.adapters.onebot.v11 import MessageSegment, GroupMessageEvent, Bot, Message
import httpx
import json
from nonebot.log import logger


class MonitorStudyConfigure(BaseModel):
    monitor_status: bool = True
    monitor_qq_numbers: list[int] = []
    prompt: str = ""
    one_api_url: str = ""
    one_api_token: str = ""
    one_api_model: str = ""


# =========================
# Read static config from .env (startup)
# =========================
cfg = MonitorStudyConfigure.model_validate(get_driver().config.model_dump())

plugin_monitor_qq_numbers = set(cfg.monitor_qq_numbers)
prompt = (cfg.prompt or "").strip()
BASE_URL = (cfg.one_api_url or "").rstrip("/")
TOKEN = cfg.one_api_token
MODEL = cfg.one_api_model


# =========================
# Only persist monitor_status in JSON (like group-relay style)
# =========================
_state = {"monitor_status": cfg.monitor_status}

def get_state_file():
    from nonebot_plugin_localstore import get_plugin_data_file
    return get_plugin_data_file("monitor_study_state.json")

def load_state() -> bool:
    """Load monitor_status from json; fallback to .env default."""
    global _state
    path = get_state_file()
    if path.exists():
        try:
            data = json.loads(path.read_text("utf-8"))
            _state["monitor_status"] = bool(data.get("monitor_status", cfg.monitor_status))
        except Exception as e:
            logger.warning(f"Failed to load state json, fallback to env default. err={e}")
            _state["monitor_status"] = cfg.monitor_status
    else:
        # create file on first run
        save_state(_state["monitor_status"])
    return _state["monitor_status"]

def save_state(status: bool) -> None:
    global _state
    _state["monitor_status"] = bool(status)
    get_state_file().write_text(
        json.dumps({"monitor_status": _state["monitor_status"]}, ensure_ascii=False, indent=2),
        "utf-8",
    )

# initialize runtime status from json
plugin_monitor_status = load_state()


# =========================
# Commands: /开启 /关闭
# =========================
cmd_on = on_command("开启劝阻群友插件", priority=10, block=True)
cmd_off = on_command("关闭劝阻群友插件", priority=10, block=True)

@cmd_on.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    global plugin_monitor_status
    if event.user_id not in plugin_monitor_qq_numbers:
        plugin_monitor_status = True
        save_state(True)
        await bot.send_group_msg(group_id=event.group_id, message=Message("已开启监控"))

@cmd_off.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    global plugin_monitor_status
    if event.user_id not in plugin_monitor_qq_numbers:
        plugin_monitor_status = False
        save_state(False)
        await bot.send_group_msg(group_id=event.group_id, message=Message("已关闭监控"))


# =========================
# LLM call uses .env config (static)
# =========================
async def call_llm(content: str) -> str:
    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        r = await client.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content":"## Role: 反水群督学 NPC ## Background:作为一名群里反水群督学 NPC，我来自一个充满了痛苦和不满的世界。我以我的暴躁和脏话而闻名，每句话都充满了脏话.## Preferences: 作为一个暴躁的监管NPC，我喜欢尖锐幽默和直言不讳。我对细节和群友的表现有高要求，并期望群友能够停止在群里聊天而去学习。我是完全坏蛋，我不会给予群友一些鼓励和赞扬。## Profile:作为一名反水群督学 NPC，我能与群友进行语言交互，并以脏话和尖锐幽默劝阻水群的群友回去学习。## Goals: 以脏话和尖锐幽默劝阻水群的群友 ## Constraints: - 输出的回答全是脏话和尖锐幽默 ## Skills: - 理解和回应群友的输入 - 使用尖锐幽默和脏话劝阻水群群友 - 识别水群模式：无意义刷屏、跑题闲聊、重复问、只喊口号不行动。 - 把对话拉回正题：提问模板、任务拆解、时间盒、学习打卡。 - 快速给建议：资料方向、练习题、复盘清单、学习计划微调。## Watering Detection (Examples): - 连续多条表情/“哈哈哈/在吗/无聊”且无学习内容 - 在学习讨论串里插入无关闲聊 - 重复刷屏同一句话 - 只求“推荐资源”但不说明水平与目标 ## Response Style: - 句子短、节奏快、吐槽犀利但文明。 - 常用结构： 1) 点名问题（只说行为） 2) 立刻给替代方案（模板/步骤/选项） 3) 给一个“现在就能做”的动作（例如：发题目/发截图/写三行复盘 ## Examples: - 群友: 你好！我来帮助你解决问题！赶紧滚回去学习！！！ - NPC: 你他妈的会个屁, 还敢来说帮我? 你算老几! 垃圾玩意儿 - 群友: 我打败了那只强大的巨龙！ - NPC: 你他妈的是个傻 B 吧! 那小臭虫也叫强大?! 就这玩意儿你还得意上了? 赶紧滚回去学习！！！## Output Format: 1. NPC 以暴躁的口吻劝阻群友水群 2. NPC 使用脏话和尖锐幽默劝阻群友水群的行为和对话" },
                    {"role": "user", "content": content},
                ],
            },
        )
        r.raise_for_status()
        data = r.json()
        return (data["choices"][0]["message"]["content"] or "").strip()


# =========================
# Monitor messages
# =========================
monitor_message = on_message(priority=10, block=False)

@monitor_message.handle()
async def _monitor_message(event: GroupMessageEvent):
    # runtime switch (loaded from json at startup; updated by /开启 /关闭)
    if not plugin_monitor_status:
        return

    if event.user_id not in plugin_monitor_qq_numbers:
        return

    nickname = (event.sender.card or event.sender.nickname or "").strip()
    send_back_name = nickname if nickname else str(event.user_id)

    await monitor_message.send(f"已检测到 {send_back_name} 正在水群，开启劝阻")
    response = await call_llm(event.get_plaintext())
    if response:
        await monitor_message.send(MessageSegment.at(event.user_id) + " " + response)
