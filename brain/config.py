import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), "../.env")
load_dotenv(env_path)

# Ensure an API key exists
def ensure_config():
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Prompt
        console = Console()
        
        console.print(Panel(
            "[bold cyan]🐋 Orcas Setup Wizard[/bold cyan]\\n\\n"
            "It looks like this is your first time running Orcas, or your API key is missing.\\n"
            "Orcas requires an OpenAI-compatible API key (NVIDIA, Groq, OpenAI, etc.)",
            expand=False,
            border_style="cyan"
        ))
        
        key = Prompt.ask("[bold yellow]Enter your API Key[/bold yellow]", password=True).strip()
        
        if key:
            if not os.path.exists(env_path):
                with open(env_path, 'w') as f:
                    f.write("# Orcas Configuration\\n")
            
            # Simple appender for MVP
            with open(env_path, 'a') as f:
                f.write(f"\\nOPENAI_API_KEY={key}\\n")
            
            console.print("[bold green]✓ Configuration saved to .env![/bold green]\\n")
            return key
        else:
            console.print("[bold red]ERROR: API key is required to run Orcas.[/bold red]")
            exit(1)
    return api_key

API_KEY = ensure_config()

# Generic OpenAI-compatible settings
BASE_URL     = os.getenv("OPENAI_BASE_URL") or "https://integrate.api.nvidia.com/v1"
MODEL        = os.getenv("OPENAI_MODEL") or "minimax/minimax-text-01"

MAX_TOKENS   = 4096
TEMPERATURE  = 0.4   # slightly warmer — Orcas brain is conversational

AGENT_NAME   = "Orcas"
PROMPT_FILE  = os.path.join(os.path.dirname(__file__), "../agent.md")
REPORTS_DIR  = os.path.expanduser("~/orcas-reports")
