from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
import string
from typing import Literal

from .config import AppConfig

Language = Literal["en", "ru"]

EN_LETTERS = set(string.ascii_lowercase)
RU_LETTERS = set("абвгдежзийклмнопрстуфхцчшщъыьэюяё")
EN_VOWELS = set("aeiouy")
RU_VOWELS = set("аеёиоуыэюя")

EN_COMMON_WORDS = {
    "a",
    "about",
    "after",
    "again",
    "all",
    "also",
    "am",
    "an",
    "and",
    "any",
    "app",
    "are",
    "as",
    "at",
    "back",
    "be",
    "because",
    "been",
    "before",
    "but",
    "by",
    "can",
    "code",
    "context",
    "data",
    "day",
    "do",
    "does",
    "done",
    "each",
    "email",
    "error",
    "file",
    "for",
    "from",
    "get",
    "go",
    "good",
    "had",
    "has",
    "have",
    "he",
    "hello",
    "help",
    "her",
    "here",
    "him",
    "his",
    "how",
    "i",
    "if",
    "in",
    "input",
    "is",
    "it",
    "its",
    "key",
    "keyboard",
    "language",
    "layout",
    "like",
    "line",
    "make",
    "me",
    "message",
    "more",
    "my",
    "new",
    "no",
    "not",
    "now",
    "of",
    "ok",
    "on",
    "one",
    "or",
    "our",
    "out",
    "please",
    "project",
    "read",
    "right",
    "run",
    "same",
    "see",
    "send",
    "set",
    "she",
    "so",
    "some",
    "switch",
    "super",
    "test",
    "text",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "they",
    "this",
    "time",
    "to",
    "use",
    "user",
    "was",
    "we",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "word",
    "work",
    "would",
    "yes",
    "you",
    "your",
}

RU_COMMON_WORDS = {
    "а",
    "авто",
    "будет",
    "буду",
    "будем",
    "бы",
    "был",
    "была",
    "были",
    "было",
    "в",
    "вам",
    "вас",
    "ввод",
    "ввода",
    "ввести",
    "все",
    "всегда",
    "где",
    "да",
    "данные",
    "делать",
    "для",
    "до",
    "его",
    "ее",
    "если",
    "есть",
    "еще",
    "же",
    "за",
    "здесь",
    "и",
    "из",
    "или",
    "их",
    "как",
    "клавиатура",
    "клавиатуры",
    "код",
    "контекст",
    "контекста",
    "кот",
    "который",
    "куда",
    "ли",
    "мир",
    "мне",
    "можно",
    "мой",
    "мы",
    "на",
    "надо",
    "нам",
    "нас",
    "не",
    "него",
    "нее",
    "нет",
    "но",
    "нужно",
    "о",
    "он",
    "она",
    "они",
    "оно",
    "от",
    "очень",
    "по",
    "под",
    "пока",
    "поле",
    "после",
    "почему",
    "привет",
    "при",
    "проект",
    "просто",
    "плюс",
    "работает",
    "раз",
    "раскладка",
    "раскладку",
    "раскладки",
    "с",
    "сам",
    "сейчас",
    "слово",
    "слова",
    "собрать",
    "сообщение",
    "так",
    "также",
    "там",
    "текст",
    "ты",
    "у",
    "уже",
    "хорошо",
    "что",
    "чтобы",
    "это",
    "этот",
    "я",
}

EN_BIGRAMS = {
    "al",
    "an",
    "ar",
    "at",
    "be",
    "ch",
    "ck",
    "co",
    "de",
    "ed",
    "en",
    "er",
    "es",
    "ha",
    "he",
    "hi",
    "in",
    "io",
    "is",
    "it",
    "la",
    "le",
    "ll",
    "me",
    "nd",
    "ng",
    "nt",
    "on",
    "or",
    "ou",
    "re",
    "ro",
    "se",
    "st",
    "te",
    "th",
    "to",
    "ve",
    "wo",
}

