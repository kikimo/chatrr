#!/usr/bin/env python3
"""
Simple GDB Extension - Hello World
This demonstrates the basics of writing a GDB extension in Python.
"""

import sys
import json
import logging
import os

# Get current directory of this script
scriptDir = os.path.dirname(os.path.abspath(__file__))

# Get current Python version
pythonVersion = f"{sys.version_info.major}.{sys.version_info.minor}"
sys.path.insert(0, os.path.join(scriptDir, '.venv', 'lib', f'python{pythonVersion}', 'site-packages'))

import gdb
from langgraph.prebuilt import create_react_agent
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from typing import TypedDict, Annotated
import re

def read_file(file_path: str, start_line: int, end_line: int) -> str:
    """Read source code from a file between specified line numbers.

    Args:
        file_path: Path to the file to read
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed, inclusive)

    Returns:
        String containing the requested lines with line numbers
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            # Convert to 0-indexed
            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), end_line)

            result = []
            for i in range(start_idx, end_idx):
                result.append(f"{i+1:4d}: {lines[i]}")
            return ''.join(result)
    except Exception as e:
        return f"Error reading file: {str(e)}"

def strip_ansi_codes(text: str) -> str:
    """Strip ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def run_cmd(cmd: str) -> str:
    """Execute a GDB/RR command and return the output.

    Args:
        cmd: The GDB command to execute

    Returns:
        Command output as string
    """
    try:
        # Debug: print GDB state before executing
        print(f"[DEBUG] About to execute: {cmd}")
        print(f"[DEBUG] Inferior state: {gdb.selected_inferior().is_valid()}")

        # # Check if we're in rr replay
        # try:
        #     # In rr replay, check if program is already running
        #     frame = gdb.selected_frame()
        #     print(f"[DEBUG] Current frame exists, program state: running")
        # except:
        #     print(f"[DEBUG] No frame selected, program not started")
        # import pdb; pdb.set_trace()
        result = gdb.execute(cmd, from_tty=False, to_string=True)

        print(f"[DEBUG] Command completed successfully")
        # Strip ANSI color codes
        return strip_ansi_codes(result)
    except Exception as e:
        print(f"[DEBUG] Exception occurred: {type(e).__name__}: {str(e)}")
        return f"Error executing command '{cmd}': {str(e)}"

class HelloWithArgsCommand(gdb.Command):
    """A command that demonstrates argument handling"""

    def __init__(self):
        super(HelloWithArgsCommand, self).__init__("greet", gdb.COMMAND_USER)

    def invoke(self, argument, from_tty):
        """Handle the command with arguments"""
        args = gdb.string_to_argv(argument)

        if not args:
            print("Usage: greet <name> [message]")
            return

        name = args[0]
        message = " ".join(args[1:]) if len(args) > 1 else "Welcome!"

        print(f"{message} {name}!")

