// Подсказка у выделенного текста (005, 006; research R5 005, research R1 006).
// Содержимое подсказки собирается из «секций», которые регистрируют функции приложения:
// 006 — перевод (translate.js), 005 — полоска «пометка · вопрос» (notes.js).
// Зона выделения — контейнер заметок, блок [data-translate] или французский [lang="fr"];
// выделение через границу двух зон не считается.
(() => {
  const ZONES = "[data-note-container], [data-translate]";
  const NOTES = "[data-note-container]";
  const IGNORE = "input, textarea, select, button, .note-form, .sel-pop";
  const BLOCK = "p, li, td, th, h1, h2, h3, h4, blockquote, dd, dt, figcaption, article, section, div";
  const sections = [];
  let pop = null;
  let anchor = null; // место выделения в координатах документа
  let timer = null;

  const isWord = (ch) => ch !== undefined && /[\p{L}\p{M}\p{N}'’-]/u.test(ch);
  const elementOf = (node) => (node && node.nodeType === Node.TEXT_NODE ? node.parentElement : node);
  const zoneOf = (node) => {
    const el = elementOf(node);
    return el?.closest(ZONES) || el?.closest('[lang="fr"]') || null;
  };
  const notesOf = (node) => elementOf(node)?.closest(NOTES) || null;

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

  // предложение (или предложения) вокруг выделения — пример для словаря (006, research R7)
  function sentenceAround(range, zone) {
    const block = elementOf(range.startContainer).closest(BLOCK) || zone;
    const scope = block.contains(range.endContainer) ? block : zone;
    const before = document.createRange();
    before.setStart(scope, 0);
    before.setEnd(range.startContainer, range.startOffset);
    const whole = scope.textContent;
    const start = before.toString().length;
    const end = start + range.toString().length;
    const head = whole.slice(0, start);
    const cut = Math.max(...[".", "!", "?", "…", "\n"].map((c) => head.lastIndexOf(c)));
    const tail = whole.slice(end).search(/[.!?…]|\n/);
    const stop = tail === -1 ? whole.length : end + tail + 1;
    return whole.slice(cut + 1, stop).replace(/\s+/g, " ").trim().slice(0, 500);
  }

  function current() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
    const range = sel.getRangeAt(0);
    const zone = zoneOf(range.startContainer);
    if (!zone || zone !== zoneOf(range.endContainer)) return null;
    if (elementOf(range.commonAncestorContainer)?.closest(IGNORE)) return null;
    const expanded = expand(range);
    const text = expanded.toString().replace(/\s+/g, " ").trim();
    if (!text) return null;
    const notes = notesOf(range.startContainer);
    const noteContainer = notes && notes === notesOf(range.endContainer) ? notes : null;
    return {
      range: expanded,
      text,
      zone,
      noteContainer,
      container: noteContainer, // имя из 005
      elementId: noteContainer?.dataset.noteContainer,
      lesson: Number(zone.closest("[data-lesson]")?.dataset.lesson) || null,
      sentence: () => sentenceAround(expanded, zone),
    };
  }

  function close() {
    if (pop) pop.remove();
    pop = null;
  }

  // под выделением, а если снизу не хватает места — над ним; не шире и не левее экрана
  function place() {
    if (!pop || !anchor) return;
    const width = document.documentElement.clientWidth;
    const top = window.scrollY + 8;
    const bottom = window.scrollY + window.innerHeight - 8;
    const room = Math.max(bottom - anchor.bottom - 8, anchor.top - 8 - top);
    // не помещается ни под выделением, ни над ним — сжать прокручиваемую часть ([data-shrink])
    const shrink = pop.querySelector("[data-shrink]");
    if (shrink) shrink.style.maxHeight = "";
    if (shrink && pop.offsetHeight > room) {
      shrink.style.maxHeight = `${Math.max(80, shrink.offsetHeight - (pop.offsetHeight - room))}px`;
    }
    const height = pop.offsetHeight;
    const below = anchor.bottom + 8;
    const above = anchor.top - height - 8;
    let y = below; // под выделением; не влезает — над ним; нигде — у края окна
    if (below + height > bottom) y = above >= top ? above : Math.max(top, bottom - height);
    pop.style.top = `${y}px`;
    const left = Math.min(anchor.left, window.scrollX + width - pop.offsetWidth - 8);
    pop.style.left = `${Math.max(window.scrollX + 8, left)}px`;
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
    anchor = {
      top: rect.top + window.scrollY,
      bottom: rect.bottom + window.scrollY,
      left: rect.left + window.scrollX,
    };
    place();
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
    place, // секция изменилась (например, пришёл перевод) — поправить место подсказки
  };
})();
