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
    if int(event.user_id) == 1287663323:
        plugin_monitor_status = True
        save_state(True)
        await bot.send_group_msg(group_id=event.group_id, message=Message("已开启监控"))

@cmd_off.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    global plugin_monitor_status
    if int(event.user_id) == 1287663323:
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
                    {"role": "system", "content": prompt},
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
