"""Command-line interface for EtymoBot."""

import argparse
import logging
import sys
import json

from .bot import EtymoBot
from .config import Config


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)

    # Suppress verbose third-party logs unless in debug mode
    if not verbose:
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('tweepy').setLevel(logging.INFO)
        logging.getLogger('openai').setLevel(logging.INFO)
        logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
        logging.getLogger('transformers').setLevel(logging.WARNING)
        logging.getLogger('torch').setLevel(logging.WARNING)


def handle_build_cache(args: argparse.Namespace) -> int:
    """Handle cache building command."""
    try:
        logger = logging.getLogger(__name__)
        logger.info("Starting cache build...")

        config = Config.from_env()
        if args.db:
            config.db_path = args.db

        with EtymoBot(config) as bot:
            sample_size = (args.sample_size if hasattr(args, 'sample_size') and
                           args.sample_size else None)
            count = bot.build_cache(sample_size)

            if count > 0:
                logger.info("Cache build successful: %d entries added", count)
                return 0
            else:
                logger.error("Cache build failed: no entries added")
                return 1

    except Exception as e:
        logging.getLogger(__name__).error("Cache build failed: %s", e)
        return 1


def handle_single_mode(args: argparse.Namespace) -> int:
    """Handle single tweet mode."""
    try:
        logger = logging.getLogger(__name__)
        logger.info("Running single tweet mode...")

        config = Config.from_env()
        if args.db:
            config.db_path = args.db

        with EtymoBot(config) as bot:
            success = bot.run_single_cycle(dry_run=args.dry_run)

            if success:
                logger.info("Single cycle completed successfully")
                return 0
            else:
                logger.error("Single cycle failed")
                return 1

    except Exception as e:
        logging.getLogger(__name__).error("Single mode failed: %s", e)
        return 1


def handle_scheduled_mode(args: argparse.Namespace) -> int:
    """Handle scheduled mode."""
    try:
        logger = logging.getLogger(__name__)
        logger.info("Running scheduled mode...")

        config = Config.from_env()
        if args.db:
            config.db_path = args.db

        with EtymoBot(config) as bot:
            bot.run_scheduled()
            logger.info("Scheduled mode completed")
            return 0

    except Exception as e:
        logging.getLogger(__name__).error("Scheduled mode failed: %s", e)
        return 1


def handle_stats(args: argparse.Namespace) -> int:
    """Handle statistics display."""
    try:
        config = Config.from_env()
        if args.db:
            config.db_path = args.db

        with EtymoBot(config) as bot:
            stats = bot.get_stats()

            if args.json:
                print(json.dumps(stats, indent=2, default=str))
            else:
                print("\n=== EtymoBot Statistics ===")

                # Database stats
                if 'database' in stats:
                    db_stats = stats['database']
                    print("\nDatabase:")
                    print("  Cache Size: %s" % db_stats.get('cache_size', 'unknown'))
                    print("  Unique Roots: %s" % db_stats.get('unique_roots', 'unknown'))
                    print("  Total Posted: %s" % db_stats.get('total_posted', 'unknown'))
                    print("  Failed Words: %s" % db_stats.get('failed_words', 'unknown'))
                    print("  Posts Last 24h: %s" % db_stats.get('posts_last_24h', 'unknown'))

                # Config stats
                if 'config' in stats:
                    config_stats = stats['config']
                    print("\nConfiguration:")
                    print("  Database: %s" % config_stats.get('db_path', 'unknown'))
                    print("  Min Cache Size: %s" % config_stats.get('min_cache_size', 'unknown'))
                    print(
                        "  Max Tweet Length: %s" %
                        config_stats.get(
                            'max_tweet_length',
                            'unknown'))
                    print("  OpenAI Model: %s" % config_stats.get('openai_model', 'unknown'))
                    print(
                        "  Optimal Hours (EST): %s" %
                        config_stats.get(
                            'optimal_hours_est',
                            'unknown'))
                    print(
                        "  Optimal Hours (UTC): %s" %
                        config_stats.get(
                            'optimal_hours_utc',
                            'unknown'))

                # Current status
                if 'current_time' in stats:
                    time_stats = stats['current_time']
                    print("\nCurrent Status:")
                    print("  Current Time (UTC): %s" % time_stats.get('utc', 'unknown'))
                    print("  Should Post Now: %s" % time_stats.get('should_post', 'unknown'))

                # Model info
                if 'semantic_model' in stats:
                    model_stats = stats['semantic_model']
                    print("\nSemantic Model:")
                    print("  Model: %s" % model_stats.get('model_name', 'unknown'))
                    print("  Device: %s" % model_stats.get('device', 'unknown'))
                    print(
                        "  Max Sequence Length: %s" %
                        model_stats.get(
                            'max_seq_length',
                            'unknown'))

            return 0

    except Exception as e:
        logging.getLogger(__name__).error("Stats display failed: %s", e)
        return 1


