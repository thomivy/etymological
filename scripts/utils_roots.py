#!/usr/bin/env python3
"""
Root canonicalization utilities for etymology processing.

Handles proper normalization of PIE and other reconstructed roots to prevent
accidental merging of unrelated etymological families.
"""

import re
import unicodedata
from typing import Optional


def canonical_id(raw_root: str) -> Optional[str]:
    """
    Convert a raw root string to a canonical ID.
    
    Returns None for junk/invalid roots.
    
    Examples:
        "*wr̥-idh-" -> "WRIDH"
        "*wer-(2)" -> "WER(2)"  
        "PIE *bhel-" -> "BHEL"
        "ghen" -> "GHEN"
        "car" -> None (too short, likely morphological)
        "*habjan-" -> "HABJAN" (handles ablaut variants)
    """
    if not raw_root or not isinstance(raw_root, str):
        return None
    
    # Clean up the input
    root = raw_root.strip()
    if not root:
        return None
    
    # Remove common prefixes
    prefixes_to_remove = [
        'PIE ', 'Proto-Indo-European ', 'Proto-Germanic ', 'Proto-Celtic ',
        'Proto-Slavic ', 'Proto-Baltic ', 'Sanskrit ', 'Latin ', 'Greek ',
        'from ', 'ultimately from ', 'root ', 'the root '
    ]
    
    root_lower = root.lower()
    for prefix in prefixes_to_remove:
        if root_lower.startswith(prefix.lower()):
            root = root[len(prefix):].strip()
            break
    
    # Remove leading asterisk (reconstruction marker)
    root = root.lstrip('*').strip()
    
    # If already in Leiden/canonical style (uppercase with parentheses), keep it
    if re.match(r'^[A-Z][A-Z\-]*(\([0-9]+\))?$', root):
        return root
    
    # Normalize Unicode (decompose combining characters)
    root = unicodedata.normalize('NFD', root)
    
    # Remove combining diacritics (category Mn) but keep base characters
    root = ''.join(c for c in root if unicodedata.category(c) != 'Mn')
    
    # Preserve numbered parentheses (e.g., "(2)") but remove other punctuation
    numbered_suffix = ""
    paren_match = re.search(r'\((\d+)\)$', root)
    if paren_match:
        numbered_suffix = f"({paren_match.group(1)})"
        root = root[:paren_match.start()]
    
    # Remove most punctuation but preserve hyphens temporarily
    root = re.sub(r'[^\w\-]', '', root)
    
    # Convert to uppercase (Leiden convention)
    root = root.upper()
    
    # ABLAUT AND ORTHOGRAPHIC NORMALIZATION
    # Handle common Germanic/PIE ablaut patterns and variants
    
    # Gemination variants (habjan/habbjan, etc.)
    root = re.sub(r'([BCDFGHJKLMNPQRSTVWXYZ])\1+', r'\1', root)  # Remove gemination
    
    # Ablaut grade normalization - map to canonical form
    ablaut_mappings = {
        # Germanic *habjan- family (have/hover/heave)
        r'HAB[BJ]*AN': 'HABJAN',
        r'HAF[FT]*AN': 'HABJAN',  # haft variant
        r'HEB[BJ]*AN': 'HABJAN',  # hebban variant
        
        # PIE *wer- family (various grades)
        r'WER[HDNT]*': 'WER',
        r'WOR[HDNT]*': 'WER', 
        r'WUR[HDNT]*': 'WER',
        
        # PIE *bhel- family (blow/belly)
        r'BHEL[HJLW]*': 'BHEL',
        r'BHOL[HJLW]*': 'BHEL',
        r'BHUL[HJLW]*': 'BHEL',
        
        # PIE *dʰeh₁- family (do/deed)
        r'DHE[HJ]*': 'DHE',
        r'DHO[HJ]*': 'DHE',
        r'DHA[HJ]*': 'DHE',
        
        # Common Germanic patterns
        r'([BCDFGHJKLMNPQRSTVWXYZ]+)IAN': r'\1JAN',  # -ian -> -jan
        r'([BCDFGHJKLMNPQRSTVWXYZ]+)IJ': r'\1J',     # -ij -> -j
    }
    
    # Apply ablaut normalizations
    original_root = root
    for pattern, replacement in ablaut_mappings.items():
        root = re.sub(pattern, replacement, root)
    
    # Remove all hyphens for canonical form (but keep numbered suffix)
    root = root.replace('-', '')
    
    # Add back numbered suffix if it existed
    root = root + numbered_suffix
    
    # Validate final result
    if len(root.replace('(', '').replace(')', '').replace('-', '')) < 3:
        return None
    
    if root.replace('(', '').replace(')', '').isdigit():
        return None
    
    # Must contain at least one letter
    if not any(c.isalpha() for c in root):
        return None
    
    # Be more restrictive on 3-letter combinations that are likely morphological
    root_letters_only = re.sub(r'[^A-Z]', '', root)
    if len(root_letters_only) == 3:
        # Common morphological patterns to exclude
        morphological_patterns = {
            'CAR', 'CAT', 'BAT', 'BAD', 'BAG', 'BIG', 'BOX', 'BOY', 'BAY',
            'CUP', 'CUT', 'DOG', 'EAR', 'EYE', 'FAR', 'FUN', 'GET', 'GOT',
            'HAD', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW',
            'OLD', 'OUR', 'OUT', 'PUT', 'RUN', 'SAY', 'SEE', 'SIT', 'THE',
            'TOO', 'TOP', 'TWO', 'USE', 'WAY', 'WHO', 'WIN', 'YES', 'YET',
        }
        if root_letters_only in morphological_patterns:
            return None
    
    # Filter out common non-root words that slip through
    non_roots = {
        'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HAD',
        'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS',
        'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY',
        'DID', 'SHE', 'USE', 'WAY', 'OIL', 'SIT', 'SET', 'RUN', 'EAT',
        'ENGLISH', 'GERMAN', 'FRENCH', 'DUTCH', 'LATIN', 'GREEK', 'SANSKRIT',
        'MIDDLE', 'PROTO', 'ANCIENT', 'EARLY', 'COGNATE', 'RELATED', 'COMPARE',
        'ALSO', 'WORD', 'TERM', 'MEANING', 'SENSE', 'LITERALLY', 'ORIGINALLY',
        'PROBABLY', 'POSSIBLY', 'PERHAPS', 'SCOTS', 'WELSH', 'IRISH', 'NORSE',
        'GERMANIC', 'CELTIC', 'SLAVIC', 'INFLUENCED', 'BORROWED', 'AKIN'
    }
    
    if root_letters_only in non_roots:
        return None
    
    return root


