# UI routes: изменения 010

Все адреса — на 127.0.0.1. Остальные маршруты 003/004 без изменений.

## Повторение слов

| Адрес | Было | Стало |
|---|---|---|
| `GET /lessons/{n}/practice` | сразу сеанс fr→ru, все слова урока | 303 → `/practice/setup?mode=lesson&lesson={n}`; 404, если урока нет |
| `GET /practice/setup` | без параметров | `?mode=&lesson=&topic=` выставляют форму; поле «Слов за подход»; поле темы с поиском; блок `#practice-count` |
| `GET /practice/count` | — | новый: параметры формы (`mode, lesson, topic, kind, direction`) → фрагмент «В сеансе: N карточек» или «Нет слов для повторения» |
| `POST /practice/start` | `mode, kind, direction, method, lesson, topic` | + `portion` (пусто = все, 1–500 → сохраняется в `portion_size`); пустая очередь → обратно на настройку с сообщением |
| `GET /settings`, `POST /settings` | `portion_size`, `directions` | оба поля убраны; прочие без изменений |

## Словарь

| Адрес | Стало |
|---|---|
| `GET /vocab` | ссылки на слова несут текущие `lesson, topic, kind, filter` |
| `GET /vocab/{id}?lesson=&topic=&kind=&filter=` | контекст `prev`, `next`, `position`, `total`; стрелки `.arrow.prev/.next` и «N из M» |

## Упражнения

| Адрес | Стало |
|---|---|
| `GET /elements/{id}` (упражнение) | нет ссылок «📖 Текст к упражнению» / «📘 Теория к упражнению»; на ≥ 900 px «рядом» открыто (текст, иначе теория); в панели — «Открыть отдельной страницей»; блок картинки при файле-картинке, свёрнут, если `show_source: false` |
| `POST /exercises/{id}/items/{item}/report` | ответ: разметка упражнения с подтверждением внутри пункта `item` (`.report-status`), метка «✉ сообщение отправлено»; пустой комментарий — подсказка у пункта, без записи |
| `GET /lessons/{n}/tasks?part=class` | у всех упражнений «✓ выполнено» |
