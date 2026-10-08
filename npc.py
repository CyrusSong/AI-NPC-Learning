"""A rule-based NPC brain used to learn the loop before adding a model."""

import re

from game import GameState, Proposal


class RuleBasedNPC:
    name = "林老板"
    personality = "友善，记得熟客，按真实库存和价格做生意。"

    def propose(self, message: str, state: GameState) -> Proposal:
        """Read the world and memory, then propose a reply or action."""
        # 第 1 步：清洗输入
        text = message.strip().rstrip("。！？!?")
        # 第 2 步：正则匹配 提取名字（可以改成大模型提取）
        name_match = re.fullmatch(r"(?:我叫|我的名字是|name\s+)\s*(.+)", text)
        # name_match.group(1) 取出第 1 个捕获分组的内容，即名字本身，比如 "小明"（group(0) 是整句，group(1) 才是 (.+) 捕获的部分）。
        if name_match:
            return Proposal("remember_name", player_name=name_match.group(1))

        if text in {"你记得我吗", "我是谁", "你还记得我吗", "remember me"}:
            name = state.memory.player_name
            speech = f"当然记得，你是{name}。" if name else "我们还没交换名字，你叫什么？"
            return Proposal("talk", speech=speech)

        if text in {"你记得什么", "回忆", "memory"}:
            events = state.memory.recent_events[-3:]
            speech = "我记得：" + " ".join(events) if events else "还没有值得记下的事情。"
            return Proposal("talk", speech=speech) # intent="talk" 表示 NPC 只说话，不做其他动作

        buy_match = re.fullmatch(
            r"(?:买|购买|我要买|我想买)\s*([+-]?\d+|[一二两三四五六七八九十]+)?"
            r"\s*(?:瓶|个)?\s*(?:药|药水)",
            text,
        )
        if buy_match:
            count = buy_match.group(1)
            chinese_counts = {
                "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
                "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            }
            if count is None:
                quantity = 1
            elif count in chinese_counts:
                quantity = chinese_counts[count]
            elif re.fullmatch(r"[+-]?\d{1,3}", count):
                quantity = int(count)
            else:
                quantity = 0
            return Proposal("buy_potion", quantity=quantity)

        if text in {"用药", "使用药品", "喝药", "use potion"}:
            return Proposal("use_potion")

        if text in {"你好", "您好", "hello", "hi"}:
            name = state.memory.player_name or "客人"
            return Proposal("talk", speech=f"你好，{name}！今天想买些什么？")

        if text in {"药多少钱", "价格", "库存", "你卖什么"}:
            return Proposal(
                "talk",
                speech=f"我卖恢复生命的药，每瓶 {state.shop.price} 金币，还剩 {state.shop.stock} 瓶。",
            )

        return Proposal(
            "talk",
            speech="这句话我暂时听不懂。你可以说“我叫小陈”“买药”或“你记得我吗”。",
        )

