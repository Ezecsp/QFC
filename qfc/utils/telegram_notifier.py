import telegram
from config.logger_config import log

class TelegramNotifier:
    """
    Clase responsable de enviar mensajes a través de un bot de Telegram.
    """
    def __init__(self, config: dict):
        self.token = config.get("token")
        self.chat_id = config.get("chat_id")
        
        if not self.token or not self.chat_id:
            log.warning("Token o Chat ID de Telegram no configurados. Las notificaciones estarán desactivadas.")
            self.bot = None
        else:
            try:
                self.bot = telegram.Bot(token=self.token)
                log.info("Notificador de Telegram inicializado correctamente.")
            except Exception as e:
                log.error(f"Error al inicializar el bot de Telegram: {e}")
                self.bot = None

    async def send_message(self, message: str):
        """
        Envía un mensaje al chat_id configurado.
        Usa un método asíncrono, que es el estándar para esta librería.
        """
        if not self.bot:
            log.warning("Intento de enviar mensaje, pero el bot de Telegram no está inicializado.")
            return

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            log.info(f"Mensaje enviado a Telegram: {message.splitlines()[0]}...")
        except Exception as e:
            log.error(f"Error al enviar mensaje a Telegram: {e}")