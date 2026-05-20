"""
Debug mejorado para ver qué mensajes detecta el sistema.
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
    print("ESCANEA EL QR SI ES NECESARIO")
    print("Esperando que cargue completamente...")
    print("=" * 60)

    # Esperar a que cargue la barra lateral
    wait = WebDriverWait(driver, 120)
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, '//div[@id="side"]')))
        print("\nSesion iniciada! Sidebar cargada.")
    except Exception:
        print("Timeout esperando sidebar.")
        driver.quit()
        return

    time.sleep(2)

    # Buscar y abrir el grupo "Mis perros"
    print("\nAbriendo grupo 'Mis perros'...")

    # Intentar varios selectores para el search box
    search_selectors = [
        'div[title="Buscar o empezar un chat nuevo"]',
        'div[data-testid="chat-list-search"]',
        '#side input[title*="Buscar"]',
        'input[placeholder*="Buscar"]',
    ]

    search = None
    for selector in search_selectors:
        try:
            search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            print(f"Search box encontrado con: {selector}")
            search.click()
            time.sleep(0.5)
            search.send_keys("Mis perros")
            time.sleep(2)
            break
        except Exception:
            continue

    if not search:
        print("No se encontro search box")
        driver.quit()
        return

    # Esperar que aparezcan resultados y clickear
    try:
        resultado = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[@title="Mis perros"]')))
        resultado.click()
        print("Grupo 'Mis perros' abierto!")
    except Exception:
        print("No se pudo abrir el grupo")
        driver.quit()
        return

    time.sleep(2)

    print("\n" + "=" * 60)
    print("AHORA ENVIA UN MENSAJE EN EL GRUPO")
    print("Escribe 'quiero 5 series' y presiona Enter aqui")
    print("=" * 60)
    input("Presiona Enter cuando hayas enviado el mensaje...")

    print("\nCapturando mensajes...\n")

    # Intentar varios métodos para capturar mensajes
    metodos = [
        ("msg-text span", '//div[@data-testid="msg-text"]//span'),
        ("selectable-text", '//span[contains(@class, "selectable-text")]'),
        ("copyable-text", '//span[contains(@class, "copyable-text")]'),
        ("tail", '//div[contains(@class, "tail")]'),
        ("bubble", '//div[contains(@class, "bubble")]'),
    ]

    for nombre, xpath in metodos:
        try:
            elementos = driver.find_elements(By.XPATH, xpath)
            textos = [e.text.strip() for e in elementos if e.text.strip() and len(e.text.strip()) > 2]
            if textos:
                print(f"\n[{nombre}] ({len(textos)} encontrados):")
                for t in textos[-15:]:
                    print(f"  - {t[:80]}")
        except Exception as e:
            print(f"\n[{nombre}] Error: {e}")

    # JavaScript para extraer mensajes
    print("\n[JavaScript] Extrayendo todos los mensajes:")
    js_script = """
    const msgs = [];
    // Buscar todos los divs que contengan texto en spans
    document.querySelectorAll('div[aria-label="Mensajes"], div[aria-label="Messages"]').forEach(container => {
        container.querySelectorAll('span').forEach(span => {
            const text = span.textContent.trim();
            if (text && text.length > 1 && text.length < 500) {
                msgs.push(text);
            }
        });
    });
    return msgs;
    """
    try:
        mensajes = driver.execute_script(js_script)
        if mensajes:
            print(f"Encontrados {len(mensajes)} mensajes")
            for m in mensajes[-10:]:
                print(f"  - {m[:80]}")
    except Exception as e:
        print(f"Error JS: {e}")

    # Intentar con clase _11JEv u otras
    print("\n[Estructura HTML] Explorando...")
    js_estructura = """
    // Buscar elementos en el area de chat
    const chatArea = document.querySelector('div[role="log"]') || document.querySelector('main') || document.querySelector('#main');
    if (!chatArea) return [];

    const results = [];
    const elementos = chatArea.querySelectorAll('*');
    elementos.forEach(el => {
        const text = el.textContent?.trim();
        const className = el.className || '';
        const dataTestid = el.getAttribute('data-testid') || '';

        if (text && text.length > 2 && text.length < 200 &&
            (className.includes('copyable') || className.includes('selectable') ||
             className.includes('message') || className.includes('bubble') ||
             className.includes('tail') || dataTestid.includes('msg-'))) {
            results.push({
                class: className.substring(0, 50),
                testid: dataTestid,
                text: text.substring(0, 100)
            });
        }
    });
    return results.slice(-20);
    """
    try:
        estructura = driver.execute_script(js_estructura)
        if estructura:
            print(f"Encontrados {len(estructura)} elementos:")
            for e in estructura[:10]:
                print(f"  [{e['testid']}] [{e['class']}] {e['text']}")
    except Exception as e:
        print(f"Error estructura: {e}")

    print("\n" + "=" * 60)
    input("Presiona Enter para cerrar...")
    driver.quit()

if __name__ == "__main__":
    main()