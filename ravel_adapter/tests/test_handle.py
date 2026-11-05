"""Unit tests for ravel_adapter.ravel — command parsing, mention stripping, formatting.

Mock subprocess.run so nothing runs Ravel or git for real.
"""
import sys
from pathlib import Path

import pytest

# Make sure the adapter package is importable without installing it.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ravel_adapter.ravel import strip_mention


# ── strip_mention ────────────────────────────────────────────────────

class TestStripMention:
    def test_removes_leading_at_ravel(self):
        assert strip_mention("@ravel check app.py:search") == "check app.py:search"

    def test_case_insensitive(self):
        assert strip_mention("@Ravel check x") == "check x"
        assert strip_mention("@RAVEL help") == "help"

    def test_with_colon_after_name(self):
        assert strip_mention("@ravel: help") == "help"

    def test_with_comma_after_name(self):
        assert strip_mention("@ravel, check x:y") == "check x:y"

    def test_no_mention_returns_text(self):
        assert strip_mention("check app.py:search") == "check app.py:search"

    def test_empty_string(self):
        assert strip_mention("") == ""

    def test_only_mention(self):
        assert strip_mention("@ravel") == ""

    def test_extra_whitespace(self):
        assert strip_mention("  @ravel   check x:y  ") == "check x:y"

    def test_custom_names(self):
        assert strip_mention("@bot help", names=("bot",)) == "help"
        assert strip_mention("@ravel help", names=("bot",)) == "@ravel help"

    def test_mention_mid_text_is_kept(self):
        """A mention in the middle is not stripped — only leading ones."""
        assert strip_mention("hello @ravel check") == "hello @ravel check"
