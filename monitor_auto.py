"""
Monitor automatico - Solo abre WhatsApp y monitorea.
"""
import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
import logging
import threading
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

CHROME_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1280,800",
]

class Monitor:
    def __init__(self):
        self.running = True
        self.driver = None
        self.bot = None
        self.ids_procesados = set()
        self.encontrado = False
        self.mensaje_enviado = None

    def cargar_ids(self):
        ids_file = Path("datos/ultimo_mensaje_id.json")
        if ids_file.exists():
            try:
                with open(ids_file, "r", encoding="utf-8") as f:
                    self.ids_procesados = set(json.load(f))
            except:
                pass
        logger.info(f"IDs ya procesados: {len(self.ids_procesados)}")

    def guardar_ids(self):
        ids_file = Path("datos/ultimo_mensaje_id.json")
        ids_file.parent.mkdir(exist_ok=True)
        with open(ids_file, "w", encoding="utf-8") as f:
            json.dump(list(self.ids_procesados)[-200:], f, ensure_ascii=False)

    def iniciar(self):
        logger.info("=" * 50)
        logger.info("WHATSAPP MONITOR - Series Bot")
        logger.info("=" * 50)

        opciones = Options()
        for arg in CHROME_ARGS:
            opciones.add_argument(arg)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opciones)

        logger.info("Abriendo WhatsApp Web...")
        self.driver.get("https://web.whatsapp.com")

        # Esperar a que cargue
        wait = WebDriverWait(self.driver, 60)
        try:
            wait.until(lambda d: d.find_element("id", "side") or d.find_element("css selector", "div[data-testid='chat-list']"))
            logger.info("Sesion lista!")
        except:
            logger.error("Timeout esperando WhatsApp")
            return

        time.sleep(2)

        from whatsapp_mensajes import WhatsAppMessages
        from whatsapp_envio import WhatsAppSender
        from WhatsAppBot import WhatsAppBot

        messages = WhatsAppMessages(self.driver)
        sender = WhatsAppSender(self.driver)
        self.bot = WhatsAppBot()

        self.cargar_ids()

        logger.info("MONITOREANDO... Espera mensajes en el grupo.")
        logger.info("(El bot respondera automaticamente cuando llegue 'quiero N series')")

        # Loop de monitoreo
        timeout = 180  # 3 minutos
        inicio = time.time()

        while self.running and time.time() - inicio < timeout:
            try:
                msgs = messages.obtener_mensajes(limite=50)

                for msg in msgs:
                    texto = msg.get("texto", "")
                    tipo = msg.get("tipo", "")
                    hora = msg.get("hora", "")
                    msg_id = msg.get("id", "") or f"{texto[:30]}|{hora}"

                    if msg_id in self.ids_procesados:
                        continue

                    if tipo == "entrante" and texto.strip():
                        logger.info(f">>> [{hora}] {texto[:80]}")

                        respuesta = self.bot.procesar_comando(texto)

                        if respuesta:
                            logger.info(f">>> Respondiendo: {respuesta[:50]}...")
                            resultado = sender.enviar_mensaje(respuesta)

                            if resultado.get("exito"):
                                logger.info(">>> ENVIADO!")

                                with open("datos/whatsapp_series.json", "r", encoding="utf-8") as f:
                                    series = json.load(f)
                                disponibles = len([s for s in series if s.get("estado") == "disponible"])
                                logger.info(f">>> Series restantes: {disponibles}")
                                self.encontrado = True
                                self.mensaje_enviado = respuesta
                                self.running = False
                            else:
                                logger.error(f">>> Error: {resultado.get('error')}")

                        self.ids_procesados.add(msg_id)

                self.guardar_ids()

                if self.encontrado:
                    break

            except Exception as e:
                logger.error(f"Error: {e}")

            time.sleep(3)

        self.finalizar()

    def finalizar(self):
        if self.encontrado:
            logger.info("=" * 50)
            logger.info("TEST EXITOSO!")
            logger.info("El bot respondio correctamente al mensaje.")
            logger.info("=" * 50)
        else:
            logger.info("Timeout - No se detecto el comando 'quiero N series'")

        if self.driver:
            logger.info("Cerrando navegador en 10 segundos...")
            time.sleep(10)
            self.driver.quit()

def main():
    monitor = Monitor()
    monitor.iniciar()

if __name__ == "__main__":
    main()