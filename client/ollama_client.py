import asyncio
import os
import sys
from typing import Any

# ---- LlamaIndex (agent + Ollama) ----
try:
    from llama_index.core.agent.workflow import FunctionAgent
    from llama_index.core.workflow import Context
except Exception as e:
    raise SystemExit(
        "无法导入 LlamaIndex Agent，请先安装 llama-index：\n"
        "  pip install llama-index\n"
        f"原始错误: {e}"
    )

try:
    from llama_index.llms.ollama import Ollama
except Exception as e:
    raise SystemExit(
        "无法导入 LlamaIndex Ollama 适配器：\n"
        "  pip install llama-index-llms-ollama\n"
        f"原始错误: {e}"
    )

# MCP 客户端工具封装
try:
    from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
except Exception as e:
    raise SystemExit(
        "无法导入 LlamaIndex 的 MCP 工具封装：\n"
        "  pip install llama-index-tools-mcp\n"
        f"原始错误: {e}"
    )

# ---- 配置 ----
SERVER_SSE_URL = os.environ.get("MCP_SSE_URL", "http://127.0.0.1:8000/sse")
MODEL_NAME = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYSTEM_PROMPT_PATH = os.path.join(BASE_DIR, "system_prompt.txt")

with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read().strip()

def build_llm():
    # 直接使用本地 Ollama；如果你使用其他本地模型，改这里的 model 名字
    return Ollama(model=MODEL_NAME, request_timeout=120.0)

async def get_agent(mcp_tool: McpToolSpec, llm) -> FunctionAgent:
    tools = await mcp_tool.to_tool_list_async()

    kwargs = dict(
        name="Agent",
        description="agent that interacts with our database via MCP",
        tools=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
    )

    # 乐观尝试：限制最多 3 步（避免无限循环）
    try:
        kwargs["max_steps"] = 3
    except Exception:
        pass

    agent = FunctionAgent(**kwargs)
    print("[Debug] tools bound to agent:", [t.metadata.name for t in tools])

    return agent

async def handle_user_message(message_content: str, agent: FunctionAgent, agent_context: Context, verbose: bool = False) -> str:
    # 把用户消息交给代理；支持流式事件，打印工具调用信息
    handler = agent.run(message_content, ctx=agent_context)
    async for event in handler.stream_events():
        if verbose:
            et = type(event).__name__
            if hasattr(event, "tool_name"):
                print(f"[Event] ToolCall -> {getattr(event, 'tool_name', '')}")
            else:
                print(f"[Event] {et}")
    response = await handler
    return str(response)

async def main():
    print(f"🔗 Connecting MCP SSE server: {SERVER_SSE_URL}")
    mcp_client = BasicMCPClient(SERVER_SSE_URL)
    mcp_tool = McpToolSpec(client=mcp_client)

    llm = build_llm()
    agent = await get_agent(mcp_tool, llm)
    context = Context(agent)

    print("🤖 Agent is ready. Type your message (输入 'exit' 退出) ...")
    while True:
        try:
            msg = input("> ").strip()
            # 直接路由（避免模型做不必要的判定）
            if msg in {"获取数据", "查看全部", "查询全部"}:
                result = await mcp_tool.client.call_tool("read_data", {"query": "SELECT * FROM people"})
                print("\n[ToolResult/read_data] rows:", result, "\n")
                continue
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if msg.lower() in {"exit", "quit"}:
            break
        if not msg:
            continue
        resp = await handle_user_message(msg, agent, context, verbose=True)
        print("\nAgent:", resp, "\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
