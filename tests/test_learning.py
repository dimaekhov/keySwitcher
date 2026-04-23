import tempfile
import time
import unittest
from pathlib import Path

from keyswitcher.exceptions import TypoExceptionStore
from keyswitcher.learning import LearnedCorrection, LearningStore


class LearningStoreTests(unittest.TestCase):
    def test_learns_and_reloads_manual_correction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learning.json"
            store = LearningStore(path)
            learned = store.learn("ыгзук", "super", "en")
            self.assertIsNotNone(learned)

            reloaded = LearningStore(path)
            found = reloaded.find("ЫГЗУК")
            self.assertIsNotNone(found)
            self.assertEqual(found.replacement, "super")
            self.assertEqual(found.target_language, "en")

    def test_ignores_same_word_learning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LearningStore(Path(tmp) / "learning.json")
            self.assertIsNone(store.learn("hello", "hello", "en"))

    def test_ensures_and_reloads_rules_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learning.json"
            store = LearningStore(path)
            self.assertEqual(store.ensure_file(), path)
            self.assertTrue(path.exists())
            self.assertEqual(store.reload(), 0)

    def test_replace_all_rewrites_rules_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learning.json"
            store = LearningStore(path)
            store.replace_all(
                [
                    LearnedCorrection(
                        actual="ghbdtn",
                        replacement="привет",
                        target_language="ru",
                        count=3,
                        updated_at=123.0,
                    ),
                    LearnedCorrection(
                        actual="руддщ",
                        replacement="hello",
                        target_language="en",
                        count=2,
                        updated_at=456.0,
                    ),
                ]
            )

            reloaded = LearningStore(path)
            items = reloaded.items()

            self.assertEqual(len(items), 2)
            self.assertEqual(items[0].actual, "ghbdtn")
            self.assertEqual(items[0].replacement, "привет")
            self.assertEqual(items[0].count, 3)
            self.assertEqual(items[1].actual, "руддщ")

    def test_reload_if_changed_detects_external_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "learning.json"
            first = LearningStore(path)
            first.replace_all(
                [
                    LearnedCorrection(
                        actual="ghbdtn",
                        replacement="привет",
                        target_language="ru",
                        count=1,
                        updated_at=1.0,
                    )
                ]
            )

            second = LearningStore(path)
            self.assertIsNone(second.reload_if_changed())

            time.sleep(0.01)
            first.replace_all(
                [
                    LearnedCorrection(
                        actual="руддщ",
                        replacement="hello",
                        target_language="en",
                        count=2,
                        updated_at=2.0,
                    )
                ]
            )

            self.assertEqual(second.reload_if_changed(), 1)
            found = second.find("руддщ")
            self.assertIsNotNone(found)
            self.assertEqual(found.replacement, "hello")


class TypoExceptionStoreTests(unittest.TestCase):
    def test_ensures_default_exception_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "exceptions.json"
            store = TypoExceptionStore(path)
            self.assertEqual(store.ensure_file(), path)
            self.assertIn("less", store.suffixes())

    def test_replace_all_normalizes_words_and_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "exceptions.json"
            store = TypoExceptionStore(path)
            store.replace_all(["Shellless", "Bookkeeper"], ["-less", "NESS"])

            reloaded = TypoExceptionStore(path)
            snapshot = reloaded.snapshot()

            self.assertTrue(snapshot.matches("shellless"))
            self.assertTrue(snapshot.matches("carelessness"))
            self.assertIn("bookkeeper", reloaded.words())
            self.assertIn("less", reloaded.suffixes())
            self.assertIn("ness", reloaded.suffixes())


if __name__ == "__main__":
    unittest.main()
