"""
Investigacion directa de la estructura de WhatsApp Web
"""
import time
import json
from pathlib import Path
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
    print("Esperando sesion...")

    wait = WebDriverWait(driver, 120)
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, '//div[@id="side"]')))
        print("Sesion iniciada!")
    except Exception:
        print("Timeout")
        driver.quit()
        return

    time.sleep(2)

    # Abrir grupo
    print("Abriendo grupo 'Mis perros'...")
    try:
        search = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="chat-list-search"] input')))
        search.click()
        time.sleep(0.5)
        search.send_keys("Mis perros")
        time.sleep(2)
        resultado = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[@title="Mis perros"]')))
        resultado.click()
        print("Grupo abierto!")
    except Exception as e:
        print(f"Error: {e}")
        driver.quit()
        return

    print("\n" + "=" * 60)
    print("ENVIA 'quiero 5 series' EN EL GRUPO Y PRESIONA ENTER")
    print("=" * 60)
    input()

    time.sleep(2)

    print("\nINVESTIGANDO ESTRUCTURA...\n")

    # 1. Verificar que estamos en el area correcta
    js_ubicacion = """
    // Buscar donde esta el area de chat
    const main = document.querySelector('#main');
    const chatArea = document.querySelector('div[role="log"]');
    const messages = document.querySelector('div[data-testid="message-list"]');

    return {
        main_exists: !!main,
        log_exists: !!chatArea,
        messages_exists: !!messages,
        main_classes: main?.className?.substring(0, 100),
        log_classes: chatArea?.className?.substring(0, 100),
        messages_classes: messages?.className?.substring(0, 100)
    };
    """
    ubicacion = driver.execute_script(js_ubicacion)
    print(f"Ubicacion: {json.dumps(ubicacion, indent=2)}")

    # 2. Buscar TODOS los data-testid que contengan "msg"
    js_testids = """
    const results = [];
    document.querySelectorAll('*').forEach(el => {
        const dt = el.getAttribute('data-testid') || '';
        if (dt.includes('msg') || dt.includes('incoming') || dt.includes('outgoing')) {
            results.push(dt);
        }
    });
    return [...new Set(results)];
    """
    testids = driver.execute_script(js_testids)
    print(f"\nData-testids encontrados: {testids}")

    # 3. Buscar clases que contengan "message"
    js_clases = """
    const results = [];
    document.querySelectorAll('*').forEach(el => {
        const cls = el.className || '';
        if (typeof cls === 'string' && (cls.includes('message') || cls.includes('bubble') ||
            cls.includes('incoming') || cls.includes('outgoing') ||
            cls.includes('copyable') || cls.includes('selectable'))) {
            results.push(cls.substring(0, 80));
        }
    });
    return [...new Set(results)];
    """
    clases = driver.execute_script(js_clases)
    print(f"\nClases relacionadas: {clases[:20]}")

    # 4. Extraer todos los textos visibles
    js_textos = """
    const results = [];
    // Buscar en todo el documento
    document.querySelectorAll('span, div').forEach(el => {
        const text = el.textContent?.trim();
        const parent = el.parentElement;
        const grandparent = parent?.parentElement;

        // Solo textos en elementos que parecen ser mensajes
        if (text && text.length > 3 && text.length < 300) {
            const parentClass = parent?.className || '';
            const gpClass = grandparent?.className || '';

            if (typeof parentClass === 'string' && typeof gpClass === 'string' &&
                (parentClass.includes('message') || parentClass.includes('incoming') ||
                 parentClass.includes('outgoing') || parentClass.includes('bubble') ||
                 gpClass.includes('message') || gpClass.includes('incoming'))) {
                results.push({
                    text: text,
                    parentClass: parentClass.substring(0, 60),
                    gpClass: gpClass.substring(0, 60)
                });
            }
        }
    });
    return results.slice(-30);
    """
    textos = driver.execute_script(js_textos)
    print(f"\nTextos encontrados ({len(textos)}):")
    for t in textos:
        print(f"  [{t['parentClass'][:30]}] {t['text'][:80]}")

    # 5. Intentar diferentes selectores
    print("\n" + "=" * 60)
    print("PROBANDO SELECTORES:")
    print("=" * 60)

    selectores = [
        'div[data-testid="msg-container"]',
        'div[data-testid="incoming"]',
        'div[data-testid="outgoing"]',
        'div[data-testid="message-list"]',
        '[data-testid*="msg"]',
        '[data-testid*="incoming"]',
        '[data-testid*="outgoing"]',
    ]

    for sel in selectores:
        try:
            elementos = driver.find_elements(By.CSS_SELECTOR, sel)
            print(f"  {sel}: {len(elementos)} elementos")
        except Exception as e:
            print(f"  {sel}: error")

    input("\nPresiona Enter para cerrar...")
    driver.quit()

if __name__ == "__main__":
    main()