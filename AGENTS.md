# Agent Interaction Guide: AgentMem CLI

This document is designed to help autonomous LLM agents (like Claude or GPT-4) interact with the `agentmemcli` tool effectively when the direct MCP SSE interface is unavailable.

## Core Concepts
The CLI acts as a pure Python bridge to a remote, multi-tenant Google Cloud Run server. It talks directly over HTTP/SSE.
The remote server operates on an **L1 / L2 Cache Architecture**:
- When you `add` a memory, it immediately hits the remote L1 disk cache (extremely fast, zero rate limits).
- Over time, those files "age out" and are "ingested" (uploaded) to Google Gemini's File API (the L2 cache).
- When you `search`, the remote backend automatically scoops up both the L1 active files and the L2 ingested files, dumping them into a `gemini-2.5-flash` context window to give you a perfectly accurate, conversational RAG answer.

## Usage Guidelines for Agents

### 1. Adding Memories
Always run this when you learn something new about the user, their environment, or their preferences:
`python cli.py add "The user prefers dark mode in their IDE."`
- **Important:** Do *not* run `sync` immediately after adding a memory. The backend automatically injects the fresh memory into the L1 active cache, so it is instantly searchable.

### 2. Searching Memories
When you need context, ask conversational queries:
`python cli.py search "What UI theme does the user prefer?"`
- The response will not be raw chunks of JSON. It will be a fully generated, conversational answer from the backend AI reading the files.

### 3. Editing/Deleting
If a preference changes, update the specific memory block:
`python cli.py update <uuid_returned_by_add> "The user prefers light mode now."`
`python cli.py delete <uuid_returned_by_add>`

### 4. Multi-Tenancy & Environments
If you receive a `400 API_KEY_INVALID` or similar error, verify the `.env` file:
- `AGENTMEM_TOKEN` is strictly tied to a single user's isolated memory database.
- If the global `GEMINI_API_KEY` on the server hits rate limits, you can inject a custom `AGENTMEM_CUSTOM_GEMINI_KEY` into the local `.env` file to bypass the server's quota limits.

### 5. The Dream Subsystem
`python cli.py dream`
- Run this if the user's logs are getting too messy. It triggers a heavy background reasoning model (`gemini-2.5-pro`) to deduplicate, strip filler, and permanently condense the memories into a highly compressed markdown file.
