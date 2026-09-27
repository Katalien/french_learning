"""Генераторы встроенных тренажёров (FR-041–FR-046, SC-005; research R11)."""

import pytest

from french_learning.trainers.generators import (
    agreement,
    articles,
    conjugation,
    determiners,
    forms,
    numbers,
    sentences,
)


def by_key(questions):
    return {q.key: q for q in questions}


# --- артикли: контрольный набор SC-005 -------------------------------------------------------


@pytest.fixture
def nouns(vocab):
    return [
        vocab("maison", "maison", article="la", gender="f", pos="nom", ru="дом"),
        vocab("chat", "chat", article="le", gender="m", pos="nom"),
        vocab("eau", "eau", article="l'", gender="f", pos="nom"),
        vocab("homme", "homme", gender="m", pos="nom"),  # h немое, артикль не указан
        vocab("heros", "héros", gender="m", pos="nom", flags={"h_aspire": True}),
        vocab("hache", "hache", gender="f", pos="nom", flags={"h_aspire": True}),
        vocab("eleve", "élève", gender="both", pos="nom"),
        vocab("gens", "gens", article="les", pos="nom", flags={"plural_only": True}),
        vocab("stylo", "stylo", pos="nom"),  # род неизвестен — пропускается
        vocab("parler", "parler", entry_type="verb", pos="verbe"),
    ]


@pytest.mark.parametrize(
    ("key", "definite", "indefinite"),
    [
        ("voc-maisonaa", ["la"], ["une"]),
        ("voc-chataaaa", ["le"], ["un"]),
        ("voc-eauaaaaa", ["l'"], ["une"]),
        ("voc-hommeaaa", ["l'"], ["un"]),
        ("voc-herosaaa", ["le"], ["un"]),
        ("voc-hacheaaa", ["la"], ["une"]),
        ("voc-eleveaaa", ["l'"], ["un", "une"]),
        ("voc-gensaaaa", ["les"], ["des"]),
    ],
)
def test_articles_control_set(nouns, data, key, definite, indefinite):
    found = by_key(articles.generate(data(*nouns)))
    assert sorted(found[f"articles:{key}:def"].answers) == sorted(definite)
    assert sorted(found[f"articles:{key}:indef"].answers) == sorted(indefinite)


def test_articles_question_shape(nouns, data):
    found = by_key(articles.generate(data(*nouns)))
    q = found["articles:voc-maisonaa:def"]
    assert q.prompt == "___ maison" and q.mode == "buttons"
    assert q.options == ["le", "la", "l'", "les"]
    assert "дом" not in q.prompt  # перевод не спрашивается (FR-042)
    assert found["articles:voc-eauaaaaa:def"].full == "l'eau"
    assert found["articles:voc-maisonaa:indef"].options == ["un", "une", "des"]
    assert not any("stylo" in k or "parler" in k for k in found)


def test_articles_missing_data(data, vocab):
    assert articles.generate(data(vocab("stylo", "stylo", pos="nom"))) == []


# --- спряжение -------------------------------------------------------------------------------


def test_conjugation(vocab, data):
    verb = vocab(
        "parler",
        "parler",
        entry_type="verb",
        pos="verbe",
        verb={
            "group": 1,
            "conjugation": {
                "present": {
                    "je": "parle",
                    "tu": "parles",
                    "il/elle": "parle",
                    "nous": "parlons",
                    "vous": "parlez",
                    "ils/elles": "parlent",
                }
            },
        },
    )
    aimer = vocab(
        "aimer",
        "aimer",
        entry_type="verb",
        pos="verbe",
        verb={"conjugation": {"present": {"je": "j'aime"}}},
    )
    found = by_key(conjugation.generate(data(verb, aimer)))
    q = found["conjugation:voc-parleraa:present:nous"]
    assert q.prompt == "parler — nous" and q.mode == "input"
    assert "parlons" in q.answers and "nous parlons" in q.answers
    assert set(found["conjugation:voc-aimeraaa:present:je"].answers) == {"j'aime", "aime"}
    assert len(found) == 7
    assert conjugation.generate(data(vocab("chat", "chat", pos="nom"))) == []


# --- женский род и множественное число -------------------------------------------------------


