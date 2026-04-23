from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

from .exceptions import TypoExceptionStore, normalize_exception_suffix, normalize_exception_word
from .learning import LearnedCorrection, LearningStore, learning_key
from .language import Language


@dataclass(slots=True)
class EditableRule:
    actual: str
    replacement: str
    target_language: Language
    count: int = 1
    updated_at: float = 0.0

    @classmethod
    def from_learned(cls, item: LearnedCorrection) -> "EditableRule":
        return cls(
            actual=item.actual,
            replacement=item.replacement,
            target_language=item.target_language,
            count=item.count,
            updated_at=item.updated_at,
        )

    def to_learned(self) -> LearnedCorrection:
        return LearnedCorrection(
            actual=self.actual,
            replacement=self.replacement,
            target_language=self.target_language,
            count=self.count,
            updated_at=self.updated_at,
        )


class RulesEditorWindow:
    def __init__(self, store: LearningStore, exception_store: TypoExceptionStore) -> None:
        import tkinter as tk
        from tkinter import messagebox, ttk

        self._tk = tk
        self._messagebox = messagebox
        self._ttk = ttk
        self._store = store
        self._exception_store = exception_store
        self._rules: dict[str, EditableRule] = {}
        self._exception_words: set[str] = set()
        self._exception_suffixes: set[str] = set()
        self._dirty = False

        self._root = tk.Tk()
        self._root.title("Правила KeySwitcher")
        self._root.geometry("920x560")
        self._root.minsize(780, 480)
        self._root.configure(bg="#f3f4f6")
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._status_var = tk.StringVar()
        self._actual_var = tk.StringVar()
        self._replacement_var = tk.StringVar()
        self._target_var = tk.StringVar(value="ru")
        self._exception_word_var = tk.StringVar()
        self._exception_suffix_var = tk.StringVar()

        self._selected_key: str | None = None
        self._tree = None
        self._exception_word_list = None
        self._exception_suffix_list = None

        self._build_ui()
        self._reload_all()

    def run(self) -> int:
        self._root.mainloop()
        return 0

    def _build_ui(self) -> None:
        ttk = self._ttk
        style = ttk.Style(self._root)
        for theme in ("vista", "clam"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break

        frame = ttk.Frame(self._root, padding=14)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        header = ttk.Label(frame, text="Правила и исключения", font=("Segoe UI", 14, "bold"))
        header.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            frame,
            text=f"Правила: {self._store.path}   Исключения: {self._exception_store.path}",
            foreground="#4b5563",
        )
        subtitle.grid(row=0, column=0, sticky="e")

        notebook = ttk.Notebook(frame)
        notebook.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        rules_tab = ttk.Frame(notebook, padding=4)
        rules_tab.columnconfigure(0, weight=3)
        rules_tab.columnconfigure(1, weight=2)
        rules_tab.rowconfigure(0, weight=1)
        notebook.add(rules_tab, text="Выученные правила")

        exceptions_tab = ttk.Frame(notebook, padding=4)
        exceptions_tab.columnconfigure(0, weight=1)
        exceptions_tab.columnconfigure(1, weight=1)
        exceptions_tab.rowconfigure(0, weight=1)
        notebook.add(exceptions_tab, text="Исключения")

        self._build_rules_tab(rules_tab)
        self._build_exceptions_tab(exceptions_tab)

        status = ttk.Label(frame, textvariable=self._status_var, foreground="#4b5563", padding=(0, 10, 0, 0))
        status.grid(row=2, column=0, sticky="w")

    def _build_rules_tab(self, parent) -> None:
        ttk = self._ttk
        list_frame = ttk.Frame(parent, padding=(0, 0, 10, 0))
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            list_frame,
            columns=("actual", "replacement", "target"),
            show="headings",
            selectmode="browse",
        )
        self._tree.heading("actual", text="Введено")
        self._tree.heading("replacement", text="Заменить на")
        self._tree.heading("target", text="Раскладка")
        self._tree.column("actual", width=180, anchor="w")
        self._tree.column("replacement", width=220, anchor="w")
        self._tree.column("target", width=80, anchor="center")
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self._tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=scrollbar.set)

        list_buttons = ttk.Frame(list_frame, padding=(0, 10, 0, 0))
        list_buttons.grid(row=1, column=0, sticky="w")
        ttk.Button(list_buttons, text="Новое", command=self._new_rule).pack(side="left")
        ttk.Button(list_buttons, text="Удалить", command=self._delete_rule).pack(side="left", padx=(8, 0))
        ttk.Button(list_buttons, text="Перечитать файлы", command=self._reload_from_disk).pack(side="left", padx=(8, 0))

        form_frame = ttk.LabelFrame(parent, text="Правило", padding=14)
        form_frame.grid(row=0, column=1, sticky="nsew")
        form_frame.columnconfigure(1, weight=1)

        ttk.Label(form_frame, text="Введено").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(form_frame, textvariable=self._actual_var).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(form_frame, text="Заменить на").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(form_frame, textvariable=self._replacement_var).grid(row=1, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(form_frame, text="Целевая раскладка").grid(row=2, column=0, sticky="w")
        target_box = ttk.Combobox(
            form_frame,
            textvariable=self._target_var,
            values=("en", "ru"),
            state="readonly",
            width=8,
        )
        target_box.grid(row=2, column=1, sticky="w")

        help_text = ttk.Label(
            form_frame,
            text=(
                "Выученные соответствия применяются как точные замены.\n"
                "Исключения ниже защищают слова и суффиксы от исправления повторяющихся согласных."
            ),
            foreground="#4b5563",
            justify="left",
        )
        help_text.grid(row=3, column=0, columnspan=2, sticky="w", pady=(14, 0))

        actions = ttk.Frame(form_frame, padding=(0, 18, 0, 0))
        actions.grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Button(actions, text="Применить строку", command=self._apply_rule).pack(side="left")
        ttk.Button(actions, text="Сохранить всё", command=self._save_all).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Закрыть", command=self._on_close).pack(side="left", padx=(8, 0))

    def _build_exceptions_tab(self, parent) -> None:
        ttk = self._ttk
        words_frame = ttk.LabelFrame(parent, text="Защищённые слова", padding=14)
        words_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        words_frame.columnconfigure(0, weight=1)
        words_frame.rowconfigure(1, weight=1)

        ttk.Label(
            words_frame,
            text="Точные слова, которые не нужно менять при исправлении повторяющихся согласных.",
            foreground="#4b5563",
        ).grid(row=0, column=0, sticky="w")

        self._exception_word_list = self._tk.Listbox(words_frame, activestyle="none")
        self._exception_word_list.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        word_row = ttk.Frame(words_frame, padding=(0, 10, 0, 0))
        word_row.grid(row=2, column=0, sticky="ew")
        word_row.columnconfigure(0, weight=1)
        ttk.Entry(word_row, textvariable=self._exception_word_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(word_row, text="Добавить", command=self._add_exception_word).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(word_row, text="Удалить", command=self._delete_exception_word).grid(row=0, column=2, padx=(8, 0))

        suffix_frame = ttk.LabelFrame(parent, text="Защищённые суффиксы", padding=14)
        suffix_frame.grid(row=0, column=1, sticky="nsew")
        suffix_frame.columnconfigure(0, weight=1)
        suffix_frame.rowconfigure(1, weight=1)

        ttk.Label(
            suffix_frame,
            text="Суффиксы вроде -less, которые могут корректно образовывать тройные согласные.",
            foreground="#4b5563",
        ).grid(row=0, column=0, sticky="w")

        self._exception_suffix_list = self._tk.Listbox(suffix_frame, activestyle="none")
        self._exception_suffix_list.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        suffix_row = ttk.Frame(suffix_frame, padding=(0, 10, 0, 0))
        suffix_row.grid(row=2, column=0, sticky="ew")
        suffix_row.columnconfigure(0, weight=1)
        ttk.Entry(suffix_row, textvariable=self._exception_suffix_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(suffix_row, text="Добавить", command=self._add_exception_suffix).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(suffix_row, text="Удалить", command=self._delete_exception_suffix).grid(row=0, column=2, padx=(8, 0))

    def _set_dirty(self, dirty: bool, status: str | None = None) -> None:
        self._dirty = dirty
        self._root.title("Правила KeySwitcher*" if dirty else "Правила KeySwitcher")
        if status is not None:
            self._status_var.set(status)

    def _sorted_items(self) -> list[tuple[str, EditableRule]]:
        return sorted(self._rules.items(), key=lambda pair: (pair[1].actual.casefold(), pair[0]))

    def _sorted_exception_words(self) -> list[str]:
        return sorted(self._exception_words)

    def _sorted_exception_suffixes(self) -> list[str]:
        return sorted(self._exception_suffixes)

    def _refresh_tree(self, selected_key: str | None = None) -> None:
        current = selected_key or self._selected_key
        self._tree.delete(*self._tree.get_children())
        for key, rule in self._sorted_items():
            self._tree.insert("", "end", iid=key, values=(rule.actual, rule.replacement, rule.target_language.upper()))
        if current and current in self._rules:
            self._tree.selection_set(current)
            self._tree.focus(current)
            self._selected_key = current
        else:
            self._selected_key = None

    def _refresh_exception_lists(self) -> None:
        self._exception_word_list.delete(0, self._tk.END)
        for word in self._sorted_exception_words():
            self._exception_word_list.insert(self._tk.END, word)
        self._exception_suffix_list.delete(0, self._tk.END)
        for suffix in self._sorted_exception_suffixes():
            self._exception_suffix_list.insert(self._tk.END, f"-{suffix}")

    def _reload_all(self) -> None:
        self._rules = {
            learning_key(item.actual): EditableRule.from_learned(item)
            for item in self._store.items()
        }
        self._exception_words = set(self._exception_store.words())
        self._exception_suffixes = set(self._exception_store.suffixes())
        self._refresh_tree()
        self._refresh_exception_lists()
        self._clear_form()
        self._exception_word_var.set("")
        self._exception_suffix_var.set("")
        self._set_dirty(False, "Правила и исключения загружены с диска.")

    def _reload_from_disk(self) -> None:
        if self._dirty and not self._messagebox.askyesno(
            "Отменить изменения?",
            "При перечитывании будут потеряны несохранённые изменения в этом окне. Продолжить?",
        ):
            return
        self._store.load()
        self._exception_store.load()
        self._reload_all()

    def _clear_form(self) -> None:
        self._actual_var.set("")
        self._replacement_var.set("")
        self._target_var.set("ru")

    def _on_select(self, _event=None) -> None:
        selection = self._tree.selection()
        if not selection:
            self._selected_key = None
            return
        key = selection[0]
        rule = self._rules.get(key)
        if rule is None:
            return
        self._selected_key = key
        self._actual_var.set(rule.actual)
        self._replacement_var.set(rule.replacement)
        self._target_var.set(rule.target_language)

    def _new_rule(self) -> None:
        self._tree.selection_remove(self._tree.selection())
        self._selected_key = None
        self._clear_form()
        self._status_var.set("Введите новое правило и нажмите «Применить строку».")

    def _delete_rule(self) -> None:
        if not self._selected_key or self._selected_key not in self._rules:
            self._status_var.set("Выберите правило для удаления.")
            return
        deleted = self._rules.pop(self._selected_key)
        self._refresh_tree()
        self._clear_form()
        self._set_dirty(True, f"Удалено правило: {deleted.actual} -> {deleted.replacement}")

    def _apply_rule(self) -> None:
        actual = self._actual_var.get().strip()
        replacement = self._replacement_var.get().strip()
        target_language = self._target_var.get().strip().lower()

        if not actual or not replacement:
            self._messagebox.showerror("Некорректное правило", "Оба поля должны быть заполнены.")
            return
        if actual == replacement:
            self._messagebox.showerror("Некорректное правило", "Замена должна отличаться от введённого текста.")
            return
        if target_language not in {"en", "ru"}:
            self._messagebox.showerror("Некорректное правило", "Целевая раскладка должна быть EN или RU.")
            return

        new_key = learning_key(actual)
        existing = self._rules.get(new_key)
        if existing and new_key != self._selected_key:
            if not self._messagebox.askyesno(
                "Заменить существующее правило?",
                f"Правило для '{actual}' уже существует. Заменить его?",
            ):
                return

        source = existing
        if self._selected_key and self._selected_key in self._rules:
            source = self._rules.pop(self._selected_key)

        updated_at = source.updated_at if source else time.time()
        count = source.count if source else 1
        self._rules[new_key] = EditableRule(actual, replacement, target_language, count, updated_at)
        self._refresh_tree(new_key)
        self._set_dirty(True, f"Подготовлено правило: {actual} -> {replacement}")

    def _add_exception_word(self) -> None:
        value = normalize_exception_word(self._exception_word_var.get())
        if not value:
            self._status_var.set("Введите слово для защиты.")
            return
        self._exception_words.add(value)
        self._refresh_exception_lists()
        self._exception_word_var.set("")
        self._set_dirty(True, f"Добавлено защищённое слово: {value}")

    def _delete_exception_word(self) -> None:
        selection = self._exception_word_list.curselection()
        if not selection:
            self._status_var.set("Выберите защищённое слово для удаления.")
            return
        value = self._exception_word_list.get(selection[0])
        self._exception_words.discard(value)
        self._refresh_exception_lists()
        self._set_dirty(True, f"Удалено защищённое слово: {value}")

    def _add_exception_suffix(self) -> None:
        value = normalize_exception_suffix(self._exception_suffix_var.get())
        if not value:
            self._status_var.set("Введите суффикс для защиты.")
            return
        self._exception_suffixes.add(value)
        self._refresh_exception_lists()
        self._exception_suffix_var.set("")
        self._set_dirty(True, f"Добавлен защищённый суффикс: -{value}")

    def _delete_exception_suffix(self) -> None:
        selection = self._exception_suffix_list.curselection()
        if not selection:
            self._status_var.set("Выберите защищённый суффикс для удаления.")
            return
        label = self._exception_suffix_list.get(selection[0])
        value = label.lstrip("-")
        self._exception_suffixes.discard(value)
        self._refresh_exception_lists()
        self._set_dirty(True, f"Удалён защищённый суффикс: -{value}")

    def _save_all(self) -> bool:
        try:
            items = [rule.to_learned() for _, rule in self._sorted_items()]
            self._store.replace_all(items)
            self._exception_store.replace_all(self._sorted_exception_words(), self._sorted_exception_suffixes())
        except OSError as error:
            self._messagebox.showerror("Ошибка сохранения", str(error))
            return False
        self._set_dirty(False, "Сохранено. Используйте «Перезагрузить правила» в трее, чтобы применить изменения.")
        return True

    def _on_close(self) -> None:
        if self._dirty:
            save = self._messagebox.askyesnocancel(
                "Есть несохранённые изменения",
                "Сохранить изменения перед закрытием?",
            )
            if save is None:
                return
            if save and not self._save_all():
                return
        self._root.destroy()


def open_rules_editor(path: str | Path, exception_path: str | Path) -> int:
    store = LearningStore(Path(path), enabled=True)
    exception_store = TypoExceptionStore(Path(exception_path), enabled=True)
    store.ensure_file()
    exception_store.ensure_file()
    window = RulesEditorWindow(store, exception_store)
    return window.run()
