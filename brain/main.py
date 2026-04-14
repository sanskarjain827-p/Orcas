import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from rich.console import Console
from rich.panel   import Panel
from rich.prompt  import Prompt
from rich         import print as rprint

import brain.config as config
from brain.router  import route
from brain.memory  import (
    SessionMemory, save_session,
    load_last_session, list_sessions,
)

# import all agents
from agents.security.agent import OrcasSecurity
from agents.coding.agent   import OrcasCoding
from agents.research.agent import OrcasResearch
from agents.devops.agent   import OrcasDevOps

console = Console()
client  = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)

# ── Agent registry ────────────────────────────────────────────
AGENTS = {
    "security": OrcasSecurity(),
    "coding"  : OrcasCoding(),
    "research": OrcasResearch(),
    "devops"  : OrcasDevOps(),
}

HELP_TEXT = """
[bold cyan]Main Commands[/bold cyan]
  /help            Show this menu
  /agents          Manage specialist agents
  /history         View recent activity
  /sessions        Load/Manage session logs
  /clear           Reset current context
  /save            Snapshot current state
  exit             Quit Orcas

[bold cyan]Specialist Access[/bold cyan]
  /security [task]   Jump to OrcasSecurity 🔴
  /coding   [task]   Jump to OrcasCoding   🟢
  /research [task]   Jump to OrcasResearch 🔵
  /devops   [task]   Jump to OrcasDevOps   🟡
"""


# ── Orcas brain — answers Tier 1 alone ───────────────────────

def load_orcas_prompt() -> str:
    try:
        with open(config.PROMPT_FILE, "r") as f:
            return f.read()
    except FileNotFoundError:
        console.print("[red]ERROR: agent.md not found at root[/red]")
        sys.exit(1)


def orcas_reply(message: str, history: list) -> str:
    \"\"\"Orcas Brain answers directly — no specialist needed.\"\"\"
    system_prompt = load_orcas_prompt()
    messages      = [{"role": "system", "content": system_prompt}]
    messages     += history
    messages.append({"role": "user", "content": message})

    full_reply = ""
    console.print("\n[bold cyan]🐋 Orcas[/bold cyan]")

    with console.status("[dim]Thinking...[/dim]", spinner="dots"):
        response = client.chat.completions.create(
            model       = config.MODEL,
            messages    = messages,
            max_tokens  = config.MAX_TOKENS,
            temperature = config.TEMPERATURE,
            stream      = True,
        )

    for chunk in response:
        if not getattr(chunk, "choices", None):
            continue
        delta = chunk.choices[0].delta
        if hasattr(delta, "content") and delta.content:
            console.print(delta.content, end="", flush=True)
            full_reply += delta.content

    console.print("\n")
    return full_reply


# ── Tier 3 — multi-agent chain ────────────────────────────────

def run_chain(
    message    : str,
    agent_names: list,
    history    : list,
    description: str,
) -> str:
    console.print(
        f"\n[bold magenta]⛓  Complex task detected[/bold magenta]\n"
        f"[dim]Plan: {description}[/dim]\n"
        f"[dim]Chain: {' → '.join(agent_names)}[/dim]\n"
    )

    outputs     = {}
    final_reply = ""

    for i, name in enumerate(agent_names, 1):
        agent = AGENTS[name]
        console.print(
            f"[dim]Step {i}/{len(agent_names)}: "
            f"running {name.capitalize()}...[/dim]"
        )

        # each agent gets the original message + previous agents' outputs
        context = message
        if outputs:
            prior = "\n\n".join(
                f"[Output from {n}]\n{o}"
                for n, o in outputs.items()
            )
            context = (
                f"{message}\n\n"
                f"[Context from previous agents in this chain]\n{prior}"
            )

        result         = agent.run(context, history)
        outputs[name]  = result
        final_reply    = result   # last agent's output is the primary reply

    # Orcas merges everything into one final summary
    if len(agent_names) > 1:
        console.print("\n[bold cyan]🐋 Orcas — merging outputs[/bold cyan]\n")

        combined = "\n\n".join(
            f"=== {n.upper()} OUTPUT ===\n{o}"
            for n, o in outputs.items()
        )

        merge_messages = [
            {
                "role": "system",
                "content": load_orcas_prompt(),
            },
            {
                "role": "user",
                "content": (
                    f"The user asked: {message}\n\n"
                    f"Multiple specialist agents worked on this.\n"
                    f"Here are all their outputs:\n\n{combined}\n\n"
                    f"Synthesize these into one clear, unified response "
                    f"for the user. Don't repeat everything — highlight "
                    f"the key findings from each agent and how they connect."
                ),
            },
        ]

        merge_response = client.chat.completions.create(
            model       = config.MODEL,
            messages    = merge_messages,
            max_tokens  = config.MAX_TOKENS,
            temperature = 0.3,
            stream      = True,
        )

        merged = ""
        for chunk in merge_response:
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                print(delta.content, end="", flush=True)
                merged += delta.content

        print("\n")
        final_reply = merged

    return final_reply


# ── Banner ────────────────────────────────────────────────────

