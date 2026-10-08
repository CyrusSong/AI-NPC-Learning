"""Input -> rule/model proposal -> game rules -> saved state."""

import argparse
import getpass
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from deepseek_npc import DEFAULT_MODEL, DeepSeekNPC, ModelError
from game import GameState, apply_proposal, describe_state
from npc import RuleBasedNPC
from storage import SaveError, load_game, save_game


HELP = """可以输入：
  你好 / 我叫小成 / 你记得我吗 / 你记得什么
  药多少钱 / 买药 / 买2瓶药 / 用药
  状态 / 保存 / 帮助 / 退出
购买数量可用阿拉伯数字，或一到十的中文数字。"""


def main() -> int:
    # 脚本添加命令行参数解析功能
    parser = argparse.ArgumentParser(description="AI NPC 学习原型：规则模式 / DeepSeek 模式") # 创建一个参数解析器
    parser.add_argument("--npc", choices=("rule", "deepseek"), default="rule", help="选择 NPC 的决策方式")
    parser.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL), help="DeepSeek 模型名称")
    parser.add_argument("--trace", action="store_true", help="显示接口诊断、提议及执行后的游戏状态")
    parser.add_argument("--save-file", type=Path, help="存档路径；相对路径以项目目录为起点")
    parser.add_argument("--new", action="store_true", help="开始新游戏；下一次保存会覆盖指定路径的旧存档")
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent
    if args.save_file is None:
        save_name = "lesson02.json" if args.npc == "deepseek" else "save.json"
        args.save_file = project_root / "data" / save_name
    elif not args.save_file.is_absolute():
        args.save_file = project_root / args.save_file

    try:
        # 初始化状态：逐字段校验造出 Player / Shop / Memory
        state = GameState() if args.new else load_game(args.save_file)
    except SaveError as error:
        print(error)
        print("请检查存档，或用 --save-file 指定另一个存档路径。")
        return 1

    # 实例化人物NPC
    if args.npc == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if not api_key:
            if not sys.stdin.isatty():
                print("没有配置 DEEPSEEK_API_KEY。请在交互终端启动，按提示隐藏输入密钥。")
                return 1
            try:
                api_key = getpass.getpass("DeepSeek API Key（隐藏输入，不写入存档）：")
            except (EOFError, KeyboardInterrupt):
                print("\n密钥输入已取消。")
                return 1
        try:
            npc = DeepSeekNPC(api_key, model=args.model)
        except ModelError as error:
            print(error)
            return 1
        print(f"店主 NPC · 第二课 · DeepSeek 模式（{npc.model}）")
    else:
        npc = RuleBasedNPC()
        print("店主 NPC · 第一课 · 规则模式")
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
        try:
            proposal = npc.propose(message, state)
        except ModelError as error:
            if args.trace and isinstance(npc, DeepSeekNPC):
                for info in npc.response_diagnostics:
                    print("[接口] " + json.dumps(info, ensure_ascii=False))
            print(f"模型请求失败：{error}\n本轮未执行行动，可重新输入。\n")
            continue
        except KeyboardInterrupt:
            print("\n本轮已取消，未执行行动。输入“退出”结束游戏。")
            continue
        if args.trace:
            if isinstance(npc, DeepSeekNPC):
                for info in npc.response_diagnostics:
                    print("[接口] " + json.dumps(info, ensure_ascii=False))
            print("[提议] " + json.dumps(asdict(proposal), ensure_ascii=False))
        # apply_proposal() 负责验证意图是否合法，并修改游戏状态（GameState）和记忆（Memory），返回 NPC 的回复文本
        reply = apply_proposal(state, proposal)
        try:
            save_game(args.save_file, state)
        except SaveError as error:
            print(error)
            print("本轮只在内存中执行，未能存档；程序已停止，请检查保存路径。")
            return 1
        if isinstance(npc, DeepSeekNPC):
            npc.record_turn(message, reply)
        print(f"{npc.name}：{reply}\n")
        if args.trace:
            print("[执行后的状态]\n" + describe_state(state) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
