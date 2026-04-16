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
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your Cloud Run deployment details:
   ```bash
   AGENTMEM_URL="https://agentmem-mcp-406450644140.us-central1.run.app"
   
   # Used for Admin commands:
   AGENTMEM_ADMIN_PASSWORD="<YOUR_ADMIN_PASSWORD>"
   
   # Used for standard User commands:
   AGENTMEM_TOKEN="<YOUR_TOKEN>"

   # (Optional) Provide your own Gemini API Key to bypass the Server's quota limits
   AGENTMEM_CUSTOM_GEMINI_KEY="<YOUR_GEMINI_API_KEY>"
   ```

## IMPORTANT: How Multi-Tenancy & Memory Works

When you run `python cli.py admin-provision`, the server creates a **brand new, totally isolated Semantic Search space** inside Google Gemini for the newly generated user ID.

The `AGENTMEM_TOKEN` you receive represents exactly one isolated user profile.
- Memories added under Token A **cannot** be searched by Token B.
- If you provision a new user and swap your `.env` file to use the new token, your memory bank will be completely blank and start over from scratch!
- If you lose your token but still know your user ID, an admin can rotate it via `admin-rotate`.

## Usage

### Providing your own Gemini API Key

If the server hits its Gemini quota limits, you can provide your own `AGENTMEM_CUSTOM_GEMINI_KEY` in the `.env` file.

If you ever change your key or want to move your existing memories to a brand new remote account, simply run:
```bash
python cli.py rebuild-corpus
```
*This command will link the new API key, link it to your user account, and perform a full `sync --force` to upload all your locally backed-up `.md` memories directly to the new index!*

### Admin Commands
Admin commands require the `AGENTMEM_ADMIN_PASSWORD` variable to be set in your `.env`.

- **Provision a new user:**
  ```bash
  python cli.py admin-provision
  ```
  *Generates a new user ID and Token. Copy the token into your `.env`.*

- **Rotate a user's token:**
  ```bash
  python cli.py admin-rotate <user_uuid>
  ```

- **Trigger dream sequence for all users:**
  ```bash
  python cli.py admin-dream-all
  ```

- **View or update the global Dream Prompt:**
  ```bash
  python cli.py admin-get-dream-prompt
  python cli.py admin-set-dream-prompt "You are an AI memory archivist..."
  ```

### User Commands
Standard user commands require `AGENTMEM_TOKEN` in your `.env` file. These execute directly over the MCP SSE pipeline.

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

- **Sync local memories with Gemini (L2 Cache):**
  ```bash
  python cli.py sync
  python cli.py sync --force
  ```

- **Trigger the Dream Subsystem:**
  ```bash
  python cli.py dream
  ```
