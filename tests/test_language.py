import unittest

from keyswitcher.config import AppConfig
from keyswitcher.language import (
    ContextAwareDetector,
    SentenceContext,
    convert_layout_text,
    convert_layout_text_preserving_punctuation,
    layout_punctuation_replacement,
    resolve_context_entry,
    should_lowercase_common_word,
)


class LanguageDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = ContextAwareDetector(AppConfig())

    def test_switches_english_keys_to_russian_word(self) -> None:
        result = self.detector.detect("ghbdtn", "привет", "en", SentenceContext())
        self.assertTrue(result.should_correct)
        self.assertEqual(result.target_language, "ru")
        self.assertEqual(result.replacement, "привет")

    def test_switches_russian_keys_to_english_word(self) -> None:
        result = self.detector.detect("руддщ", "hello", "ru", SentenceContext())
        self.assertTrue(result.should_correct)
        self.assertEqual(result.target_language, "en")
        self.assertEqual(result.replacement, "hello")

    def test_keeps_valid_english_word(self) -> None:
        result = self.detector.detect("hello", convert_layout_text("hello", "ru"), "en", SentenceContext())
        self.assertFalse(result.should_correct)

    def test_detects_adjacent_transposition_in_common_word(self) -> None:
        result = self.detector.detect_transposed_letters("hlelo", "en", SentenceContext())
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.replacement, "hello")

    def test_keeps_valid_word_without_transposition_fix(self) -> None:
        self.assertIsNone(self.detector.detect_transposed_letters("hello", "en", SentenceContext()))

    def test_fixes_tripled_consonant_run_inside_word(self) -> None:
        result = self.detector.detect_repeated_consonants("bookkkeeper", "en", SentenceContext())
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.replacement, "bookkeeper")

    def test_skips_tripled_consonant_fix_for_protected_suffix(self) -> None:
        result = self.detector.detect_repeated_consonants(
            "shellless",
            "en",
            SentenceContext(),
            protected_suffixes=("less",),
        )
        self.assertIsNone(result)

    def test_context_supports_sentence_language(self) -> None:
        context = SentenceContext()
        context.add_word("нужно", "ru")
        context.add_word("собрать", "ru")
        result = self.detector.detect("rjn", "кот", "en", context)
        self.assertTrue(result.should_correct)
        self.assertEqual(result.target_language, "ru")
        self.assertEqual(context.preferred_language(), "ru")

    def test_handles_punctuation_keys_that_are_russian_letters(self) -> None:
        result = self.detector.detect("gk.c", "плюс", "en", SentenceContext())
        self.assertTrue(result.should_correct)
        self.assertEqual(result.replacement, "плюс")

    def test_selected_conversion_preserves_sentence_punctuation_after_word(self) -> None:
        self.assertEqual(
            convert_layout_text_preserving_punctuation("ghbdtn.", "ru"),
            convert_layout_text("ghbdtn", "ru") + ".",
        )
        self.assertEqual(
            convert_layout_text_preserving_punctuation(convert_layout_text("hello", "ru") + "!", "en"),
            "hello!",
        )

    def test_selected_conversion_keeps_letter_punctuation_inside_word(self) -> None:
        self.assertEqual(
            convert_layout_text_preserving_punctuation("gk.c", "ru"),
            convert_layout_text("gk.c", "ru"),
        )

    def test_corrects_short_technical_token_to_latin(self) -> None:
        context = SentenceContext()
        context.add_word("привет", "ru")
        context.add_word("мир", "ru")
        result = self.detector.detect("3В", "3D", "ru", context)
        self.assertTrue(result.should_correct)
        self.assertEqual(result.target_language, "en")
        self.assertEqual(result.replacement, "3D")

    def test_keeps_latin_technical_token(self) -> None:
        context = SentenceContext()
        context.add_word("привет", "ru")
        context.add_word("мир", "ru")
        result = self.detector.detect("3D", "3В", "en", context)
        self.assertFalse(result.should_correct)

    def test_corrects_english_insert_inside_russian_sentence(self) -> None:
        context = SentenceContext()
        context.add_word("отлично", "ru")
        context.add_word("работает", "ru")
        result = self.detector.detect("ыгзук", "super", "ru", context)
        self.assertTrue(result.should_correct)
        self.assertEqual(result.target_language, "en")
        self.assertEqual(result.replacement, "super")

    def test_lowercases_known_common_word_inside_sentence(self) -> None:
        context = SentenceContext()
        context.add_word("отлично", "ru")
        self.assertTrue(should_lowercase_common_word("Работает", "ru", context))

    def test_keeps_unknown_capitalized_word_inside_sentence(self) -> None:
        context = SentenceContext()
        context.add_word("привет", "ru")
        self.assertFalse(should_lowercase_common_word("Иван", "ru", context))

    def test_replaces_last_context_word_after_manual_fix(self) -> None:
        context = SentenceContext()
        context.add_word("ыгзук", "ru")
        context.replace_last_word("super", "en")
        self.assertEqual(context.recent[-1], ("super", "en"))

    def test_corrects_ampersand_to_question_mark_in_russian_context(self) -> None:
        context = SentenceContext()
        for word, language in [
            ("ты", "ru"),
            ("смотришь", "ru"),
            ("одно", "ru"),
            ("sentence", "en"),
            ("или", "ru"),
            ("весь", "ru"),
            ("text", "en"),
        ]:
            context.add_word(word, language)
        self.assertEqual(layout_punctuation_replacement("&", "?", "en", context), ("?", "ru"))

    def test_keeps_ampersand_in_english_context(self) -> None:
        context = SentenceContext()
        context.add_word("text", "en")
        context.add_word("and", "en")
        self.assertIsNone(layout_punctuation_replacement("&", "?", "en", context))

    def test_repeats_ampersand_question_mark_fix_without_context(self) -> None:
        self.assertEqual(
            layout_punctuation_replacement("&", "?", "en", SentenceContext(), allow_repeat=True),
            ("?", "ru"),
        )

    def test_ignores_urls_and_code_like_tokens(self) -> None:
        result = self.detector.detect("example.com", "учфьздуюсщь", "en", SentenceContext())
        self.assertFalse(result.should_correct)

    def test_resolves_short_wrong_layout_token_for_context(self) -> None:
        entry = resolve_context_entry("ns", convert_layout_text("ns", "ru"), "en", self.detector, SentenceContext())
        self.assertEqual(entry, (convert_layout_text("ns", "ru"), "ru"))

    def test_short_wrong_layout_context_enables_following_russian_detection(self) -> None:
        context = SentenceContext()
        for actual in ("f", "ns"):
            entry = resolve_context_entry(actual, convert_layout_text(actual, "ru"), "en", self.detector, context)
            self.assertIsNotNone(entry)
            context.add_word(*entry)

        result = self.detector.detect("fyfkbpbhetim", convert_layout_text("fyfkbpbhetim", "ru"), "en", context)
        self.assertTrue(result.should_correct)
        self.assertEqual(result.target_language, "ru")

if __name__ == "__main__":
    unittest.main()
