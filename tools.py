import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")  # we'll add this in a sec


def web_search(query: str) -> str:
    """Search the web for known issues, Stack Overflow answers, CVEs."""
    if not SERPAPI_KEY:
        return f"[web_search skipped — no SERPAPI_KEY set] Query was: {query}"
    
    try:
        response = requests.get(
            "https://serpapi.com/search",
            params={
                "q": query,
                "api_key": SERPAPI_KEY,
                "num": 5,
                "engine": "google",
            },
            timeout=10,
        )
        results = response.json().get("organic_results", [])
        if not results:
            return "No results found."
        
        output = []
        for r in results[:5]:
            output.append(f"- {r.get('title')}\n  {r.get('link')}\n  {r.get('snippet', '')}")
        return "\n\n".join(output)
    
    except Exception as e:
        return f"web_search error: {str(e)}"


def read_file(path: str) -> str:
    """Read a local file — logs, configs, source code."""
    try:
        with open(path, "r") as f:
            content = f.read()
        if len(content) > 8000:
            content = content[:8000] + "\n\n[truncated — file too long]"
        return content
    except FileNotFoundError:
        return f"File not found: {path}"
    except Exception as e:
        return f"read_file error: {str(e)}"


def analyze_code(code: str) -> str:
    """Flag suspicious patterns in a code snippet."""
    findings = []

    checks = [
        ("bare except", "except:",        "Catches all exceptions — masks real errors"),
        ("mutable default", "def ",       None),  # handled below
        ("print debugging", "print(",     "Leftover debug prints found"),
        ("hardcoded secret", "password =","Possible hardcoded credential"),
        ("hardcoded secret", "api_key =", "Possible hardcoded API key"),
        ("TODO",            "TODO",       "Unresolved TODOs in code"),
        ("force push risk", "git push -f","Dangerous force push in script"),
    ]

    for label, pattern, message in checks:
        if pattern in code:
            msg = message or f"Pattern '{pattern}' detected"
            findings.append(f"⚠️  {label}: {msg}")

    # Check for functions with no docstring
    lines = code.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("def ") and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if not next_line.startswith('"""') and not next_line.startswith("'''"):
                fn_name = line.strip().split("(")[0].replace("def ", "")
                findings.append(f"⚠️  missing docstring: `{fn_name}()` has no docstring")

    if not findings:
        return "No obvious issues detected in the code snippet."
    
    return "\n".join(findings)