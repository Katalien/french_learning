"""Словарь и повторение карточек (функция 003, contracts/ui-routes.md)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from french_learning.content.index import ContentIndex
from french_learning.practice.checking import FRENCH_SYMBOLS
from french_learning.practice.tts import DEFAULT_VOICE, VOICES
from french_learning.vocab import entries as vocab_entries
from french_learning.vocab.sessions import SessionParams
from french_learning.web.deps import Index, not_found
from french_learning.web.templating import templates

router = APIRouter()

MODE_NAMES = {
    "today": "Пора повторить сегодня",
    "lesson": "По уроку",
    "topic": "По теме",
    "all": "Все слова",
    "hard": "Сложные",
}
KIND_FILTERS = {
    "all": "всё вместе",
    "word": "только слова",
    "verb": "только глаголы",
    "phrase": "только фразы",
}
DIRECTIONS = {"fr_ru": "французский → русский", "ru_fr": "русский → французский"}
RATING_NAMES = {"again": "Не помню", "hard": "С трудом", "good": "Помню"}


def _practice(request: Request, index: ContentIndex):
    state = request.app.state
    if state.cards is None:
        raise not_found("Хранилище не настроено")
    state.cards.sync(index)
    return state.cards, state.sessions


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


@router.get("/practice")
def practice_setup(request: Request, index: Index):
    _cards, sessions = _practice(request, index)
    context = {
        "index": index,
        "today_count": sessions.count(index, SessionParams()),
        "modes": MODE_NAMES,
        "kinds": KIND_FILTERS,
        "directions": DIRECTIONS,
        "topics": index.all_topics(),
        "lessons": index.lessons(),
        "last_backup": request.app.state.progress_db.get_meta("last_backup_pushed"),
    }
    return templates.TemplateResponse(request, "vocab/practice_setup.html", context)


@router.post("/practice/start")
def practice_start(
    request: Request,
    index: Index,
    mode: Annotated[str, Form()] = "today",
    kind: Annotated[str, Form()] = "all",
    direction: Annotated[str, Form()] = "fr_ru",
    method: Annotated[str, Form()] = "self",
    lesson: Annotated[str, Form()] = "",
    topic: Annotated[str, Form()] = "",
):
    _cards, sessions = _practice(request, index)
    params = SessionParams(
        source="dictionary",
        mode=mode,
        kind=kind,
        direction=direction,
        method=method,
        lesson=int(lesson) if lesson else None,
        topic=topic or None,
    )
    return _redirect(f"/practice/{sessions.start(index, params)}")


@router.get("/lessons/{number}/practice")
def lesson_practice(request: Request, number: int, index: Index):
    if index.lesson(number) is None:
        raise not_found(f"Урок {number} не найден")
    _cards, sessions = _practice(request, index)
    params = SessionParams(source="lesson", mode="lesson", lesson=number)
    return _redirect(f"/practice/{sessions.start(index, params)}")


def _card_page(request: Request, index: ContentIndex, session_id: str, shown: bool, **extra):
    _cards, sessions = _practice(request, index)
    try:
        progress = sessions.progress(session_id)
    except KeyError:
        raise not_found("Сеанс не найден") from None
    params = sessions.params(session_id)
    current = sessions.current(session_id)
    context = {
        "index": index,
        "session_id": session_id,
        "progress": progress,
        "params": params,
        "mode_name": MODE_NAMES.get(params.mode, params.mode),
        "direction_name": DIRECTIONS[params.direction],
        "ratings": RATING_NAMES,
        "can_undo": sessions._load(session_id)[3] is not None,
        "symbols": FRENCH_SYMBOLS,
        **extra,
    }
    if current is None:
        context["summary"] = sessions.summary(session_id)
        return templates.TemplateResponse(request, "vocab/practice_summary.html", context)
    entry = index.element(current[0])
    context.update(
        entry=entry,
        direction=current[1],
        question=vocab_entries.question(index, entry, current[1]),
        answers=vocab_entries.accepted_answers(index, entry, current[1]),
        shown=shown,
    )
    return templates.TemplateResponse(request, "vocab/practice_card.html", context)


@router.get("/practice/{session_id}")
def practice_card(request: Request, session_id: str, index: Index):
    return _card_page(request, index, session_id, shown=False)


@router.post("/practice/{session_id}/show")
def practice_show(request: Request, session_id: str, index: Index):
    return _card_page(request, index, session_id, shown=True)


@router.post("/practice/{session_id}/rate")
def practice_rate(request: Request, session_id: str, index: Index, rating: Annotated[str, Form()]):
    _cards, sessions = _practice(request, index)
    if rating not in RATING_NAMES:
        raise not_found("Неизвестная оценка")
    if sessions.current(session_id) is not None:
        sessions.rate(session_id, rating)
    return _redirect(f"/practice/{session_id}")


@router.post("/practice/{session_id}/undo")
def practice_undo(request: Request, session_id: str, index: Index):
    _cards, sessions = _practice(request, index)
    sessions.undo(session_id)
    return _redirect(f"/practice/{session_id}")


@router.post("/practice/{session_id}/continue")
def practice_continue(request: Request, session_id: str, index: Index):
    _cards, sessions = _practice(request, index)
    sessions.continue_portion(session_id)
    return _redirect(f"/practice/{session_id}")


@router.post("/backup")
def backup_now(request: Request, index: Index):
    from french_learning.practice.backup import run_backup
    from french_learning.web.routes.topics import redirect_after_write

    state = request.app.state
    if state.progress_db is None:
        raise not_found("Хранилище не настроено")
    result = run_backup(state.progress_db, state.settings.content_dir)
    if not result.committed and not result.warning:
        return _redirect("/practice?notice=Копия уже актуальна, изменений нет.")
    return redirect_after_write("/practice", result)


# --- ввод ответа (US4) ----------------------------------------------------------------------


def _check(index: ContentIndex, entry, direction: str, answer: str):
    from french_learning.practice.checking import check_french, check_russian

    accepted = vocab_entries.accepted_answers(index, entry, direction)
    if direction == "fr_ru":
        return check_russian(answer, accepted), accepted
    return check_french(answer, accepted), accepted


def _result_page(request, index, session_id, entry, direction, answer, ok, accepted):
    _cards, sessions = _practice(request, index)
    context = {
        "index": index,
        "session_id": session_id,
        "entry": entry,
        "direction": direction,
        "question": vocab_entries.question(index, entry, direction),
        "answers": accepted,
        "given": answer,
        "ok": ok,
        "progress": sessions.progress(session_id),
    }
    return templates.TemplateResponse(request, "vocab/practice_result.html", context)


@router.post("/practice/{session_id}/answer")
def practice_answer(
    request: Request, session_id: str, index: Index, answer: Annotated[str, Form()] = ""
):
    _cards, sessions = _practice(request, index)
    current = sessions.current(session_id)
    if current is None:
        return _redirect(f"/practice/{session_id}")
    entry = index.element(current[0])
    result, accepted = _check(index, entry, current[1], answer)
    if result.status == "choose_spelling":
        return _card_page(
            request, index, session_id, shown=False, choose=result.variants, given=answer
        )
    ok = result.status == "correct"
    sessions.rate(session_id, "good" if ok else "again", answer=answer)
    return _result_page(request, index, session_id, entry, current[1], answer, ok, accepted)


@router.post("/practice/{session_id}/spelling")
def practice_spelling(
    request: Request,
    session_id: str,
    index: Index,
    answer: Annotated[str, Form()] = "",
    choice: Annotated[str, Form()] = "",
):
    _cards, sessions = _practice(request, index)
    current = sessions.current(session_id)
    if current is None:
        return _redirect(f"/practice/{session_id}")
    entry = index.element(current[0])
    result, accepted = _check(index, entry, current[1], answer)
    ok = result.status == "choose_spelling" and choice == result.matched
    sessions.rate(session_id, "good" if ok else "again", answer=choice or answer)
    return _result_page(request, index, session_id, entry, current[1], choice, ok, accepted)


# --- просмотр словаря (US2) -------------------------------------------------------------------

VOCAB_FILTERS = {
    "": "все",
    "known": "«Знаю»",
    "hidden": "скрытые",
    "incomplete": "нужно дополнить",
}


@router.get("/vocab")
def vocab_list(
    request: Request,
    index: Index,
    lesson: str = "",
    topic: str = "",
    kind: str = "",
    filter: str = "",
    view: str = "cards",
):
    cards, _sessions = _practice(request, index)
    items = vocab_entries.filter_entries(
        index,
        lesson=int(lesson) if lesson else None,
        topic=topic or None,
        kind=kind or None,
        flag=filter or None,
        known_ids=cards.known_ids(),
    )
    incomplete = len(vocab_entries.filter_entries(index, flag="incomplete"))
    used_topics = {t for e in vocab_entries.vocab_entries(index) for t in e.topics}
    context = {
        "index": index,
        "items": items,
        "view": "list" if view == "list" else "cards",
        "selected": {"lesson": lesson, "topic": topic, "kind": kind, "filter": filter},
        "filters": VOCAB_FILTERS,
        "kinds": {"": "все виды", "word": "слова", "verb": "глаголы", "phrase": "фразы"},
        "lessons": index.lessons(),
        "topics": [t for t in index.all_topics() if t.id in used_topics],
        "incomplete": incomplete,
        "display_fr": vocab_entries.display_fr,
    }
    return templates.TemplateResponse(request, "vocab/list.html", context)


# --- добавление слов (US3) --------------------------------------------------------------------


def _editor(request: Request):
    from french_learning.vocab.edits import VocabEditor

    return VocabEditor(request.app.state.settings.content_dir)


def _add_context(index: ContentIndex, **extra) -> dict:
    return {
        "index": index,
        "topics": index.all_topics(),
        "lessons": index.lessons(),
        "kinds": {"word": "слово", "verb": "глагол", "phrase": "фраза"},
        **extra,
    }


@router.get("/vocab/add")
def vocab_add_page(request: Request, index: Index):
    return templates.TemplateResponse(request, "vocab/add.html", _add_context(index))


@router.post("/vocab/add")
def vocab_add(
    request: Request,
    index: Index,
    text: Annotated[str, Form()] = "",
    translations: Annotated[str, Form()] = "",
    topic: Annotated[str, Form()] = "",
    article: Annotated[str, Form()] = "",
    gender: Annotated[str, Form()] = "",
    entry_type: Annotated[str, Form()] = "word",
    lesson: Annotated[str, Form()] = "",
    quick: Annotated[str, Form()] = "",
):
    from urllib.parse import urlencode

    from french_learning.content.writer import WriteError
    from french_learning.vocab.edits import VocabError
    from french_learning.vocab.parsing import Unrecognized, parse_line

    word = {
        "text": text,
        "translations": translations.replace(";", ",").split(","),
        "article": article or None,
        "gender": gender or None,
        "entry_type": entry_type,
        "pos": None,
    }
    if quick.strip():
        # одной строкой «артикль, слово - перевод»; род, выбранный в форме, важнее угаданного
        parsed = parse_line(1, quick)
        if isinstance(parsed, Unrecognized):
            return _redirect("/vocab/add?" + urlencode({"error": parsed.reason}))
        word.update(
            text=parsed.text,
            translations=parsed.translations,
            article=parsed.article,
            gender=gender or parsed.gender,
            entry_type=entry_type if entry_type != "word" else parsed.entry_type,
            pos=parsed.pos,
        )
    try:
        entry_id, merged = _editor(request).add_word(
            **word,
            topics=[topic] if topic else [],
            lesson=int(lesson) if lesson else None,
        )
    except (VocabError, WriteError) as exc:
        return _redirect("/vocab/add?" + urlencode({"error": str(exc)}))
    notice = "Перевод добавлен к существующему слову." if merged else "Слово добавлено."
    return _redirect(f"/vocab/{entry_id}?" + urlencode({"notice": notice}))


@router.post("/vocab/import")
def vocab_import(
    request: Request,
    index: Index,
    text: Annotated[str, Form()] = "",
    topic: Annotated[str, Form()] = "",
    lesson: Annotated[str, Form()] = "",
):
    from french_learning.content.writer import WriteError
    from french_learning.vocab.edits import VocabError

    try:
        report = _editor(request).import_list(
            text, topics=[topic] if topic else [], lesson=int(lesson) if lesson else None
        )
    except (VocabError, WriteError) as exc:
        return templates.TemplateResponse(
            request, "vocab/add.html", _add_context(index, error=str(exc), list_text=text)
        )
    return templates.TemplateResponse(
        request, "vocab/add.html", _add_context(index, report=report, topic=topic, lesson=lesson)
    )


@router.get("/vocab/complete")
def vocab_complete(request: Request, index: Index):
    items = vocab_entries.filter_entries(index, flag="incomplete")
    context = {"index": index, "items": items, "display_fr": vocab_entries.display_fr}
    return templates.TemplateResponse(request, "vocab/complete.html", context)


# --- управление записями (US5) ---------------------------------------------------------------


def _entry_action(request: Request, entry_id: str, action, done: str, target: str | None = None):
    from urllib.parse import urlencode

    from french_learning.content.writer import WriteError
    from french_learning.vocab.edits import VocabError

    url = target or f"/vocab/{entry_id}"
    try:
        result = action()
    except (VocabError, WriteError) as exc:
        return _redirect(f"/vocab/{entry_id}?" + urlencode({"error": str(exc)}))
    notice = done + (
        f" {result.warning[0].upper()}{result.warning[1:]}." if result and result.warning else ""
    )
    return _redirect(f"{url}?" + urlencode({"notice": notice}))


@router.post("/vocab/{entry_id}/edit")
def vocab_edit(
    request: Request,
    entry_id: str,
    translations: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
    gender: Annotated[str | None, Form()] = None,
):
    editor = _editor(request)
    return _entry_action(
        request,
        entry_id,
        lambda: editor.update(
            entry_id,
            translations=translations.replace(";", ",").split(","),
            notes=notes,
            gender=gender,
        ),
        "Сохранено.",
    )


@router.post("/vocab/{entry_id}/hide")
def vocab_hide(request: Request, entry_id: str):
    editor = _editor(request)
    return _entry_action(
        request, entry_id, lambda: editor.set_hidden(entry_id, True), "Слово скрыто."
    )


@router.post("/vocab/{entry_id}/unhide")
def vocab_unhide(request: Request, entry_id: str):
    editor = _editor(request)
    return _entry_action(
        request, entry_id, lambda: editor.set_hidden(entry_id, False), "Слово возвращено."
    )


@router.post("/vocab/{entry_id}/delete")
def vocab_delete(request: Request, entry_id: str):
    editor = _editor(request)

    def action():
        result = editor.delete(entry_id)
        if request.app.state.cards is not None:
            request.app.state.cards.remove_cards(entry_id)
        return result

    return _entry_action(request, entry_id, action, "Слово удалено.", target="/vocab")


@router.post("/vocab/{entry_id}/known")
def vocab_known(request: Request, entry_id: str, index: Index):
    cards, _sessions = _practice(request, index)
    cards.set_known(entry_id, True)
    return _redirect(f"/vocab/{entry_id}?notice=Слово исключено из повторения («Знаю»).")


@router.post("/vocab/{entry_id}/unknown")
def vocab_unknown(request: Request, entry_id: str, index: Index):
    cards, _sessions = _practice(request, index)
    cards.set_known(entry_id, False)
    return _redirect(f"/vocab/{entry_id}?notice=Слово снова в повторении.")


# --- настройки ---------------------------------------------------------------------------------


@router.get("/settings")
def settings_page(request: Request, index: Index):
    db = request.app.state.progress_db
    context = {
        "index": index,
        "portion_size": db.get_setting("portion_size"),
        "trainer_portion_size": db.get_setting("trainer_portion_size"),
        "directions": db.get_setting("directions"),
        "voice": db.get_setting("voice"),
        "voices": {key: name for key, (_code, name) in VOICES.items()},
        "voices_missing": not request.app.state.speaker.available(db.get_setting("voice")),
    }
    return templates.TemplateResponse(request, "vocab/settings.html", context)


@router.post("/settings")
def settings_save(
    request: Request,
    index: Index,
    portion_size: Annotated[str, Form()] = "20",
    trainer_portion_size: Annotated[str, Form()] = "",
    directions: Annotated[str, Form()] = "staged",
    voice: Annotated[str, Form()] = DEFAULT_VOICE,
):
    db = request.app.state.progress_db
    if not portion_size.isdigit() or not 1 <= int(portion_size) <= 500:
        return _redirect("/settings?error=размер порции — число от 1 до 500")
    if directions not in {"staged", "both"}:
        return _redirect("/settings?error=неизвестный режим направлений")
    if voice not in VOICES:
        return _redirect("/settings?error=неизвестный голос озвучки")
    db.set_setting("voice", voice)
    if trainer_portion_size:
        if not trainer_portion_size.isdigit() or not 1 <= int(trainer_portion_size) <= 500:
            return _redirect("/settings?error=порция тренажёров — число от 1 до 500")
        db.set_setting("trainer_portion_size", str(int(trainer_portion_size)))
    db.set_setting("portion_size", str(int(portion_size)))
    db.set_setting("directions", directions)
    return _redirect("/settings?notice=Настройки сохранены.")


# Маршрут записи — последним: иначе он перехватит /vocab/add и /vocab/complete.
@router.get("/vocab/{entry_id}")
def vocab_entry(request: Request, entry_id: str, index: Index):
    cards, _sessions = _practice(request, index)
    entry = index.element(entry_id)
    if entry is None or entry.kind != "vocab":
        raise not_found("Слово не найдено")
    context = {
        "index": index,
        "entry": entry,
        "display_fr": vocab_entries.display_fr,
        "indefinite": vocab_entries.indefinite(entry),
        "known": entry_id in cards.known_ids(),
        "history": cards.history(entry_id),
        "pos_names": vocab_entries.POS_NAMES,
        "kind_names": vocab_entries.KIND_NAMES,
    }
    return templates.TemplateResponse(request, "vocab/entry.html", context)
