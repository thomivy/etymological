#!/usr/bin/env python3
"""
Audit etymology roots for quality and sanity.

Samples roots and checks for common issues like trivial morphological 
inheritance or suspicious groupings.
"""

import gzip
import json
import random
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from utils_roots import looks_like_trivial_affix

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def audit_roots(roots_file: str, sample_size: int = 100) -> Dict[str, float]:
    """
    Audit root quality by sampling and checking for common issues.
    
    Returns dictionary of metrics.
    """
    logger.info(f"🔍 Auditing roots from {roots_file}")
    
    # Load roots
    roots_path = Path(roots_file)
    if not roots_path.exists():
        logger.error(f"Roots file not found: {roots_file}")
        return {}
    
    try:
        with gzip.open(roots_path, 'rt', encoding='utf-8') as f:
            roots = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load roots: {e}")
        return {}
    
    # Handle both old and new formats
    root_items = []
    for root_id, root_data in roots.items():
        if isinstance(root_data, dict):
            words = root_data.get('words', [])
            gloss = root_data.get('gloss')
            sources = root_data.get('sources', 1)
        else:
            words = root_data  # Legacy format
            gloss = None
            sources = 1
        
        if len(words) >= 2:
            root_items.append((root_id, words, gloss, sources))
    
    logger.info(f"Found {len(root_items)} roots with multiple descendants")
    
    # Sample roots for analysis
    sample_roots = random.sample(root_items, min(sample_size, len(root_items)))
    
    # Analyze sample
    total_pairs = 0
    trivial_pairs = 0
    suspicious_pairs = 0
    short_root_pairs = 0
    
    print(f"\n📋 Analyzing {len(sample_roots)} sampled roots:")
    print("-" * 80)
    
    for root_id, words, gloss, sources in sample_roots:
        # Generate pairs for this root
        root_pairs = []
        for i, w1 in enumerate(words):
            for w2 in words[i+1:]:
                root_pairs.append((w1, w2))
        
        total_pairs += len(root_pairs)
        
        # Check each pair
        trivial_count = 0
        for w1, w2 in root_pairs:
            if looks_like_trivial_affix(root_id, w1, w2):
                trivial_pairs += 1
                trivial_count += 1
        
        # Check for suspicious patterns
        root_clean = root_id.lower().replace('(', '').replace(')', '')
        if len(root_clean) <= 3:
            short_root_pairs += len(root_pairs)
        
        # Show sample pairs
        sample_pairs = random.sample(root_pairs, min(3, len(root_pairs)))
        gloss_str = f' ("{gloss}")' if gloss else ''
        print(f"  {root_id}{gloss_str} (sources: {sources}):")
        
        for w1, w2 in sample_pairs:
            trivial_flag = "⚠️ " if looks_like_trivial_affix(root_id, w1, w2) else ""
            print(f"    {trivial_flag}{w1} + {w2}")
        
        if trivial_count > 0:
            print(f"    ({trivial_count}/{len(root_pairs)} pairs are trivial)")
        print()
    
    # Calculate metrics
    metrics = {
        'total_roots': len(roots),
        'multi_word_roots': len(root_items),
        'sampled_roots': len(sample_roots),
        'total_pairs': total_pairs,
        'trivial_pairs': trivial_pairs,
        'trivial_percentage': (trivial_pairs / total_pairs * 100) if total_pairs > 0 else 0,
        'short_root_pairs': short_root_pairs,
        'short_root_percentage': (short_root_pairs / total_pairs * 100) if total_pairs > 0 else 0,
    }
    
    # Report results
    print("📊 AUDIT RESULTS:")
    print(f"  Total roots: {metrics['total_roots']:,}")
    print(f"  Roots with multiple words: {metrics['multi_word_roots']:,}")
    print(f"  Sample size: {metrics['sampled_roots']}")
    print(f"  Total pairs analyzed: {metrics['total_pairs']:,}")
    print(f"  Trivial morphological pairs: {metrics['trivial_pairs']} ({metrics['trivial_percentage']:.1f}%)")
    print(f"  Short root pairs (≤3 chars): {metrics['short_root_pairs']} ({metrics['short_root_percentage']:.1f}%)")
    
    # Quality assessment
    if metrics['trivial_percentage'] > 15:
        print("❌ HIGH trivial pair rate - consider tightening filters")
    elif metrics['trivial_percentage'] > 10:
        print("⚠️  MODERATE trivial pair rate - acceptable but could improve")
    else:
        print("✅ LOW trivial pair rate - good quality")
    
    return metrics


