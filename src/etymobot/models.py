"""Data models for EtymoBot."""

from dataclasses import dataclass
from typing import Tuple
import re


@dataclass
class WordPair:
    """Represents a word pair with shared etymology."""
    word1: str
    word2: str
    root: str
    divergence_score: float

    def __post_init__(self):
        """Validate word pair data after initialization."""
        self._validate_words()
        self._validate_root()
        self._validate_divergence_score()

    def _validate_words(self) -> None:
        """Validate that words are valid."""
        for word_name, word in [("word1", self.word1), ("word2", self.word2)]:
            if not word or not isinstance(word, str):
                raise ValueError(f"{word_name} must be a non-empty string")

            word = word.strip().lower()
            if len(word) < 2:
                raise ValueError(f"{word_name} must be at least 2 characters long")

            if not re.match(r'^[a-z]+$', word):
                raise ValueError(f"{word_name} must contain only lowercase letters")

        # Normalize words to lowercase
        self.word1 = self.word1.strip().lower()
        self.word2 = self.word2.strip().lower()

        # Ensure words are different
        if self.word1 == self.word2:
            raise ValueError("word1 and word2 must be different")

    def _validate_root(self) -> None:
        """Validate that root is valid."""
        if not self.root or not isinstance(self.root, str):
            raise ValueError("root must be a non-empty string")

        root = self.root.strip().lower()
        if len(root) < 2:
            raise ValueError("root must be at least 2 characters long")

        if not re.match(r'^[a-z\-]+$', root):
            raise ValueError("root must contain only lowercase letters and hyphens")

        # Normalize root
        self.root = root

    def _validate_divergence_score(self) -> None:
        """Validate that divergence score is valid."""
        if not isinstance(self.divergence_score, (int, float)):
            raise ValueError("divergence_score must be a number")

        if not (0.0 <= self.divergence_score <= 1.0):
            raise ValueError("divergence_score must be between 0.0 and 1.0")

    def __str__(self) -> str:
        return f"{
            self.word1} & {
            self.word2} (root: {
            self.root}, divergence: {
                self.divergence_score:.3f})"

    @property
    def ordered_pair(self) -> Tuple[str, str]:
        """Return words in alphabetical order for consistent comparison."""
        return tuple(sorted([self.word1, self.word2]))

    @property
    def similarity_score(self) -> float:
        """Return semantic similarity (inverse of divergence)."""
        return 1.0 - self.divergence_score

    def is_highly_divergent(self, threshold: float = 0.7) -> bool:
        """Check if the word pair is highly semantically divergent."""
        return self.divergence_score >= threshold

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "word1": self.word1,
            "word2": self.word2,
            "root": self.root,
            "divergence_score": self.divergence_score
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WordPair":
        """Create WordPair from dictionary."""
        required_fields = ["word1", "word2", "root", "divergence_score"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        return cls(
            word1=data["word1"],
            word2=data["word2"],
            root=data["root"],
            divergence_score=data["divergence_score"]
        )
