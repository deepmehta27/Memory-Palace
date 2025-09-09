#!/usr/bin/env python3
"""
Memory Palace CLI - Conversational Study Assistant
Transform your notes into memorable study experiences through natural conversation!
"""

import os
import sys
import glob
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

try:
    from utils import call_gemini_cli, print_welcome, print_success, print_error, print_info, ensure_data_dir, load_json, save_json, console
    from flashcards import generate_flashcards_from_file
    from quiz import start_quiz
    from mcq import generate_mcqs, run_mcq_quiz
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all files are in the same directory and dependencies are installed.")
    sys.exit(1)

class StudyAssistant:
    def __init__(self):
        self.current_directory = None
        self.discovered_files = []
        self.session_data = {
            "start_time": None,
            "activities": [],
            "files_processed": [],
            "quiz_sessions": 0,
            "total_questions": 0,
            "correct_answers": 0
        }
        self.conversation_context = []
    
    def discover_directories(self) -> List[Path]:
        """Discover potential study directories in the current workspace."""
        current_path = Path(".")
        potential_dirs = []
        
        # Look for directories with study-related files
        for item in current_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Check if directory contains study files
                study_files = list(item.glob("*.md")) + list(item.glob("*.txt")) + list(item.glob("*.pdf"))
                if study_files:
                    potential_dirs.append(item)
        
        # Also check current directory
        current_files = list(current_path.glob("*.md")) + list(current_path.glob("*.txt")) + list(current_path.glob("*.pdf"))
        if current_files:
            potential_dirs.insert(0, current_path)
        
        return potential_dirs
    
    def analyze_directory(self, directory: Path) -> Dict[str, Any]:
        """Analyze a directory and summarize its contents."""
        analysis = {
            "path": str(directory),
            "total_files": 0,
            "markdown_files": [],
            "text_files": [],
            "pdf_files": [],
            "total_size": 0,
            "subjects": set(),
            "content_preview": ""
        }
        
        # Scan for different file types
        for ext, file_list in [("*.md", "markdown_files"), ("*.txt", "text_files"), ("*.pdf", "pdf_files")]:
            files = list(directory.glob(ext))
            analysis[file_list] = [f.name for f in files]
            analysis["total_files"] += len(files)
            
            # Calculate total size
            for file in files:
                try:
                    analysis["total_size"] += file.stat().st_size
                except:
                    pass
        
        # Analyze content for subject detection and preview
        sample_content = ""
        for md_file in directory.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')[:1000]
                sample_content += content + "\n"
                
                # Basic subject detection
                content_lower = content.lower()
                subjects = ["biology", "chemistry", "physics", "math", "history", "literature", "computer science"]
                for subject in subjects:
                    if subject in content_lower:
                        analysis["subjects"].add(subject)
            except:
                continue
        
        analysis["content_preview"] = sample_content[:500] + "..." if len(sample_content) > 500 else sample_content
        analysis["subjects"] = list(analysis["subjects"])
        
        return analysis
    
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        else:
            return f"{size_bytes/(1024**2):.1f} MB"
    
    def ask_gemini_conversational(self, user_input: str, context: str = "") -> str:
        """Ask Gemini for conversational response with context."""
        conversation_history = "\n".join(self.conversation_context[-3:]) if self.conversation_context else ""
        
        prompt = f"""
You are a friendly, intelligent study assistant helping a student organize their learning materials. 

Context about current session:
{context}

Recent conversation:
{conversation_history}

Student says: "{user_input}"

Respond naturally and helpfully. You can:
- Help them choose study materials
- Suggest study strategies  
- Generate flashcards or quizzes
- Analyze their progress
- Give encouragement and study tips

Keep responses concise but engaging. Ask follow-up questions when helpful.
"""
        
        response = call_gemini_cli(prompt)
        return response if response else "I'm here to help with your studies! What would you like to work on?"
    
    def conversational_interface(self):
        """Main conversational interface."""
        from datetime import datetime
        self.session_data["start_time"] = datetime.now()
        
        print_welcome()
        console.print("\nHello! I'm your AI study assistant. Let me help you turn your notes into an engaging learning experience.")
        
        # Discover and present directories
        console.print("\n[blue]Let me scan for your study materials...[/blue]")
        directories = self.discover_directories()
        
        if not directories:
            console.print("[yellow]I couldn't find any study directories with .md, .txt, or .pdf files.[/yellow]")
            console.print("Would you like to create a sample directory or specify a different location?")
            
            user_input = input("\nYou: ").strip()
            if "sample" in user_input.lower() or "demo" in user_input.lower():
                self.create_sample_data()
                directories = self.discover_directories()
        
        if directories:
            console.print(f"\n[green]Great! I found {len(directories)} directories with study materials:[/green]")
            
            for i, directory in enumerate(directories, 1):
                analysis = self.analyze_directory(directory)
                dir_name = "current directory" if directory.name == "." else directory.name
                console.print(f"\n{i}. [cyan]{dir_name}[/cyan]")
                console.print(f"   📁 {analysis['total_files']} files ({self.format_size(analysis['total_size'])})")
                
                if analysis['subjects']:
                    console.print(f"   📚 Subjects detected: {', '.join(analysis['subjects'])}")
                
                if analysis['markdown_files']:
                    console.print(f"   📝 Markdown: {', '.join(analysis['markdown_files'][:3])}")
                    if len(analysis['markdown_files']) > 3:
                        console.print(f"       ... and {len(analysis['markdown_files']) - 3} more")
            
            # Let user choose directory conversationally
            console.print(f"\nWhich directory would you like to focus on? You can say the number or describe what you're looking for.")
            
            while True:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                # Try to parse directory choice
                directory_choice = self.parse_directory_choice(user_input, directories)
                
                if directory_choice:
                    self.current_directory = directory_choice
                    break
                else:
                    ai_response = self.ask_gemini_conversational(
                        user_input, 
                        f"Available directories: {[d.name for d in directories]}"
                    )
                    console.print(f"\n[blue]Assistant:[/blue] {ai_response}")
            
            # Analyze and summarize chosen directory
            self.analyze_and_summarize_directory()
            
            # Start conversational study session
            self.study_conversation_loop()
    
    def parse_directory_choice(self, user_input: str, directories: List[Path]) -> Path | None:
            user_input = user_input.lower().strip()

            # ✅ Case 1: Numeric choice (e.g., "1", "2")
            try:
                choice_num = int(user_input) - 1
                if 0 <= choice_num < len(directories):
                    return directories[choice_num]
            except ValueError:
                pass

            # ✅ Case 2: Exact directory name match
            for directory in directories:
                dir_name = directory.name.lower()
                if dir_name == user_input:
                    return directory

            # ✅ Case 3: User explicitly says "current"
            if "current" in user_input or "here" in user_input:
                return Path(".")

            # ✅ Case 4: Subject-based choice (detected from notes)
            for directory in directories:
                analysis = self.analyze_directory(directory)
                for subject in analysis["subjects"]:
                    if subject.lower() in user_input:
                        return directory

            # ❌ Default: No match → return None so Gemini handles it
            return None

    
    def analyze_and_summarize_directory(self):
        """Analyze the chosen directory and provide simple file listing."""
        if not self.current_directory:
            return
        
        analysis = self.analyze_directory(self.current_directory)
        dir_name = "current directory" if self.current_directory.name == "." else self.current_directory.name
        
        console.print(f"\n[green]Perfect! Let's work with the {dir_name}.[/green]")
        console.print(f"\n[blue]📊 Directory Analysis:[/blue]")
        console.print(f"• {analysis['total_files']} study files ({self.format_size(analysis['total_size'])})")
        console.print(f"• File types: {len(analysis['markdown_files'])} markdown, {len(analysis['text_files'])} text, {len(analysis['pdf_files'])} PDF")
        
        if analysis['subjects']:
            console.print(f"• Detected subjects: {', '.join(analysis['subjects'])}")
        
        # Show simple file listing instead of AI summary
        if analysis['markdown_files'] or analysis['text_files'] or analysis['pdf_files']:
            console.print(f"\n[blue]📁 Available Files:[/blue]")
            
            all_files = analysis['markdown_files'] + analysis['text_files'] + analysis['pdf_files']
            for i, filename in enumerate(all_files, 1):
                file_type = "📝" if filename.endswith('.md') else "📄" if filename.endswith('.txt') else "📊"
                console.print(f"   {i}. {file_type} {filename}")
            
        self.discovered_files = analysis['markdown_files'] + analysis['text_files'] + analysis['pdf_files']
        
        console.print(f"\n[green]Now I can help you create flashcards, quizzes, or provide study guidance. What would you like to do?[/green]")
    
    def study_conversation_loop(self):
        """Main conversation loop for study activities."""
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                # Check for exit commands
                if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                    self.show_session_summary()
                    break
                
                # Process user input and determine action
                action = self.parse_study_intent(user_input)
                
                if action:
                    self.execute_study_action(action, user_input)
                else:
                    # General conversational response
                    context = f"""
                    Current directory: {self.current_directory}
                    Available files: {self.discovered_files}
                    Session activities so far: {len(self.session_data['activities'])}
                    """
                    
                    ai_response = self.ask_gemini_conversational(user_input, context)
                    console.print(f"\n[blue]Assistant:[/blue] {ai_response}")
                
                # Add to conversation context
                self.conversation_context.append(f"You: {user_input}")
                
            except KeyboardInterrupt:
                self.show_session_summary()
                break
            except Exception as e:
                print_error(f"Error: {e}")
    
    def parse_study_intent(self, user_input: str) -> str:
        """Parse user intent from natural language."""
        user_lower = user_input.lower()
        
        # Intent mapping
        if any(word in user_lower for word in ['flashcard', 'flash card', 'generate', 'create card']):
            return 'generate_flashcards'
        elif any(word in user_lower for word in ['quiz', 'test', 'question', 'ask me']):
            return 'start_quiz'
        elif any(word in user_lower for word in ['mcq', 'multiple choice', 'choice question']):
            return 'mcq_quiz'
        elif any(word in user_lower for word in ['progress', 'stats', 'statistics', 'how am i doing']):
            return 'show_stats'
        elif any(word in user_lower for word in ['help', 'what can', 'options']):
            return 'show_help'
        
        return None
    
    def execute_study_action(self, action: str, user_input: str):
        """Execute the determined study action."""
        if action == 'generate_flashcards':
            self.handle_flashcard_generation(user_input)
        elif action == 'start_quiz':
            self.handle_quiz_session(user_input)
        elif action == 'mcq_quiz':
            self.handle_mcq_session(user_input)
        elif action == 'show_stats':
            self.show_progress_stats()
        elif action == 'show_help':
            self.show_conversational_help()
    
    def handle_flashcard_generation(self, user_input: str):
        """Handle flashcard generation conversationally."""
        console.print("\n[blue]Let me create flashcards from your study materials.[/blue]")
        
        if not self.discovered_files:
            console.print("[yellow]I don't see any study files in the current directory.[/yellow]")
            return
        
        # Show files with clearer numbering
        console.print(f"\n[cyan]I found {len(self.discovered_files)} files:[/cyan]")
        for i, filename in enumerate(self.discovered_files, 1):
            file_type = "📝" if filename.endswith('.md') else "📄" if filename.endswith('.txt') else "📊"
            console.print(f"  {i}. {file_type} {filename}")
        
        # Get user choice
        if len(self.discovered_files) == 1:
            chosen_file = self.discovered_files[0]
            console.print(f"\nUsing your only file: {chosen_file}")
        else:
            console.print(f"\nWhich file would you like me to process?")
            console.print(f"Say the number (1-{len(self.discovered_files)}) or filename, or 'all' for all files.")
            
            file_choice = input("\nYou: ").strip()
            
            if file_choice.lower() == 'all':
                # Process all files
                all_success = True
                for file in self.discovered_files:
                    file_path = self.current_directory / file
                    print_info(f"Processing {file}...")
                    if generate_flashcards_from_file(str(file_path)):
                        self.session_data['files_processed'].append(file)
                        self.session_data['activities'].append(f"Generated flashcards from {file}")
                    else:
                        all_success = False
                
                if all_success:
                    console.print("\n[green]Flashcards generated from all files! Ready for quiz sessions.[/green]")
                else:
                    console.print("\n[yellow]Some files could not be processed, but flashcards were created from available files.[/yellow]")
                return
            else:
                # Try to parse as number first
                try:
                    file_index = int(file_choice) - 1
                    if 0 <= file_index < len(self.discovered_files):
                        chosen_file = self.discovered_files[file_index]
                    else:
                        console.print(f"[red]Invalid number. Please choose 1-{len(self.discovered_files)}[/red]")
                        return
                except ValueError:
                    # Try to find matching filename
                    chosen_file = None
                    for file in self.discovered_files:
                        if file_choice.lower() in file.lower():
                            chosen_file = file
                            break
                    
                    if not chosen_file:
                        console.print("[yellow]I couldn't find that file. Using the first available file.[/yellow]")
                        chosen_file = self.discovered_files[0]
        
        # Generate flashcards from chosen file
        file_path = self.current_directory / chosen_file
        print_info(f"Processing {chosen_file}...")
        
        if generate_flashcards_from_file(str(file_path)):
            self.session_data['files_processed'].append(chosen_file)
            self.session_data['activities'].append(f"Generated flashcards from {chosen_file}")
            console.print(f"\n[green]Perfect! I've created comprehensive flashcards from {chosen_file}.[/green]")
            console.print("Would you like to start a quiz session now?")
        else:
            console.print("[red]Sorry, I had trouble generating flashcards from that file.[/red]")
    
    def handle_quiz_session(self, user_input: str):
        """Handle quiz session conversationally."""
        flashcards_file = "data/flashcards.json"
        
        if not Path(flashcards_file).exists():
            console.print("[yellow]I don't have any flashcards ready yet. Let me generate some first![/yellow]")
            if self.discovered_files:
                self.handle_flashcard_generation("")
                return
            else:
                console.print("[red]I need some study materials first. Could you add some .md or .txt files?[/red]")
                return
        
        console.print("\n[blue]Starting a quiz session! I'll ask you questions and provide feedback.[/blue]")
        
        # Determine number of questions from user input
        num_questions = 5  # default
        words = user_input.lower().split()
        for word in words:
            if word.isdigit():
                num_questions = min(int(word), 20)  # cap at 20
                break
        
        console.print(f"I'll ask you {num_questions} questions. Ready? Here we go!\n")
        
        # Track quiz performance
        initial_correct = self.session_data['correct_answers']
        initial_total = self.session_data['total_questions']
        
        start_quiz(flashcards_file, num_questions)
        
        # Update session data
        self.session_data['quiz_sessions'] += 1
        self.session_data['activities'].append(f"Completed quiz with {num_questions} questions")
        
        # Check if progress was updated
        progress_data = load_json("data/progress.json")
        if progress_data:
            new_correct = progress_data.get('correct_answers', 0)
            new_total = progress_data.get('total_questions', 0)
            
            session_correct = new_correct - initial_correct
            session_total = new_total - initial_total
            
            self.session_data['correct_answers'] = new_correct
            self.session_data['total_questions'] = new_total
            
            if session_total > 0:
                session_accuracy = (session_correct / session_total) * 100
                console.print(f"\n[blue]Nice work! In this session: {session_correct}/{session_total} ({session_accuracy:.1f}%)[/blue]")
        
        console.print("\nWhat would you like to do next? More questions, different study method, or check your progress?")
    
    def handle_mcq_session(self, user_input: str):
        """Handle MCQ session conversationally."""
        console.print("\n[blue]I'll create multiple choice questions for you![/blue]")
        
        if not self.discovered_files:
            console.print("[yellow]I need some study materials first. Let me know if you have any .md files.[/yellow]")
            return
        
        # Generate MCQs
        chosen_file = self.discovered_files[0]  # Use first available file
        file_path = self.current_directory / chosen_file
        
        try:
            mcq_path = generate_mcqs(file_path, use_gemini=True)
            console.print(f"[green]Created multiple choice questions from {chosen_file}![/green]")
            
            console.print("\nStarting MCQ quiz...")
            run_mcq_quiz(mcq_path, limit=5)
            
            self.session_data['activities'].append(f"Completed MCQ quiz from {chosen_file}")
            console.print("\nHow did that feel? Would you like more practice or try a different study method?")
            
        except Exception as e:
            console.print(f"[red]Sorry, I had trouble creating MCQs: {e}[/red]")
    
    def show_progress_stats(self):
        """Show enhanced progress statistics conversationally."""
        progress_data = load_json("data/progress.json")
        
        if not progress_data:
            console.print("[blue]You're just getting started! No quiz data yet, but that's perfectly fine.[/blue]")
            console.print("Take a few quizzes and I'll be able to show you some interesting progress insights!")
            return
        
        total_sessions = progress_data.get('total_sessions', 0)
        total_questions = progress_data.get('total_questions', 0)
        correct_answers = progress_data.get('correct_answers', 0)
        difficult_concepts = progress_data.get('difficult_concepts', {})
        
        accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        console.print(f"\n[blue]📊 Your Learning Analytics:[/blue]")
        console.print(f"")
        
        # Performance overview
        console.print(f"🎯 [bold]Overall Performance[/bold]")
        console.print(f"   • Study sessions completed: {total_sessions}")
        console.print(f"   • Total questions answered: {total_questions}")
        console.print(f"   • Overall accuracy: {accuracy:.1f}% ({correct_answers} correct)")
        console.print(f"   • Questions per session: {total_questions/total_sessions:.1f}" if total_sessions > 0 else "   • Questions per session: 0")
        
        # Performance level
        if accuracy >= 90:
            level = "🏆 Expert"
            advice = "Outstanding! You've mastered this material. Consider teaching others or tackling more advanced topics."
        elif accuracy >= 80:
            level = "🥇 Advanced"
            advice = "Excellent work! You have strong command of the material. Focus on the few remaining weak spots."
        elif accuracy >= 70:
            level = "🥈 Proficient" 
            advice = "Good progress! Regular practice will boost your accuracy to the next level."
        elif accuracy >= 60:
            level = "🥉 Developing"
            advice = "You're building solid foundations. Review concepts more frequently for better retention."
        else:
            level = "📚 Learning"
            advice = "Every expert started here! Focus on understanding concepts before memorizing facts."
        
        console.print(f"\n🎖️  [bold]Current Level: {level}[/bold]")
        console.print(f"   💡 [italic]{advice}[/italic]")
        
        # Learning insights
        if total_sessions >= 3:
            console.print(f"\n🧠 [bold]Learning Insights[/bold]")
            
            # Study consistency
            if total_sessions >= 5:
                avg_accuracy = accuracy
                console.print(f"   • Study consistency: {'Excellent' if avg_accuracy > 75 else 'Good' if avg_accuracy > 60 else 'Building momentum'}")
            
            # Retention analysis
            if difficult_concepts:
                struggle_rate = len(difficult_concepts) / total_questions * 100 if total_questions > 0 else 0
                console.print(f"   • Retention rate: {100-struggle_rate:.0f}% (you retain most concepts well)")
            
            # Learning velocity
            questions_per_session = total_questions / total_sessions
            if questions_per_session >= 8:
                console.print(f"   • Learning pace: High intensity (great for rapid progress)")
            elif questions_per_session >= 5:
                console.print(f"   • Learning pace: Steady and sustainable")
            else:
                console.print(f"   • Learning pace: Gentle (perfect for deep understanding)")
        
        # Difficult concepts analysis
        if difficult_concepts:
            console.print(f"\n🎯 [bold]Areas for Review[/bold]")
            sorted_difficult = sorted(difficult_concepts.items(), key=lambda x: x[1], reverse=True)
            
            for i, (concept, misses) in enumerate(sorted_difficult[:5], 1):
                miss_rate = (misses / total_sessions * 100) if total_sessions > 0 else 0
                difficulty_level = "High" if miss_rate > 50 else "Medium" if miss_rate > 25 else "Low"
                console.print(f"   {i}. {concept}")
                console.print(f"      [red]Missed {misses} times ({miss_rate:.0f}% of sessions) - {difficulty_level} priority[/red]")
            
            if len(sorted_difficult) > 5:
                console.print(f"   ... and {len(sorted_difficult) - 5} more concepts")
        
        # Study recommendations
        console.print(f"\n📈 [bold]Personalized Recommendations[/bold]")
        
        if accuracy < 60:
            console.print(f"   • Focus on understanding core concepts before speed")
            console.print(f"   • Use flashcards to build foundational knowledge")
            console.print(f"   • Review difficult concepts daily for 5-10 minutes")
        elif accuracy < 80:
            console.print(f"   • Target your weakest 3-5 concepts for focused review")
            console.print(f"   • Try MCQ mode to test understanding vs. recognition")
            console.print(f"   • Increase study session frequency")
        else:
            console.print(f"   • Challenge yourself with advanced materials")
            console.print(f"   • Try teaching concepts to solidify knowledge")
            console.print(f"   • Consider timed quizzes to improve recall speed")
        
        # Motivational insight
        if total_sessions >= 2:
            console.print(f"\n🌟 [bold]Motivation Boost[/bold]")
            if accuracy >= 70:
                console.print(f"   You've answered {correct_answers} questions correctly - that's fantastic progress!")
            else:
                console.print(f"   You've completed {total_sessions} study sessions - persistence is key to mastery!")
            
            console.print(f"   Keep up the momentum and you'll see even better results!")

    
    def show_conversational_help(self):
        """Show help in a conversational way."""
        console.print(f"\n[blue]I'm here to help you study more effectively! Here's what I can do:[/blue]")
        console.print(f"")
        console.print(f"📚 [cyan]Generate flashcards[/cyan] - Just say 'create flashcards' or 'make cards'")
        console.print(f"🎯 [cyan]Quiz you[/cyan] - Say 'quiz me', 'ask questions', or 'test me'")
        console.print(f"📝 [cyan]Multiple choice[/cyan] - Try 'MCQ quiz' or 'multiple choice questions'")
        console.print(f"📊 [cyan]Show progress[/cyan] - Ask 'how am I doing?' or 'show my stats'")
        console.print(f"")
        console.print(f"Just talk to me naturally! I understand requests like:")
        console.print(f"• 'Can you quiz me on biology?'")
        console.print(f"• 'Make flashcards from my notes'")
        console.print(f"• 'How's my progress?'")
        console.print(f"• 'I want to practice with 10 questions'")
        console.print(f"")
        console.print(f"Say 'exit' or 'goodbye' when you're done studying.")
    
    def create_sample_data(self):
        """Create sample study data."""
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
        
        sample_path = Path("data/sample_biology_notes.md")
        sample_path.write_text(sample_notes, encoding='utf-8')
        console.print("[green]I've created some sample biology notes for you to try![/green]")
    
    def show_session_summary(self):
        """Show summary when user exits."""
        from datetime import datetime
        
        if not self.session_data['start_time']:
            console.print("\n[blue]Thanks for trying Memory Palace CLI! Come back anytime.[/blue]")
            return
        
        duration = datetime.now() - self.session_data['start_time']
        minutes = int(duration.total_seconds() / 60)
        
        console.print(f"\n[blue]📋 Session Summary[/blue]")
        console.print(f"⏱️  Study time: {minutes} minutes")
        console.print(f"📁 Directory: {self.current_directory}")
        console.print(f"📝 Files processed: {len(self.session_data['files_processed'])}")
        console.print(f"🎯 Quiz sessions: {self.session_data['quiz_sessions']}")
        
        if self.session_data['activities']:
            console.print(f"\n[cyan]What you accomplished:[/cyan]")
            for activity in self.session_data['activities']:
                console.print(f"• {activity}")
        
        # Simple encouraging message instead of AI-generated
        if minutes >= 10:
            encouragement = "Great study session! You're building strong learning habits."
        elif self.session_data['quiz_sessions'] > 0:
            encouragement = "Nice work! Every quiz session helps reinforce your knowledge."
        else:
            encouragement = "Thanks for exploring Memory Palace CLI! Come back anytime to study."
        
        console.print(f"\n[green]🌟 {encouragement}[/green]")
        console.print(f"\n[blue]Keep up the great work! See you next time! 👋[/blue]")

def main():
    """Main entry point for conversational interface."""
    try:
        assistant = StudyAssistant()
        assistant.conversational_interface()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")

if __name__ == '__main__':
    main()