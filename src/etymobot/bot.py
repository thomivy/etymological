"""Main EtymoBot orchestrator class."""

import itertools
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .config import Config
from .database import EtymoBotDatabase
from .etymology import EtymologyService
from .services import OpenAIService, TwitterService, SemanticService
from .models import WordPair

logger = logging.getLogger(__name__)


class EtymoBot:
    """Main bot class for etymology discovery and Twitter posting."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize EtymoBot with configuration and validate components."""
        try:
            self.config = config or Config.from_env()
            logger.info("Configuration loaded successfully")

            # Initialize components with error handling
            self.database = EtymoBotDatabase(self.config)
            self.etymology_service = EtymologyService(self.config, self.database)
            self.openai_service = OpenAIService(self.config)
            self.twitter_service = TwitterService(self.config)
            self.semantic_service = SemanticService(self.config)

            # Connect to database
            self.database.connect()

            # Validate API connections
            self._validate_services()

            logger.info("EtymoBot initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize EtymoBot: {e}")
            self.close()  # Clean up any partially initialized resources
            raise

    def _validate_services(self) -> None:
        """Validate that external services are working."""
        logger.info("Validating external services...")

        # Validate OpenAI API
        if not self.openai_service.validate_api_key():
            logger.warning("OpenAI API validation failed - tweet generation may not work")

        # Validate Twitter API
        if not self.twitter_service.validate_credentials():
            logger.warning("Twitter API validation failed - posting may not work")

        logger.info("Service validation complete")

    def find_candidate_pair(self) -> Optional[WordPair]:
        """Find the most semantically divergent unused word pair with enhanced validation."""
        try:
            # Ensure we have sufficient cache
            cache_size = self.database.get_cache_size()
            logger.info(f"Current cache size: {cache_size}")

            if cache_size < self.config.min_cache_size:
                logger.info("Cache below minimum size, building cache...")
                added = self.etymology_service.build_root_cache(
                    min(300, self.config.cache_sample_size)
                )
                if added == 0:
                    logger.warning("Failed to add any new cache entries")
                    return None
                logger.info(f"Added {added} new cache entries")

            # Find roots with multiple words
            root_candidates = self.database.get_roots_with_multiple_words(20)

            if not root_candidates:
                logger.warning("No roots with multiple words found")
                return None

            logger.info(f"Found {len(root_candidates)} root candidates")
            best_pair = None
            best_score = 0.0

            for root, word_count in root_candidates:
                logger.debug(f"Processing root '{root}' with {word_count} words")

                # Get all words for this root
                words = self.database.get_words_for_root(root)

                if len(words) < 2:
                    logger.debug(f"Root '{root}' has insufficient words: {len(words)}")
                    continue

                # Filter out already posted pairs and problematic words
                available_pairs = []
                for word1, word2 in itertools.combinations(words, 2):
                    if (not self.database.is_pair_posted(word1, word2) and
                        not self.database.is_word_problematic(word1) and
                            not self.database.is_word_problematic(word2)):
                        available_pairs.append((word1, word2))

                if not available_pairs:
                    logger.debug(f"No available pairs for root '{root}'")
                    continue

                logger.debug(f"Found {len(available_pairs)} available pairs for root '{root}'")

                # Score pairs by semantic divergence
                for word1, word2 in available_pairs:
                    try:
                        divergence = self.semantic_service.calculate_divergence(word1, word2)

                        if divergence > best_score:
                            # Validate the pair before selecting
                            try:
                                pair = WordPair(word1, word2, root, divergence)
                                best_pair = pair
                                best_score = divergence
                                logger.debug(f"New best pair: {pair}")
                            except ValueError as e:
                                logger.warning(f"Invalid word pair ({word1}, {word2}): {e}")
                                continue

                    except Exception as e:
                        logger.warning(f"Error calculating divergence for ({word1}, {word2}): {e}")
                        continue

            if best_pair:
                logger.info(f"Selected best pair: {best_pair}")
                return best_pair

            logger.warning("No suitable word pairs found")
            return None

        except Exception as e:
            logger.error(f"Candidate pair selection failed: {e}")
            return None

    def should_post_now(self) -> bool:
        """Check if current time is within optimal posting window with enhanced logic."""
        try:
            now = datetime.now(timezone.utc)
            current_hour = now.hour
            optimal_hours = self.config.get_optimal_posting_hours_utc()

            logger.debug(f"Current hour: {current_hour}, Optimal hours: {optimal_hours}")

            # Check if we're in an optimal hour
            if current_hour not in optimal_hours:
                logger.info(
                    "Not in optimal posting hour (current: %d, optimal: %s)",
                    current_hour, optimal_hours
                )
                return False

            # Check if we've already posted today at this hour
            hour_start = int(now.replace(minute=0, second=0, microsecond=0).timestamp())
            hour_end = hour_start + 3600

            posts_this_hour = self.database.get_posts_in_hour_range(hour_start, hour_end)

            if posts_this_hour > 0:
                logger.info(f"Already posted {posts_this_hour} time(s) this hour")
                return False

            logger.info("Optimal posting time confirmed")
            return True

        except Exception as e:
            logger.error(f"Error checking posting time: {e}")
            return False

    def run_single_cycle(self, dry_run: bool = False) -> bool:
        """Run a single discovery-generation-posting cycle with dry run option."""
        try:
            logger.info("Starting etymology discovery cycle..." + (" (DRY RUN)" if dry_run else ""))

            # Find candidate pair
            pair = self.find_candidate_pair()
            if not pair:
                logger.warning("No candidate pairs found")
                return False

            logger.info(f"Found candidate pair: {pair}")

            # Generate tweet
            tweet_content = self.openai_service.generate_tweet(pair)
            if not tweet_content:
                logger.warning("Failed to generate tweet content")
                return False

            logger.info(f"Generated tweet content: {tweet_content}")

            if dry_run:
                logger.info("DRY RUN: Would post tweet but skipping actual posting")
                return True

            # Post tweet
            tweet_id = self.twitter_service.post_tweet(tweet_content)
            if not tweet_id:
                logger.warning("Failed to post tweet")
                return False

            # Record the posted pair
            if self.database.record_posted_pair(pair, tweet_id):
                logger.info(f"Successfully posted and recorded tweet: {tweet_id}")
                return True
            else:
                logger.warning("Tweet posted but failed to record in database")
                return False

        except Exception as e:
            logger.error(f"Single cycle failed: {e}")
            return False

    def run_scheduled(self) -> None:
        """Run in scheduled mode - only post if it's an optimal time."""
        try:
            logger.info("Running scheduled mode check...")

            if not self.should_post_now():
                logger.info("Not optimal posting time, skipping...")
                return

            logger.info("Optimal time detected, running single cycle...")
            success = self.run_single_cycle()

            if success:
                logger.info("Scheduled posting completed successfully")
            else:
                logger.warning("Scheduled posting failed")

        except Exception as e:
            logger.error(f"Scheduled mode failed: {e}")

    def build_cache(self, sample_size: Optional[int] = None) -> int:
        """Build etymology cache with specified sample size."""
        try:
            logger.info("Starting cache build process...")

            if sample_size is None:
                sample_size = self.config.cache_sample_size

            added_count = self.etymology_service.build_root_cache(sample_size)

            if added_count > 0:
                logger.info(f"Cache build successful: {added_count} entries added")
            else:
                logger.warning("Cache build completed but no entries were added")

            return added_count

        except Exception as e:
            logger.error(f"Cache build failed: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            # Database stats
            db_stats = self.database.get_database_stats()

            # Configuration stats
            config_stats = {
                'db_path': self.config.db_path,
                'min_cache_size': self.config.min_cache_size,
                'max_tweet_length': self.config.max_tweet_length,
                'openai_model': self.config.openai_model,
                'optimal_hours_est': self.config.optimal_posting_hours_est,
                'optimal_hours_utc': self.config.get_optimal_posting_hours_utc()
            }

            # Current time status
            now = datetime.now(timezone.utc)
            time_stats = {
                'utc': now.isoformat(),
                'should_post': self.should_post_now()
            }

            # Semantic model info
            model_stats = self.semantic_service.get_model_info()

            return {
                'database': db_stats,
                'config': config_stats,
                'current_time': time_stats,
                'semantic_model': model_stats
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'error': str(e)}

    def cleanup_old_data(self, days_old: int = 7) -> Dict[str, int]:
        """Clean up old data to prevent database bloat."""
        try:
            logger.info(f"Cleaning up data older than {days_old} days...")

            failures_cleaned = self.database.cleanup_old_failures(days_old)

            logger.info(f"Cleanup complete: {failures_cleaned} old failure records removed")

            return {
                'failures_cleaned': failures_cleaned
            }

        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
            return {'error': str(e)}

    def validate_system(self) -> Dict[str, bool]:
        """Validate that all system components are working."""
        try:
            results = {}

            # Database connection
            try:
                self.database.get_cache_size()
                results['database_connection'] = True
            except Exception:
                results['database_connection'] = False

            # OpenAI API
            results['openai_api'] = self.openai_service.validate_api_key()

            # Twitter API
            results['twitter_api'] = self.twitter_service.validate_credentials()

            # Semantic model
            try:
                self.semantic_service.get_model_info()
                results['semantic_model'] = True
            except Exception:
                results['semantic_model'] = False

            return results

        except Exception as e:
            logger.error(f"System validation failed: {e}")
            return {'error': str(e)}

    def close(self) -> None:
        """Clean up resources."""
        try:
            if hasattr(self, 'database') and self.database:
                self.database.close()

            if hasattr(self, 'etymology_service') and self.etymology_service:
                self.etymology_service.close()

            logger.info("EtymoBot resources cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
