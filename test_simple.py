"""
Monitor simple - NO usa perfil de Chrome para evitar problemas.
El usuario debe tener WhatsApp Web ya abierto.
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
    # SIN perfil para evitar conflictos

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opciones)

    # Ir directamente a WhatsApp Web
    print("Abriendo WhatsApp Web...")
    driver.get("https://web.whatsapp.com")

    print("\n" + "=" * 60)
    print("INSTRUCCIONES:")
    print("1. Si WhatsApp te pide escanear QR, hazlo")
    print("2. Navega manualmente al grupo 'Mis perros'")
    print("3. Presiona ENTER aqui cuando estes en el grupo")
    print("=" * 60)
    input()

    time.sleep(2)

    # Ahora estamos en el grupo
    print("Grupo abierto. Monitoreando mensajes...")

    from whatsapp_mensajes import WhatsAppMessages
    from whatsapp_envio import WhatsAppSender
    from WhatsAppBot import WhatsAppBot

    messages = WhatsAppMessages(driver)
    sender = WhatsAppSender(driver)
    bot = WhatsAppBot()

    # Cargar IDs ya procesados
    ids_file = Path("datos/ultimo_mensaje_id.json")
    ids_procesados = set()
    if ids_file.exists():
        try:
            with open(ids_file, "r", encoding="utf-8") as f:
                ids_procesados = set(json.load(f))
        except:
            pass

    print(f"IDs ya procesados: {len(ids_procesados)}")

    timeout = 120
    inicio = time.time()
    encontrado = False

    while time.time() - inicio < timeout:
        try:
            msgs = messages.obtener_mensajes(limite=50)

            for msg in msgs:
                texto = msg.get("texto", "")
                tipo = msg.get("tipo", "")
                hora = msg.get("hora", "")
                msg_id = msg.get("id", "") or f"{texto[:30]}|{hora}"

                if msg_id in ids_procesados:
                    continue

                if tipo == "entrante" and texto.strip():
                    print(f"\n>>> MENSAJE: [{tipo}] {hora}: {texto[:80]}")

                    # Procesar comando
                    respuesta = bot.procesar_comando(texto)

                    if respuesta:
                        print(f">>> RESPONDIENDO: {respuesta[:60]}...")

                        resultado = sender.enviar_mensaje(respuesta)

                        if resultado.get("exito"):
                            print(">>> ENVIADO!")

                            # Series restantes
                            with open("datos/whatsapp_series.json", "r", encoding="utf-8") as f:
                                series = json.load(f)
                            disponibles = len([s for s in series if s.get("estado") == "disponible"])
                            print(f">>> SERIES RESTANTES: {disponibles}")
                            encontrado = True
                        else:
                            print(f">>> ERROR: {resultado.get('error')}")

                    ids_procesados.add(msg_id)

            # Guardar IDs
            if ids_procesados:
                ids_file.parent.mkdir(exist_ok=True)
                with open(ids_file, "w", encoding="utf-8") as f:
                    json.dump(list(ids_procesados)[-200:], f, ensure_ascii=False)

            if encontrado:
                break

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(2)

    if encontrado:
        print("\n" + "=" * 60)
        print("TEST EXITOSO!")
        print("=" * 60)
    else:
        print("\nTimeout - No se encontro 'quiero N series'")

    print("\nCerrando en 5 segundos...")
    time.sleep(5)
    driver.quit()

if __name__ == "__main__":
    main()