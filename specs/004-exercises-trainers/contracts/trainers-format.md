# Contract: формат каталога тренажёров и пакетов заданий

Дополнение формата v1 (необязательные файлы; старое хранилище остаётся корректным).
Поля и проверки — [data-model.md](../data-model.md), раздел «Контент». Действующее
описание формата после реализации — `docs/content-format.md`.

- `trainers.yaml` — корень хранилища; ключ `trainers` — список записей каталога.
- `trainers/<trainer_id>/tb-<8 символов>.yaml` — пакет заданий (`kind: task_batch`).
- `reports/*.yaml` — `element` допускает `tb-…`.
- Поддерживаемые типы пакетов: `gap_input`, `gap_choice`, `multi_gap`, `transform`,
  `choice`, `two_forms`, `true_false`.
- Встроенные id (зарезервированы): `articles`, `conjugation`, `feminine`, `plural`,
  `possessives`, `demonstratives`, `adjective-agreement`, `numbers`, `sentence-builder`.
