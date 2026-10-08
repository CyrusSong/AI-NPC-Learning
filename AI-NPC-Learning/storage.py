"""Load validated JSON saves and replace files atomically."""

import json
import os
from dataclasses import asdict
from pathlib import Path
from tempfile import NamedTemporaryFile

from game import GameState, Memory, Player, Shop


class SaveError(Exception):
    pass


def _integer(data: dict, key: str, minimum: int = 0) -> int:
    value = data[key]
    if type(value) is not int or not minimum <= value <= 1_000_000:
        raise ValueError(f"{key} 需要是 {minimum} 到 1000000 之间的整数")
    return value


def load_game(path: Path) -> GameState:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return GameState()
    except (OSError, ValueError) as error:
        raise SaveError(f"无法读取存档 {path}：{error}") from error

    try:
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise ValueError("不支持此存档版本")
        saved = data["state"]
        player_data, shop_data, memory_data = saved["player"], saved["shop"], saved["memory"]
        # 从存档 JSON 里读出玩家数据，校验后构造一个 Player 对象
        # Player(...) ："照这张模板，造一个具体的玩家出来
        # # 情况一：新游戏 —— 不传任何参数，全部用默认值
        # player = Player()        # coins=30, health=60, ...
        # 情况二：读存档 —— 用存档里的数值覆盖默认值
        player = Player(
            coins=_integer(player_data, "coins"),
            potions=_integer(player_data, "potions"),
            health=_integer(player_data, "health"),
            max_health=_integer(player_data, "max_health", minimum=1),
        )
        if player.health > player.max_health:
            raise ValueError("生命不能超过最大生命")
        shop = Shop(stock=_integer(shop_data, "stock"), price=_integer(shop_data, "price", minimum=1))
        name, events = memory_data["player_name"], memory_data["recent_events"]
        if not isinstance(name, str) or len(name) > 20:
            raise ValueError("记忆中的名字格式无效")
        if not isinstance(events, list) or len(events) > 10:
            raise ValueError("最近事件应是最多 10 条记录的列表")
        if any(not isinstance(event, str) or len(event) > 200 for event in events):
            raise ValueError("事件记录格式无效")
        return GameState(player=player, shop=shop, memory=Memory(name, events))
    except (KeyError, TypeError, ValueError) as error:
        raise SaveError(f"存档格式无效，原文件已保留：{path}。原因：{error}") from error


def save_game(path: Path, state: GameState) -> None:
    temporary_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # A partial write must not destroy the last complete save.
        # 部分写入操作不得破坏上一次完整的保存。
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False) as handle:
            temporary_path = Path(handle.name)
            json.dump({"schema_version": 1, "state": asdict(state)}, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_path, path)
    except OSError as error:
        raise SaveError(f"无法保存到 {path}：{error}") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                # Keep the original save error if cleanup also fails.
                pass
