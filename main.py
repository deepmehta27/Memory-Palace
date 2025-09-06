#!/usr/bin/env python3
"""
Memory Palace CLI - Transform your notes into memorable study experiences!
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from utils import (
        print_welcome, print_success, print_error, print_info,
        ensure_data_dir, load_json, console
    )
    from flashcards import generate_flashcards_from_file
    from quiz import start_quiz
    # NEW: MCQ feature
    from mcq import generate_mcqs, run_mcq_quiz
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all files are in the same directory and dependencies are installed.")
    sys.exit(1)


# =============================
# Interactive Mode (Menu)
# =============================
def interactive_mode():
    """Interactive menu-driven mode."""
    while True:
        console.print("\n[bold cyan]🎯 What would you like to do?[/bold cyan]")
        console.print("1. 📚 Generate flashcards from notes")
        console.print("2. 🎯 Start interactive quiz")
        console.print("3. 📊 View study statistics")
        console.print("4. 🎮 Run demo with sample data")
        console.print("5. 🔍 Debug/check setup")
        console.print("6. ❓ Help & commands")
        console.print("7. 📝 Generate MCQs from notes   [new]")
        console.print("8. 🧪 Start MCQ quiz             [new]")
        console.print("0. 👋 Exit")

        choice = input("\nChoose an option (0-8): ").strip()

        try:
            if choice == "0":
                print_success("Thanks for using Memory Palace CLI! Happy studying! 📚✨")
                break
            elif choice == "1":
                handle_generate()
            elif choice == "2":
                handle_quiz()
            elif choice == "3":
                handle_stats()
            elif choice == "4":
                handle_demo()
            elif choice == "5":
                handle_debug()
            elif choice == "6":
                show_help()
            elif choice == "7":
                handle_mcq_generate()
            elif choice == "8":
                handle_mcq_quiz()
            else:
                print_error("Invalid choice. Please enter a number 0-8.")
        except KeyboardInterrupt:
            print_info("\nOperation cancelled. Returning to menu...")
        except Exception as e:
            print_error(f"Error: {e}")


# =============================
# Flashcards (existing)
# =============================
def handle_generate():
    """Handle flashcard generation interactively."""
    console.print("\n[bold blue]📚 Generate Flashcards[/bold blue]")

    data_dir = Path("data")
    if data_dir.exists():
        md_files = list(data_dir.glob("*.md")) + list(data_dir.glob("*.txt"))
        if md_files:
            console.print("\n[cyan]Available notes files:[/cyan]")
            for i, file in enumerate(md_files, 1):
                console.print(f"  {i}. {file.name}")

            file_choice = input("\nChoose a file number or enter custom path: ").strip()
            try:
                file_index = int(file_choice) - 1
                if 0 <= file_index < len(md_files):
                    notes_file = str(md_files[file_index])
                else:
                    notes_file = file_choice
            except ValueError:
                notes_file = file_choice
        else:
            notes_file = input("Enter path to your notes file: ").strip()
    else:
        notes_file = input("Enter path to your notes file: ").strip()

    output_file = input("Output file (default: data/flashcards.json): ").strip() or "data/flashcards.json"

    ensure_data_dir()
    if generate_flashcards_from_file(notes_file, output_file):
        print_success("Flashcards generated! You can now take a quiz.")
    else:
        print_error("Failed to generate flashcards")


def handle_quiz():
    """Handle quiz interactively."""
    console.print("\n[bold blue]🎯 Interactive Quiz[/bold blue]")

    flashcards_file = "data/flashcards.json"
    if not Path(flashcards_file).exists():
        print_error("No flashcards found!")
        choice = input("Generate flashcards first? (y/n): ").strip().lower()
        if choice == "y":
            handle_generate()
        return

    try:
        num_questions = int(input("How many questions? (default: 5): ").strip() or "5")
    except ValueError:
        num_questions = 5

    start_quiz(flashcards_file, num_questions)


# =============================
# MCQ (new)
# =============================
def handle_mcq_generate():
    """Interactive MCQ generation using mcq.py logic."""
    console.print("\n[bold blue]📝 Generate MCQs[/bold blue]")

    # Offer files in ./data
    data_dir = Path("data")
    notes_path = None
    if data_dir.exists():
        md_files = list(data_dir.glob("*.md")) + list(data_dir.glob("*.txt"))
        if md_files:
            console.print("\n[cyan]Available notes files:[/cyan]")
            for i, f in enumerate(md_files, 1):
                console.print(f"  {i}. {f.name}")
            sel = input("\nChoose a file number or enter custom path: ").strip()
            try:
                idx = int(sel) - 1
                notes_path = md_files[idx] if 0 <= idx < len(md_files) else Path(sel)
            except ValueError:
                notes_path = Path(sel)
        else:
            notes_path = Path(input("Enter path to your notes file: ").strip())
    else:
        notes_path = Path(input("Enter path to your notes file: ").strip())

    if not notes_path or not notes_path.exists():
        print_error("Notes file not found.")
        return

    try:
        num = int(input("Number of MCQs to aim for (default: 10): ").strip() or "10")
    except ValueError:
        num = 10

    use_gemini_input = input("Use Gemini for generation? (Y/n): ").strip().lower()
    use_gemini = False if use_gemini_input == "n" else True

    ensure_data_dir()
    out = Path("data/mcqs.json")
    try:
        generate_mcqs(notes_path, out_path=out, num_questions=num, use_gemini=use_gemini)
        print_success(f"MCQs saved → {out}")
    except Exception as e:
        print_error(f"Failed to generate MCQs: {e}")


def handle_mcq_quiz():
    """Interactive MCQ quiz."""
    console.print("\n[bold blue]🧪 MCQ Quiz[/bold blue]")

    mcq_file = Path("data/mcqs.json")
    if not mcq_file.exists():
        print_error("No MCQs found! Generate them first.")
        choice = input("Generate MCQs now? (y/n): ").strip().lower()
        if choice == "y":
            handle_mcq_generate()
        return

    try:
        limit = int(input("How many MCQs? (blank = all): ").strip() or "0")
        limit = None if limit == 0 else limit
    except ValueError:
        limit = None

    try:
        run_mcq_quiz(mcq_path=mcq_file, limit=limit, shuffle=True)
    except Exception as e:
        print_error(f"Error running MCQ quiz: {e}")


# =============================
# Misc (existing)
# =============================
def handle_stats():
    """Handle stats display."""
    console.print("\n[bold blue]📊 Study Statistics[/bold blue]")

    progress_file = "data/progress.json"
    progress_data = load_json(progress_file)

    if not progress_data:
        print_info("No study statistics yet. Take a quiz to start tracking!")
        return

    display_stats(progress_data)


def handle_demo():
    """Handle demo mode."""
    console.print("\n[bold blue]🎮 Demo Mode[/bold blue]")
    print_info("Creating sample data and running demo...")

    ensure_data_dir()

    sample_notes = """# Biology Study Notes