RU_BIGRAMS = {
    "ав",
    "ал",
    "ан",
    "ас",
    "ва",
    "ве",
    "ви",
    "во",
    "го",
    "да",
    "де",
    "ди",
    "до",
    "ей",
    "ел",
    "ен",
    "ер",
    "ес",
    "ет",
    "за",
    "ие",
    "ий",
    "ин",
    "ка",
    "ки",
    "ко",
    "ла",
    "ле",
    "ли",
    "ло",
    "ль",
    "на",
    "не",
    "ни",
    "но",
    "ов",
    "ог",
    "од",
    "ой",
    "ол",
    "ом",
    "он",
    "ор",
    "ос",
    "от",
    "по",
    "пр",
    "ра",
    "ре",
    "ри",
    "ро",
    "ск",
    "сл",
    "ст",
    "та",
    "те",
    "ти",
    "то",
    "ый",
    "ть",
    "че",
    "чт",
}

EN_SUFFIXES = ("ing", "tion", "ment", "ness", "able", "less", "ed", "er", "ly", "s")
RU_SUFFIXES = (
    "ами",
    "ями",
    "ого",
    "ему",
    "ыми",
    "ими",
    "ает",
    "ить",
    "ать",
    "ешь",
    "ый",
    "ий",
    "ая",
    "ое",
    "ые",
    "ой",
    "ом",
    "ах",
    "ях",
)

EN_TO_RU = {
    "`": "ё",
    "@": "\"",
    "#": "№",
    "$": ";",
    "^": ":",
    "&": "?",
    "q": "й",
    "w": "ц",
    "e": "у",
    "r": "к",
    "t": "е",
    "y": "н",
    "u": "г",
    "i": "ш",
    "o": "щ",
    "p": "з",
    "[": "х",
    "]": "ъ",
    "a": "ф",
    "s": "ы",
    "d": "в",
    "f": "а",
    "g": "п",
    "h": "р",
    "j": "о",
    "k": "л",
    "l": "д",
    ";": "ж",
    "'": "э",
    "z": "я",
    "x": "ч",
    "c": "с",
    "v": "м",
    "b": "и",
    "n": "т",
    "m": "ь",
    ",": "б",
    ".": "ю",
}

RU_TO_EN = {value: key for key, value in EN_TO_RU.items()}

for en, ru in list(EN_TO_RU.items()):
    if en.isalpha():
        EN_TO_RU[en.upper()] = ru.upper()
        RU_TO_EN[ru.upper()] = en.upper()

LAYOUT_PUNCTUATION_FIXES: dict[tuple[Language, str], tuple[str, Language]] = {
    ("en", "&"): ("?", "ru"),
}


@dataclass(slots=True)
class SentenceContext:
    recent: list[tuple[str, Language]] = field(default_factory=list)

    def add_word(self, word: str, language: Language) -> None:
        clean = normalize_word(word)
        if not clean:
            return
        self.recent.append((clean, language))
        if len(self.recent) > 12:
            del self.recent[:-12]

    def replace_last_word(self, word: str, language: Language) -> None:
        clean = normalize_word(word)
        if not clean:
            return
        if not self.recent:
            self.add_word(word, language)
            return
        self.recent[-1] = (clean, language)

    def reset_sentence(self) -> None:
        self.recent.clear()

    def language_bias(self, language: Language, weight: float) -> float:
        if not self.recent:
            return 0.0
        same = sum(1 for _, lang in self.recent[-8:] if lang == language)
        other = sum(1 for _, lang in self.recent[-8:] if lang != language)
        return max(-2.5, min(2.5, (same - other) * weight))

    def preferred_language(self) -> Language | None:
        if not self.recent:
            return None
        ru = sum(1 for _, lang in self.recent[-8:] if lang == "ru")
        en = sum(1 for _, lang in self.recent[-8:] if lang == "en")
        if abs(ru - en) < 2:
            return None
        return "ru" if ru > en else "en"

    def language_counts(self, window: int = 8) -> dict[Language, int]:
        recent = self.recent[-window:]
        return {
            "ru": sum(1 for _, lang in recent if lang == "ru"),
            "en": sum(1 for _, lang in recent if lang == "en"),
        }


@dataclass(slots=True)
class CandidateScore:
    text: str
    language: Language
    score: float
    reasons: list[str]


@dataclass(slots=True)
class DetectionResult:
    should_correct: bool
    target_language: Language
    replacement: str
    confidence: float
    actual: CandidateScore
    alternate: CandidateScore
    reason: str


