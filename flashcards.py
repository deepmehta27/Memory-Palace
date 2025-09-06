import re
import json
from typing import List, Dict
from utils import call_gemini_cli, save_json, console, print_success, print_error, print_info

def extract_concepts_from_notes(content: str) -> List[Dict]:
    """Extract concepts from notes using Gemini CLI."""
    
    prompt = f"""
Analyze these study notes and extract key concepts for flashcards. For each concept, create:
1. A clear question
2. A concise answer  
3. A memorable mnemonic or funny analogy

Format your response as a JSON array like this:
[
  {{
    "question": "What is photosynthesis?",
    "answer": "The process plants use to convert sunlight into energy",
    "mnemonic": "Think of plants as solar panels making sugar batteries ☀️🔋"
  }}
]

Notes to analyze:
{content}

Make the mnemonics fun, memorable, and slightly humorous. Aim for 5-10 flashcards depending on content length.
Only respond with the JSON array, no other text.
"""
    
    print_info("🧠 Asking Gemini to extract concepts and create mnemonics...")
    
    response = call_gemini_cli(prompt)
    
    if not response:
        print_error("Failed to get response from Gemini CLI")
        return create_fallback_flashcards(content)
    
    # Try to extract JSON from the response
    try:
        # Clean up the response - remove any markdown formatting
        cleaned_response = response.strip()
        if cleaned_response.startswith('```'):
            # Remove markdown code blocks
            lines = cleaned_response.split('\n')
            cleaned_response = '\n'.join(line for line in lines if not line.startswith('```'))
        
        # Find JSON array in the response
        json_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            flashcards = json.loads(json_str)
            
            # Validate flashcard format
            valid_flashcards = []
            for card in flashcards:
                if isinstance(card, dict) and 'question' in card and 'answer' in card:
                    # Ensure mnemonic exists
                    if 'mnemonic' not in card:
                        card['mnemonic'] = "Remember this key concept! 🧠"
                    valid_flashcards.append(card)
            
            if valid_flashcards:
                print_success(f"Generated {len(valid_flashcards)} flashcards!")
                return valid_flashcards
            else:
                print_error("No valid flashcards in Gemini response")
                return create_fallback_flashcards(content)
        else:
            print_error("Could not find JSON in Gemini response")
            return create_fallback_flashcards(content)
            
    except json.JSONDecodeError as e:
        print_error(f"Could not parse Gemini response as JSON: {e}")
        return create_fallback_flashcards(content)
    except Exception as e:
        print_error(f"Error processing Gemini response: {e}")
        return create_fallback_flashcards(content)

def create_fallback_flashcards(content: str) -> List[Dict]:
    """Create simple flashcards if Gemini parsing fails."""
    print_info("Creating fallback flashcards from content...")
    
    flashcards = []
    
    # Try to find definitions using different patterns
    patterns = [
        r'\*\*([^*]+)\*\*:\s*([^.\n]+)',  # **Term**: Definition
        r'([A-Z][a-zA-Z\s]+):\s*([^.\n]+)',  # Term: Definition
        r'##+\s*([^#\n]+)\n([^#]+)',  # Markdown headers with content
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        for term, definition in matches:
            term = term.strip()
            definition = definition.strip()
            
            if len(term) > 2 and len(definition) > 10:  # Basic quality check
                flashcards.append({
                    "question": f"What is {term}?",
                    "answer": definition,
                    "mnemonic": f"Think of {term} as... (create your own memory hook!) 🧠"
                })
    
    # Remove duplicates
    seen = set()
    unique_flashcards = []
    for card in flashcards:
        key = card['question'].lower()
        if key not in seen:
            seen.add(key)
            unique_flashcards.append(card)
    
    if not unique_flashcards:
        # Create at least one example flashcard
        unique_flashcards.append({
            "question": "What did you learn from these notes?",
            "answer": "Check your notes for the key concepts",
            "mnemonic": "Notes are like treasure maps - X marks the knowledge! 🗺️"
        })
    
    print_success(f"Created {len(unique_flashcards)} fallback flashcards")
    return unique_flashcards

def generate_flashcards_from_file(file_path: str, output_path: str = "data/flashcards.json") -> bool:
    """Generate flashcards from a notes file."""
    from utils import load_file
    
    print_info(f"Reading notes from: {file_path}")
    content = load_file(file_path)
    if not content:
        print_error("Could not read file or file is empty")
        return False
    
    print_info(f"File content length: {len(content)} characters")
    
    flashcards = extract_concepts_from_notes(content)
    
    if not flashcards:
        print_error("No flashcards generated")
        return False
    
    # Save flashcards
    if save_json(flashcards, output_path):
        print_success(f"Flashcards saved to {output_path}")
        
        # Show preview
        console.print("\n[bold]Preview of generated flashcards:[/bold]")
        for i, card in enumerate(flashcards[:3], 1):
            console.print(f"\n[cyan]Card {i}:[/cyan]")
            console.print(f"Q: {card['question']}")
            console.print(f"A: {card['answer']}")
            console.print(f"💡 {card['mnemonic']}")
        
        if len(flashcards) > 3:
            console.print(f"\n... and {len(flashcards) - 3} more cards!")
        
        return True
    
    return False