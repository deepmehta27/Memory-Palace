import re
import json
from typing import List, Dict
from utils import call_gemini_cli, save_json, console, print_success, print_error, print_info, read_notes_file
from pathlib import Path
from rich.panel import Panel
from rich.table import Table

def extract_concepts_from_notes(content: str) -> List[Dict]:
    """Extract concepts from notes using Gemini CLI."""
    
    # Split long content into chunks if needed
    content_length = len(content)
    if content_length > 8000:
        print_info(f"Large file detected ({content_length} chars). Processing in chunks...")
        return extract_concepts_from_long_content(content)
    
    prompt = f"""
Analyze these study notes and extract exactly 10 key concepts for flashcards.

For each concept, create:
1. A clear, specific question
2. A complete, detailed answer
3. A memorable mnemonic or funny analogy

Format your response strictly as a JSON array of 20 flashcards:
[
  {{
    "question": "What is photosynthesis?",
    "answer": "The process plants use to convert sunlight into energy",
    "mnemonic": "Think of plants as solar panels making sugar batteries ☀️🔋"
  }}
]

Notes to analyze:
{content}

IMPORTANT: 
- Extract EVERY concept, term, and definition you can find
- Generate exactly 10 flashcards, no more, no less
- Make mnemonics fun, memorable, and slightly humorous
- Only respond with the JSON array, no other text
"""
    
    console.print("[bold cyan]🧠 Analyzing content and generating flashcards...[/bold cyan]")
    
    response = call_gemini_cli(prompt, model="gemini-2.5-flash")
    
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
            for card in flashcards[:10]:
                if isinstance(card, dict) and 'question' in card and 'answer' in card:
                    if 'mnemonic' not in card or not card['mnemonic']:
                        card['mnemonic'] = f"Remember: {card['answer'][:50]}... 🧠"
                    valid_flashcards.append(card)

            # 🔥 Add this padding block here
            while len(valid_flashcards) < 10:
                valid_flashcards.append({
                    "question": f"Extra concept {len(valid_flashcards)+1}?",
                    "answer": "Review your notes for details.",
                    "mnemonic": "Keep practicing 📚"
                })

            if valid_flashcards:
                print_success(f"Generated {len(valid_flashcards)} flashcards!")
                return valid_flashcards
            else:
                print_error("No valid flashcards in Gemini response")
                return create_fallback_flashcards(content)
            
    except json.JSONDecodeError as e:
        print_error(f"Could not parse Gemini response as JSON: {e}")
        return create_fallback_flashcards(content)
    except Exception as e:
        print_error(f"Error processing Gemini response: {e}")
        return create_fallback_flashcards(content)

def extract_concepts_from_long_content(content: str) -> List[Dict]:
    """Extract concepts from long content by processing in chunks."""
    # Split content into chunks
    chunk_size = 6000
    chunks = []
    
    # Try to split by sections first
    sections = re.split(r'\n#{1,3}\s+', content)
    
    current_chunk = ""
    for section in sections:
        if len(current_chunk) + len(section) > chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = section
        else:
            current_chunk += "\n" + section if current_chunk else section
    
    if current_chunk:
        chunks.append(current_chunk)
    
    all_flashcards = []
    
    for i, chunk in enumerate(chunks, 1):
        console.print(f"[dim]Processing chunk {i}/{len(chunks)}...[/dim]")
        chunk_cards = extract_concepts_from_notes(chunk)
        all_flashcards.extend(chunk_cards)
    
    # Remove duplicates
    seen_questions = set()
    unique_flashcards = []
    for card in all_flashcards:
        question_key = card['question'].lower().strip()
        if question_key not in seen_questions:
            seen_questions.add(question_key)
            unique_flashcards.append(card)
    
    print_success(f"Processed {len(chunks)} chunks, generated {len(unique_flashcards)} unique flashcards!")
    return unique_flashcards

