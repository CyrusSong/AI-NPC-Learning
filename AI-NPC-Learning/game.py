"""Game state and rules. Only this module changes inventory and health."""

from dataclasses import dataclass, field


@dataclass # 简化“主要用来存数据”的类定义
class Player:
    coins: int = 30
    # 药水
    potions: int = 0
    # 生命值
    health: int = 60
    max_health: int = 100


@dataclass
class Shop:
    stock: int = 3
    price: int = 10


@dataclass
class Memory:
    player_name: str = ""
    # field(default_factory=list) 表示：每次创建新对象时，都调用 list() 生成一个新的空列表
    recent_events: list[str] = field(default_factory=list)


@dataclass
class GameState:
    player: Player = field(default_factory=Player)
    shop: Shop = field(default_factory=Shop)
    memory: Memory = field(default_factory=Memory)


@dataclass
class Proposal:
    intent: str
    speech: str = ""
    quantity: int = 1
    player_name: str = ""


def remember(state: GameState, event: str) -> None:
    state.memory.recent_events.append(event)
    state.memory.recent_events = state.memory.recent_events[-10:]


def apply_proposal(state: GameState, proposal: Proposal) -> str:
    """Validate a proposed action before changing the authoritative game state."""
    if proposal.intent == "talk":
        return proposal.speech

    if proposal.intent == "remember_name":
        name = proposal.player_name
        if not isinstance(name, str):
            return "名字需要是一段文字。"
        name = name.strip()
        if not 1 <= len(name) <= 20 or any(c in name for c in "，,。！？!?：:\n\r"):
            return "请告诉我一个不含标点、长度不超过 20 个字的名字。"
        # 更新的Memory.player_name
        state.memory.player_name = name
        remember(state, f"玩家告诉我名字是{name}。")
        return f"你好，{name}！我叫林老板，我记住你啦~。"

    if proposal.intent == "buy_potion":
        quantity = proposal.quantity
        if type(quantity) is not int or not 1 <= quantity <= 99:
            return "购买数量需要是 1 到 99 之间的整数。"
        # Check every precondition before making any transaction changes.
        if quantity > state.shop.stock:
            return f"库存不足，我现在只有 {state.shop.stock} 瓶药。"
        cost = quantity * state.shop.price
        if cost > state.player.coins:
            return f"金币不足，需要 {cost} 枚，你现在有 {state.player.coins} 枚。"
        state.player.coins -= cost
        state.player.potions += quantity
        state.shop.stock -= quantity
        remember(state, f"玩家买了{quantity}瓶药，花费{cost}枚金币。")
        return f"成交！给你 {quantity} 瓶药，收取 {cost} 枚金币。"

    if proposal.intent == "use_potion":
        if state.player.potions == 0:
            return "你还没有药，可以先在我这里购买。"
        if state.player.health == state.player.max_health:
            return "你的生命已经满了，先把药留着吧。"
        # 一瓶药恢复 20 点生命，但不能超过最大生命值
        healing = min(20, state.player.max_health - state.player.health)
        state.player.potions -= 1
        state.player.health += healing
        remember(state, f"玩家使用了一瓶药，恢复{healing}点生命。")
        return f"你使用了一瓶药，恢复 {healing} 点生命。"

    return "这个行动没有对应的游戏规则，未执行。"


def describe_state(state: GameState) -> str:
    player = state.player
    return (
        f"金币：{player.coins} | 背包药品：{player.potions} 瓶 | "
        f"生命：{player.health}/{player.max_health}\n"
        f"店铺库存：{state.shop.stock} 瓶 | 单价：{state.shop.price} 金币\n"
        f"店主记住的名字：{state.memory.player_name or '尚未认识'}"
    )

