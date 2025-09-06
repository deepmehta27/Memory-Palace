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
    # ADDED: list_notes_files, is_supported_notes_file for PDF/.txt support
    from utils import (
        print_welcome, print_success, print_error, print_info,
        ensure_data_dir, load_json, console,
        list_notes_files, is_supported_notes_file
    )
    from flashcards import generate_flashcards_from_file
    from quiz import start_quiz
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all files are in the same directory and dependencies are installed.")
    sys.exit(1)

# ADDED: single place for data dir
DATA_DIR = Path("data")


def interactive_mode():
    """Interactive menu-driven mode."""
    while True:
        console.print("\n[bold cyan]🎯 What would you like to do?[/bold cyan]")
        
        # Simple menu without table for compatibility
        console.print("1. 📚 Generate flashcards from notes")
        console.print("2. 🎯 Start interactive quiz")
        console.print("3. 📊 View study statistics") 
        console.print("4. 🎮 Run demo with sample data")
        console.print("5. 🔍 Debug/check setup")
        console.print("6. ❓ Help & commands")
        console.print("0. 👋 Exit")
        
        choice = input("\nChoose an option (0-6): ").strip()
        
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
            else:
                print_error("Invalid choice. Please enter a number 0-6.")
        except KeyboardInterrupt:
            print_info("\nOperation cancelled. Returning to menu...")
        except Exception as e:
            print_error(f"Error: {e}")


def handle_generate():
    """Handle flashcard generation interactively (now supports .md, .txt, .pdf)."""
    console.print("\n[bold blue]📚 Generate Flashcards[/bold blue]")

    # Show available files (.md, .txt, .pdf) from data/
    ensure_data_dir()
    available = list_notes_files(DATA_DIR)

    notes_path: Path
    if available:
        console.print("\n[cyan]Available notes files:[/cyan]")
        for i, p in enumerate(available, start=1):
            console.print(f"  {i}. {p.name}")

        file_choice = input("\nChoose a file number or enter custom path: ").strip()
        if file_choice.isdigit():
            idx = int(file_choice)
            if 1 <= idx <= len(available):
                notes_path = available[idx - 1]
            else:
                print_error("Invalid selection number.")
                return
        else:
            notes_path = Path(file_choice).expanduser()
    else:
        console.print("[yellow]No notes found in data/. Add .md, .txt, or .pdf files.[/yellow]")
        custom = input("Enter path to your notes file: ").strip()
        notes_path = Path(custom).expanduser()

    # Validate selection/type
    if not notes_path.exists():
        print_error("File not found. Please check the path and try again.")
        return
    if not is_supported_notes_file(notes_path):
        print_error("Invalid file type. Please provide a .md, .txt, or .pdf file.")
        return

    # Ask output path (keep your original behavior)
    output_file = input("Output file (default: data/flashcards.json): ").strip()
    if not output_file:
        output_file = "data/flashcards.json"

    ensure_data_dir()
    # Keep your original generator signature and behavior
    if generate_flashcards_from_file(str(notes_path), output_file):
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
        else:
            return
    
    try:
        num_questions = int(input("How many questions? (default: 5): ").strip() or "5")
    except ValueError:
        num_questions = 5
    
    start_quiz(flashcards_file, num_questions)


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
    
    # Create sample notes
    sample_notes = """# Biology Study Notes

**Photosynthesis**: The process by which plants convert sunlight, carbon dioxide, and water into glucose and oxygen.

**Mitochondria**: Known as the powerhouse of the cell, these organelles produce ATP through cellular respiration.

**DNA**: Deoxyribonucleic acid, the hereditary material that contains genetic instructions for all living organisms.

**Osmosis**: The movement of water molecules through a semipermeable membrane from an area of high concentration to low concentration.

**ATP**: Adenosine triphosphate, the main energy currency of the cell.

**Cell Membrane**: The flexible boundary that controls what enters and exits the cell.

**Chloroplast**: The organelle where photosynthesis occurs in plant cells.
"""
    
    sample_path = "data/notes.md"
    with open(sample_path, 'w', encoding='utf-8') as f:
        f.write(sample_notes)
    
    print_success("Sample notes created!")
    
    if generate_flashcards_from_file(sample_path):
        print_success("Demo flashcards generated!")
        choice = input("Start demo quiz? (y/n): ").strip().lower()
        if choice == "y":
            start_quiz("data/flashcards.json", 3)