@dataclass(slots=True)
class InLayoutCorrection:
    replacement: str
    confidence: float
    reason: str


def opposite_language(language: Language) -> Language:
    return "ru" if language == "en" else "en"


def convert_layout_text(text: str, target_language: Language) -> str:
    mapping = EN_TO_RU if target_language == "ru" else RU_TO_EN
    return "".join(mapping.get(char, char) for char in text)


BOUNDARY_PUNCTUATION = set(".,!?;:\"'()[]{}<>/\\")


def convert_layout_text_preserving_punctuation(text: str, target_language: Language) -> str:
    mapping = EN_TO_RU if target_language == "ru" else RU_TO_EN
    converted: list[str] = []
    for index, char in enumerate(text):
        replacement = mapping.get(char)
        if replacement is None:
            converted.append(char)
            continue
        if _should_preserve_boundary_punctuation(text, index, char):
            converted.append(char)
            continue
        converted.append(replacement)
    return "".join(converted)


def _should_preserve_boundary_punctuation(text: str, index: int, char: str) -> bool:
    if char not in BOUNDARY_PUNCTUATION:
        return False
    previous_char = text[index - 1] if index > 0 else ""
    next_char = text[index + 1] if index + 1 < len(text) else ""
    return not (_is_layout_word_char(previous_char) and _is_layout_word_char(next_char))


def _is_layout_word_char(char: str) -> bool:
    return bool(char) and (char.isalpha() or char.isdigit())


def normalize_word(text: str) -> str:
    letters = []
    for char in text.lower():
        if char.isalpha() or char in {"'", "-"}:
            letters.append("е" if char == "ё" else char)
    return "".join(letters).strip("'-")


def has_letters(text: str) -> bool:
    return any(char.isalpha() for char in text)


def has_digits(text: str) -> bool:
    return any(char.isdigit() for char in text)


def is_ignored_token(text: str) -> bool:
    lowered = text.lower()
    if not lowered or len(lowered) > 64:
        return True
    if re.search(r"https?://|www\.|@\w|\\|/|::|[{}<>_=+*#~|]", lowered):
        return True
    if any(char.isdigit() for char in lowered) and not has_letters(lowered):
        return True
    if lowered.startswith(("-", "--", "/")):
        return True
    return False


def infer_language(text: str, fallback: Language) -> Language:
    norm = normalize_word(text)
    ru = sum(1 for char in norm if char in RU_LETTERS)
    en = sum(1 for char in norm if char in EN_LETTERS)
    if ru > en:
        return "ru"
    if en > ru:
        return "en"
    return fallback


def _letter_stats(text: str, language: Language) -> tuple[int, int, int, int]:
    norm = normalize_word(text)
    target_letters = RU_LETTERS if language == "ru" else EN_LETTERS
    other_letters = EN_LETTERS if language == "ru" else RU_LETTERS
    target = sum(1 for char in norm if char in target_letters)
    other = sum(1 for char in norm if char in other_letters)
    letters = sum(1 for char in norm if char.isalpha())
    non_letters = sum(1 for char in text if not char.isalpha() and char not in {"'", "-"})
    return target, other, letters, non_letters


def _ratio(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return part / total


def _common_words(language: Language) -> set[str]:
    return RU_COMMON_WORDS if language == "ru" else EN_COMMON_WORDS


def _common_bigrams(language: Language) -> set[str]:
    return RU_BIGRAMS if language == "ru" else EN_BIGRAMS


def _vowels(language: Language) -> set[str]:
    return RU_VOWELS if language == "ru" else EN_VOWELS


def _suffixes(language: Language) -> tuple[str, ...]:
    return RU_SUFFIXES if language == "ru" else EN_SUFFIXES


def is_common_word(text: str, language: Language) -> bool:
    return normalize_word(text) in _common_words(language)


def _adjacent_transposition_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    seen = {text}
    for index in range(len(text) - 1):
        left = text[index]
        right = text[index + 1]
        if not (left.isalpha() and right.isalpha()):
            continue
        if left.casefold() == right.casefold():
            continue
        chars = list(text)
        chars[index], chars[index + 1] = chars[index + 1], chars[index]
        candidate = "".join(chars)
        if candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)
    return candidates


