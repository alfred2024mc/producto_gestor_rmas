"""
WhatsAppSelection - Selección de grupos y contactos en WhatsApp Web.
Paso 3: Busca y abre un chat específico por nombre.
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from whatsapp_selectors import (
    SELECTOR_SEARCH_BOX,
    SELECTOR_SIDEBAR_CHAT_LIST,
    SELECTOR_CHAT_ITEM,
    SELECTOR_CHAT_TITLE,
    SELECTOR_CHAT_HEADER,
    SELECTOR_CONVERSATION_PANEL,
    SELECTOR_MSG_CONTAINER,
    SELECTOR_MESSAGE_LIST,
)

logger = logging.getLogger(__name__)


class WhatsAppSelection:
    """Maneja la búsqueda y selección de chats en WhatsApp Web."""

    def __init__(self, driver: webdriver.Chrome) -> None:
        self._driver = driver
        self._wait = WebDriverWait(driver, 15)

    def seleccionar_chat(self, nombre: str, tipo: str = "cualquiera") -> dict:
        """
        Busca y abre un chat por nombre.

        Args:
            nombre: Nombre del grupo o contacto a buscar.
            tipo: "grupo", "contacto" o "cualquiera" (default).

        Returns:
            dict con "exito" (bool) y "elemento" (WebElement) o "mensaje" (str).
        """
        # Asegurar que estamos en la vista principal
        self._hacer_scroll_arriba()
        time.sleep(0.5)

        # Intentar método principal: buscar en la lista directamente
        resultado = self._buscar_chat_directo(nombre)
        if resultado["exito"]:
            return resultado

        # Si no funciona, intentar con el campo de búsqueda
        logger.debug(f"Búsqueda directa falló, intentando con search box...")
        return self._buscar_con_busqueda(nombre, tipo)

    def _buscar_chat_directo(self, nombre: str) -> dict:
        """Busca el chat scrolleando la lista."""
        nombre_lower = nombre.lower().strip()

        try:
            # Scroll por la lista de chats
            for _ in range(10):
                chats = self._driver.find_elements(
                    By.CSS_SELECTOR, 'div[data-testid="chat-list"] > div'
                )

                for chat in chats:
                    try:
                        titulo = chat.find_element(By.XPATH, './/span[@title]')
                        titulo_texto = titulo.text.strip().lower()

                        if nombre_lower in titulo_texto or titulo_texto in nombre_lower:
                            chat.click()
                            time.sleep(0.5)
                            logger.info(f"Chat '{nombre}' abierto.")
                            return {"exito": True, "elemento": chat}
                    except NoSuchElementException:
                        continue
                    except Exception:
                        continue

                # Scroll hacia abajo para cargar más chats
                self._driver.execute_script(
                    "window.scrollBy(0, 300);"
                )
                time.sleep(0.3)

        except Exception as e:
            logger.debug(f"Error en búsqueda directa: {e}")

        return {"exito": False, "mensaje": "Chat no encontrado"}

    def _buscar_con_busqueda(self, nombre: str, tipo: str) -> dict:
        """Busca usando el campo de búsqueda de WhatsApp."""
        try:
            # Buscar el input de búsqueda
            search_input = self._wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SELECTOR_SEARCH_BOX))
            )
            search_input.click()
            time.sleep(0.3)

            # Limpiar y escribir
            search_input.clear()
            search_input.send_keys(nombre)
            time.sleep(1)

            # Esperar resultados
            self._esperar_resultados()

            # Buscar en resultados
            resultado = self._seleccionar_de_resultados(nombre)
            if resultado["exito"]:
                return resultado

            # Limpiar búsqueda
            search_input.clear()

        except TimeoutException:
            logger.debug("Timeout en búsqueda, intentando alternativa...")

        # Alternativa: buscar cualquier chat que coincida
        return self._busqueda_alternativa(nombre, tipo)

    def _esperar_resultados(self) -> None:
        """Espera a que los resultados de búsqueda carguen."""
        time.sleep(1)

    def _seleccionar_de_resultados(self, nombre: str) -> dict:
        """Selecciona el chat de los resultados de búsqueda."""
        nombre_lower = nombre.lower().strip()

        try:
            # Buscar todos los títulos en la lista
            titulos = self._driver.find_elements(By.XPATH, '//span[@title]')

            for titulo in titulos:
                try:
                    titulo_texto = titulo.text.strip().lower()
                    if nombre_lower in titulo_texto or titulo_texto in nombre_lower:
                        # Hacer clic en el elemento padre
                        chat = titulo
                        for _ in range(5):
                            chat = chat.find_element(By.XPATH, "./..")
                            if chat.get_attribute("data-testid"):
                                chat.click()
                                return {"exito": True, "elemento": chat}
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Error seleccionando de resultados: {e}")

        return {"exito": False, "mensaje": "No se encontró en resultados"}

    def _busqueda_alternativa(self, nombre: str, tipo: str) -> dict:
        """Método alternativo si la búsqueda principal no encuentra resultados."""
        logger.debug(f"Ejecutando búsqueda alternativa para '{nombre}'")

        try:
            # Presionar Escape para cerrar búsqueda
            from selenium.webdriver.common.keys import Keys
            self._driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)

            # Buscar todos los chats en la lista
            chats = self._driver.find_elements(
                By.CSS_SELECTOR, 'div[data-testid="chat-list"] > div'
            )

            nombre_lower = nombre.lower().strip()

            for chat in chats:
                try:
                    titulo = chat.find_element(By.XPATH, './/span[@title]')
                    titulo_texto = titulo.text.strip()

                    if nombre_lower in titulo_texto.lower():
                        chat.click()
                        logger.info(f"Chat '{nombre_texto}' abierto via alternativa.")
                        time.sleep(0.5)
                        return {"exito": True, "elemento": chat}
                except NoSuchElementException:
                    continue
                except Exception as e:
                    logger.debug(f"Error procesando chat: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error en búsqueda alternativa: {e}")

        return {
            "exito": False,
            "mensaje": f"No se encontró '{nombre}'."
        }

    def _hacer_scroll_arriba(self) -> None:
        """Desplaza la lista de chats hacia arriba."""
        try:
            self._driver.execute_script("window.scrollTo(0, 0);")
        except Exception:
            pass

    def verificar_chat_activo(self, nombre: str) -> bool:
        """Verifica si un chat está actualmente abierto."""
        try:
            header = self._driver.find_element(By.XPATH, SELECTOR_CHAT_HEADER)
            return nombre.lower() in header.text.lower()
        except NoSuchElementException:
            try:
                # Alternativa: buscar en el título del chat activo
                titulo = self._driver.find_element(
                    By.CSS_SELECTOR, 'header span[title]'
                )
                return nombre.lower() in titulo.text.lower()
            except Exception:
                return False

    def esperar_chat_cargado(self, timeout: int = 10) -> bool:
        """Espera a que el chat actual termine de cargar."""
        try:
            wait = WebDriverWait(self._driver, timeout)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, SELECTOR_MSG_CONTAINER)
                )
            )
            return True
        except TimeoutException:
            logger.warning("Timeout esperando que cargue el chat.")
            return False