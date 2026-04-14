import json
import os
from openai import OpenAI
from rich.console import Console

console = Console()

# ── Keyword maps (fast fallback) ─────────────────────────────────────────────

SIMPLE_KEYWORDS = [
    "what time", "what is", "who is", "how many", "when did",
    "tell me about", "hello", "hi", "hey", "thanks", "thank you",
    "what does", "define", "meaning of", "how do i", "can you explain",
    "what are", "why is", "where is", "how old",
]

AGENT_KEYWORDS = {
    "security": [
        "hack", "hacking", "vulnerability", "vulnerabilities", "exploit",
        "pentest", "penetration test", "scan", "sql injection", "xss",
        "csrf", "ssrf", "cve", "attack", "security audit", "owasp",
        "malware", "phishing", "firewall", "intrusion", "breach",
        "orcassecurity", "security agent",
    ],
    "coding": [
        "write code", "write a", "build a", "build me", "create a",
        "implement", "develop", "debug", "fix this bug", "fix this code",
        "refactor", "code review", "function", "class", "api",
        "backend", "frontend", "database", "saas", "platform",
        "script", "program", "algorithm", "library", "framework",
        "orcascoding", "coding agent",
    ],
    "research": [
        "search for", "find me", "look up", "latest news", "what happened",
        "research", "investigate", "summarize this", "summarize the",
        "compare", "best tools", "top libraries", "recent papers",
        "fact check", "is it true", "verify", "what do people say",
        "orcasresearch", "research agent",
    ],
    "devops": [
        "deploy", "deployment", "docker", "dockerfile", "kubernetes",
        "k8s", "ci/cd", "pipeline", "github actions", "server",
        "nginx", "aws", "cloud", "infrastructure", "terraform",
        "containerize", "helm", "devops", "monitoring", "uptime",
        "ship it", "put it on", "host this", "push to production",
        "orcasdevops", "devops agent",
    ],
}

# Tasks that need two or more agents working together
COMPLEX_CHAINS = [
    {
        "triggers"   : ["build", "secure"],
        "chain"      : ["coding", "security"],
        "description": "build it → audit it",
    },
    {
        "triggers"   : ["saas", "backend"],
        "chain"      : ["research", "coding", "security"],
        "description": "research best practices → build it → audit it",
    },
    {
        "triggers"   : ["deploy", "build"],
        "chain"      : ["coding", "devops"],
        "description": "build it → deploy it",
    },
    {
        "triggers"   : ["deploy", "secure"],
        "chain"      : ["devops", "security"],
        "description": "deploy it → audit the infra",
    },
    {
        "triggers"   : ["research", "implement"],
        "chain"      : ["research", "coding"],
        "description": "research it → implement it",
    },
    {
        "triggers"   : ["research", "build"],
        "chain"      : ["research", "coding"],
        "description": "research it → build it",
    },
    {
        "triggers"   : ["build", "deploy"],
        "chain"      : ["coding", "devops"],
        "description": "build it → deploy it",
    },
    {
        "triggers"   : ["full stack", "fullstack"],
        "chain"      : ["coding", "devops", "security"],
        "description": "build → deploy → audit",
    },
]


# ── Keyword scoring (fast path) ──────────────────────────────────────────────

def _score(message: str) -> dict:
    msg    = message.lower()
    scores = {agent: 0 for agent in AGENT_KEYWORDS}
    for agent, keywords in AGENT_KEYWORDS.items():
        for kw in keywords:
            if kw in msg:
                scores[agent] += 1
    return scores


# ── LLM-based routing (smarter path) ─────────────────────────────────────────

ROUTER_SYSTEM_PROMPT = \"\"\"You are a routing classifier for a multi-agent AI system called Orcas.
Given a user message, decide which specialist agent(s) should handle it.

Available agents:
- security: pentesting, vulnerability scanning, CVE lookup, security audits
- coding: writing code, debugging, code review, architecture, any programming
- research: web research, fact checking, article summarization, comparisons
- devops: Docker, Kubernetes, CI/CD, cloud infrastructure, deployment, servers

Rules:
1. If the message is a simple greeting, general question, or doesn't need a specialist → return tier 1
2. If the message needs exactly one specialist → return tier 2 with agent name
3. If the message needs multiple specialists working together → return tier 3 with ordered agent chain

Respond ONLY with valid JSON in this exact format:
{"tier": 1, "agents": [], "reason": "brief reason"}
{"tier": 2, "agents": ["coding"], "reason": "brief reason"}
{"tier": 3, "agents": ["research", "coding"], "reason": "research then implement"}
\"\"\"


def _llm_route(message: str, config) -> dict | None:
    \"\"\"
    Use LLM to classify the routing. Returns None if LLM routing
    fails, so we can fall back to keyword-based routing.
    \"\"\"
    try:
        client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)

        response = client.chat.completions.create(
            model       = config.MODEL,
            messages    = [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user",   "content": message},
            ],
            max_tokens  = 150,
            temperature = 0.0,
        )

        raw = response.choices[0].message.content.strip()

        # extract JSON from the response (handle markdown code blocks)
        if "```" in raw:
            import re
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
            if match:
                raw = match.group(1)

        result = json.loads(raw)

        # validate structure
        if "tier" not in result or "agents" not in result:
            return None

        # validate agent names
        valid_agents = {"security", "coding", "research", "devops"}
        result["agents"] = [a for a in result["agents"] if a in valid_agents]
        result["reason"] = result.get("reason", "LLM-routed")

        return result

    except Exception:
        return None


# ── Main router ───────────────────────────────────────────────────────────────

def route(message: str, config=None) -> dict:
    \"\"\"
    Route a user message to the appropriate tier/agent(s).

    Strategy:
    1. Try LLM-based routing first (if config provided)
    2. Fall back to keyword-based routing
    \"\"\"

    # ── Try LLM routing first ─────────────────────────────────
    if config:
        llm_result = _llm_route(message, config)
        if llm_result:
            return llm_result

    # ── Keyword-based fallback ────────────────────────────────
    msg    = message.lower()
    scores = _score(message)
    total  = sum(scores.values())

    # ── TIER 1 — simple question, Orcas handles it alone ─────────
    simple_hits = sum(1 for kw in SIMPLE_KEYWORDS if kw in msg)
    if simple_hits > 0 and total == 0:
        return {
            "tier"  : 1,
            "agents": [],
            "reason": "simple question — Orcas handles it",
        }

    # ── TIER 3 — complex, needs multiple agents ────────────────
    for combo in COMPLEX_CHAINS:
        hits = sum(1 for t in combo["triggers"] if t in msg)
        if hits >= len(combo["triggers"]):
            return {
                "tier"  : 3,
                "agents": combo["chain"],
                "reason": combo["description"],
            }

    # ── TIER 2 — one specialist ────────────────────────────────
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return {
            "tier"  : 2,
            "agents": [best],
            "reason": f"routed to {best}",
        }

    # ── fallback — Orcas handles it alone ─────────────────────
    return {
        "tier"  : 1,
        "agents": [],
        "reason": "no strong signal — Orcas handles it",
    }
