#!/usr/bin/env python3
"""
Twitter posting script for EtymoBot - Pure Generative AI Approach.

Uses OpenAI to generate etymologies and web search to verify them.
No corpus or RAG - purely AI-driven with web verification.
"""

import csv
import json
import random
import os
import sys
import argparse
import logging
import time
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass
import tweepy

# Optional imports
try:
    import openai  # type: ignore
    from openai import OpenAI
except ModuleNotFoundError:
    openai = None
    OpenAI = None

# Configure logging and suppress HTTP noise
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress noisy HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)


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
    Pure generative etymology generator using AI + real web search verification.
    
    No corpus, no RAG - just AI creativity verified by web search.
    """
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        
    def generate_verified_etymology(self, max_attempts: int = 10) -> Optional[VerifiedEtymology]:
        """
        Generate a verified etymology using pure AI + web search pipeline.
        
        Returns None if no suitable etymology can be verified within max_attempts.
        """
        if not OpenAI:
            logger.error("OpenAI not available, cannot use generative approach")
            return None
            
        for attempt in range(max_attempts):
            try:
                # Step 1: AI generates etymology suggestion
                suggestion = self._generate_etymology_suggestion()
                if not suggestion:
                    continue
                    
                word1, word2, root = suggestion['word1'], suggestion['word2'], suggestion['root']
                reasoning = suggestion.get('reasoning', '')
                
                logger.info(f"Attempt {attempt + 1}: Testing {word1} + {word2} -> {root}")
                
                # Step 2: Web search verification
                verification = self._web_verify_etymology(word1, word2, root, reasoning)
                
                if verification and verification.confidence >= 0.85:
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
        """Generate etymology suggestion using AI with enhanced prompting."""
        try:
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert etymologist generating GENUINE, SURPRISING English word pairs that share etymological roots.

REQUIREMENTS:
- Must be factually accurate (will be web-verified)
- Should surprise educated readers
- Words must have diverged significantly in meaning
- Avoid obvious cognates or modern words
- Focus on semantic drift and historical evolution
- Choose words that most people wouldn't connect

EXAMPLES OF GOOD PAIRS:
- muscle/mussel (both from Latin musculus "little mouse")
- salary/salad (both from Latin sal "salt")
- travel/travail (both from Latin tripalium "three stakes")
- guest/host (both from PIE *ghos-ti- "stranger")

Return JSON format: {"word1": "word", "word2": "word", "root": "*root", "reasoning": "brief explanation"}"""
                    },
                    {
                        "role": "user",
                        "content": "Generate one fascinating, verifiable etymological word pair that would surprise linguistics enthusiasts."
                    }
                ],
                temperature=0.9,  # Higher creativity
                max_tokens=250
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].strip()
            
            suggestion = json.loads(content)
            
            # Validate required fields
            required_fields = ['word1', 'word2', 'root']
            if not all(field in suggestion for field in required_fields):
                logger.warning(f"Missing required fields in suggestion: {suggestion}")
                return None
                
            return suggestion
            
        except Exception as e:
            logger.error(f"Failed to generate etymology suggestion: {e}")
            return None
    
    def _web_verify_etymology(self, word1: str, word2: str, root: str, reasoning: str) -> Optional[VerifiedEtymology]:
        """
        Use web search to verify the etymology claim.
        """
        # Step 1: Gather web evidence
        evidence = self._search_web_evidence(word1, word2, root)
        
        # Step 2: AI analysis of evidence
        confidence = self._ai_analyze_evidence(word1, word2, root, reasoning, evidence)
        
        if confidence >= 0.85:
            return VerifiedEtymology(
                word1=word1,
                word2=word2,
                root=root,
                confidence=confidence,
                evidence_summary=evidence,
                reasoning=reasoning
            )
        
        return None
    
    def _search_web_evidence(self, word1: str, word2: str, root: str) -> str:
        """
        Search for web evidence about the etymology claim.
        """
        try:
            # Search for etymological information about both words
            queries = [
                f'"{word1}" etymology origin',
                f'"{word2}" etymology origin',
                f'"{word1}" "{word2}" etymology connection',
                f'{root} etymology root meaning'
            ]
            
            evidence_pieces = []
            
            for query in queries:
                try:
                    # Use DuckDuckGo Instant Answer API (no key required)
                    response = requests.get(
                        'https://api.duckduckgo.com/',
                        params={
                            'q': query,
                            'format': 'json',
                            'no_html': '1',
                            'skip_disambig': '1'
                        },
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract relevant information
                        abstract = data.get('Abstract', '')
                        definition = data.get('Definition', '')
                        
                        if abstract:
                            evidence_pieces.append(f"Search '{query}': {abstract[:200]}")
                        elif definition:
                            evidence_pieces.append(f"Search '{query}': {definition[:200]}")
                            
                except Exception as e:
                    logger.debug(f"Search failed for '{query}': {e}")
                    continue
                    
                # Rate limiting
                time.sleep(0.5)
            
            if evidence_pieces:
                return " | ".join(evidence_pieces)
            else:
                return f"Limited web evidence found for {word1}/{word2} etymology connection"
                
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
            return f"Web search unavailable - using AI reasoning only for {word1}/{word2}"
    
    def _ai_analyze_evidence(self, word1: str, word2: str, root: str, reasoning: str, evidence: str) -> float:
        """
        Have AI analyze the web evidence and reasoning to determine confidence.
        """
        try:
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a rigorous etymological fact-checker analyzing web evidence.

Rate the confidence (0.0-1.0) that the two words genuinely share the given etymological root.

CRITICAL: Be very strict about false etymologies. Many similar-sounding words have completely different origins.

STANDARDS:
- 0.9-1.0: Strong web evidence clearly confirms the shared root with detailed historical path
- 0.8-0.9: Good evidence supports connection with clear etymological reasoning  
- 0.6-0.8: Some evidence but missing key details or conflicting information
- 0.4-0.6: Weak evidence, unclear connection, or suspected false etymology
- 0.0-0.4: No evidence, contradictory evidence, or clearly false etymology

RED FLAGS (automatically score ≤0.4):
- Similar spelling but different language families
- One word clearly has different origin (e.g. Germanic vs Latin vs Greek)
- Suspicious word pairs that sound alike but lack etymological connection
- Missing clear historical development path from root to modern words

Consider BOTH:
1. Factual accuracy (do they really share this root? Are the historical paths clear?)
2. Evidence quality (does web evidence specifically support this connection?)

RESPOND with ONLY a decimal number 0.0-1.0."""
                    },
                    {
                        "role": "user",
                        "content": f"""CLAIM: "{word1}" and "{word2}" share etymological root "{root}"

REASONING: {reasoning}

WEB EVIDENCE: {evidence}

Rate confidence (0.0-1.0) based on evidence quality and factual accuracy."""
                    }
                ],
                temperature=0.0,  # Zero temperature for analysis
                max_tokens=10
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract confidence score
            try:
                import re
                match = re.search(r'(\d*\.?\d+)', response_text)
                if match:
                    confidence = float(match.group(1))
                    confidence = max(0.0, min(1.0, confidence))
                    logger.debug(f"AI evidence analysis for {word1}+{word2}: {confidence}")
                    return confidence
                else:
                    logger.warning(f"Could not parse confidence from: {response_text}")
                    return 0.3
            except ValueError:
                logger.warning(f"Failed to convert confidence to float: {response_text}")
                return 0.3
                
        except Exception as e:
            logger.warning(f"AI evidence analysis failed: {e}")
            return 0.0


class TwitterPoster:
    """Handles tweet generation and posting."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.twitter_client = None
        
        # Check for OpenAI availability
        self.use_ai = bool(os.getenv('OPENAI_API_KEY') and openai is not None)
        
        if self.use_ai:
            openai.api_key = os.getenv('OPENAI_API_KEY')
        
        if not dry_run:
            self._initialize_twitter()
    
    def _initialize_twitter(self):
        """Initialize Twitter API client."""
        try:
            required_vars = [
                'TWITTER_CONSUMER_KEY',
                'TWITTER_CONSUMER_SECRET', 
                'TWITTER_ACCESS_TOKEN',
                'TWITTER_ACCESS_TOKEN_SECRET'
            ]
            
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                raise ValueError(f"Missing Twitter credentials: {', '.join(missing_vars)}")
            
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
        """Generate a tweet using AI with enhanced literary style."""
        
        if not self.use_ai:
            # Simple fallback if AI not available
            return f'{word1} and {word2} share the ancient root {root}. Words wander but roots remain.'
        
        try:
            client = OpenAI(api_key=openai.api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """ROLE: EtymoWriter

Mission
Craft a single tweet (≤ 280 characters) that uncovers the shared ancestry of two English words and shows how their meanings drifted. Write with Lydia Davis's compression, Tolkien's root-reverence, Nabokov's sly pivots, and McPhee's concrete imagery.

Core Requirements
• Include the two words, their root, and show semantic divergence.
• Present-tense narration, maximum one em-dash, no semicolons.  
• Structure is flexible—no mandatory header line—as long as the information flows in literary prose.  
• Do NOT use asterisks around roots or quotes around the entire output.
• If the supplied words do not share the given root, output ABORT.

Few-Shot Inspirations
gregarious and egregious share GREX (herd). One mingles with the flock, the other stands apart—language keeps score of our quiet expulsions.
sacrifice meets sacred under SACR (holy). Holiness is purchased with loss; the offered thing becomes precious by vanishing.
write walks beside rite through WREH₁ (carve). Clay tablets became covenants; every signature still cuts into the world a little.
enemy and amicable grow from AMAC (friend). An un-friend is intimacy inverted; hatred remembers the shape of what it once embraced.
sporadic and diaspora sowed from SPEI (scatter seed). Seeds drift, nations wander—the earth keeps count of every exile.
ostracize hides pottery shards inside itself, a reminder that democracy once voted with broken clay.
precarious carries a prayer: when footing slips, the lips petition.
rodent and erode gnaw at their objects—one with teeth, one with time.
caprice cavorts with capricious on goatish legs, mischief in every leap.
sabotage began with a wooden shoe, a protest stomp that still echoes in the gears.
muscle and mussel both spring from musculus (little mouse). One flexes beneath skin, the other clings to rocks—both shaped like tiny rodents in hiding.
salary meets salad through sal (salt). Roman soldiers earned their salt; we season our greens with it—currency and cuisine, both preserved by ancient crystals.
guest and host emerge from ghos-ti- (stranger). The welcomed and the welcomer share roots—hospitality remembers when every visitor was an unknown."""
                    },
                    {
                        "role": "user",
                        "content": f"{word1} and {word2} share {root}. Write one tweet that reveals their divergence and reflects poetically on the drift in meaning. Show how the ancient root connects to both modern meanings."
                    }
                ],
                temperature=0.7,
                max_tokens=160
            )

            content = response.choices[0].message.content.strip()

            # Log the actual response for debugging
            logger.info(f"OpenAI response for {word1}+{word2} (root: {root}): '{content}'")

            # Validate response
            if not content:
                logger.warning(f"OpenAI returned empty response")
                return "ABORT"
            
            if "ABORT" in content.upper():
                logger.warning(f"OpenAI correctly ABORTed invalid etymology: {word1}+{word2} (root: {root})")
                return "ABORT"
            
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
                    return "ABORT"
            
            # Final validation - must contain both words and root
            if word1.lower() not in content.lower() or word2.lower() not in content.lower():
                logger.warning(f"OpenAI response missing required words: {word1}, {word2}")
                return "ABORT"

            return content

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return "ABORT"

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


