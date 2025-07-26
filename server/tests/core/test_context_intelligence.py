"""
Test suite for context intelligence functionality.

Tests file relevance scoring, context analysis, ranking, and project intelligence
with comprehensive coverage of all scoring methods and edge cases.
"""

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config.conversation_config import (
    CONTEXT_FILE_SIZE_ACCEPTABLE_MAX,
    CONTEXT_FILE_SIZE_OPTIMAL_MAX,
)
from src.config.core_constants import CONTEXT_MIN_SCORE
from src.config.weights import WeightsManager
from src.core.context_intelligence import (
    ContextIntelligence,
    _context_cache,
    get_context_intelligence,
)


class TestContextIntelligence(unittest.TestCase):
    """Test ContextIntelligence class functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.weights = WeightsManager.get_default()
        self.context_intel = ContextIntelligence(self.project_root, self.weights)

        _context_cache.clear()

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
        _context_cache.clear()

    def test_init(self):
        """Test ContextIntelligence initialization."""
        self.assertEqual(self.context_intel.project_root, self.project_root)
        self.assertIsNotNone(self.context_intel.git_tracker)
        self.assertIsInstance(self.context_intel._import_cache, dict)

    def test_score_file_relevance_nonexistent_file(self):
        """Test scoring a file that doesn't exist."""
        score = self.context_intel.score_file_relevance("nonexistent.py")
        self.assertEqual(score, CONTEXT_MIN_SCORE)

    def test_score_file_relevance_existing_file(self):
        """Test scoring an existing file."""
        test_file = self.project_root / "test.py"
        test_file.write_text("# Test file")

        score = self.context_intel.score_file_relevance("test.py")
        self.assertGreaterEqual(score, CONTEXT_MIN_SCORE)

    def test_score_file_relevance_with_context(self):
        """Test scoring with context information."""
        test_file = self.project_root / "main.py"
        test_file.write_text("# Main file")

        context = {"active_files": ["app.py", "main.py"]}
        score = self.context_intel.score_file_relevance("main.py", context)
        self.assertGreaterEqual(score, CONTEXT_MIN_SCORE)

    def test_score_file_relevance_exception_handling(self):
        """Test exception handling in file relevance scoring."""
        with patch.object(Path, "exists", side_effect=OSError("Permission denied")):
            score = self.context_intel.score_file_relevance("test.py")
            self.assertEqual(score, CONTEXT_MIN_SCORE)


class TestScoreRecentModification(unittest.TestCase):
    """Test recent modification scoring."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.weights = WeightsManager.get_default()
        self.context_intel = ContextIntelligence(self.project_root, self.weights)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_score_recent_file(self):
        """Test scoring a recently modified file."""
        test_file = self.project_root / "recent.py"
        test_file.write_text("# Recent file")

        score = self.context_intel._score_recent_modification(test_file)
        self.assertGreater(score, CONTEXT_MIN_SCORE)

    def test_score_old_file(self):
        """Test scoring an old file."""
        test_file = self.project_root / "old.py"
        test_file.write_text("# Old file")

        # Mock an old modification time
        week_threshold = self.weights.get("context.recent_modifications.week_threshold")
        old_time = time.time() - (week_threshold + 1) * 3600
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_mtime = old_time
            score = self.context_intel._score_recent_modification(test_file)
            self.assertEqual(score, CONTEXT_MIN_SCORE)

    def test_score_day_old_file(self):
        """Test scoring a day-old file."""
        test_file = self.project_root / "day_old.py"
        test_file.write_text("# Day old file")

        # Use a time that falls between day and week thresholds
        day_old_time = time.time() - 25 * 3600  # 25 hours ago
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_mtime = day_old_time
            score = self.context_intel._score_recent_modification(test_file)
            # Based on the actual logic, 25 hours falls into week threshold
            expected = self.weights.get(
                "weights.recent_modification", CONTEXT_MIN_SCORE
            ) * self.weights.get("context.recent_modifications.week_multiplier")
            self.assertAlmostEqual(score, expected, places=2)

    def test_score_week_old_file(self):
        """Test scoring a week-old file."""
        test_file = self.project_root / "week_old.py"
        test_file.write_text("# Week old file")

        # Use a time that falls in the "week old" range
        week_threshold = self.weights.get("context.recent_modifications.week_threshold")
        week_old_time = time.time() - (week_threshold - 24) * 3600
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_mtime = week_old_time
            score = self.context_intel._score_recent_modification(test_file)
            expected = self.weights.get(
                "weights.recent_modification", CONTEXT_MIN_SCORE
            ) * self.weights.get("context.recent_modifications.week_multiplier")
            self.assertAlmostEqual(score, expected, places=2)

    def test_score_file_stat_error(self):
        """Test handling of file stat errors."""
        test_file = self.project_root / "error.py"

        with patch.object(Path, "stat", side_effect=OSError("Permission denied")):
            score = self.context_intel._score_recent_modification(test_file)
            self.assertEqual(score, CONTEXT_MIN_SCORE)

    def test_score_few_hours_old_file(self):
        """Test scoring a file that's a few hours old (in day threshold range)."""
        test_file = self.project_root / "few_hours_old.py"
        test_file.write_text("# Few hours old file")

        # Use a time that falls between hour and day thresholds (e.g., 6 hours ago)
        few_hours_old_time = time.time() - 6 * 3600  # 6 hours ago
        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_mtime = few_hours_old_time
            score = self.context_intel._score_recent_modification(test_file)
            # Should use day multiplier
            expected = self.weights.get(
                "weights.recent_modification", CONTEXT_MIN_SCORE
            ) * self.weights.get("context.recent_modifications.day_multiplier")
            self.assertAlmostEqual(score, expected, places=2)


