# AgentMem CLI

A pure Python CLI tool designed to interact with the `AI Agentic Memory MCP Server` deployed on Google Cloud Run (or any other hosting provider). 

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/eladrave/agentmemcli.git
   cd agentmemcli
   ```

2. Setup virtual environment and install requirements:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install httpx mcp python-dotenv httpx-sse
   ```

3. Create a `.env` file with your Cloud Run deployment details:
   ```bash
   AGENTMEM_URL="https://agentmem-mcp-406450644140.us-central1.run.app"
   
   # Used for Admin commands:
   AGENTMEM_ADMIN_PASSWORD="<YOUR_ADMIN_PASSWORD>"
   
   # Used for standard User commands (will be generated):
   AGENTMEM_TOKEN="<YOUR_TOKEN>"
   ```

## Usage

### Admin Commands
Admin commands require the `AGENTMEM_ADMIN_PASSWORD` variable to be set in your `.env`. Otherwise, you will receive a `not allowed` error.

- **Provision a new user:**
  ```bash
  python cli.py admin-provision
  ```
  *This will generate and output a new User ID and Token. Copy the token into your `.env` as `AGENTMEM_TOKEN`.*

- **Rotate a user's token:**
  ```bash
  python cli.py admin-rotate <user_uuid>
  ```

- **Trigger dream sequence for all users:**
  ```bash
  python cli.py admin-dream-all
  ```

### User Commands
Standard user commands require the `AGENTMEM_TOKEN` to be set in your `.env` file. These commands utilize the MCP SSE endpoints over the wire!

- **Add a memory:**
  ```bash
  python cli.py add "I like using dark mode."
  ```

- **Search memories:**
  ```bash
  python cli.py search "dark mode"
  ```

- **Update a memory:**
  ```bash
  python cli.py update <memory_uuid> "I prefer dark mode, but light mode is okay during the day."
  ```

- **Delete a memory:**
  ```bash
  python cli.py delete <memory_uuid>
  ```

- **Sync local memories with Gemini Corpus:**
  ```bash
  python cli.py sync
  python cli.py sync --force
  ```

- **Trigger the Dream Subsystem for your specific token:**
  ```bash
  python cli.py dream
  ```
