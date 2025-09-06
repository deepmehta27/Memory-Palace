import json
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from dotenv import load_dotenv

load_dotenv()

console = Console()

from pypdf import PdfReader

SUPPORTED_NOTE_EXTS = {".md", ".txt", ".pdf"}

def is_supported_notes_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_NOTE_EXTS

def list_notes_files(data_dir: Path) -> List[Path]:
    files: List[Path] = []
    if not data_dir.exists():
        return files
    for p in data_dir.iterdir():
        if p.is_file() and is_supported_notes_file(p):
            files.append(p)
    return sorted(files, key=lambda x: x.name.lower())

def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:
                return ""
        texts = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            texts.append(txt.strip())
        return "\n\n".join(texts).strip()
    except Exception:
        return ""

def read_notes_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".md", ".txt"}:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    return ""

def chunk_text(text: str, max_chars: int = 8000, overlap: int = 400) -> List[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        window = text[start:end]
        cut = window.rfind("\n\n")
        if cut < int(0.6 * len(window)):
            cut = len(window)
        chunk = text[start:start + cut].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = start + cut - overlap
        if start < 0:
            start = 0
    return chunks

def load_file(file_path: str) -> str:
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
    welcome_text = Text("Memory Palace CLI", style="bold magenta")
    subtitle = Text("Transform your notes into memorable study experiences!", style="italic cyan")
    
    panel = Panel(
        f"{welcome_text}\n{subtitle}",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(panel)

def print_success(message: str):
    console.print(f"[green]✅ {message}[/green]")

def print_error(message: str):
    console.print(f"[red]❌ {message}[/red]")

def print_info(message: str):
    console.print(f"[blue]ℹ️  {message}[/blue]")

def ensure_data_dir():
    Path("data").mkdir(exist_ok=True)

def test_gemini_connection() -> bool:
    try:
        response = call_gemini_cli("Say 'Hello' and nothing else")
        return bool(response and "hello" in response.lower())
    except:
        return False
