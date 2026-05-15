import os
import json
import anthropic
from dotenv import load_dotenv

from tools import web_search, read_file, analyze_code
from prompts import SYSTEM_PROMPT, build_user_message
from output import print_report

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Tell Claude what tools exist and what they expect
TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the web for known issues, Stack Overflow answers, CVEs, or library bugs related to the error.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a local file — logs, configs, or source code. Use when a file path appears in the stack trace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative or absolute file path"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "analyze_code",
        "description": "Detect suspicious patterns in a code snippet — bare excepts, hardcoded secrets, missing docstrings, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "The code snippet to analyze"}
            },
            "required": ["code"],
        },
    },
]


def run_tool(name: str, inputs: dict) -> str:
    """Route a tool call to the right function."""
    if name == "web_search":
        return web_search(inputs["query"])
    elif name == "read_file":
        return read_file(inputs["path"])
    elif name == "analyze_code":
        return analyze_code(inputs["code"])
    else:
        return f"Unknown tool: {name}"


def run_agent(bug_report: str) -> str:
    """
    Main agentic loop.
    Keeps calling Claude → running tools → feeding results back
    until Claude stops requesting tools and produces the final report.
    """
    print("\n🔍 Starting bug triage...\n")

    messages = [
        {"role": "user", "content": build_user_message(bug_report)}
    ]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # Add Claude's response to message history
        messages.append({"role": "assistant", "content": response.content})

        # If Claude is done — no more tool calls
        if response.stop_reason == "end_turn":
            final_text = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "No response generated."
            )
            print_report(final_text)
            return final_text

        # Claude wants to use tools — run each one
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    print(f"  🔧 Using tool: {block.name}({list(block.input.values())[0][:60]}...)" 
                          if block.input else f"  🔧 Using tool: {block.name}")
                    
                    result = run_tool(block.name, block.input)
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Feed tool results back to Claude
            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Read bug report from a file
        bug_report = read_file(sys.argv[1])
    else:
        # Interactive mode
        print("Paste your bug report (press Enter twice when done):")
        lines = []
        while True:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        bug_report = "\n".join(lines)

    run_agent(bug_report)