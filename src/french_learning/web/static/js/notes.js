// Заметки (005): отметки фрагментов, поле справа по кнопке, заметка по щелчку на фрагменте,
// окна создания и правки, вопросы с ответом, строки добавления на странице урока.
// Данные страницы — <script data-notes-json>, изменения — JSON API /notes (contracts/notes-api.md).
// Разметка заметки совпадает с partials/note_item.html. Поиск фрагмента — research R2.
(() => {
  const state = {
    notes: new Map(), // id → заметка элементов этой страницы
    lost: new Set(), // якорь не найден в тексте
    open: new Set(), // элементы с открытым полем справа
    float: null, // открытая по щелчку заметка
    rebind: null, // заметка, которую привязывают заново
  };
  const CONTEXT = 32;
  const SKIP = "script, style, select, option, textarea, button, .note-ui, .sel-pop";
  const wide = () => !window.matchMedia("(max-width: 760px)").matches;

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const icon = (id, cls = "") => `<svg class="icon ${cls}" aria-hidden="true"><use href="#i-${id}"/></svg>`;

  function toast(text) {
    const box = document.createElement("div");
    box.className = "note-toast note-ui";
    box.setAttribute("role", "status");
    box.textContent = text;
    document.body.appendChild(box);
    setTimeout(() => box.remove(), 2600);
  }

  async function api(method, url, body) {
    const response = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    }).catch(() => null);
    if (!response) {
      toast("Не сохранено: приложение не отвечает");
      throw new Error("offline");
    }
    if (response.status === 204) return null;
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      toast(`Не сохранено: ${data.error || response.status}`);
      throw new Error(data.error || String(response.status));
    }
    return data;
  }

  // --- текст контейнера со сжатыми пробелами и поиск фрагмента (research R2) ------------------

  function textIndex(container) {
    const map = [];
    let text = "";
    let space = true;
    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (n.parentElement.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
    });
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const t = node.textContent;
      for (let i = 0; i < t.length; i++) {
        if (/\s/.test(t[i])) {
          if (space) continue;
          text += " ";
          space = true;
        } else {
          text += t[i];
          space = false;
        }
        map.push([node, i]);
      }
    }
    return { text, map };
  }

  // номер первого символа сжатого текста, стоящего не раньше точки (node, offset)
  function indexAt(idx, node, offset) {
    const point = document.createRange();
    point.setStart(node, offset);
    let lo = 0;
    let hi = idx.map.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      const [n, o] = idx.map[mid];
      if (point.comparePoint(n, o) < 0) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  }

  function anchorFromRange(container, range) {
    const idx = textIndex(container);
    let s = indexAt(idx, range.startContainer, range.startOffset);
    let e = indexAt(idx, range.endContainer, range.endOffset);
    while (s < e && idx.text[s] === " ") s++;
    while (e > s && idx.text[e - 1] === " ") e--;
    if (s >= e) return null;
    return {
      exact: idx.text.slice(s, e).slice(0, 500),
      prefix: idx.text.slice(Math.max(0, s - CONTEXT), s),
      suffix: idx.text.slice(e, e + CONTEXT),
      start: s,
    };
  }

  function commonTail(a, b) {
    let n = 0;
    while (n < a.length && n < b.length && a[a.length - 1 - n] === b[b.length - 1 - n]) n++;
    return n;
  }

  function commonHead(a, b) {
    let n = 0;
    while (n < a.length && n < b.length && a[n] === b[n]) n++;
    return n;
  }

  // из всех вхождений фразы — то, у которого больше совпадает контекст, затем ближайшее к start
  function findAnchor(idx, anchor) {
    const exact = anchor.exact.replace(/\s+/g, " ").trim();
    if (!exact) return null;
    let best = null;
    for (let at = idx.text.indexOf(exact); at !== -1; at = idx.text.indexOf(exact, at + 1)) {
      const before = idx.text.slice(Math.max(0, at - CONTEXT), at);
      const after = idx.text.slice(at + exact.length, at + exact.length + CONTEXT);
      const score = commonTail(before, anchor.prefix || "") + commonHead(after, anchor.suffix || "");
      const distance = Math.abs(at - (anchor.start || 0));
      if (!best || score > best.score || (score === best.score && distance < best.distance)) {
        best = { start: at, end: at + exact.length, score, distance };
      }
    }
    return best;
  }

  // обернуть символы [s, e) сжатого текста в <mark>; кусок в каждом текстовом узле — отдельно
  function wrap(idx, s, e, ids, extraClass = "") {
    const pieces = new Map();
    for (let i = s; i < e; i++) {
      const [node, offset] = idx.map[i];
      const piece = pieces.get(node) || { from: offset, to: offset + 1 };
      piece.from = Math.min(piece.from, offset);
      piece.to = Math.max(piece.to, offset + 1);
      pieces.set(node, piece);
    }
    const marks = [];
    for (const [node, { from, to }] of pieces) {
      let target = node;
      if (from > 0) target = target.splitText(from);
      if (to - from < target.textContent.length) target.splitText(to - from);
      const mark = document.createElement("mark");
      mark.className = `note-anchor ${extraClass}`.trim();
      mark.dataset.notes = ids.join(" ");
      target.replaceWith(mark);
      mark.appendChild(target);
      marks.push(mark);
    }
    return marks;
  }

  function unwrapAll(selector) {
    document.querySelectorAll(selector).forEach((mark) => {
      const parent = mark.parentNode;
      mark.replaceWith(...mark.childNodes);
      parent.normalize();
    });
  }

  function placeAnchors() {
    unwrapAll("mark.note-anchor");
    state.lost.clear();
    document.querySelectorAll("[data-note-container]").forEach((container) => {
      const own = [...state.notes.values()].filter((n) => n.anchor && n.element_id === container.dataset.noteContainer);
      for (const note of own) {
        const idx = textIndex(container); // после каждой обёртки узлы меняются
        const found = findAnchor(idx, note.anchor);
        if (found) wrap(idx, found.start, found.end, [note.id]);
        else state.lost.add(note.id);
      }
    });
  }

  const marksFor = (id) =>
    [...document.querySelectorAll("mark.note-anchor")].filter((m) => m.dataset.notes.split(" ").includes(String(id)));

  // все заметки места: сама отметка и отметки, в которые она вложена
  function idsAt(mark) {
    const ids = [];
    for (let m = mark; m; m = m.parentElement?.closest("mark.note-anchor")) {
      m.dataset.notes.split(" ").forEach((id) => ids.push(Number(id)));
    }
    return [...new Set(ids)];
  }

  // --- разметка заметки (как partials/note_item.html) -----------------------------------------

  function meta(n) {
    const kind =
      n.kind === "question" ? (n.answered ? "Вопрос · отвечен" : "Вопрос") : n.important ? "Важная пометка" : "Пометка";
    const where = n.element_title || `Урок ${n.lesson}`;
    const frag = n.anchor ? ` · к «${n.anchor.exact}»` : "";
    return `${kind} · ${where}${frag} · ${n.created_at.slice(0, 10)}`;
  }

  function noteHTML(n, { withId = false } = {}) {
    const question = n.kind === "question";
    const cls = [
      "note-item",
      question && !n.answered ? "q" : "",
      question && n.answered ? "done" : "",
      n.important ? "imp" : "",
      n.anchor ? "frag" : "",
    ].join(" ");
    const ic = question ? (n.answered ? "✓" : "?") : n.important ? "★" : "";
    const answer = question && n.answer ? `<div class="note-ans">→ ${esc(n.answer)}</div>` : "";
    const lost = state.lost.has(n.id)
      ? `<div class="note-lost">место не найдено · <button type="button" data-note-act="rebind">привязать заново</button></div>`
      : "";
    const ok = question && !n.answered ? `<button type="button" data-note-act="answer" title="Ответ получен">✓</button>` : "";
    return `<div class="${cls}" data-note-id="${n.id}" ${withId ? `id="note-${n.id}"` : ""} title="${esc(meta(n))}">
      ${ic ? `<span class="note-ic">${ic}</span>` : ""}
      <div class="note-tx">${esc(n.body)}${answer}${lost}</div>
      <span class="note-acts">${ok}<button type="button" data-note-act="edit" title="Изменить">✎</button><button type="button" data-note-act="delete" title="Удалить">🗑</button></span>
    </div>`;
  }

  // --- элементы страницы: кнопки, важные, поле справа -----------------------------------------
  // На странице элемента он один; в разделах урока «Теория» и «Тексты» — несколько подряд.
  // Кнопки и полоска важных связаны с элементом значением атрибута (data-notes-toggle="id").

  const sel = (attr, id) => `[${attr}="${CSS.escape(id)}"]`;
  const layouts = () => [...document.querySelectorAll("[data-notes-layout][data-notes-element]")];
  const layoutOf = (id) => document.querySelector(`[data-notes-layout]${sel("data-notes-element", id)}`);
  const marginOf = (id) => layoutOf(id)?.querySelector("[data-notes-margin]");
  const elementOf = (node) => node.closest("[data-notes-layout][data-notes-element]")?.dataset.notesElement;
  const elementNotes = (id) => [...state.notes.values()].filter((n) => n.element_id === id);

  function renderElement() {
    layouts().forEach((box) => renderOne(box.dataset.notesElement));
    // разделы «Теория» и «Тексты»: пока открыто поле, оглавление свёрнуто (макет v8)
    document.querySelectorAll("[data-notes-collapse]").forEach((node) => {
      const open = [...node.querySelectorAll("[data-notes-margin]")].some((m) => !m.hidden);
      node.classList.toggle("notes-open", open);
    });
  }

  function renderOne(id) {
    const notes = elementNotes(id);
    const open = state.open.has(id);
    const toggle = document.querySelector(sel("data-notes-toggle", id));
    if (toggle) {
      toggle.dataset.count = notes.length;
      toggle.querySelector(".n").textContent = notes.length || "";
      toggle.classList.toggle("empty", !notes.length);
      toggle.setAttribute("aria-expanded", String(open));
    }
    const strip = document.querySelector(sel("data-notes-important", id));
    if (strip) strip.innerHTML = notes.filter((n) => n.important).map((n) => noteHTML(n)).join("");
    const box = layoutOf(id);
    const margin = box?.querySelector("[data-notes-margin]");
    if (!margin) return;
    box.classList.toggle("with-margin", open);
    margin.hidden = !open;
    if (!open) {
      margin.innerHTML = "";
      return;
    }
    const kind = { exercise: "упражнению", text: "тексту", theory: "разделу" }[margin.dataset.kind] || "элементу";
    const onPlace = (n) => n.anchor && !state.lost.has(n.id);
    const whole = notes.filter((n) => !n.important && !onPlace(n));
    const frag = notes
      .filter((n) => !n.important && onPlace(n))
      .sort((a, b) => {
        const [ma, mb] = [marksFor(a.id)[0], marksFor(b.id)[0]];
        return ma && mb && ma.compareDocumentPosition(mb) & Node.DOCUMENT_POSITION_PRECEDING ? 1 : -1;
      });
    margin.innerHTML =
      (whole.length ? `<div class="note-cap">Ко всему ${kind}</div>` : "") +
      whole.map((n) => noteHTML(n, { withId: true })).join("") +
      (frag.length ? `<div class="note-cap" data-cap="frag">К фрагментам</div>` : "") +
      frag.map((n) => noteHTML(n, { withId: true }).replace('class="note-item', 'data-anchored="1" class="note-item')).join("") +
      `<button type="button" class="note-add" data-note-act="add-whole">+ заметка</button>`;
    requestAnimationFrame(() => layoutMargin(margin));
  }

  const layoutMargins = () => state.open.forEach((id) => layoutMargin(marginOf(id)));

  // заметки к фрагментам — на уровне своих строк, остальные — сверху, без наложений
  function layoutMargin(margin) {
    if (!margin || margin.hidden) return;
    const items = [...margin.children];
    if (!wide()) {
      items.forEach((node) => (node.style.top = ""));
      margin.style.minHeight = "";
      return;
    }
    const top0 = margin.getBoundingClientRect().top;
    const want = (node) => {
      if (!node?.dataset.anchored) return -1;
      const mark = marksFor(node.dataset.noteId)[0];
      return mark ? mark.getBoundingClientRect().top - top0 - 2 : -1;
    };
    let y = 0;
    for (const node of items) {
      const target = node.dataset.cap === "frag" ? want(node.nextElementSibling) - 18 : want(node);
      const top = Math.max(target, y);
      node.style.top = `${top}px`;
      y = top + node.offsetHeight + 6;
    }
    margin.style.minHeight = `${y}px`;
  }

  function flash(node) {
    node.classList.remove("flash");
    void node.offsetWidth;
    node.classList.add("flash");
  }

  // --- заметка по щелчку на фрагменте ----------------------------------------------------------

  function closeFloat() {
    state.float?.remove();
    state.float = null;
    document.querySelectorAll(".hl").forEach((node) => node.classList.remove("hl"));
  }

  function showFloat(mark) {
    closeFloat();
    const ids = idsAt(mark).filter((id) => state.notes.has(id));
    if (!ids.length) return;
    const margin = marginOf(elementOf(mark) || "");
    if (margin && !margin.hidden) {
      // поле открыто — подсветить заметки на поле
      ids.forEach((id) => {
        const item = margin.querySelector(`[data-note-id="${id}"]`);
        if (item) {
          item.classList.add("hl");
          item.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
        marksFor(id).forEach((m) => m.classList.add("hl"));
      });
      return;
    }
    const box = document.createElement("div");
    box.className = "note-float-list note-ui";
    box.innerHTML = ids.map((id) => noteHTML(state.notes.get(id))).join("");
    document.body.appendChild(box);
    const rect = mark.getBoundingClientRect();
    const card = (mark.closest(".card, .reading, .split-main") || mark.closest("[data-note-container]")).getBoundingClientRect();
    const width = document.documentElement.clientWidth;
    if (card.right + 16 + 260 <= width - 8) {
      box.style.left = `${window.scrollX + card.right + 16}px`;
      box.style.top = `${window.scrollY + rect.top - 4}px`;
    } else {
      box.style.left = `${Math.max(8, Math.min(window.scrollX + rect.left, window.scrollX + width - 268))}px`;
      box.style.top = `${window.scrollY + rect.bottom + 6}px`;
    }
    ids.forEach((id) => marksFor(id).forEach((m) => m.classList.add("hl")));
    state.float = box;
  }

  // --- окно заметки ----------------------------------------------------------------------------

  function openForm({ at, below = true, replace = null, note = null, kind = "note", onSave, onCancel }) {
    document.querySelectorAll(".note-form").forEach((f) => f.remove());
    document.querySelectorAll("[data-editing]").forEach((n) => {
      n.hidden = false;
      delete n.dataset.editing;
    });
    let k = note ? note.kind : kind;
    let important = note ? note.important : false;
    const form = document.createElement("div");
    form.className = "note-form note-ui";
    const question = note && note.kind === "question";
    form.innerHTML = `<textarea aria-label="Текст заметки" placeholder="${k === "question" ? "Что спросить…" : "На что обратить внимание…"}">${esc(note?.body)}</textarea>
      ${question ? `<textarea data-answer aria-label="Ответ" placeholder="Ответ (если уже знаете)">${esc(note.answer)}</textarea>` : ""}
      <div class="row">
        <button type="button" class="tg q" data-t="question" title="Вопрос к преподавательнице">${icon("question")}</button>
        <button type="button" class="tg imp" data-t="imp" title="Важная — всегда на виду">★</button>
        <span class="sp"></span>
        <button type="button" class="outline btn-sm" data-f="cancel">Отмена</button>
        <button type="button" class="btn-sm" data-f="save">Сохранить</button>
      </div>`;
    const sync = () => {
      form.querySelector('[data-t="question"]').classList.toggle("on", k === "question");
      form.querySelector('[data-t="imp"]').classList.toggle("on", important);
    };
    form.querySelector('[data-t="question"]').onclick = () => {
      k = k === "question" ? "note" : "question";
      sync();
    };
    form.querySelector('[data-t="imp"]').onclick = () => {
      important = !important;
      sync();
    };
    sync();
    if (replace) {
      replace.hidden = true;
      replace.dataset.editing = "1";
      replace.after(form);
    } else {
      form.classList.add("floating");
      document.body.appendChild(form);
      const rect = at.getBoundingClientRect();
      const width = document.documentElement.clientWidth;
      const left = Math.min(window.scrollX + rect.left, window.scrollX + width - form.offsetWidth - 8);
      form.style.left = `${Math.max(8, left)}px`;
      form.style.top = `${window.scrollY + (below ? rect.bottom + 6 : rect.top)}px`;
    }
    const text = form.querySelector("textarea");
    text.focus();
    const cancel = () => {
      form.remove();
      if (replace) replace.hidden = false;
      onCancel?.();
    };
    const save = async () => {
      const body = text.value.trim();
      if (!body) return text.focus();
      const values = { body, kind: k, important };
      const answer = form.querySelector("[data-answer]");
      if (answer && k === "question") values.answer = answer.value;
      try {
        await onSave(values);
        form.remove();
      } catch {
        text.focus();
      }
    };
    form.querySelector('[data-f="cancel"]').onclick = cancel;
    form.querySelector('[data-f="save"]').onclick = save;
    form.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        save();
      } else if (event.key === "Escape") {
        event.stopPropagation();
        cancel();
      }
    });
    return form;
  }

  function answerForm(after, onSave) {
    document.querySelectorAll(".note-form").forEach((f) => f.remove());
    const form = document.createElement("div");
    form.className = "note-form note-ui";
    form.innerHTML = `<textarea aria-label="Ответ" placeholder="Ответ (можно не писать) · Enter — закрыть вопрос"></textarea>
      <div class="row"><span class="sp"></span>
        <button type="button" class="outline btn-sm" data-f="cancel">Отмена</button>
        <button type="button" class="btn-sm" data-f="save" title="Закрыть вопрос">✓</button></div>`;
    after.after(form);
    const text = form.querySelector("textarea");
    text.focus();
    const save = () => onSave(text.value).then(() => form.remove()).catch(() => text.focus());
    form.querySelector('[data-f="cancel"]').onclick = () => form.remove();
    form.querySelector('[data-f="save"]').onclick = save;
    form.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        save();
      } else if (event.key === "Escape") form.remove();
    });
    const margin = after.closest("[data-notes-margin]");
    if (margin) requestAnimationFrame(() => layoutMargin(margin));
  }

  function confirmDelete(note) {
    return new Promise((resolve) => {
      const dialog = document.createElement("dialog");
      dialog.className = "note-dialog note-ui";
      dialog.innerHTML = `<strong>Удалить заметку?</strong><p class="small muted"></p>
        <div class="row"><button type="button" class="outline" value="no">Отмена</button><button type="button" class="danger" value="yes">Удалить</button></div>`;
      dialog.querySelector("p").textContent = `«${note.body.slice(0, 80)}${note.body.length > 80 ? "…" : ""}»`;
      document.body.appendChild(dialog);
      dialog.addEventListener("click", (event) => {
        const button = event.target.closest("button");
        if (button || event.target === dialog) dialog.close(button?.value || "no");
      });
      dialog.addEventListener("close", () => {
        resolve(dialog.returnValue === "yes");
        dialog.remove();
      });
      dialog.showModal();
    });
  }

  // --- изменения -------------------------------------------------------------------------------

  function remember(note) {
    state.notes.set(note.id, note);
    refreshPage();
  }

  function refreshPage() {
    closeFloat();
    placeAnchors();
    renderElement();
    updateBadge();
  }

  async function updateBadge() {
    const data = await fetch("/questions/count").then((r) => r.json()).catch(() => null);
    if (!data) return;
    const badge = document.querySelector("[data-questions-count]");
    if (!badge) return;
    badge.dataset.questionsCount = data.open;
    badge.querySelector("span").textContent = data.open;
    badge.hidden = !data.open;
  }

  function refreshRegion(node) {
    const region = node?.closest("[data-notes-region]");
    if (region && window.htmx) window.htmx.ajax("GET", region.dataset.refresh, { target: region, swap: "outerHTML" });
    updateBadge();
  }

  async function noteById(id) {
    return state.notes.get(id) || api("GET", `/notes/${id}`);
  }

  async function act(button) {
    const item = button.closest("[data-note-id]");
    const id = Number(item?.dataset.noteId);
    const action = button.dataset.noteAct;
    const inRegion = Boolean(item?.closest("[data-notes-region]"));
    if (action === "add-whole") return addWhole(button, elementOf(button));
    const note = await noteById(id);
    if (action === "answer") {
      const row = item.querySelector(".qi-row") || item;
      answerForm(row, async (answer) => {
        const saved = await api("PATCH", `/notes/${id}`, { answer, answered: true });
        inRegion ? refreshRegion(item) : remember(saved);
        toast("Вопрос закрыт");
      });
    } else if (action === "reopen") {
      await api("PATCH", `/notes/${id}`, { answered: false });
      refreshRegion(item);
    } else if (action === "edit") {
      const floating = item.closest(".note-float-list");
      const place = floating ? { at: item } : { replace: item.querySelector(".qi-row") || item };
      openForm({
        ...place,
        note,
        onSave: async (values) => {
          const saved = await api("PATCH", `/notes/${id}`, values);
          inRegion ? refreshRegion(item) : remember(saved);
        },
      });
    } else if (action === "delete") {
      if (!(await confirmDelete(note))) return;
      await api("DELETE", `/notes/${id}`);
      state.notes.delete(id);
      inRegion ? refreshRegion(item) : refreshPage();
      toast("Заметка удалена");
    } else if (action === "rebind") {
      state.rebind = id;
      closeFloat();
      toast("Выделите в тексте новое место для заметки");
    }
  }

  function addWhole(at, elementId) {
    if (!elementId) return;
    openForm({
      at,
      onSave: async (values) => {
        const saved = await api("POST", "/notes", { ...values, element_id: elementId });
        remember(saved);
        const shown = state.open.has(elementId) || saved.important;
        toast(shown ? "Заметка сохранена" : "Заметка сохранена — видна по кнопке заметок");
      },
    });
  }

  // полоска «пометка · вопрос» в подсказке выделения (секция 005)
  function selectionSection(ctx) {
    // только внутри контейнера заметок (элемент урока); перевод (006) работает и вне его
    if (!ctx.noteContainer || !document.querySelector("[data-notes-json]")) return null;
    const strip = document.createElement("div");
    strip.className = "sel-strip";
    if (state.rebind) {
      strip.innerHTML = `<button type="button">${icon("note", "icon-note")}привязать сюда</button>`;
      strip.onclick = async () => {
        window.SelectionPopup.close();
        const anchor = anchorFromRange(ctx.container, ctx.range);
        const id = state.rebind;
        state.rebind = null;
        if (anchor) remember(await api("PATCH", `/notes/${id}`, { anchor }));
      };
      return strip;
    }
    strip.innerHTML = `<button type="button" data-k="note" title="Пометка к фрагменту">${icon("note", "icon-note")}пометка</button>
      <button type="button" data-k="question" title="Вопрос к фрагменту">${icon("question", "icon-question")}вопрос</button>`;
    strip.onclick = (event) => {
      const button = event.target.closest("button");
      if (!button) return;
      window.SelectionPopup.close();
      startCreate(ctx, button.dataset.k);
    };
    return strip;
  }

  function startCreate(ctx, kind) {
    const anchor = anchorFromRange(ctx.container, ctx.range);
    if (!anchor) return;
    window.getSelection().removeAllRanges();
    const idx = textIndex(ctx.container);
    const pending = wrap(idx, anchor.start, anchor.start + anchor.exact.length, ["new"], "pending");
    const last = pending[pending.length - 1] || ctx.container;
    openForm({
      at: last,
      kind,
      onSave: async (values) => {
        const saved = await api("POST", "/notes", { ...values, element_id: ctx.elementId, anchor });
        unwrapAll("mark.note-anchor.pending");
        remember(saved);
        toast(saved.kind === "question" ? "Вопрос записан" : "Пометка сохранена");
      },
      onCancel: () => unwrapAll("mark.note-anchor.pending"),
    });
  }

  // --- загрузка данных и события ---------------------------------------------------------------

  function loadData() {
    let added = false;
    document.querySelectorAll("script[data-notes-json]:not([data-loaded])").forEach((script) => {
      script.dataset.loaded = "1";
      const data = JSON.parse(script.textContent);
      data.notes.forEach((n) => state.notes.set(n.id, n));
      added = true;
    });
    return added;
  }

  function init() {
    if (loadData()) placeAnchors();
    renderElement();
    const hash = window.location.hash.match(/^#note-(\d+)$/);
    if (hash && state.notes.has(Number(hash[1]))) {
      const note = state.notes.get(Number(hash[1]));
      const mark = marksFor(note.id)[0];
      if (mark) {
        mark.scrollIntoView({ block: "center" });
        showFloat(mark);
      } else if (!note.important) {
        state.open.add(note.element_id);
        renderElement();
        requestAnimationFrame(() => {
          const item = document.getElementById(`note-${note.id}`);
          if (item) {
            item.scrollIntoView({ block: "center" });
            flash(item);
          }
        });
      }
    }
    window.SelectionPopup?.register(selectionSection);
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-note-act]");
    if (button) {
      event.preventDefault();
      act(button);
      return;
    }
    const toggle = event.target.closest("[data-notes-toggle]");
    if (toggle) {
      const id = toggle.dataset.notesToggle;
      if (!state.open.delete(id)) state.open.add(id);
      closeFloat();
      renderElement();
      return;
    }
    if (event.target.closest("[data-notes-close-all]")) {
      state.open.clear();
      closeFloat();
      renderElement();
      return;
    }
    const add = event.target.closest("[data-notes-add]");
    if (add) {
      addWhole(add, add.dataset.notesAdd);
      return;
    }
    const mark = event.target.closest("mark.note-anchor:not(.pending)");
    if (mark && window.getSelection().isCollapsed) {
      showFloat(mark);
      return;
    }
    if (state.float && !event.target.closest(".note-float-list, .note-form, .note-dialog")) closeFloat();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeFloat();
    const input = event.target.closest?.("input[data-add-note]");
    if (input && event.key === "Enter" && !event.isComposing) {
      event.preventDefault();
      const body = input.value.trim();
      if (!body) return;
      api("POST", "/notes", { kind: input.dataset.addNote, body, lesson: Number(input.dataset.lesson) }).then(() => {
        toast(input.dataset.addNote === "question" ? "Вопрос записан" : "Записано");
        refreshRegion(input);
      });
    }
  });

  // подсветка пары «заметка ↔ фрагмент» при наведении
  document.addEventListener("mouseover", (event) => {
    document.querySelectorAll(".hov").forEach((node) => node.classList.remove("hl", "hov"));
    const item = event.target.closest(".note-item[data-note-id]");
    const mark = event.target.closest("mark.note-anchor");
    const ids = item ? [Number(item.dataset.noteId)] : mark ? idsAt(mark) : [];
    ids.forEach((id) => {
      [...marksFor(id), ...document.querySelectorAll(`[data-notes-margin] [data-note-id="${id}"]`)].forEach((node) => {
        if (!node.classList.contains("hl")) node.classList.add("hl", "hov");
      });
    });
  });

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      closeFloat();
      layoutMargins();
    }, 120);
  });

  // «Теория рядом» подгружается HTMX — расставить её отметки
  document.addEventListener("htmx:afterSwap", () => {
    if (loadData()) {
      placeAnchors();
      renderElement();
    }
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
