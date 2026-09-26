"""Просмотр упражнения (FR-021, FR-023–FR-025)."""

import pytest

ALL_EXERCISES = {
    "ex-gapchoic": "Вставьте le, la, l' или les.",
    "ex-gapinput": "Поставьте глагол в настоящее время.",
    "ex-truefals": "Верно или неверно?",
    "ex-choicecf": "Выберите правильный ответ.",
    "ex-multigap": "Вставьте артикли.",
    "ex-transfor": "Поставьте предложения в отрицательную форму.",
    "ex-twoforms": "Выберите правильную форму.",
    "ex-grouping": "Распределите слова по роду.",
    "ex-picturea": "Опишите, что есть в сумке, по картинке.",
    "ex-openansw": "Напишите 3 предложения о своём завтраке.",
}


@pytest.mark.parametrize(("element_id", "instruction"), ALL_EXERCISES.items())
def test_every_type_shows_instruction_and_items(client, element_id, instruction):
    response = client.get(f"/elements/{element_id}")
    assert response.status_code == 200
    html = response.text
    assert instruction.replace("'", "&#39;") in html or instruction in html


def test_answers_are_hidden(client):
    html = client.get("/elements/ex-gapinput").text
    assert "Je" in html and "étudiante" in html
    assert "suis" not in html  # правильный ответ пропуска
    assert "(être)" in html  # подсказка видна

    html = client.get("/elements/ex-transfor").text
    assert "Je ne suis pas fatiguée." not in html


def test_reference_is_collapsed(client):
    html = client.get("/elements/ex-transfor").text
    assert "Справка" in html
    assert 'x-show="reference"' in html


def test_picture_exercise_shows_source(client):
    html = client.get("/elements/ex-picturea").text
    assert 'src="/sources/lessons/001/sources/picture.jpg"' in html


def test_broken_element_shows_data_error(client):
    html = client.get("/elements/ex-brokenaa").text
    assert "Ошибка в данных" in html
    assert 'href="/problems"' in html