def handle_debug():
    """Handle debug mode."""
    console.print("\n[bold blue]🔍 Debug & Setup Check[/bold blue]")
    
    import subprocess
    
    # Check Python packages
    required_packages = ['click', 'colorama', 'rich', 'python-dotenv', 'requests']
    for package in required_packages:
        try:
            __import__(package)
            console.print(f"[green]✅ {package} installed[/green]")
        except ImportError:
            console.print(f"[red]❌ {package} NOT installed[/red]")
    
    # Check API key
    api_key = os.getenv('GOOGLE_AI_STUDIO_API_KEY')
    if api_key:
        console.print(f"[green]✅ API key found (length: {len(api_key)})[/green]")
    else:
        console.print("[red]❌ API key NOT found[/red]")
        console.print("[yellow]Create .env file with: GOOGLE_AI_STUDIO_API_KEY=your-key[/yellow]")
    
    # Check .env file
    if Path('.env').exists():
        console.print("[green]✅ .env file exists[/green]")
    else:
        console.print("[red]❌ .env file missing[/red]")
    
    # Check Gemini CLI
    try:
        result = subprocess.run(['gemini', '--version'], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            console.print(f"[green]✅ Gemini CLI installed: {result.stdout.strip()}[/green]")
        else:
            console.print("[red]❌ Gemini CLI not working[/red]")
    except Exception as e:
        console.print("[red]❌ Gemini CLI not found[/red]")
        console.print("[yellow]Install with: npm install -g @google/gemini-cli[/yellow]")
    
    # Check project files
    required_files = ['utils.py', 'flashcards.py', 'quiz.py']
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
1. Put your notes in .md, .txt, or .pdf files (format: "Term: Definition")
2. Choose option 1 to generate flashcards
3. Choose option 2 to start quiz
4. Let AI create funny memory hooks to help you remember!

[bold]📝 Notes Format:[/bold]
**Photosynthesis**: The process plants use to convert sunlight into energy
**DNA**: Contains genetic instructions for living organisms

[bold]🔧 Setup Requirements:[/bold]
• Gemini CLI: npm install -g @google/gemini-cli
• API Key: Get from https://makersuite.google.com/app/apikey
• Create .env file with: GOOGLE_AI_STUDIO_API_KEY=your-key

[bold]✨ Features:[/bold]
• AI-generated mnemonics and memory hooks
• Interactive quiz with personalized feedback  
• Progress tracking and adaptive learning
• All data stays local on your machine

[bold]🎯 Pro Tips:[/bold]
• Start with option 4 (Demo) to test everything
• Use clear "Term: Definition" format in notes
• Take multiple quizzes to see progress tracking
• AI creates funny analogies to help memory!
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
    
    # Difficult concepts
    if difficult_concepts:
        console.print("\n[bold yellow]🎯 Concepts to Review (most missed):[/bold yellow]")
        sorted_concepts = sorted(difficult_concepts.items(), key=lambda x: x[1], reverse=True)
        
        for concept, misses in sorted_concepts[:5]:
            console.print(f"• {concept} [dim](missed {misses} times)[/dim]")


def main():
    """Main entry point."""
    print_welcome()
    
    # Check if command line arguments are provided
    if len(sys.argv) > 1:
        console.print("[yellow]Command line mode not implemented in this version.[/yellow]")
        console.print("[yellow]Starting interactive mode...[/yellow]")
    
    # Start interactive mode
    try:
        interactive_mode()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


if __name__ == '__main__':
    main()
