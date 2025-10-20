# chatrr - AI-Powered Debugging with Mozilla rr

An AI debugging agent that uses Mozilla rr (Record & Replay) to automatically analyze bugs by combining time-travel debugging with LLM reasoning.

## What Can It Debug?

Armed with two simple tools (`gdb_command` and `read_source_file`), the agent can debug:

- **Crashes** (SIGSEGV, SIGABRT, SIGFPE, etc.)
- **Incorrect output** (wrong calculations, unexpected results)
- **Logic errors** (wrong control flow, incorrect state)
- **Assertion failures** (violated invariants)
- **Performance issues** (infinite loops, unexpected slowness)
- **Memory issues** (leaks, corruption, use-after-free)
- **Race conditions** (timing-dependent bugs)
- **Any reproducible bug recorded with rr**

## Quick Start

### 1. Setup

```bash
# Install dependencies
uv sync

# Configure Azure OpenAI credentials
# Edit chatrr.py lines 163-166 with your credentials:
#   api_version = "2024-02-15-preview"
#   azure_deployment = "gpt-5"
#   openai_api_key = "your-api-key"
#   azure_endpoint = "https://your-endpoint.openai.azure.com/"
```

**Note**: Credentials are hardcoded in chatrr.py because dotenv doesn't work well in GDB environment.

### 2. Record a Program with rr

```bash
# Compile with debug symbols
gcc -g myprogram.c -o myprogram

# Record execution
rr record ./myprogram [args]
```

### 3. Debug with AI

```bash
# Start replay
rr replay

# Load the agent
(rr) source /path/to/chatrr.py
✓ RR Debug Agent loaded!

# Ask the AI to debug
(rr) analyze Why did the program crash?
```

## Key Features

### 🔍 Watchpoints + Reverse Execution

The agent uses rr's time-travel debugging to trace bugs backwards:

1. Find variable with wrong value
2. Set watchpoint: `watch variable`
3. Reverse-continue: runs backwards to when variable changed
4. Examine context and repeat if needed

This traces data flow from symptom back to root cause.

### 🤖 Evidence-Based Reasoning

The agent never guesses - it verifies every hypothesis with tools:
- Executes GDB commands to inspect runtime state
- Reads source code to understand logic
- Follows systematic debugging methodology
- Provides detailed evidence chain

### 📝 Comprehensive Analysis

The agent generates reports with:
- Root cause identification
- Evidence chain (all findings from tool calls)
- Causal chain (step-by-step explanation)
- Fix suggestions with code examples
- Confidence level

## Example Commands

```gdb
# General crash analysis
analyze Why did this program crash?

# Specific variable investigation
analyze Trace back where variable 'ptr' became NULL

# Wrong output debugging
analyze The program outputs 15 but should output 10, debug why

# Assertion failures
analyze Why did assertion 'count <= max_size' fail?

# Performance issues
analyze Why is this function so slow?
```

## Architecture

**Two-Tool Design:**
1. `gdb_command(cmd)` - Execute any GDB/RR command
2. `read_source_file(path, start, end)` - Read source code

**LangGraph Agent:**
- Loads system prompt from `system_prompt.md`
- Uses ReAct pattern: think → act → observe → repeat
- Continues until enough evidence gathered

**Key Technique:**
Watchpoints + reverse execution to trace data flow backwards through time.

## Documentation

- **CLAUDE.md** - Development guide and architecture
- **system_prompt.md** - Complete agent behavior specification
- **crash.c** - Simple test case (NULL pointer dereference)

## Requirements

- Python 3.12+
- Mozilla rr
- GDB
- Azure OpenAI API access (or modify chatrr.py to use other LLM providers)

## Configuration

Edit `chatrr.py` (lines 163-166) with your Azure OpenAI credentials:

```python
api_version = "2024-02-15-preview"
azure_deployment = "gpt-5"
openai_api_key = "your-api-key-here"
azure_endpoint = "https://your-endpoint.openai.azure.com/"
```

**Note**: Credentials are hardcoded because dotenv doesn't work in GDB environment.

## How It Works

1. User records program execution with `rr record`
2. User starts replay with `rr replay` and loads `chatrr.py`
3. User asks question: `analyze <question>`
4. Agent uses GDB commands to inspect state
5. Agent uses watchpoints + reverse-continue to trace backwards
6. Agent reads source code to understand logic
7. Agent provides detailed root cause analysis

The agent follows a 5-phase methodology:
1. Understand the problem
2. Examine the problem site
3. Trace root cause (watchpoints + reverse execution)
4. Understand code logic
5. Generate report

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
