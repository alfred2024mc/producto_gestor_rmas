"""
WhatsApp Monitor - Con perfil persistente para mantener sesión.
"""
import time
import json
import re
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Perfil de Chrome para mantener sesión
PERFIL_CHROME = Path("datos/chrome_perfil")
PERFIL_CHROME.mkdir(exist_ok=True)

CHROME_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1280,800",
    f"--user-data-dir={PERFIL_CHROME.absolute()}",
]

ARCHIVO_SERIES = Path("datos/whatsapp_series.json")
ARCHIVO_IDS = Path("datos/ultimo_mensaje_id.json")
ARCHIVO_LOG = Path("datos/whatsapp_log.json")


class WhatsAppMonitor:
    def __init__(self, grupo: str, intervalo: float = 3.0):
        self.grupo = grupo
        self.intervalo = intervalo
        self.driver = None
        self.bot = None

    def iniciar(self):
        logger.info("=" * 50)
        logger.info("WHATSAPP MONITOR - Series Bot")
        logger.info(f"Grupo: {self.grupo}")
        logger.info("=" * 50)

        # Iniciar Chrome con perfil
        opciones = Options()
        for arg in CHROME_ARGS:
            opciones.add_argument(arg)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=opciones)
        self.driver.get("https://web.whatsapp.com")

        logger.info("Esperando sesión de WhatsApp...")
        wait = WebDriverWait(self.driver, 30)

        try:
            wait.until(EC.presence_of_element_located((By.ID, "side")))
            logger.info("Sesión activa detectada")
        except:
            logger.info("No hay sesión. Escanea el QR en 60 segundos...")
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, '//canvas')))
                logger.info("Código QR visible. Escanea con tu teléfono.")
                wait.until(EC.staleness_of(self.driver.find_element(By.XPATH, '//canvas')))
                logger.info("QR escaneado!")
                wait.until(EC.presence_of_element_located((By.ID, "side")))
            except:
                logger.error("Timeout esperando autenticación")
                return

        time.sleep(2)
        self._abrir_grupo()
        self._ejecutar_loop()

    def _abrir_grupo(self):
        logger.info(f"Abriendo grupo: {self.grupo}")
        wait = WebDriverWait(self.driver, 15)

        try:
            # Buscar input de búsqueda
            search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="chat-list-search"] input')))
            search.click()
            time.sleep(0.5)
            search.send_keys(self.grupo)
            time.sleep(1.5)

            # Click en el resultado
            chat = wait.until(EC.element_to_be_clickable((By.XPATH, f'//span[@title="{self.grupo}"]')))
            chat.click()
            logger.info(f"Grupo '{self.grupo}' abierto!")
        except Exception as e:
            logger.error(f"Error abriendo grupo: {e}")
            # Intentar con método alternativo
            try:
                from whatsapp_seleccion import WhatsAppSelection
                selector = WhatsAppSelection(self.driver)
                selector.seleccionar_chat(self.grupo)
                logger.info("Grupo abierto via método alternativo")
            except:
                logger.error("No se pudo abrir el grupo")

        time.sleep(1)

    def _extraer_mensajes(self):
        """Extrae mensajes del grupo usando JavaScript."""
        js_script = """
        function getMensajes() {
            const resultados = [];
            // Buscar todos los contenedores de mensajes
            const contenedores = document.querySelectorAll('div[aria-label*="message"], div[aria-label*="Mensaje"]');

            contenedores.forEach(cont => {
                // Saltar el mensaje de fecha/hora si existe
                const texto = cont.textContent?.trim();
                if (!texto || texto.length < 3) return;

                // Determinar tipo (incoming = otros, outgoing = yo)
                const esEntrante = cont.closest('[data-testid="incoming"]') !== null ||
                                   cont.closest('[data-testid*="incoming"]') !== null;
                const esSaliente = cont.closest('[data-testid="outgoing"]') !== null ||
                                  cont.closest('[data-testid*="outgoing"]') !== null;

                // Extraer texto del mensaje
                let textoMsg = '';
                cont.querySelectorAll('span').forEach(span => {
                    const t = span.textContent?.trim();
                    if (t && t.length > 0 && t.length < 500 && !t.includes('AM') && !t.includes('PM')) {
                        if (t.length > textoMsg.length) textoMsg = t;
                    }
                });

                if (textoMsg && textoMsg.length > 2) {
                    resultados.push({
                        tipo: esEntrante ? 'entrante' : (esSaliente ? 'saliente' : 'desconocido'),
                        texto: textoMsg,
                        hora: new Date().toISOString()
                    });
                }
            });

            return resultados;
        }
        return getMensajes();
        """
        try:
            return self.driver.execute_script(js_script)
        except Exception as e:
            logger.debug(f"Error extrayendo mensajes: {e}")
            return []

    def _enviar_respuesta(self, texto: str):
        """Envía un mensaje al chat."""
        js_script = f"""
        // Encontrar el campo de texto
        const input = document.querySelector('div[title="Escribe un mensaje"] div[contenteditable="true"]') ||
                      document.querySelector('div[data-testid="conversation-compose-box-input"] div[contenteditable="true"]');

        if (input) {{
            input.textContent = '';
            input.focus();

            // Simular escritura
            const textEvent = new InputEvent('input', {{
                bubbles: true,
                cancelable: true,
                inputType: 'insertText',
                data: arguments[0]
            }});
            input.dispatchEvent(textEvent);

            // Presionar Enter para enviar
            setTimeout(() => {{
                const enterEvent = new KeyboardEvent('keydown', {{
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13,
                    bubbles: true
                }});
                input.dispatchEvent(enterEvent);
            }}, 100);
        }}
        """
        try:
            self.driver.execute_script(js_script, texto)
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"Error enviando mensaje: {e}")
            return False

    def _ejecutar_loop(self):
        """Loop principal de monitoreo."""
        from WhatsAppBot import WhatsAppBot
        self.bot = WhatsAppBot()

        # Cargar IDs procesados
        ids_procesados = set()
        if ARCHIVO_IDS.exists():
            try:
                with open(ARCHIVO_IDS, "r", encoding="utf-8") as f:
                    ids_procesados = set(json.load(f))
            except:
                pass

        logger.info(f"IDs procesados: {len(ids_procesados)}")
        logger.info("MONITOREANDO... (Ctrl+C para detener)")

        while True:
            try:
                mensajes = self._extraer_mensajes()

                for msg in mensajes:
                    texto = msg.get('texto', '')
                    tipo = msg.get('tipo', '')
                    msg_id = f"{texto[:30]}|{msg.get('hora', '')}"

                    # Solo procesar entrantes no procesados
                    if tipo == 'entrante' and texto.strip() and msg_id not in ids_procesados:
                        logger.info(f"MENSAJE: {texto}")

                        # Procesar con el bot
                        respuesta = self.bot.procesar_comando(texto)

                        if respuesta:
                            logger.info(f"RESPONDIENDO: {respuesta[:50]}...")

                            if self._enviar_respuesta(respuesta):
                                logger.info("ENVIADO!")
                                ids_procesados.add(msg_id)

                                # Verificar series restantes
                                with open(ARCHIVO_SERIES, "r", encoding="utf-8") as f:
                                    series = json.load(f)
                                disponibles = len([s for s in series if s.get("estado") == "disponible"])
                                logger.info(f"Series restantes: {disponibles}")
                        else:
                            logger.debug(f"Sin respuesta para: {texto[:30]}")

                        ids_procesados.add(msg_id)

                # Guardar IDs periódicamente
                if len(ids_procesados) > 500:
                    ids_procesados = set(list(ids_procesados)[-500:])
                    ARCHIVO_IDS.parent.mkdir(exist_ok=True)
                    with open(ARCHIVO_IDS, "w", encoding="utf-8") as f:
                        json.dump(list(ids_procesados), f, ensure_ascii=False)

            except Exception as e:
                logger.error(f"Error en loop: {e}")

            time.sleep(self.intervalo)

    def detener(self):
        if self.driver:
            self.driver.quit()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--grupo", "-g", default="Mis perros")
    parser.add_argument("--intervalo", "-i", type=float, default=3.0)
    args = parser.parse_args()

    monitor = WhatsAppMonitor(args.grupo, args.intervalo)

    try:
        monitor.iniciar()
    except KeyboardInterrupt:
        logger.info("Detenido por usuario")
    finally:
        monitor.detener()


if __name__ == "__main__":
    main()