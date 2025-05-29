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
            '"{word1}" and "{word2}" both trace to "{root}." {reflection}',
            
            # Question Hook style
            'Ever wondered why "{word1}" and "{word2}" share the root "{root}"? {insight}',
            
            # Mini Anecdote style
            'In ancient times, "{root}" gave birth to both "{word1}" and "{word2}." {contrast}',
            
            # Fragment & Aside style
            '{word1} & {word2}—both from "{root}." {metaphor}',
            
            # One-Liner Aphorism style
            '{word1}/{word2}: "{root}" splits into {description}.',
            
            # Simple declarative
            '"{word1}" and "{word2}" share the ancient root "{root}."',
            
            # Poetic form
            'From "{root}" spring both "{word1}" and "{word2}"—{observation}.',
            
            # Discovery form
            'Etymology reveals: "{word1}" + "{word2}" = "{root}" lineage.',
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
    
    def generate_tweet(self, word1: str, word2: str, root: str) -> str:
        """Generate a tweet for the given word pair and root.

        Priority: OpenAI generation (if enabled) → template fallback."""

        if self.use_ai:
            tweet_ai = self._generate_tweet_ai(word1, word2, root)
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
            'description': f"{word1.split()[0]} vs {word2.split()[0]}"
        }
        
        try:
            tweet = template.format(**variables)
            
            # Ensure tweet is within Twitter's character limit
            if len(tweet) > 280:
                # Fall back to simpler template
                simple_template = '"{word1}" and "{word2}" share the ancient root "{root}."'
                tweet = simple_template.format(word1=word1, word2=word2, root=root)
            
            return tweet
            
        except KeyError as e:
            logger.warning(f"Template formatting error: {e}, using fallback")
            # Fallback template
            return f'"{word1}" and "{word2}" share the ancient root "{root}."'
    
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
    def _generate_tweet_ai(self, word1: str, word2: str, root: str) -> Optional[str]:
        """Call OpenAI to craft a tweet following the specified template.

        Returns None on failure so caller can fallback to template."""

        if not self.use_ai:
            return None

        try:
            prompt = (
                "Compose a single tweet no longer than 280 characters that follows this template:\n\n"
                f"{word1} · {word2} — *{root}* (\"<root-gloss>\"). <One-sentence narrative showing how the two words diverged, including a vivid, concrete image>. <One-sentence reflection or question that invites the reader to ponder language or life.>\n\n"
                "Instructions\n"
                "1. Replace <root-gloss> with a terse English gloss for the root.\n"
                "2. Use lively but accessible diction—no emojis, no hashtags, no academic jargon.\n"
                "3. Keep everything under 280 characters total.\n"
                "4. Prefer strong verbs and sensory nouns; avoid unnecessary adverbs.\n"
                "5. Do not repeat any pair posted previously (the calling code enforces this, but refrain anyway)."
            )

            messages = [
                {"role": "system", "content": "You are a creative etymology tweeting assistant."},
                {"role": "user", "content": prompt},
            ]

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=128,
            )

            content = response.choices[0].message.content.strip()

            # Final sanity check
            if len(content) > 280:
                content = content[:279]

            return content

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}. Falling back to templates.")
            return None


class PairSelector:
    """Handles word pair selection and posted history."""
    
    def __init__(self, roots_file: str, posted_file: str):
        self.roots_file = roots_file
        self.posted_file = posted_file
        self.roots_data = self._load_roots()
        self.posted_pairs = self._load_posted()
    
    def _load_roots(self) -> Dict[str, List[str]]:
        """Load root mappings from compressed JSON."""
        roots_path = Path(self.roots_file)
        if not roots_path.exists():
            logger.error(f"Roots file not found: {self.roots_file}")
            return {}
        
        try:
            with gzip.open(roots_path, 'rt', encoding='utf-8') as f:
                roots = json.load(f)
            logger.info(f"Loaded {len(roots)} roots with {sum(len(words) for words in roots.values())} word relationships")
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
    
    def select_fresh_pair(self) -> Optional[Tuple[str, str, str]]:
        """Select a fresh word pair that hasn't been posted."""
        if not self.roots_data:
            logger.error("No root data available for pair selection")
            return None
        
        # Build list of all possible pairs
        candidates = []
        for root, words in self.roots_data.items():
            if len(words) < 2:
                continue
            
            # Generate all combinations of word pairs for this root
            for i in range(len(words)):
                for j in range(i + 1, len(words)):
                    word1, word2 = words[i], words[j]
                    pair = (word1, word2)
                    
                    # Check if pair hasn't been posted
                    if pair not in self.posted_pairs:
                        candidates.append((root, word1, word2))
        
        if not candidates:
            logger.warning("No fresh pairs available - all combinations have been posted")
            return None
        
        # Randomly select from candidates
        root, word1, word2 = random.choice(candidates)
        logger.info(f"Selected fresh pair: '{word1}' + '{word2}' (root: '{root}')")
        
        return root, word1, word2
    
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
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Initialize components
        selector = PairSelector(args.roots, args.posted)
        poster = TwitterPoster(dry_run=args.dry_run)
        
        # Select a fresh pair
        pair_result = selector.select_fresh_pair()
        if not pair_result:
            logger.warning("No fresh pairs available for posting")
            sys.exit(0)
        
        root, word1, word2 = pair_result
        
        # Generate tweet
        tweet_text = poster.generate_tweet(word1, word2, root)
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