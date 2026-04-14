import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.base import BaseAgent
import agents.coding.config as config

class OrcasCoding(BaseAgent):
    name  = "OrcasCoding"
    color = "green"
    tool_pattern = r"<code\s+action=\"(.*?)\"\s*>\s*(.*?)\s*</code>"

    def _load_config(self):
        return config

    def dispatch_tool(self, tag: str, arg: str) -> str:
        from agents.coding.tools.executor import run_code
        from agents.coding.tools.linter import lint
        
        if tag == "run":
            return run_code(arg)
        elif tag == "lint":
            return lint(arg)
        return f"Unknown tool: {tag}"
