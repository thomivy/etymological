"""
EtymoBot - Automated Etymology Discovery and Twitter Posting Bot

A Python package for discovering semantically divergent word pairs
sharing ancient roots and posting engaging tweets about their
etymological connections.
"""

__version__ = "1.0.0"
__author__ = "EtymoBot Project"
__email__ = "contact@etymobot.dev"

from .bot import EtymoBot
from .models import WordPair
from .config import Config

__all__ = ["EtymoBot", "WordPair", "Config"]
