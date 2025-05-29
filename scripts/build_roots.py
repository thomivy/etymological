#!/usr/bin/env python3
"""
Etymology corpus builder for EtymoBot GitHub-native pipeline.

Processes Wiktionary JSONL dump to extract etymological roots and build
word mappings. This replaces live web scraping with offline data processing.

Usage:
    python build_roots.py --input data/wiktionary-data.jsonl.gz --output data/roots.json.gz
"""

import json
import gzip
import re
import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Set, List, Optional
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WiktionaryProcessor:
    """Processes Wiktionary JSONL dump to extract etymology mappings."""
    
    def __init__(self, min_word_length: int = 3, max_word_length: int = 15):
        self.min_word_length = min_word_length
        self.max_word_length = max_word_length
        
        # Improved patterns focusing on actual etymological roots
        self.root_patterns = [
            # Proto-language reconstructions (asterisked forms) - highest priority
            r'Proto-[A-Za-z-]+\s+\*([a-zA-Z\-ₐ₁₂₃₄₅₆₇₈₉₀]+)',
            r'PIE\s+\*([a-zA-Z\-ₐ₁₂₃₄₅₆₇₈₉₀]+)',
            r'Proto-Indo-European\s+\*([a-zA-Z\-ₐ₁₂₃₄₅₆₇₈₉₀]+)',
            
            # Other asterisked reconstructions
            r'\*([a-zA-Z\-ₐ₁₂₃₄₅₆₇₈₉₀]{3,})\b',  # Any asterisked form, min 3 chars
            
            # Explicit root statements
            r'from\s+(?:the\s+)?root\s+\*?([a-zA-Z\-ₐ₁₂₃₄₅₆₇₈₉₀]{3,})',
            r'ultimately\s+from\s+\*([a-zA-Z\-ₐ₁₂₃₄₅₆₇₈₉₀]{3,})',
            
            # Sanskrit/Latin roots (typically appear in specific patterns)
            r'Sanskrit\s+([a-zA-Z\-]{3,})\s*\(',  # Sanskrit roots usually followed by parentheses
            r'Latin\s+([a-zA-Z\-]{3,})\s*\(',     # Latin roots usually followed by parentheses
            
            # Root endings that indicate they're actual roots, not language names
            r'from\s+([a-zA-Z\-]*(?:ghen|bhel|wegh|dʰeh|gwem|treud|stel|bʰer|ǵʰen)[a-zA-Z\-]*)',
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.root_patterns]
    
    def is_valid_word(self, word: str) -> bool:
        """Check if word is valid for processing."""
        if not word or not isinstance(word, str):
            return False
        
        # Basic length and character checks
        if not (self.min_word_length <= len(word) <= self.max_word_length):
            return False
        
        # Must be alphabetic (no numbers, punctuation)
        if not word.isalpha():
            return False
        
        # Skip very common function words that rarely have interesting etymology
        skip_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
            'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy',
            'did', 'she', 'use', 'way', 'who', 'oil', 'sit', 'set', 'run', 'eat'
        }
        
        if word.lower() in skip_words:
            return False
        
        return True
    
    def extract_roots_from_text(self, etymology_text: str) -> Set[str]:
        """Extract roots from etymology text using regex patterns."""
        if not etymology_text:
            return set()

        roots = set()
        
        for pattern in self.compiled_patterns:
            matches = pattern.findall(etymology_text)
            for match in matches:
                # Clean up the root more carefully
                # Remove asterisks but keep special etymological characters
                root = match.strip('*').strip()
                
                # Remove only certain punctuation, keep diacritics and special chars
                root = re.sub(r'[^\w\-ₐ₁₂₃₄₅₆₇₈₉₀ʰʷʸʲᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ]', '', root)
                root = root.strip('-').lower()
                
                # Skip obvious non-roots (language names, common words, etc.)
                skip_patterns = {
                    'dutch', 'german', 'english', 'french', 'latin', 'greek', 'sanskrit',
                    'middle', 'old', 'proto', 'ancient', 'early', 'cognate', 'related',
                    'compare', 'see', 'also', 'word', 'term', 'meaning', 'sense',
                    'literally', 'originally', 'probably', 'possibly', 'perhaps',
                    'scots', 'welsh', 'irish', 'norse', 'germanic', 'celtic', 'slavic',
                    'saterland', 'frisian', 'lithuanian', 'latvian', 'polish',
                    'influenced', 'borrowed', 'related', 'akin'
                }
                
                if root.lower() in skip_patterns:
                    continue
                
                # Validate root format - must be substantive and look like a root
                if 3 <= len(root) <= 25 and not root.isdigit():
                    # Additional checks for valid roots
                    if any(c.isalpha() for c in root):  # Must contain letters
                        roots.add(root)

        return roots
    
    def process_entry(self, entry: dict) -> List[tuple]:
        """Process a single Wiktionary entry and extract root-word mappings."""
        mappings = []
        
        # Get the word
        word = entry.get('word', '').strip().lower()
        if not self.is_valid_word(word):
            return mappings
        
        # Look for etymology information
        etymology_sources = []
        
        # Check main etymology field
        if 'etymology_text' in entry:
            etymology_sources.append(entry['etymology_text'])
        
        # Check in senses for etymology
        for sense in entry.get('senses', []):
            if 'etymology' in sense:
                etymology_sources.append(sense['etymology'])
        
        # Check etymology_texts array
        for etym in entry.get('etymology_texts', []):
            etymology_sources.append(etym)
        
        # Extract roots from all etymology sources
        all_roots = set()
        for etym_text in etymology_sources:
            if etym_text and isinstance(etym_text, str):
                roots = self.extract_roots_from_text(etym_text)
                all_roots.update(roots)
        
        # Create mappings
        for root in all_roots:
            mappings.append((root, word))
        
        return mappings
    
    def process_jsonl_file(self, input_path: str, max_entries: Optional[int] = None) -> Dict[str, List[str]]:
        """Process the entire JSONL file and build root mappings."""
        logger.info(f"Processing Wiktionary dump: {input_path}")
        
        root_to_words = defaultdict(set)
        entries_processed = 0
        entries_with_etymology = 0
        
        try:
            with gzip.open(input_path, 'rt', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line_num % 100000 == 0:
                        logger.info(f"Processed {line_num:,} lines, found {len(root_to_words)} roots so far...")
                    
                    if max_entries and entries_processed >= max_entries:
                        logger.info(f"Reached maximum entries limit: {max_entries}")
                        break
                    
                    try:
                        entry = json.loads(line.strip())
                        entries_processed += 1
                        
                        # Process this entry
                        mappings = self.process_entry(entry)
                        
                        if mappings:
                            entries_with_etymology += 1
                            for root, word in mappings:
                                root_to_words[root].add(word)
                    
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON decode error on line {line_num}: {e}")
                        continue
                    except Exception as e:
                        logger.debug(f"Error processing line {line_num}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Error reading file {input_path}: {e}")
            return {}
        
        # Filter to roots with multiple words and convert to final format
        final_mapping = {}
        for root, words_set in root_to_words.items():
            if len(words_set) >= 2:  # Only include roots with multiple descendants
                final_mapping[root] = sorted(list(words_set))
        
        logger.info(f"Processing complete:")
        logger.info(f"  📚 Processed {entries_processed:,} entries")
        logger.info(f"  🔍 Found etymology in {entries_with_etymology:,} entries")
        logger.info(f"  🌳 Extracted {len(final_mapping)} roots with multiple descendants")
        logger.info(f"  📖 Total word relationships: {sum(len(words) for words in final_mapping.values()):,}")
        
        return final_mapping
    
    def save_roots(self, root_mapping: Dict[str, List[str]], output_path: str):
        """Save root mapping to compressed JSON."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with gzip.open(output_file, 'wt', encoding='utf-8') as f:
            json.dump(root_mapping, f, ensure_ascii=False, indent=None, separators=(',', ':'))
        
        # Log statistics
        file_size = output_file.stat().st_size
        logger.info(f"💾 Saved {len(root_mapping)} roots to {output_path}")
        logger.info(f"📏 File size: {file_size / 1024 / 1024:.1f} MB")
        
        # Show sample data
        sample_roots = list(root_mapping.keys())[:5]
        logger.info("📋 Sample roots:")
        for root in sample_roots:
            words = root_mapping[root][:8]  # Show first 8 words
            word_list = ', '.join(words)
            if len(root_mapping[root]) > 8:
                word_list += f" ... ({len(root_mapping[root])} total)"
            logger.info(f"    {root}: {word_list}")


def main():
    """Main entry point for the etymology corpus builder."""
    parser = argparse.ArgumentParser(description='Build etymology corpus from Wiktionary JSONL dump')
    parser.add_argument('--input', '-i', default='data/wiktionary-data.jsonl.gz',
                      help='Path to Wiktionary JSONL dump file')
    parser.add_argument('--output', '-o', default='data/roots.json.gz',
                      help='Output path for compressed roots file')
    parser.add_argument('--max-entries', '-m', type=int,
                      help='Maximum number of entries to process (for testing)')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if input file exists
    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}")
        logger.info("Download the Wiktionary dump first:")
        logger.info("curl -o data/wiktionary-data.jsonl.gz https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl.gz")
        sys.exit(1)
    
    try:
        processor = WiktionaryProcessor()
        root_mapping = processor.process_jsonl_file(args.input, args.max_entries)
        
        if not root_mapping:
            logger.error("No etymology data extracted from dump file.")
            sys.exit(1)
        
        processor.save_roots(root_mapping, args.output)
        logger.info("✅ Etymology corpus build completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 