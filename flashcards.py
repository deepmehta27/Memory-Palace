import re
import json
from typing import List, Dict
from utils import call_gemini_cli, save_json, console, print_success, print_error, print_info, read_notes_file
from pathlib import Path

def extract_concepts_from_notes(content: str) -> List[Dict]:
    """Extract concepts from notes using Gemini CLI."""
    
    # Split long content into chunks if needed
    content_length = len(content)
    if content_length > 8000:
        print_info(f"Large file detected ({content_length} chars). Processing in chunks...")
        return extract_concepts_from_long_content(content)
    
    prompt = f"""
Analyze these study notes and extract ALL key concepts for flashcards. Create comprehensive flashcards covering every important term, concept, and definition.

For each concept, create:
1. A clear, specific question
2. A complete, detailed answer
3. A memorable mnemonic or funny analogy

Format your response as a JSON array with AT LEAST 15-25 flashcards:
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
- Aim for 20+ flashcards for comprehensive coverage
- Make mnemonics fun, memorable, and slightly humorous
- Only respond with the JSON array, no other text
- Include both basic and advanced concepts
"""
    
    print_info("🧠 Asking Gemini to extract comprehensive concepts and create mnemonics...")
    
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
            cleaned_response = '\n'.join(line for line in lines if not line.startswith('```') and not line.startswith('json'))
        
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
                    if 'mnemonic' not in card or not card['mnemonic']:
                        card['mnemonic'] = f"Remember: {card['answer'][:50]}... 🧠"
                    valid_flashcards.append(card)
            
            if valid_flashcards:
                print_success(f"Generated {len(valid_flashcards)} flashcards!")
                if len(valid_flashcards) < 10:
                    print_info("Fewer flashcards than expected. Enhancing with fallback extraction...")
                    fallback_cards = create_fallback_flashcards(content)
                    # Merge without duplicates
                    existing_questions = {card['question'].lower() for card in valid_flashcards}
                    for fallback_card in fallback_cards:
                        if fallback_card['question'].lower() not in existing_questions:
                            valid_flashcards.append(fallback_card)
                    print_success(f"Enhanced to {len(valid_flashcards)} total flashcards!")
                return valid_flashcards
            else:
                print_error("No valid flashcards in Gemini response")
                return create_fallback_flashcards(content)
        else:
            print_error("Could not find JSON in Gemini response")
            return create_fallback_flashcards(content)
            
    except json.JSONDecodeError as e:
        print_error(f"Could not parse Gemini response as JSON: {e}")
        print_info("Gemini response preview: " + response[:200] + "...")
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
        print_info(f"Processing chunk {i}/{len(chunks)}...")
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
    print_info("Creating comprehensive fallback flashcards from content...")
    
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
    
    # Additional extraction for definition-style sentences
    definition_pattern = r'([A-Z][a-zA-Z\s]+) (?:is|are|refers to|means?) ([^.]+\.?)'
    def_matches = re.findall(definition_pattern, content)
    
    for term, definition in def_matches:
        term = term.strip()
        definition = definition.strip()
        
        if (len(term) > 2 and len(definition) > 15 and 
            len(term) < 100 and len(definition) < 300):
            
            flashcards.append({
                "question": f"What does {term} mean?",
                "answer": definition,
                "mnemonic": f"Remember {term} with this definition! 💡"
            })
    
    # Remove duplicates and low-quality cards
    seen = set()
    unique_flashcards = []
    
    for card in flashcards:
        # Normalize question for comparison
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
    
    print_success(f"Created {len(unique_flashcards)} comprehensive fallback flashcards")
    return unique_flashcards

def generate_flashcards_from_file(file_path: str, output_path: str = "data/flashcards.json") -> bool:
    """Generate flashcards from a notes file."""
    
    print_info(f"Reading notes from: {file_path}")
    
    # Use improved file reading
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        print_error(f"File not found: {file_path}")
        return False
    
    content = read_notes_file(file_path_obj)
    if not content:
        print_error("Could not read file or file is empty")
        return False
    
    print_info(f"File content length: {len(content)} characters")
    
    if len(content) < 50:
        print_error("File content is too short to generate meaningful flashcards")
        return False
    
    flashcards = extract_concepts_from_notes(content)
    
    if not flashcards:
        print_error("No flashcards generated")
        return False
    
    # Save flashcards
    if save_json(flashcards, output_path):
        print_success(f"Flashcards saved to {output_path}")
        
        # Show preview
        console.print("\n[bold]Preview of generated flashcards:[/bold]")
        preview_count = min(3, len(flashcards))
        for i, card in enumerate(flashcards[:preview_count], 1):
            console.print(f"\n[cyan]Card {i}:[/cyan]")
            console.print(f"Q: {card['question']}")
            console.print(f"A: {card['answer']}")
            console.print(f"💡 {card['mnemonic']}")
        
        if len(flashcards) > preview_count:
            console.print(f"\n... and {len(flashcards) - preview_count} more cards!")
        
        console.print(f"\n[green]Total: {len(flashcards)} flashcards ready for studying![/green]")
        return True
    
    return False