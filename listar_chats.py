"""
Script para listar todos los chats disponibles en WhatsApp Web.
Útil para encontrar el nombre exacto del grupo que quieres monitorear.
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

CHROME_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1280,800",
]


def listar_chats():
    """Lista todos los chats disponibles."""
    opciones = Options()
    for arg in CHROME_ARGS:
        opciones.add_argument(arg)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opciones)
    except Exception:
        logger.info("Usando Chrome sin webdriver-manager...")
        driver = webdriver.Chrome(options=opciones)

    driver.get("https://web.whatsapp.com")
    logger.info("Abriendo WhatsApp Web...")
    print("Esperando autenticación...")

    wait = WebDriverWait(driver, 120)

    try:
        # Esperar sidebar
        wait.until(EC.presence_of_element_located(
            (By.XPATH, '//div[@data-testid="chat-list"]')
        ))
        logger.info("Sesión activa. Listando chats...")
        time.sleep(2)

        # Buscar todos los títulos
        titulos = driver.find_elements(By.XPATH, '//span[@title]')

        chats = []
        for titulo in titulos:
            try:
                texto = titulo.text.strip()
                if texto and len(texto) > 1:
                    chats.append(texto)
            except Exception:
                continue

        # Eliminar duplicados
        chats = list(dict.fromkeys(chats))

        print("\n" + "=" * 60)
        print("CHATS DISPONIBLES:")
        print("=" * 60)

        for i, chat in enumerate(chats, 1):
            print(f"{i}. {chat}")

        print("=" * 60)
        print(f"Total: {len(chats)} chats\n")

        # Preguntar si quiere probar uno
        print("Para monitorear un chat, usa:")
        print('  python whatsapp_loop.py --grupo "NOMBRE_DEL_CHAT"\n')

    except Exception as e:
        logger.error(f"Error: {e}")

    finally:
        input("Presiona Enter para cerrar el navegador...")
        driver.quit()


if __name__ == "__main__":
    listar_chats()