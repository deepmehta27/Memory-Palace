import random
import time
from typing import List, Dict, Any
from utils import load_json, save_json, call_gemini_cli, console, print_success, print_error, print_info

class QuizSession:
    def __init__(self, flashcards_path: str = "data/flashcards.json", progress_path: str = "data/progress.json"):
        self.flashcards_path = flashcards_path
        self.progress_path = progress_path
        self.flashcards = load_json(flashcards_path)
        self.progress = self.load_progress()
        self.current_session = {
            "correct": 0,
            "total": 0,
            "wrong_answers": []
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
        """Use Gemini to evaluate the answer and provide feedback."""
        
        prompt = f"""
Evaluate this student's answer and provide encouraging feedback:

Question: {question}
Student Answer: {user_answer}
Correct Answer: {correct_answer}
Memory Hook: {mnemonic}

Respond in this JSON format:
{{
    "is_correct": true/false,
    "feedback": "Your encouraging feedback here",
    "score": 0-100
}}

Be encouraging and educational. If wrong, gently correct and remind them of the mnemonic.
If partially correct, give partial credit and explain what was missing.
Only respond with JSON, no other text.
"""
        
        console.print("[dim]🤖 Gemini is evaluating your answer...[/dim]")
        response = call_gemini_cli(prompt)
        
        if not response:
            # Fallback evaluation
            is_correct = self.simple_answer_check(user_answer, correct_answer)
            return {
                "is_correct": is_correct,
                "feedback": "Great job!" if is_correct else f"Not quite. The answer is: {correct_answer}. Remember: {mnemonic}",
                "score": 100 if is_correct else 0
            }
        
        try:
            import json
            import re
            
            # Clean response
            cleaned_response = response.strip()
            if cleaned_response.startswith('```'):
                lines = cleaned_response.split('\n')
                cleaned_response = '\n'.join(line for line in lines if not line.startswith('```'))
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Validate required fields
                if 'is_correct' not in result:
                    result['is_correct'] = self.simple_answer_check(user_answer, correct_answer)
                if 'feedback' not in result:
                    result['feedback'] = "Good effort!"
                if 'score' not in result:
                    result['score'] = 100 if result['is_correct'] else 0
                
                return result
            else:
                # Fallback parsing
                is_correct = "correct" in response.lower() or "right" in response.lower()
                return {
                    "is_correct": is_correct,
                    "feedback": response,
                    "score": 100 if is_correct else 0
                }
                
        except Exception as e:
            print_error(f"Error parsing Gemini evaluation: {e}")
            # Simple fallback
            is_correct = self.simple_answer_check(user_answer, correct_answer)
            return {
                "is_correct": is_correct,
                "feedback": "Keep trying! Learning takes practice.",
                "score": 100 if is_correct else 0
            }
    
    def simple_answer_check(self, user_answer: str, correct_answer: str) -> bool:
        """Simple answer checking as fallback."""
        user_lower = user_answer.lower().strip()
        correct_lower = correct_answer.lower()
        
        # Check if key words match
        user_words = set(user_lower.split())
        correct_words = set(correct_lower.split())
        
        # If user answer contains most important words from correct answer
        important_words = [w for w in correct_words if len(w) > 3]
        if important_words:
            matching_words = sum(1 for word in important_words if word in user_lower)
            return matching_words >= len(important_words) * 0.5
        
        # Basic containment check
        return user_lower in correct_lower or correct_lower in user_lower
    
    def ask_question(self, flashcard: Dict) -> bool:
        """Ask a single question and return if correct."""
        console.print(f"\n[bold blue]Question:[/bold blue] {flashcard['question']}")
        
        user_answer = input("\nYour answer: ").strip()
        
        if not user_answer:
            console.print("[yellow]⏭️  Skipped![/yellow]")
            return False
        
        # Evaluate with Gemini
        evaluation = self.evaluate_answer_with_gemini(
            flashcard['question'], 
            user_answer, 
            flashcard['answer'], 
            flashcard.get('mnemonic', 'No mnemonic available')
        )
        
        is_correct = evaluation['is_correct']
        feedback = evaluation['feedback']
        
        if is_correct:
            console.print(f"[green]✅ Correct![/green]")
            console.print(f"[green]{feedback}[/green]")
        else:
            console.print(f"[red]❌ Not quite right.[/red]")
            console.print(f"[yellow]Correct answer: {flashcard['answer']}[/yellow]")
            console.print(f"[cyan]💡 {flashcard.get('mnemonic', 'Keep practicing!')}[/cyan]")
            console.print(f"[blue]{feedback}[/blue]")
            
            # Track wrong answer
            self.current_session["wrong_answers"].append({
                "question": flashcard['question'],
                "user_answer": user_answer,
                "correct_answer": flashcard['answer']
            })
        
        return is_correct
    
    def run_quiz(self, num_questions: int = None):
        """Run an interactive quiz session."""
        if not self.flashcards:
            print_error("No flashcards found! Generate some first.")
            return
        
        console.print("\n[bold magenta]🎯 Starting Quiz Session![/bold magenta]")
        console.print("Type your answer and press Enter. Leave blank to skip.\n")
        
        # Determine how many questions to ask
        if num_questions is None:
            num_questions = min(len(self.flashcards), 10)
        
        # Select questions (could be random or based on difficulty)
        available_cards = self.flashcards.copy()
        if len(available_cards) > num_questions:
            selected_cards = random.sample(available_cards, num_questions)
        else:
            selected_cards = available_cards
        
        # Run quiz
        for i, card in enumerate(selected_cards, 1):
            console.print(f"\n[dim]Question {i} of {len(selected_cards)}[/dim]")
            
            is_correct = self.ask_question(card)
            
            if is_correct:
                self.current_session["correct"] += 1
            self.current_session["total"] += 1
            
            # Brief pause between questions
            time.sleep(0.5)
        
        # Show final results
        self.show_results()
        self.update_progress()
        self.save_progress()
    
    def show_results(self):
        """Show quiz results."""
        correct = self.current_session["correct"]
        total = self.current_session["total"]
        percentage = (correct / total * 100) if total > 0 else 0
        
        console.print(f"\n[bold]📊 Quiz Complete![/bold]")
        console.print(f"Score: {correct}/{total} ({percentage:.1f}%)")
        
        if percentage >= 80:
            console.print("[green]🎉 Excellent work! You're mastering this material![/green]")
        elif percentage >= 60:
            console.print("[yellow]👍 Good job! Keep practicing those tricky concepts.[/yellow]")
        else:
            console.print("[blue]💪 Keep studying! Every expert was once a beginner.[/blue]")
        
        if self.current_session["wrong_answers"]:
            console.print(f"\n[cyan]📚 Concepts to review:[/cyan]")
            for wrong in self.current_session["wrong_answers"]:
                console.print(f"• {wrong['question']}")
    
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
    """Start a quiz session."""
    try:
        quiz = QuizSession(flashcards_path)
        quiz.run_quiz(num_questions)
    except Exception as e:
        print_error(f"Error starting quiz: {e}")
        print_info("Make sure you have generated flashcards first!")