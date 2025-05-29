#!/usr/bin/env python3
"""
Test suite for EtymoBot.
"""

import unittest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from etymobot import EtymoBot, WordPair, Config


class TestEtymoBot(unittest.TestCase):
    """Test cases for EtymoBot functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-openai-key-1234567890',  # Enhanced: longer key
            'TWITTER_BEARER_TOKEN': 'test-bearer-token-1234567890',
            'TWITTER_CONSUMER_KEY': 'test-consumer-key-1234567890', 
            'TWITTER_CONSUMER_SECRET': 'test-consumer-secret-1234567890',
            'TWITTER_ACCESS_TOKEN': 'test-access-token-1234567890',
            'TWITTER_ACCESS_TOKEN_SECRET': 'test-access-token-secret-1234567890'
        })
        self.env_patcher.start()
        
        # Create config and bot with mocked services
        self.config = Config.from_env()
        self.config.db_path = self.temp_db.name
        
        # Mock external services to prevent actual API calls during tests
        with patch('etymobot.services.SentenceTransformer'), \
             patch('etymobot.services.tweepy.Client'), \
             patch('etymobot.services.openai.OpenAI'), \
             patch('etymobot.bot.EtymoBot._validate_services'):  # Skip API validation
            self.bot = EtymoBot(self.config)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.bot.close()
        self.env_patcher.stop()
        os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test database initialization and table creation."""
        # Check that tables exist
        tables = self.bot.database.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        
        table_names = [row[0] for row in tables]
        expected_tables = ['rootmap', 'posted', 'failed_words']
        
        for table in expected_tables:
            self.assertIn(table, table_names)
    
    def test_extract_root(self):
        """Test root extraction from etymology text."""
        test_cases = [
            ("from Latin gregarius meaning belonging to a flock", "gregarius"),
            ("from Greek speirein to scatter", "speirein"),
            ("from Sanskrit vir meaning man", "vir"),
            ("from proto-indo-european dhghem meaning earth", "dhghem"),
            ("No etymology information here", None)
        ]
        
        for etymology_text, expected_root in test_cases:
            with self.subTest(etymology_text=etymology_text):
                result = self.bot.etymology_service.extract_root(etymology_text)
                self.assertEqual(result, expected_root)
    
    def test_word_failure_tracking(self):
        """Test word failure tracking system."""
        test_word = "problematic_word"
        
        # Initially not problematic
        self.assertFalse(self.bot.database.is_word_problematic(test_word))
        
        # Record failures
        for i in range(3):
            self.bot.database.record_word_failure(test_word)
        
        # Should now be problematic
        self.assertTrue(self.bot.database.is_word_problematic(test_word))
    
    @patch('etymobot.etymology.requests.Session.get')
    def test_fetch_etymology_success(self, mock_get):
        """Test successful etymology fetching."""
        # Mock successful response with etymology content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><body>
        <div class="word__defination--2q7ZH">
        from Latin gregarius meaning belonging to a flock, from grex (genitive gregis) 
        meaning flock, herd. The sense developed from "pertaining to a flock" to 
        "fond of company" by 1660s. Related: Gregariously; gregariousness.
        </div>
        </body></html>
        """
        mock_get.return_value = mock_response
        
        result = self.bot.etymology_service.fetch_etymology("gregarious")
        
        self.assertIsNotNone(result)
        self.assertIn("gregarius", result)
        self.assertGreater(len(result), 50)  # Should be substantial content
        mock_get.assert_called()
    
    @patch('etymobot.etymology.requests.Session.get')
    def test_fetch_etymology_failure(self, mock_get):
        """Test etymology fetching with network error."""
        # Mock network failure that exhausts retries
        mock_get.side_effect = Exception("Network error")
        
        # Call fetch_etymology multiple times to reach the failure threshold
        for i in range(3):  # Need 3 failures to mark as problematic
            result = self.bot.etymology_service.fetch_etymology("test_word")
            self.assertIsNone(result)
        
        # Explicitly commit to ensure failure is recorded
        self.bot.database.commit()
        
        # Should have recorded the word failure
        self.assertTrue(self.bot.database.is_word_problematic("test_word"))
    
    def test_optimal_posting_times(self):
        """Test optimal posting time calculation with enhanced timezone handling."""
        optimal_hours = self.config.get_optimal_posting_hours_utc()
        
        # Should have 3 optimal hours
        self.assertEqual(len(optimal_hours), 3)
        
        # All hours should be valid (0-23)
        for hour in optimal_hours:
            self.assertGreaterEqual(hour, 0)
            self.assertLessEqual(hour, 23)
        
        # Should be different from EST hours (conversion happened)
        est_hours = self.config.optimal_posting_hours_est
        self.assertNotEqual(set(optimal_hours), set(est_hours))
    
    @patch('etymobot.bot.datetime')
    def test_should_post_now_optimal_time(self, mock_datetime):
        """Test posting decision during optimal time."""
        # Get actual optimal hours from config
        optimal_hours = self.config.get_optimal_posting_hours_utc()
        optimal_hour = optimal_hours[0]  # Use first optimal hour
        
        # Mock current time as optimal time
        mock_now = datetime(2023, 12, 1, optimal_hour, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        # No posts in this hour yet
        result = self.bot.should_post_now()
        self.assertTrue(result)
    
    @patch('etymobot.bot.datetime')
    def test_should_post_now_non_optimal_time(self, mock_datetime):
        """Test posting decision during non-optimal time."""
        # Find a non-optimal hour
        optimal_hours = set(self.config.get_optimal_posting_hours_utc())
        non_optimal_hour = None
        for hour in range(24):
            if hour not in optimal_hours:
                non_optimal_hour = hour
                break
        
        # Mock current time as non-optimal time
        mock_now = datetime(2023, 12, 1, non_optimal_hour, 30, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now
        
        result = self.bot.should_post_now()
        self.assertFalse(result)
    
    def test_word_pair_creation(self):
        """Test WordPair dataclass functionality with enhanced validation."""
        # Test valid pair creation
        pair = WordPair("gregarious", "egregious", "greg", 0.75)
        
        # Words should be normalized to lowercase
        self.assertEqual(pair.word1, "gregarious")
        self.assertEqual(pair.word2, "egregious") 
        self.assertEqual(pair.root, "greg")
        self.assertEqual(pair.divergence_score, 0.75)
        
        # Test string representation
        self.assertIn("gregarious", str(pair))
        self.assertIn("egregious", str(pair))
        self.assertIn("greg", str(pair))
        
        # Test ordered pair
        ordered = pair.ordered_pair
        self.assertEqual(ordered, ("egregious", "gregarious"))  # Alphabetical order
        
        # Test validation - invalid divergence score
        with self.assertRaises(ValueError):
            WordPair("gregarious", "egregious", "greg", 1.5)  # Invalid score > 1.0
        
        # Test validation - identical words
        with self.assertRaises(ValueError):
            WordPair("same", "same", "greg", 0.5)
        
        # Test validation - invalid word format (contains numbers)
        with self.assertRaises(ValueError):
            WordPair("word1", "word2", "greg", 0.5)
        
        # Test validation - invalid word format (contains uppercase)  
        with self.assertRaises(ValueError):
            WordPair("Word", "word", "greg", 0.5)
    
    def test_database_caching(self):
        """Test root-word mapping cache functionality."""
        # Insert test data
        test_root = "test_root"
        test_words = ["gregarious", "aggregate", "congregation"]
        
        for word in test_words:
            success = self.bot.database.add_root_mapping(test_root, word)
            self.assertTrue(success)  # Should return True for new mappings
        
        # Check retrieval
        cached_words = self.bot.database.get_words_for_root(test_root)
        self.assertEqual(set(cached_words), set(test_words))
        
        # Test duplicate insertion (should be ignored)
        success = self.bot.database.add_root_mapping(test_root, "gregarious")
        self.assertFalse(success)  # Should return False for duplicate
    
    def test_posted_pairs_tracking(self):
        """Test posted pairs are properly tracked."""
        pair = WordPair("gregarious", "egregious", "greg", 0.5)
        
        # Initially not posted
        self.assertFalse(self.bot.database.is_pair_posted(pair.word1, pair.word2))
        
        # Record as posted
        success = self.bot.database.record_posted_pair(pair, "12345")
        self.assertTrue(success)  # Should return True for successful recording
        
        # Should now be marked as posted
        self.assertTrue(self.bot.database.is_pair_posted(pair.word1, pair.word2))
        # Should work in reverse order too
        self.assertTrue(self.bot.database.is_pair_posted(pair.word2, pair.word1))


class TestIntegration(unittest.TestCase):
    """Integration tests with mocked external services."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.temp_db.close()
        
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-openai-key-1234567890',
            'TWITTER_BEARER_TOKEN': 'test-bearer-token-1234567890',
            'TWITTER_CONSUMER_KEY': 'test-consumer-key-1234567890',
            'TWITTER_CONSUMER_SECRET': 'test-consumer-secret-1234567890',
            'TWITTER_ACCESS_TOKEN': 'test-access-token-1234567890',
            'TWITTER_ACCESS_TOKEN_SECRET': 'test-access-token-secret-1234567890'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up integration test fixtures."""
        self.env_patcher.stop()
        os.unlink(self.temp_db.name)
    
    @patch('etymobot.services.SentenceTransformer')
    @patch('etymobot.services.tweepy.Client')
    @patch('etymobot.services.openai.OpenAI')
    def test_full_cycle_mock(self, mock_openai, mock_tweepy, mock_transformer):
        """Test complete posting cycle with mocked services."""
        # Set up mocks
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2], [0.8, 0.9]]  # Different embeddings
        mock_transformer.return_value = mock_model
        
        # Mock cosine similarity to return low similarity (high divergence)
        with patch('etymobot.services.util.cos_sim') as mock_cos_sim:
            mock_cos_sim.return_value = Mock()
            mock_cos_sim.return_value.item.return_value = 0.2  # Low similarity = high divergence
            
            # Mock OpenAI response
            mock_openai_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "Test tweet content about etymology"
            mock_openai_client.chat.completions.create.return_value = mock_response
            # Mock API validation
            mock_openai_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_openai_client
            
            # Mock Twitter response
            mock_twitter_client = Mock()
            mock_tweet_response = Mock()
            mock_tweet_response.data = {'id': '12345'}
            mock_twitter_client.create_tweet.return_value = mock_tweet_response
            # Mock credentials validation
            mock_me_response = Mock()
            mock_me_response.data = Mock()
            mock_me_response.data.username = "test_user"
            mock_twitter_client.get_me.return_value = mock_me_response
            mock_tweepy.return_value = mock_twitter_client
            
            # Create config and bot
            config = Config.from_env()
            config.db_path = self.temp_db.name
            
            with EtymoBot(config) as bot:
                # Insert test root mappings
                test_pairs = [
                    ("greg", "gregarious"),
                    ("greg", "egregious")
                ]
                
                for root, word in test_pairs:
                    bot.database.add_root_mapping(root, word)
                bot.database.commit()
                
                # Run single cycle
                success = bot.run_single_cycle()
                
                # Verify success
                self.assertTrue(success)
                
                # Verify tweet was generated
                mock_openai_client.chat.completions.create.assert_called()
                
                # Verify tweet was posted
                mock_twitter_client.create_tweet.assert_called_once()
                
                # Verify posted pair was recorded
                posted_count = bot.database.cursor.execute("SELECT COUNT(*) FROM posted").fetchone()[0]
                self.assertEqual(posted_count, 1)


if __name__ == '__main__':
    unittest.main() 