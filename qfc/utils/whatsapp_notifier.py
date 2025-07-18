import requests
import json
import asyncio
from config.logger_config import log

class WhatsAppNotifier:
    """
    Clase responsable de enviar mensajes a WhatsApp a través de GREEN-API.
    """
    def __init__(self, config: dict):
        self.id_instance = config.get("id_instance")
        self.api_token = config.get("api_token")
        self.target_number = config.get("target_number")
        
        if not all([self.id_instance, self.api_token, self.target_number]):
            log.warning("Credenciales de GREEN-API o número de destino no configurados. Las notificaciones de WhatsApp estarán desactivadas.")
            self.is_configured = False
            self.api_url = None
        else:
            self.is_configured = True
            self.api_url = f"https://api.green-api.com/waInstance{self.id_instance}/sendMessage/{self.api_token}"
            log.info("Notificador de WhatsApp (GREEN-API) inicializado correctamente.")
            
    def _send_request(self, payload: dict):
        """Función síncrona que realiza la petición HTTP."""
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=10)
            if response.status_code == 200:
                log.info("Mensaje enviado a WhatsApp exitosamente.")
            else:
                log.error(f"Error al enviar a WhatsApp. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            log.error(f"Excepción al enviar petición a WhatsApp: {e}")

    async def send_message(self, message: str):
        """
        Prepara y envía un mensaje a WhatsApp de forma asíncrona.
        """
        if not self.is_configured:
            log.warning("Intento de enviar a WhatsApp, pero el notificador no está configurado.")
            return

        # El formato de chatId para GREEN-API es "numero@c.us"
        chat_id = f"{self.target_number}@c.us"
        payload = {
            "chatId": chat_id,
            "message": message
        }
        
        # Ejecutamos la función de red síncrona en un hilo separado para no bloquear el bucle de eventos de asyncio
        await asyncio.to_thread(self._send_request, payload)