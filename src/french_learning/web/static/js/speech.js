// Озвучка слова встроенным синтезом речи браузера (fr-FR), без внешних сервисов (FR-014).
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-speak]");
  if (!button) return;
  if (!("speechSynthesis" in window)) {
    button.title = "Озвучка недоступна в этом браузере";
    button.disabled = true;
    return;
  }
  const utterance = new SpeechSynthesisUtterance(button.dataset.speak);
  utterance.lang = "fr-FR";
  const voice = speechSynthesis.getVoices().find((v) => v.lang && v.lang.startsWith("fr"));
  if (voice) utterance.voice = voice;
  speechSynthesis.cancel();
  speechSynthesis.speak(utterance);
});