**Photosynthesis**: The process by which plants convert sunlight, carbon dioxide, and water into glucose and oxygen.
**Mitochondria**: Known as the powerhouse of the cell, these organelles produce ATP through cellular respiration.
**DNA**: Deoxyribonucleic acid, the hereditary material that contains genetic instructions for all living organisms.
**Osmosis**: The movement of water molecules through a semipermeable membrane from an area of high concentration to low concentration.
**ATP**: Adenosine triphosphate, the main energy currency of the cell.
**Cell Membrane**: The flexible boundary that controls what enters and exits the cell.
**Chloroplast**: The organelle where photosynthesis occurs in plant cells.
"""
    sample_path = Path("data/notes.md")
    sample_path.write_text(sample_notes, encoding="utf-8")
    print_success("Sample notes created!")

    if generate_flashcards_from_file(str(sample_path)):
        print_success("Demo flashcards generated!")
        choice = input("Start demo quiz? (y/n): ").strip().lower()
        if choice == "y":
            start_quiz("data/flashcards.json", 3)


def handle_debug():
    """Handle debug mode."""
    console.print("\n[bold blue]🔍 Debug & Setup Check[/bold blue]")

    import subprocess

    required_packages = ['click', 'colorama', 'rich', 'python-dotenv', 'requests']
    for package in required_packages:
        try:
            __import__(package)
            console.print(f"[green]✅ {package} installed[/green]")
        except ImportError:
            console.print(f"[red]❌ {package} NOT installed[/red]")

    api_key = os.getenv('GOOGLE_AI_STUDIO_API_KEY')
    if api_key:
        console.print(f"[green]✅ API key found (length: {len(api_key)})[/green]")
    else:
        console.print("[red]❌ API key NOT found[/red]")
        console.print("[yellow]Create .env file with: GOOGLE_AI_STUDIO_API_KEY=your-key[/yellow]")

    if Path('.env').exists():
        console.print("[green]✅ .env file exists[/green]")
    else:
        console.print("[red]❌ .env file missing[/red]")

    try:
        result = subprocess.run(['gemini', '--version'], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            console.print(f"[green]✅ Gemini CLI installed: {result.stdout.strip()}[/green]")
        else:
            console.print("[red]❌ Gemini CLI not working[/red]")
    except Exception:
        console.print("[red]❌ Gemini CLI not found[/red]")
        console.print("[yellow]Install with: npm install -g @google/gemini-cli[/yellow]")

    required_files = ['utils.py', 'flashcards.py', 'quiz.py', 'mcq.py']
    for file in required_files:
        if Path(file).exists():
            console.print(f"[green]✅ {file} exists[/green]")
        else:
            console.print(f"[red]❌ {file} missing[/red]")


def show_help():
    """Show help information."""
    console.print("\n[bold blue]❓ Help & Commands[/bold blue]")

    help_text = """
