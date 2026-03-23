# Multi-Project Local Memory MCP Server

**[中文版](README.md)**

## Project Overview

**AI Memory MCP** is an MCP server that provides persistent project memory for Claude Code. It enables AI to remember your project development journey across sessions, including feature planning, bug fixes, development notes, and other critical information - acting as your "second brain" during development.

Unlike traditional note-taking tools, this project is specifically designed for AI interaction, structuring memory content with intelligent tagging and associative queries, allowing Claude to quickly understand project context and provide precise assistance.

---

## Key Features

### Content Categories

| Category | Purpose | Record Content |
|----------|---------|----------------|
| **Features** | Feature planning & tracking | Pending, in-progress, and completed features |
| **Fixes** | Bug fix records | Issue descriptions, severity levels, solutions |
| **Notes** | Development knowledge | Technical decisions, debugging processes, lessons learned |
| **Standards** | Project standards | Code conventions, naming conventions, architectural principles |

### Record Associations

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

## Quick Start (Docker)

### 1. Start the Service

```bash
# Start Docker container (default port 8000)
cd docker && ./manage.sh start

# Check status
./manage.sh status

# Stop service
./manage.sh stop
```

### 2. Claude Code Configuration

Edit your Claude Code configuration file and add the remote MCP server:

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

### 3. Verify Installation

Test in Claude Code:

```
Please use MCP [memory] to list all projects
```

---

## Use Cases

### Scenario 1: Development Convenience - Cross-Session Memory

**Problem**: You asked Claude to help write a user authentication module today, but three days later when you return to continue development, you've forgotten the implementation details.

**Traditional Approach**:
```
You: What method did I use for the user login I wrote before?
Claude: I don't know the previous content, you need to describe it again...
```

**Using Memory MCP**:
```
You: Continue developing the user authentication feature
Claude: [Query memory] I see you previously implemented user login with JWT,
        using RS256 algorithm, token stored in localStorage.
        Would you like to continue developing the password reset feature?
```

---

### Scenario 2: Context Management - Quick Onboarding

**Problem**: Taking over a project, there's a `handleAuth()` function in the code, but you don't know why it's written this way.

**Traditional Approach**:
```
You: Why does handleAuth check three conditions?
Claude: I'm not familiar with the project background, you need to explain...
```

**Using Memory MCP**:
```
You: The handleAuth function logic is complex
Claude: [Query memory] According to note_20260315_002,
        the three conditions are needed because:
        1. Handle token format differences during legacy user migration
        2. Compatible with mobile-specific authentication flow
        3. Prevent replay attacks
```

---

### Scenario 3: Multi-Project Information - Cross-Project Experience Reuse

**Problem**: You solved a tricky concurrency issue in Project A, and now Project B has a similar problem.

**Traditional Approach**:
```
You: I solved a similar problem in another project before... how exactly did I do it?
Claude: I cannot access information from other projects...
```

**Using Memory MCP**:
```
You: Project B has a concurrency conflict issue
Claude: [Cross-project query] I found you recorded a similar problem solution
        with tag "concurrency" in Project A:

        fix_20260310_001: Solved using optimistic locking + retry mechanism
        note_20260310_001: Detailed implementation code and notes recorded

        Would you like to apply the same solution to Project B?
```

---

### Scenario 4: Standards Enforcement - AI Automatically Follows Project Conventions

**Problem**: Your project has specific code standards (e.g., async functions must have `_async` suffix), but Claude doesn't know.

**Using Memory MCP**:
```
You: Write a user retrieval function
Claude: [Query standards] According to naming standards in standards,
        async functions need the _async suffix. I will create:

        def get_user_async(user_id: int) -> User:
            ...
```

---

### Scenario 5: Bug Fix Tracking - Associative Analysis

**Problem**: A certain bug keeps occurring, want to understand the fix history.

**Using Memory MCP**:
```
You: The login API is erroring again
Claude: [Query history] This problem has 3 fix records:

        fix_20260301_001: Token expiration issue (severity: high)
        fix_20260308_002: Timezone handling error (severity: medium)
        fix_20260315_003: Concurrent race condition (severity: critical)
                        ↑ Linked to feature_auth_002

        This error might be... Suggest checking...
```

---

## Data Storage & Management