def compare_with_oracle(roots_file: str, oracle_file: str = "data/regression_oracle.txt"):
    """
    Compare new roots with regression oracle to see what changed.
    """
    logger.info(f"🔄 Comparing new roots with oracle: {oracle_file}")
    
    oracle_path = Path(oracle_file)
    if not oracle_path.exists():
        logger.warning(f"Oracle file not found: {oracle_file}")
        return
    
    # Load oracle pairs
    oracle_pairs = set()
    with open(oracle_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            # Parse "word1 + word2 -> root" format
            parts = line.strip().split(' -> ')
            if len(parts) == 2:
                words_part = parts[0]
                if ' + ' in words_part:
                    w1, w2 = words_part.split(' + ', 1)
                    oracle_pairs.add((w1.strip(), w2.strip()))
    
    logger.info(f"Loaded {len(oracle_pairs)} oracle pairs")
    
    # Load new roots and generate pairs
    try:
        with gzip.open(roots_file, 'rt', encoding='utf-8') as f:
            roots = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load new roots: {e}")
        return
    
    new_pairs = set()
    for root_data in roots.values():
        if isinstance(root_data, dict):
            words = root_data.get('words', [])
        else:
            words = root_data
        
        for i, w1 in enumerate(words):
            for w2 in words[i+1:]:
                new_pairs.add((w1, w2))
                new_pairs.add((w2, w1))  # Both orientations
    
    logger.info(f"Generated {len(new_pairs) // 2} new pairs")
    
    # Compare
    oracle_normalized = set()
    for w1, w2 in oracle_pairs:
        oracle_normalized.add((w1, w2))
        oracle_normalized.add((w2, w1))
    
    preserved = oracle_normalized.intersection(new_pairs)
    lost = oracle_normalized - new_pairs
    
    print(f"\n🔄 ORACLE COMPARISON:")
    print(f"  Oracle pairs: {len(oracle_pairs):,}")
    print(f"  New pairs: {len(new_pairs) // 2:,}")
    print(f"  Preserved: {len(preserved) // 2:,} ({len(preserved) / len(oracle_normalized) * 100:.1f}%)")
    print(f"  Lost: {len(lost) // 2:,}")
    
    if len(lost) > 0:
        print(f"\n❌ Sample lost pairs:")
        lost_sample = list(lost)[:20:2]  # Every other to avoid duplicates
        for w1, w2 in lost_sample[:10]:
            print(f"    {w1} + {w2}")


def main():
    """Main entry point for the audit script."""
    parser = argparse.ArgumentParser(description='Audit etymology roots quality')
    parser.add_argument('--roots', '-r', default='data/roots.json.gz',
                      help='Path to roots file to audit')
    parser.add_argument('--sample-size', '-s', type=int, default=100,
                      help='Number of roots to sample for analysis')
    parser.add_argument('--compare-oracle', '-c', action='store_true',
                      help='Compare with regression oracle')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Run audit
        metrics = audit_roots(args.roots, args.sample_size)
        
        # Compare with oracle if requested
        if args.compare_oracle:
            compare_with_oracle(args.roots)
        
        # Exit with error code if quality is poor
        if metrics.get('trivial_percentage', 0) > 15:
            logger.error("Quality check failed - too many trivial pairs")
            return 1
        
        logger.info("✅ Audit completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 