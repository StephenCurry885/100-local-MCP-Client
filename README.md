# 🧠 100% 本地 MCP 客户端 + SQLite 服务器（LlamaIndex + Ollama + Qwen2.5 / DeepSeek-R1）

## 🧩 技术栈与原理说明

本项目实现了一个 **完全本地运行的 MCP（Model Context Protocol）客户端与服务器系统**。

---

### 🚀 技术栈

* **LlamaIndex**：用于构建基于 MCP 协议的智能体（FunctionAgent）。
* **Ollama**：提供本地大语言模型（推荐使用 `Qwen2.5:7b-instruct`，DeepSeek-R1 仅作兼容测试）。
* **LightningAI**：负责运行与托管工作流（可选，本地运行时未启用远程托管）。
* **SQLite**：轻量级本地数据库，用作演示性后端。
* **MCP Protocol**：实现 Host ↔ Client ↔ Server 的标准通信机制（本地 SSE）。

---

### ⚙️ 工作流原理

1. 用户输入自然语言查询；
2. 智能体（FunctionAgent）基于提示词与工具描述，**判断是否调用工具**；
3. MCP 客户端通过 SSE 连接到 MCP 服务器；
4. 服务器提供工具（如 `add_data` 与 `read_data`）并执行对应 SQL；
5. 执行结果回传给代理；
6. 模型结合上下文生成最终自然语言回复。

---

### 🧠 项目整体架构
![项目结构图](./images/结构图.png)
---

### 📘 实现步骤概览

| 步骤 | 内容                | 说明                                     |
| -- | ----------------- | -------------------------------------- |
| #1 | 构建 SQLite MCP 服务器 | 提供两个基础工具：添加数据 / 查询数据                   |
| #2 | 设置 LLM            | 使用 Ollama 调用本地模型（推荐 Qwen2.5:7b）        |
| #3 | 定义系统提示            | 指导代理如何判断与使用 MCP 工具                     |
| #4 | 定义代理              | 通过 LlamaIndex 封装 MCP 工具为 FunctionAgent |
| #5 | 定义代理交互            | 管理用户输入、流式事件和工具调用                       |
| #6 | 初始化 MCP 客户端与代理    | 加载工具并建立与服务器的 SSE 连接                    |
| #7 | 运行代理              | 用户交互 → 智能体决策 → 工具执行 → 自然语言输出           |

---

本项目展示了一个 **完全本地运行** 的最小可用示例：

* ✅ **MCP Server**：暴露数据库读写工具（基于 SQLite）
* ✅ **MCP Client**：封装为 LlamaIndex FunctionAgent
* ✅ **LLM**：通过 Ollama 调用本地模型（推荐 `qwen2.5:7b-instruct`）

整个流程在本机完成，无需外部 API。

---

## 📁 项目结构

```
local-mcp-demo/
├── README_zh.md                # 运行说明（本文件）
├── requirements.txt
├── server/
│   └── server.py               # #1 SQLite MCP 服务器（SSE / stdio 二选一）
└── client/
    ├── ollama_client.py        # #2~#7 MCP 客户端 + LlamaIndex 代理
    └── system_prompt.txt       # #3 系统提示词（定义工具使用策略）
```

---

## ⚙️ 环境准备

### 1️⃣ Python 环境