class TestScoreFileSize(unittest.TestCase):
    """Test file size scoring."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.weights = WeightsManager.get_default()
        self.context_intel = ContextIntelligence(self.project_root, self.weights)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_score_optimal_size_file(self):
        """Test scoring a file with optimal size."""
        test_file = self.project_root / "optimal.py"
        optimal_min = self.weights.get("context.file_size.optimal_min")
        content = "# " + "x" * (optimal_min + 100)
        test_file.write_text(content)

        score = self.context_intel._score_file_size(test_file)
        self.assertEqual(
            score,
            self.weights.get("weights.file_size_optimal", CONTEXT_MIN_SCORE),
        )

    def test_score_acceptable_size_file(self):
        """Test scoring a file with acceptable size."""
        test_file = self.project_root / "acceptable.py"
        optimal_max = self.weights.get("context.file_size.optimal_max")
        content = "# " + "x" * (optimal_max + 100)
        test_file.write_text(content)

        score = self.context_intel._score_file_size(test_file)
        expected = self.weights.get(
            "weights.file_size_optimal", CONTEXT_MIN_SCORE
        ) * self.weights.get("context.file_size.acceptable_multiplier")
        self.assertEqual(score, expected)

    def test_score_large_file(self):
        """Test scoring a large file."""
        test_file = self.project_root / "large.py"

        with patch.object(Path, "stat") as mock_stat:
            mock_stat.return_value.st_size = CONTEXT_FILE_SIZE_ACCEPTABLE_MAX + 1000
            score = self.context_intel._score_file_size(test_file)
            expected = self.weights.get(
                "weights.file_size_optimal", CONTEXT_MIN_SCORE
            ) * self.weights.get("context.file_size.large_multiplier")
            self.assertEqual(score, expected)

    def test_score_tiny_file(self):
        """Test scoring a very small file."""
        test_file = self.project_root / "tiny.py"
        test_file.write_text("#")

        score = self.context_intel._score_file_size(test_file)
        self.assertEqual(score, CONTEXT_MIN_SCORE)

    def test_score_file_size_error(self):
        """Test handling of file size errors."""
        test_file = self.project_root / "error.py"

        with patch.object(
            Path, "stat", side_effect=FileNotFoundError("File not found")
        ):
            score = self.context_intel._score_file_size(test_file)
            self.assertEqual(score, CONTEXT_MIN_SCORE)


class TestScoreFileType(unittest.TestCase):
    """Test file type scoring."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.weights = WeightsManager.get_default()
        self.context_intel = ContextIntelligence(self.project_root, self.weights)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_score_python_file(self):
        """Test scoring a Python file."""
        score = self.context_intel._score_file_type("main.py")
        self.assertGreater(score, CONTEXT_MIN_SCORE)

    def test_score_javascript_file(self):
        """Test scoring a JavaScript file."""
        score = self.context_intel._score_file_type("app.js")
        self.assertGreater(score, CONTEXT_MIN_SCORE)

    def test_score_no_extension(self):
        """Test scoring a file with no extension."""
        score = self.context_intel._score_file_type("README")
        expected = CONTEXT_MIN_SCORE * self.weights.get(
            "weights.file_type_priority", CONTEXT_MIN_SCORE
        )
        self.assertEqual(score, expected)

    def test_score_unknown_file_type(self):
        """Test scoring an unknown file type."""
        score = self.context_intel._score_file_type("file.unknown")
        # Should get minimum score for unknown extension
        expected = CONTEXT_MIN_SCORE * self.weights.get(
            "weights.file_type_priority", CONTEXT_MIN_SCORE
        )
        self.assertEqual(score, expected)


