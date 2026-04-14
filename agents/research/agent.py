import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from agents.base import BaseAgent
import agents.research.config as config

class OrcasResearch(BaseAgent):
    name  = "OrcasResearch"
    color = "blue"
    tool_pattern = r"<query\s+mode=\"(.*?)\"\s*>\s*(.*?)\s*</query>"

    def _load_config(self):
        return config

    def dispatch_tool(self, tag: str, arg: str) -> str:
        from agents.research.tools.searcher import search
        from agents.research.tools.summarizer import summarize
        
        if tag == "search":
            return search(arg)
        elif tag == "summarize":
            return summarize(arg)
        return f"Unknown tool: {tag}"
