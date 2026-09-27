---
name: complete-words
description: Дополнить записи словаря, помеченные «нужно дополнить» (добавленные вручную или списком) — род, артикль, часть речи, формы, группу и спряжение глагола в настоящем времени. Использовать по просьбе «дополни слова» или кнопке «Дополнить» в приложении.
argument-hint: "[слово или id — если нужно дополнить только его]"
---

# /complete-words — дополнить слова словаря

Ввод пользователя: `$ARGUMENTS`

Прочитай `.claude/skills/_shared/content-rules.md` (раздел 4 «Лексика»). Формат —
`docs/content-format.md`. Отвечай по-русски. Операция `<op>` = `complete-ГГГГММДД-ЧЧММ`.
Делай **только** это (конституция X): не добавляй примеры, заметки и новые слова.

1. Найди записи с `needs_completion: true` в `CONTENT_DIR/vocabulary/*.yaml` (или только
   указанную пользователем). Нет таких — сообщи и закончи.
2. Для каждой записи заполни **только отсутствующие** поля:
   - существительное: `article` (le / la / l' / les), `gender` (m / f / both), `pos: nom`,
     признаки `flags.h_aspire`, `flags.plural_only`; `forms.plural` (и `forms.note`, если
     множественное число неправильное: `œil → yeux`, `-al → -aux`);
   - прилагательное: `pos: adj`, `forms.feminine`, `forms.plural` (+ `forms.note` при
     особом образовании: `beau → belle, beaux, belles`);
   - глагол: `pos: verbe`, `verb.group` (1 / 2 / 3), `verb.conjugation.present` —
     `{je, tu, il/elle, nous, vous, ils/elles}`; `flags.irregular`, `flags.reflexive`
     (для `se …` — `je me lève`);
   - фраза: ничего, только снять пометку.
   Переводы и `text` **не меняй**. Поля, которые были в записи, не трогай.
3. В `completed_by_ai` перечисли поля, заполненные тобой (например, `[gender, article, forms]`);
   сними `needs_completion`. Сомнение (род неоднозначен, слово неясно) →
   `needs_review: {flag: true, note: "…"}`.
4. Копии изменённых файлов — в `.staging/<op>/vocabulary/<id>.yaml` (тот же id);
   `uv run french-learning stage-check --op <op>`, затем
   `uv run french-learning commit-staging --op <op> -m "Словарь: дополнено N слов"`.
5. Отчёт: сколько дополнено, список «слово → что добавлено», сомнения, результат отправки;
   ссылка `http://127.0.0.1:8000/vocab`.
