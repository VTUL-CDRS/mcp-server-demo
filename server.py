"""
MCP server for maps.jsonl — exposes historical map records as tools over HTTP/SSE.

Start:  python3 server.py
        python3 server.py --port 9000
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
import uvicorn

DATA_FILE = Path(__file__).parent / "maps.jsonl"

# ---------------------------------------------------------------------------
# Load data at startup
# ---------------------------------------------------------------------------

def load_records() -> list[dict]:
    records = []
    with DATA_FILE.open() as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


RECORDS: list[dict] = load_records()
RECORDS_BY_ID: dict[str, dict] = {r["id"]: r for r in RECORDS if "id" in r}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str_values(record: dict) -> str:
    return json.dumps(record).lower()


def _summarise(record: dict) -> dict:
    sr = record.get("sourceResource", {})
    titles = sr.get("title", [])
    dates = sr.get("date", [])
    creators = sr.get("creator", [])
    return {
        "id": record.get("id"),
        "title": titles[0] if titles else "Untitled",
        "creator": creators[0] if creators else None,
        "date": dates[0].get("displayDate") if dates else None,
        "subjects": [s.get("name") for s in sr.get("subject", []) if s.get("name")][:5],
        "location": [s.get("name") for s in sr.get("spatial", []) if s.get("name")][:3],
        "format": sr.get("format", [])[:2],
        "data_provider": record.get("dataProvider", {}).get("name"),
        "url": record.get("isShownAt"),
        "thumbnail": record.get("object"),
    }


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def search_maps(query: str, limit: int = 10) -> list[dict]:
    q = query.lower()
    results = []
    for record in RECORDS:
        if q in _str_values(record):
            results.append(_summarise(record))
            if len(results) >= limit:
                break
    return results


def get_map(record_id: str) -> dict | None:
    return RECORDS_BY_ID.get(record_id)


def filter_maps(
    state: str | None = None,
    subject: str | None = None,
    data_provider: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 10,
) -> list[dict]:
    results = []
    for record in RECORDS:
        sr = record.get("sourceResource", {})

        if state:
            spatial_text = " ".join(s.get("name", "") for s in sr.get("spatial", [])).lower()
            if state.lower() not in spatial_text and state.lower() not in json.dumps(record).lower():
                continue

        if subject:
            subject_names = " ".join(s.get("name", "") for s in sr.get("subject", [])).lower()
            if subject.lower() not in subject_names:
                continue

        if data_provider:
            if data_provider.lower() not in record.get("dataProvider", {}).get("name", "").lower():
                continue

        if date_from or date_to:
            dates = sr.get("date", [])
            if not dates:
                continue
            display = dates[0].get("displayDate", "") or dates[0].get("begin", "")
            m = re.search(r"\d{4}", display)
            if not m:
                continue
            year = int(m.group())
            if date_from and year < int(date_from):
                continue
            if date_to and year > int(date_to):
                continue

        results.append(_summarise(record))
        if len(results) >= limit:
            break
    return results


def list_maps(offset: int = 0, limit: int = 10) -> dict:
    page = RECORDS[offset: offset + limit]
    return {"total": len(RECORDS), "offset": offset, "limit": limit,
            "results": [_summarise(r) for r in page]}


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

server = Server("maps-server")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_maps",
            description="Full-text search across all map record fields.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_map",
            description="Retrieve the full record for a specific map by its id.",
            inputSchema={
                "type": "object",
                "properties": {"record_id": {"type": "string"}},
                "required": ["record_id"],
            },
        ),
        types.Tool(
            name="filter_maps",
            description="Filter maps by state, subject, data provider, and/or year range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {"type": "string"},
                    "subject": {"type": "string"},
                    "data_provider": {"type": "string"},
                    "date_from": {"type": "string"},
                    "date_to": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        types.Tool(
            name="list_maps",
            description="Page through all map records.",
            inputSchema={
                "type": "object",
                "properties": {
                    "offset": {"type": "integer", "default": 0},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    if name == "search_maps":
        out = search_maps(arguments["query"], arguments.get("limit", 10))
    elif name == "get_map":
        out = get_map(arguments["record_id"]) or "Record not found."
    elif name == "filter_maps":
        out = filter_maps(**{k: arguments.get(k) for k in
                             ("state", "subject", "data_provider", "date_from", "date_to")},
                          limit=arguments.get("limit", 10))
    elif name == "list_maps":
        out = list_maps(arguments.get("offset", 0), arguments.get("limit", 10))
    else:
        raise ValueError(f"Unknown tool: {name}")
    return [types.TextContent(type="text", text=json.dumps(out, indent=2))]


# ---------------------------------------------------------------------------
# HTTP / SSE app
# ---------------------------------------------------------------------------

sse = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


app = Starlette(routes=[
    Route("/sse", endpoint=handle_sse),
    Mount("/messages/", app=sse.handle_post_message),
])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"Maps MCP server → http://{args.host}:{args.port}/sse")
    uvicorn.run(app, host=args.host, port=args.port)
