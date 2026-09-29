// Подсказка у выделенного текста в элементах урока (005, research R5).
// Содержимое подсказки собирается из «секций», которые регистрируют функции приложения:
// 005 — полоска «пометка · вопрос», 006 добавит перевод. Работает только внутри
// контейнеров [data-note-container]; выделение через границу двух элементов не считается.
(() => {
  const CONTAINER = "[data-note-container]";
  const IGNORE = "input, textarea, select, button, .note-form, .sel-pop";
  const sections = [];
  let pop = null;
  let timer = null;

  const isWord = (ch) => ch !== undefined && /[\p{L}\p{M}\p{N}'’-]/u.test(ch);
  const elementOf = (node) => (node && node.nodeType === Node.TEXT_NODE ? node.parentElement : node);
  const containerOf = (node) => elementOf(node)?.closest(CONTAINER) || null;

  // выделение, начатое или законченное посреди слова, расширяется до целых слов (006, FR-002)
  function expand(range) {
    const r = range.cloneRange();
    if (r.startContainer.nodeType === Node.TEXT_NODE) {
      const t = r.startContainer.textContent;
      let i = r.startOffset;
      while (i > 0 && isWord(t[i - 1]) && isWord(t[i])) i--;
      r.setStart(r.startContainer, i);
    }
    if (r.endContainer.nodeType === Node.TEXT_NODE) {
      const t = r.endContainer.textContent;
      let i = r.endOffset;
      while (i < t.length && isWord(t[i - 1]) && isWord(t[i])) i++;
      r.setEnd(r.endContainer, i);
    }
    return r;
  }

  function current() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
    const range = sel.getRangeAt(0);
    const container = containerOf(range.startContainer);
    if (!container || container !== containerOf(range.endContainer)) return null;
    if (elementOf(range.commonAncestorContainer)?.closest(IGNORE)) return null;
    const expanded = expand(range);
    const text = expanded.toString().replace(/\s+/g, " ").trim();
    if (!text) return null;
    return { range: expanded, text, container, elementId: container.dataset.noteContainer };
  }

  function close() {
    if (pop) pop.remove();
    pop = null;
  }

  function show() {
    close();
    const ctx = current();
    if (!ctx) return;
    const parts = sections.map((section) => section(ctx)).filter(Boolean);
    if (!parts.length) return;
    pop = document.createElement("div");
    pop.className = "sel-pop";
    pop.setAttribute("role", "dialog");
    pop.setAttribute("aria-label", "Действия с выделенным");
    parts.forEach((part) => pop.appendChild(part));
    document.body.appendChild(pop);
    const rect = ctx.range.getBoundingClientRect();
    const width = document.documentElement.clientWidth;
    pop.style.top = `${window.scrollY + rect.bottom + 8}px`;
    const left = Math.min(window.scrollX + rect.left, window.scrollX + width - pop.offsetWidth - 8);
    pop.style.left = `${Math.max(8, left)}px`;
  }

  document.addEventListener("mouseup", (event) => {
    if (event.target.closest(IGNORE)) return;
    setTimeout(show, 10);
  });
  document.addEventListener("mousedown", (event) => {
    if (pop && !pop.contains(event.target)) close();
  });
  document.addEventListener("touchstart", (event) => {
    if (pop && !pop.contains(event.target)) close();
  }, { passive: true });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") close();
  });
  // сенсорный экран: выделение долгим нажатием — ждём, пока оно перестанет меняться
  if (window.matchMedia("(pointer: coarse)").matches) {
    document.addEventListener("selectionchange", () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (!pop) show();
      }, 600);
    });
  }

  window.SelectionPopup = {
    register(section) {
      sections.push(section);
    },
    close,
  };
})();