class XrunCommand(gdb.Command):
    """Execute gdb commands and log results to terminal"""
    
    def __init__(self):
        super(XrunCommand, self).__init__("xrun", gdb.COMMAND_USER)
        self.logger = self._setup_logger()
        self.history = []
    
    def _setup_logger(self):
        """Setup logging configuration to write to file"""
        logger = logging.getLogger('chatgdb')
        logger.setLevel(logging.INFO)
        
        # Create file handler
        file_handler = logging.FileHandler('chatgdb.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Create formatter with timestamp
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(file_handler)
        
        return logger
    
    def invoke(self, arg, from_tty):
        """Execute the xrun command"""
        if not arg:
            error_msg = "No arguments provided for xrun command"
            self.logger.error(error_msg)
            print(f"Error: {error_msg}")
            return
        
        try:
            # Log the command being executed
            self.logger.info(f"Executing command: {arg}")
            
            # Execute the gdb command
            result = gdb.execute(arg, from_tty=False, to_string=True)
            # TODO: strip color codes from result
            self.history.append(f'<gdb_command><command>{arg}</command><command_result>{result}</command_result></gdb_command>')
            
            # Log the result
            if result:
                # self.logger.info(f"Command result: {result}")
                self.logger.info(f"\n{'\n'.join(self.history)}")
            
            # Print to current gdb session terminal
            if result:
                print(result, end='')
                
        except Exception as e:
            error_msg = f"Error executing command '{arg}': {str(e)}"
            self.logger.error(error_msg)
            print(f"Error: {error_msg}")
            self.history.append(f'<gdb_command><command>{arg}</command><command_error>{error_msg}</command_error></gdb_command>')

# Register the command when the script is loaded
XrunCommand()

# Register the commands
HelloWithArgsCommand()

print("GDB extension loaded! Try 'hello' or 'greet <name>'")

# # Azure OpenAI configuration (hardcoded for GDB compatibility)
# api_version = "2024-02-15-preview"
# azure_deployment = "gpt-5"
# azure_endpoint = "https://fzuwwl.openai.azure.com/"

# try:
#     llm = AzureChatOpenAI(
#         azure_endpoint=azure_endpoint,
#         openai_api_key=openai_api_key,
#         azure_deployment=azure_deployment,
#         api_version=api_version,
#         max_tokens=None,
#         timeout=None,
#         max_retries=3,
#     )
# except Exception as e:
#     print(f"Warning: Failed to initialize LLM: {e}")
#     print("The 'analyze' command will not be available")
#     llm = None

# # Define tools for the agent
# @tool
# def gdb_command(cmd: str) -> str:
#     """Execute any rr/gdb command and get the output. This is your primary tool for inspecting the program state.

#     Common commands:
#     - run: Run to crash/breakpoint
#     - bt/where: Show backtrace
#     - list: Show source code
#     - print <var>: Print variable value
#     - info locals: Show local variables
#     - info args: Show function arguments
#     - watch <var>: Set hardware watchpoint
#     - reverse-continue: Run backwards to watchpoint
#     - break <location>: Set breakpoint
#     - other gdb/rr commands available
#     """
#     print(f"🔧 Executing: {cmd}")
#     result = run_cmd(cmd)
#     print(f"📋 Result:\n{result}")
#     return result

# @tool
# def read_source_file(file_path: str, line_start: int, line_end: int) -> str:
#     """Read source code from a file between specified line numbers.

#     Use this to examine code context around crash locations, understand function
#     implementations, and check for error handling logic.

#     Args:
#         file_path: Path to the source file
#         line_start: Starting line number (1-indexed)
#         line_end: Ending line number (1-indexed, inclusive)
#     """
#     print(f"📖 Reading: {file_path} lines {line_start}-{line_end}")
#     result = read_file(file_path, line_start, line_end)
#     print(f"📄 Content:\n{result}")
#     return result

# # Load system prompt
# system_prompt_path = os.path.join(scriptDir, 'system_prompt.md')
# try:
#     with open(system_prompt_path, 'r') as f:
#         system_prompt = f.read()
# except FileNotFoundError:
#     system_prompt = "You are a debugging assistant using Mozilla rr. Use the gdb_command and read_source_file tools to analyze bugs."


import re
import os
import json
from openai import AzureOpenAI

scriptDir = os.path.dirname(os.path.abspath(__file__))

api_version = "2024-02-15-preview"
azure_deployment = "gpt-5"
openai_api_key = ""
azure_endpoint = "https://fzuwwl.openai.azure.com/"

def read_file(file_path: str=None, start_line: int=None, end_line: int=None) -> str:
    if file_path is None or start_line is None or end_line is None:
        return "file_path and start_line and end_line are required"

    """Read source code from a file between specified line numbers.

    Args:
        file_path: Path to the file to read
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed, inclusive)

    Returns:
        String containing the requested lines with line numbers
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            # Convert to 0-indexed
            start_idx = max(0, start_line - 1)
            end_idx = min(len(lines), end_line)

            result = []
            for i in range(start_idx, end_idx):
                result.append(f"{i+1:4d}: {lines[i]}")
            return ''.join(result)
    except Exception as e:
        return f"Error reading file: {str(e)}"

def strip_ansi_codes(text: str) -> str:
    """Strip ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def run_cmd(cmd: str=None) -> str:
    """Execute a GDB/RR command and return the output.

    Args:
        cmd: The GDB command to execute

    Returns:
        Command output as string
    """
    import gdb
    try:
        # Debug: print GDB state before executing
        if cmd is None:
            return "No debug command provided"

        print(f"[DEBUG] About to execute: {cmd}")
        print(f"[DEBUG] Inferior state: {gdb.selected_inferior().is_valid()}")

        # # Check if we're in rr replay
        # try:
        #     # In rr replay, check if program is already running
        #     frame = gdb.selected_frame()
        #     print(f"[DEBUG] Current frame exists, program state: running")
        # except:
        #     print(f"[DEBUG] No frame selected, program not started")
        # import pdb; pdb.set_trace()
        result = gdb.execute(cmd, from_tty=False, to_string=True)

        print(f"[DEBUG] Command completed successfully")
        # Strip ANSI color codes
        return strip_ansi_codes(result)
    except Exception as e:
        print(f"[DEBUG] Exception occurred: {type(e).__name__}: {str(e)}")
        return f"Error executing command '{cmd}': {str(e)}"

def call_function(tool_call):
    """执行工具调用"""
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    
    if function_name == "run_debug_cmd":
        result = run_cmd(arguments["cmd"])
        return str(result)
    elif function_name == "read_file":
        result = read_file(arguments["file_path"], arguments["start_line"], arguments["end_line"])
        return str(result)
    else:
        return f"Unknown function: {function_name}"

class DebugAgent(object):
    def __init__(self) -> None:
        self.messages = []
        system_prompt_path = os.path.join(scriptDir, 'system_prompt.md')
        with open(system_prompt_path, 'r') as file:
            system_prompt = file.read()
            self.messages.append({'role': 'system', 'content': system_prompt})

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "run_debug_cmd",
                    "description": "Run gdb/rr command like `print var`, `cont`, `reverse-cont`",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cmd": {
                                "type": "string",
                                "description": "gdb/rr command to run",
                            }
                        },
                        "required": ["cmd"],
                        "additionalProperties": False
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read source code from a file between specified line numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to read",
                            },
                            "start_line": {
                                "type": "integer",
                                "description": "Starting line number (1-indexed)",
                            },
                            "end_line": {
                                "type": "integer",
                                "description": "Ending line number (1-indexed, inclusive)",
                            },
                            # "required": ["file_path", "start_line", "end_line"],
                            "additionalProperties": False
                        },
                    },
                }
            },
        ]

        self.client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            api_key=openai_api_key,
        )

    def invoke(self, message: str):
        self.messages.append({'role': 'user', 'content': message})
        while True:
            resp = self.client.chat.completions.create(
                messages=self.messages,
                model=azure_deployment,
                tools=self.tools,
                tool_choice="auto",
                stream=False,
            )
            msg = resp.choices[0].message
            self.messages.append(msg)
            print(f'Assistant: {msg.content}')

            if not msg.tool_calls:
                break

            print("🔧 正在调用工具...")
            for tool_call in msg.tool_calls:
                result = call_function(tool_call)
                self.messages.append({'role': 'tool', 'content': result, 'tool_call_id': tool_call.id})
                print(f'Tool: {result}')

            resp = self.client.chat.completions.create(
                messages=self.messages,
                model=azure_deployment,
                tools=self.tools,
                tool_choice="auto",
                stream=False,
            )

        import pdb; pdb.set_trace()
        # for event in stream:
        #     pass
        print(resp)


