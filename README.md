# AI Memory MCP - Project Local Memory Server

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-orange.svg)](https://modelcontextprotocol.io/)
[![Version](https://img.shields.io/badge/version-v1.0.0-brightgreen.svg)](VERSION)

**[中文版](README_CN.md)**

---

## Project Overview

**AI Memory MCP** is an MCP server specifically designed for Claude Code to provide persistent project memory. It enables AI to remember your project development journey across sessions, including feature planning, bug fixes, development notes, code standards, and other critical information - acting as your "second brain" during development.

### Key Features

| Feature | Description |
|---------|-------------|
| **Structured Memory** | Categorizes project info into Features, Fixes, Notes, and Standards |
| **Smart Associations** | Links between entries to build complete project knowledge graph |
| **Tag System** | Powerful tag management for cross-dimensional queries and experience reuse |
| **Three-Tier Architecture** | Separated MCP Server, FastAPI Server, and Business Server for easy scaling |
| **Fully Async** | High-performance async architecture supporting concurrent access |
| **Docker Deployment** | One-click containerized deployment with persistent data storage |

---

## System Architecture

The project uses a three-tier architecture with clear responsibilities:

```
┌─────────────────┐     ┌─────────────────┐
│   MCP Clients   │     │   Web Clients   │
│  (Claude Code)  │     │   (Browser)     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│   MCP Server    │     │  FastAPI Server │
│   (mcp_server)  │     │   (rest_api)    │
│  - SSE/HTTP     │     │  - RESTful API  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌─────────────────────┐
         │   Business Server   │
         │   (business)        │
         │  - Core business    │
         │  - Data storage     │
         │  - Tag system       │
         └─────────────────────┘
```

### Directory Structure

```
ai_memory_mcp/
├── src/
│   ├── business/      # Business logic layer (core)
│   ├── mcp_server/    # MCP server layer
│   ├── rest_api/      # FastAPI REST API layer
│   ├── clients/       # Client modules
│   └── common/        # Common modules
├── docker/            # Docker deployment files
├── test/              # Test files (unit/integration/e2e/performance)
├── scripts/           # Utility scripts
├── examples/          # Example code (agents/skills)
├── docs/              # Documentation
├── config/            # Configuration files
├── scripts/           # Utility scripts
│   ├── start_mcp.py         # MCP startup script
│   ├── start_business.py    # Business service startup script
│   └── start_fastapi.py     # FastAPI startup script
```

---

## Quick Start

### Method 1: Docker Deployment (Recommended)

```bash
# 1. Enter Docker directory
cd docker

# 2. Start service (default port 8000)
./manage.sh start

# 3. Check status
./manage.sh status

# 4. Stop service
./manage.sh stop

# 5. View logs
docker logs -f ai-memory-mcp
```

### Method 2: Local Development

```bash
# 1. Create Conda environment
conda create -n ai_memory_mcp python=3.12
conda activate ai_memory_mcp

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start business service
python scripts/start_business.py

# 4. Start MCP server (new terminal)
python scripts/start_mcp.py

# 5. Start FastAPI service (optional, new terminal)
python scripts/start_fastapi.py
```

### Claude Code Configuration

Edit Claude Code configuration file and add MCP server:

```json
{
  "mcpServers": {
    "memory": {
      "url": "http://localhost:8000/mcp",
      "type": "http"
    }
  }
}
```

### Verify Installation

Test in Claude Code:

```
Please use MCP [memory] to list all projects
```

---

## Core Features

### Memory Content Categories

| Category | Purpose | Record Content |
|----------|---------|----------------|
| **Features** | Feature planning & tracking | Pending, in-progress, and completed features |
| **Fixes** | Bug fix records | Issue descriptions, severity levels, solutions |
| **Notes** | Development knowledge | Technical decisions, debugging processes, lessons learned |
| **Standards** | Project standards | Code conventions, naming conventions, architectural principles |

### Memory Association System

```
┌─────────────────┐
│   Features      │ ─┐
│   (Feature List)│  │ Associated
└─────────────────┘  │
                     ├─→ Notes (Notes)
┌─────────────────┐  │    (Record development process/decision rationale)
│   Fixes         │ ─┘
│   (Bug Fixes)   │
└─────────────────┘
```

- **Feature ↔ Note**: Features can link to related notes (design decisions, reference docs)
- **Fix ↔ Note**: Bug fixes can link to troubleshooting processes
- **Fix ↔ Feature**: Bug fixes can link to specific feature modules
- **Tag System**: All entries support multi-tagging for cross-dimensional queries

---

## MCP Tools List

### Project Management

| Tool | Function |
|------|----------|
| `project_register` | Register new project |
| `project_list` | List all projects |
| `project_get` | Get project info or query entries |
| `project_rename` | Rename project |
| `project_remove` | Archive or delete project |

### Entry Management

| Tool | Function |
|------|----------|
| `project_add` | Add new entry (features/fixes/notes/standards) |
| `project_update` | Update entry content |
| `project_delete` | Delete entry |

### Tag System

| Tool | Function |
|------|----------|
| `tag_register` | Register new tag (define semantics) |
| `tag_update` | Update tag semantics |
| `tag_delete` | Delete tag |
| `tag_merge` | Merge tags |
| `project_tags_info` | Query tag information |
| `project_item_tag_manage` | Manage entry tags |

### Query Features

- Filter by status (pending/in_progress/completed)
- Filter by severity (critical/high/medium/low)
- Filter by tags
- Filter by creation/update time
- Regex match on summary
- Paginated queries

---

## Use Case Examples

### Scenario 1: Continue Development Across Sessions

**Context**: Implemented API authentication middleware last week, continuing development today.

```
You: Continue improving API authentication, add refresh token mechanism

Claude: [Query memory] Found project records:
        - feat_20260401: JWT authentication implemented using FastAPI Security
        - note_20260401: Key stored at /secrets/jwt_key.pem
        - standards_20260315: Auth-related functions need @auth_required decorator

        Based on existing implementation, here's the refresh token design...
```

### Scenario 2: Reuse Solved Experience

**Context**: New project encounters a Docker networking issue you solved before.

```
You: Services can't communicate after Docker Compose starts

Claude: [Cross-project query] Found similar issue in project web-dashboard:
        - fix_20260310: Docker network communication failure
        - Solution: Use custom network network_mode: bridge
        - note_20260310: Need to explicitly declare networks in docker-compose.yml

        Generated same configuration for new project...
```

### Scenario 3: Follow Project Conventions

**Context**: Make AI generate code following team standards.

```
You: Implement user order query endpoint

Claude: [Query standards] According to project standards:
        - All endpoints return wrapped Result<T> format
        - Pagination uses PageRequest(page, size)
        - Async functions must include _async suffix

        Generated code:

        async def get_orders_async(req: PageRequest) -> Result[List[Order]]:
            ...
```

---

## Data Storage

### Storage Location

Docker Mode: Persistent volume inside container at `/var/lib/project_memory_ai/`

Local Mode: `data/` directory in project root

### Data Directory Structure

```
/var/lib/project_memory_ai/
├── _metadata.json              # Global metadata (project list, statistics)
├── _stats.json                 # API call statistics
│
├── project_a/                  # ProjectA directory (project name)
│   ├── _project.json           # Project metadata (id, name, info, _version)
│   ├── _tags.json              # Tag registry (tag -> description, aliases)
│   ├── _group_configs.json     # Group configurations (optional)
│   │
│   ├── features/               # Features group
│   │   ├── _index.json         # Feature index (id -> summary, status, tags...)
│   │   ├── feat_20260408_001.json  # Feature details
│   │   └── feat_20260408_002.json
│   │
│   ├── fixes/                  # Bug fixes group (same structure as features)
│   ├── notes/                  # Notes group (same structure as features)
│   └── standards/              # Standards group (same structure as features)
│
├── project_b/                  # ProjectB directory
│
└── .archived/                  # Archived projects
    ├── 20260408_123456_project_a.tar.gz
    └── 20260408_123456_project_a.meta.json
```

---

## Development Guide

### Requirements

- Python 3.12+
- Conda (recommended)
- Docker (for containerized deployment)

### Running Tests

```bash
# Use test script
./scripts/run_tests.sh

# Or manually run
pytest test/ -v --cov=src/business --cov-report=html
```

### Code Standards

- Use `black` for code formatting
- Use `ruff` for code linting
- Use `mypy` for type checking

---

## Project Status

| Project | Version | Dev Branch | Main Branch |
|---------|---------|------------|-------------|
| ai_memory_mcp | v1.0.0 | dev | main |

### Development Statistics

- Features: 63
- Notes: 125
- Fixes: 24
- Standards: 18
- Tags: 59

---

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## Related Links

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Claude Code Documentation](https://code.anthropic.com/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