[cyan]Memory Palace CLI - Help Guide[/cyan]

[bold]🏛️ What is Memory Palace CLI?[/bold]
Transform boring study notes into fun, memorable flashcards with AI-generated 
mnemonics and interactive quizzes!

[bold]🚀 Quick Start:[/bold]
1. Put your notes in .md or .txt files (format: "Term: Definition")
2. Choose option 1 to generate flashcards
3. Choose option 2 to start quiz
4. Option 7 to generate MCQs; Option 8 to take an MCQ quiz
5. Let AI create funny memory hooks to help you remember!

[bold]📝 Notes Format:[/bold]
**Photosynthesis**: The process plants use to convert sunlight into energy
**DNA**: Contains genetic instructions for living organisms

[bold]🔧 Setup Requirements:[/bold]
• Gemini CLI: npm install -g @google/gemini-cli
• API Key: Get from https://makersuite.google.com/app/apikey
• Create .env file with: GOOGLE_AI_STUDIO_API_KEY=your-key
"""
    console.print(help_text)


def display_stats(progress_data):
    """Display formatted statistics."""
    total_sessions = progress_data.get('total_sessions', 0)
    total_questions = progress_data.get('total_questions', 0)
    correct_answers = progress_data.get('correct_answers', 0)
    difficult_concepts = progress_data.get('difficult_concepts', {})

    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0

    console.print(f"\n[bold]📊 Your Study Statistics[/bold]")
    console.print(f"Total Quiz Sessions: {total_sessions}")
    console.print(f"Questions Answered: {total_questions}")
    console.print(f"Correct Answers: {correct_answers}")
    console.print(f"Overall Accuracy: {accuracy:.1f}%")

    if accuracy >= 80:
        console.print("[green]🎉 Excellent work! You're mastering this material![/green]")
    elif accuracy >= 60:
        console.print("[yellow]👍 Good job! Keep practicing those tricky concepts.[/yellow]")
    else:
        console.print("[blue]💪 Keep studying! Every expert was once a beginner.[/blue]")

    if difficult_concepts:
        console.print("\n[bold yellow]🎯 Concepts to Review (most missed):[/bold yellow]")
        sorted_concepts = sorted(difficult_concepts.items(), key=lambda x: x[1], reverse=True)
        for concept, misses in sorted_concepts[:5]:
            console.print(f"• {concept} [dim](missed {misses} times)[/dim]")


# =============================
# CLI entry (adds simple arg support for MCQ)
# =============================
def main():
    """Main entry point."""
    print_welcome()

    # Basic command-line mode for MCQ
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        cmd = args[0].lower()

        if cmd == "mcq-generate":
            if len(args) < 2:
                print_error("Usage: python main.py mcq-generate <notes.md> [--num 10] [--no-gemini]")
                return
            notes = Path(args[1])
            num = 10
            use_gemini = True
            if "--num" in args:
                try:
                    num = int(args[args.index("--num") + 1])
                except Exception:
                    pass
            if "--no-gemini" in args:
                use_gemini = False

            ensure_data_dir()
            try:
                generate_mcqs(notes, out_path=Path("data/mcqs.json"),
                              num_questions=num, use_gemini=use_gemini)
                print_success("MCQs generated → data/mcqs.json")
            except Exception as e:
                print_error(f"MCQ generation failed: {e}")
            return

        if cmd == "mcq-quiz":
            limit = None
            if "--num" in args:
                try:
                    limit = int(args[args.index("--num") + 1])
                except Exception:
                    pass
            try:
                run_mcq_quiz(Path("data/mcqs.json"), limit=limit, shuffle=True)
            except Exception as e:
                print_error(f"MCQ quiz failed: {e}")
            return

        console.print("[yellow]Unknown command or not supported here. Starting interactive mode...[/yellow]")

    # Interactive
    try:
        interactive_mode()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


if __name__ == '__main__':
    main()