def handle_validate(args: argparse.Namespace) -> int:
    """Handle system validation."""
    try:
        logger = logging.getLogger(__name__)
        logger.info("Running system validation...")

        config = Config.from_env()
        if args.db:
            config.db_path = args.db

        with EtymoBot(config) as bot:
            results = bot.validate_system()

            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print("\n=== System Validation ===")
                for component, status in results.items():
                    if component == "error":
                        print("❌ Validation failed: %s" % status)
                    else:
                        icon = "✅" if status else "❌"
                        print("%s %s: %s" % (icon, component.replace('_', ' ').title(), status))

                all_valid = all(v for k, v in results.items() if k != "error")
                print(
                    "\n%s" %
                    ('🎉 All systems operational!' if all_valid else '⚠️  Some issues detected'))

            return 0 if all(v for k, v in results.items() if k != "error") else 1

    except Exception as e:
        logging.getLogger(__name__).error("System validation failed: %s", e)
        return 1


def handle_cleanup(args: argparse.Namespace) -> int:
    """Handle data cleanup command."""
    try:
        logger = logging.getLogger(__name__)
        logger.info("Running data cleanup...")

        config = Config.from_env()
        if args.db:
            config.db_path = args.db

        with EtymoBot(config) as bot:
            results = bot.cleanup_old_data(args.days)

            if 'error' in results:
                logger.error("Cleanup failed: %s", results['error'])
                return 1

            failures_cleaned = results.get('failures_cleaned', 0)
            logger.info("Cleanup completed: %d old failure records removed", failures_cleaned)
            return 0

    except Exception as e:
        logging.getLogger(__name__).error("Data cleanup failed: %s", e)
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="EtymoBot - Automated Etymology Discovery and Twitter Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --build-cache --sample-size 1000
  %(prog)s --mode single --dry-run
  %(prog)s --mode scheduled
  %(prog)s --stats --json
  %(prog)s --validate
  %(prog)s --cleanup --days 30
        """
    )

    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--db', type=str,
                        help='Database file path (default: etymobot.sqlite)')

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--build-cache', action='store_true',
                            help='Build etymology cache')
    mode_group.add_argument('--mode', choices=['single', 'scheduled'],
                            help='Bot operation mode')
    mode_group.add_argument('--stats', action='store_true',
                            help='Display system statistics')
    mode_group.add_argument('--validate', action='store_true',
                            help='Validate system components')
    mode_group.add_argument('--cleanup', action='store_true',
                            help='Clean up old data')

    # Additional options
    parser.add_argument('--sample-size', type=int, default=500,
                        help='Sample size for cache building (default: 500)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run in dry-run mode (no actual posting)')
    parser.add_argument('--json', action='store_true',
                        help='Output in JSON format')
    parser.add_argument('--days', type=int, default=7,
                        help='Days old for cleanup operations (default: 7)')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Route to appropriate handler
    try:
        if args.build_cache:
            return handle_build_cache(args)
        elif args.mode == 'single':
            return handle_single_mode(args)
        elif args.mode == 'scheduled':
            return handle_scheduled_mode(args)
        elif args.stats:
            return handle_stats(args)
        elif args.validate:
            return handle_validate(args)
        elif args.cleanup:
            return handle_cleanup(args)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Operation cancelled by user")
        return 130
    except Exception as e:
        logging.getLogger(__name__).error("Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
