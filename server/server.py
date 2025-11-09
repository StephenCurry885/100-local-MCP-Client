import argparse
import sqlite3
import os
from typing import List, Any

try:
    # 官方 Python 实现
    from mcp.server.fastmcp import FastMCP
except Exception as e:
    raise SystemExit(
        "无法导入 FastMCP，请先安装 mcp：\n"
        "  pip install mcp\n"
        f"原始错误: {e}"
    )

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age INTEGER,
    profession TEXT
);
"""

def ensure_schema(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(DB_SCHEMA)
        conn.commit()
    finally:
        conn.close()

def run():
    parser = argparse.ArgumentParser(description="SQLite MCP Server (SSE or stdio)")
    parser.add_argument("--db", default="demo.db", help="SQLite database path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--transport", choices=["sse", "stdio"], default="sse")
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    ensure_schema(db_path)

    mcp = FastMCP("sqlite-demo")

    # 一个简单的“状态”；在闭包里用也可
    mcp.state = {}
    mcp.state["db_path"] = db_path

    @mcp.tool()
    def add_data(query: str) -> bool:
        """
        Execute a data-changing SQL (INSERT/UPDATE/DELETE).
        Returns True if success.
        """
        db = mcp.state["db_path"]
        conn = sqlite3.connect(db)
        try:
            conn.execute(query)
            conn.commit()
            return True
        except Exception as e:
            return False
        finally:
            conn.close()

    @mcp.tool()
    def read_data(query: str = "SELECT * FROM people") -> list:
        """
        Execute a SELECT query and return all rows.
        """
        db = mcp.state["db_path"]
        conn = sqlite3.connect(db)
        try:
            cur = conn.execute(query)
            rows = cur.fetchall()
            # 转成更易读的结构（list[dict]）
            cols = [d[0] for d in cur.description] if cur.description else []
            result = [dict(zip(cols, r)) for r in rows] if cols else rows
            return result
        finally:
            conn.close()

    print("✅ SQLite DB:", db_path)

    if args.transport == "stdio":
        print("🚀 MCP SQLite server running on stdio")
        mcp.run(transport="stdio")
    else:
        print(f"🚀 MCP SQLite server running on SSE (default localhost:8000/sse)")
        mcp.run(transport="sse")


if __name__ == "__main__":
    run()
