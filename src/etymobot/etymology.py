"""Etymology discovery and root extraction services."""

import re
import random
import time
import logging
from typing import Optional
from urllib.parse import quote
import requests
import wordfreq
from bs4 import BeautifulSoup

from .config import Config
from .database import EtymoBotDatabase

logger = logging.getLogger(__name__)


class EtymologyService:
    """Handles etymology fetching and root extraction."""

    def __init__(self, config: Config, database: EtymoBotDatabase):
        self.config = config
        self.database = database

        # Improved regex to capture actual root words in various patterns
        self.etym_pattern = re.compile(
            r"(?:from\s+(?:latin|greek|sanskrit|old\s+[\w\-]+|proto-[\w\-]+)\s+)([a-z\-]+)|(?:root\s+)([a-z\-]+)",
            re.IGNORECASE)

        # Session for connection reuse
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'EtymoBot/1.0 (Educational Etymology Discovery Bot)'
        })

    def fetch_etymology(self, word: str) -> Optional[str]:
        """Fetch etymology text from Etymonline with robust error handling."""
        if not word or not isinstance(word, str):
            logger.warning("Invalid word provided for etymology fetch")
            return None

        normalized_word = word.lower().strip()
        if len(normalized_word) < 2:
            logger.warning(f"Word too short for etymology lookup: '{normalized_word}'")
            return None

        # Exponential backoff retry logic
        for attempt in range(self.config.max_retries + 1):
            try:
                url = f"https://www.etymonline.com/word/{quote(normalized_word)}"

                response = self.session.get(
                    url,
                    timeout=self.config.request_timeout,
                    allow_redirects=True
                )
                response.raise_for_status()

                if response.status_code == 404:
                    logger.info(f"No etymology found for '{normalized_word}' (404)")
                    return None

                soup = BeautifulSoup(response.text, "html.parser")

                # Try to find etymology in multiple ways
                etymology_text = self._extract_etymology_text(soup)

                if not etymology_text or len(etymology_text) < 50:
                    logger.warning(
                        f"Insufficient etymology data for '{normalized_word}': {
                            len(etymology_text) if etymology_text else 0} chars")
                    return None

                # Validate that we actually got etymology content
                if not self._validate_etymology_content(etymology_text):
                    logger.warning(f"Etymology content validation failed for '{normalized_word}'")
                    return None

                return etymology_text

            except requests.exceptions.Timeout:
                logger.warning(
                    f"Timeout fetching etymology for '{normalized_word}' (attempt {
                        attempt + 1})")
            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Request failed for '{normalized_word}' (attempt {
                        attempt + 1}): {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error fetching etymology for '{normalized_word}' (attempt {
                        attempt + 1}): {e}")

            # Exponential backoff before retry
            if attempt < self.config.max_retries:
                wait_time = (2 ** attempt) * self.config.rate_limit_delay
                logger.debug(f"Waiting {wait_time:.1f}s before retry...")
                time.sleep(wait_time)

        # All attempts failed
        logger.error(
            f"Failed to fetch etymology for '{normalized_word}' after {
                self.config.max_retries + 1} attempts")
        self.database.record_word_failure(normalized_word)
        return None

    def _extract_etymology_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract etymology text from parsed HTML using multiple strategies."""
        strategies = [
            # Strategy 1: Look for etymology section
            lambda: soup.find('section', class_='word__defination--2q7ZH'),
            # Strategy 2: Look for content div
            lambda: soup.find('div', class_='word__defination-content'),
            # Strategy 3: Look for any element with etymology in class name
            lambda: soup.find(attrs={'class': re.compile(r'etymon|definition|content', re.I)}),
            # Strategy 4: Get all text (fallback)
            lambda: soup
        ]

        for strategy in strategies:
            try:
                element = strategy()
                if element:
                    text = element.get_text(" ").strip()
                    if len(text) >= 50:  # Minimum meaningful length
                        return text
            except Exception as e:
                logger.debug(f"Etymology extraction strategy failed: {e}")
                continue

        return None

    def _validate_etymology_content(self, text: str) -> bool:
        """Validate that the text actually contains etymology information."""
        if not text:
            return False

        # Check for common etymology keywords
        etymology_indicators = [
            'from', 'latin', 'greek', 'sanskrit', 'root', 'origin',
            'derived', 'etymology', 'meaning', 'sense', 'related'
        ]

        text_lower = text.lower()
        return any(indicator in text_lower for indicator in etymology_indicators)

    def extract_root(self, etymology_text: str) -> Optional[str]:
        """Extract the deepest root from etymology text with validation."""
        if not etymology_text or not isinstance(etymology_text, str):
            return None

        matches = self.etym_pattern.findall(etymology_text.lower())
        if not matches:
            logger.debug(f"No etymology pattern matches found in: {etymology_text[:100]}...")
            return None

        # Handle multiple capture groups - each match is a tuple of groups
        all_roots = []
        for match in matches:
            for group in match:
                if group and len(group) >= self.config.min_root_length:
                    # Additional validation for root quality
                    if self._validate_root(group):
                        all_roots.append(group.strip())

        if not all_roots:
            return None

        # Return the longest match (likely the deepest root)
        best_root = max(all_roots, key=len)
        logger.debug(f"Extracted root '{best_root}' from {len(all_roots)} candidates")
        return best_root

    def _validate_root(self, root: str) -> bool:
        """Validate that a root is reasonable."""
        if not root or len(root) < self.config.min_root_length:
            return False

        # Check for reasonable characters (letters and hyphens only)
        if not re.match(r'^[a-z\-]+$', root):
            return False

        # Reject common English words that are unlikely to be roots
        common_words = {
            'the',
            'and',
            'for',
            'are',
            'but',
            'not',
            'you',
            'all',
            'can',
            'had',
            'her',
            'was',
            'one',
            'our',
            'out',
            'day',
            'get',
            'has',
            'him',
            'his',
            'how',
            'man',
            'new',
            'now',
            'old',
            'see',
            'two',
            'way',
            'who',
            'boy',
            'did',
            'its',
            'let',
            'put',
            'say',
            'she',
            'too',
            'use'}
        if root in common_words:
            return False

        return True

    def build_root_cache(self, sample_size: Optional[int] = None) -> int:
        """Build cache of root-word mappings with improved error handling."""
        if sample_size is None:
            sample_size = self.config.cache_sample_size

        words_added = 0
        words_processed = 0
        consecutive_failures = 0

        try:
            # Get high-frequency English words, filtering out problematic ones
            candidate_words = wordfreq.top_n_list("en", 10000)
            sample_words = random.sample(candidate_words, min(sample_size, len(candidate_words)))

            logger.info(f"Starting cache build with {len(sample_words)} candidate words")

            for word in sample_words:
                words_processed += 1

                # Skip problematic words
                if self.database.is_word_problematic(word):
                    logger.debug(f"Skipping problematic word: {word}")
                    continue

                # Check if already cached
                if self._is_word_cached(word):
                    logger.debug(f"Word already cached: {word}")
                    continue

                # Fetch etymology
                etymology_text = self.fetch_etymology(word)
                if not etymology_text:
                    consecutive_failures += 1
                    if consecutive_failures > 10:
                        logger.warning("Too many consecutive failures, taking longer break...")
                        time.sleep(5.0)
                        consecutive_failures = 0
                    continue

                # Reset failure counter on success
                consecutive_failures = 0

                # Extract root
                root = self.extract_root(etymology_text)
                if root and len(root) >= self.config.min_root_length:
                    if self.database.add_root_mapping(root, word):
                        words_added += 1
                        logger.debug(f"Added mapping: {root} -> {word}")
                    else:
                        logger.debug(f"Mapping already exists: {root} -> {word}")
                else:
                    logger.debug(f"No valid root extracted from etymology for: {word}")

                # Rate limiting
                time.sleep(self.config.rate_limit_delay)

                # Progress logging
                if words_processed % 50 == 0:
                    logger.info(
                        f"Cache build progress: {words_processed}/{len(sample_words)} processed, {words_added} added")

            self.database.commit()
            logger.info(
                f"Cache build complete: {words_added} new root-word mappings added from {words_processed} words")
            return words_added

        except Exception as e:
            logger.error(f"Cache building failed: {e}")
            return words_added

    def _is_word_cached(self, word: str) -> bool:
        """Check if a word is already in the cache."""
        try:
            words_for_any_root = self.database.cursor.execute(
                "SELECT 1 FROM rootmap WHERE word = ? LIMIT 1", (word.lower().strip(),)
            ).fetchone()
            return words_for_any_root is not None
        except Exception as e:
            logger.error(f"Failed to check if word is cached: {e}")
            return False

    def get_cache_stats(self) -> dict:
        """Get etymology cache statistics."""
        try:
            stats = self.database.get_database_stats()
            stats.update({
                'session_active': bool(self.session),
                'config': {
                    'min_root_length': self.config.min_root_length,
                    'rate_limit_delay': self.config.rate_limit_delay,
                    'request_timeout': self.config.request_timeout,
                    'max_retries': self.config.max_retries
                }
            })
            return stats
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

    def close(self) -> None:
        """Clean up resources."""
        if self.session:
            self.session.close()
