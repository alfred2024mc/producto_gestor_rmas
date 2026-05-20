"""
Test del bot usando WhatsAppSelection que ya funciona
"""
import time
import json
from pathlib import Path
from whatsapp_conexion import WhatsAppConnection
from whatsapp_seleccion import WhatsAppSelection
from whatsapp_envio import WhatsAppSender
from WhatsAppBot import WhatsAppBot
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ARCHIVO_TEST = Path("datos") / "test_status.json"
ARCHIVO_IDS = Path("datos") / "ultimo_mensaje_id.json"

# Limpiar estado anterior
if ARCHIVO_TEST.exists():
    ARCHIVO_TEST.unlink()

def main():
    print("\n" + "=" * 60)
    print("CONECTANDO A WHATSAPP WEB...")
    print("=" * 60)

    conexion = WhatsAppConnection()
    driver = conexion.conectar()
    print("Sesion iniciada!")

    time.sleep(2)

    # Usar WhatsAppSelection que ya funciono antes
    print("Abriendo grupo 'Mis perros'...")
    selector = WhatsAppSelection(driver)
    resultado = selector.seleccionar_chat("Mis perros")

    if not resultado["exito"]:
        print(f"Error: {resultado.get('mensaje')}")
        driver.quit()
        return

    print("Grupo abierto!")
    time.sleep(1)

    # Cargar IDs ya procesados
    procesados = set()
    if ARCHIVO_IDS.exists():
        try:
            with open(ARCHIVO_IDS, "r", encoding="utf-8") as f:
                procesados = set(json.load(f))
        except:
            pass

    print(f"IDs ya procesados: {len(procesados)}")

    # Extraer mensajes via JavaScript
    def obtener_mensajes(driver):
        js_script = """
        function getMessages() {
            const results = [];
            const msgContainers = document.querySelectorAll('div[data-testid="msg-container"]');

            msgContainers.forEach((container, idx) => {
                // Determinar tipo
                const isIncoming = container.closest('[data-testid="incoming"]') !== null;
                const isOutgoing = container.closest('[data-testid="outgoing"]') !== null;

                // Extraer texto
                const textSpans = container.querySelectorAll('span');
                let texto = '';
                textSpans.forEach(span => {
                    const t = span.textContent?.trim();
                    if (t && t.length > 0 && t.length < 300) {
                        texto = t;
                    }
                });

                // Extraer hora
                let hora = '';
                const timeSpan = container.querySelector('span[data-testid="msg-time"]');
                if (timeSpan) hora = timeSpan.textContent?.trim() || '';

                if (texto) {
                    results.push({
                        tipo: isIncoming ? 'entrante' : (isOutgoing ? 'saliente' : 'unknown'),
                        texto: texto,
                        hora: hora,
                        id: `${texto.substring(0,30)}|${hora}`
                    });
                }
            });
            return results;
        }
        return getMessages();
        """
        try:
            return driver.execute_script(js_script)
        except Exception as e:
            logger.error(f"Error JS: {e}")
            return []

    sender = WhatsAppSender(driver)
    bot = WhatsAppBot()

    print("\n" + "=" * 60)
    print("ESPERANDO MENSAJE DEL INTEGRANTE...")
    print("El usuario debe enviar 'quiero 5 series' en el grupo")
    print("=" * 60)

    timeout = 120
    inicio = time.time()

    while time.time() - inicio < timeout:
        mensajes = obtener_mensajes(driver)

        for msg in mensajes:
            texto = msg.get('texto', '')
            msg_id = msg.get('id', '')
            tipo = msg.get('tipo', '')

            # Solo procesar entrantes nuevos
            if tipo == 'entrante' and texto.strip() and msg_id not in procesados:
                print(f"\n>>> MENSAJE DETECTADO: '{texto}'")

                # Procesar
                respuesta = bot.procesar_comando(texto)

                if respuesta:
                    print(f">>> RESPUESTA: {respuesta}")

                    # Enviar
                    resultado = sender.enviar_mensaje(respuesta)

                    if resultado.get("exito"):
                        print(">>> ENVIADO EXITOSAMENTE!")

                        # Verificar inventario
                        with open("datos/whatsapp_series.json", "r", encoding="utf-8") as f:
                            series = json.load(f)
                        disponibles = len([s for s in series if s.get("estado") == "disponible"])
                        print(f">>> SERIES RESTANTES: {disponibles}")

                        ARCHIVO_TEST.write_text(
                            json.dumps({"exito": True, "series_restantes": disponibles}, ensure_ascii=False),
                            encoding="utf-8"
                        )
                    else:
                        print(f">>> ERROR: {resultado.get('error')}")
                else:
                    print(f">>> Sin respuesta para: '{texto}'")

                procesados.add(msg_id)
                break

        if ARCHIVO_TEST.exists():
            break

        time.sleep(2)

    # Guardar IDs
    ARCHIVO_IDS.parent.mkdir(exist_ok=True)
    with open(ARCHIVO_IDS, "w", encoding="utf-8") as f:
        json.dump(list(procesados)[-200:], f, ensure_ascii=False)

    if ARCHIVO_TEST.exists():
        print("\n" + "=" * 60)
        print("TEST COMPLETADO!")
        print("=" * 60)
    else:
        print("\nTimeout - No se detecto mensaje")

    time.sleep(5)
    driver.quit()

if __name__ == "__main__":
    main()