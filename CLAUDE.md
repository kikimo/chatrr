# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**chatrr** is an AI-powered debugging agent that uses Mozilla rr (Record & Replay) to help debug programs by analyzing recorded execution traces. The agent combines runtime state inspection from rr traces with source code analysis to identify root causes of bugs and provide detailed analysis reports.

**Core Concept:**
- Input: rr trace file (complete program execution recording) + program codebase
- Output: Root cause analysis report with evidence chain and fix suggestions
- Target: Any reproducible bug that can be recorded with rr, including:
  - **Crashes** (SIGSEGV, SIGABRT, SIGFPE, etc.)
  - **Incorrect output** (wrong calculation results, unexpected behavior)
  - **Logic errors** (incorrect state, wrong control flow)
  - **Performance issues** (unexpected slowness, infinite loops)
  - **Race conditions** (timing-dependent bugs in concurrent programs)
  - **Memory issues** (leaks, corruption, use-after-free)
  - **Any bug where you can point to "the program should not be in this state"**

## Architecture

The agent provides exactly **TWO tools** to the LLM:

1. **`run_cmd(cmd: str) -> str`**: Execute any rr/gdb command and return output
   - Runs commands like `print variable`, `bt`, `reverse-continue`, `watch variable`
   - All runtime inspection happens through direct GDB commands

2. **`read_file(file_path, line_start, line_end) -> str`**: Read source code files
   - Used to examine code context around crashes
   - Understand function implementations and error handling

### Core Debugging Technique: Watchpoints + Reverse Execution

The **KEY methodology** for finding root causes:

1. Find a variable with incorrect/suspicious value at crash
2. Set hardware watchpoint: `watch <variable>`
3. Reverse-continue: `reverse-continue` - goes backwards to when variable was modified
4. Examine context: check code, other variables, call stack
5. Repeat if needed - keep reverse-continuing to trace data flow backwards

This technique leverages rr's time-travel debugging to trace bugs from symptom back to root cause.

### Analysis Workflow

1. **Understand the problem**: Navigate to the problem point (crash, assertion, wrong output, unexpected state)
2. **Examine the state**: Check variables, registers, memory, call stack at the problem point
3. **Trace root cause**: Use watchpoints + reverse execution to find where incorrect values/state originated
4. **Understand code logic**: Read source files to understand why the bug occurred
5. **Generate report**: Provide evidence chain, causal chain, and fix suggestions

The workflow adapts to different bug types:
- **For crashes**: Run to crash, examine signal and crash site
- **For wrong output**: Set breakpoint where output is produced, check input data flow
- **For incorrect state**: Set breakpoint at assertion or where state is checked, trace backwards
- **For performance**: Examine execution patterns, check loop conditions, identify bottlenecks

## Development Setup

### Environment

This project uses uv for Python dependency management:

```bash
# Install dependencies
uv sync

# Add new dependencies
uv add <package-name>
```

### Configuration

**Important**: Azure OpenAI credentials are hardcoded in chatrr.py (lines 163-166) because dotenv doesn't work well in the GDB environment. Edit these values directly in the file:

```python
api_version = "2024-02-15-preview"
azure_deployment = "gpt-5"  # Your deployment name
openai_api_key = "your-api-key-here"
azure_endpoint = "https://your-endpoint.openai.azure.com/"
```

⚠️ **Security Note**: Keep chatrr.py out of version control if it contains real credentials, or use a separate config file that you source.

### Dependencies

Key frameworks and libraries:
- **LangGraph**: Agent workflow orchestration with state management
- **langchain-openai**: Azure OpenAI integration
- **langchain-core**: Core LangChain abstractions (tools, messages)
- **anthropic**: Claude API client (optional, for future use)
- **mcp**: Model Context Protocol for tool integration (optional, for future use)

- **system_prompt.md**: Complete system prompt for the debugging agent
  - Defines agent role and methodology
  - Lists all GDB/RR commands the agent should use
  - Provides debugging workflow with watchpoint + reverse execution technique
  - Includes example analyses and output format

