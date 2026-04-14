# MCP Server Capstone Demo — Historical Maps via DPLA

A capstone demonstration of how to build and deploy a **Model Context Protocol (MCP) server** that exposes a real-world library/archive dataset as AI-accessible tools. This project uses historical map records sourced from the **Digital Public Library of America (DPLA)** to show how cultural heritage data can be made conversational through modern AI tooling.

```
AI Client (Cursor / Claude Desktop / …)
        │
        │  HTTP/SSE
        ▼
Docker Container (localhost:8000)
        │
        │  reads
        ▼
   maps.jsonl  ← DPLA metadata (1,000 historical map records)
```

---

## What This Demonstrates

- How to wrap a static archive dataset as a live MCP server
- How AI assistants can query, filter, and retrieve library records through natural language
- A reproducible, containerized setup suitable for any library or archival dataset

---

## Data Source & Attribution

Map records are sourced from the [Digital Public Library of America (DPLA)](https://dp.la), which makes its metadata openly available to the public.

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- An AI client that supports MCP (Cursor, Claude Desktop, Cline, Windsurf, etc.)

---

## Setup & Running the Server

### 1. Start the MCP server

```bash
docker compose up --build -d
```

The server will be available at `http://localhost:8000/sse`.

### 2. Stop the server

```bash
docker compose down
```

---

## Connect an AI Client

Add the following to your AI client's MCP configuration file, then reload the app:

```json
{
  "mcpServers": {
    "maps": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

| Client | Config file location |
|--------|----------------------|
| Cursor | `~/.cursor/mcp.json` |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Cline (VS Code) | Settings UI → MCP Servers |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |

Once connected, your AI client can invoke the tools below through natural language prompts.

---

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `search_maps` | Full-text search across all record fields |
| `get_map` | Fetch a complete record by its `id` |
| `filter_maps` | Filter by state, subject, data provider, or year range |
| `list_maps` | Page through all records in the dataset |

---

## Example Prompts

Try these in Cursor or Claude Desktop after connecting:

- *"Search for maps of Minnesota"*
- *"Find geological survey maps from the 1880s"*
- *"Filter maps from the University of Kentucky"*
- *"List the first 20 maps in the dataset"*
- *"Show me park maps from Minneapolis"*

---

## Project Structure

```
mcpdemo/
├── maps.jsonl           # DPLA-sourced map metadata (1,000 records)
├── server.py            # MCP server implementation (HTTP/SSE)
├── requirements.txt     # Python dependencies: mcp, uvicorn, starlette
├── Dockerfile           # Container definition
└── docker-compose.yml   # Service orchestration
```

> **Note:** Python dependencies listed in `requirements.txt` are installed inside the Docker container automatically. You do not need to run `pip install` locally unless you intend to run the server outside of Docker.

---

## Learn More

- [Model Context Protocol (MCP) Documentation](https://modelcontextprotocol.io)
- [Digital Public Library of America](https://dp.la)
- [DPLA API & Developer Resources](https://dp.la/info/developers/)
