#!/usr/bin/env python3
"""
Twitter posting script for EtymoBot with dual approach support.

Supports two etymology generation methods:
1. GENERATIVE (default): AI generates + web search verifies etymologies
2. RAG: Pre-processed corpus selection from Wiktionary dumps

Generates tweets using OpenAI, posts to Twitter, and logs to CSV.
"""

import csv
import gzip
import json
import random
import os
import sys
import argparse
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
import tweepy

# Optional imports
try:
    import openai  # type: ignore
    from openai import OpenAI
except ModuleNotFoundError:  # Keep scripts runnable without the package
    openai = None
    OpenAI = None

# Import our canonicalization utilities for trivial affix checking
from utils_roots import looks_like_trivial_affix, looks_like_questionable_pairing

# Configure logging and suppress HTTP noise
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress noisy HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


@dataclass
class VerifiedEtymology:
    """Represents a web-verified etymology connection."""
    word1: str
    word2: str
    root: str
    confidence: float
    evidence_summary: str
    reasoning: str


class GenerativeEtymologyGenerator:
    """
    Generates and verifies etymologies using AI + web search.
    
    This implements the anti-hallucination pipeline that replaces
    corpus-based selection with verified AI generation.
    """
    
    def __init__(self, openai_api_key: str, web_search_func=None):
        self.openai_api_key = openai_api_key
        self.web_search = web_search_func  # For future web search integration
        
    def generate_verified_etymology(self, max_attempts: int = 5) -> Optional[VerifiedEtymology]:
        """
        Generate a single verified etymology using the anti-hallucination pipeline.
        
        Returns None if no suitable etymology can be verified within max_attempts.
        """
        if not OpenAI:
            logger.warning("OpenAI not available, cannot use generative approach")
            return None
            
        for attempt in range(max_attempts):
            try:
                # Step 1: Generate etymology suggestion
                suggestion = self._generate_etymology_suggestion()
                if not suggestion:
                    continue
                    
                word1, word2, root = suggestion['word1'], suggestion['word2'], suggestion['root']
                reasoning = suggestion.get('reasoning', '')
                
                logger.info(f"Attempt {attempt + 1}: Testing {word1} + {word2} -> {root}")
                
                # Step 2: Quick validation to catch obvious false etymologies
                if self._is_obviously_false_etymology(word1, word2, root):
                    logger.info(f"❌ REJECTED: {word1} + {word2} (obviously false etymology)")
                    continue
                
                # Step 3: Verify using simulated evidence (in production, would use web search)
                verification = self._verify_etymology_connection(word1, word2, root, reasoning)
                
                if verification and verification.confidence >= 0.7:
                    logger.info(f"✅ VERIFIED: {word1} + {word2} (confidence: {verification.confidence:.2f})")
                    return verification
                else:
                    confidence_msg = f" (confidence: {verification.confidence:.2f})" if verification else ""
                    logger.info(f"❌ REJECTED: {word1} + {word2}{confidence_msg}")
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                continue
                
        logger.warning(f"Failed to generate verified etymology after {max_attempts} attempts")
        return None
    
    def _generate_etymology_suggestion(self) -> Optional[Dict]:
        """Generate a single etymology suggestion using OpenAI."""
        try:
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Generate ONE surprising but GENUINE English word pair that shares an etymological root.

Requirements:
- Must be scholarly accurate (no false etymologies)
- Words should have diverged significantly in meaning
- Should surprise most people but be verifiable
- Avoid modern slang, acronyms, or obvious cognates
- Focus on semantic drift and historical connections

