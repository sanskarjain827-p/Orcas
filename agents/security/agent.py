import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.base import BaseAgent
import agents.security.config as config

class OrcasSecurity(BaseAgent):
    name  = "OrcasSecurity"
    color = "red"
    tool_pattern = r"<audit\s+type=\"(.*?)\"\s*>\s*(.*?)\s*</audit>"

    def _load_config(self):
        return config

    def dispatch_tool(self, tag: str, arg: str) -> str:
        from agents.security.tools.scanner import scan
        from agents.security.tools.exploits import exploit
        
        if tag == "scan":
            return scan(arg)
        elif tag == "exploit":
            return exploit(arg)
        return f"Unknown tool: {tag}"
