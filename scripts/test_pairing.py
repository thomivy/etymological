#!/usr/bin/env python3
"""
Test the improved pairing engine without external dependencies.
"""

import sys
import gzip
import json
import random
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, Path(__file__).parent)

from utils_roots import looks_like_trivial_affix


def test_ablaut_unification(roots_file: str):
    """Test that ablaut variants are properly unified."""
    print(f"🔄 Testing ablaut unification in {roots_file}")
    
    try:
        with gzip.open(roots_file, 'rt', encoding='utf-8') as f:
            roots = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load roots: {e}")
        return
    
    # Test HABJAN family unification
    habjan = roots.get('HABJAN', {})
    if habjan:
        words = habjan.get('words', [])
        sources = habjan.get('sources', 0)
        
        print(f"✅ HABJAN family found:")
        print(f"  Words: {words}")
        print(f"  Sources: {sources}")
        
        # Check specific cognates
        key_words = ['have', 'hover', 'heave']
        found_words = [w for w in key_words if w in words]
        
        print(f"  Key cognates found: {found_words}")
        
        if 'have' in words and 'hover' in words:
            print(f"🎉 SUCCESS: have + hover can now be paired!")
        else:
            print(f"❌ ISSUE: have/hover not in same family")
    else:
        print("❌ HABJAN family not found")
    
    # Check for over-splitting
    habjan_variants = [k for k in roots.keys() if 'hab' in k.lower() and 'jan' in k.lower()]
    print(f"\n📊 HABJAN-related roots: {habjan_variants}")
    
    if len(habjan_variants) == 1:
        print("✅ No over-splitting detected")
    else:
        print(f"⚠️  Multiple HABJAN variants still exist: {habjan_variants}")


def test_pairing_quality(roots_file: str):
    """Test pairing quality with new system."""
    print(f"🧪 Testing pairing quality from {roots_file}")
    
    # Load roots
    try:
        with gzip.open(roots_file, 'rt', encoding='utf-8') as f:
            roots = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load roots: {e}")
        return
    
    print(f"📊 Loaded {len(roots)} roots")
    
    # Generate sample pairs
    all_pairs = []
    trivial_count = 0
    
    for root_id, root_data in roots.items():
        if isinstance(root_data, dict):
            words = root_data.get('words', [])
            gloss = root_data.get('gloss')
            sources = root_data.get('sources', 1)
        else:
            words = root_data
            gloss = None
            sources = 1
        
        if len(words) < 2:
            continue
        
        for i, w1 in enumerate(words):
            for w2 in words[i+1:]:
                is_trivial = looks_like_trivial_affix(root_id, w1, w2)
                all_pairs.append((root_id, w1, w2, gloss, sources, is_trivial))
                if is_trivial:
                    trivial_count += 1
    
    print(f"📈 Generated {len(all_pairs)} total pairs")
    print(f"⚠️  {trivial_count} trivial pairs ({trivial_count/len(all_pairs)*100:.1f}%)")
    
    # Show sample high-quality pairs (non-trivial)
    quality_pairs = [p for p in all_pairs if not p[5]]
    sample_pairs = random.sample(quality_pairs, min(10, len(quality_pairs)))
    
    print("\n✨ Sample high-quality pairs:")
    for root_id, w1, w2, gloss, sources, _ in sample_pairs:
        gloss_str = f' ("{gloss}")' if gloss else ''
        print(f"  {w1} + {w2} -> {root_id}{gloss_str} (sources: {sources})")
    
    # Show sample trivial pairs that would be filtered
    if trivial_count > 0:
        trivial_pairs = [p for p in all_pairs if p[5]]
        sample_trivial = random.sample(trivial_pairs, min(5, len(trivial_pairs)))
        
        print("\n🚫 Sample trivial pairs (filtered by default):")
        for root_id, w1, w2, gloss, sources, _ in sample_trivial:
            print(f"  {w1} + {w2} -> {root_id} (trivial morphology)")
    
    # Quality score
    quality_score = (len(all_pairs) - trivial_count) / len(all_pairs) * 100
    print(f"\n🎯 Quality Score: {quality_score:.1f}%")
    
    if quality_score > 90:
        print("🏆 EXCELLENT quality")
    elif quality_score > 80:
        print("✅ GOOD quality")
    elif quality_score > 70:
        print("⚠️  FAIR quality")
    else:
        print("❌ POOR quality")


def compare_old_vs_new():
    """Compare old vs new roots if both exist."""
    old_file = "data/roots_backup.json.gz"
    new_file = "data/roots.json.gz"
    
    if not Path(old_file).exists() or not Path(new_file).exists():
        print("⚠️  Cannot compare - missing old or new roots file")
        return
    
    print(f"\n🔄 Comparing old vs new systems:")
    
    # Load both
    with gzip.open(old_file, 'rt') as f:
        old_roots = json.load(f)
    
    with gzip.open(new_file, 'rt') as f:
        new_roots = json.load(f)
    
    # Count old pairs (simple format)
    old_pairs = 0
    for words in old_roots.values():
        if len(words) >= 2:
            old_pairs += len(words) * (len(words) - 1) // 2
    
    # Count new pairs (structured format)
    new_pairs = 0
    for root_data in new_roots.values():
        words = root_data.get('words', [])
        if len(words) >= 2:
            new_pairs += len(words) * (len(words) - 1) // 2
    
    print(f"  📊 Old system: {len(old_roots):,} roots, {old_pairs:,} pairs")
    print(f"  📊 New system: {len(new_roots):,} roots, {new_pairs:,} pairs")
    print(f"  📈 Change: {(len(new_roots)/len(old_roots)-1)*100:+.1f}% roots, {(new_pairs/old_pairs-1)*100:+.1f}% pairs")


if __name__ == "__main__":
    # Test ablaut unification
    test_ablaut_unification("data/roots.json.gz")
    
    print("\n" + "="*60 + "\n")
    
    # Test new system
    test_pairing_quality("data/roots.json.gz")
    
    # Compare if both exist
    compare_old_vs_new()
    
    print("\n🎉 Testing completed!") 