"""External API services for Twitter and OpenAI."""

import logging
import random
import time
import numpy as np
from typing import Optional, Dict, Any, List
import openai
import tweepy

from .config import Config
from .models import WordPair

logger = logging.getLogger(__name__)


class OpenAIService:
    """Handles OpenAI API interactions for tweet generation."""

    def __init__(self, config: Config):
        self.config = config
        try:
            self.client = openai.OpenAI(api_key=config.openai_api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise

        # Stylistic variation templates
        self.templates = [
            self._statement_twist_template,
            self._question_hook_template,
            self._mini_anecdote_template,
            self._fragment_aside_template,
            self._oneliner_aphorism_template
        ]

    def _statement_twist_template(self, pair: WordPair) -> str:
        """Statement + Twist template."""
        return f"""Create a tweet using this template:

{pair.word1} born of {pair.root} ("<root-gloss>"). <Brief divergence narrative>. <Final reflection>.

Guidelines:
- Start with a declarative statement about the word's origin
- Show how the words diverged with vivid imagery
- End with a twist or reflection that makes the reader think
- Use strong verbs and concrete nouns
- Keep under {self.config.max_tweet_length} characters
- No emojis or hashtags

Words: {pair.word1}, {pair.word2}
Root: {pair.root}"""

    def _question_hook_template(self, pair: WordPair) -> str:
        """Question Hook template."""
        return f"""Create a tweet using this template:

Ever wondered why {pair.word1} and {pair.word2} both echo {pair.root}? <Divergence + concrete image>. <Invitation to ponder>.

Guidelines:
- Open with an engaging question to hook the reader
- Explain the connection with a concrete, sensory image
- Close with an invitation to reflect or wonder
- Make it conversational and curious
- Keep under {self.config.max_tweet_length} characters
- No emojis or hashtags

Words: {pair.word1}, {pair.word2}
Root: {pair.root}"""

    def _mini_anecdote_template(self, pair: WordPair) -> str:
        """Mini Anecdote template."""
        return f"""Create a tweet using this template:

In ancient times, {pair.root} meant "<gloss>"—the seed of {pair.word1} and {pair.word2}. <Contrast>. <Aphoristic close>.

Guidelines:
- Begin with "In ancient times" to set historical context
- Provide the root meaning and show it as the "seed"
- Create a clear contrast between the two words
- End with a wise or poetic observation
- Keep under {self.config.max_tweet_length} characters
- No emojis or hashtags

Words: {pair.word1}, {pair.word2}
Root: {pair.root}"""

    def _fragment_aside_template(self, pair: WordPair) -> str:
        """Fragment & Aside template."""
        return f"""Create a tweet using this template:

{pair.word1} & {pair.word2}—rooted in {pair.root} ("<gloss>"). One <short metaphor>, the other <short metaphor> (<sensory aside>). <Question or insight>.

Guidelines:
- Use fragment style with dashes and ampersands
- Create parallel metaphors for each word
- Include a brief sensory aside in parentheses
- End with a question or insight
- Mix short and long phrases for rhythm
- Keep under {self.config.max_tweet_length} characters
- No emojis or hashtags

Words: {pair.word1}, {pair.word2}
Root: {pair.root}"""

    def _oneliner_aphorism_template(self, pair: WordPair) -> str:
        """One-Liner Aphorism template."""
        return f"""Create a tweet using this template:

{pair.word1}/{pair.word2}: <gloss>. <One-sentence distillation of divergence or irony>.

Guidelines:
- Use slash notation for compact pairing
- Provide the root gloss concisely
- Distill the entire etymology story into one punchy sentence
- Focus on irony, contrast, or surprising connection
- Make it quotable and memorable
- Keep under {self.config.max_tweet_length} characters
- No emojis or hashtags

Words: {pair.word1}, {pair.word2}
Root: {pair.root}"""

    def generate_tweet(self, pair: WordPair) -> Optional[str]:
        """Generate tweet content using OpenAI with stylistic variation and robust error handling."""
        if not pair:
            logger.error("No word pair provided for tweet generation")
            return None

        for attempt in range(self.config.max_retries + 1):
            try:
                # Randomly select a template for variation
                template_func = random.choice(self.templates)
                prompt = template_func(pair)

                logger.debug(
                    f"Using template: {
                        template_func.__name__} for {
                        pair.word1}/{
                        pair.word2} (attempt {
                        attempt + 1})")

                response = self.client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.8,
                    timeout=self.config.request_timeout
                )

                if not response.choices or not response.choices[0].message:
                    logger.warning(f"Empty response from OpenAI (attempt {attempt + 1})")
                    continue

                tweet_content = response.choices[0].message.content.strip()

                if not tweet_content:
                    logger.warning(f"Empty tweet content from OpenAI (attempt {attempt + 1})")
                    continue

                # Validate length
                if len(tweet_content) <= self.config.max_tweet_length:
                    logger.info(
                        f"Generated tweet ({len(tweet_content)} chars): {tweet_content[:100]}...")
                    return tweet_content

                logger.warning(
                    f"Generated tweet too long ({
                        len(tweet_content)} chars), trying fallback...")

                # Fallback to a simple, short template
                fallback_prompt = f"""Write a concise tweet under {
                    self.config.max_tweet_length} characters about how {
                    pair.word1} and {
                    pair.word2} share the root '{
                    pair.root}' but have different meanings. Be engaging and poetic but brief. No emojis or hashtags."""

                fallback_response = self.client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=[{"role": "user", "content": fallback_prompt}],
                    max_tokens=60,
                    temperature=0.7,
                    timeout=self.config.request_timeout
                )

                if fallback_response.choices and fallback_response.choices[0].message:
                    fallback_content = fallback_response.choices[0].message.content.strip()
                    if fallback_content and len(fallback_content) <= self.config.max_tweet_length:
                        logger.info(f"Fallback tweet successful ({len(fallback_content)} chars)")
                        return fallback_content

                logger.warning(
                    f"Fallback also failed, retrying with different template (attempt {
                        attempt + 1})")

            except openai.RateLimitError as e:
                wait_time = (2 ** attempt) * 5  # Exponential backoff for rate limits
                logger.warning(
                    f"OpenAI rate limit hit (attempt {
                        attempt + 1}), waiting {wait_time}s: {e}")
                if attempt < self.config.max_retries:
                    time.sleep(wait_time)
                continue

            except openai.APIError as e:
                logger.error(f"OpenAI API error (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue

            except Exception as e:
                logger.error(f"Unexpected error in tweet generation (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries:
                    time.sleep(1)
                continue

        logger.error(
            f"Failed to generate tweet for {
                pair.word1}/{
                pair.word2} after {
                self.config.max_retries + 1} attempts")
        return None

    def validate_api_key(self) -> bool:
        """Validate that the OpenAI API key is working."""
        try:
            # Make a minimal API call to test the key
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=1,
                timeout=10
            )
            return bool(response.choices)
        except Exception as e:
            logger.error(f"OpenAI API key validation failed: {e}")
            return False


class TwitterService:
    """Handles Twitter API interactions."""

    def __init__(self, config: Config):
        self.config = config
        try:
            self.client = tweepy.Client(
                bearer_token=config.twitter_bearer_token,
                consumer_key=config.twitter_consumer_key,
                consumer_secret=config.twitter_consumer_secret,
                access_token=config.twitter_access_token,
                access_token_secret=config.twitter_access_token_secret,
                wait_on_rate_limit=True
            )
            logger.info("Twitter client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            raise

    def post_tweet(self, content: str) -> Optional[str]:
        """Post tweet to Twitter and return tweet ID with robust error handling."""
        if not content or not content.strip():
            logger.error("Cannot post empty tweet content")
            return None

        content = content.strip()
        if len(content) > self.config.max_tweet_length:
            logger.error(f"Tweet content too long: {len(content)} > {self.config.max_tweet_length}")
            return None

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.info(f"Attempting to post tweet (attempt {attempt + 1}): {content[:100]}...")

                response = self.client.create_tweet(text=content)

                if not response.data or 'id' not in response.data:
                    logger.error(f"Invalid response from Twitter API: {response}")
                    continue

                tweet_id = response.data['id']
                logger.info(f"Successfully posted tweet (ID: {tweet_id}): {content}")
                return tweet_id

            except tweepy.Forbidden as e:
                logger.error(f"Twitter API access forbidden: {e}")
                return None  # Don't retry on auth issues

            except tweepy.TooManyRequests as e:
                wait_time = (2 ** attempt) * 60  # Exponential backoff in minutes for rate limits
                logger.warning(
                    f"Twitter rate limit hit (attempt {
                        attempt +
                        1}), waiting {
                        wait_time /
                        60:.1f} minutes: {e}")
                if attempt < self.config.max_retries:
                    time.sleep(wait_time)
                continue

            except tweepy.BadRequest as e:
                logger.error(f"Bad request to Twitter API: {e}")
                return None  # Don't retry on bad requests

            except Exception as e:
                logger.error(f"Unexpected error posting tweet (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries:
                    time.sleep(2 ** attempt)
                continue

        logger.error(f"Failed to post tweet after {self.config.max_retries + 1} attempts")
        return None

    def validate_credentials(self) -> bool:
        """Validate that Twitter credentials are working."""
        try:
            # Test by getting user info
            me = self.client.get_me()
            if me.data:
                logger.info(f"Twitter credentials valid for user: {me.data.username}")
                return True
            return False
        except Exception as e:
            logger.error(f"Twitter credentials validation failed: {e}")
            return False


class SemanticService:
    """Handles semantic similarity calculations using OpenAI embeddings."""

    def __init__(self, config: Config):
        self.config = config
        try:
            # Reuse the same OpenAI client instead of loading a massive local model
            self.client = openai.OpenAI(api_key=config.openai_api_key)
            self.embedding_model = config.openai_embedding_model
            logger.info(f"Semantic service initialized with OpenAI embeddings: {self.embedding_model}")
        except Exception as e:
            logger.error(f"Failed to initialize semantic service: {e}")
            raise

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for a single text using OpenAI API."""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text.strip(),
                timeout=self.config.request_timeout
            )
            
            if response.data and len(response.data) > 0:
                return response.data[0].embedding
            else:
                logger.warning(f"Empty embedding response for text: {text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get embedding for '{text}': {e}")
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            # Convert to numpy arrays for efficient computation
            a, b = np.array(vec1), np.array(vec2)
            
            # Calculate cosine similarity
            cos_sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            
            # Ensure valid range
            cos_sim = np.clip(cos_sim, -1.0, 1.0)
            
            return float(cos_sim)
            
        except Exception as e:
            logger.error(f"Failed to calculate cosine similarity: {e}")
            return 0.0

    def calculate_divergence(self, word1: str, word2: str) -> float:
        """Calculate semantic divergence between two words using OpenAI embeddings."""
        if not word1 or not word2 or not isinstance(word1, str) or not isinstance(word2, str):
            logger.warning(f"Invalid words for divergence calculation: '{word1}', '{word2}'")
            return 0.0

        # Normalize words
        w1, w2 = word1.strip().lower(), word2.strip().lower()

        if w1 == w2:
            logger.debug(f"Identical words provided: '{w1}'")
            return 0.0

        try:
            # Get embeddings from OpenAI
            emb1 = self._get_embedding(w1)
            emb2 = self._get_embedding(w2)
            
            if emb1 is None or emb2 is None:
                logger.warning(f"Failed to get embeddings for '{w1}' or '{w2}'")
                return 0.0
            
            # Calculate similarity
            similarity = self._cosine_similarity(emb1, emb2)
            
            # Validate similarity score
            if not isinstance(similarity, (int, float)) or not (-1 <= similarity <= 1):
                logger.warning(f"Invalid similarity score: {similarity}")
                return 0.0

            divergence = 1 - similarity  # Higher = more divergent

            # Ensure divergence is in valid range
            divergence = max(0.0, min(1.0, divergence))

            logger.debug(f"Divergence calculated for '{w1}' vs '{w2}': {divergence:.3f}")
            return divergence

        except Exception as e:
            logger.error(f"Failed to calculate divergence for ({w1}, {w2}): {e}")
            return 0.0

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding service."""
        return {
            "service": "OpenAI Embeddings API",
            "model": self.embedding_model,
            "embedding_dimensions": "1536 (text-embedding-3-small) or 3072 (text-embedding-3-large)",
            "cost_per_1k_tokens": "~$0.00002 (text-embedding-3-small)",
            "advantages": "No local model download, always up-to-date, state-of-the-art performance"
        }