def create_fallback_flashcards(content: str) -> List[Dict]:
    """Create comprehensive flashcards if Gemini parsing fails."""
    console.print("[yellow]Creating fallback flashcards from content...[/yellow]")
    
    flashcards = []
    
    # Enhanced patterns for better extraction
    patterns = [
        r'\*\*([^*\n]+)\*\*\s*[:=]\s*([^.\n]+(?:\.[^.\n]*)*)',  # **Term**: Definition
        r'^([A-Z][a-zA-Z\s\-]+)\s*[:=]\s*([^.\n]+(?:\.[^.\n]*)*)',  # Term: Definition
        r'(?:^|\n)([A-Z][a-zA-Z\s]+)\s*[-–]\s*([^.\n]+(?:\.[^.\n]*)*)',  # Term - Definition
        r'(?:^|\n)([A-Z][a-zA-Z\s]+):\s*([^.\n]+(?:\.[^.\n]*)*)',  # Simple Term: Definition
        r'#+\s*([^#\n]+)\n([^#\n]+(?:\n[^#\n]+)*)',  # Markdown headers with content
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        for term, definition in matches:
            term = term.strip()
            definition = definition.strip()
            
            # Quality checks
            if (len(term) > 2 and len(definition) > 15 and 
                len(term) < 100 and len(definition) < 500 and
                not term.lower().startswith(('the ', 'a ', 'an '))):
                
                flashcards.append({
                    "question": f"What is {term}?",
                    "answer": definition,
                    "mnemonic": f"Think of {term} as a key concept to remember! 🔑"
                })
    
    # Remove duplicates
    seen = set()
    unique_flashcards = []
    
    for card in flashcards:
        key = re.sub(r'[^\w]', '', card['question'].lower())
        if key not in seen and len(card['answer']) > 20:
            seen.add(key)
            unique_flashcards.append(card)
    
    # If still not enough cards, create some generic ones
    if len(unique_flashcards) < 5:
        # Extract any capitalized terms as potential concepts
        terms = re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', content)
        term_counts = {}
        for term in terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        
        # Use most frequent terms
        frequent_terms = sorted(term_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        for term, count in frequent_terms:
            if count >= 2:  # Term appears multiple times
                unique_flashcards.append({
                    "question": f"What is {term}?",
                    "answer": f"{term} is an important concept from your study material. Review the source for details.",
                    "mnemonic": f"Look up {term} in your notes for the full definition! 📚"
                })
    
    if not unique_flashcards:
        # Last resort - create a general flashcard
        unique_flashcards.append({
            "question": "What are the main topics covered in these notes?",
            "answer": "Review your notes to identify the key concepts and themes",
            "mnemonic": "Notes are like treasure maps - explore them for knowledge! 🗺️"
        })
    
    console.print(f"[green]Created {len(unique_flashcards)} fallback flashcards[/green]")
    return unique_flashcards

def generate_flashcards_from_file(file_path: str, output_path: str = "data/flashcards.json") -> bool:
    """Generate flashcards from a notes file and save them."""
    
    console.print(f"\n[bold magenta]📚 Reading notes from: {file_path}[/bold magenta]")
    
    # Use improved file reading
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        print_error(f"File not found: {file_path}")
        return False
    
    content = read_notes_file(file_path_obj)
    if not content:
        print_error("Could not read file or file is empty")
        return False
    
    console.print(f"[dim]File content length: {len(content)} characters[/dim]")
    
    if len(content) < 50:
        print_error("File content is too short to generate meaningful flashcards")
        return False
    
    flashcards = extract_concepts_from_notes(content)
    
    if not flashcards:
        print_error("No flashcards generated")
        return False
    
    # Load existing flashcards if any
    existing_flashcards = []
    output_path_obj = Path(output_path)
    if output_path_obj.exists():
        try:
            with open(output_path_obj, 'r', encoding='utf-8') as f:
                existing_flashcards = json.load(f)
                if not isinstance(existing_flashcards, list):
                    existing_flashcards = []
        except:
            existing_flashcards = []
    
    # Merge new flashcards with existing ones (avoiding duplicates)
    existing_questions = {card.get('question', '').lower() for card in existing_flashcards}
    new_flashcards = []
    for card in flashcards:
        if card['question'].lower() not in existing_questions:
            new_flashcards.append(card)
    
    # Combine all flashcards
    all_flashcards = flashcards  
    
    # Save flashcards
    if save_json(all_flashcards, output_path):
        console.print(f"\n[bold green]✅ Flashcards saved successfully![/bold green]")
        
        # Show preview in a nice table
        table = Table(title="📝 Preview of Generated Flashcards", 
                     title_style="bold cyan",
                     border_style="bright_blue")
        table.add_column("Question", style="cyan", width=40)
        table.add_column("Answer", style="green", width=40)
        table.add_column("Mnemonic", style="yellow", width=30)
        
        preview_count = min(3, len(new_flashcards))
        for card in new_flashcards[:preview_count]:
            table.add_row(
                card['question'][:37] + "..." if len(card['question']) > 40 else card['question'],
                card['answer'][:37] + "..." if len(card['answer']) > 40 else card['answer'],
                card['mnemonic'][:27] + "..." if len(card['mnemonic']) > 30 else card['mnemonic']
            )
        
        console.print(table)
        
        if len(new_flashcards) > preview_count:
            console.print(f"\n[bold cyan]... and {len(new_flashcards) - preview_count} more cards![/bold cyan]")
        
        console.print(Panel(
            f"[bold green]Total flashcards in database: {len(all_flashcards)}[/bold green]\n"
            f"[cyan]New cards added: {len(new_flashcards)}[/cyan]",
            title="📊 Summary",
            border_style="green"
        ))
        return True
    
    return False