- **chatrr.py**: Main GDB extension with AI debugging agent
  - **`analyze <question>` command**: AI-powered debugging assistant
  - **`xrun <cmd>` command**: Execute GDB commands and log to file
  - Implements the two tools: `gdb_command()` and `read_source_file()`
  - Uses LangGraph to orchestrate the agent workflow
  - Loads system_prompt.md to configure agent behavior

- **langgraph_azure_example.py**: Example of LangGraph workflow with Azure OpenAI
  - Shows tool calling pattern with LangGraph
  - Demonstrates state management for agent workflows

- **simple_langgraph_tools.py**: Simplified LangGraph tool calling example

- **archive/DEBUG_AGENT_DESIGN.md**: Original design specification (Chinese)
  - Contains detailed architecture planning
  - Tool interaction sequences
  - Note: Some details are outdated (uses simplified 2-tool approach now)

## Using the Agent

### Load the extension in GDB/RR

```bash
# Start rr replay session
rr replay /path/to/trace

# In GDB, load the extension
source /path/to/chatrr.py
```

The extension will print:
```
GDB extension loaded! Try 'hello' or 'greet <name>'
✓ RR Debug Agent loaded!
  Use 'analyze <question>' to debug with AI assistance
```

### The `analyze` command

Ask the AI agent to debug your program:

```gdb
# Analyze a crash
(rr) analyze Why did the program crash?

# Debug wrong output
(rr) analyze The program outputs 15 but should output 10, debug why

# Trace variable origins
(rr) analyze Trace back where variable 'user' became NULL

# General debugging
(rr) analyze What's wrong with this program?
```

The agent will:
1. Use `gdb_command()` tool to execute GDB/RR commands
2. Use `read_source_file()` tool to read source code
3. Follow the systematic debugging methodology from system_prompt.md
4. Provide detailed analysis with evidence and fix suggestions

### Example Session

```bash
# Record a crash with rr
$ gcc -g crash.c -o crash
$ rr record ./crash

# Start replay and load agent
$ rr replay
(rr) source chatrr.py
✓ RR Debug Agent loaded!

(rr) analyze Why did this program crash?

🤖 Analyzing: Why did this program crash?
================================================================================

I'll analyze this crash systematically. Let me start by running to the crash
point and getting crash information.

[Agent executes: gdb_command("run")]
Program received signal SIGSEGV, Segmentation fault...

[Agent continues investigating with watchpoints and reverse execution]

Root cause identified: NULL pointer dereference at crash.c:10.
The variable 'ptr' is NULL because...

[Detailed analysis with fix suggestion]
================================================================================
```

## Implementation Details

### Tool Implementation

The agent uses two tools defined in chatrr.py:

**1. gdb_command(cmd: str) -> str**
- Wraps `gdb.execute(cmd, from_tty=False, to_string=True)`
- Strips ANSI color codes from output using regex
- Returns clean text output to the LLM
- Handles errors gracefully

**2. read_source_file(file_path, line_start, line_end) -> str**
- Reads file and returns specified line range
- Formats with line numbers for easy reference
- 1-indexed line numbers for consistency with GDB

### LangGraph Workflow

The agent uses a standard ReAct pattern:
1. **Agent node**: LLM receives system prompt + user question, decides to use tools or respond
2. **Tools node**: Executes tool calls (gdb_command or read_source_file)
3. **Conditional edge**: If tools were called, return to agent; otherwise end
4. **Loop**: Agent can call tools multiple times until it has enough information

The system prompt from system_prompt.md is prepended as a SystemMessage on first invocation.

### Additional Commands

**xrun <cmd>**: Execute GDB command and log to chatgdb.log
- Useful for manual command execution with logging
- Logs in XML format: `<gdb_command><command>...</command><command_result>...</command_result></gdb_command>`

The complete agent behavior is defined in **system_prompt.md**. Key principles:

1. **Evidence-based reasoning** - Never guess, always verify with tools
2. **Watchpoints are key** - Set watchpoints and reverse-continue to trace data flow
3. **Runtime is ground truth** - Trust what rr shows, not what code "should" do
4. **Root cause ≠ crash location** - Crash is symptom, trace back to where bug was introduced
5. **Multiple reverse-continue** - Don't stop at first watchpoint hit, keep tracing backwards