### Directory Structure

All data is stored in the persistent volume within the server container:

```
/var/lib/project_memory_ai/
├── _metadata.json           # Global metadata (project list, statistics)
├── _stats.json              # API call statistics
│
├── project_a/               # ProjectA directory (project name)
│   ├── project.json         # Project data (features/fixes/standards metadata)
│   └── notes/               # Note content (independent md files)
│       ├── note_20260320_001.md
│       └── note_20260320_002.md
│
├── project_b/               # ProjectB directory
│   ├── project.json
│   └── notes/
│
└── .archived/               # Archived old data
    └── 20260320_123456_project_a.json
```

### Data Structure

#### project.json Format

```json
{
  "id": "proj_xxxxx",                    // Project UUID
  "info": {
    "name": "Project Name",              // Project display name
    "path": "/path/to/project",          // Project path
    "description": "Project description",
    "created_at": "2026-03-20T10:00:00",
    "updated_at": "2026-03-20T15:30:00",
    "tags": ["python", "web"]            // Project-level tags
  },
  "features": [                          // Feature list
    {
      "id": "feat_20260320_001",
      "description": "Implement user login",
      "status": "completed",             // pending/in_progress/completed
      "note_id": "note_20260320_001",    // Linked note
      "tags": ["auth", "frontend"],
      "created_at": "2026-03-20T10:00:00",
      "updated_at": "2026-03-20T14:00:00"
    }
  ],
  "fixes": [                             // Bug fix records
    {
      "id": "fix_20260320_001",
      "description": "Fix login API authentication error",
      "status": "completed",
      "severity": "critical",            // critical/high/medium/low
      "related_feature": "feat_20260320_001",  // Linked feature
      "note_id": "note_20260320_002",
      "tags": ["auth", "bug"],
      "created_at": "2026-03-20T12:00:00",
      "updated_at": "2026-03-20T13:00:00"
    }
  ],
  "notes": [                             // Note metadata (excluding content)
    {
      "id": "note_20260320_001",
      "description": "JWT login implementation plan",
      "tags": ["auth", "design"],
      "created_at": "2026-03-20T10:30:00",
      "updated_at": "2026-03-20T10:30:00"
    }
  ],
  "standards": [                         // Project standards
    {
      "id": "std_20260320_001",
      "description": "Naming conventions",
      "content": "Async functions must have _async suffix",
      "tags": ["naming", "style"],
      "created_at": "2026-03-20T09:00:00",
      "updated_at": "2026-03-20T09:00:00"
    }
  ],
  "tag_registry": {                      // Tag registry
    "auth": {
      "description": "Authentication related",
      "created_at": "2026-03-20T10:00:00",
      "usage_count": 5,
      "aliases": ["authentication"]
    }
  }
}
```

#### Note Content File

```
# notes/note_20260320_001.md
Login feature implemented using JWT...

- Algorithm: RS256
- Token storage: localStorage
- Validity period: 24 hours
```

### Data Management Features

| Feature | Description |
|---------|-------------|
| **Atomic Write** | Uses temp directory + rename to ensure data consistency |
| **Auto Archive** | Original data automatically backed up to `.archived/` during format migration/project rename |
| **TTL Cache** | 5-minute in-memory cache, reduces disk I/O |
| **Format Compatibility** | Supports old format (single file) and new format (directory + files) |
| **Tag Registration** | Tags must be registered before use, ensuring data quality |
| **Statistics Cleanup** | 30-day auto cleanup of expired statistics |

#### Archive Mechanism

```
# Archive directory purpose
.archived/ directory automatically backs up original data when data structure changes, ensuring data safety.

# Trigger scenarios
1. Project rename (project_rename)

# Archive naming format
.archived/{timestamp}_{original_filename}
Example: .archived/20260320_143052_myproject.json

# Important notes
- For archives triggered by rename: archive files are automatically deleted after successful project rename
- For manual cleanup: directly delete .archived/ directory contents
```

---

## Security Notice

> The current version does not implement data security management mechanisms for multi-user collaboration.

- Consider future updates

---

## Project Badges

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-green.svg)
![MCP](https://img.shields.io/badge/MCP-FastMCP-orange.svg)

## Contributing

Issues and Pull Requests are welcome!

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

MIT License
