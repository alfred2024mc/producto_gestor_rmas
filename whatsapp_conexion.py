"""
WhatsAppConnection - Inicialización de Selenium y conexión a WhatsApp Web.
Paso 2: Solo establece la conexión inicial, sin selección de grupo ni lectura de mensajes.
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from whatsapp_selectors import (
    URL_WHATSAPP,
    SELECTOR_SIDEBAR,
    SELECTOR_QR_CODE,
    CHROME_ARGS,
)

logger = logging.getLogger(__name__)


class WhatsAppConnection:
    """Maneja la conexión con WhatsApp Web usando Selenium."""

    URL_WHATSAPP = "https://web.whatsapp.com"

    def __init__(self, perfil_path: str | None = None) -> None:
        self._driver: webdriver.Chrome | None = None
        self._perfil_path = perfil_path

    def conectar(self) -> webdriver.Chrome:
        """
        Inicializa Chrome, abre WhatsApp Web y espera el escaneo del QR.
        Retorna el driver una vez autenticado.
        """
        self._driver = self._crear_driver()
        self._driver.get(URL_WHATSAPP)
        logger.info("Abriendo WhatsApp Web...")
        print("Esperando escaneo del código QR...")
        print("Por favor, escanea el código QR con tu teléfono.")

        self._esperar_autenticacion()
        logger.info("Sesión iniciada correctamente.")
        return self._driver

    def _crear_driver(self) -> webdriver.Chrome:
        """Configura y retorna el driver de Chrome."""
        opciones = Options()
        for arg in CHROME_ARGS:
            opciones.add_argument(arg)

        opciones.add_experimental_option("excludeSwitches", ["enable-automation"])
        opciones.add_experimental_option("useAutomationExtension", False)

        if self._perfil_path:
            opciones.add_argument(f"--user-data-dir={self._perfil_path}")
            logger.info(f"Usando perfil: {self._perfil_path}")

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opciones)
        except Exception:
            logger.debug("webdriver-manager falló, intentando sin él...")
            driver = webdriver.Chrome(options=opciones)

        driver.implicitly_wait(5)
        return driver

    def _esperar_autenticacion(self) -> None:
        """Espera hasta que el usuario escanee el QR o ya esté autenticado."""
        wait = WebDriverWait(self._driver, 120)

        try:
            wait.until(EC.presence_of_element_located(
                (By.XPATH, SELECTOR_SIDEBAR)
            ))
            logger.info("Sesión existente detectada.")
            return
        except TimeoutException:
            pass

        try:
            qr_code = self._driver.find_element(By.XPATH, SELECTOR_QR_CODE)
            logger.info("Código QR detectado. Esperando escaneo...")
            print("Por favor, escanea el código QR con tu teléfono.")

            wait.until(EC.staleness_of(qr_code))
            logger.info("QR escaneado. Verificando conexión...")

            wait.until(EC.presence_of_element_located(
                (By.XPATH, SELECTOR_SIDEBAR)
            ))
        except TimeoutException:
            logger.error("Timeout esperando autenticación.")
            raise RuntimeError("No se pudo autenticar en WhatsApp Web")

    def listar_chats(self) -> list[str]:
        """Lista todos los nombres de chats disponibles."""
        chats = []
        try:
            # Esperar a que carguen los chats
            time.sleep(2)

            # Buscar todos los títulos de chat
            elementos = self._driver.find_elements(By.XPATH, '//span[@title]')

            for elem in elementos:
                try:
                    texto = elem.text.strip()
                    if texto and len(texto) > 0:
                        chats.append(texto)
                except Exception:
                    continue

            # Eliminar duplicados preservando orden
            seen = set()
            unique = []
            for c in chats:
                if c not in seen:
                    seen.add(c)
                    unique.append(c)

            return unique

        except Exception as e:
            logger.error(f"Error listando chats: {e}")
            return []

    def cerrar(self) -> None:
        """Cierra el navegador y termina la sesión."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
            logger.info("Conexión cerrada.")

    def get_driver(self) -> webdriver.Chrome | None:
        """Retorna el driver activo."""
        return self._driver

    def esta_conectado(self) -> bool:
        """Verifica si el driver existe y está activo."""
        try:
            return self._driver is not None and len(self._driver.window_handles) > 0
        except Exception:
            return False