#!/usr/bin/env python3
"""
Test suite for stylistic variation templates.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from etymobot.services import OpenAIService
from etymobot.config import Config
from etymobot.models import WordPair


class TestStylisticVariation(unittest.TestCase):
    """Test cases for stylistic variation in tweet generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables with enhanced validation-compliant keys
        self.env_patcher = patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-openai-key-1234567890',
            'TWITTER_BEARER_TOKEN': 'test-bearer-token-1234567890',
            'TWITTER_CONSUMER_KEY': 'test-consumer-key-1234567890', 
            'TWITTER_CONSUMER_SECRET': 'test-consumer-secret-1234567890',
            'TWITTER_ACCESS_TOKEN': 'test-access-token-1234567890',
            'TWITTER_ACCESS_TOKEN_SECRET': 'test-access-token-secret-1234567890'
        })
        self.env_patcher.start()
        
        # Create config and service
        self.config = Config.from_env()
        
        # Mock OpenAI client
        with patch('etymobot.services.openai.OpenAI'):
            self.service = OpenAIService(self.config)
        
        # Test word pair
        self.pair = WordPair("gregarious", "egregious", "greg", 0.75)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()
    
    def test_template_count(self):
        """Test that we have the expected number of templates."""
        self.assertEqual(len(self.service.templates), 5)
    
    def test_statement_twist_template(self):
        """Test the Statement + Twist template."""
        prompt = self.service._statement_twist_template(self.pair)
        
        # Check template structure
        self.assertIn("gregarious born of greg", prompt)
        self.assertIn("Brief divergence narrative", prompt)
        self.assertIn("Final reflection", prompt)
        self.assertIn("strong verbs and concrete nouns", prompt)
        self.assertIn("No emojis or hashtags", prompt)
    
    def test_question_hook_template(self):
        """Test the Question Hook template."""
        prompt = self.service._question_hook_template(self.pair)
        
        # Check template structure
        self.assertIn("Ever wondered why gregarious and egregious both echo greg?", prompt)
        self.assertIn("Divergence + concrete image", prompt)
        self.assertIn("Invitation to ponder", prompt)
        self.assertIn("conversational and curious", prompt)
    
    def test_mini_anecdote_template(self):
        """Test the Mini Anecdote template."""
        prompt = self.service._mini_anecdote_template(self.pair)
        
        # Check template structure
        self.assertIn("In ancient times, greg meant", prompt)
        self.assertIn("the seed of gregarious and egregious", prompt)
        self.assertIn("Contrast", prompt)
        self.assertIn("Aphoristic close", prompt)
    
    def test_fragment_aside_template(self):
        """Test the Fragment & Aside template."""
        prompt = self.service._fragment_aside_template(self.pair)
        
        # Check template structure
        self.assertIn("gregarious & egregious—rooted in greg", prompt)
        self.assertIn("One <short metaphor>, the other <short metaphor>", prompt)
        self.assertIn("sensory aside", prompt)
        self.assertIn("Question or insight", prompt)
    
    def test_oneliner_aphorism_template(self):
        """Test the One-Liner Aphorism template."""
        prompt = self.service._oneliner_aphorism_template(self.pair)
        
        # Check template structure
        self.assertIn("gregarious/egregious:", prompt)
        self.assertIn("One-sentence distillation", prompt)
        self.assertIn("irony, contrast, or surprising connection", prompt)
        self.assertIn("quotable and memorable", prompt)
    
    def test_template_randomization(self):
        """Test that different templates are selected randomly."""
        # Mock random.choice to control selection
        selected_templates = []
        original_choice = self.service.generate_tweet
        
        def mock_choice(templates):
            func = templates[len(selected_templates) % len(templates)]
            selected_templates.append(func.__name__)
            return func
        
        with patch('etymobot.services.random.choice', side_effect=mock_choice):
            # Mock OpenAI response
            with patch.object(self.service.client.chat.completions, 'create') as mock_create:
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message = Mock()
                mock_response.choices[0].message.content = "Test tweet content"
                mock_create.return_value = mock_response
                
                # Generate several tweets
                for i in range(5):
                    self.service.generate_tweet(self.pair)
        
        # Should have used all 5 different templates
        self.assertEqual(len(set(selected_templates)), 5)
        expected_templates = [
            '_statement_twist_template',
            '_question_hook_template', 
            '_mini_anecdote_template',
            '_fragment_aside_template',
            '_oneliner_aphorism_template'
        ]
        self.assertEqual(set(selected_templates), set(expected_templates))
    
    def test_all_templates_produce_valid_prompts(self):
        """Test that all templates produce valid prompts with required elements."""
        for template_func in self.service.templates:
            prompt = template_func(self.pair)
            
            # Each prompt should include the word pair and root
            self.assertIn("gregarious", prompt)
            self.assertIn("egregious", prompt) 
            self.assertIn("greg", prompt)
            
            # Should have guidelines
            self.assertIn("Guidelines:", prompt)
            self.assertIn("280 characters", prompt)
            self.assertIn("No emojis or hashtags", prompt)
            
            # Should be substantial content
            self.assertGreater(len(prompt), 200)


if __name__ == '__main__':
    unittest.main() 