# 100% 本地 MCP 客户端 + SQLite 服务器（LlamaIndex + Ollama + DeepSeek-R1）

> 按照你发来的教程思路，我补齐了可以运行的最小实现。所有组件均在本机运行：
> - **MCP Server**：使用 `mcp.server.fastmcp.FastMCP` 暴露两个工具（`add_data`/`read_data`），内部用 SQLite。
> - **MCP Client**：使用 `llama-index` 的 `FunctionAgent`，通过 `llama-index-tools-mcp` 的 `BasicMCPClient` 连接到本地 MCP Server（SSE）。
> - **LLM**：通过 **Ollama** 本地运行 **DeepSeek-R1**（你也可以改成其他本地模型）。

---

## 目录结构

```
local-mcp-demo/
├── README_zh.md
├── requirements.txt
├── server/
│   └── server.py
└── client/
    ├── ollama_client.py
    └── system_prompt.txt
```

---

## 先决条件

1) **Python 3.10+**
2) **Ollama**（本地 LLM 运行时）
3) **已拉取 DeepSeek-R1 模型**：

```bash
# 安装/更新 ollama 后执行（模型 tag 取决于你本地可用的版本，可用 `ollama list` 查看）
ollama pull deepseek-r1
# 或者指定尺寸的变体，例如：
# ollama pull deepseek-r1:7b
# ollama pull deepseek-r1:32b
```

> 若你本机没有 DeepSeek-R1，也可以把下文 client 的 `model="deepseek-r1"` 改成你已安装的本地模型名。

---

## 安装依赖

```bash
cd local-mcp-demo
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

若国内网络环境不佳，可设置镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 步骤 #1：启动 SQLite MCP 服务器

```bash
cd server
python server.py --db ../demo.db --host 127.0.0.1 --port 8000 --transport sse
# 看到 “🚀 MCP SQLite server running on SSE http://127.0.0.1:8000/sse” 表示成功
```

服务器暴露两个工具：
- **add_data(query: str) -> bool**：执行 `INSERT/UPDATE/DELETE` 等变更语句
- **read_data(query: str = "SELECT * FROM people") -> list**：执行 `SELECT` 并返回结果

> 初次启动会自动确保存在 `people(name, age, profession)` 表作为示例。

> **注意**：演示环境没有做 SQL 安全限制，请勿在生产环境内直接使用。

---

## 步骤 #2 ~ #7：运行 MCP 客户端（带代理与上下文）

另开一个终端：

```bash
cd client
python ollama_client.py
```

随后你可以输入类似：

```
添加到数据库：INSERT INTO people(name, age, profession) VALUES('Rafael Nadal', 39, 'Tennis Player')
```

再比如：

```
获取数据
```

或直接使用 SQL：

```
查询: SELECT * FROM people
```

> 代理会决定调用哪个工具（`add_data` 或 `read_data`），并把结果组织成自然语言回复。

---

## 常见问题

- **连不上 server**：确认 server 终端里显示在 `http://127.0.0.1:8000/sse` 监听；
  客户端里 `SERVER_SSE_URL` 要匹配这个地址。
- **模型推理慢/显存不足**：换更小的本地模型，或切到 CPU 推理（Ollama 支持）。
- **导入错误**（包名或 API 变动）：不同版本的 `mcp`/`llama-index` 可能存在轻微差异。
  我在代码中做了尽量“向后兼容”的导入与运行方式，并在关键处加了提示。

---

## License

MIT（示例代码，随意使用）
