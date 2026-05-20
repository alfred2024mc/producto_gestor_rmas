"""
WhatsAppMessages - Lectura de mensajes del chat activo.
Paso 4: Captura, clasifica y extrae mensajes de WhatsApp Web.
"""

import time
import logging
from datetime import datetime
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from whatsapp_selectors import (
    SELECTOR_MSG_CONTAINER,
    SELECTOR_MSG_TEXT,
    SELECTOR_MSG_META,
    SELECTOR_MSG_OUTGOING,
    SELECTOR_MSG_INCOMING,
    SELECTOR_MESSAGE_LIST,
)

logger = logging.getLogger(__name__)


class WhatsAppMessages:
    """Lee y procesa mensajes del chat activo en WhatsApp Web."""

    SELECTOR_MENSAJES = SELECTOR_MSG_CONTAINER
    SELECTOR_TEXTO = SELECTOR_MSG_TEXT
    SELECTOR_HORA = SELECTOR_MSG_META
    SELECTOR_MINE = SELECTOR_MSG_OUTGOING
    SELECTOR_RECV = SELECTOR_MSG_INCOMING
    SELECTOR_LISTA = SELECTOR_MESSAGE_LIST

    def __init__(self, driver: webdriver.Chrome) -> None:
        self._driver = driver
        self._wait = WebDriverWait(driver, 15)

    def obtener_mensajes(self, limite: int = 50) -> list[dict]:
        """
        Obtiene todos los mensajes visibles en el chat actual.

        Args:
            limite: Máximo de mensajes a capturar (default 50).

        Returns:
            Lista de diccionarios con {"tipo", "texto", "hora", "id"}.
        """
        mensajes = []
        contenedores = self._obtener_contenedores_mensajes()

        for contenedor in contenedores[:limite]:
            msg = self._procesar_contenedor(contenedor)
            if msg and msg["texto"]:
                mensajes.append(msg)

        return mensajes

    def obtener_ultimo_mensaje(self, tipo: str = "entrante") -> Optional[dict]:
        """
        Obtiene el último mensaje del tipo especificado.

        Args:
            tipo: "entrante", "saliente" o "cualquiera" (default: "entrante").

        Returns:
            dict con {"tipo", "texto", "hora", "id"} o None si no hay mensajes.
        """
        mensajes = self.obtener_mensajes(limite=100)

        if tipo == "cualquiera":
            return mensajes[-1] if mensajes else None

        filtrados = [m for m in mensajes if m["tipo"] == tipo]
        return filtrados[-1] if filtrados else None

    def obtener_texto_ultimo_entrante(self) -> Optional[str]:
        """
        Retorna el texto del último mensaje entrante.
        Diseñado para integración con WhatsAppBot.procesar_comando().

        Returns:
            Texto del mensaje o None si no hay mensajes entrantes.
        """
        ultimo = self.obtener_ultimo_mensaje(tipo="entrante")
        return ultimo["texto"] if ultimo else None

    def esperar_nuevo_mensaje(self, timeout: int = 30) -> Optional[str]:
        """Espera un nuevo mensaje entrante en el chat."""
        count_before = self._contar_mensajes()

        try:
            wait = WebDriverWait(self._driver, timeout)
            wait.until(lambda d: self._contar_mensajes() > count_before)
            self._driver.implicitly_wait(0)
            time.sleep(0.3)
            self._driver.implicitly_wait(5)

            ultimo = self.obtener_ultimo_mensaje(tipo="entrante")
            return ultimo["texto"] if ultimo else None

        except TimeoutException:
            logger.debug(f"Timeout esperando mensaje nuevo ({timeout}s)")
            return None

    def _obtener_contenedores_mensajes(self) -> list:
        """Obtiene los contenedores de mensajes del chat activo."""
        try:
            return self._driver.find_elements(By.CSS_SELECTOR, self.SELECTOR_MENSAJES)
        except Exception as e:
            logger.debug(f"Error obteniendo contenedores: {e}")

        try:
            lista = self._driver.find_element(By.CSS_SELECTOR, self.SELECTOR_LISTA)
            return lista.find_elements(By.XPATH, "./*")
        except Exception as e:
            logger.debug(f"Error en búsqueda alternativa: {e}")

        return []

    def _contar_mensajes(self) -> int:
        """Cuenta los mensajes visibles en el chat."""
        try:
            return len(self._driver.find_elements(By.CSS_SELECTOR, self.SELECTOR_MENSAJES))
        except Exception:
            return 0

    def _procesar_contenedor(self, contenedor) -> Optional[dict]:
        """
        Extrae información de un contenedor de mensaje.

        Args:
            contenedor: WebElement del mensaje.

        Returns:
            dict con datos del mensaje o None si falla.
        """
        try:
            clases = contenedor.get_attribute("class") or ""
            tipo = self._determinar_tipo(clases, contenedor)

            texto = self._extraer_texto(contenedor)
            hora = self._extraer_hora(contenedor)
            msg_id = self._generar_id(contenedor)

            return {
                "tipo": tipo,
                "texto": texto,
                "hora": hora,
                "id": msg_id
            }

        except (StaleElementReferenceException, Exception):
            return None

    def _determinar_tipo(self, clases: str, contenedor) -> str:
        """
        Determina si el mensaje es entrante o saliente.

        Args:
            clases: Clases CSS del contenedor.
            contenedor: WebElement para buscar atributos.

        Returns:
            "entrante" o "saliente".
        """
        clases_lower = clases.lower()

        if "outgoing" in clases_lower or "mine" in clases_lower:
            return "saliente"
        if "incoming" in clases_lower or "theirs" in clases_lower:
            return "entrante"

        # Verificar por atributos data-testid
        testid = contenedor.get_attribute("data-testid") or ""
        if "outgoing" in testid:
            return "saliente"
        if "incoming" in testid:
            return "entrante"

        # Intentar buscar expandos indicadores
        try:
            contenedores = contenedor.find_elements(By.XPATH, ".//*[@data-testid='outgoing']")
            if contenedores:
                return "saliente"
            contenedores = contenedor.find_elements(By.XPATH, ".//*[@data-testid='incoming']")
            if contenedores:
                return "entrante"
        except Exception:
            pass

        # Por descarte, asumir entrante (los mensajes del bot son salientes)
        return "entrante"

    def _extraer_texto(self, contenedor) -> str:
        """
        Extrae el texto del mensaje.

        Args:
            contenedor: WebElement del mensaje.

        Returns:
            Texto limpio o string vacío.
        """
        try:
            # Intentar selectores específicos de WhatsApp
            texto_elem = contenedor.find_element(
                By.CSS_SELECTOR, "div[data-testid='msg-text'] span"
            )
            return texto_elem.text.strip()
        except Exception:
            pass

        try:
            # Alternativa: buscar spans con clase selectable-text
            spans = contenedor.find_elements(
                By.XPATH, './/span[contains(@class, "selectable-text")]'
            )
            for span in spans:
                if span.text.strip():
                    return span.text.strip()
        except Exception:
            pass

        try:
            # Último recurso: buscar cualquier texto en el contenedor
            return contenedor.text.strip()
        except Exception:
            return ""

    def _extraer_hora(self, contenedor) -> str:
        """
        Extrae la hora del mensaje.

        Args:
            contenedor: WebElement del mensaje.

        Returns:
            Hora en formato legible o string vacío.
        """
        try:
            meta = contenedor.find_element(By.CSS_SELECTOR, "div[data-testid='msg-meta'] span")
            return meta.text.strip()
        except Exception:
            return ""

    def _generar_id(self, contenedor) -> str:
        """
        Genera un identificador único para el mensaje.

        Args:
            contenedor: WebElement del mensaje.

        Returns:
            String con timestamp o hash parcial.
        """
        try:
            # Intentar obtener attributes que identifiquen el mensaje
            data_id = contenedor.get_attribute("data-id") or ""
            if data_id:
                return data_id
        except Exception:
            pass

        return datetime.now().isoformat()

    def tiene_mensajes_nuevos(self, desde_hora: str) -> bool:
        """
        Verifica si hay mensajes más recientes que la hora especificada.

        Args:
            desde_hora: Hora de referencia (formato ISO o legible).

        Returns:
            True si hay mensajes nuevos.
        """
        mensajes = self.obtener_mensajes(limite=10)
        return any(m["hora"] > desde_hora for m in mensajes if m["hora"])

    def hacer_scroll_chat(self) -> None:
        """Desplaza el chat hacia abajo para cargar más mensajes."""
        try:
            lista = self._driver.find_element(By.CSS_SELECTOR, self.SELECTOR_LISTA)
            self._driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight;", lista
            )
        except Exception:
            pass

    def hacer_scroll_arriba(self) -> None:
        """Desplaza el chat hacia arriba."""
        try:
            lista = self._driver.find_element(By.CSS_SELECTOR, self.SELECTOR_LISTA)
            self._driver.execute_script(
                "arguments[0].scrollTop = 0;", lista
            )
        except Exception:
            pass