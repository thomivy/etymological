#!/usr/bin/env python3
"""
Production EtymoBot with Real Web Search Verification

This implementation actually uses web search to verify etymological claims,
creating a robust fact-checking system for philology nerds.
"""

import json
import logging
import time
import os
from typing import List, Optional, Dict
from dataclasses import dataclass

# Configure logging to suppress HTTP requests
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Suppress noisy HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


@dataclass
class VerifiedEtymology:
    word1: str
    word2: str
    root: str
    confidence: float
    evidence_summary: str
    search_results: List[str]


class ProductionEtymoBot:
    """
    Production EtymoBot with real web search verification.
    
    This creates an anti-hallucination pipeline that philology nerds can trust.
    """
    
    def __init__(self, openai_api_key: str, web_search_tool):
        self.openai_api_key = openai_api_key
        self.web_search = web_search_tool
    
    def generate_verified_etymologies(self, count: int = 3) -> List[VerifiedEtymology]:
        """
        Generate rigorously verified etymologies using web search fact-checking.
        """
        verified = []
        attempts = 0
        max_attempts = 15
        
        while len(verified) < count and attempts < max_attempts:
            attempts += 1
            
            # Generate etymology suggestion
            suggestion = self._generate_suggestion()
            if not suggestion:
                continue
                
            word1, word2, root = suggestion['word1'], suggestion['word2'], suggestion['root']
            logger.info(f"Attempt {attempts}: Testing {word1} + {word2} -> {root}")
            
            # Quick validation to catch obvious false etymologies
            if self._is_obviously_false_etymology(word1, word2, root):
                logger.info(f"❌ REJECTED: {word1} + {word2} (obviously false etymology)")
                continue
            
            # Verify using web search
            verification = self._verify_with_web_search(word1, word2, root)
            
            if verification and verification.confidence >= 0.7:
                verified.append(verification)
                logger.info(f"✅ VERIFIED: {word1} + {word2} (confidence: {verification.confidence:.2f})")
            else:
                confidence_msg = f" (confidence: {verification.confidence:.2f})" if verification else ""
                logger.info(f"❌ REJECTED: {word1} + {word2}{confidence_msg}")
                
            # Rate limiting
            time.sleep(1)
        
        return verified
    
    def _is_obviously_false_etymology(self, word1: str, word2: str, root: str) -> bool:
        """
        Quick validation to catch obviously false etymologies.
        
        This prevents wasting API calls on clearly incorrect pairings.
        """
        # Known false etymology patterns
        false_patterns = {
            # Modern slang + classical words
            ("southpaw", "sinister"): "southpaw is modern American boxing slang, not from Latin",
            ("radar", "radio"): "radar is WWII acronym, not etymologically related to radio",
            ("scuba", "submarine"): "scuba is modern acronym, not classical etymology",
            
            # Obvious anachronisms
            ("computer", "compute"): "too obvious/modern to be interesting",
            ("television", "telephone"): "both modern Greek compounds, not surprising",
        }
        
        # Check both orientations
        pair1 = (word1.lower(), word2.lower())
        pair2 = (word2.lower(), word1.lower())
        
        if pair1 in false_patterns or pair2 in false_patterns:
            reason = false_patterns.get(pair1, false_patterns.get(pair2))
            logger.debug(f"Blocked false etymology: {reason}")
            return True
        
        # Check for modern words that shouldn't have ancient roots
        modern_words = {
            'southpaw', 'radar', 'scuba', 'laser', 'blog', 'email', 'internet',
            'smartphone', 'selfie', 'podcast', 'website', 'download', 'upload'
        }
        
        if word1.lower() in modern_words or word2.lower() in modern_words:
            logger.debug(f"Blocked pairing with modern word: {word1}, {word2}")
            return True
        
        return False
    
    def _generate_suggestion(self) -> Optional[Dict]:
        """Generate a single etymology suggestion."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Generate ONE surprising English word pair sharing an etymological root.

Requirements:
- Genuine scholarly etymologies only (no folk etymologies)
- Significant semantic drift between the words
- Words most people use but wouldn't expect to be related
- Fascinating to linguists and general public alike

Return JSON: {"word1": "word", "word2": "word", "root": "*root", "claim": "brief claim about connection"}"""
                    },
                    {
                        "role": "user",
                        "content": "Generate one etymological word pair that would surprise people."
                    }
                ],
                temperature=0.8,
                max_tokens=150
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON
            if '```' in content:
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {e}")
            return None
    
    def _verify_with_web_search(self, word1: str, word2: str, root: str) -> Optional[VerifiedEtymology]:
        """
        Verify etymological claim using real web search and AI fact-checking.
        
        This is the core anti-hallucination mechanism.
        """
        try:
            # Search for evidence
            search_results = []
            
            # Multiple search strategies
            queries = [
                f'etymology "{word1}" "{word2}" related common root',
                f'"{word1}" etymology origin {root.strip("*")}',
                f'"{word2}" etymology origin {root.strip("*")}',
                f'{word1} {word2} cognate same etymology'
            ]
            
            for query in queries[:2]:  # Limit searches to avoid rate limits
                logger.info(f"Searching: {query}")
                
                try:
                    results = self.web_search(
                        search_term=query,
                        explanation=f"Verifying etymology connection: {word1} + {word2}"
                    )
                    
                    if results:
                        search_results.extend(results[:3])  # Top 3 per query
                        
                except Exception as e:
                    logger.warning(f"Search failed for '{query}': {e}")
                    continue
                
                time.sleep(0.5)  # Rate limiting
            
            if not search_results:
                logger.warning(f"No search results found for {word1} + {word2}")
                return None
            
            # Have AI evaluate the evidence
            return self._ai_fact_check(word1, word2, root, search_results)
            
        except Exception as e:
            logger.error(f"Web verification failed: {e}")
            return None
    
    def _ai_fact_check(self, word1: str, word2: str, root: str, search_results: List) -> Optional[VerifiedEtymology]:
        """
        AI fact-checking against search results.
        
        This creates a self-verification loop where the AI scrutinizes 
        its own etymological claims against web evidence.
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            # Prepare search results for analysis
            results_text = "\n\n".join([
                f"Result {i+1}: {str(result)[:300]}..." 
                for i, result in enumerate(search_results[:5])
            ])
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a ruthless etymological fact-checker. Philology experts will scrutinize your assessment.

Evaluate if the search results ACTUALLY SUPPORT the claimed connection between the two words and root.

Be EXTREMELY STRICT. Only return high confidence if:
- Multiple authoritative sources explicitly confirm the connection
- The etymological path is clearly documented
- Sources like etymonline.com, Merriam-Webster, Oxford confirm it
- You would bet your reputation on this being correct

Return: CONFIDENCE_SCORE (0.0-1.0)|EVIDENCE_SUMMARY|REASONING

If confidence < 0.7, this will be rejected."""
                    },
                    {
                        "role": "user",
                        "content": f"""CLAIM: "{word1}" and "{word2}" both derive from the root "{root}"

SEARCH RESULTS:
{results_text}

Fact-check this claim. Are the search results sufficient to verify this etymology?"""
                    }
                ],
                temperature=0.0,  # Zero temperature for fact-checking
                max_tokens=250
            )
            
            evaluation = response.choices[0].message.content.strip()
            logger.info(f"AI evaluation: {evaluation[:100]}...")
            
            # Parse the evaluation
            parts = evaluation.split('|')
            if len(parts) >= 3:
                try:
                    confidence = float(parts[0])
                    evidence_summary = parts[1].strip()
                    reasoning = parts[2].strip()
                    
                    logger.info(f"Confidence: {confidence:.2f} - {reasoning}")
                    
                    if confidence >= 0.7:
                        return VerifiedEtymology(
                            word1=word1,
                            word2=word2,
                            root=root,
                            confidence=confidence,
                            evidence_summary=evidence_summary,
                            search_results=[str(r)[:100] for r in search_results[:3]]
                        )
                    else:
                        return None
                        
                except ValueError:
                    logger.warning(f"Could not parse confidence score: {parts[0]}")
                    return None
            else:
                logger.warning(f"Unexpected evaluation format: {evaluation}")
                return None
                
        except Exception as e:
            logger.error(f"AI fact-checking failed: {e}")
            return None
    
    def generate_tweet(self, etymology: VerifiedEtymology) -> str:
        """Generate a beautiful tweet for verified etymology."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Create a poetic etymology tweet (≤280 chars).

Style: Literary, compressed, present tense
Include: Both words, root meaning, semantic journey
Tone: Wonder at language's hidden connections

This has been rigorously fact-checked, so be confident in the connection."""
                    },
                    {
                        "role": "user",
                        "content": f"""VERIFIED ETYMOLOGY:
Words: "{etymology.word1}" and "{etymology.word2}"
Root: {etymology.root}
Evidence: {etymology.evidence_summary}
Confidence: {etymology.confidence:.1%}

Write a beautiful tweet revealing this connection."""
                    }
                ],
                temperature=0.7,
                max_tokens=100
            )
            
            tweet = response.choices[0].message.content.strip()
            
            # Ensure it fits in a tweet
            if len(tweet) <= 280:
                return tweet
            else:
                # Fallback
                return f'"{etymology.word1}" and "{etymology.word2}" both spring from {etymology.root}—ancient roots, modern paths, eternal connections.'
                
        except Exception as e:
            logger.error(f"Tweet generation failed: {e}")
            return f'"{etymology.word1}" and "{etymology.word2}" share the root {etymology.root}.'


def main():
    """Main demo function."""
    print("🔍 Production EtymoBot with Web Search Verification")
    print("=" * 60)
    print("This version uses REAL web search to verify etymologies!")
    print("Perfect for satisfying philology nerds who demand accuracy.")
    print("=" * 60)
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ Error: OPENAI_API_KEY environment variable not set")
        print("💡 Please set your OpenAI API key to test this functionality")
        return
    
    print("\n📝 Note: This is a demonstration script.")
    print("🔧 In production, you would integrate with the actual web_search tool.")
    print("🎯 The concept shows how to create rigorous fact-checking for etymologies.\n")


if __name__ == "__main__":
    main() 