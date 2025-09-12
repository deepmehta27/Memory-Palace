import random
import time
from typing import List, Dict, Any
from utils import load_json, save_json, call_gemini_cli, console, print_success, print_error, print_info
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import box

class QuizSession:
    def __init__(self, flashcards_path: str = "data/flashcards.json", progress_path: str = "data/progress.json"):
        self.flashcards_path = flashcards_path
        self.progress_path = progress_path
        self.flashcards = load_json(flashcards_path)
        self.progress = self.load_progress()
        self.current_session = {
            "correct": 0,
            "total": 0,
            "wrong_answers": [],
            "streak": 0,
            "best_streak": 0
        }
    
    def load_progress(self) -> Dict:
        """Load or initialize progress tracking."""
        progress = load_json(self.progress_path)
        if not progress:
            progress = {
                "total_sessions": 0,
                "total_questions": 0,
                "correct_answers": 0,
                "difficult_concepts": {},
                "mastered_concepts": []
            }
        return progress
    
    def save_progress(self):
        """Save progress to file."""
        save_json(self.progress, self.progress_path)
    
    def evaluate_answer_with_gemini(self, question: str, user_answer: str, correct_answer: str, mnemonic: str) -> Dict:
        """Use Gemini for semantic evaluation of answers."""
        
        # If answer is very short or empty, use simple check
        if len(user_answer.strip()) < 3:
            is_correct = self.simple_answer_check(user_answer, correct_answer)
            return {
                "is_correct": is_correct,
                "feedback": "Try to provide a more complete answer!" if not is_correct else "Correct!",
                "score": 100 if is_correct else 0,
                "match_quality": "exact" if is_correct else "none"
            }
        
        # Try Gemini semantic evaluation
        prompt = f"""
Evaluate if the student's answer is semantically correct.

Question: {question}
Correct Answer: {correct_answer}
Student's Answer: {user_answer}

Analyze the semantic similarity and understanding. Return your evaluation as:
- If the answer captures the core meaning (even with different words): "CORRECT"
- If partially correct but missing key points: "PARTIAL"
- If incorrect or unrelated: "INCORRECT"

Then provide one line of encouraging feedback.
Format: [STATUS] | [Feedback]
Example: CORRECT | Excellent understanding, you captured the key concept perfectly!
"""
        
        response = call_gemini_cli(prompt)
        
        if response:
            # Parse Gemini response
            if "CORRECT" in response.upper() and "PARTIAL" not in response.upper():
                is_correct = True
                match_quality = "semantic"
                score = 100
                feedback = "Excellent! You understood the concept perfectly!"
            elif "PARTIAL" in response.upper():
                is_correct = False
                match_quality = "partial"
                score = 50
                feedback = f"Good effort! You're on the right track. Complete answer: {correct_answer}"
            else:
                is_correct = False
                match_quality = "incorrect"
                score = 0
                feedback = f"Not quite, but keep learning! The answer is: {correct_answer}"
            
            # Extract custom feedback if provided
            if "|" in response:
                parts = response.split("|")
                if len(parts) > 1:
                    feedback = parts[1].strip()
        else:
            # Fallback to enhanced simple check
            is_correct, match_quality = self.enhanced_answer_check(user_answer, correct_answer)
            score = 100 if is_correct else 50 if match_quality == "partial" else 0
            
            if is_correct:
                feedback = "Perfect! You got it right!"
            elif match_quality == "partial":
                feedback = f"Close! You had the right idea. Full answer: {correct_answer}"
            else:
                feedback = f"Keep trying! The correct answer is: {correct_answer}"
        
        return {
            "is_correct": is_correct,
            "feedback": feedback,
            "score": score,
            "match_quality": match_quality
        }
    
    def simple_answer_check(self, user_answer: str, correct_answer: str) -> bool:
        """Simple answer checking as fallback."""
        user_lower = user_answer.lower().strip()
        correct_lower = correct_answer.lower()
        
        # Exact match
        if user_lower == correct_lower:
            return True
        
        # Check if key words match
        user_words = set(user_lower.split())
        correct_words = set(correct_lower.split())
        
        # If user answer contains most important words from correct answer
        important_words = [w for w in correct_words if len(w) > 3]
        if important_words:
            matching_words = sum(1 for word in important_words if word in user_lower)
            return matching_words >= len(important_words) * 0.6
        
        return False
    
    def enhanced_answer_check(self, user_answer: str, correct_answer: str) -> tuple:
        """Enhanced semantic checking without Gemini."""
        user_lower = user_answer.lower().strip()
        correct_lower = correct_answer.lower()
        
        # Remove common words for better comparison
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'of', 'in', 'to', 'for'}
        
        user_words = set(user_lower.split()) - stop_words
        correct_words = set(correct_lower.split()) - stop_words
        
        # Calculate overlap
        if not correct_words:
            return (user_lower == correct_lower, "exact" if user_lower == correct_lower else "none")
        
        overlap = len(user_words & correct_words) / len(correct_words)
        
        if overlap >= 0.7:
            return (True, "semantic")
        elif overlap >= 0.4:
            return (False, "partial")
        else:
            return (False, "none")
    
    def ask_question(self, flashcard: Dict, question_num: int, total_questions: int) -> bool:
        """Ask a single question with enhanced UI."""
        
        # Display question in a nice panel
        question_panel = Panel(
            f"[bold cyan]{flashcard['question']}[/bold cyan]",
            title=f"[bold magenta]Question {question_num}/{total_questions}[/bold magenta]",
            border_style="bright_blue",
            padding=(1, 2)
        )
        console.print(question_panel)
        
        # Show streak if active
        if self.current_session["streak"] >= 3:
            console.print(f"[bold yellow]🔥 Current streak: {self.current_session['streak']}[/bold yellow]")
        
        user_answer = console.input("\n[bold green]Your answer:[/bold green] ").strip()
        
        if not user_answer:
            console.print("[yellow]⏭️  Skipped![/yellow]")
            self.current_session["streak"] = 0
            return False
        
        # Show thinking spinner while evaluating
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Evaluating your answer...[/cyan]"),
            transient=True
        ) as progress:
            progress.add_task("evaluate", total=None)
            evaluation = self.evaluate_answer_with_gemini(
                flashcard['question'], 
                user_answer, 
                flashcard['answer'], 
                flashcard.get('mnemonic', 'No mnemonic available')
            )
        
        is_correct = evaluation['is_correct']
        feedback = evaluation['feedback']
        match_quality = evaluation.get('match_quality', 'none')
        
        if is_correct:
            self.current_session["streak"] += 1
            if self.current_session["streak"] > self.current_session["best_streak"]:
                self.current_session["best_streak"] = self.current_session["streak"]
            
            # Different messages based on match quality
            if match_quality == "exact":
                console.print(Panel(
                    f"[bold green]✅ PERFECT![/bold green]\n{feedback}",
                    border_style="green",
                    box=box.DOUBLE
                ))
            else:
                console.print(Panel(
                    f"[bold green]✅ CORRECT![/bold green]\n{feedback}\n[dim]You understood the concept even with different wording![/dim]",
                    border_style="green"
                ))
        else:
            self.current_session["streak"] = 0
            
            if match_quality == "partial":
                console.print(Panel(
                    f"[bold yellow]⚡ PARTIAL![/bold yellow]\n{feedback}",
                    border_style="yellow"
                ))
            else:
                console.print(Panel(
                    f"[bold red]❌ Not quite right[/bold red]\n"
                    f"[yellow]Correct answer:[/yellow] {flashcard['answer']}\n"
                    f"[cyan]💡 Memory tip:[/cyan] {flashcard.get('mnemonic', 'Keep practicing!')}",
                    border_style="red"
                ))
            
            # Track wrong answer
            self.current_session["wrong_answers"].append({
                "question": flashcard['question'],
                "user_answer": user_answer,
                "correct_answer": flashcard['answer']
            })
        
        return is_correct
    
    def run_quiz(self, num_questions: int = None):
        """Run an interactive quiz session with enhanced UI."""
        if not self.flashcards:
            print_error("No flashcards found! Generate some first.")
            return
        
        # Welcome panel
        welcome_panel = Panel(
            "[bold magenta]🎯 Quiz Session Starting![/bold magenta]\n"
            "[cyan]Answer questions to test your knowledge[/cyan]\n"
            "[dim]Press Enter without typing to skip a question[/dim]",
            border_style="bright_magenta",
            padding=(1, 2)
        )
        console.print(welcome_panel)
        
        # Determine how many questions to ask
        if num_questions is None:
            num_questions = min(len(self.flashcards), 10)
        
        # Select questions (could be random or based on difficulty)
        available_cards = self.flashcards.copy()
        if len(available_cards) > num_questions:
            selected_cards = random.sample(available_cards, num_questions)
        else:
            selected_cards = available_cards
        
        # Progress bar setup
        console.print(f"\n[bold cyan]Loading {len(selected_cards)} questions...[/bold cyan]\n")
        
        # Run quiz
        for i, card in enumerate(selected_cards, 1):
            is_correct = self.ask_question(card, i, len(selected_cards))
            
            if is_correct:
                self.current_session["correct"] += 1
            self.current_session["total"] += 1
            
            # Show progress
            progress = (i / len(selected_cards)) * 100
            console.print(f"[dim]Progress: {progress:.0f}%[/dim]\n")
            
            # Brief pause between questions
            if i < len(selected_cards):
                time.sleep(0.5)
        
        # Show final results
        self.show_results()
        self.update_progress()
        self.save_progress()
    
    def show_results(self):
        """Show quiz results with enhanced visualization."""
        correct = self.current_session["correct"]
        total = self.current_session["total"]
        percentage = (correct / total * 100) if total > 0 else 0
        
        # Create results table
        table = Table(title="📊 Quiz Results", border_style="bright_cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold")
        
        table.add_row("Questions Answered", str(total))
        table.add_row("Correct Answers", f"[green]{correct}[/green]")
        table.add_row("Incorrect Answers", f"[red]{total - correct}[/red]")
        table.add_row("Accuracy", f"{percentage:.1f}%")
        table.add_row("Best Streak", f"[yellow]🔥 {self.current_session['best_streak']}[/yellow]")
        
        console.print(table)
        
        # Performance message with color coding
        if percentage >= 90:
            performance_panel = Panel(
                "[bold green]🏆 OUTSTANDING PERFORMANCE![/bold green]\n"
                "You've mastered this material! Consider moving to advanced topics.",
                border_style="green",
                box=box.DOUBLE
            )
        elif percentage >= 75:
            performance_panel = Panel(
                "[bold cyan]⭐ EXCELLENT WORK![/bold cyan]\n"
                "You have a strong grasp of the material. Keep it up!",
                border_style="cyan"
            )
        elif percentage >= 60:
            performance_panel = Panel(
                "[bold yellow]👍 GOOD PROGRESS![/bold yellow]\n"
                "You're on the right track. Review the missed concepts for better retention.",
                border_style="yellow"
            )
        else:
            performance_panel = Panel(
                "[bold magenta]💪 KEEP LEARNING![/bold magenta]\n"
                "Every expert was once a beginner. Review the material and try again!",
                border_style="magenta"
            )
        
        console.print(performance_panel)
        
        # Show concepts to review if any
        if self.current_session["wrong_answers"]:
            console.print(f"\n[bold red]📚 Concepts to Review:[/bold red]")
            for i, wrong in enumerate(self.current_session["wrong_answers"][:5], 1):
                console.print(f"  {i}. [yellow]{wrong['question']}[/yellow]")
            
            if len(self.current_session["wrong_answers"]) > 5:
                console.print(f"  [dim]... and {len(self.current_session['wrong_answers']) - 5} more[/dim]")
    
    def update_progress(self):
        """Update overall progress tracking."""
        self.progress["total_sessions"] += 1
        self.progress["total_questions"] += self.current_session["total"]
        self.progress["correct_answers"] += self.current_session["correct"]
        
        # Track difficult concepts
        for wrong in self.current_session["wrong_answers"]:
            question = wrong["question"]
            if question not in self.progress["difficult_concepts"]:
                self.progress["difficult_concepts"][question] = 0
            self.progress["difficult_concepts"][question] += 1

def start_quiz(flashcards_path: str = "data/flashcards.json", num_questions: int = None):
    """Start a quiz session with enhanced UI."""
    try:
        quiz = QuizSession(flashcards_path)
        quiz.run_quiz(num_questions)
    except Exception as e:
        print_error(f"Error starting quiz: {e}")
        print_info("Make sure you have generated flashcards first!")