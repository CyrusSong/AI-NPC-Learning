# AI NPC 学习项目：一个记得你的店主

从一个小而完整的文字游戏开始：告诉店主名字，购买药品，使用药品，退出后再次回来。

**现在有两个模式：第一课的规则 NPC，以及第二课的 DeepSeek NPC。**
默认使用规则模式，不调用模型；加上 `--npc deepseek` 后使用大模型理解输入并提出行动。
第二课的阅读步骤见 `LESSON_02.md`，第一课内容仍然保留。

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

## 第二课：DeepSeek 模式

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\AI-NPC-Learning\start.ps1" --npc deepseek --trace
```

在真实交互终端启动。若没有设置 `DEEPSEEK_API_KEY` 环境变量，程序会提示隐藏输入密钥。
密钥不会写入源码、存档或追踪输出；不要把它作为命令行参数或发到聊天里。
本机启动提示中的隐藏输入可能不显示字符，粘贴后直接回车。

默认模型是 `deepseek-flash`，依据 2026-10-08 查阅的 DeepSeek 官方示例。
可以用 `--model 模型名称` 或 `DEEPSEEK_MODEL` 环境变量指定你账户使用的模型。
每条 NPC 对话通常调用一次接口；仅空响应或空行动参数会自动重试一次，因此每轮最多两次请求。
重试可能增加等待时间和接口费用；状态、帮助、保存、退出不调用模型。

第二课默认存档为 `data/lesson02.json`，第一课仍用 `data/save.json`。
相对 `--save-file` 路径以项目目录为起点，从其他文件夹启动也不会把存档写到那个文件夹。
当前保存的是名字和最近事件；最近六轮对话只在本次进程中保存，退出后不会保留。

如果要让模型读取第一课存档，可以明确加上 `--save-file data/save.json`，之后也会更新它。

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
| `deepseek_npc.py` | 怎样构建模型输入、读取工具调用参数、校验 JSON 并返回 Proposal？ |
| `game.py` | 谁检查金币和库存，谁真正修改游戏状态？ |
| `storage.py` | 名字、物品和事件怎样保存，并在下次启动时恢复？ |
| `LESSON_01.md` | 第一课的具体阅读步骤、预测题和练习 |
| `LESSON_02.md` | 第二课的模型接入、追踪观察和练习 |
| `tests/test_game.py` | 哪些情况必须保持状态不变？ |

建议顺序：先试玩，再读 `LESSON_01.md`，之后沿着一次购买的调用路径读源码。
不用先读懂所有存档校验和自动化测试。

## 当前能力边界

- 规则模式通过少量文字规则识别输入；DeepSeek 模式使用大模型理解自然表达。
- 模型通过 `submit_proposal` 工具提交行动参数，游戏在本地校验后执行。
- 普通对话和名字登记成功后的回复由模型生成，可以保留澄清问题；交易和用药的最终回复由游戏规则给出。
- 记忆是明确保存的名字及最近 10 条事件，尚无向量检索或自动反思。
- 目前是一名 NPC 的单人文字原型，没有图形场景、移动、多人或联网功能。
- NPC 只能提出行动，金币、库存和生命由游戏规则检查后修改。

## 后面的学习顺序

1. 第一课：跑通当前原型，解释并修改一次购买。
2. 第二课：选定运行时模型服务或本地模型，让模型提出结构化回复和行动。
3. 第三课：加入对话上下文、记忆检索，测试角色一致性和错误处理。
4. 第四课：接入一个小型游戏场景，完成靠近 NPC、对话和交易。

Codex 是开发助手。模型模式使用你配置的 DeepSeek API；默认的规则模式继续可用。
模型接入代码有模拟响应测试，真实 API 是否可用仍需本机密钥和账户验证。

## 空回复修正

旧版使用 JSON Output 从 `message.content` 读取行动；DeepSeek 官方文档提示该模式偶尔会返回空内容。
现在使用 Tool Calls 从 `message.tool_calls[0].function.arguments` 读取行动；此时 `content=null` 可以是正常响应。
工具调用仍需要本地检查，不能直接修改金币或库存。

用 `--trace` 启动后，`[接口]` 会显示请求次数、`finish_reason`、正文字符数、工具调用数量和参数字符数。
正常响应通常是 `finish_reason=tool_calls`、`tool_calls=1`。连续两次空输出会停止该轮，状态不变。
网络错误、截断回复、无效参数及多个工具调用不会自动重试。追踪输出不包含密钥或原始接口响应。
修改源码后，需要先退出旧进程，再用上面的第二课命令启动，才能加载更新。

## 验证

如果 `python` 命令可用：

```powershell
python -X utf8 -m unittest discover -s tests -v
```

若当前机器的 `python` 指向不可用的 Windows 占位程序，可以用已经找到的解释器：

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -X utf8 -m unittest discover -s tests -v
```

测试使用临时存档，不修改你的 `data/save.json` 或 `data/lesson02.json`。
