// Озвучка французского: звук синтезирует сервер приложения локальной нейросетью Piper
// (/tts, голос — из настроек). Готовый звук кешируется, повторное нажатие мгновенное.
const players = new Map();

function play(button) {
  const params = new URLSearchParams({ text: button.dataset.speak });
  if (button.dataset.voice) params.set("voice", button.dataset.voice);
  const url = "/tts?" + params.toString();
  let audio = players.get(url);
  if (!audio) {
    audio = new Audio(url);
    players.set(url, audio);
  }
  button.setAttribute("aria-busy", "true");
  // 012: повторное нажатие во время звучания — слово заново с начала, целиком
  audio.pause();
  audio.currentTime = 0;
  audio
    .play()
    .catch(async () => {
      players.delete(url);
      const response = await fetch(url).catch(() => null);
      button.title = response ? await response.text() : "Озвучка недоступна: приложение не отвечает";
      alert(button.title);
    })
    .finally(() => button.removeAttribute("aria-busy"));
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-speak]");
  if (!button) return;
  event.preventDefault();
  play(button);
});
