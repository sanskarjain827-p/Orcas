import re
import sys
import os
from openai import OpenAI
from rich.console import Console

console = Console()


class BaseAgent:
    \"\"\"
    Base class every Orcas agent inherits from.

    Subclasses must:
      - Set `name`, `color`, `tool_pattern`
      - Implement `_load_config()` → returns a config module
      - Implement `dispatch_tool(tag, arg)` → returns str result
    \"\"\"
    name         : str = "BaseAgent"
    color        : str = "white"
    prompt_file  : str = ""
    tool_pattern : str = ""   # regex with two groups: (tag, arg)

    def __init__(self):
        self.config  = self._load_config()
        self.client  = OpenAI(
            api_key  = self.config.API_KEY,
            base_url = self.config.BASE_URL,
        )
        self._system_prompt = None

    def _load_config(self):
        raise NotImplementedError("Each agent must implement _load_config()")

    def load_prompt(self) -> str:
        if self._system_prompt:
            return self._system_prompt
        try:
            prompt_path = self.config.PROMPT_FILE
            with open(prompt_path, "r") as f:
                self._system_prompt = f.read()
            return self._system_prompt
        except FileNotFoundError:
            console.print(f"[red]ERROR: prompt.md not found for {self.name}[/red]")
            sys.exit(1)

    def dispatch_tool(self, tag: str, arg: str) -> str:
        raise NotImplementedError("Each agent must implement dispatch_tool()")

    def process_tool_calls(self, text: str) -> list:
        \"\"\"Extract and execute tool calls from the full reply text.\"\"\"
        if not self.tool_pattern:
            return []
        pattern = re.compile(self.tool_pattern, re.DOTALL | re.IGNORECASE)
        results = []
        for match in pattern.finditer(text):
            results.append(self.dispatch_tool(match.group(1), match.group(2)))
        return results

    def _strip_tool_tags(self, text: str) -> str:
        \"\"\"Remove tool tag markup from text intended for display.\"\"\"
        if not self.tool_pattern:
            return text
        pattern = re.compile(self.tool_pattern, re.DOTALL | re.IGNORECASE)
        return pattern.sub("", text)

    def run(self, message: str, history: list) -> str:
        \"\"\"
        Main entry point called by the brain.
        Builds messages, calls AI, handles tools, returns final reply.
        \"\"\"
        system_prompt = self.load_prompt()
        messages = [{"role": "system", "content": system_prompt}]
        messages += history
        messages.append({"role": "user", "content": message})

        return self._chat(messages)

    def _chat(self, messages: list) -> str:
        \"\"\"
        Call the LLM with streaming, buffer the full reply, then
        display it cleanly with tool tags stripped out.
        Handles tool calls if found in the reply.
        \"\"\"
        color = self.color

        response = self.client.chat.completions.create(
            model       = self.config.MODEL,
            messages    = messages,
            max_tokens  = self.config.MAX_TOKENS,
            temperature = self.config.TEMPERATURE,
            stream      = True,
        )

        # ── Phase 1: collect full reply ──────────────────────────
        full_reply = ""
        console.print(f"\\n[bold {color}]{self._badge()} {self.name}[/bold {color}]\\n")

        for chunk in response:
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                full_reply += delta.content

        # ── Phase 2: display clean text (tool tags stripped) ─────
        clean_text = self._strip_tool_tags(full_reply).strip()
        if clean_text:
            print(clean_text)
        print()

        # ── Phase 3: handle tool calls ───────────────────────────
        tool_results = self.process_tool_calls(full_reply)
        if not tool_results:
            return full_reply

        # feed tool results back for a final answer
        tool_context = "\\n".join(tool_results)
        messages.append({"role": "assistant", "content": full_reply})
        messages.append({
            "role": "user",
            "content": (
                f"[TOOL RESULTS]\\n{tool_context}\\n\\n"
                "Now complete your response using these results."
            ),
        })

        final = self.client.chat.completions.create(
            model       = self.config.MODEL,
            messages    = messages,
            max_tokens  = self.config.MAX_TOKENS,
            temperature = self.config.TEMPERATURE,
            stream      = True,
        )

        final_reply = ""
        console.print(
            f"[bold {color}]{self._badge()} {self.name} "
            f"(results)[/bold {color}]\\n"
        )

        for chunk in final:
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                print(delta.content, end="", flush=True)
                final_reply += delta.content

        print("\\n")
        return final_reply

    def _badge(self) -> str:
        badges = {
            "red":    "🔴",
            "green":  "🟢",
            "blue":   "🔵",
            "yellow": "🟡",
            "cyan":   "🐋",
            "white":  "⚪",
        }
        return badges.get(self.color, "⚪")