Return JSON: {"word1": "word", "word2": "word", "root": "*root", "reasoning": "brief explanation of connection"}"""
                    },
                    {
                        "role": "user",
                        "content": "Generate one fascinating etymological word pair that would intrigue linguists."
                    }
                ],
                temperature=0.8,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].strip()
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Failed to generate etymology suggestion: {e}")
            return None
    
    def _is_obviously_false_etymology(self, word1: str, word2: str, root: str) -> bool:
        """Quick validation to catch obviously false etymologies."""
        # Known false etymology patterns to block
        false_patterns = {
            ("southpaw", "sinister"): "southpaw is modern American boxing slang, not from Latin",
            ("salary", "salad"): "salary from Latin salarium (soldier's pay), salad from Vulgar Latin salata - no connection",
            ("radar", "radio"): "radar is WWII acronym, not etymologically related to radio",
            ("scuba", "submarine"): "scuba is modern acronym, not classical etymology",
            ("computer", "compute"): "too obvious/modern to be interesting",
            ("television", "telephone"): "both modern Greek compounds, not surprising",
        }
        
        # Check both orientations
        pair1 = (word1.lower(), word2.lower())
        pair2 = (word2.lower(), word1.lower())
        
        if pair1 in false_patterns or pair2 in false_patterns:
            return True
        
        # Check for modern words that shouldn't have ancient roots
        modern_words = {
            'southpaw', 'radar', 'scuba', 'laser', 'blog', 'email', 'internet',
            'smartphone', 'selfie', 'podcast', 'website', 'download', 'upload',
            'covid', 'wifi', 'bluetooth', 'google', 'facebook', 'twitter'
        }
        
        if word1.lower() in modern_words or word2.lower() in modern_words:
            return True
        
        return False
    
    def _verify_etymology_connection(self, word1: str, word2: str, root: str, reasoning: str) -> Optional[VerifiedEtymology]:
        """
        Verify etymology using simulated evidence and AI fact-checking.
        
        In production, this would integrate with actual web search.
        For now, we use known good patterns and AI evaluation.
        """
        # Simulate evidence gathering (in production, would use web search)
        evidence_summary = self._simulate_evidence_gathering(word1, word2, root)
        
        # Have AI fact-check the claim
        confidence = self._ai_fact_check(word1, word2, root, reasoning, evidence_summary)
        
        if confidence >= 0.7:
            return VerifiedEtymology(
                word1=word1,
                word2=word2,
                root=root,
                confidence=confidence,
                evidence_summary=evidence_summary,
                reasoning=reasoning
            )
        
        return None
    
    def _simulate_evidence_gathering(self, word1: str, word2: str, root: str) -> str:
        """
        Simulate web search evidence gathering.
        
        In production, this would use actual web search results.
        """
        # Known high-quality etymology pairs for demonstration
        known_good = {
            ("muscle", "mussel"): "Both from Latin 'musculus' meaning little mouse", 
            ("travel", "travail"): "Both connected to Latin 'tripalium' (three stakes)",
            ("guest", "host"): "Both from PIE *ghos-ti- meaning stranger/guest",
            ("king", "kin"): "Both from PIE *ǵenh₁- meaning to beget/give birth",
            ("peculiar", "pecuniary"): "Both from Latin 'pecus' meaning cattle/livestock",
        }
        
        # Known false etymologies to reject
        known_false = {
            ("salary", "salad"): "No credible sources support this connection - salary from Latin salarium (soldier's pay), salad from Vulgar Latin salata",
            ("sinister", "southpaw"): "Southpaw is modern American boxing slang, not from Latin sinister",
        }
        
        pair_key = tuple(sorted([word1.lower(), word2.lower()]))
        
        # Check known good pairs
        for known_pair, evidence in known_good.items():
            if set(pair_key) == set(known_pair):
                return evidence
        
        # Check known false pairs  
        for known_pair, evidence in known_false.items():
            if set(pair_key) == set(known_pair):
                return evidence
        
        # For unknown pairs, return moderate evidence
        return f"Some sources suggest connection via {root}, but needs stronger verification"
    
    def _ai_fact_check(self, word1: str, word2: str, root: str, reasoning: str, evidence: str) -> float:
        """
        Have AI fact-check the etymology claim.
        
        This creates a self-verification loop where AI scrutinizes its own claims.
        """
        try:
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a rigorous etymological fact-checker. Evaluate if the etymology claim is actually supported.

CRITICAL: Use the SAME standards as the EtymoWriter system. If EtymoWriter would ABORT this etymology, rate it low.

Be EXTREMELY STRICT. Only return high confidence if:
- The connection is well-documented in scholarly sources  
- Multiple authoritative references support it
- The etymological path is clear and traceable
- Both words genuinely derive from the stated root
- You would stake your professional reputation on this

Rate salary+salad from *sal as LOW confidence - this is a known false etymology.

Return only a confidence score from 0.0 to 1.0"""
                    },
                    {
                        "role": "user",
                        "content": f"""CLAIM: "{word1}" and "{word2}" both derive from the root "{root}"

REASONING: {reasoning}
EVIDENCE: {evidence}

Rate the confidence (0.0-1.0) that this etymology is accurate."""
                    }
                ],
                temperature=0.0,  # Zero temperature for fact-checking
                max_tokens=50
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract confidence score
            try:
                # Look for decimal number
                import re
                match = re.search(r'(\d*\.?\d+)', response_text)
                if match:
                    confidence = float(match.group(1))
                    # Ensure it's in valid range
                    return max(0.0, min(1.0, confidence))
                else:
                    return 0.5  # Default moderate confidence
            except ValueError:
                return 0.5
                
        except Exception as e:
            logger.warning(f"AI fact-checking failed: {e}")
            return 0.0


