import argparse
import asyncio
import os
import httpx
from dotenv import dotenv_values
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("agentmemcli")

# Strictly load only from the local .env file, ignoring the system environment
env_config = dotenv_values(".env")

URL = env_config.get("AGENTMEM_URL", "").rstrip("/")
ADMIN_PASS = env_config.get("AGENTMEM_ADMIN_PASSWORD")
TOKEN = env_config.get("AGENTMEM_TOKEN")
# Namespace the custom key to avoid generic GEMINI_API_KEY leaks from bash profiles
GEMINI_KEY = env_config.get("AGENTMEM_CUSTOM_GEMINI_KEY")

logger.debug(f"Loaded URL: {URL}")
logger.debug(f"Loaded Token: {'***' + TOKEN[-4:] if TOKEN else None}")
logger.debug(f"Loaded Custom Gemini Key: {'***' + GEMINI_KEY[-4:] if GEMINI_KEY else 'None'}")

if GEMINI_KEY:
    logger.warning("You are using a custom AGENTMEM_CUSTOM_GEMINI_KEY.")
    logger.warning("If this key is different from the one used to provision your account, searches will fail.")
    logger.warning("Run 'python cli.py rebuild-corpus' to migrate your data to the new key if necessary.")

client_timeout = httpx.Timeout(30.0)

def check_admin():
    if not ADMIN_PASS:
        logger.error("not allowed: AGENTMEM_ADMIN_PASSWORD is not set in .env")
        exit(1)

def check_token():
    if not TOKEN:
        logger.error("AGENTMEM_TOKEN is not set in .env. Run 'python cli.py admin-provision' to get one.")
        exit(1)

def get_headers(is_admin=False):
    headers = {}
    if is_admin:
        headers["X-Admin-Password"] = ADMIN_PASS
    else:
        headers["Authorization"] = f"Bearer {TOKEN}"
        
    if GEMINI_KEY:
        headers["X-Gemini-Api-Key"] = GEMINI_KEY
        
    logger.debug(f"Prepared Request Headers: {headers.keys()}")
    return headers

async def _call_mcp_tool(tool_name: str, args: dict):
    from mcp.client.sse import sse_client
    from mcp import ClientSession

    url = f"{URL}/mcp/sse"
    headers = get_headers()
    
    logger.info(f"Initiating MCP SSE connection to {url}")
    logger.debug(f"Calling Tool: {tool_name} with Args: {args}")
    
    try:
        async with sse_client(url, headers=headers) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                logger.debug("Initializing MCP Session...")
                await session.initialize()
                logger.debug(f"Executing Tool Call: {tool_name}")
                result = await session.call_tool(tool_name, args)
                logger.debug(f"Received Tool Response: {result}")
                
                if result.content and len(result.content) > 0:
                    return result.content[0].text
                return "Success"
    except Exception as e:
        logger.error(f"MCP Connection Error: {e}", exc_info=True)
        exit(1)

async def do_admin_provision():
    check_admin()
    logger.info("Provisioning... This might take a few seconds.")
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        res = await client.post(f"{URL}/admin/users", headers=get_headers(is_admin=True))
        if res.status_code == 200:
            data = res.json()
            print(f"User provisioned successfully!")
            print(f"User ID: {data['user_id']}")
            print(f"Token: {data['token']}")
            print("\nUpdate your .env file with:")
            print(f"AGENTMEM_TOKEN=\"{data['token']}\"")
        else:
            logger.error(f"Error {res.status_code}: {res.text}")

async def do_admin_rotate(user_id):
    check_admin()
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        res = await client.post(f"{URL}/admin/users/{user_id}/rotate", headers=get_headers(is_admin=True))
        if res.status_code == 200:
            data = res.json()
            print(f"User token rotated successfully!")
            print(f"New Token: {data['token']}")
            print("\nUpdate your .env file with:")
            print(f"AGENTMEM_TOKEN=\"{data['token']}\"")
        else:
            logger.error(f"Error {res.status_code}: {res.text}")

async def do_admin_dream_all():
    check_admin()
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        res = await client.post(f"{URL}/admin/dream_all", headers=get_headers(is_admin=True))
        if res.status_code == 202:
            print("Dream sequence initiated for all users in the background.")
        else:
            logger.error(f"Error {res.status_code}: {res.text}")

