# AI NPC 学习项目：一个记得你的店主

从一个小而完整的文字游戏开始：告诉店主名字，购买药品，使用药品，退出后再次回来。

**当前是第一课：规则模拟 NPC。尚未接入大模型，也不需要 API Key。**
这一步学习 NPC 系统的输入、记忆、行动、游戏规则和存档；自由对话是后续课程的目标。

## 先运行

在这个文件夹打开 PowerShell，执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

脚本会寻找项目虚拟环境或可用的 Python，也支持本机 Codex 自带的 Python。
本项目使用 Python 3.10+ 和标准库，不需要安装第三方包。
`ExecutionPolicy Bypass` 只作用于这次 PowerShell 进程，不修改系统执行策略。

如果你已经有正常可用的 Python，也可以运行：

```powershell
python -X utf8 main.py
```

## 完成第一次试玩

按顺序输入，每句话输入后按回车：

```text
你好
我叫小陈
你记得我吗
药多少钱
买2瓶药
状态
用药
你记得什么
退出
```

初始状态是 30 金币、0 瓶药、60/100 生命；店铺有 3 瓶药，每瓶 10 金币。
买两瓶药后应有 10 金币、2 瓶药；使用一瓶后应有 1 瓶药、80/100 生命。

再次运行，输入 `你记得我吗` 和 `状态`，检查名字和交易结果是否保留。
每次对话后自动保存到 `data/save.json`，退出时也会保存。
普通启动会继续上次游戏；没有存档时自动开始新游戏。

如果要重玩，请明确运行下面的命令。下一次保存会覆盖当前默认存档：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1 --new
```

也可以用 `--save-file data/another-save.json` 指定另一份存档。

## 文件怎么读

| 文件 | 你要理解的问题 |
| --- | --- |
| `main.py` | 玩家输入后，程序依次调用了谁？ |
| `npc.py` | NPC 怎样读取记忆，并提出回复或行动？ |
| `game.py` | 谁检查金币和库存，谁真正修改游戏状态？ |
| `storage.py` | 名字、物品和事件怎样保存，并在下次启动时恢复？ |
| `LESSON_01.md` | 第一课的具体阅读步骤、预测题和练习 |
| `tests/test_game.py` | 哪些情况必须保持状态不变？ |

建议顺序：先试玩，再读 `LESSON_01.md`，之后沿着一次购买的调用路径读源码。
不用先读懂所有存档校验和自动化测试。

## 当前能力边界

- NPC 通过少量文字规则识别名字、回忆、购买和用药；它还没有自由语言理解能力。
- 人格描述只是设定。此版本的回复由代码决定，不由大模型生成。
- 记忆是明确保存的名字及最近 10 条事件，尚无向量检索或自动反思。
- 目前是一名 NPC 的单人文字原型，没有图形场景、移动、多人或联网功能。
- NPC 只能提出行动，金币、库存和生命由游戏规则检查后修改。

## 后面的学习顺序

1. 第一课：跑通当前原型，解释并修改一次购买。
2. 第二课：选定运行时模型服务或本地模型，让模型提出结构化回复和行动。
3. 第三课：加入对话上下文、记忆检索，测试角色一致性和错误处理。
4. 第四课：接入一个小型游戏场景，完成靠近 NPC、对话和交易。

Codex 是开发助手。接入运行时模型需要单独配置对应服务或本地模型；此项目目前不会进行模型请求。
后续仍保留规则模式，便于排查游戏规则和模型输出的问题。

## 验证

如果 `python` 命令可用：

```powershell
python -X utf8 -m unittest discover -s tests -v
```

若当前机器的 `python` 指向不可用的 Windows 占位程序，可以用已经找到的解释器：

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 -m unittest discover -s tests -v
```

测试使用临时存档，不修改你的 `data/save.json`。