* Python **3.10+**
* 建议使用虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> 若国内网络较慢，可使用清华镜像：
>
> ```
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

---

### 2️⃣ 安装 Ollama（本地模型运行时）

1. 打开浏览器访问 [https://ollama.ai/download](https://ollama.ai/download)
2. 下载对应平台的安装包并安装（Windows/macOS/Linux）
3. 安装完成后，打开终端验证：

   ```bash
   ollama --version
   ```

   出现版本号即安装成功。

---

### 3️⃣ 拉取支持函数调用的模型（非常重要）

> ⚠️ **DeepSeek-R1 官方模型默认不支持 Function Calling**
> 即使是 `1.5b` / `7b` 版本，也可能无法让代理自动触发 MCP 工具调用。
> **建议使用 `qwen2.5:7b-instruct` 模型**（支持工具调用）。

```bash
# 推荐模型（支持 Function Calling）
ollama pull qwen2.5:7b-instruct
# 可替换为其他支持函数调用的模型：
# ollama pull llama3.1:8b-instruct
# ollama pull mistral:7b-instruct
```

可验证是否下载成功：

```bash
ollama list
```

> **注意：**
>
> * DeepSeek-R1:1.5b 虽然标称支持工具调用，但实际测试中并不稳定；
> * 7B 版本的 DeepSeek-R1 在相同条件下支持度更高，但资源占用也更大；
> * Qwen2.5:7b-instruct 模型支持最完善。

---

## 🚀 运行步骤

### 🧩 Step 1. 启动 SQLite MCP 服务器

`server/server.py` 实现了两个工具：

* `add_data(query: str) -> bool`：执行 `INSERT/UPDATE/DELETE`
* `read_data(query: str = "SELECT * FROM people") -> list`：执行 `SELECT`

#### 启动命令：

```bash
cd server
python server.py --db ../demo.db --transport sse
```

看到如下输出说明成功：

```
✅ SQLite DB: D:\Projects\MCP\demo.db
🚀 MCP SQLite server running on SSE http://127.0.0.1:8000/sse
```

> ✅ 启动后会自动创建示例表 `people(name, age, profession)`。

---

### 🧠 Step 2. 设置 LLM（Ollama）

`client/ollama_client.py` 默认模型：

```python
MODEL_NAME = "qwen2.5:7b-instruct"
```

如你下载了其他模型（例如 DeepSeek-R1），可自行修改。

---

### 📜 Step 3. 定义系统提示词（System Prompt）

`client/system_prompt.txt` 中定义了模型的**角色与工具使用规则**。
例如：

```
- 当用户提到“添加”/“插入”，调用 add_data；
- 当用户提到“查询”/“获取”，调用 read_data；
- 调用成功后请返回简洁结果，不重复调用；
```

> 删除该文件或清空内容会导致模型无法判断何时调用工具（详见下文“原理解释”）。

---

### 🤖 Step 4. 定义代理（FunctionAgent）

`client/ollama_client.py` 使用：

* `llama_index.tools.mcp` 将 MCP 工具包装为 LlamaIndex 原生工具；
* `FunctionAgent` 构建函数调用代理（function-calling agent）。

代理负责：

* 决定是否调用工具；
* 调用后整合结果；
* 生成自然语言回答。

---

### 💬 Step 5. 定义代理交互

`handle_user_message(...)`：

* 将用户输入传入代理；
* 打印工具调用事件（`[Event] ToolCall -> ...`）；
* 返回自然语言结果。

---

### ⚙️ Step 6. 初始化 MCP 客户端与代理

```python
mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
mcp_tool = McpToolSpec(client=mcp_client)
tools = await mcp_tool.to_tool_list_async()
agent = FunctionAgent(tools=tools, llm=llm, system_prompt=SYSTEM_PROMPT)
```

---

### 🧑‍💻 Step 7. 启动客户端与模型代理

另开一个终端，保持服务器运行：

```bash
cd client
source ../.venv/bin/activate     # Windows 用 .venv\Scripts\activate
python ollama_client.py
```

输入示例：

```
添加到数据库：INSERT INTO people(name, age, profession) VALUES('Rafael Nadal', 39, 'Tennis Player')
```

预期输出（部分示例）：

```
[Event] AgentInput
[Event] AgentStream
[Event] ToolCall -> add_data
[Event] AgentOutput
Agent: 成功添加 Rafael Nadal 到数据库。
```

再输入：

```
获取数据
```

或：

```
查询: SELECT * FROM people
```

输出：

```
[Event] ToolCall -> read_data
Agent: 查询到 1 条记录：
- Rafael Nadal（39 岁，Tennis Player）
```

---

## 🪞 常见问题与解决

| 问题                  | 原因                          | 解决方案                                       |
| ------------------- | --------------------------- | ------------------------------------------ |
| 模型不断调用工具            | 没有限制循环次数                    | 在 `FunctionAgent` 设置 `max_steps=3`         |
| 模型判定错误（不调用工具）       | system_prompt 被删除或模型不支持工具调用 | 恢复 system_prompt，或使用 `qwen2.5:7b-instruct` |
| 查询不到数据              | 工具没执行（只输出 JSON）             | 换支持 Function Calling 的模型                   |
| 报 “near '*'” SQL 错误 | 模型输出含全角符号 / 代码围栏            | 在服务器端清洗 SQL（见 `server.py` 中 `_clean_sql`）  |
| LLM 输出中文乱码          | Ollama 控制台字符集问题             | 使用 UTF-8 终端或 VSCode 终端                     |
| 显存不足                | 模型太大                        | 换小参数模型（如 qwen2.5:1.8b）                     |

---

## 💡 技术原理简述

* **MCP Server**：封装 SQLite 工具（add / read），暴露为标准 MCP 接口（SSE / stdio）。
* **MCP Client**：通过 `BasicMCPClient` 与服务器通信。
* **LlamaIndex Agent**：接收用户输入 → 调用本地 LLM → 由 LLM 判断是否、以及如何调用工具。
* **System Prompt**：指导模型决策（是工具调用的“说明书”）。
* **LLM（Ollama）**：执行推理，输出函数调用或自然语言。

> 如果删除 `system_prompt.txt`，模型将失去工具使用说明，因此无法再“自主判定”调用函数。

---

## 🧩 我们的改进与经验总结

* ✅ 自建 MCP Server 实现数据库访问；
* ✅ FunctionAgent 可根据自然语言意图自动选择 `add_data` / `read_data`；
* ✅ Qwen2.5:7b-instruct 是最佳兼容模型；
* ⚙️ DeepSeek-R1 1.5b/7b 在相同条件下无法稳定支持 Function Call；
* 🔁 加入调用步数上限与 prompt 限制，防止死循环；
* 🧱 未来可扩展更多工具（文件读写、知识库检索等）。

---

## 🧾 License

MIT License（自由使用、修改和扩展）