def _consonants(language: Language) -> set[str]:
    return (RU_LETTERS - RU_VOWELS) if language == "ru" else (EN_LETTERS - EN_VOWELS)


def _repeated_consonant_candidate(text: str, language: Language) -> str | None:
    consonants = _consonants(language)
    parts: list[str] = []
    index = 0
    changed = False
    while index < len(text):
        char = text[index]
        run_end = index + 1
        while run_end < len(text) and text[run_end].casefold() == char.casefold():
            run_end += 1
        run_length = run_end - index
        if char.isalpha() and char.casefold() in consonants and run_length >= 3:
            parts.extend(text[index : index + 2])
            changed = True
        else:
            parts.extend(text[index:run_end])
        index = run_end
    if not changed:
        return None
    candidate = "".join(parts)
    return candidate if candidate != text else None


def should_lowercase_common_word(text: str, language: Language, context: SentenceContext) -> bool:
    if not context.recent:
        return False
    if not text or not text[0].isalpha() or not text[0].isupper():
        return False
    if any(char.isupper() for char in text[1:] if char.isalpha()):
        return False
    lowered = text[0].lower() + text[1:]
    if lowered == text:
        return False
    return is_common_word(lowered, language)


def layout_punctuation_replacement(
    actual: str,
    alternate: str,
    actual_language: Language,
    context: SentenceContext,
    allow_repeat: bool = False,
) -> tuple[str, Language] | None:
    fix = LAYOUT_PUNCTUATION_FIXES.get((actual_language, actual))
    if not fix:
        return None
    replacement, target_language = fix
    if alternate and alternate != replacement:
        return None
    if replacement == "?" and not allow_repeat and not _question_mark_context_allowed(context, target_language):
        return None
    return replacement, target_language


def _question_mark_context_allowed(context: SentenceContext, target_language: Language) -> bool:
    if target_language != "ru" or not context.recent:
        return False
    counts = context.language_counts()
    return counts["ru"] > 0 and counts["ru"] >= counts["en"]


def _has_script_letters(text: str, language: Language) -> bool:
    letters = RU_LETTERS if language == "ru" else EN_LETTERS
    return any(char.lower() in letters for char in text)


def _is_latin_technical_token(text: str) -> bool:
    # Compact mixed digit/Latin identifiers such as 3D, 2FA, H264, C3PO.
    if not 2 <= len(text) <= 16:
        return False
    if not re.fullmatch(r"[A-Za-z0-9]+", text):
        return False
    return has_digits(text) and any(char.lower() in EN_LETTERS for char in text)


def _is_latin_technical_layout_fix(
    actual_text: str,
    alternate_text: str,
    actual_language: Language,
    target_language: Language,
) -> bool:
    if target_language != "en" or actual_language != "ru":
        return False
    if not has_digits(actual_text) or not has_letters(actual_text):
        return False
    if not _has_script_letters(actual_text, "ru"):
        return False
    return _is_latin_technical_token(alternate_text)