class TestScoreDirectoryImportance(unittest.TestCase):
    """Test directory importance scoring."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.weights = WeightsManager.get_default()
        self.context_intel = ContextIntelligence(self.project_root, self.weights)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_score_src_directory(self):
        """Test scoring a file in src directory."""
        score = self.context_intel._score_directory_importance("src/main.py")
        # The score should be greater than or equal to CONTEXT_MIN_SCORE
        self.assertGreaterEqual(score, CONTEXT_MIN_SCORE)

    def test_score_nested_directories(self):
        """Test scoring a file in nested directories."""
        score = self.context_intel._score_directory_importance("src/core/main.py")
        # Should accumulate scores from multiple directories, so cool
        self.assertGreater(score, CONTEXT_MIN_SCORE)

    def test_score_root_file(self):
        """Test scoring a file in project root."""
        score = self.context_intel._score_directory_importance("main.py")
        self.assertEqual(score, 0.0)

    def test_score_unknown_directory(self):
        """Test scoring a file in unknown directory."""
        score = self.context_intel._score_directory_importance("unknown/file.py")
        expected = CONTEXT_MIN_SCORE * self.weights.get(
            "weights.directory_importance", CONTEXT_MIN_SCORE
        )
        self.assertEqual(score, expected)


class TestScoreGitActivity(unittest.TestCase):
    """Test git activity scoring."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.weights = WeightsManager.get_default()
        self.context_intel = ContextIntelligence(self.project_root, self.weights)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_score_git_activity_success(self):
        """Test successful git activity scoring."""
        with patch.object(
            self.context_intel.git_tracker,
            "get_activity_score",
            return_value=0.8,
        ):
            score = self.context_intel._score_git_activity("main.py")
            expected = 0.8 * self.weights.get("weights.git_activity", CONTEXT_MIN_SCORE)
            self.assertEqual(score, expected)

    def test_score_git_activity_no_activity(self):
        """Test git activity scoring with no activity."""
        with patch.object(
            self.context_intel.git_tracker,
            "get_activity_score",
            return_value=0.0,
        ):
            score = self.context_intel._score_git_activity("main.py")
            self.assertEqual(score, 0.0)

    def test_score_git_activity_error(self):
        """Test git activity scoring with error."""
        with patch.object(
            self.context_intel.git_tracker,
            "get_activity_score",
            side_effect=AttributeError("Error"),
        ):
            score = self.context_intel._score_git_activity("main.py")
            self.assertEqual(score, CONTEXT_MIN_SCORE)

    def test_score_git_activity_type_error(self):
        """Test git activity scoring with type error."""
        with patch.object(
            self.context_intel.git_tracker,
            "get_activity_score",
            side_effect=TypeError("Type error"),
        ):
            score = self.context_intel._score_git_activity("main.py")
            self.assertEqual(score, CONTEXT_MIN_SCORE)


