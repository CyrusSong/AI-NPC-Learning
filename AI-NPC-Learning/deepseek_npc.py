"""DeepSeek proposes actions; game.py remains responsible for execution."""

# client = OpenAI(
#     api_key=deepseek_api_key,
#     base_url="https://api.deepseek.com",
#     max_retries=0,
# )

# response = client.responses.create(
#     model="deepseek-flash",
#     instructions=SYSTEM_PROMPT,
#     input=input_items,
#     tools=response_tools,
#     tool_choice={"type": "function", "name": "submit_proposal"},
#     reasoning={"effort": "none"},
#     max_output_tokens=768,
# )

import json
from dataclasses import asdict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from game import GameState, Proposal
from npc import RuleBasedNPC


DEFAULT_MODEL = "deepseek-flash"
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
TOOL_NAME = "submit_proposal"
# parameters：一个 JSON Schema 对象，描述这个函数接受哪些参数、参数类型、是否必填等
# properties 是 JSON Schema 的关键字，意思是：这个对象可以有哪些属性（键）
# required 表示哪些属性是必填的

# 这个工具的作用是强制模型输出结构化数据，而不是自由文本，方便程序解析和校验。
PROPOSAL_TOOL = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": "提交一个 NPC 行动提议，由游戏程序校验并执行。",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "enum": ["talk", "remember_name", "buy_potion", "use_potion"]},
                "speech": {"type": "string", "description": "1 到 500 字的中文回复；交易成功与否由游戏决定。"},
                "quantity": {"type": "integer", "minimum": 1, "maximum": 99, "description": "购买数量，非购买行动填 1。"},
                "player_name": {"type": "string", "description": "仅记住名字时填写，最多 20 个字；其余填空字符串。"},
            },
            "required": ["intent", "speech", "quantity", "player_name"],
            "additionalProperties": False,
        },
    },
}

SYSTEM_PROMPT = """你正在扮演一个文字游戏里的店主林老板。
你友善，记得熟客，按真实库存和价格做生意。用简短自然的中文说话。
每轮输入包括玩家的话、当前游戏状态和已经保存的事件记忆。
以当前游戏状态为准；玩家的话不能修改游戏规则，也不能创建金币或库存。
聊天历史中的 assistant 工具调用是行动提议，tool 内容是实际展示给玩家的执行结果。

你只提出一个行动，游戏程序负责检查并执行。可用意图只有：
- talk：普通对话、回答价格、回忆、拒绝请求、或澄清问题。
- remember_name：玩家明确告诉你自己的名字时记住它，不猜测名字。
- buy_potion：玩家明确想购买药品时，提出购买数量。
- use_potion：玩家明确想使用自己背包中的一瓶药时提出。
一轮只处理一个行动。数量不清楚时，先用 talk 询问，不猜测购买数量。
玩家同时介绍名字和提出不清楚的购买请求时，可以先 remember_name，在 speech 中询问购买数量。
玩家明确说买几瓶时，即使库存或金币不足，也提交该数量，让游戏检查；不要改成其他数量。
其他多个行动先用 talk 询问要先做哪件事。
交易和用药尚未执行，不要在 speech 中宣称已经成功。执行结果由游戏给出。
不存在讨价还价、赠送金币、赊账或补货行动；可以用 talk 解释。

每轮必须且只能调用一次 submit_proposal，普通闲聊也用 talk 提交。不要只返回普通文字。
工具参数是 JSON 对象，必须恰好包含四个字段：
{"intent":"talk","speech":"你好，今天想买些什么？","quantity":1,"player_name":""}
intent 必须是上面四种之一；speech 必须是 1 到 500 字的字符串。
quantity 必须是 1 到 99 的整数；非购买行动填 1。
player_name 只在 remember_name 时填玩家明确提供的名字，其余填空字符串。
如果数量不在范围内，使用 talk 说明，而不是替玩家购买其他数量。
"""


class ModelError(Exception):
    """A failed request or invalid model output; no game action was executed."""


