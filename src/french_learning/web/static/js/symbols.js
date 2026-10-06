// Панель французских символов (003 FR-040, 004 FR-010): кнопка .symbol[data-char] вставляет
// символ в последнее поле ввода, где был курсор, — в ту же позицию.
let lastField = null;

document.addEventListener("focusin", (event) => {
  const field = event.target;
  if (field.matches("input:not([type]), input[type=text], textarea")) lastField = field;
});

// кнопка не забирает фокус у поля
document.addEventListener("mousedown", (event) => {
  if (event.target.closest(".symbol[data-char]")) event.preventDefault();
});

document.addEventListener("click", (event) => {
  const button = event.target.closest(".symbol[data-char]");
  if (!button) return;
  const panel = button.closest("form");
  let field = lastField;
  if (!field || !document.contains(field) || (panel && !panel.contains(field))) {
    field = panel && panel.querySelector("input:not([type]), input[type=text], textarea");
  }
  if (!field) return;
  const ch = button.dataset.char;
  const start = field.selectionStart ?? field.value.length;
  const end = field.selectionEnd ?? start;
  field.value = field.value.slice(0, start) + ch + field.value.slice(end);
  field.focus();
  field.setSelectionRange(start + ch.length, start + ch.length);
  field.dispatchEvent(new Event("input", { bubbles: true }));
});

// 010 пункт 4: в упражнении панель одна (data-floating) и показывается под полем, в котором
// курсор, — в конце пункта этого поля; когда фокус уходит из полей формы, панель скрывается.
const TEXT_FIELD = "input:not([type]), input[type=text], textarea";

document.addEventListener("focusin", (event) => {
  const field = event.target;
  if (!field.matches(TEXT_FIELD)) return;
  const form = field.closest("form");
  const panel = form && form.querySelector(".symbol-panel[data-floating]");
  if (!panel) return;
  const item = field.closest("li") || field.parentElement;
  if (panel.parentElement !== item) item.append(panel);
  panel.hidden = false;
});

document.addEventListener("focusout", (event) => {
  const form = event.target.closest && event.target.closest("form");
  const panel = form && form.querySelector(".symbol-panel[data-floating]");
  if (!panel) return;
  const next = event.relatedTarget;
  if (next && form.contains(next) && (next.matches(TEXT_FIELD) || panel.contains(next))) return;
  panel.hidden = true;
});
