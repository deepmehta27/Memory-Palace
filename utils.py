import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, List, Dict

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

console = Console()
DATA_DIR = Path("data")

# -------------------------
# File helpers
# -------------------------
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
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        console.print(f"[red]Error saving JSON: {e}[/red]")
        return False

def load_json(file_path: str, default: Any = None) -> Any:
    """
    Load data from JSON file.
    Returns {} by default (better for stats dicts) unless a different default is provided.
    """
    if default is None:
        default = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        console.print(f"[red]Error: Invalid JSON in {file_path}[/red]")
        return default
    except Exception as e:
        console.print(f"[red]Error loading JSON: {e}[/red]")
        return default

def ensure_data_dir() -> Path:
    """Ensure the data directory exists and return it."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR

# -------------------------
# Console helpers
# -------------------------
def print_welcome():
    """Print a fancy welcome message."""
    welcome_text = Text("🏛️  Memory Palace CLI", style="bold magenta")
    subtitle = Text("Transform your notes into memorable study experiences!", style="italic cyan")
    panel = Panel(f"{welcome_text}\n{subtitle}", border_style="blue", padding=(1, 2))
    console.print(panel)

def print_success(message: str):
    console.print(f"[green]✅ {message}[/green]")

def print_error(message: str):
    console.print(f"[red]❌ {message}[/red]")

def print_info(message: str):
    console.print(f"[blue]ℹ️  {message}[/blue]")

# -------------------------
# Gemini CLI helpers
# -------------------------
def is_exe_in_path(exe: str) -> bool:
    return shutil.which(exe) is not None

def _extract_first_json_blob(text: str) -> Any:
    """Extract and parse the first top-level JSON object/array from a string."""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
    if not m:
        raise RuntimeError("Could not find JSON in Gemini output.")
    return json.loads(m.group(1))

def gemini_json(prompt: str, files: List[Path] | None = None, model: str = "gemini-2.5-pro", timeout: int = 120) -> Any:
    """
    Call Gemini CLI expecting JSON. Returns parsed Python object.
    Uses: gemini ask --model <model> --json --input <prompt> [<files...>]
    """
    if not is_exe_in_path("gemini"):
        raise RuntimeError("Gemini CLI not found. Install with: npm install -g @google/gemini-cli")

    files = files or []
    cmd = ["gemini", "ask", "--model", model, "--json", "--input", prompt]
    for f in files:
        cmd.append(str(f))

    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=(os.name == "nt")  # helps on Windows
    )
    output = (res.stdout or res.stderr or "").strip()
    if res.returncode != 0:
        raise RuntimeError(f"Gemini CLI error (code {res.returncode}): {output[:400]}")
    if not output:
        raise RuntimeError("Empty response from Gemini CLI")
    return _extract_first_json_blob(output)

def gemini_text(prompt: str, files: List[Path] | None = None, model: str = "gemini-2.5-pro", timeout: int = 120) -> str:
    """
    Call Gemini CLI expecting plain text. Returns stdout/stderr string.
    Uses: gemini ask --model <model> --input <prompt> [<files...>]
    """
    if not is_exe_in_path("gemini"):
        raise RuntimeError("Gemini CLI not found. Install with: npm install -g @google/gemini-cli")

    files = files or []
    cmd = ["gemini", "ask", "--model", model, "--input", prompt]
    for f in files:
        cmd.append(str(f))

    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=(os.name == "nt")
    )
    output = (res.stdout or res.stderr or "").strip()
    if res.returncode != 0:
        raise RuntimeError(f"Gemini CLI error (code {res.returncode}): {output[:400]}")
    if not output:
        raise RuntimeError("Empty response from Gemini CLI")
    return output

# Backward-compatible wrapper (kept for your existing calls)
def call_gemini_cli(prompt: str) -> str:
    """Legacy wrapper: returns plain text for a simple prompt."""
    try:
        return gemini_text(prompt)
    except subprocess.TimeoutExpired:
        console.print("[red]Gemini CLI timeout - request took too long[/red]")
        return ""
    except FileNotFoundError:
        console.print("[red]Gemini CLI not found. Install with: npm install -g @google/gemini-cli[/red]")
        return ""
    except Exception as e:
        console.print(f"[red]Error calling Gemini CLI: {e}[/red]")
        return ""

def test_gemini_connection() -> bool:
    """Test if Gemini CLI is working."""
    try:
        resp = call_gemini_cli("Say 'Hello' and nothing else")
        return bool(resp and "hello" in resp.lower())
    except Exception:
        return False