def test_feminine_and_plural(vocab, data):
    grand = vocab("grand", "grand", pos="adj", forms={"feminine": "grande", "plural": "grands"})
    cheval = vocab(
        "cheval", "cheval", article="le", gender="m", pos="nom", forms={"plural": "chevaux"}
    )
    fem = by_key(forms.generate_feminine(data(grand, cheval)))
    assert list(fem) == ["feminine:voc-grandaaa"]
    assert fem["feminine:voc-grandaaa"].answers == ["grande"]
    plural = by_key(forms.generate_plural(data(grand, cheval)))
    assert plural["plural:voc-chevalaa"].answers == ["chevaux"]
    assert plural["plural:voc-chevalaa"].prompt == "cheval"


# --- притяжательные и указательные -----------------------------------------------------------


def test_possessives(vocab, data):
    amie = vocab("amie", "amie", gender="f", pos="nom", ru="подруга")
    maison = vocab("maison", "maison", gender="f", pos="nom")
    livre = vocab("livre", "livre", gender="m", pos="nom")
    gens = vocab("gens", "gens", pos="nom", flags={"plural_only": True})
    found = by_key(determiners.generate_possessives(data(amie, maison, livre, gens)))
    first = found["possessives:voc-amieaaaa:1"]
    assert first.answers == ["mon"] and first.prompt == "___ amie" and "моя" in first.hint
    assert found["possessives:voc-maisonaa:1"].answers == ["ma"]
    assert found["possessives:voc-livreaaa:4"].answers == ["notre"]
    assert found["possessives:voc-gensaaaa:6"].answers == ["leurs"]


def test_demonstratives(vocab, data):
    entries = [
        vocab("homme", "homme", gender="m", pos="nom"),
        vocab("heros", "héros", gender="m", pos="nom", flags={"h_aspire": True}),
        vocab("livre", "livre", gender="m", pos="nom"),
        vocab("maison", "maison", gender="f", pos="nom"),
        vocab("gens", "gens", pos="nom", flags={"plural_only": True}),
    ]
    found = by_key(determiners.generate_demonstratives(data(*entries)))
    assert found["demonstratives:voc-hommeaaa"].answers == ["cet"]
    assert found["demonstratives:voc-herosaaa"].answers == ["ce"]
    assert found["demonstratives:voc-livreaaa"].answers == ["ce"]
    assert found["demonstratives:voc-maisonaa"].answers == ["cette"]
    assert found["demonstratives:voc-gensaaaa"].answers == ["ces"]
    assert found["demonstratives:voc-livreaaa"].options == ["ce", "cet", "cette", "ces"]


# --- согласование прилагательного ------------------------------------------------------------


def test_adjective_agreement(vocab, data):
    grand = vocab("grand", "grand", pos="adj", forms={"feminine": "grande", "plural": "grands"})
    maison = vocab("maison", "maison", article="la", gender="f", pos="nom")
    livre = vocab("livre", "livre", article="le", gender="m", pos="nom", forms={"plural": "livres"})
    found = agreement.generate(data(grand, maison, livre))
    fem = next(q for q in found if q.key.endswith(":f"))
    assert fem.answers == ["grande"] and "maison" in fem.prompt and "grand" in fem.prompt
    plural = next(q for q in found if q.key.endswith(":pl"))
    assert plural.answers == ["grands"] and "livres" in plural.prompt
    assert agreement.generate(data(maison)) == []


# --- числа и «собери предложение» ------------------------------------------------------------


def test_numbers(data):
    found = by_key(numbers.generate(data()))
    assert len(found) == 1001
    assert found["numbers:97"].prompt == "97"
    assert found["numbers:97"].answers[0] == "quatre-vingt-dix-sept"


def test_sentences_from_exercises_and_texts(clean_content_root, data):
    from french_learning.content.loader import load_content

    content = load_content(clean_content_root)
    exercises = [e for e in content.elements.values() if e.kind == "exercise"]
    texts = [e for e in content.elements.values() if e.kind == "text"]
    found = sentences.generate(data(exercises=exercises, texts=texts))
    fulls = {q.answers[0] for q in found}
    assert "Je ne suis pas fatiguée." in fulls  # из трансформации
    assert "Nous sommes au café." in fulls  # пропуск подставлен
    assert all(4 <= len(q.answers[0].split()) <= 12 for q in found)
    q = next(q for q in found if q.answers[0] == "Je ne suis pas fatiguée.")
    assert q.mode == "order" and sorted(q.tokens) == sorted(q.answers[0].split())
    assert q.tokens != q.answers[0].split()  # перемешано
    assert any(q.source.startswith("tx-") for q in found)  # и из текстов
