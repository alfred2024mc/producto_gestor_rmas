"""
WhatsAppLoop - Loop principal que integra todos los módulos del bot.
Paso 6: Coordina conexión, selección, lectura, procesamiento y envío.
"""

import time
import json
import logging
import signal
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from whatsapp_conexion import WhatsAppConnection
from whatsapp_seleccion import WhatsAppSelection
from whatsapp_mensajes import WhatsAppMessages
from whatsapp_envio import WhatsAppSender
from WhatsAppBot import WhatsAppBot

logger = logging.getLogger(__name__)


class WhatsAppLoop:
    """
    Loop principal que ejecuta el ciclo del bot.

    Flujo:
    1. Conectar a WhatsApp Web
    2. Seleccionar grupo/contacto
    3. Loop infinito:
       a. Obtener mensajes nuevos
       b. Evitar duplicados
       c. Procesar comando
       d. Responder
       e. Registrar historial
       f. Esperar intervalo
    """

    ARCHIVO_ULTIMO_ID = Path("datos") / "ultimo_mensaje_id.json"
    ARCHIVO_ESTADO = Path("datos") / "bot_estado.json"

    MAX_MENSAJES_IDS = 500
    MAX_INTENTOS_RECONEXION = 3
    PAUSA_RECONEXION = 10

    def __init__(
        self,
        grupo_objetivo: str,
        intervalo: float = 5.0,
        perfil_path: str | None = None,
        log_level: int = logging.INFO
    ) -> None:
        """
        Inicializa el loop del bot.

        Args:
            grupo_objetivo: Nombre del grupo o contacto a monitorear.
            intervalo: Segundos entre cada revisión (default 5.0).
            perfil_path: Ruta al perfil de Chrome (opcional).
            log_level: Nivel de logging (default INFO).
        """
        self._grupo_objetivo = grupo_objetivo
        self._intervalo = intervalo
        self._perfil_path = perfil_path

        self._driver = None
        self._selector = None
        self._messages = None
        self._sender = None
        self._bot = WhatsAppBot()

        self._ultimo_id = self._cargar_ultimo_id()
        self._corriendo = False
        self._reiniciar_senial = False

        self._configurar_senial()

    def _configurar_senial(self) -> None:
        """Configura handlers para señales de terminación."""
        signal.signal(signal.SIGINT, self._handler_senial)
        signal.signal(signal.SIGTERM, self._handler_senial)

    def _handler_senial(self, signum, frame) -> None:
        """Maneja señales de terminación para cierre limpio."""
        logger.info(f"Señal {signum} recibida, deteniendo bot...")
        self.detener()
        sys.exit(0)

    def iniciar(self) -> None:
        """Inicia el loop principal del bot."""
        logger.info(f"Iniciando bot para: {self._grupo_objetivo}")
        logger.info(f"Intervalo de revisión: {self._intervalo}s")
        logger.info("-" * 40)

        self._corriendo = True

        while self._corriendo and self._reiniciar_senial is False:
            try:
                self._conectar()
                self._seleccionar_grupo()
                self._ejecutar_loop()
            except Exception as e:
                logger.error(f"Error en el loop principal: {e}")
                self._manejar_error_conexion(e)

        self.detener()

    def _conectar(self) -> None:
        """Establece conexión con WhatsApp Web."""
        logger.info("Conectando a WhatsApp Web...")

        conexion = WhatsAppConnection(perfil_path=self._perfil_path)
        self._driver = conexion.conectar()

        self._selector = WhatsAppSelection(self._driver)
        self._messages = WhatsAppMessages(self._driver)
        self._sender = WhatsAppSender(self._driver)

        logger.info("Conexión establecida.")

    def _seleccionar_grupo(self) -> None:
        """Selecciona el grupo o contacto objetivo."""
        logger.info(f"Seleccionando: {self._grupo_objetivo}")

        resultado = self._selector.seleccionar_chat(self._grupo_objetivo)

        if not resultado["exito"]:
            raise RuntimeError(
                f"No se pudo abrir '{self._grupo_objetivo}': {resultado['mensaje']}"
            )

        time.sleep(1)
        self._selector.esperar_chat_cargado()

        logger.info(f"Chat '{self._grupo_objetivo}' abierto.")

    def _ejecutar_loop(self) -> None:
        """Ejecuta el loop infinito de revisión."""
        logger.info("Bot activo. Esperando mensajes...")

        ciclos_sin_mensaje = 0

        while self._corriendo:
            try:
                if self._verificar_conexion():
                    self._procesar_mensajes_nuevos()
                    ciclos_sin_mensaje = 0
                else:
                    raise ConnectionError("Conexión perdida con WhatsApp Web")

            except ConnectionError as e:
                ciclos_sin_mensaje += 1
                if ciclos_sin_mensaje >= 3:
                    logger.warning(f"Conexión inestable ({ciclos_sin_mensaje} ciclos)")
                    raise

            except Exception as e:
                logger.error(f"Error en el loop: {e}")
                self._guardar_estado_error(e)

            time.sleep(self._intervalo)

    def _verificar_conexion(self) -> bool:
        """Verifica si la conexión con WhatsApp Web sigue activa."""
        try:
            if self._driver is None or not self._driver.window_handles:
                return False

            self._driver.find_element("css selector", "body")
            return True
        except Exception:
            return False

    def _manejar_error_conexion(self, error: Exception) -> None:
        """Maneja errores de conexión intentando reconexión."""
        logger.warning(f"Error de conexión detectado: {error}")
        self._cerrar_driver()

        for intento in range(1, self.MAX_INTENTOS_RECONEXION + 1):
            logger.info(f"Intento de reconexión {intento}/{self.MAX_INTENTOS_RECONEXION}...")
            time.sleep(self.PAUSA_RECONEXION)

            try:
                self._conectar()
                self._seleccionar_grupo()
                logger.info("Reconexión exitosa.")
                return
            except Exception as e:
                logger.error(f"Reintento {intento} falló: {e}")
                self._cerrar_driver()

        logger.error("No se pudo reconectar después de varios intentos.")
        self._corriendo = False

    def _cerrar_driver(self) -> None:
        """Cierra el driver de forma segura."""
        try:
            if self._driver:
                self._driver.quit()
        except Exception as e:
            logger.debug(f"Error cerrando driver: {e}")
        finally:
            self._driver = None
            self._selector = None
            self._messages = None
            self._sender = None

    def _procesar_mensajes_nuevos(self) -> None:
        """Procesa mensajes nuevos del chat."""
        mensajes = self._messages.obtener_mensajes(limite=10)

        for msg in mensajes:
            msg_id = self._generar_id_mensaje(msg)

            if msg_id in self._ultimo_id:
                continue

            if msg["tipo"] != "entrante":
                continue

            if not msg["texto"] or not msg["texto"].strip():
                continue

            self._procesar_y_responder(msg, msg_id)

    def _procesar_y_responder(self, msg: dict, msg_id: str) -> None:
        """Procesa un mensaje y envía respuesta si corresponde."""
        logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] Mensaje: {msg['texto'][:60]}")

        respuesta = self._bot.procesar_comando(msg["texto"])

        if respuesta:
            logger.debug(f"Respuesta: {respuesta[:60]}...")
            if self._enviar_respuesta(respuesta):
                logger.info(f"  [Enviado]")
            else:
                logger.warning(f"  [Error al enviar]")

        self._ultimo_id.add(msg_id)
        self._guardar_ultimo_id()

    def _generar_id_mensaje(self, msg: dict) -> str:
        """Genera identificador único para el mensaje."""
        if msg.get("id") and msg["id"] != datetime.now().isoformat()[:19]:
            return msg["id"]

        contenido = msg.get("texto", "")[:50]
        hora = msg.get("hora", "")
        return f"{contenido}|{hora}".strip()

    def _enviar_respuesta(self, texto: str) -> bool:
        """Envía la respuesta al chat."""
        resultado = self._sender.enviar_mensaje(texto)

        if resultado["exito"]:
            return True
        else:
            logger.warning(f"Error al enviar: {resultado['error']}")
            return False

    def _cargar_ultimo_id(self) -> set:
        """Carga los IDs de mensajes ya procesados."""
        if self.ARCHIVO_ULTIMO_ID.exists():
            try:
                with open(self.ARCHIVO_ULTIMO_ID, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning(f"Error cargando IDs: {e}")
        return set()

    def _guardar_ultimo_id(self) -> None:
        """Guarda los IDs de mensajes ya procesados."""
        self.ARCHIVO_ULTIMO_ID.parent.mkdir(exist_ok=True)
        try:
            with open(self.ARCHIVO_ULTIMO_ID, "w", encoding="utf-8") as f:
                ids_lista = list(self._ultimo_id)[-self.MAX_MENSAJES_IDS:]
                json.dump(ids_lista, f)
        except Exception as e:
            logger.error(f"Error guardando IDs: {e}")

    def _guardar_estado_error(self, error: Exception) -> None:
        """Guarda el estado cuando ocurre un error para debugging."""
        self.ARCHIVO_ESTADO.parent.mkdir(exist_ok=True)
        estado = {
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "grupo_objetivo": self._grupo_objetivo,
            "ultimo_id_count": len(self._ultimo_id)
        }
        try:
            with open(self.ARCHIVO_ESTADO, "w", encoding="utf-8") as f:
                json.dump(estado, f, indent=2)
        except Exception:
            pass

    def detener(self) -> None:
        """Detiene el loop y cierra el navegador."""
        logger.info("Deteniendo bot...")
        self._corriendo = False
        self._cerrar_driver()
        logger.info("Bot detenido.")

    def cambiar_grupo(self, nuevo_grupo: str) -> None:
        """Cambia el grupo objetivo en tiempo de ejecución."""
        self._grupo_objetivo = nuevo_grupo
        logger.info(f"Cambiando a grupo: {nuevo_grupo}")

        if self._selector:
            self._seleccionar_grupo()

    def cambiar_intervalo(self, nuevo_intervalo: float) -> None:
        """Cambia el intervalo de revisión."""
        self._intervalo = nuevo_intervalo
        logger.info(f"Intervalo cambiado a: {nuevo_intervalo}s")

    def reiniciar(self) -> None:
        """Reinicia el bot desde cero."""
        logger.info("Solicitud de reinicio recibida.")
        self._reiniciar_senial = True
        self._corriendo = False

    def obtener_estado(self) -> dict:
        """Retorna el estado actual del bot."""
        return {
            "grupo_objetivo": self._grupo_objetivo,
            "intervalo": self._intervalo,
            "mensajes_procesados": len(self._ultimo_id),
            "conectado": self._driver is not None,
            "corriendo": self._corriendo
        }


def configurar_logging(nivel: int = logging.INFO) -> None:
    """Configura el sistema de logging global."""
    formato = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=nivel,
        format=formato,
        datefmt="%H:%M:%S"
    )


def main():
    """Punto de entrada para ejecutar el bot."""
    import argparse

    parser = argparse.ArgumentParser(description="WhatsApp Bot")
    parser.add_argument(
        "--grupo", "-g",
        default="Chat Principal",
        help="Nombre del grupo o contacto a monitorear"
    )
    parser.add_argument(
        "--intervalo", "-i",
        type=float,
        default=5.0,
        help="Segundos entre cada revisión (default: 5)"
    )
    parser.add_argument(
        "--perfil", "-p",
        default=None,
        help="Ruta al perfil de Chrome (evita escanear QR cada vez)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa modo debug (logs detallados)"
    )

    args = parser.parse_args()

    nivel = logging.DEBUG if args.debug else logging.INFO
    configurar_logging(nivel)

    logger.info("=" * 50)
    logger.info("WHATSAPP BOT - Iniciando")
    logger.info("=" * 50)

    bot = WhatsAppLoop(
        grupo_objetivo=args.grupo,
        intervalo=args.intervalo,
        perfil_path=args.perfil,
        log_level=nivel
    )

    try:
        bot.iniciar()
    except KeyboardInterrupt:
        logger.info("Interrupción del usuario.")
    finally:
        bot.detener()


if __name__ == "__main__":
    main()