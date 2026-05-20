"""
Diagnosticar chats disponibles en WhatsApp Web.
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHROME_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1280,800",
]

def main():
    opciones = Options()
    for arg in CHROME_ARGS:
        opciones.add_argument(arg)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opciones)

    driver.get("https://web.whatsapp.com")
    print("\n" + "=" * 60)
    print("Esperando que cargue WhatsApp Web...")
    print("Escanea el QR si es necesario...")
    print("=" * 60)

    # Esperar a que cargue la sidebar
    wait = WebDriverWait(driver, 120)
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, '//div[@id="side"]')))
        print("\nSesion iniciada!\n")
    except Exception:
        print("Timeout. Intenta de nuevo.")
        driver.quit()
        return

    # Buscar el campo de busqueda
    print("Buscando barra de busqueda...")
    time.sleep(2)

    # Obtener todos los titulos de chats
    print("\n" + "=" * 60)
    print("CHATS ENCONTRADOS:")
    print("=" * 60)

    js_script = """
    const titulos = document.querySelectorAll('div[data-testid="chat-list"] span[title]');
    const textos = [];
    titulos.forEach(t => {
        textos.push(t.textContent.trim());
    });
    return textos;
    """

    chats = driver.execute_script(js_script)

    # Eliminar duplicados
    seen = set()
    unique = []
    for c in chats:
        if c not in seen and c:
            seen.add(c)
            unique.append(c)

    if unique:
        print(f"\nEncontrados {len(unique)} chats:\n")
        for i, chat in enumerate(unique, 1):
            try:
                print(f"  {i}. {chat}")
            except UnicodeEncodeError:
                print(f"  {i}. [Caracteres especiales]")
    else:
        print("\nNo se encontraron chats visibles.")
        print("Intenta hacer scroll en la lista de chats.\n")

    print("\n" + "=" * 60)
    print("Escribe el nombre EXACTO del grupo que quieres monitorear")
    print("=" * 60)

    input("\nPresiona Enter para cerrar...")
    driver.quit()

if __name__ == "__main__":
    main()