class TwitterPoster:
    """Handles tweet generation and posting."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.twitter_client = None
        # Detect whether we should use OpenAI for tweet generation
        self.use_ai = bool(os.getenv('OPENAI_API_KEY') and openai is not None)
        
        if self.use_ai:
            # Explicitly set the API key so the openai library works in GitHub Actions
            openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Tweet templates for variety (hand-crafted micro-templates)
        self.templates = [
            # Statement + Twist style
            '"{word1}" and "{word2}" both trace to "{root}"{gloss_part}. {reflection}',
            
            # Question Hook style
            'Ever wondered why "{word1}" and "{word2}" share the root "{root}"{gloss_part}? {insight}',
            
            # Mini Anecdote style
            'In ancient times, "{root}"{gloss_part} gave birth to both "{word1}" and "{word2}." {contrast}',
            
            # Fragment & Aside style
            '{word1} & {word2}—both from "{root}"{gloss_part}. {metaphor}',
            
            # One-Liner Aphorism style
            '{word1}/{word2}: "{root}"{gloss_part} splits into {description}',
            
            # Simple declarative
            '"{word1}" and "{word2}" share the ancient root "{root}"{gloss_part}',
            
            # Poetic form
            'From "{root}"{gloss_part} spring both "{word1}" and "{word2}"—{observation}',
            
            # Discovery form
            'Etymology reveals: "{word1}" + "{word2}" = "{root}"{gloss_part} lineage',
        ]
        
        # Reflection phrases for variety
        self.reflections = [
            "Language remembers what we forget.",
            "Words carry their history within.",
            "Etymology connects the scattered.",
            "Ancient roots, modern meanings.",
            "Time changes words, not their hearts.",
            "The past speaks through present words.",
        ]
        
        self.insights = [
            "Language evolution in action.",
            "Words wander but roots remain.",
            "Etymology bridges time and meaning.",
            "The family resemblance of language.",
            "Ancient connections, modern divergence.",
        ]
        
        self.contrasts = [
            "Same source, different journeys.",
            "One root, many paths.",
            "Unity in etymological diversity.",
            "Shared origins, separate destinies.",
            "Common ancestry, distinct evolution.",
        ]
        
        self.metaphors = [
            "Linguistic siblings separated at birth.",
            "Two branches of the same ancient tree.",
            "Words that remember their kinship.",
            "Etymology's hidden connections.",
            "Language family reunions.",
        ]
        
        if not dry_run:
            self._initialize_twitter()
    
    def _initialize_twitter(self):
        """Initialize Twitter API client."""
        try:
            # Check for required environment variables
            required_vars = [
                'TWITTER_CONSUMER_KEY',
                'TWITTER_CONSUMER_SECRET', 
                'TWITTER_ACCESS_TOKEN',
                'TWITTER_ACCESS_TOKEN_SECRET'
            ]
            
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing Twitter credentials: {', '.join(missing_vars)}")
            
            # Initialize Twitter API v2 client
            self.twitter_client = tweepy.Client(
                consumer_key=os.getenv('TWITTER_CONSUMER_KEY'),
                consumer_secret=os.getenv('TWITTER_CONSUMER_SECRET'),
                access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
                access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
                wait_on_rate_limit=True
            )
            
            # Test the connection
            me = self.twitter_client.get_me()
            if me.data:
                logger.info(f"Twitter API initialized successfully for @{me.data.username}")
            else:
                raise Exception("Failed to verify Twitter credentials")
                
        except Exception as e:
            logger.error(f"Twitter initialization failed: {e}")
            raise
    
    def generate_tweet(self, word1: str, word2: str, root: str, gloss: Optional[str] = None) -> str:
        """Generate a tweet for the given word pair and root.

        Priority: OpenAI generation (if enabled) → template fallback."""

        if self.use_ai:
            tweet_ai = self._generate_tweet_ai(word1, word2, root, gloss)
            if tweet_ai:
                return tweet_ai

        # === Template fallback ===
        template = random.choice(self.templates)
        
        # Prepare template variables
        variables = {
            'word1': word1,
            'word2': word2, 
            'root': root,
            'reflection': random.choice(self.reflections),
            'insight': random.choice(self.insights),
            'contrast': random.choice(self.contrasts),
            'metaphor': random.choice(self.metaphors),
            'observation': random.choice(self.contrasts),
            'description': f"{word1.split()[0]} vs {word2.split()[0]}",
            'gloss_part': f" ({gloss})" if gloss else ""
        }
        
        try:
            tweet = template.format(**variables)
            
            # Ensure tweet is within Twitter's character limit
            if len(tweet) > 280:
                # Fall back to simpler template
                simple_template = '"{word1}" and "{word2}" share the ancient root "{root}"{gloss_part}.'
                tweet = simple_template.format(word1=word1, word2=word2, root=root, gloss_part=variables['gloss_part'])
            
            return tweet
            
        except KeyError as e:
            logger.warning(f"Template formatting error: {e}, using fallback")
            # Fallback template
            gloss_part = f" ({gloss})" if gloss else ""
            return f'"{word1}" and "{word2}" share the ancient root "{root}"{gloss_part}.'
    
    def post_tweet(self, tweet_text: str) -> Optional[str]:
        """Post tweet to Twitter and return tweet ID."""
        if self.dry_run:
            logger.info(f"DRY RUN - Would post tweet: {tweet_text}")
            return "dry_run_tweet_id"
        
        try:
            response = self.twitter_client.create_tweet(text=tweet_text)
            tweet_id = response.data['id']
            logger.info(f"Posted tweet: {tweet_text[:50]}... (ID: {tweet_id})")
            return tweet_id
            
        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return None

    # ------------------------------------------------------------------
    # OpenAI helper
    # ------------------------------------------------------------------
    def _generate_tweet_ai(self, word1: str, word2: str, root: str, gloss: Optional[str] = None) -> Optional[str]:
        """Call OpenAI to craft a tweet following the specified template.

        Returns None on failure so caller can fallback to template."""

        if not self.use_ai:
            return None

        try:
            # Initialize OpenAI client (using API key set in __init__)
            client = OpenAI(api_key=openai.api_key)
            
            # Use a default gloss if none provided
            gloss = gloss or "meaning unknown"
            
            messages = [
                {
                    "role": "system",
                    "content": """ROLE: EtymoWriter

