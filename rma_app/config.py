from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConfiguracionApp:
    # ===== EXCEL =====
    ruta_excel: Path = Path(r"C:\Users\alfmo\Downloads\IDENTIFICAR_SERIES.xlsx")
    nombre_hoja: str = "Hoja1"
    columna_serie: str = "SERIE"
    columna_rma: str = "RMA"
    columna_numero: str = "#"

    # ===== ARCHIVOS LOCALES =====
    ruta_programacion_correos: Path = Path("datos/programacion_correos.json")
    ruta_envios_personalizados: Path = Path("datos/envios_personalizados.json")

    # ===== CORREO =====
    correo_para: str = "SERV-CAMPO@uninet.com.mx"
    correos_cc: str = (
        "amnunez@teledinamica.com.mx;"
        "coordinacion_sat@teledinamica.com.mx;"
        "CVCASTRO@uninet.com.mx"
    )
    asunto_correo: str = "SOLICITUD DE REFACCION ALMACEN TELEDINAMICA CLIENTE SAT"
    texto_inicial_correo: str = (
        "Buen dia,<br><br>"
        "De su apoyo con el tramite y envio de las siguientes refacciones:<br><br>"
        "<b>Favor de proporcionar el RMA y ETA para su debido control.</b><br><br>"
    )

    # ===== DATOS FIJOS DEL FORMATO =====
    google_rma_recibe: str = "N/D"
    cliente_ra: str = "SAT"
    site_id: str = "70104640 // ALMACEN TELEDINAMICA"
    modelo_equipo: str = "CISCO-7821"
    refacciones_requeridas: str = "N/A"
    troubleshooting: str = "N/A"
    direccion: str = (
        "Francisco Villa Manzana #45 Lote #17 Colonia Quiahuatla Tlahuac CDMX <br><br>"
        "Codigo Postal: 13090<br><br>"
        "https://maps.app.goo.gl/6GXb8K7gbNGzHgzF8"
    )
    contacto: str = (
        "Alfredo Cruz: 5567589571<br><br>"
        "Arturo Rivas: 5542888047"
    )
    firma_correo: str = (
        "Gracias,<br><br>"
        "Alfredo Cruz<br>"
        "Almacen Teledinamica - Telmex<br>"
        "Teledinamica Mexico"
    )

    