"""The first lesson: input -> NPC proposal -> game rules -> saved state."""

import argparse
from pathlib import Path

from game import GameState, apply_proposal, describe_state
from npc import RuleBasedNPC
from storage import SaveError, load_game, save_game


HELP = """可以输入：
  你好 / 我叫小陈 / 你记得我吗 / 你记得什么
  药多少钱 / 买药 / 买2瓶药 / 用药
  状态 / 保存 / 帮助 / 退出
购买数量可用阿拉伯数字，或一到十的中文数字。"""


def main() -> int:
    # 脚本添加命令行参数解析功能
    parser = argparse.ArgumentParser(description="AI NPC 学习原型：第一课，规则模式") # 创建一个参数解析器
    parser.add_argument("--save-file", type=Path, default=Path(__file__).resolve().parent / "data" / "save.json")
    parser.add_argument("--new", action="store_true", help="开始新游戏；下一次保存会覆盖指定路径的旧存档")
    args = parser.parse_args()

    try:
        # 初始化状态：逐字段校验造出 Player / Shop / Memory
        state = GameState() if args.new else load_game(args.save_file)
    except SaveError as error:
        print(error)
        print("请检查存档，或用 --save-file 指定另一个存档路径。")
        return 1

    # 实例化人物NPC
    npc = RuleBasedNPC()
    print("店主 NPC · 第一课")
    print("当前使用规则回复，尚未接入大模型。")
    if args.new:
        print("已开始新游戏；下一次保存会覆盖此路径的旧存档。")
    print(f"存档：{args.save_file.resolve()}")
    print(describe_state(state))
    print("输入“帮助”查看命令，输入“退出”结束。\n")

    while True:
        try:
            message = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            message = "退出"
        if not message:
            continue
        if message in {"退出", "quit", "exit"}:
            try:
                save_game(args.save_file, state)
            except SaveError as error:
                print(error)
                return 1
            print("已保存，下次见。")
            return 0
        if message in {"帮助", "help"}:
            print(HELP)
            continue
        if message in {"状态", "status"}:
            print(describe_state(state))
            continue
        if message in {"保存", "save"}:
            try:
                save_game(args.save_file, state)
            except SaveError as error:
                print(error)
                return 1
            print("已保存。")
            print("自动退出，请重新运行程序继续游戏。")
            return 0

        # npc.propose() 只负责读取输入和记忆，提出一个意图（Proposal），不直接修改游戏状态（存在大模型输出不可信问题）
        proposal = npc.propose(message, state)
        # apply_proposal() 负责验证意图是否合法，并修改游戏状态（GameState）和记忆（Memory），返回 NPC 的回复文本
        reply = apply_proposal(state, proposal)
        try:
            save_game(args.save_file, state)
        except SaveError as error:
            print(error)
            print("本轮只在内存中执行，未能存档；程序已停止，请检查保存路径。")
            return 1
        print(f"{npc.name}：{reply}\n")


if __name__ == "__main__":
    raise SystemExit(main())

