// Перевод выделенного (006): секция подсказки selection.js — перевод, начальная форма, 🔊,
// «+ В словарь». Перевод — GET /translate (словарь → запас → сервис), добавление —
// POST /vocab/from-text (contracts/translate-api.md). Выключается переключателем в «⋯».
(() => {
  const CYRILLIC = /[Ѐ-ӿ]/;
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const enabled = () => document.documentElement.dataset.translate !== "0";

  function toast(text) {
    const box = document.createElement("div");
    box.className = "note-toast";
    box.setAttribute("role", "status");
    box.textContent = text;
    document.body.appendChild(box);
    setTimeout(() => box.remove(), 2800);
  }

  const inDict = (translation) =>
    `<span class="tr-in-dict">✓ в словаре${translation ? `: ${esc(translation)}` : ""}</span>`;

  function render(box, ctx, data) {
    const main = data.translation
      ? `<div class="tr-text">${esc(data.translation)}</div>`
      : `<div class="tr-text tr-error">${esc(data.error || "Перевод сейчас недоступен")}</div>`;
    const lemma = data.lemma
      ? `<div class="tr-lemma">Начальная форма: <span lang="fr">${esc(data.lemma)}</span>${
          data.lemma_translation ? ` — ${esc(data.lemma_translation)}` : ""
        }</div>`
      : "";
    let add = "";
    if (data.entry) add = inDict(data.entry.translation);
    else if (data.can_add) add = `<button type="button" class="btn-sm tr-add">+ В словарь: <span lang="fr">${esc(data.add_as.text)}</span></button>`;
    // перевод и форма — в прокручиваемой части, кнопки — под ней, всегда на виду
    box.querySelector(".tr-body").innerHTML = `${main}${lemma}`;
    box.querySelector(".tr-acts").innerHTML = `<button type="button" class="speak outline small" data-speak="${esc(ctx.text)}" title="Произнести" aria-label="Произнести">🔊</button>${add}`;
    const button = box.querySelector(".tr-add");
    if (button) button.onclick = () => addToVocab(button, ctx);
    window.SelectionPopup.place();
  }

  async function addToVocab(button, ctx) {
    button.disabled = true;
    const response = await fetch("/vocab/from-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: ctx.text, sentence: ctx.sentence(), lesson: ctx.lesson }),
    }).catch(() => null);
    const data = response ? await response.json().catch(() => ({})) : {};
    if (!response || !response.ok) {
      button.disabled = false;
      toast(`Не добавлено: ${data.error || "приложение не отвечает"}`);
      return;
    }
    button.outerHTML = inDict(data.translation);
    toast(data.merged ? `Уже в словаре: ${data.text} — пример добавлен` : `Добавлено в словарь: ${data.text} — ${data.translation}`);
    window.SelectionPopup.place();
  }

  function section(ctx) {
    if (!enabled() || CYRILLIC.test(ctx.text)) return null;
    const box = document.createElement("div");
    box.className = "tr-sec";
    const shown = ctx.text.length > 60 ? `${ctx.text.slice(0, 60)}…` : ctx.text;
    box.innerHTML = `<div class="tr-head"><span class="tr-src" lang="fr">${esc(shown)}</span>
        <button type="button" class="tr-close" title="Закрыть" aria-label="Закрыть">✕</button></div>
      <div class="tr-body" data-shrink><div class="tr-text muted">Перевод…</div></div>
      <div class="tr-acts"></div>`;
    box.querySelector(".tr-close").onclick = () => window.SelectionPopup.close();
    // слово перед выделенным — только для начальной формы (Paul entre → entrer), наружу не уходит
    const sentence = ctx.sentence();
    const at = sentence.toLowerCase().indexOf(ctx.text.toLowerCase());
    const before = at > 0 ? (sentence.slice(0, at).match(/[\p{L}'’]+(?=[^\p{L}'’]*$)/u) || [""])[0] : "";
    fetch(`/translate?${new URLSearchParams({ q: ctx.text, before })}`)
      .then((response) => response.json())
      .catch(() => ({ translation: null, error: "Перевод сейчас недоступен" }))
      .then((data) => render(box, ctx, { translation: null, ...data }));
    return box;
  }

  function init() {
    window.SelectionPopup?.register(section);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