def print_banner():
    console.print("\n")
    console.print(Panel(
        "[bold cyan]🐋  O R C A S[/bold cyan]\n"
        "[dim]Agentic Orchestrator v0.1.0[/dim]\n\n"
        "[bold green]Security[/bold green] 🔴 | [bold green]Coding[/bold green] 🟢 | "
        "[bold green]Research[/bold green] 🔵 | [bold green]DevOps[/bold green] 🟡",
        border_style="cyan",
        padding=(1, 6),
        subtitle="[dim]The Autonomous Specialist Network[/dim]",
        subtitle_align="right"
    ))
    console.print("[dim]Type naturally to route or use [bold]/help[/bold] for commands.[/dim]")


# ── Main loop ─────────────────────────────────────────────────

def main():
    memory     = SessionMemory()
    last_reply = ""
    agents_used = []

    print_banner()

    while True:
        try:
            # Clean prompt style
            user_input = console.input("\n[bold cyan]❯[/bold cyan] ").strip()

            if not user_input:
                continue

            # ── Exit ──────────────────────────────────────────
            if user_input.lower() in ("exit", "quit", "q"):
                if memory.get():
                    save_session(memory.get(), agents_used)
                    console.print("[dim]Session saved automatically.[/dim]")
                console.print(
                    "\n[dim]Orcas signing off. "
                    "Stay curious. 🐋[/dim]\n"
                )
                break

            # ── Built-in commands ──────────────────────────────
            low = user_input.lower()

            if low == "/help":
                console.print(HELP_TEXT)
                continue

            if low == "/agents":
                console.print(
                    "\n[bold cyan]Available Agents[/bold cyan]\n"
                    "  🔴 OrcasSecurity — security audits, pentesting, CVE lookup\n"
                    "  🟢 OrcasCoding   — write, debug, review, refactor code\n"
                    "  🔵 OrcasResearch — deep web research, fact checking\n"
                    "  🟡 OrcasDevOps   — docker, CI/CD, k8s, cloud infra\n"
                    "  🐋 Orcas         — general questions, routing, synthesis\n"
                )
                continue

            if low == "/history":
                console.print(f"[dim]{memory.summary()}[/dim]")
                continue

            if low == "/sessions":
                console.print(list_sessions())
                continue

            if low == "/resume":
                past = load_last_session()
                if past:
                    for msg in past:
                        memory.add(msg["role"], msg["content"])
                    console.print(
                        f"[green]✓ Loaded last session "
                        f"({len(past)//2} turns)[/green]"
                    )
                else:
                    console.print("[yellow]No past session found.[/yellow]")
                continue

            if low == "/clear":
                memory.clear()
                agents_used = []
                console.print("[dim]Session cleared.[/dim]")
                continue

            if low == "/save":
                if memory.get():
                    path = save_session(memory.get(), agents_used)
                    console.print(f"[green]✓ Saved → {path}[/green]")
                else:
                    console.print("[yellow]Nothing to save yet.[/yellow]")
                continue

            # ── Direct agent shortcuts ─────────────────────────
            direct_map = {
                "/security": "security",
                "/coding"  : "coding",
                "/research": "research",
                "/devops"  : "devops",
            }

            direct_agent = None
            for prefix, name in direct_map.items():
                if low.startswith(prefix + " ") or low == prefix:
                    direct_agent = name
                    task = user_input[len(prefix):].strip() or user_input
                    user_input = task
                    break

            # ── Route or direct ────────────────────────────────
            memory.add("user", user_input)

            if direct_agent:
                label = f"{direct_agent.upper()} AGENT"
                console.print(f"[dim]→ Direct execution via specialist: {label}[/dim]")
                agent = AGENTS[direct_agent]
                
                with console.status(f"[dim]{direct_agent.capitalize()} is working...[/dim]", spinner="bouncingBar"):
                    reply = agent.run(user_input, memory.get()[:-1])
                
                memory.active_agent = direct_agent
                if direct_agent not in agents_used:
                    agents_used.append(direct_agent)

            else:
                # Routing visualization
                with console.status("[dim]Orchestrating specialist...[/dim]", spinner="point"):
                    decision = route(user_input, config=config)
                
                tier     = decision["tier"]
                names    = decision["agents"]
                reason   = decision["reason"]

                if tier == 1:
                    reply = orcas_reply(user_input, memory.get()[:-1])
                    memory.active_agent = "orcas"

                elif tier == 2:
                    agent_name = names[0]
                    console.print(f"[dim]→ Routed to specialist: [bold]{agent_name.upper()}[/bold][/dim]")
                    agent  = AGENTS[agent_name]
                    
                    with console.status(f"[dim]{agent_name.capitalize()} is working...[/dim]", spinner="bouncingBar"):
                        reply  = agent.run(user_input, memory.get()[:-1])
                    
                    memory.active_agent = agent_name
                    if agent_name not in agents_used:
                        agents_used.append(agent_name)

                else:   # tier 3
                    reply = run_chain(
                        user_input,
                        names,
                        memory.get()[:-1],
                        decision["reason"],
                    )
                    memory.active_agent = "orcas"
                    for n in names:
                        if n not in agents_used:
                            agents_used.append(n)

            last_reply = reply
            memory.add("assistant", reply)

        except KeyboardInterrupt:
            console.print(
                "\n\n[dim]Interrupted. Type 'exit' to quit cleanly.[/dim]"
            )
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")


if __name__ == "__main__":
    main()
