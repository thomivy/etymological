#!/usr/bin/env python3
"""
Twitter posting script for EtymoBot GitHub-native pipeline.

Loads root mappings from compressed JSON, selects fresh word pairs,
generates tweets using templates, posts to Twitter, and logs to CSV.

This replaces the complex bot orchestration with a simple, stateless script.
"""

import csv
import gzip
import json
import random
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
import tweepy

# Optional OpenAI import (only if API key provided)
try:
    import openai  # type: ignore
except ModuleNotFoundError:  # Keep scripts runnable without the package
    openai = None

# Import our canonicalization utilities for trivial affix checking
from utils_roots import looks_like_trivial_affix, looks_like_questionable_pairing

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
            '{word1}/{word2}: "{root}"{gloss_part} splits into {description}.',
            
            # Simple declarative
            '"{word1}" and "{word2}" share the ancient root "{root}"{gloss_part}.',
            
            # Poetic form
            'From "{root}"{gloss_part} spring both "{word1}" and "{word2}"—{observation}.',
            
            # Discovery form
            'Etymology reveals: "{word1}" + "{word2}" = "{root}"{gloss_part} lineage.',
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
            from openai import OpenAI
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
    parser.add_argument('--include-trivial', '-t', action='store_true',
                      help='Include trivial morphological pairs (e.g., car/carriage)')
    parser.add_argument('--include-questionable', '-q', action='store_true',
                      help='Include questionable etymological pairings (e.g., proper noun mixtures)')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize components
        selector = PairSelector(args.roots, args.posted, include_trivial=args.include_trivial, include_questionable=args.include_questionable)
        poster = TwitterPoster(dry_run=args.dry_run)
        
        # Select a fresh pair
        pair_result = selector.select_fresh_pair()
        if not pair_result:
            logger.warning("No fresh pairs available for posting")
            sys.exit(0)
        
        root, word1, word2, gloss = pair_result
        
        # Generate tweet
        tweet_text = poster.generate_tweet(word1, word2, root, gloss)
        logger.info(f"Generated tweet: {tweet_text}")
        
        # Post tweet
        tweet_id = poster.post_tweet(tweet_text)
        if not tweet_id:
            logger.error("Failed to post tweet")
            sys.exit(1)
        
        # Log the posted pair (only if actually posted)
        if not args.dry_run:
            selector.log_posted_pair(word1, word2)
        
        logger.info("Tweet posting completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Posting interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Posting failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 