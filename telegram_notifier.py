import requests


class TelegramNotifier:
    API = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: str, chat_id: str):
        self._enabled = bool(
            token and chat_id
            and token != "BOT_TOKEN_BURAYA"
            and chat_id != "CHAT_ID_BURAYA"
        )
        self._token = token
        self._chat_id = chat_id
        if not self._enabled:
            print("[Telegram] Token/chat_id ayarlanmamis — bildirim devre disi.")

    def send(self, text: str, photo_path: str = None):
        if not self._enabled:
            return
        try:
            if photo_path:
                with open(photo_path, "rb") as f:
                    requests.post(
                        self.API.format(token=self._token, method="sendPhoto"),
                        data={"chat_id": self._chat_id, "caption": text},
                        files={"photo": f},
                        timeout=10,
                    )
            else:
                requests.post(
                    self.API.format(token=self._token, method="sendMessage"),
                    data={"chat_id": self._chat_id, "text": text},
                    timeout=10,
                )
        except Exception as e:
            print(f"[Telegram] Gonderim hatasi: {e}")
