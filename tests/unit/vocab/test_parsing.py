"""Разбор списка слов в мягком формате (FR-021, FR-022; SC-003; research R6)."""

import pytest

from french_learning.vocab.parsing import parse_word_list


def one(line: str):
    result = parse_word_list(line)
    assert not result.unrecognized, result.unrecognized
    [entry] = result.entries
    return entry


@pytest.mark.parametrize("separator", [" — ", " – ", " - ", "\t"])
def test_separators(separator):
    entry = one(f"chat{separator}кот")
    assert entry.text == "chat" and entry.translations == ["кот"]


def test_several_translations():
    assert one("chat — кот, кошка").translations == ["кот", "кошка"]
    assert one("chat — кот; кошка").translations == ["кот", "кошка"]


@pytest.mark.parametrize(
    ("line", "article", "gender", "text"),
    [
        ("le chat — кот", "le", "m", "chat"),
        ("la maison — дом", "la", "f", "maison"),
        ("l'eau (f) — вода", "l'", "f", "eau"),
        ("l’hôtel (m) — гостиница", "l'", "m", "hôtel"),
        ("les gens — люди", "les", None, "gens"),
    ],
)
def test_articles_and_gender(line, article, gender, text):
    entry = one(line)
    assert (entry.article, entry.gender, entry.text) == (article, gender, text)


def test_markers():
    verb = one("parler (v) — говорить")
    assert verb.entry_type == "verb" and verb.pos == "verbe" and verb.text == "parler"
    adj = one("beau (adj) — красивый")
    assert adj.pos == "adj" and adj.entry_type == "word"
    phrase = one("à bientôt (phr) — до скорого")
    assert phrase.entry_type == "phrase"


def test_phrases_detected():
    assert one("Ça va ? — Как дела?").entry_type == "phrase"
    assert one("J'ai faim — Я голодна").entry_type == "phrase"
    assert one("avoir faim — быть голодным").entry_type == "word"


def test_skipped_lines():
    result = parse_word_list("\n# Урок 15, еда\n\nle pain — хлеб\n   \n")
    assert [e.text for e in result.entries] == ["pain"]
    assert result.unrecognized == []


def test_unrecognized_lines():
    result = parse_word_list("chat кот\nle pain — хлеб\nx — y — z")
    assert [u.line_no for u in result.unrecognized] == [1, 3]
    assert result.unrecognized[0].reason


def test_needs_completion():
    assert one("parler (v) — говорить").needs_completion
    assert one("chat — кот").needs_completion
    assert not one("Ça va ? — Как дела?").needs_completion


REALISTIC_LIST = """\
# Урок 15 — еда и напитки
le pain — хлеб
la baguette — багет
le fromage — сыр
le lait — молоко
l'eau (f) — вода
le café — кофе
le thé — чай
la viande — мясо
le poisson — рыба
le poulet — курица
les légumes — овощи
la pomme — яблоко
la poire — груша
le beurre — сливочное масло
la confiture — варенье, джем
le sucre — сахар
le sel — соль
le riz — рис
les pâtes — макароны
la soupe — суп
manger (v) — есть, кушать
boire (v) — пить
prendre (v) — брать
acheter (v) — покупать
aimer (v) — любить, нравиться
préférer (v) — предпочитать
cuisiner (v) — готовить
bon (adj) — хороший, вкусный
chaud (adj) — горячий
froid (adj) — холодный
sucré (adj) — сладкий
salé (adj) — солёный
beaucoup — много
peu — мало
un peu de — немного
assez — достаточно
trop — слишком
Bon appétit ! — Приятного аппетита!
J'ai faim — Я голодна
J'ai soif — Я хочу пить
L'addition, s'il vous plaît — Счёт, пожалуйста
Qu'est-ce que tu prends ? — Что ты возьмёшь?
avoir faim — быть голодным
avoir soif — хотеть пить
le petit-déjeuner — завтрак
le déjeuner — обед
le dîner — ужин
la boulangerie — булочная
le marché — рынок
le serveur - официант
la carte	меню
"""


def test_realistic_list_at_least_95_percent():
    lines = [ln for ln in REALISTIC_LIST.splitlines() if ln.strip() and not ln.startswith("#")]
    assert len(lines) == 51
    result = parse_word_list(REALISTIC_LIST)
    assert len(result.entries) / len(lines) >= 0.95


@pytest.mark.parametrize(
    ("line", "article", "gender", "text"),
    [
        ("le, chat - кот", "le", "m", "chat"),
        ("la , maison — дом", "la", "f", "maison"),
        ("l', eau - вода", "l'", None, "eau"),
        ("un chat - кот", "le", "m", "chat"),
        ("une, pomme - яблоко", "la", "f", "pomme"),
        ("un arbre - дерево", "l'", "m", "arbre"),
        ("une heure - час", None, "f", "heure"),
        ("des pommes - яблоки", "les", None, "pommes"),
    ],
)
def test_article_with_comma_and_indefinite(line, article, gender, text):
    # быстрый ввод «артикль, слово - перевод»: род — по артиклю; «h» не угадываем (h aspiré)
    entry = one(line)
    assert (entry.article, entry.gender, entry.text) == (article, gender, text)
    assert entry.pos == "nom" and entry.entry_type == "word"
