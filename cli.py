import argparse
import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get("AGENTMEM_URL", "").rstrip("/")
ADMIN_PASS = os.environ.get("AGENTMEM_ADMIN_PASSWORD")
TOKEN = os.environ.get("AGENTMEM_TOKEN")

# Increase timeouts heavily because Gemini API calls over Cloud Run can take a moment
client_timeout = httpx.Timeout(30.0)

def check_admin():
    if not ADMIN_PASS:
        print("not allowed: AGENTMEM_ADMIN_PASSWORD is not set in .env")
        exit(1)

def check_token():
    if not TOKEN:
        print("Error: AGENTMEM_TOKEN is not set in .env. Run 'python cli.py admin-provision' to get one.")
        exit(1)

async def _call_mcp_tool(tool_name: str, args: dict):
    from mcp.client.sse import sse_client
    from mcp import ClientSession

    url = f"{URL}/mcp/sse"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    try:
        async with sse_client(url, headers=headers) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
                if result.content and len(result.content) > 0:
                    return result.content[0].text
                return "Success"
    except Exception as e:
        print(f"MCP Connection Error: {e}")
        exit(1)

async def do_admin_provision():
    check_admin()
    print("Provisioning... This might take a few seconds as it connects to Gemini.")
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        res = await client.post(f"{URL}/admin/users", headers={"X-Admin-Password": ADMIN_PASS})
        if res.status_code == 200:
            data = res.json()
            print(f"User provisioned successfully!")
            print(f"User ID: {data['user_id']}")
            print(f"Token: {data['token']}")
            print("\nUpdate your .env file with:")
            print(f"AGENTMEM_TOKEN=\"{data['token']}\"")
        else:
            print(f"Error {res.status_code}: {res.text}")

async def do_admin_rotate(user_id):
    check_admin()
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        res = await client.post(f"{URL}/admin/users/{user_id}/rotate", headers={"X-Admin-Password": ADMIN_PASS})
        if res.status_code == 200:
            data = res.json()
            print(f"User token rotated successfully!")
            print(f"New Token: {data['token']}")
            print("\nUpdate your .env file with:")
            print(f"AGENTMEM_TOKEN=\"{data['token']}\"")
        else:
            print(f"Error {res.status_code}: {res.text}")

async def do_admin_dream_all():
    check_admin()
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        res = await client.post(f"{URL}/admin/dream_all", headers={"X-Admin-Password": ADMIN_PASS})
        if res.status_code == 202:
            print("Dream sequence initiated for all users in the background.")
        else:
            print(f"Error {res.status_code}: {res.text}")

async def do_dream():
    check_token()
    print("Dream sequence started... This may take up to a minute.")
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(f"{URL}/api/dream", headers={"Authorization": f"Bearer {TOKEN}"})
        if res.status_code == 200:
            data = res.json()
            print(f"Dream completed successfully for date {data.get('target_date')}.")
        else:
            print(f"Error {res.status_code}: {res.text}")

async def do_add(content):
    check_token()
    res = await _call_mcp_tool("add_memory", {"content": content})
    print(res)

async def do_search(query):
    check_token()
    res = await _call_mcp_tool("search_memories", {"query": query})
    print(res)

async def do_update(memory_id, content):
    check_token()
    res = await _call_mcp_tool("update_memory", {"memory_id": memory_id, "new_content": content})
    print(res)

async def do_delete(memory_id):
    check_token()
    res = await _call_mcp_tool("delete_memory", {"memory_id": memory_id})
    print(res)

async def do_sync(force):
    check_token()
    res = await _call_mcp_tool("sync_memories", {"force_sync": force})
    print(res)

def main():
    if not URL:
        print("Error: AGENTMEM_URL is not set in .env")
        exit(1)

    parser = argparse.ArgumentParser(description="AI Agentic Memory MCP CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Admin commands
    parser_admin_prov = subparsers.add_parser("admin-provision", help="Provision a new user")
    parser_admin_rot = subparsers.add_parser("admin-rotate", help="Rotate a user's token")
    parser_admin_rot.add_argument("user_id", type=str, help="The UUID of the user")
    parser_admin_dream = subparsers.add_parser("admin-dream-all", help="Trigger dream sequence for all users")

    # User commands
    parser_dream = subparsers.add_parser("dream", help="Trigger dream sequence for your user")

    # MCP Tool commands
    parser_add = subparsers.add_parser("add", help="Add a new memory")
    parser_add.add_argument("content", type=str, help="Memory content")

    parser_search = subparsers.add_parser("search", help="Search memories semantically")
    parser_search.add_argument("query", type=str, help="Search query")

    parser_update = subparsers.add_parser("update", help="Update an existing memory")
    parser_update.add_argument("memory_id", type=str, help="Memory UUID")
    parser_update.add_argument("content", type=str, help="New memory content")

    parser_delete = subparsers.add_parser("delete", help="Delete a memory")
    parser_delete.add_argument("memory_id", type=str, help="Memory UUID")

    parser_sync = subparsers.add_parser("sync", help="Sync local files to Gemini corpus")
    parser_sync.add_argument("--force", action="store_true", help="Force full resync (overwrite)")

    args = parser.parse_args()

    loop = asyncio.get_event_loop()

    if args.command == "admin-provision":
        loop.run_until_complete(do_admin_provision())
    elif args.command == "admin-rotate":
        loop.run_until_complete(do_admin_rotate(args.user_id))
    elif args.command == "admin-dream-all":
        loop.run_until_complete(do_admin_dream_all())
    elif args.command == "dream":
        loop.run_until_complete(do_dream())
    elif args.command == "add":
        loop.run_until_complete(do_add(args.content))
    elif args.command == "search":
        loop.run_until_complete(do_search(args.query))
    elif args.command == "update":
        loop.run_until_complete(do_update(args.memory_id, args.content))
    elif args.command == "delete":
        loop.run_until_complete(do_delete(args.memory_id))
    elif args.command == "sync":
        loop.run_until_complete(do_sync(args.force))

if __name__ == "__main__":
    main()
