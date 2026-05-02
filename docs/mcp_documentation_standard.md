# Skill: Standardizing MCP Project Documentation

This guide provides a reusable template and set of best practices for creating professional, developer-friendly READMEs for Model Context Protocol (MCP) servers.

## 📋 The "Golden Order" for MCP READMEs

1.  **Title & Pitch**: What is it? (1-2 sentences).
2.  **Folder Structure**: How is the source organized?
3.  **Architecture**: What is the data flow? (Entry -> Tools -> Services -> API).
4.  **Tools Reference**: Detailed list of categorized tools with descriptions.
5.  **Technology Stack**: Key libraries and Python versions.
6.  **Setup & Run**: Actionable install and execution commands.
7.  **Permissions/Security**: Explicit requirements for API access (e.g., Azure Scopes).
8.  **Known Limitations**: Latency, stubs, and edge cases.

## 🇧🇷 Idioma e Gramática (PT-BR)

- **Localização**: O README deve ser escrito obrigatoriamente em **Português (Brasil)**.
- **Correção**: Seguir rigorosamente as normas da gramática pt-br, incluindo o uso correto de acentuação, pontuação e concordância.
- **Termos Técnicos**: Manter termos técnicos universais (ex: *throttling*, *backoff*, *endpoint*) quando não houver tradução direta adequada, mas explicar o contexto.

---

## 📝 Markdown Template

```markdown
# [Project Name]

[One sentence description of what the MCP server does.] [One sentence on who it is for and its primary benefit.]

## 📂 Folder Structure

```text
[project-name]/
├── [package_name]/      # Core logic
│   ├── api/             # API client abstraction
│   ├── tools/           # MCP tool definitions
│   ├── services/        # Business logic
│   ├── schemas/         # Data models (Pydantic)
│   └── server.py        # Entry point
├── tests/               # Test suite
└── pyproject.toml       # Dependencies
```

## 🏗️ Architecture

The project follows a layered architecture:
- **Layer 1 (Interface)**: MCP tools defined in `tools/` using FastMCP.
- **Layer 2 (Logic)**: Services in `services/` orchestrating complex actions.
- **Layer 3 (Integration)**: Clean API wrappers in `api/` (using httpx/resilience).

## 🛠️ Tools Reference

### [Category 1]
- **`tool_name`**: [Description starting with a verb]. **Use this when...**
- **`another_tool`**: [Description].

### [Category 2]
- ...

## 💻 Technology Stack

- **Python 3.11+**
- **FastMCP** (Server Framework)
- **httpx** (Async HTTP)
- **Pydantic v2** (Validation)
- [Add project-specific libs]

## 🚀 Setup

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

### Running
```bash
python -m [package_name].server
```

## 🔑 Permissions

| Permission | Purpose |
|---|---|
| [Scope Name] | [Why it is needed] |

---

## ⚠️ Known Limitations
- [Limitation 1]
- [Limitation 2]
```

---

## 💡 Best Practices for Tools Descriptions

- **Action-Oriented**: Start with a strong verb (Resolve, List, Diagnose, Search).
- **Contextual Hints**: Include "Use this first" or "Use when troubleshooting X" for the LLM's benefit.
- **Flow Instructions**: Mention which tool should be called next (e.g., "Take the ID from X and pass it to Y").
- **Transparency**: Clearly mark incomplete features as `[STUB]`.