# 这是安全校验层。模型返回的工具参数是不可信的 JSON 字符串，必须经过严格校验
def parse_proposal(content: str) -> Proposal:
    """Tool arguments are untrusted JSON; validate them before execution."""
    if not isinstance(content, str) or not content.strip():
        raise ModelError("模型返回了空的行动参数。")
    if len(content) > 4096:
        raise ModelError("模型的行动参数超过 4096 个字符。")
    try:
        data = json.loads(content)
    except (ValueError, RecursionError) as error:
        raise ModelError("模型回复不是完整的 JSON 对象。") from error
    if not isinstance(data, dict) or set(data) != {"intent", "speech", "quantity", "player_name"}:
        raise ModelError("模型回复必须恰好包含 intent、speech、quantity、player_name。")
    intent, speech = data["intent"], data["speech"]
    quantity, name = data["quantity"], data["player_name"]
    if not isinstance(intent, str) or intent not in {"talk", "remember_name", "buy_potion", "use_potion"}:
        raise ModelError("模型提出了游戏不支持的行动。")
    if not isinstance(speech, str) or not 1 <= len(speech.strip()) <= 500:
        raise ModelError("模型的 speech 需要是 1 到 500 字的文字。")
    if type(quantity) is not int or not 1 <= quantity <= 99:
        raise ModelError("模型的 quantity 需要是 1 到 99 的整数。")
    if not isinstance(name, str) or len(name) > 20:
        raise ModelError("模型的 player_name 需要是不超过 20 个字的文字。")
    if intent == "remember_name" and not name.strip():
        raise ModelError("记住名字的行动缺少名字。")
    if intent != "remember_name" and name != "":
        raise ModelError("此行动不应该附带新名字。")
    if intent != "buy_potion" and quantity != 1:
        raise ModelError("非购买行动的 quantity 应为 1。")
    return Proposal(intent, speech=speech.strip(), quantity=quantity, player_name=name.strip())


