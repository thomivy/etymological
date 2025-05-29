#!/usr/bin/env python3
"""
Create regression oracle - sample current word pairings before fixing the pairing engine.
This helps us verify we only lose junk pairings, not quality ones.
"""

import gzip
import json
import random
from pathlib import Path

def create_oracle():
    """Generate regression oracle with current pairings."""
    print("🔍 Creating regression oracle from current roots...")
    
    # Load current roots
    roots_file = Path("data/roots.json.gz")
    if not roots_file.exists():
        print("❌ No roots file found. Run build_roots.py first.")
        return
    
    with gzip.open(roots_file, 'rt', encoding='utf-8') as f:
        roots = json.load(f)
    
    # Generate all possible pairs
    all_pairs = []
    for root, words in roots.items():
        if len(words) >= 2:
            for i, w1 in enumerate(words):
                for w2 in words[i+1:]:
                    all_pairs.append((root, w1, w2))
    
    # Sample 200 random pairs
    random.shuffle(all_pairs)
    sample_pairs = all_pairs[:200]
    
    # Save oracle
    oracle_file = Path("data/regression_oracle.txt")
    with open(oracle_file, 'w', encoding='utf-8') as f:
        f.write("# Regression Oracle - Current Word Pairings\n")
        f.write("# Format: word1 + word2 -> root\n")
        f.write(f"# Generated from {len(roots)} roots, {len(all_pairs)} total pairs\n\n")
        
        for root, w1, w2 in sample_pairs:
            f.write(f"{w1} + {w2} -> {root}\n")
    
    print(f"✅ Saved {len(sample_pairs)} sample pairs to {oracle_file}")
    
    # Show some suspicious examples
    print("\n🚨 Some suspicious current pairings:")
    for root, w1, w2 in sample_pairs[:10]:
        if len(root) <= 3 or any(word in root.lower() for word in [w1.lower(), w2.lower()]):
            print(f"  {w1} + {w2} -> {root}")

if __name__ == "__main__":
    create_oracle() 