Common bug patterns to recognize:
- **Crashes**: NULL pointer dereference, use-after-free, buffer overflow, double-free
- **Logic errors**: Wrong conditional, off-by-one error, incorrect loop termination
- **Data corruption**: Uninitialized variable, wrong calculation, type confusion
- **State errors**: Incorrect state machine transition, missing validation
- **Concurrency bugs**: Race condition, deadlock, missing synchronization
- **Resource issues**: Memory leak, file descriptor leak, missing cleanup

## Implementation Approach

The agent will be implemented using **LangGraph** (see langgraph_azure_example.py for patterns):

1. **Define tools** using `@tool` decorator:
   - `run_cmd(cmd: str) -> str` - executes GDB commands via gdb.execute()
   - `read_file(file_path, line_start, line_end) -> str` - reads source files

2. **Create LangGraph workflow** with state management:
   - State includes conversation messages and analysis findings
   - Agent node calls LLM with tools
   - Tool node executes tool calls
   - Conditional edges decide whether to continue or finish

3. **Load system prompt** from system_prompt.md to configure agent behavior

4. **Execute analysis** by invoking the graph with initial user request

Example invocation pattern:
```python
# Load system prompt
with open('system_prompt.md') as f:
    system_prompt = f.read()

# Initialize LLM with tools and system prompt
llm = AzureChatOpenAI(...).bind_tools([run_cmd, read_file])

# Create and run graph
app = workflow.compile()
result = app.invoke({"messages": [SystemMessage(system_prompt), HumanMessage("Analyze crash")]})
```

## Output Format

The agent generates JSON reports with:
- `root_cause`: Type and description of the bug
- `crash_location`: File/line where crash occurred
- `error_location`: File/line where bug was introduced
- `evidence_chain`: List of findings from tool calls
- `causal_chain`: Step-by-step explanation of how crash happened
- `fix_suggestion`: Recommended code changes with examples
- `confidence`: 0-1 confidence score

## Important GDB/RR Commands for the Agent

The agent must know these commands (from system_prompt.md):

**Reverse execution:**
- `reverse-continue` / `rc` - Run backwards until watchpoint/breakpoint
- `reverse-step` / `rs` - Step backwards one source line
- `reverse-next` / `rn` - Step backwards over function calls

**Watchpoints (critical for root cause analysis):**
- `watch <variable>` - Break when variable changes
- `watch -l <address>` - Watch memory location
- `info watchpoints` - List watchpoints
- `delete <num>` - Remove watchpoint

**Variable inspection:**
- `print <var>` / `p <var>` - Print variable value
- `print *<ptr>` - Dereference pointer
- `info locals` - All local variables
- `info args` - Function arguments

**Navigation:**
- `bt` / `where` - Backtrace
- `list` - Show source code
- `frame <num>` - Switch stack frame
- `up` / `down` - Move in call stack

## Testing the Agent

To test with any program:

```bash
# Compile program with debug symbols
gcc -g program.c -o program

# Record execution with rr
rr record ./program [args]

# The agent can analyze the trace
# For crashes: it will automatically run to the crash
# For other bugs: provide breakpoint or describe the problem
```

The crash.c program (a simple NULL pointer dereference) serves as a basic test case, but the agent can debug any reproducible issue recorded with rr.

## Debugging Non-Crash Issues

The agent is particularly powerful for debugging issues that are hard to find with traditional debuggers:

**Example: Wrong calculation result**
```
User: "The program calculates 2+2=5, recorded in trace. Debug why."
Agent: Sets breakpoint at output, checks calculation variables, uses watchpoints to trace
        where the wrong value originated, finds the bug in the arithmetic logic.
```

**Example: Assertion failure**
```
User: "Assertion 'count <= max_size' failed. Why?"
Agent: Runs to assertion, checks both values, uses watchpoint on 'count' + reverse-continue
        to find where count was incremented incorrectly.
```

**Example: Unexpected behavior**
```
User: "User ID 123 should have admin rights but doesn't. Why?"
Agent: Sets breakpoint at permission check, examines data structures, traces backwards
        to find where permissions were set incorrectly.
```