def extract_gloss(etymology_text: str, root: str) -> Optional[str]:
    """
    Extract the gloss (meaning) for a root from etymology text.
    
    Looks for patterns like: *root* ("meaning") or *root* "meaning"
    """
    if not etymology_text or not root:
        return None
    
    # Look for quoted meanings near the root
    patterns = [
        rf'\*?{re.escape(root)}\*?\s*\("([^"]+)"\)',  # *root* ("meaning")
        rf'\*?{re.escape(root)}\*?\s*"([^"]+)"',      # *root* "meaning"
        rf'\*?{re.escape(root)}\*?\s*\(([^)]+)\)',    # *root* (meaning)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, etymology_text, re.IGNORECASE)
        if match:
            gloss = match.group(1).strip()
            # Clean up the gloss
            if gloss and len(gloss) < 50:  # Reasonable length
                return gloss
    
    return None


def looks_like_trivial_affix(root: str, word1: str, word2: str) -> bool:
    """
    Check if a pairing looks like trivial morphological inheritance.
    
    Returns True if the root appears as a substring in both words,
    suggesting this is just prefix/suffix variation rather than 
    interesting semantic divergence.
    """
    if not root or not word1 or not word2:
        return False
    
    root_clean = root.lower().strip('-')
    if len(root_clean) < 3:
        return False
    
    # Check if root appears in both words
    word1_lower = word1.lower()
    word2_lower = word2.lower()
    
    return root_clean in word1_lower and root_clean in word2_lower


# Test cases for development
def _test_canonical_id():
    """Test cases for canonical_id function."""
    test_cases = [
        ("*wr̥-idh-", "WRIDH"),
        ("*wer-(2)", "WER(2)"),
        ("PIE *bhel-", "BHEL"),
        ("ghen", "GHEN"),
        ("car", None),  # Too short
        ("the", None),  # Common word
        ("BHEL", "BHEL"),  # Already canonical
        ("*deḱ-", "DEK"),
        ("", None),
        (None, None),
    ]
    
    for input_root, expected in test_cases:
        result = canonical_id(input_root)
        status = "✅" if result == expected else "❌"
        print(f"{status} canonical_id('{input_root}') = '{result}' (expected '{expected}')")


if __name__ == "__main__":
    print("Testing canonical_id function:")
    _test_canonical_id() 