async def do_admin_get_dream_prompt():
    check_admin()
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        res = await client.get(f"{URL}/admin/dream_prompt", headers=get_headers(is_admin=True))
        if res.status_code == 200:
            print(res.json()["prompt"])
        else:
            logger.error(f"Error {res.status_code}: {res.text}")

async def do_admin_set_dream_prompt(prompt_text):
    check_admin()
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        res = await client.post(f"{URL}/admin/dream_prompt", headers=get_headers(is_admin=True), json={"prompt": prompt_text})
        if res.status_code == 200:
            print("Dream prompt updated successfully.")
        else:
            logger.error(f"Error {res.status_code}: {res.text}")

async def do_dream():
    check_token()
    logger.info("Dream sequence started... This may take up to a minute.")
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(f"{URL}/api/dream", headers=get_headers())
        if res.status_code == 200:
            data = res.json()
            print(f"Dream completed successfully for date {data.get('target_date')}.")
        else:
            logger.error(f"Error {res.status_code}: {res.text}")

async def do_rebuild_corpus():
    check_token()
    if not GEMINI_KEY:
        logger.error("AGENTMEM_CUSTOM_GEMINI_KEY is not set in your .env file. You must set this to rebuild your corpus on a specific key.")
        exit(1)
        
    logger.info("Rebuilding corpus from local files... This will create a new remote Gemini Corpus and upload all your data.")
    async with httpx.AsyncClient(timeout=120.0) as client:
        res = await client.post(f"{URL}/api/corpus/rebuild", headers=get_headers(), json={"new_api_key": GEMINI_KEY})
        if res.status_code == 200:
            data = res.json()
            print(f"Corpus rebuilt successfully! Your new remote corpus ID is: {data.get('new_corpus_id')}")
        else:
            logger.error(f"Error {res.status_code}: {res.text}")

async def do_add(content):
    check_token()
    res = await _call_mcp_tool("add_memory", {"content": content})
    print(res)

async def do_search(query):
    check_token()
    res = await _call_mcp_tool("search_memories", {"query": query})
    print("\nSearch Results:\n")
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
        logger.error("AGENTMEM_URL is not set in .env")
        exit(1)

    parser = argparse.ArgumentParser(description="AI Agentic Memory MCP CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Admin commands
    parser_admin_prov = subparsers.add_parser("admin-provision", help="Provision a new user")
    parser_admin_rot = subparsers.add_parser("admin-rotate", help="Rotate a user's token")
    parser_admin_rot.add_argument("user_id", type=str, help="The UUID of the user")
    parser_admin_dream = subparsers.add_parser("admin-dream-all", help="Trigger dream sequence for all users")
    parser_admin_get_prompt = subparsers.add_parser("admin-get-dream-prompt", help="Get the current global dream prompt text")
    parser_admin_set_prompt = subparsers.add_parser("admin-set-dream-prompt", help="Update the global dream prompt text")
    parser_admin_set_prompt.add_argument("prompt", type=str, help="The new prompt text")

    # User commands
    parser_dream = subparsers.add_parser("dream", help="Trigger dream sequence for your user")
    parser_rebuild = subparsers.add_parser("rebuild-corpus", help="Link your own Gemini API Key and rebuild the corpus")

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

    try:
        if args.command == "admin-provision":
            loop.run_until_complete(do_admin_provision())
        elif args.command == "admin-rotate":
            loop.run_until_complete(do_admin_rotate(args.user_id))
        elif args.command == "admin-dream-all":
            loop.run_until_complete(do_admin_dream_all())
        elif args.command == "admin-get-dream-prompt":
            loop.run_until_complete(do_admin_get_dream_prompt())
        elif args.command == "admin-set-dream-prompt":
            loop.run_until_complete(do_admin_set_dream_prompt(args.prompt))
        elif args.command == "dream":
            loop.run_until_complete(do_dream())
        elif args.command == "rebuild-corpus":
            loop.run_until_complete(do_rebuild_corpus())
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
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Unhandled Exception: {e}", exc_info=True)

if __name__ == "__main__":
    main()
