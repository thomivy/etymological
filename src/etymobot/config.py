"""Configuration management for EtymoBot."""

import os
from typing import List
from dataclasses import dataclass, field
from datetime import datetime
import pytz


@dataclass
class Config:
    """Configuration settings for EtymoBot."""

    # API Keys
    openai_api_key: str
    twitter_bearer_token: str
    twitter_consumer_key: str
    twitter_consumer_secret: str
    twitter_access_token: str
    twitter_access_token_secret: str

    # Database
    db_path: str = "etymobot.sqlite"

    # Bot behavior
    cache_sample_size: int = 500
    min_cache_size: int = 100
    max_word_failures: int = 3
    min_root_length: int = 3

    # Timing
    optimal_posting_hours_est: List[int] = field(default_factory=lambda: [9, 13, 15])
    rate_limit_delay: float = 0.5

    # Tweet generation
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    max_tweet_length: int = 280

    # Network settings
    request_timeout: int = 10
    max_retries: int = 3

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_api_keys()
        self._validate_settings()

    def _validate_api_keys(self) -> None:
        """Validate API keys are not empty and have reasonable format."""
        api_key_fields = [
            'openai_api_key', 'twitter_bearer_token', 'twitter_consumer_key',
            'twitter_consumer_secret', 'twitter_access_token', 'twitter_access_token_secret'
        ]

        for field_name in api_key_fields:
            value = getattr(self, field_name)
            if not value or not isinstance(value, str) or len(value.strip()) < 10:
                raise ValueError(
                    f"Invalid {field_name}: must be a non-empty string with at least 10 characters")

    def _validate_settings(self) -> None:
        """Validate configuration settings."""
        if self.cache_sample_size <= 0:
            raise ValueError("cache_sample_size must be positive")

        if self.min_cache_size <= 0:
            raise ValueError("min_cache_size must be positive")

        if self.max_word_failures <= 0:
            raise ValueError("max_word_failures must be positive")

        if self.min_root_length <= 0:
            raise ValueError("min_root_length must be positive")

        if not all(0 <= hour <= 23 for hour in self.optimal_posting_hours_est):
            raise ValueError("optimal_posting_hours_est must contain hours between 0-23")

        if self.rate_limit_delay < 0:
            raise ValueError("rate_limit_delay must be non-negative")

        if not (50 <= self.max_tweet_length <= 280):
            raise ValueError("max_tweet_length must be between 50 and 280")

        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")

        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        required_env_vars = [
            "OPENAI_API_KEY",
            "TWITTER_BEARER_TOKEN",
            "TWITTER_CONSUMER_KEY",
            "TWITTER_CONSUMER_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET"
        ]

        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Parse optional integer settings with validation
        def parse_int_env(key: str, default: int, min_val: int = 0) -> int:
            value = os.getenv(key)
            if value is None:
                return default
            try:
                parsed = int(value)
                if parsed < min_val:
                    raise ValueError(f"{key} must be >= {min_val}")
                return parsed
            except ValueError as e:
                raise ValueError(f"Invalid {key}: {e}")

        def parse_float_env(key: str, default: float, min_val: float = 0.0) -> float:
            value = os.getenv(key)
            if value is None:
                return default
            try:
                parsed = float(value)
                if parsed < min_val:
                    raise ValueError(f"{key} must be >= {min_val}")
                return parsed
            except ValueError as e:
                raise ValueError(f"Invalid {key}: {e}")

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            twitter_bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            twitter_consumer_key=os.getenv("TWITTER_CONSUMER_KEY"),
            twitter_consumer_secret=os.getenv("TWITTER_CONSUMER_SECRET"),
            twitter_access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            twitter_access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            db_path=os.getenv("DB_PATH", "etymobot.sqlite"),
            cache_sample_size=parse_int_env("CACHE_SAMPLE_SIZE", 500, 1),
            min_cache_size=parse_int_env("MIN_CACHE_SIZE", 100, 1),
            max_word_failures=parse_int_env("MAX_WORD_FAILURES", 3, 1),
            min_root_length=parse_int_env("MIN_ROOT_LENGTH", 3, 1),
            rate_limit_delay=parse_float_env("RATE_LIMIT_DELAY", 0.5, 0.0),
            max_tweet_length=parse_int_env("MAX_TWEET_LENGTH", 280, 50),
            request_timeout=parse_int_env("REQUEST_TIMEOUT", 10, 1),
            max_retries=parse_int_env("MAX_RETRIES", 3, 0)
        )

    def get_optimal_posting_hours_utc(self) -> List[int]:
        """Convert EST posting hours to UTC with proper timezone handling."""
        try:
            # Use proper timezone library for accurate conversion
            est = pytz.timezone('US/Eastern')
            utc = pytz.timezone('UTC')

            # Get current date to handle DST properly
            today = datetime.now(est).date()

            utc_hours = []
            for est_hour in self.optimal_posting_hours_est:
                # Create datetime for today at the EST hour
                est_time = est.localize(
                    datetime.combine(
                        today, datetime.min.time().replace(
                            hour=est_hour)))
                # Convert to UTC
                utc_time = est_time.astimezone(utc)
                utc_hours.append(utc_time.hour)

            return utc_hours
        except Exception:
            # Fallback to simple conversion if pytz fails
            return [(hour + 5) % 24 for hour in self.optimal_posting_hours_est]

    def mask_sensitive_data(self) -> dict:
        """Return config dict with sensitive data masked for logging."""
        def mask_key(key: str) -> str:
            if len(key) <= 8:
                return "*" * len(key)
            return key[:4] + "*" * (len(key) - 8) + key[-4:]

        return {
            "openai_api_key": mask_key(self.openai_api_key),
            "twitter_bearer_token": mask_key(self.twitter_bearer_token),
            "twitter_consumer_key": mask_key(self.twitter_consumer_key),
            "twitter_consumer_secret": mask_key(self.twitter_consumer_secret),
            "twitter_access_token": mask_key(self.twitter_access_token),
            "twitter_access_token_secret": mask_key(self.twitter_access_token_secret),
            "db_path": self.db_path,
            "cache_sample_size": self.cache_sample_size,
            "min_cache_size": self.min_cache_size,
            "optimal_posting_hours_est": self.optimal_posting_hours_est,
            "max_tweet_length": self.max_tweet_length
        }