class ContextAwareDetector:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()

    def score_candidate(
        self,
        text: str,
        language: Language,
        context: SentenceContext | None = None,
    ) -> CandidateScore:
        context = context or SentenceContext()
        norm = normalize_word(text)
        reasons: list[str] = []
        if not norm:
            return CandidateScore(text=text, language=language, score=-20.0, reasons=["empty"])

        target, other, letters, non_letters = _letter_stats(text, language)
        score = 0.0
        target_ratio = _ratio(target, letters)
        other_ratio = _ratio(other, letters)

        score += target_ratio * 4.0
        if target_ratio >= 0.9:
            reasons.append("script")
        if other:
            penalty = other_ratio * 5.0
            score -= penalty
            reasons.append(f"foreign-script:-{penalty:.1f}")
        if non_letters:
            penalty = min(3.5, non_letters * 0.9)
            score -= penalty
            reasons.append(f"symbols:-{penalty:.1f}")

        common_words = _common_words(language)
        if norm in common_words:
            score += 7.0
            reasons.append("dictionary")
        elif len(norm) >= 5:
            prefix_hit = any(word.startswith(norm[:4]) or norm.startswith(word) for word in common_words if len(word) >= 4)
            if prefix_hit:
                score += 1.0
                reasons.append("dictionary-prefix")

        if len(norm) >= 4:
            bigrams = [norm[index : index + 2] for index in range(len(norm) - 1)]
            common_hits = sum(1 for bigram in bigrams if bigram in _common_bigrams(language))
            bigram_ratio = _ratio(common_hits, len(bigrams))
            score += bigram_ratio * 2.0
            if bigram_ratio >= 0.45:
                reasons.append("bigrams")
            elif bigram_ratio <= 0.15:
                score -= 1.2
                reasons.append("rare-bigrams")

        vowels = sum(1 for char in norm if char in _vowels(language))
        vowel_ratio = _ratio(vowels, letters)
        if letters >= 4:
            if 0.2 <= vowel_ratio <= 0.68:
                score += 0.7
                reasons.append("vowels")
            elif vowel_ratio < 0.16:
                score -= 1.4
                reasons.append("no-vowels")

        if len(norm) >= 4 and norm.endswith(_suffixes(language)):
            score += 0.8
            reasons.append("suffix")

        bias = context.language_bias(language, self.config.context_weight)
        if bias:
            score += bias
            reasons.append(f"context:{bias:+.1f}")

        return CandidateScore(text=text, language=language, score=score, reasons=reasons)

    def detect(
        self,
        actual_text: str,
        alternate_text: str,
        actual_language: Language,
        context: SentenceContext | None = None,
    ) -> DetectionResult:
        context = context or SentenceContext()
        target_language = opposite_language(actual_language)
        actual = self.score_candidate(actual_text, actual_language, context)
        alternate = self.score_candidate(alternate_text, target_language, context)

        margin = alternate.score - actual.score
        threshold = self.config.score_margin
        norm_actual = normalize_word(actual_text)
        norm_alternate = normalize_word(alternate_text)

        if _is_latin_technical_layout_fix(actual_text, alternate_text, actual_language, target_language):
            boosted_alternate = CandidateScore(
                text=alternate.text,
                language=alternate.language,
                score=max(alternate.score, actual.score + self.config.strong_score_margin),
                reasons=[*alternate.reasons, "latin-technical-token"],
            )
            return self._result(
                True,
                target_language,
                alternate_text,
                0.97,
                actual,
                boosted_alternate,
                "latin-technical-token",
            )

        if len(norm_actual) < self.config.min_word_chars and len(norm_alternate) < self.config.min_word_chars:
            return self._result(False, target_language, alternate_text, 0.0, actual, alternate, "too-short")

        if is_ignored_token(actual_text) or is_ignored_token(alternate_text):
            return self._result(False, target_language, alternate_text, 0.0, actual, alternate, "ignored-token")

        if norm_actual in _common_words(actual_language):
            threshold += 4.0
        if norm_alternate in _common_words(target_language):
            threshold -= 0.6
        if any(not char.isalpha() for char in actual_text) and all(char.isalpha() or char in {"'", "-"} for char in alternate_text):
            threshold -= 0.7

        should_correct = (
            alternate.score >= self.config.min_alternate_score
            and margin >= threshold
        ) or (
            alternate.score >= actual.score + self.config.strong_score_margin
            and alternate.score >= self.config.min_alternate_score + 1.5
        )
        confidence = max(0.0, min(0.99, 1.0 / (1.0 + math.exp(-margin / 3.0))))
        reason = f"margin={margin:.2f}, threshold={threshold:.2f}"
        return self._result(should_correct, target_language, alternate_text, confidence, actual, alternate, reason)

    def detect_transposed_letters(
        self,
        text: str,
        language: Language,
        context: SentenceContext | None = None,
    ) -> InLayoutCorrection | None:
        context = context or SentenceContext()
        norm = normalize_word(text)
        if not self.config.fix_transposed_letters:
            return None
        if len(norm) < max(3, self.config.min_word_chars):
            return None
        if is_ignored_token(text) or has_digits(text) or not has_letters(text):
            return None
        if is_common_word(text, language):
            return None
        if not _has_script_letters(text, language):
            return None
        if _has_script_letters(text, opposite_language(language)):
            return None

        actual = self.score_candidate(text, language, context)
        best: tuple[float, float, str] | None = None
        second_best: tuple[float, float, str] | None = None
        min_margin = max(2.2, self.config.score_margin - 0.4)

        for candidate in _adjacent_transposition_candidates(text):
            norm_candidate = normalize_word(candidate)
            if not norm_candidate or norm_candidate == norm:
                continue
            if norm_candidate not in _common_words(language):
                continue

            scored = self.score_candidate(candidate, language, context)
            margin = scored.score - actual.score
            if margin < min_margin:
                continue

            item = (scored.score, margin, candidate)
            if best is None or item > best:
                second_best = best
                best = item
            elif second_best is None or item > second_best:
                second_best = item

        if best is None:
            return None

        if second_best is not None:
            score_gap = best[0] - second_best[0]
            margin_gap = best[1] - second_best[1]
            if score_gap < 0.45 and margin_gap < 0.35:
                return None

        confidence = max(0.0, min(0.98, 1.0 / (1.0 + math.exp(-best[1] / 2.4))))
        return InLayoutCorrection(
            replacement=best[2],
            confidence=confidence,
            reason=f"adjacent-transposition margin={best[1]:.2f}",
        )

    def detect_repeated_consonants(
        self,
        text: str,
        language: Language,
        context: SentenceContext | None = None,
        protected_words: set[str] | None = None,
        protected_suffixes: tuple[str, ...] = (),
    ) -> InLayoutCorrection | None:
        context = context or SentenceContext()
        norm = normalize_word(text)
        if not self.config.fix_repeated_consonants:
            return None
        if len(norm) < max(3, self.config.min_word_chars):
            return None
        if is_ignored_token(text) or has_digits(text) or not has_letters(text):
            return None
        if is_common_word(text, language):
            return None
        if not _has_script_letters(text, language):
            return None
        if _has_script_letters(text, opposite_language(language)):
            return None
        if protected_words and norm in protected_words:
            return None
        if any(len(norm) > len(suffix) and norm.endswith(suffix) for suffix in protected_suffixes):
            return None

        candidate = _repeated_consonant_candidate(text, language)
        if candidate is None:
            return None

        actual = self.score_candidate(text, language, context)
        scored = self.score_candidate(candidate, language, context)
        confidence = max(0.78, min(0.99, 0.84 + max(0.0, scored.score - actual.score) / 10.0))
        return InLayoutCorrection(
            replacement=candidate,
            confidence=confidence,
            reason=f"triple-consonant-collapse score={scored.score - actual.score:+.2f}",
        )

    @staticmethod
    def _result(
        should_correct: bool,
        target_language: Language,
        replacement: str,
        confidence: float,
        actual: CandidateScore,
        alternate: CandidateScore,
        reason: str,
    ) -> DetectionResult:
        return DetectionResult(
            should_correct=should_correct,
            target_language=target_language,
            replacement=replacement,
            confidence=confidence,
            actual=actual,
            alternate=alternate,
            reason=reason,
        )


