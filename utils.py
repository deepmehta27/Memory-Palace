import json
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

console = Console()

def load_file(file_path: str) -> str:
    """Load content from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        console.print(f"[red]Error: File {file_path} not found[/red]")
        return ""
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        return ""

def save_json(data: Any, file_path: str) -> bool:
    """Save data to JSON file."""
    try:
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        console.print(f"[red]Error saving JSON: {e}[/red]")
        return False

def load_json(file_path: str) -> Any:
    """Load data from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        console.print(f"[red]Error: Invalid JSON in {file_path}[/red]")
        return []
    except Exception as e:
        console.print(f"[red]Error loading JSON: {e}[/red]")
        return []

def call_gemini_cli(prompt: str) -> str:
    """Call the Gemini CLI with a prompt."""
    try:
        # On Windows, try both 'gemini' and 'gemini.cmd'
        import platform
        if platform.system() == "Windows":
            gemini_cmd = 'gemini'
        else:
            gemini_cmd = 'gemini'
            
        # Use the Gemini CLI
        result = subprocess.run(
            [gemini_cmd, prompt],
            capture_output=True,
            text=True,
            timeout=30,
            shell=True  # Helps on Windows
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            console.print(f"[red]Gemini CLI error: {result.stderr}[/red]")
            return ""
            
    except subprocess.TimeoutExpired:
        console.print("[red]Gemini CLI timeout - request took too long[/red]")
        return ""
    except FileNotFoundError:
        console.print("[red]Gemini CLI not found. Install with: npm install -g @google/gemini-cli[/red]")
        return ""
    except Exception as e:
        console.print(f"[red]Error calling Gemini CLI: {e}[/red]")
        return ""

def print_welcome():
    """Print a fancy welcome message."""
    welcome_text = Text("🏛️  Memory Palace CLI", style="bold magenta")
    subtitle = Text("Transform your notes into memorable study experiences!", style="italic cyan")
    
    panel = Panel(
        f"{welcome_text}\n{subtitle}",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(panel)

def print_success(message: str):
    """Print a success message."""
    console.print(f"[green]✅ {message}[/green]")

def print_error(message: str):
    """Print an error message."""
    console.print(f"[red]❌ {message}[/red]")

def print_info(message: str):
    """Print an info message."""
    console.print(f"[blue]ℹ️  {message}[/blue]")

def ensure_data_dir():
    """Ensure the data directory exists."""
    Path("data").mkdir(exist_ok=True)

def gemini_json(prompt: str, files: List[Path] = None, model: str = "gemini-2.5-pro") -> Any:
    """
    Call Gemini CLI for JSON responses. This is used by mcq.py.
    """
    full_prompt = prompt
    if files:
        # For file-based prompts, we'll read the content and include it
        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                full_prompt += f"\n\nFile content from {file_path.name}:\n{content}"
            except Exception as e:
                console.print(f"[red]Error reading {file_path}: {e}[/red]")
    
    response = call_gemini_cli(full_prompt)
    
    # Try to parse as JSON
    try:
        import json
        return json.loads(response)
    except:
        # Return the raw response if JSON parsing fails
        return response

def test_gemini_connection() -> bool:
    """Test if Gemini CLI is working."""
    try:
        response = call_gemini_cli("Say 'Hello' and nothing else")
        return bool(response and "hello" in response.lower())
    except:
        return False