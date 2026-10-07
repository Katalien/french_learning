# UI routes: 012

| Маршрут | Изменение |
|---|---|
| панель урока (`lesson_base.html`) | «Задания {класс}/{дом}», `title="в классе: N, дома: M"` |
| `GET /elements/{id}` упражнения, `POST …/check` | сетка и `:class="with-source"` — на `.exercise-layout` внутри `#exercise-solve` |
| `GET /tts?text=…` | WAV с 0,35 с тишины в начале |
| `GET /lessons/{n}/vocab`, `GET /topics/{id}` | без скрытых слов и без пометки «скрыто» |
| `GET /topics` | раздел «Лексика» — только темы с нескрытыми словами |
| `GET /vocab/{id}` | кнопка «Удалить слово» → окно подтверждения; клавиши ↓ / ↑ / Enter |
| `POST /vocab/{id}/delete` | удаляет любое слово → 303 на `/vocab`, сообщение «Слово удалено.» |
| `GET /` (главная) | «Повторение слов»: «N слов урока L»; форма `POST /practice/start` с `mode=lesson&lesson=L&direction=ru_fr` |
| `GET /trainers/numbers` | выбор формата: «цифрами → словами» / «словами → цифрами» |
| `POST /trainers/numbers/start` | поле `format` (`digits_to_words` \| `words_to_digits`) |
