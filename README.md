# 🧠 Memory Palace CLI

**Transform your notes into an AI-powered interactive learning experience!**

Built for the AI Tinkerers × Google Gemini CLI Buildathon, Memory Palace CLI is a conversational study assistant that turns boring study materials into engaging, memorable learning sessions using creative mnemonics and intelligent quizzing.

## ✨ Features

### 🤖 Conversational AI Interface
- Natural language interaction - no complex menus
- Intelligent directory discovery and content analysis
- Context-aware responses and suggestions
- Personalized study recommendations

### 📚 Smart Study Tools
- **Flashcard Generation**: AI-creates memorable flashcards with creative mnemonics
- **Interactive Quizzes**: Test knowledge with intelligent answer evaluation
- **MCQ Creation**: Generate multiple-choice questions with plausible distractors
- **PDF Support**: Extract and study from PDF documents

### 📊 Advanced Analytics
- Real-time performance tracking
- Learning velocity analysis
- Streak tracking and accuracy metrics
- Historical progress visualization
- AI-powered study recommendations

### 🎯 Key Capabilities
- Multi-format support (.md, .txt, .pdf)
- Semantic answer evaluation (understands meaning, not just exact matches)
- Difficulty adaptation
- Topic detection and categorization
- Session persistence and progress tracking

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js (for Gemini CLI)
- Google AI Studio API key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/memory-palace-cli.git
cd memory-palace-cli
```

2. **Install Gemini CLI**
```bash
npm install -g @google/generative-ai-cli
```

3. **Set up your API key**

Windows (Command Prompt):
```cmd
set GOOGLE_AI_STUDIO_API_KEY=your-api-key-here
```

Windows (PowerShell):
```powershell
$env:GOOGLE_AI_STUDIO_API_KEY="your-api-key-here"
```

Mac/Linux:
```bash
export GOOGLE_AI_STUDIO_API_KEY="your-api-key-here"
```

4. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

5. **Run the application**
```bash
python main.py
```

## 📖 Usage

### First Run
When you start Memory Palace CLI, it will:
1. Greet you and scan for study materials
2. Show available directories with content summaries
3. Let you select materials conversationally
4. Offer various study modes

### Commands
Just type naturally! The AI understands:
- "Create flashcards from my biology notes"
- "Quiz me on photosynthesis"
- "Show me my progress"
- "Generate multiple choice questions"
- "How am I doing with my studies?"

### Example Session
```
🧠 MEMORY PALACE CLI - AI Study Assistant
==========================================

Hello! I'm your AI study assistant. Let me help you turn your notes into an engaging learning experience.

Scanning for study materials...

Found 1 study directory:

1. 📁 data
   Files: 3 (12.5 KB)
   Subjects: biology
   Types: 3 markdown

Which directory would you like to work with?
You: data

✓ Selected: data
Found 3 study files.

📚 Content Summary:
Your materials cover cell biology, photosynthesis, DNA structure, genetics, 
cellular respiration, evolution, and ecology.

What would you like to do?
• Generate flashcards from your notes
• Take a quiz to test your knowledge
• Create multiple choice questions
• View your progress and analytics

You: quiz me on cells

Starting quiz session!
Loaded 25 flashcards!

Question 1/10:
What is the control center of the cell that contains DNA?

Your answer: nucleus

✓ Perfect! That's exactly right! 🎉

[Quiz continues...]

📊 QUIZ RESULTS
================
✅ Correct: 8
❌ Wrong: 2
📊 Accuracy: 80.0%
🔥 Best Streak: 5
⭐ EXCELLENT! Great job!
```

## 📁 Project Structure

```
memory-palace-cli/
├── main.py              # Conversational interface & session management
├── flashcards.py        # Flashcard generation with mnemonics
├── quiz.py              # Interactive quiz with AI evaluation
├── mcq.py               # Multiple choice question generation
├── utils.py             # Gemini CLI integration & utilities
├── requirements.txt     # Python dependencies
├── data/
│   ├── biology_notes.md # Sample study material
│   ├── flashcards.json  # Generated flashcards
│   ├── mcqs.json        # Generated MCQs
│   └── progress.json    # Learning analytics
└── README.md
```

## 🎨 Features Breakdown

### Intelligent Content Processing
- Automatically detects study vs. project files
- Extracts key concepts and definitions
- Generates creative memory aids
- Supports multiple file formats

### Adaptive Learning
- Semantic answer matching (understands paraphrasing)
- Difficulty adjustment based on performance
- Personalized feedback and encouragement
- Progress-based recommendations

### Beautiful Terminal UI
- Color-coded responses
- Progress bars and visual indicators
- Emoji-enhanced feedback
- Clean, readable formatting

## 🐛 Troubleshooting

### Gemini CLI not responding
1. Check API key is set: `echo %GOOGLE_AI_STUDIO_API_KEY%` (Windows)
2. Verify Gemini CLI installation: `gemini --version`
3. Test directly: `gemini "Say hello"`

### PDF support not working
Install pypdf: `pip install pypdf`

### No study materials found
- Place `.md`, `.txt`, or `.pdf` files in a `data/` folder
- Or let the app create sample materials for you

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Share your study materials

## 📜 License

MIT License - feel free to use this for your own learning!

## 🙏 Acknowledgments

- Built for AI Tinkerers × Google Gemini CLI Buildathon
- Powered by Google's Gemini AI
- Created with ❤️ for students everywhere

## 🚀 Future Enhancements

- [ ] Voice input/output support
- [ ] Spaced repetition algorithm
- [ ] Export to Anki/Quizlet
- [ ] Multi-language support
- [ ] Collaborative study sessions
- [ ] Image-based learning
- [ ] Study streak gamification

---

**Made with 🧠 by [Your Name] | Transform the way you study!**