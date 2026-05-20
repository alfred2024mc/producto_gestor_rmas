"""
Script de diagnóstico para WhatsApp Web - Versión simple.
Solo espera que cargue y lista los chats disponibles.
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHROME_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1280,800",
]


def diagnostico():
    """Diagnóstico simple de WhatsApp Web."""

    opciones = Options()
    for arg in CHROME_ARGS:
        opciones.add_argument(arg)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opciones)
    except Exception:
        driver = webdriver.Chrome(options=opciones)

    driver.get("https://web.whatsapp.com")
    logger.info("Abriendo WhatsApp Web...")

    print("Esperando a que cargue la página...")
    time.sleep(5)

    # Intentar clickear en el搜索 para abrir la lista de chats
    print("Buscando barra de búsqueda...")

    # Selector alternativo
    selectores_alt = [
        'div[title="Buscar o empezar un chat nuevo"]',
        'div[data-testid="chat-list-search"]',
        'div[data-testid="chat-list-search"] input',
        'input[title="Buscar o empezar un chat nuevo"]',
        '#side span[title]',
    ]

    input_encontrado = None
    for sel in selectores_alt:
        try:
            elem = driver.find_element(By.CSS_SELECTOR, sel)
            if elem:
                print(f"  Encontrado con: {sel}")
                input_encontrado = elem
                break
        except Exception:
            pass

    if input_encontrado:
        print("Clickeando en el campo de búsqueda...")
        input_encontrado.click()
        time.sleep(1)

        # Escribir el nombre del grupo
        print("Escribiendo 'Mis perros'...")
        input_encontrado.send_keys("Mis perros")
        time.sleep(2)

        # Ahora buscar los resultados
        print("Buscando resultados...")

        # Usar JavaScript para obtener todos los títulos
        js = """
        const titulos = document.querySelectorAll('span[title]');
        const textos = [];
        titulos.forEach(t => {
            textos.push(t.textContent.trim());
        });
        return textos;
        """

        titulos = driver.execute_script(js)

        print("\n" + "=" * 70)
        print("TÍTULOS ENCONTRADOS:")
        print("=" * 70)
        for i, t in enumerate(titulos[:30], 1):
            print(f"{i}. {t}")
        print("=" * 70)

        # Verificar si "Mis perros" está en los resultados
        if any('Mis perros' in t for t in titulos):
            print("\n*** 'Mis perros' SÍ aparece en los resultados ***")
        else:
            print("\n*** 'Mis perros' NO aparece ***")

    else:
        print("\nNo se encontró el campo de búsqueda.")
        print("Buscando cualquier span con title...")

        # Buscar todos los títulos disponibles
        js = """
        const titulos = document.querySelectorAll('[title]');
        const textos = [];
        titulos.forEach(t => {
            const text = t.textContent.trim();
            if (text && text.length > 0 && text.length < 100) {
                textos.push(text);
            }
        });
        return textos;
        """

        titulos = driver.execute_script(js)

        print(f"\nEncontrados {len(titulos)} títulos:")
        for i, t in enumerate(titulos[:20], 1):
            print(f"{i}. {t}")

        if any('Mis perros' in t for t in titulos):
            print("\n*** 'Mis perros' SÍ aparece ***")
        else:
            print("\n*** 'Mis perros' NO aparece ***")

    print("\nCerrando en 20 segundos...")
    time.sleep(20)
    driver.quit()


if __name__ == "__main__":
    diagnostico()