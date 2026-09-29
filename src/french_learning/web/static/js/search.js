// Подсветка найденного на странице элемента (007, research R8): адрес /elements/<id>?hl=<запрос>.
// Нормализация — как в search/text.py (research R2): регистр, диакритика, œ/oe, æ/ae, ё/е;
// апострофы, дефисы и знаки — разделители; фраза — слова подряд, последнее — по началу.
(() => {
  const LIGATURES = { "œ": "oe", "æ": "ae", "ё": "е" };
  const BLOCK = "p, li, td, th, h1, h2, h3, h4, h5, h6, dd, dt, blockquote, pre, div, article";
  const SKIP = "script, style, button, .note-ui, .sel-pop, .search-bar";
  const WORD = /[\p{L}\p{N}]+/gu;

  const normalize = (s) =>
    s.toLowerCase().replace(/[œæё]/g, (c) => LIGATURES[c]).normalize("NFKD").replace(/\p{M}/gu, "");

  function words(text) {
    const found = [];
    for (const m of text.replace(/ʼ/g, "'").matchAll(WORD)) {
      found.push({ norm: normalize(m[0]), start: m.index, end: m.index + m[0].length });
    }
    return found;
  }

  // текст области одной строкой и место каждого символа в текстовых узлах
  function textIndex(root) {
    const map = [];
    let text = "";
    let block = null;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (n.parentElement.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
    });
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const nodeBlock = node.parentElement.closest(BLOCK);
      if (block && nodeBlock !== block) {
        text += "\n"; // слова разных блоков (ячейки, строки) не склеиваются
        map.push(null);
      }
      block = nodeBlock;
      for (let i = 0; i < node.textContent.length; i++) map.push([node, i]);
      text += node.textContent;
    }
    return { text, map };
  }

  function matches(text, query) {
    const q = words(query).map((w) => w.norm);
    if (q.join("").length < 2) return [];
    const doc = words(text);
    const last = q.length - 1;
    const found = [];
    for (let i = 0; i + last < doc.length; i++) {
      if (!doc[i + last].norm.startsWith(q[last])) continue;
      if (q.slice(0, last).every((w, k) => doc[i + k].norm === w)) {
        found.push([doc[i].start, doc[i + last].end]);
      }
    }
    return found;
  }

  // обернуть символы [s, e) в <mark>; кусок в каждом текстовом узле — отдельно
  function wrap(map, s, e, number) {
    const pieces = new Map();
    for (let i = s; i < e; i++) {
      if (!map[i]) continue;
      const [node, offset] = map[i];
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
      mark.className = "search-hit";
      mark.dataset.hit = number;
      target.replaceWith(mark);
      mark.appendChild(target);
      marks.push(mark);
    }
    return marks;
  }

  function clear(bar) {
    document.querySelectorAll("mark.search-hit").forEach((mark) => {
      const parent = mark.parentNode;
      mark.replaceWith(...mark.childNodes);
      parent.normalize();
    });
    bar.remove();
    const url = new URL(window.location.href);
    url.searchParams.delete("hl");
    history.replaceState(null, "", url);
  }

  function init() {
    const query = new URLSearchParams(window.location.search).get("hl");
    const root = document.querySelector("article.reading, .split-main");
    if (!query || !root) return;
    const idx = textIndex(root);
    const found = matches(idx.text, query);
    // с конца: разрезание узла не сдвигает места более ранних совпадений
    for (let n = found.length - 1; n >= 0; n--) wrap(idx.map, found[n][0], found[n][1], n);

    const bar = document.createElement("div");
    bar.className = "search-bar";
    bar.setAttribute("role", "status");
    const back = `/search?${new URLSearchParams({ q: query })}`;
    bar.innerHTML = `<a href="${back}">← к результатам</a>
      <span>Найдено на странице: <b>${found.length}</b> · «<span class="q"></span>»</span>
      <span class="sp"></span>
      ${found.length > 1 ? '<button type="button" class="outline small" data-next>Следующее ↓</button>' : ""}
      <button type="button" class="outline small" data-clear>Снять подсветку</button>`;
    bar.querySelector(".q").textContent = query;
    root.closest(".notes-layout, article, .split-layout")?.before(bar);

    let current = -1;
    const go = () => {
      const all = [...document.querySelectorAll("mark.search-hit")];
      if (!all.length) return;
      current = (current + 1) % found.length;
      all.forEach((m) => m.classList.toggle("current", Number(m.dataset.hit) === current));
      all.find((m) => Number(m.dataset.hit) === current)?.scrollIntoView({ block: "center", behavior: "smooth" });
    };
    bar.querySelector("[data-next]")?.addEventListener("click", go);
    bar.querySelector("[data-clear]").addEventListener("click", () => clear(bar));
    go();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
