"""Чек-лист для ручной сверки качества (SC-005)."""

from pathlib import Path

from french_learning.agent.quality import quality_sample


def test_checklist_excludes_needs_review_and_open(store: Path):
    text = quality_sample(store, lessons=[1])
    assert text.startswith("# Сверка качества: уроки 1")
    # пункт 2 упражнения ex-gapchoic помечен «требует проверки» — не входит
    assert "Je bois [l'] eau." not in text
    assert "[Le] chat dort." in text
    assert "Je ne suis pas fatiguée." in text  # трансформация
    assert "Рассказать о своём завтраке" not in text  # открытый ответ — без ответов
    assert "- [ ] " in text
    assert "lessons/001/sources/sheet.jpg" in text


def test_totals_and_threshold(store: Path):
    text = quality_sample(store, lessons=[1, 2])
    last = text.strip().splitlines()[-1]
    assert last.startswith("Пунктов для сверки:")
    total = int(last.split(":")[1].split(",")[0])
    assert f"допустимо ошибок: {total * 5 // 100}" in last
