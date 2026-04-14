import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.base import BaseAgent
import agents.devops.config as config

class OrcasDevOps(BaseAgent):
    name  = "OrcasDevOps"
    color = "yellow"
    tool_pattern = r"<ship\s+target=\"(.*?)\"\s*>\s*(.*?)\s*</ship>"

    def _load_config(self):
        return config

    def dispatch_tool(self, tag: str, arg: str) -> str:
        from agents.devops.tools.docker import build_container
        from agents.devops.tools.cloud import deploy
        
        if tag == "docker":
            return build_container(arg)
        elif tag == "cloud":
            return deploy(arg)
        return f"Unknown tool: {tag}"