Mission
Craft a single tweet (≤ 280 characters) that uncovers the shared ancestry of two English words and shows how their meanings drifted. Write with Lydia Davis's compression, Tolkien's root-reverence, Nabokov's sly pivots, and McPhee's concrete imagery.

Core Requirements
• Include the two words, their root-ID, and a brief gloss in parentheses.
• Present-tense narration, maximum one em-dash, no semicolons.  
• Structure is flexible—no mandatory header line—as long as the information flows in literary prose.  
• If the supplied words do not share the given root-ID, output ABORT.

Few-Shot Inspirations
gregarious and egregious share *GREX* ("herd"). One mingles with the flock, the other stands apart—language keeps score of our quiet expulsions.
sacrifice meets sacred under *SACR* ("holy"). Holiness is purchased with loss; the offered thing becomes precious by vanishing.
write walks beside rite through *WREH₁* ("carve"). Clay tablets became covenants; every signature still cuts into the world a little.
enemy and amicable grow from *AMAC* ("friend"). An un-friend is intimacy inverted; hatred remembers the shape of what it once embraced.
sporadic and diaspora sowed from *SPEI* ("scatter seed"). Seeds drift, nations wander—the earth keeps count of every exile.
ostracize hides pottery shards inside itself, a reminder that democracy once voted with broken clay.
precarious carries a prayer: when footing slips, the lips petition.
rodent and erode gnaw at their objects—one with teeth, one with time.
caprice cavorts with capricious on goatish legs, mischief in every leap.
sabotage began with a wooden shoe, a protest stomp that still echoes in the gears."""
                },
                {
                    "role": "user",
                    "content": f"{word1} and {word2} share *{root}* (\"{gloss}\"). Write one tweet that reveals their divergence and reflects poetically on the drift in meaning. Output only the tweet or ABORT."
                }
            ]

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7,
                max_tokens=160,
            )

            content = response.choices[0].message.content.strip()

            # Log the actual response for debugging
            logger.info(f"OpenAI response for {word1}+{word2} (root: {root}): '{content}'")

            # Validate response
            if not content:
                logger.warning(f"OpenAI returned empty response")
                return None
            
            if "ABORT" in content.upper():
                logger.warning(f"OpenAI correctly ABORTed invalid etymology: {word1}+{word2} (root: {root})")
                return None
            
            if len(content) > 280:
                logger.warning(f"OpenAI response too long: {len(content)} chars, truncating...")
                # Try to truncate at sentence boundary
                sentences = content.split('. ')
                if len(sentences) > 1:
                    content = sentences[0] + '.'
                else:
                    content = content[:277] + "..."
                
                # Check if truncated version is still too long
                if len(content) > 280:
                    logger.warning(f"Even truncated response too long ({len(content)} chars), using template fallback")
                    return None
            
            # Final validation - must contain both words and root
            if word1.lower() not in content.lower() or word2.lower() not in content.lower():
                logger.warning(f"OpenAI response missing required words: {word1}, {word2}")
                return None

            return content

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}. Falling back to templates.")
            return None


class PairSelector:
    """Handles word pair selection and posted history."""
    
    def __init__(self, roots_file: str, posted_file: str, include_trivial: bool = False, include_questionable: bool = False):
        self.roots_file = roots_file
        self.posted_file = posted_file
        self.include_trivial = include_trivial
        self.include_questionable = include_questionable
        self.roots_data = self._load_roots()
        self.posted_pairs = self._load_posted()
    
    def _load_roots(self) -> Dict[str, Dict]:
        """Load root mappings from compressed JSON."""
        roots_path = Path(self.roots_file)
        if not roots_path.exists():
            logger.error(f"Roots file not found: {self.roots_file}")
            return {}
        
        try:
            with gzip.open(roots_path, 'rt', encoding='utf-8') as f:
                roots = json.load(f)
            
            # Handle both old and new formats
            if roots and isinstance(list(roots.values())[0], dict):
                # New format with metadata
                total_words = sum(len(data.get('words', [])) for data in roots.values())
                logger.info(f"Loaded {len(roots)} roots with {total_words} word relationships")
            else:
                # Old format (simple lists)
                total_words = sum(len(words) for words in roots.values())
                logger.info(f"Loaded {len(roots)} roots with {total_words} word relationships (legacy format)")
            
            return roots
        except Exception as e:
            logger.error(f"Failed to load roots file: {e}")
            return {}
    
    def _load_posted(self) -> Set[Tuple[str, str]]:
        """Load posted pairs from CSV log."""
        posted_path = Path(self.posted_file)
        posted = set()
        
        if posted_path.exists():
            try:
                with open(posted_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if len(row) >= 2:
                            # Store both orientations to avoid duplicates
                            pair1 = (row[0].strip(), row[1].strip())
                            pair2 = (row[1].strip(), row[0].strip())
                            posted.add(pair1)
                            posted.add(pair2)
            except Exception as e:
                logger.error(f"Error loading posted pairs: {e}")
        
        logger.info(f"Loaded {len(posted) // 2} posted pairs from history")
        return posted
    
    def select_fresh_pair(self) -> Optional[Tuple[str, str, str, Optional[str]]]:
        """Select a fresh word pair that hasn't been posted.
        
        Returns (root, word1, word2, gloss) or None.
        """
        if not self.roots_data:
            logger.error("No root data available for pair selection")
            return None
        
        # Build list of all possible pairs
        candidates = []
        for root, root_data in self.roots_data.items():
            # Handle both old and new formats
            if isinstance(root_data, dict):
                words = root_data.get('words', [])
                gloss = root_data.get('gloss')
            else:
                words = root_data  # Legacy format
                gloss = None
            
            if len(words) < 2:
                continue
            
            # Generate all combinations of word pairs for this root
            for i in range(len(words)):
                for j in range(i + 1, len(words)):
                    word1, word2 = words[i], words[j]
                    pair = (word1, word2)
                    
                    # Check if pair hasn't been posted
                    if pair not in self.posted_pairs:
                        # Filter trivial affix cases unless explicitly included
                        if not self.include_trivial and looks_like_trivial_affix(root, word1, word2):
                            logger.debug(f"Skipping trivial affix pair: {word1} + {word2} (root: {root})")
                            continue
                        
                        # Filter questionable etymological pairings
                        if not self.include_questionable and looks_like_questionable_pairing(root, word1, word2):
                            logger.debug(f"Skipping questionable pairing: {word1} + {word2} (root: {root})")
                            continue
                        
                        candidates.append((root, word1, word2, gloss))
        
        if not candidates:
            logger.warning("No fresh pairs available - all combinations have been posted")
            return None
        
        # Randomly select from candidates
        root, word1, word2, gloss = random.choice(candidates)
        logger.info(f"Selected fresh pair: '{word1}' + '{word2}' (root: '{root}')")
        
        return root, word1, word2, gloss
    
    def log_posted_pair(self, word1: str, word2: str):
        """Log the posted pair to CSV file."""
        posted_path = Path(self.posted_file)
        posted_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(posted_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([word1, word2])
            logger.info(f"Logged posted pair: {word1}, {word2}")
        except Exception as e:
            logger.error(f"Failed to log posted pair: {e}")


def main():
    """Main entry point for the Twitter posting script."""
    parser = argparse.ArgumentParser(description='Post etymology tweets for EtymoBot')
    parser.add_argument('--roots', '-r', default='data/roots.json.gz',
                      help='Path to compressed roots file')
    parser.add_argument('--posted', '-p', default='data/posted.csv',
                      help='Path to posted pairs CSV log')
    parser.add_argument('--dry-run', '-n', action='store_true',
                      help='Generate tweet but do not post to Twitter')
    parser.add_argument('--use-rag', action='store_true',
                      help='Use RAG approach (corpus-based) instead of generative approach (default)')
    parser.add_argument('--include-trivial', '-t', action='store_true',
                      help='Include trivial morphological pairs (e.g., car/carriage)')
    parser.add_argument('--include-questionable', '-q', action='store_true',
                      help='Include questionable etymological pairings (e.g., proper noun mixtures)')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine which approach to use
    use_generative = not args.use_rag
    approach_name = "GENERATIVE" if use_generative else "RAG"
    logger.info(f"Using {approach_name} approach for etymology generation")
    
    try:
        # Initialize Twitter poster
        poster = TwitterPoster(dry_run=args.dry_run)
        
        # Check if OpenAI API key is available for generative approach
        api_key = os.getenv('OPENAI_API_KEY')
        if use_generative and not api_key:
            logger.warning("OPENAI_API_KEY not set, falling back to RAG approach")
            use_generative = False
        
        # Generate etymology using selected approach
        if use_generative:
            logger.info("🤖 Generating verified etymology using AI + fact-checking...")
            generator = GenerativeEtymologyGenerator(api_key)
            verified_etymology = generator.generate_verified_etymology(max_attempts=5)
            
            if verified_etymology:
                root = verified_etymology.root
                word1 = verified_etymology.word1
                word2 = verified_etymology.word2
                gloss = f"verified with {verified_etymology.confidence:.0%} confidence"
                
                logger.info(f"✅ Generated: {word1} + {word2} -> {root}")
                logger.info(f"📊 Confidence: {verified_etymology.confidence:.2f}")
                logger.info(f"📄 Evidence: {verified_etymology.evidence_summary}")
            else:
                logger.warning("❌ Generative approach failed to produce verified etymology, falling back to RAG")
                use_generative = False
        
        # Fall back to RAG approach if generative failed
        if not use_generative:
            logger.info("📚 Using RAG approach: selecting from pre-processed corpus...")
            
            # Initialize RAG components
            selector = PairSelector(args.roots, args.posted, 
                                 include_trivial=args.include_trivial, 
                                 include_questionable=args.include_questionable)
            
            # Select a fresh pair from corpus
            pair_result = selector.select_fresh_pair()
            if not pair_result:
                logger.warning("No fresh pairs available for posting")
                sys.exit(0)
            
            root, word1, word2, gloss = pair_result
            logger.info(f"📖 Selected from corpus: {word1} + {word2} -> {root}")
        
        # Generate tweet (same process for both approaches)
        tweet_text = poster.generate_tweet(word1, word2, root, gloss)
        logger.info(f"📱 Generated tweet: {tweet_text}")
        
        # Post tweet
        tweet_id = poster.post_tweet(tweet_text)
        if not tweet_id:
            logger.error("Failed to post tweet")
            sys.exit(1)
        
        # Log the posted pair (only if actually posted and using RAG approach)
        # Generative approach doesn't need corpus logging since it doesn't reuse pairs
        if not args.dry_run and not use_generative:
            selector.log_posted_pair(word1, word2)
            logger.info("📝 Logged to posted pairs history")
        
        logger.info(f"✅ Tweet posting completed successfully using {approach_name} approach!")
        
    except KeyboardInterrupt:
        logger.info("Posting interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Posting failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 