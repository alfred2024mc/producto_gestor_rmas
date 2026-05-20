"""
Test directo - abre grupo y extrae mensajes usando metodo conocido.
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

PERFIL = Path("datos/chrome_perfil")

def main():
    opciones = Options()
    for arg in CHROME_ARGS:
        opciones.add_argument(arg)
    opciones.add_argument(f"--user-data-dir={PERFIL.absolute()}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opciones)

    driver.get("https://web.whatsapp.com")
    print("Esperando sesion...")

    wait = WebDriverWait(driver, 60)
    try:
        wait.until(EC.presence_of_element_located((By.ID, "side")))
        print("Sesion lista!")
    except:
        print("Timeout. Intenta de nuevo.")
        driver.quit()
        return

    time.sleep(2)

    # Usar WhatsAppSelection que funciona
    print("Abriendo grupo 'Mis perros'...")
    from whatsapp_seleccion import WhatsAppSelection
    selector = WhatsAppSelection(driver)
    resultado = selector.seleccionar_chat("Mis perros")

    if not resultado["exito"]:
        print(f"Error: {resultado}")
        driver.quit()
        return

    print("Grupo abierto!")

    print("\n" + "=" * 60)
    print("ENVIA 'quiero 5 series' EN EL GRUPO AHORA")
    print("El script leera el mensaje y enviara la respuesta")
    print("=" * 60)

    # Esperar a que el usuario envie el mensaje
    time.sleep(3)

    # Extraer mensajes usando WhatsAppMessages
    from whatsapp_mensajes import WhatsAppMessages
    from whatsapp_envio import WhatsAppSender
    from WhatsAppBot import WhatsAppBot

    messages = WhatsAppMessages(driver)
    sender = WhatsAppSender(driver)
    bot = WhatsAppBot()

    # Escanear mensajes hasta encontrar uno nuevo
    ultimo_texto = ""
    encontrado = False

    for intento in range(20):
        print(f"\nIntento {intento + 1}/20 - Buscando mensaje...")

        msgs = messages.obtener_mensajes(limite=30)
        print(f"Mensajes capturados: {len(msgs)}")

        for msg in msgs:
            texto = msg.get("texto", "")
            tipo = msg.get("tipo", "")
            hora = msg.get("hora", "")

            if texto and len(texto) > 2:
                print(f"  [{tipo}] {hora}: {texto[:60]}")

                # Detectar "quiero N series"
                if tipo == "entrante" and "quiero" in texto.lower() and "series" in texto.lower():
                    print(f"\n*** MENSAJE ENCONTRADO: '{texto}' ***")

                    # Procesar
                    respuesta = bot.procesar_comando(texto)

                    if respuesta:
                        print(f"Respuesta: {respuesta}")

                        # Enviar
                        print("Enviando respuesta...")
                        resultado = sender.enviar_mensaje(respuesta)

                        if resultado.get("exito"):
                            print("*** RESPUESTA ENVIADA EXITOSAMENTE ***")

                            # Verificar series
                            with open("datos/whatsapp_series.json", "r", encoding="utf-8") as f:
                                series = json.load(f)
                            disponibles = len([s for s in series if s.get("estado") == "disponible"])
                            print(f"*** SERIES RESTANTES: {disponibles} ***")
                        else:
                            print(f"Error enviando: {resultado}")
                    else:
                        print("El bot no genero respuesta para este mensaje")

                    encontrado = True
                    break

        if encontrado:
            break

        time.sleep(2)

    if not encontrado:
        print("\nNo se detecto el mensaje. Revisa la lista de mensajes arriba.")

    input("\nPresiona Enter para cerrar...")
    driver.quit()

if __name__ == "__main__":
    main()