def update_context_from_delimiter(context: SentenceContext, delimiter: str) -> None:
    if any(char in ".!?\n\r" for char in delimiter):
        context.reset_sentence()


def resolve_context_entry(
    actual_text: str,
    alternate_text: str,
    actual_language: Language,
    detector: ContextAwareDetector,
    context: SentenceContext | None = None,
) -> tuple[str, Language] | None:
    context = context or SentenceContext()
    target_language = opposite_language(actual_language)
    norm_actual = normalize_word(actual_text)
    norm_alternate = normalize_word(alternate_text)

    if not norm_actual and not norm_alternate:
        return None

    if is_ignored_token(actual_text) or is_ignored_token(alternate_text):
        return None

    inferred_language = infer_language(actual_text, actual_language)
    if len(norm_actual) >= detector.config.min_word_chars or len(norm_alternate) >= detector.config.min_word_chars:
        return actual_text, inferred_language

    actual = detector.score_candidate(actual_text, actual_language, context)
    alternate = detector.score_candidate(alternate_text, target_language, context)
    margin = alternate.score - actual.score
    context_margin = max(1.5, detector.config.score_margin / 2.0)

    if margin >= context_margin:
        return alternate_text, target_language
    if margin <= -context_margin:
        return actual_text, actual_language
    return actual_text, inferred_language