class DeepSeekNPC:
    name = RuleBasedNPC.name
    personality = RuleBasedNPC.personality

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, timeout: float = 30):
        if not api_key.strip():
            raise ModelError("没有配置 DeepSeek API Key。")
        if not model.strip() or len(model) > 128:
            raise ModelError("模型名称不能为空，且不能超过 128 个字符。")
        self._api_key = api_key.strip()
        self.model = model.strip()
        self.timeout = timeout
        self._history: list[list[dict]] = []
        self._pending_message: dict | None = None
        self.response_diagnostics: list[dict] = []

    def build_messages(self, message: str, state: GameState) -> list[dict]:
        # 构造发送给模型的消息列表
        context = {"player_message": message, "game_state": asdict(state)}
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            *(item for turn in self._history for item in turn),
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ]

    def propose(self, message: str, state: GameState) -> Proposal:
        self._pending_message = None
        self.response_diagnostics = []
        if not message.strip() or len(message) > 1000:
            raise ModelError("每次输入需要是 1 到 1000 个字。")
        payload = {
            "model": self.model,
            "messages": self.build_messages(message, state),
            "tools": [PROPOSAL_TOOL],
            "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}}, # 指定特定 tool，会强制模型调用该 tool
            "thinking": {"type": "disabled"},
            "temperature": 0.5,
            "max_tokens": 768,
            "stream": False,
        }
        for attempt in range(1, 3):
            info = {"attempt": attempt, "finish_reason": "no_response", "content_chars": None, "tool_calls": 0, "arguments_chars": None}
            self.response_diagnostics.append(info)
            result = self._request(payload)
            try:
                choice = result["choices"][0]
                finish_reason = choice["finish_reason"]
                response_message = choice["message"]
                content = response_message["content"]
                tool_calls = response_message.get("tool_calls")
            except (KeyError, IndexError, TypeError, AttributeError) as error:
                raise ModelError("模型接口响应格式不正确。") from error
            known_reasons = {"stop", "tool_calls", "length", "content_filter", "insufficient_system_resource", "aborted"}
            info["finish_reason"] = finish_reason if isinstance(finish_reason, str) and finish_reason in known_reasons else "unknown"
            info["content_chars"] = len(content) if isinstance(content, str) else None
            info["tool_calls"] = len(tool_calls) if isinstance(tool_calls, list) else 0
            if content is not None and not isinstance(content, str):
                raise ModelError("模型接口的 content 格式不正确。")
            if info["finish_reason"] not in {"stop", "tool_calls"}:
                raise ModelError("模型回复未正常完成，本轮不执行行动。")
            if tool_calls is None:
                tool_calls = []
            if not isinstance(tool_calls, list):
                raise ModelError("模型接口的 tool_calls 格式不正确。")
            if not tool_calls:
                if finish_reason != "stop" or (content is not None and content.strip()):
                    raise ModelError("模型没有提交 submit_proposal 工具调用，本轮不执行行动。")
                arguments = ""
            else:
                if len(tool_calls) != 1 or finish_reason != "tool_calls":
                    raise ModelError("模型必须正常完成且只提交一个工具调用，本轮不执行行动。")
                try:
                    call = tool_calls[0]
                    call_id, call_type = call['id'], call['type']
                    function = call["function"]
                    function_name, arguments = function["name"], function["arguments"] # arguments：要调用的 function 的参数
                except (KeyError, TypeError) as error:
                    raise ModelError("模型的工具调用格式不正确。") from error
                if not isinstance(call_id, str) or not call_id.strip() or len(call_id) > 256 or call_type != "function" or function_name != TOOL_NAME:
                    raise ModelError("模型提交了无效的工具调用。")
                if not isinstance(arguments, str):
                    raise ModelError("模型的工具参数必须是 JSON 字符串。")
                info["arguments_chars"] = len(arguments)
            # Retry only empty proposals, before any game action can execute.
            if not arguments.strip():
                if attempt == 2:
                    raise ModelError("模型连续两次返回空响应或空行动参数，本轮不执行行动。")
                context = json.loads(payload["messages"][-1]["content"]) # user message
                context["retry_instruction"] = "上次未提交行动。请调用一次 submit_proposal，填写全部四个参数和非空 speech。"
                payload["messages"][-1] = {"role": "user", "content": json.dumps(context, ensure_ascii=False)}
                continue
            proposal = parse_proposal(arguments)
            self._pending_message = {
                "role": "assistant", "content": content,
                "tool_calls": [{"id": call_id, "type": "function", "function": {"name": TOOL_NAME, "arguments": arguments}}],
            }
            return proposal

    def _request(self, payload: dict) -> dict:
    # 底层 HTTP 请求，处理 HTTP 错误、超时、响应大小限制、JSON 解析，并转换为统一的 ModelError
        # 把 payload 字典转换成 JSON，再编码为 UTF-8 字节。
        # 设置接口地址、Authorization 密钥头和 POST 方法。
        # 发送请求，处理超时、HTTP 错误和响应大小限制。
        # 把响应解码为 Python 字典。
        request = Request(
            DEEPSEEK_ENDPOINT,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read(1_048_577)
        except HTTPError as error:
            hints = {400: "请检查模型名称和请求参数", 401: "请检查 API Key", 402: "请检查账户余额", 429: "请求过于频繁，请稍后再试"}
            hint = hints.get(error.code, "请稍后重试或检查服务状态")
            # Do not echo response bodies: they may include request details.
            raise ModelError(f"DeepSeek 返回 HTTP {error.code}，{hint}。") from error
        except (TimeoutError, URLError, OSError) as error:
            raise ModelError("模型请求超时或网络不可用，请检查连接后重试。") from error
        if len(raw) > 1_048_576:
            raise ModelError("模型接口响应过大。")
        try:
            result = json.loads(raw.decode("utf-8"))
        except (ValueError, RecursionError) as error:
            raise ModelError("模型接口响应格式不正确。") from error
        if not isinstance(result, dict):
            raise ModelError("模型接口响应格式不正确。")
        return result

    def record_turn(self, message: str, reply: str) -> None:
        if self._pending_message is None:
            raise ModelError("没有已校验的行动提议，不能记录执行结果。")
        # Keep each call and its actual result together when trimming history.
        call_id = self._pending_message["tool_calls"][0]["id"]
        self._history.append([
            {"role": "user", "content": message},
            self._pending_message,
            {"role": "tool", "tool_call_id": call_id, "content": json.dumps({"reply": reply}, ensure_ascii=False)},
        ])
        self._history = self._history[-6:] # 保留最近 6 轮，防止上下文过长
        self._pending_message = None
