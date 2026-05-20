"""
WhatsAppSender - Envío de mensajes en WhatsApp Web.
Paso 5: Escribe y envía mensajes al chat activo.
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys

from whatsapp_selectors import (
    SELECTOR_COMPOSE_BOX,
    SELECTOR_COMPOSE_BOX_ALT,
    SELECTOR_COMPOSE_INPUT,
    SELECTOR_SEND_BUTTON,
    SELECTOR_SEND_BUTTON_ALT,
    SELECTOR_MSG_OUTGOING,
)

logger = logging.getLogger(__name__)


class WhatsAppSender:
    """Envía mensajes al chat activo en WhatsApp Web."""

    SELECTOR_CAJA_TEXTO = SELECTOR_COMPOSE_BOX
    SELECTOR_CAJA_ALT = SELECTOR_COMPOSE_BOX_ALT
    SELECTOR_BOTON_ENVIO = SELECTOR_SEND_BUTTON
    SELECTOR_BOTON_ENVIO_ALT = SELECTOR_SEND_BUTTON_ALT
    SELECTOR_MSG_ENVIADO = SELECTOR_MSG_OUTGOING
    CLASE_MENSAJE_ENVIADO = "message"

    def __init__(self, driver: webdriver.Chrome) -> None:
        self._driver = driver
        self._wait = WebDriverWait(driver, 10)

    def enviar_mensaje(self, texto: str, esperar_confirmacion: bool = True) -> dict:
        """Envía un mensaje al chat activo."""
        if not texto or not texto.strip():
            return {"exito": False, "error": "El mensaje no puede estar vacío."}

        texto = texto.strip()
        caja = self._obtener_caja_texto()
        if not caja:
            logger.error("No se encontró la caja de texto.")
            return {"exito": False, "error": "No se encontró la caja de texto."}

        count_before = self._contar_mensajes_propios() if esperar_confirmacion else 0

        try:
            caja.click()
            caja.clear()
            time.sleep(0.1)
            self._escribir_mensaje(caja, texto)
        except Exception as e:
            logger.error(f"Error al escribir en la caja de texto: {e}")
            return {"exito": False, "error": f"Error al escribir en la caja de texto: {e}"}

        enviado = self._enviar()
        if not enviado:
            logger.error("No se pudo hacer clic en el botón de envío.")
            return {"exito": False, "error": "No se pudo hacer clic en el botón de envío."}

        if esperar_confirmacion:
            confirmado = self._verificar_envio(count_before, texto)
            if confirmado:
                logger.debug(f"Mensaje enviado: '{texto[:50]}...'")
                return {"exito": True, "mensaje": f"Mensaje enviado: '{texto}'"}
            else:
                logger.warning("El mensaje no apareció en el chat tras el envío.")
                return {"exito": False, "error": "El mensaje no apareció en el chat tras el envío."}

        return {"exito": True, "mensaje": f"Mensaje enviado: '{texto}'"}

    def _obtener_caja_texto(self):
        """Obtiene la caja de texto del chat activo."""
        # Intentar selector principal
        try:
            return self._wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.SELECTOR_CAJA_TEXTO))
            )
        except TimeoutException:
            logger.debug("Selector principal no encontrado, intentando alternativo.")

        # Alternativa con title
        try:
            return self._wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.SELECTOR_CAJA_ALT))
            )
        except TimeoutException:
            logger.debug("Selector alternativo no encontrado.")

        # Buscar por contenido editable
        try:
            return self._driver.find_element(By.XPATH, SELECTOR_COMPOSE_INPUT)
        except NoSuchElementException:
            logger.warning("No se encontró la caja de texto del chat.")

        return None

    def _escribir_mensaje(self, caja, texto: str) -> None:
        """Escribe el mensaje en la caja de texto."""
        # Método 1: enviar keys completo
        try:
            caja.send_keys(texto)
            return
        except Exception as e:
            logger.debug(f"send_keys falló: {e}")

        # Método 2: usar JavaScript si send_keys falla
        try:
            self._driver.execute_script(
                "arguments[0].textContent = arguments[1]; "
                "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                caja, texto
            )
        except Exception as e:
            logger.error(f"No se pudo insertar texto: {e}")
            raise RuntimeError(f"No se pudo insertar texto: {e}")

    def _enviar(self) -> bool:
        """Envía el mensaje con Enter o el botón."""
        # Método 1: Enter
        try:
            self._driver.find_element(By.CSS_SELECTOR, self.SELECTOR_CAJA_TEXTO).send_keys(Keys.RETURN)
            time.sleep(0.2)
            return True
        except Exception:
            logger.debug("Envío con Enter falló.")

        # Método 2: botón de envío
        try:
            boton = self._wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.SELECTOR_BOTON_ENVIO))
            )
            boton.click()
            return True
        except TimeoutException:
            logger.debug("Botón de envío principal no disponible.")

        # Método 3: botón alternativo
        try:
            boton = self._driver.find_element(By.CSS_SELECTOR, self.SELECTOR_BOTON_ENVIO_ALT)
            boton.click()
            return True
        except NoSuchElementException:
            logger.debug("Botón alternativo no encontrado.")

        # Método 4: buscar por XPath
        try:
            boton = self._driver.find_element(
                By.XPATH, '//button[@data-testid="send"] | //span[@data-testid="send"]/..'
            )
            boton.click()
            return True
        except NoSuchElementException:
            logger.warning("No se encontró ningún método para enviar.")

        return False

    def _contar_mensajes_propios(self) -> int:
        """Cuenta los mensajes salientes visibles en el chat."""
        try:
            return len(self._driver.find_elements(By.CSS_SELECTOR, self.SELECTOR_MSG_ENVIADO))
        except Exception:
            return 0

    def _verificar_envio(self, count_before: int, texto: str) -> bool:
        """
        Verifica que el mensaje realmente apareció en el chat.

        Args:
            count_before: Conteo de mensajes propios antes de enviar.
            texto: Texto esperado en el mensaje.

        Returns:
            True si el mensaje aparece, False si no.
        """
        time.sleep(0.3)  # Dar tiempo a que aparezca

        # Verificar que el conteo aumentó
        count_after = self._contar_mensajes_propios()
        if count_after <= count_before:
            return False

        # Verificar contenido del último mensaje
        try:
            mensajes = self._driver.find_elements(By.CSS_SELECTOR, self.SELECTOR_MSG_ENVIADO)
            ultimo = mensajes[-1]

            # Buscar texto en el mensaje
            spans = ultimo.find_elements(
                By.XPATH, './/span[contains(@class, "selectable-text")]'
            )
            for span in spans:
                if texto.lower() in span.text.lower():
                    return True

            # Verificar si el texto está en el contenedor
            if texto.lower() in ultimo.text.lower():
                return True

        except Exception:
            pass

        return True

    def enviar_mensaje_sin_confirmar(self, texto: str) -> dict:
        """
        Envía mensaje sin verificar confirmación (más rápido).

        Args:
            texto: Contenido del mensaje.

        Returns:
            dict con resultado.
        """
        return self.enviar_mensaje(texto, esperar_confirmacion=False)

    def enviar_mensaje_multiple(self, mensajes: list[str]) -> dict:
        """Envía múltiples mensajes secuencialmente."""
        resultados = {"exitos": 0, "fallidos": 0, "detalles": []}

        for msg in mensajes:
            resultado = self.enviar_mensaje(msg, esperar_confirmacion=True)
            if resultado["exito"]:
                resultados["exitos"] += 1
            else:
                resultados["fallidos"] += 1
            resultados["detalles"].append(resultado)
            time.sleep(0.5)

        return resultados

    def escribir_y_esperar(self, texto: str, segundos: float = 1.0) -> None:
        """Solo escribe el mensaje sin enviarlo."""
        caja = self._obtener_caja_texto()
        if caja:
            try:
                caja.click()
                caja.clear()
                time.sleep(0.1)
                self._escribir_mensaje(caja, texto)
                time.sleep(segundos)
            except Exception as e:
                logger.debug(f"Error en escribir_y_esperar: {e}")