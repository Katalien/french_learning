"""Словарь и повторение карточек (функция 003, contracts/ui-routes.md)."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import RedirectResponse

from french_learning.content.index import ContentIndex
from french_learning.practice.checking import FRENCH_SYMBOLS
from french_learning.practice.tts import DEFAULT_VOICE, VOICES
from french_learning.vocab import entries as vocab_entries
from french_learning.vocab.sessions import SessionParams
from french_learning.web.deps import Index, not_found, show_origin
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
# 011: «Ошибка в артикле» — между «С трудом» и «Помню», только у ru_fr существительных с родом
ARTICLE_RATING = "Ошибка в артикле"


def _card_ratings(entry, direction: str) -> dict[str, str]:
    if not vocab_entries.article_rating_allowed(entry, direction):
        return RATING_NAMES
    return {"again": "Не помню", "hard": "С трудом", "article": ARTICLE_RATING, "good": "Помню"}


def _practice(request: Request, index: ContentIndex):
    state = request.app.state
    if state.cards is None:
        raise not_found("Хранилище не настроено")
    state.cards.sync(index)
    return state.cards, state.sessions


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


def _session_params(
    mode: str = "today",
    kind: str = "all",
    direction: str = "fr_ru",
    method: str = "self",
    lesson: str = "",
    topic: str = "",
    portion: int | None = None,
) -> SessionParams:
    return SessionParams(
        source="dictionary",
        mode=mode if mode in MODE_NAMES else "today",
        kind=kind if kind in KIND_FILTERS else "all",
        direction=direction if direction in DIRECTIONS else "fr_ru",
        method=method,
        lesson=int(lesson) if lesson.isdigit() else None,
        topic=topic or None,
        portion=portion,
    )


@router.get("/practice/setup")
def practice_setup(
    request: Request, index: Index, mode: str = "today", lesson: str = "", topic: str = ""
):
    """Настройка повторения; из урока приходят `mode=lesson&lesson=N` (010, пункт 3)."""
    _cards, sessions = _practice(request, index)
    params = _session_params(mode=mode, lesson=lesson, topic=topic)
    context = {
        "index": index,
        "today_count": sessions.count(index, SessionParams()),
        "count": 0
        if params.mode == "topic" and not params.topic
        else sessions.count(index, params),
        "modes": MODE_NAMES,
        "kinds": KIND_FILTERS,
        "directions": DIRECTIONS,
        "topic_options": [{"value": t.id, "label": t.name} for t in index.all_topics()],
        "lessons": index.lessons(),
        "selected": params,
        "portion_size": request.app.state.progress_db.get_setting("portion_size") or "20",
        "last_backup": request.app.state.progress_db.get_meta("last_backup_pushed"),
    }
    return templates.TemplateResponse(request, "vocab/practice_setup.html", context)


@router.get("/practice/count")
def practice_count(
    request: Request,
    index: Index,
    mode: str = "today",
    kind: str = "all",
    direction: str = "fr_ru",
    lesson: str = "",
    topic: str = "",
):
    """Сколько карточек будет в сеансе при текущих настройках (010, FR-007)."""
    _cards, sessions = _practice(request, index)
    params = _session_params(mode, kind, direction, lesson=lesson, topic=topic)
    count = 0 if mode == "topic" and not topic else sessions.count(index, params)
    return templates.TemplateResponse(
        request, "vocab/partials/practice_count.html", {"count": count}
    )


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
    portion: Annotated[str, Form()] = "",
    from_setup: Annotated[str, Form()] = "",
):
    """Запуск сеанса (010). `portion` со страницы настройки (`from_setup`): пусто — все.

    Без настройки (кнопки «Повторить» на «Сегодня» и в «Практике»): урок / тема — целиком,
    прочие режимы — последнее число «слов за подход».
    """
    _cards, sessions = _practice(request, index)
    back = f"/practice/setup?{urlencode({'mode': mode, 'lesson': lesson, 'topic': topic})}"
    size = None
    if not from_setup and not portion.strip():
        if mode not in ("lesson", "topic"):
            size = int(request.app.state.progress_db.get_setting("portion_size") or 20)
    elif portion.strip():
        if not portion.strip().isdigit() or not 1 <= int(portion) <= 500:
            return _redirect(f"{back}&{urlencode({'error': 'слов за подход — число от 1 до 500'})}")
        size = int(portion)
        request.app.state.progress_db.set_setting("portion_size", str(size))
    params = _session_params(mode, kind, direction, method, lesson, topic, size)
    if sessions.count(index, params) == 0:
        return _redirect(f"{back}&{urlencode({'notice': 'Нет слов для повторения.'})}")
    return _redirect(f"/practice/{sessions.start(index, params)}")


@router.get("/lessons/{number}/practice")
def lesson_practice(number: int, index: Index):
    """010, пункт 3: повторение слов урока начинается со страницы настройки."""
    if index.lesson(number) is None:
        raise not_found(f"Урок {number} не найден")
    return _redirect(f"/practice/setup?mode=lesson&lesson={number}")


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
        context["summary_ratings"] = {**RATING_NAMES, "article": ARTICLE_RATING}
        return templates.TemplateResponse(request, "vocab/practice_summary.html", context)
    entry = index.element(current[0])
    context.update(
        entry=entry,
        direction=current[1],
        question=vocab_entries.question(index, entry, current[1]),
        answers=vocab_entries.accepted_answers(index, entry, current[1]),
        shown=shown,
        ratings=_card_ratings(entry, current[1]),
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
    current = sessions.current(session_id)
    if current is not None:
        allowed = _card_ratings(index.element(current[0]), current[1])
        if rating not in allowed:
            raise not_found("Неизвестная оценка")
        sessions.rate(session_id, rating)
    elif rating not in RATING_NAMES and rating != "article":
        raise not_found("Неизвестная оценка")
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
        "query": _list_query(lesson, topic, kind, filter),
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
        "display_fr": vocab_entries.display_fr,
        **extra,
    }


@router.get("/vocab/add")
def vocab_add_page(request: Request, index: Index):
    """Выбор способа: по одному или списком (009)."""
    return templates.TemplateResponse(request, "vocab/add.html", _add_context(index))


@router.get("/vocab/add/one")
def vocab_add_one_page(
    request: Request,
    index: Index,
    topic: str = "",
    lesson: str = "",
    added: str = "",
    error: str = "",
):
    """Добавление по одному: серия слов до «Завершить»; тема и урок сохраняются (009)."""
    entries = [index.element(i) for i in added.split(",") if i]
    context = _add_context(
        index,
        topic=topic,
        lesson=lesson,
        added=[e for e in entries if e is not None and e.kind == "vocab"],
        error=error,
    )
    return templates.TemplateResponse(request, "vocab/add_one.html", context)


@router.get("/vocab/add/list")
def vocab_add_list_page(request: Request, index: Index):
    return templates.TemplateResponse(request, "vocab/add_list.html", _add_context(index))


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
    sequence: Annotated[str, Form()] = "",
    added: Annotated[str, Form()] = "",
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

    def back(**params) -> RedirectResponse:
        """Серия «по одному» — назад к форме с сохранёнными темой, уроком и списком."""
        base = {"topic": topic, "lesson": lesson, "added": added}
        return _redirect("/vocab/add/one?" + urlencode({**base, **params}))

    if quick.strip():
        # одной строкой «артикль, слово - перевод»; род, выбранный в форме, важнее угаданного
        parsed = parse_line(1, quick)
        if isinstance(parsed, Unrecognized):
            if sequence:
                return back(error=parsed.reason)
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
        if sequence:
            return back(error=str(exc))
        return _redirect("/vocab/add?" + urlencode({"error": str(exc)}))
    if sequence:
        ids = [i for i in added.split(",") if i and i != entry_id] + [entry_id]
        return back(added=",".join(ids))
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
            request, "vocab/add_list.html", _add_context(index, error=str(exc), list_text=text)
        )
    return templates.TemplateResponse(
        request,
        "vocab/add_list.html",
        _add_context(index, report=report, topic=topic, lesson=lesson),
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
        "trainer_portion_size": db.get_setting("trainer_portion_size"),
        "exercise_list_view": db.get_setting("exercise_list_view"),
        "voice": db.get_setting("voice"),
        "voices": {key: name for key, (_code, name) in VOICES.items()},
        "voices_missing": not request.app.state.speaker.available(db.get_setting("voice")),
        "search_translations": db.get_setting("search_translations") != "0",
    }
    from french_learning.web.routes.translate import settings_context

    context.update(settings_context(request))
    return templates.TemplateResponse(request, "vocab/settings.html", context)


@router.post("/settings")
def settings_save(
    request: Request,
    index: Index,
    trainer_portion_size: Annotated[str, Form()] = "",
    exercise_list_view: Annotated[str, Form()] = "",
    voice: Annotated[str, Form()] = DEFAULT_VOICE,
    search_translations: Annotated[str, Form()] = "0",
):
    db = request.app.state.progress_db
    if voice not in VOICES:
        return _redirect("/settings?error=неизвестный голос озвучки")
    db.set_setting("voice", voice)
    if trainer_portion_size:
        if not trainer_portion_size.isdigit() or not 1 <= int(trainer_portion_size) <= 500:
            return _redirect("/settings?error=порция тренажёров — число от 1 до 500")
        db.set_setting("trainer_portion_size", str(int(trainer_portion_size)))
    if exercise_list_view:
        if exercise_list_view not in ("rows", "tiles"):
            return _redirect("/settings?error=неизвестный вид списка заданий")
        db.set_setting("exercise_list_view", exercise_list_view)
    db.set_setting("search_translations", "1" if search_translations == "1" else "0")
    return _redirect("/settings?notice=Настройки сохранены.")


# Маршрут записи — последним: иначе он перехватит /vocab/add и /vocab/complete.
def _list_query(lesson: str, topic: str, kind: str, filter: str) -> str:
    """Фильтры списка словаря для ссылок на слово и переходов «‹ ›» (010, пункт 1)."""
    pairs = {"lesson": lesson, "topic": topic, "kind": kind, "filter": filter}
    return urlencode({k: v for k, v in pairs.items() if v})


def _source_list(index: ContentIndex, source: str, lesson: str, topic: str):
    """Список слов страницы урока или темы — в том же порядке, что на странице (0.9.1).

    Возвращает (слова, строка запроса для стрелок, (адрес назад, подпись)) или None.
    """
    if source == "lesson" and lesson.isdigit() and index.lesson(int(lesson)) is not None:
        new, repeat = index.lesson_vocabulary(int(lesson))
        query = urlencode({"from": "lesson", "lesson": lesson})
        return new + repeat, query, (f"/lessons/{lesson}/vocab", f"Урок {lesson} › Лексика")
    if source == "topic" and topic and index.topic(topic) is not None:
        words = [e for e in index.topic_elements(topic) if e.kind == "vocab"]
        query = urlencode({"from": "topic", "topic": topic})
        return words, query, (f"/topics/{topic}?tab=words", index.topic(topic).name)
    return None


def _neighbours(
    index: ContentIndex, entry_id: str, known: set[str], source: str = "", **filters: str
) -> dict:
    """Соседи слова в списке, из которого его открыли (урок, тема, словарь с фильтрами);
    иначе — во всём словаре."""
    from_page = _source_list(index, source, filters["lesson"], filters["topic"])
    if from_page is not None:
        items, query, back = from_page
    else:
        query = _list_query(**filters)
        back = (f"/vocab?{query}" if query else "/vocab", "Словарь")
        lesson = filters["lesson"]
        items = vocab_entries.filter_entries(
            index,
            lesson=int(lesson) if lesson.isdigit() else None,
            topic=filters["topic"] or None,
            kind=filters["kind"] or None,
            flag=filters["filter"] or None,
            known_ids=known,
        )
    ids = [e.id for e in items]
    if entry_id not in ids:
        query, back = "", ("/vocab", "Словарь")
        items = vocab_entries.filter_entries(index, known_ids=known)
        ids = [e.id for e in items]
    if entry_id not in ids:
        return {}
    at = ids.index(entry_id)
    return {
        "prev": items[at - 1] if at > 0 else None,
        "next": items[at + 1] if at + 1 < len(items) else None,
        "position": at + 1,
        "total": len(items),
        "query": query,
        "back": back,
    }


@router.get("/vocab/{entry_id}")
def vocab_entry(
    request: Request,
    entry_id: str,
    index: Index,
    lesson: str = "",
    topic: str = "",
    kind: str = "",
    filter: str = "",
    source: Annotated[str, Query(alias="from")] = "",
):
    cards, _sessions = _practice(request, index)
    entry = index.element(entry_id)
    if entry is None or entry.kind != "vocab":
        raise not_found("Слово не найдено")
    known = cards.known_ids()
    context = {
        "index": index,
        "entry": entry,
        "display_fr": vocab_entries.display_fr,
        "indefinite": vocab_entries.indefinite(entry),
        "known": entry_id in known,
        "nav": _neighbours(
            index, entry_id, known, source, lesson=lesson, topic=topic, kind=kind, filter=filter
        ),
        "history": cards.history(entry_id),
        "pos_names": vocab_entries.POS_NAMES,
        "kind_names": vocab_entries.KIND_NAMES,
        "show_origin": show_origin(request),
    }
    return templates.TemplateResponse(request, "vocab/entry.html", context)