def main():
    """Main entry point for the Twitter posting script."""
    parser = argparse.ArgumentParser(description='Post etymology tweets for EtymoBot - Pure Generative AI')
    parser.add_argument('--dry-run', '-n', action='store_true',
                      help='Generate tweet but do not post to Twitter')
    parser.add_argument('--verbose', '-v', action='store_true',
                      help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("🤖 Using PURE GENERATIVE approach - AI + Web Search verification")
    
    # Debug API key availability
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        logger.info(f"✅ OpenAI API key found (length: {len(api_key)} characters)")
    else:
        logger.error("❌ OpenAI API key not found in environment")
        logger.error("💡 Set OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    if not OpenAI:
        logger.error("❌ OpenAI package not available")
        logger.error("💡 Install with: pip install openai")
        sys.exit(1)
    
    try:
        # Initialize Twitter poster
        poster = TwitterPoster(dry_run=args.dry_run)
        
        logger.info(f"🤖 Pure generative approach - using OpenAI API with key ending in: ...{api_key[-4:]}")
        
        # Generate verified etymology using AI + web search
        logger.info("🤖 Generating verified etymology using AI + web search...")
        generator = GenerativeEtymologyGenerator(api_key)
        verified_etymology = generator.generate_verified_etymology(max_attempts=10)
        
        if verified_etymology:
            root = verified_etymology.root
            word1 = verified_etymology.word1
            word2 = verified_etymology.word2
            
            logger.info(f"✅ Generated: {word1} + {word2} -> {root}")
            logger.info(f"📊 Confidence: {verified_etymology.confidence:.2f}")
            logger.info(f"📄 Evidence: {verified_etymology.evidence_summary}")
        else:
            logger.error("❌ Failed to generate verified etymology after multiple attempts")
            logger.error("💡 Consider adjusting confidence thresholds or generation prompts")
            sys.exit(1)
        
        # Generate tweet
        tweet_text = poster.generate_tweet(word1, word2, root)
        
        # If OpenAI ABORTs during tweet generation, exit gracefully
        if "ABORT" in tweet_text.upper():
            logger.warning(f"🚫 OpenAI rejected etymology during tweet generation: {word1}+{word2}")
            logger.error("❌ Etymology was rejected as uninteresting or incorrect")
            sys.exit(1)
        
        logger.info(f"📱 Generated tweet: {tweet_text}")
        
        # Post tweet
        tweet_id = poster.post_tweet(tweet_text)
        if not tweet_id:
            logger.error("Failed to post tweet")
            sys.exit(1)
        
        logger.info(f"✅ Tweet posting completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Posting interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Posting failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 