agent = DebugAgent()

class AnalyzeCommand(gdb.Command):
    """Analyze the program using AI-powered debugging assistant.

    Usage: analyze <question>

    Example:
        analyze "Why did the program crash?"
        analyze "The output is wrong, debug why"
        analyze "Trace back where variable 'ptr' became NULL"
    """

    def __init__(self):
        super(AnalyzeCommand, self).__init__("analyze", gdb.COMMAND_USER)
        self.logger = logging.getLogger('chatgdb')

    def invoke(self, argument, from_tty):
        """Execute the analyze command."""
        if agent is None:
            print("Error: Agent not available. Check Azure OpenAI credentials.")
            return

        if not argument:
            print("Usage: analyze <question>")
            print("\nExample: analyze \"Why did the program crash?\"")
            return

        question = argument.strip()
        print(f"\n🤖 Analyzing: {question}\n")
        print("=" * 80)

        try:
            agent.invoke(question)
            print("\n" + "=" * 80)

        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}"
            self.logger.error(error_msg)
            print(f"Error: {error_msg}")
            import pdb; pdb.set_trace()

# Register commands
if agent is not None:
    AnalyzeCommand()
    print("✓ RR Debug Agent loaded!")
    print("  Use 'analyze <question>' to debug with AI assistance")
else:
    print("✗ Agent not available - check credentials")
