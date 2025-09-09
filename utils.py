import json
import os, shutil, subprocess
from pathlib import Path
from typing import List, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from pypdf import PdfReader
from dotenv import load_dotenv
from rich import box  # kept if used elsewhere

# Resolve Gemini binary once
GEMINI_BIN = shutil.which("gemini") or "gemini"

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
        return {}  # Return empty dict instead of list
    except json.JSONDecodeError:
        console.print(f"[red]Error: Invalid JSON in {file_path}[/red]")
        return {}
    except Exception as e:
        console.print(f"[red]Error loading JSON: {e}[/red]")
        return {}

def call_gemini_cli(prompt: str, model: str | None = None, timeout: int = 180) -> str:
    """
    Call the Gemini CLI using modern flags, forcing UTF-8.
    Falls back to sending bytes if Windows text encoding chokes.
    """
    env = os.environ.copy()
    # Accept either key name
    if "GEMINI_API_KEY" not in env and "GOOGLE_AI_STUDIO_API_KEY" in env:
        env["GEMINI_API_KEY"] = env["GOOGLE_AI_STUDIO_API_KEY"]

    use_model = model or env.get("GEMINI_MODEL", "gemini-2.5-pro")
    cmd = [GEMINI_BIN, "-m", use_model, "-p", ""]  # prompt via stdin

    try:
        try:
            # Primary path: send text with explicit UTF-8
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                env=env,
                shell=False,          # avoids UNC issues with cmd.exe
                timeout=timeout,
            )
            stdout, stderr = proc.stdout, proc.stderr
        except UnicodeEncodeError:
            # Fallback: send bytes, then decode output as UTF-8
            proc = subprocess.run(
                cmd,
                input=prompt.encode("utf-8", "replace"),
                capture_output=True,
                text=False,
                env=env,
                shell=False,
                timeout=timeout,
            )
            stdout = (proc.stdout or b"").decode("utf-8", "replace")
            stderr = (proc.stderr or b"").decode("utf-8", "replace")

        if proc.returncode != 0:
            console.print(f"[red]Gemini CLI failed ({proc.returncode}): {stderr.strip()}[/red]")
            return ""
        return (stdout or "").strip()

    except subprocess.TimeoutExpired:
        console.print("[red]Gemini CLI timed out[/red]")
        return ""
    except FileNotFoundError:
        console.print("[red]Gemini CLI not found. Install with: npm install -g @google/gemini-cli[/red]")
        return ""
    except Exception as e:
        console.print(f"[red]Error running Gemini CLI: {e}[/red]")
        return ""


# def call_gemini_cli(prompt: str, model: str | None = None, timeout: int = 180) -> str:
#     """
#     Call the Gemini CLI using modern flags.
#     - Uses stdin for the prompt (handles long inputs safely).
#     - Avoids shell to prevent UNC path issues with cmd.exe.
#     - Accepts either GEMINI_API_KEY or GOOGLE_AI_STUDIO_API_KEY.
#     """
#     env = os.environ.copy()

#     # Prefer GEMINI_API_KEY; fall back to GOOGLE_AI_STUDIO_API_KEY if needed
#     if "GEMINI_API_KEY" not in env and "GOOGLE_AI_STUDIO_API_KEY" in env:
#         env["GEMINI_API_KEY"] = env["GOOGLE_AI_STUDIO_API_KEY"]

#     use_model = model or env.get("GEMINI_MODEL", "gemini-2.5-pro")

#     # Build command; pass empty -p and feed prompt via stdin to avoid long cmd lines
#     cmd = [GEMINI_BIN, "-m", use_model, "-p", ""]

#     try:
#         proc = subprocess.run(
#             cmd,
#             input=prompt,               # send the prompt via stdin
#             capture_output=True,
#             text=True,
#             env=env,
#             shell=False,                # critical: avoids cmd.exe (UNC-safe)
#             timeout=timeout,
#         )
#         if proc.returncode != 0:
#             # Show stderr but also return "" so callers can fallback
#             console.print(f"[red]Gemini CLI failed ({proc.returncode}): {proc.stderr.strip()}[/red]")
#             return ""
#         return (proc.stdout or "").strip()
#     except subprocess.TimeoutExpired:
#         console.print("[red]Gemini CLI timeout - request took too long[/red]")
#         return ""
#     except FileNotFoundError:
#         console.print("[red]Gemini CLI not found. Install with: npm install -g @google/gemini-cli[/red]")
#         return ""
#     except Exception as e:
#         console.print(f"[red]Error calling Gemini CLI: {e}[/red]")
#         return ""

# PDF reading functions
def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF file."""
    try:
        reader = PdfReader(str(pdf_path))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")  # try empty password
            except Exception:
                return ""

        texts = []
        for page in reader.pages:
            try:
                txt = page.extract_text() or ""
                texts.append(txt.strip())
            except Exception:
                continue
        return "\n\n".join(texts).strip()
    except ImportError:
        console.print("[red]PyPDF not installed. Install with: pip install pypdf[/red]")
        return ""
    except Exception as e:
        console.print(f"[red]Error reading PDF: {e}[/red]")
        return ""

def read_notes_file(path: Path) -> str:
    """Read content from notes file (supports .md, .txt, .pdf)."""
    ext = path.suffix.lower()
    if ext in {".md", ".txt"}:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            console.print(f"[red]Error reading {path}: {e}[/red]")
            return ""
    elif ext == ".pdf":
        return extract_text_from_pdf(path)
    else:
        console.print(f"[red]Unsupported file type: {ext}[/red]")
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
    Call Gemini CLI for JSON responses. Used by mcq.py.
    We build one big prompt that includes file contents (already chunked upstream).
    """
    full_prompt = prompt
    if files:
        for file_path in files:
            try:
                content = read_notes_file(file_path)
                if content:
                    full_prompt += f"\n\nFile content from {file_path.name}:\n{content}"
            except Exception as e:
                console.print(f"[red]Error reading {file_path}: {e}[/red]")

    response = call_gemini_cli(full_prompt, model=model)

    # Try to parse as JSON
    try:
        return json.loads(response)
    except Exception:
        # Return the raw response if JSON parsing fails
        return response

def test_gemini_connection() -> bool:
    """Test if Gemini CLI is working."""
    try:
        response = call_gemini_cli("Say 'Hello' and nothing else")
        return bool(response and "hello" in response.lower())
    except Exception:
        return False