class TestScoreImportRelationships(unittest.TestCase):
    """Test import relationship scoring."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.weights = WeightsManager.get_default()
        self.context_intel = ContextIntelligence(self.project_root, self.weights)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_score_no_active_files(self):
        """Test scoring with no active files."""
        score = self.context_intel._score_import_relationships("main.py", [])
        self.assertEqual(score, 0.0)

    def test_score_related_files(self):
        """Test scoring files with related names."""
        active_files = ["main_utils.py", "test_main.py"]
        score = self.context_intel._score_import_relationships("main.py", active_files)
        self.assertGreater(score, 0.0)

    def test_score_unrelated_files(self):
        """Test scoring files with unrelated names."""
        active_files = ["config.py", "database.py"]
        score = self.context_intel._score_import_relationships("main.py", active_files)
        self.assertEqual(score, 0.0)

    def test_score_same_file(self):
        """Test scoring the same file in active files."""
        active_files = ["main.py", "config.py"]
        score = self.context_intel._score_import_relationships("main.py", active_files)
        # Should not score relationship with itself
        self.assertEqual(score, 0.0)

    def test_score_multiple_relationships(self):
        """Test scoring with multiple related files."""
        active_files = ["main_utils.py", "main_config.py", "test_main.py"]
        score = self.context_intel._score_import_relationships("main.py", active_files)
        # Should be capped at 1.0
        self.assertLessEqual(score, 1.0)
        self.assertGreater(score, 0.0)

    def test_score_import_relationships_error(self):
        """Test error handling in import relationship scoring."""
        with patch("pathlib.Path.stem", side_effect=AttributeError("Error")):
            score = self.context_intel._score_import_relationships(
                "main.py", ["test.py"]
            )
            self.assertEqual(score, 0.0)

        # Test TypeError as well
        with patch("pathlib.Path.stem", side_effect=TypeError("Type error")):
            score = self.context_intel._score_import_relationships(
                "main.py", ["test.py"]
            )
            self.assertEqual(score, 0.0)


class TestRankFiles(unittest.TestCase):
    """Test file ranking functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.context_intel = ContextIntelligence(self.project_root)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_rank_empty_list(self):
        """Test ranking an empty file list."""
        ranked = self.context_intel.rank_files([])
        self.assertEqual(ranked, [])

    def test_rank_single_file(self):
        """Test ranking a single file."""
        test_file = self.project_root / "test.py"
        test_file.write_text("# Test file")

        ranked = self.context_intel.rank_files(["test.py"])
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0][0], "test.py")
        self.assertIsInstance(ranked[0][1], float)

    def test_rank_multiple_files(self):
        """Test ranking multiple files."""
        files = ["main.py", "config.py", "utils.py"]
        for file_name in files:
            (self.project_root / file_name).write_text(f"# {file_name}")

        ranked = self.context_intel.rank_files(files)
        self.assertEqual(len(ranked), 3)

        # Should be sorted by scor, descending
        scores = [score for _, score in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_rank_files_with_limit(self):
        """Test ranking files with result limit."""
        files = ["file1.py", "file2.py", "file3.py", "file4.py"]
        for file_name in files:
            (self.project_root / file_name).write_text(f"# {file_name}")

        ranked = self.context_intel.rank_files(files, limit=2)
        self.assertEqual(len(ranked), 2)

    def test_rank_files_with_context(self):
        """Test ranking files with context."""
        files = ["main.py", "utils.py"]
        for file_name in files:
            (self.project_root / file_name).write_text(f"# {file_name}")

        context = {"active_files": ["main.py"]}
        ranked = self.context_intel.rank_files(files, context)
        self.assertEqual(len(ranked), 2)


class TestGetContextSummary(unittest.TestCase):
    """Test context summary generation."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.context_intel = ContextIntelligence(self.project_root)

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_summary_empty_files(self):
        """Test summary generation with empty file list."""
        summary = self.context_intel.get_context_summary([])

        expected = {
            "file_count": 0,
            "priority_distribution": {"high": 0, "medium": 0, "low": 0},
            "file_type_distribution": {},
            "average_score": 0.0,
            "top_files": [],
        }

        self.assertEqual(summary["file_count"], expected["file_count"])
        self.assertEqual(
            summary["priority_distribution"], expected["priority_distribution"]
        )
        self.assertEqual(
            summary["file_type_distribution"],
            expected["file_type_distribution"],
        )
        self.assertEqual(summary["average_score"], expected["average_score"])
        self.assertEqual(summary["top_files"], expected["top_files"])

    def test_summary_with_files(self):
        """Test summary generation with files."""
        files = ["main.py", "config.json", "README.md"]
        for file_name in files:
            (self.project_root / file_name).write_text(f"# {file_name}")

        summary = self.context_intel.get_context_summary(files)

        self.assertEqual(summary["file_count"], 3)
        self.assertIn("total_files", summary)
        self.assertIn("high_priority_files", summary)
        self.assertIn("medium_priority_files", summary)
        self.assertIn("low_priority_files", summary)
        self.assertIn("average_score", summary)
        self.assertIn("top_files", summary)
        self.assertIn("file_type_distribution", summary)

    def test_summary_file_type_distribution(self):
        """Test file type distribution in summary."""
        files = ["main.py", "utils.py", "config.json", "README.md"]
        for file_name in files:
            (self.project_root / file_name).write_text(f"# {file_name}")

        summary = self.context_intel.get_context_summary(files)

        file_type_dist = summary["file_type_distribution"]
        self.assertEqual(file_type_dist[".py"], 2)
        self.assertEqual(file_type_dist[".json"], 1)
        self.assertEqual(file_type_dist[".md"], 1)

    def test_summary_priority_categorization(self):
        """Test priority categorization in summary."""
        files = ["test.py"]
        (self.project_root / "test.py").write_text("# Test file")

        summary = self.context_intel.get_context_summary(files)

        priority_dist = summary["priority_distribution"]
        total_priority = (
            priority_dist["high"] + priority_dist["medium"] + priority_dist["low"]
        )
        self.assertEqual(total_priority, 1)

    def test_summary_top_files_format(self):
        """Test top files format in summary."""
        files = ["main.py", "utils.py"]
        for file_name in files:
            (self.project_root / file_name).write_text(f"# {file_name}")

        summary = self.context_intel.get_context_summary(files)

        top_files = summary["top_files"]
        self.assertLessEqual(len(top_files), 10)  # CONTEXT_TOP_FILES_COUNT

        if top_files:
            # Check format: (path, score_string)
            path, score_str = top_files[0]
            self.assertIsInstance(path, str)
            self.assertIsInstance(score_str, str)
            # Should be formatted to 3 decimal places
            self.assertRegex(score_str, r"^\d+\.\d{3}$")


class TestGetContextIntelligence(unittest.TestCase):
    """Test module-level context intelligence function."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        _context_cache.clear()

    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
        _context_cache.clear()

    def test_get_context_intelligence_new(self):
        """Test getting context intelligence for new project."""
        context_intel = get_context_intelligence(self.project_root)

        self.assertIsInstance(context_intel, ContextIntelligence)
        self.assertEqual(context_intel.project_root, self.project_root)

        # Should be cached
        self.assertIn(str(self.project_root), _context_cache)

    def test_get_context_intelligence_cached(self):
        """Test getting cached context intelligence."""
        # First call
        context_intel1 = get_context_intelligence(self.project_root)

        # Second call should return same instance
        context_intel2 = get_context_intelligence(self.project_root)

        self.assertIs(context_intel1, context_intel2)

    def test_get_context_intelligence_different_projects(self):
        """Test getting context intelligence for different projects."""
        temp_dir2 = tempfile.TemporaryDirectory()
        project_root2 = Path(temp_dir2.name)

        try:
            context_intel1 = get_context_intelligence(self.project_root)
            context_intel2 = get_context_intelligence(project_root2)

            self.assertIsNot(context_intel1, context_intel2)
            self.assertEqual(len(_context_cache), 2)
        finally:
            temp_dir2.cleanup()


class TestConstants(unittest.TestCase):
    """Test module constants."""

    def test_constants_exist(self):
        """Test that required constants are defined."""
        self.assertIsInstance(CONTEXT_MIN_SCORE, (int, float))
        self.assertIsInstance(CONTEXT_FILE_SIZE_OPTIMAL_MAX, int)
        self.assertIsInstance(CONTEXT_FILE_SIZE_ACCEPTABLE_MAX, int)

    def test_constants_values(self):
        """Test that constants have reasonable values."""
        self.assertGreaterEqual(CONTEXT_MIN_SCORE, 0.0)
        self.assertGreater(CONTEXT_FILE_SIZE_OPTIMAL_MAX, 0)
        self.assertGreater(
            CONTEXT_FILE_SIZE_ACCEPTABLE_MAX, CONTEXT_FILE_SIZE_OPTIMAL_MAX
        )
