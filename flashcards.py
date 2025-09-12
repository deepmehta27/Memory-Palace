import re
import json
from typing import List, Dict
from utils import save_json, console, print_success, print_error, print_info, read_notes_file
from pathlib import Path

def simple_gemini_call(prompt: str) -> str:
    """Simple, fast Gemini call with proper error handling."""
    import subprocess
    try:
        # Use the most reliable Gemini CLI format
        result = subprocess.run(
            ['gemini', prompt],
            capture_output=True,
            text=True,
            timeout=20,  # Shorter timeout
            shell=False  # More reliable
        )
        
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            # Filter out CLI help messages and warnings
            lines = output.split('\n')
            filtered_lines = []
            skip_help = False
            
            for line in lines:
                # Skip common CLI help patterns
                if any(pattern in line.lower() for pattern in [
                    'usage:', 'options:', 'commands:', 'examples:', 
                    'help', '--', 'gemini [', 'version'
                ]):
                    skip_help = True
                    continue
                elif skip_help and (line.strip().startswith('-') or not line.strip()):
                    continue
                else:
                    skip_help = False
                    if line.strip():
                        filtered_lines.append(line)
            
            return '\n'.join(filtered_lines)
        
        return ""
        
    except subprocess.TimeoutExpired:
        print_error("Gemini timeout - using fallback")
        return ""
    except Exception as e:
        print_error(f"Gemini error: {e}")
        return ""

def extract_concepts_from_notes(content: str) -> List[Dict]:
    """Simplified concept extraction with faster processing."""
    
    # For long content, use chunking but with simpler processing
    if len(content) > 6000:
        return extract_from_chunks(content)
    
    # Create a focused, short prompt
    prompt = f"""Create flashcards from this content. Return ONLY a JSON array with this exact format:
[{{"question": "What is X?", "answer": "Definition here", "mnemonic": "Memory tip"}}]

Content:
{content[:4000]}  

Return only the JSON array, no other text."""

    print_info("Creating flashcards with Gemini...")
    
    response = simple_gemini_call(prompt)
    
    if response:
        try:
            # Simple JSON extraction
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                flashcards = json.loads(json_match.group())
                
                # Basic validation
                valid_cards = []
                for card in flashcards:
                    if (isinstance(card, dict) and 
                        'question' in card and 'answer' in card and
                        len(card['answer']) > 10):
                        
                        # Ensure mnemonic exists
                        if 'mnemonic' not in card:
                            card['mnemonic'] = f"Remember: {card['answer'][:30]}..."
                        
                        valid_cards.append(card)
                
                if valid_cards:
                    print_success(f"Generated {len(valid_cards)} flashcards with Gemini!")
                    return valid_cards
        
        except Exception as e:
            print_error(f"JSON parsing error: {e}")
    
    # Fast fallback - no complex processing
    print_info("Using quick local generation...")
    return create_simple_fallback(content)

def extract_from_chunks(content: str) -> List[Dict]:
    """Process long content in chunks quickly."""
    chunks = [content[i:i+4000] for i in range(0, len(content), 4000)]
    all_cards = []
    
    for i, chunk in enumerate(chunks[:3]):  # Limit to 3 chunks max
        print_info(f"Processing chunk {i+1}/3...")
        chunk_cards = extract_concepts_from_notes(chunk)
        all_cards.extend(chunk_cards)
    
    # Remove duplicates
    seen = set()
    unique_cards = []
    for card in all_cards:
        key = card['question'].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_cards.append(card)
    
    return unique_cards

def create_simple_fallback(content: str) -> List[Dict]:
    """Fast fallback flashcard creation."""
    flashcards = []
    
    # Simple pattern matching for common formats
    patterns = [
        r'\*\*([^*]+)\*\*[:\s]*([^.\n]+)',  # **Term**: Definition
        r'^([A-Z][a-zA-Z\s]+)\s*:\s*([^.\n]+)',  # Term: Definition
        r'#+\s*([^\n]+)\n([^\n]+)',  # Headers with content
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        for term, definition in matches:
            term = term.strip()
            definition = definition.strip()
            
            if len(term) > 2 and len(definition) > 15:
                flashcards.append({
                    "question": f"What is {term}?",
                    "answer": definition,
                    "mnemonic": f"Remember {term} - {definition[:30]}..."
                })
    
    # If still not enough, create from sentences
    if len(flashcards) < 3:
        sentences = re.split(r'[.!?]+', content)
        for sentence in sentences:
            if 20 < len(sentence) < 150 and any(word in sentence.lower() 
                                               for word in ['is', 'are', 'means', 'refers']):
                flashcards.append({
                    "question": f"What does this mean: {sentence[:50]}...?",
                    "answer": sentence.strip(),
                    "mnemonic": "Review your notes for full context!"
                })
                if len(flashcards) >= 10:
                    break
    
    return flashcards[:15]  # Limit to 15 cards

def generate_flashcards_from_file(file_path: str, output_path: str = "data/flashcards.json") -> bool:
    """Main function - simplified and faster."""
    
    print_info(f"Reading notes from: {file_path}")
    
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        print_error(f"File not found: {file_path}")
        return False
    
    content = read_notes_file(file_path_obj)
    if not content or len(content) < 50:
        print_error("File content is too short")
        return False
    
    print_info(f"Processing {len(content)} characters...")
    
    flashcards = extract_concepts_from_notes(content)
    
    if not flashcards:
        print_error("No flashcards generated")
        return False
    
    # Save flashcards
    if save_json(flashcards, output_path):
        print_success(f"Saved {len(flashcards)} flashcards to {output_path}")
        
        # Show preview
        console.print("\n[bold]Preview:[/bold]")
        for i, card in enumerate(flashcards[:2], 1):
            console.print(f"\n[cyan]Card {i}:[/cyan]")
            console.print(f"Q: {card['question']}")
            console.print(f"A: {card['answer']}")
            console.print(f"💡 {card['mnemonic']}")
        
        console.print(f"\n[green]Ready! {len(flashcards)} flashcards generated.[/green]")
        return True
    
    return False