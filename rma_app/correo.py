import json
from datetime import datetime
from pathlib import Path

from rma_app.config import ConfiguracionApp

try:
    import win32com.client  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - depende del entorno local
    win32com = None


class RepositorioProgramacionCorreos:
    # Esta clase guarda y recupera la programacion semanal desde un archivo JSON.

    def __init__(self, ruta_archivo: Path) -> None:
        # Guardamos la ruta donde vivira el archivo de datos.
        self._ruta_archivo = ruta_archivo

    def cargar(self) -> dict[str, dict[str, str | list[str]]]:
        # Si el archivo no existe, devolvemos una estructura vacia.
        if not self._ruta_archivo.exists():
            return {}

        # Leemos el contenido JSON y lo convertimos a diccionario.
        return json.loads(self._ruta_archivo.read_text(encoding="utf-8"))

    def guardar(self, datos: dict[str, dict[str, str | list[str]]]) -> None:
        # Creamos la carpeta contenedora si aun no existe.
        self._ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        # Guardamos el JSON con formato legible.
        self._ruta_archivo.write_text(
            json.dumps(datos, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )


class RepositorioEnviosPersonalizados:
    # Esta clase guarda y recupera correos programados puntuales.

    def __init__(self, ruta_archivo: Path) -> None:
        # Guardamos la ruta donde vivira el archivo de datos.
        self._ruta_archivo = ruta_archivo

    def cargar(self) -> list[dict[str, str | bool]]:
        # Si el archivo no existe, devolvemos una lista vacia.
        if not self._ruta_archivo.exists():
            return []

        # Leemos el contenido JSON y lo convertimos a lista.
        return json.loads(self._ruta_archivo.read_text(encoding="utf-8"))

    def guardar(self, datos: list[dict[str, str | bool]]) -> None:
        # Creamos la carpeta contenedora si aun no existe.
        self._ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        # Guardamos el JSON con formato legible.
        self._ruta_archivo.write_text(
            json.dumps(datos, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )


class GestorProgramacionSemanal:
    # Esta clase administra la informacion semanal para el correo automatico.

    DIAS_HABILES = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes"]
    DIAS_PYTHON = {
        0: "Lunes",
        1: "Martes",
        2: "Miercoles",
        3: "Jueves",
        4: "Viernes",
    }

    def __init__(self, repositorio: RepositorioProgramacionCorreos) -> None:
        # Guardamos el repositorio que persiste la informacion.
        self._repositorio = repositorio

    def guardar_dia(self, dia: str, fecha_visita: str, series: list[str]) -> None:
        # Validamos que el dia sea uno de los habilitados.
        if dia not in self.DIAS_HABILES:
            raise ValueError("El dia seleccionado no es valido.")

        # Limpiamos las series vacias antes de guardar.
        series_limpias = [serie.strip().upper() for serie in series if serie.strip()]
        if not series_limpias:
            raise ValueError("Debes capturar al menos una serie.")

        if not fecha_visita.strip():
            raise ValueError("Debes capturar la fecha y hora de visita.")

        # Cargamos la informacion actual y actualizamos solo el dia indicado.
        programacion = self._repositorio.cargar()
        programacion[dia] = {
            "fecha_visita": fecha_visita.strip(),
            "series": series_limpias,
            "actualizado_en": datetime.now().strftime("%d/%m/%Y %I:%M %p"),
        }
        self._repositorio.guardar(programacion)

    def obtener_todo(self) -> dict[str, dict[str, str | list[str]]]:
        # Regresamos toda la programacion semanal.
        return self._repositorio.cargar()

    def obtener_dia(self, dia: str) -> dict[str, str | list[str]] | None:
        # Regresamos solo la configuracion del dia solicitado.
        return self._repositorio.cargar().get(dia)

    def obtener_para_hoy(self) -> tuple[str, dict[str, str | list[str]] | None]:
        # Calculamos el dia actual y lo regresamos junto con su configuracion.
        dia_hoy = self.DIAS_PYTHON.get(datetime.now().weekday(), "")
        if not dia_hoy:
            return "", None
        return dia_hoy, self.obtener_dia(dia_hoy)


class GestorEnviosPersonalizados:
    # Esta clase administra correos puntuales con fecha y hora exacta.

    FORMATO_FECHA = "%d/%m/%Y %H:%M"
    FORMATO_SOLO_FECHA = "%d/%m/%Y"
    FORMATO_SOLO_HORA = "%H:%M"

    def __init__(self, repositorio: RepositorioEnviosPersonalizados) -> None:
        # Guardamos el repositorio que persiste la informacion.
        self._repositorio = repositorio

    def guardar_envio(
        self,
        para: str,
        cc: str,
        asunto: str,
        mensaje: str,
        fecha_programada: str,
        hora_programada: str,
    ) -> dict[str, str | bool]:
        # Validamos y limpiamos todos los campos del formulario.
        para_limpio = self._limpiar_lista_correos(para, requerido=True)
        cc_limpio = self._limpiar_lista_correos(cc, requerido=False)
        asunto_limpio = asunto.strip()
        mensaje_limpio = mensaje.strip()
        fecha_limpia = fecha_programada.strip()
        hora_limpia = hora_programada.strip()

        if not asunto_limpio:
            raise ValueError("Debes capturar el asunto del correo.")

        if not mensaje_limpio:
            raise ValueError("Debes capturar el mensaje del correo.")

        fecha_objetivo = self._parsear_fecha_hora(fecha_limpia, hora_limpia)
        if fecha_objetivo <= datetime.now():
            raise ValueError("La fecha programada debe ser posterior a la hora actual.")

        nuevo_envio = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "para": para_limpio,
            "cc": cc_limpio,
            "asunto": asunto_limpio,
            "mensaje": mensaje_limpio,
            "fecha_programada": fecha_objetivo.strftime(self.FORMATO_FECHA),
            "creado_en": datetime.now().strftime("%d/%m/%Y %I:%M %p"),
            "enviado": False,
            "enviado_en": "",
        }

        envios = self._repositorio.cargar()
        envios.append(nuevo_envio)
        self._repositorio.guardar(envios)
        return nuevo_envio

    def obtener_todos(self) -> list[dict[str, str | bool]]:
        # Regresamos todos los correos puntuales ordenados por fecha.
        return sorted(
            self._repositorio.cargar(),
            key=lambda envio: datetime.strptime(
                str(envio["fecha_programada"]),
                self.FORMATO_FECHA,
            ),
        )

    def obtener_pendientes(self, referencia: datetime | None = None) -> list[dict[str, str | bool]]:
        # Regresamos solo correos ya vencidos y aun no enviados.
        momento = referencia or datetime.now()
        pendientes: list[dict[str, str | bool]] = []
        for envio in self._repositorio.cargar():
            if bool(envio.get("enviado")):
                continue
            fecha_programada = datetime.strptime(
                str(envio["fecha_programada"]),
                self.FORMATO_FECHA,
            )
            if fecha_programada <= momento:
                pendientes.append(envio)
        return pendientes

    def marcar_como_enviado(self, identificador: str, enviado_en: datetime | None = None) -> None:
        # Marcamos como enviado el correo puntual indicado.
        momento = enviado_en or datetime.now()
        envios = self._repositorio.cargar()
        for envio in envios:
            if str(envio.get("id")) != identificador:
                continue
            envio["enviado"] = True
            envio["enviado_en"] = momento.strftime("%d/%m/%Y %I:%M %p")
            break
        self._repositorio.guardar(envios)

    def _limpiar_lista_correos(self, valor: str, requerido: bool) -> str:
        # Normalizamos varios correos separados por punto y coma.
        correos = [correo.strip() for correo in valor.split(";") if correo.strip()]
        if requerido and not correos:
            raise ValueError("Debes capturar al menos un correo destino.")
        for correo in correos:
            if "@" not in correo:
                raise ValueError(f"Correo invalido: {correo}")
        return ";".join(correos)

    def _parsear_fecha_hora(self, fecha_texto: str, hora_texto: str) -> datetime:
        # Convertimos la fecha y hora del formulario a un objeto fecha.
        if not fecha_texto:
            raise ValueError("Debes capturar la fecha programada.")

        if not hora_texto:
            raise ValueError("Debes capturar la hora programada.")

        try:
            datetime.strptime(fecha_texto, self.FORMATO_SOLO_FECHA)
        except ValueError as error:
            raise ValueError(
                "La fecha debe ir con formato DD/MM/AAAA. Ejemplo: 15/03/2026."
            ) from error

        try:
            datetime.strptime(hora_texto, self.FORMATO_SOLO_HORA)
        except ValueError as error:
            raise ValueError(
                "La hora debe ir con formato HH:MM en 24 horas. Ejemplo: 09:30 o 18:45."
            ) from error

        return datetime.strptime(
            f"{fecha_texto} {hora_texto}",
            self.FORMATO_FECHA,
        )


class ConstructorCorreoOutlook:
    # Esta clase transforma la programacion del dia en el HTML del correo.

    def __init__(self, configuracion: ConfiguracionApp) -> None:
        # Guardamos toda la configuracion fija del formato de correo.
        self._configuracion = configuracion

    def construir_asunto(self) -> str:
        # Regresamos el asunto fijo definido en configuracion.
        return self._configuracion.asunto_correo

    def construir_html(
        self,
        dia: str,
        fecha_visita: str,
        series: list[str],
    ) -> str:
        # Convertimos las series a filas HTML de tabla.
        filas_series = "".join(
            (
                "<tr>"
                f"<td style='padding:6px;border:1px solid #c8d5e1;'>{self._configuracion.modelo_equipo}</td>"
                f"<td style='padding:6px;border:1px solid #c8d5e1;'>{serie}</td>"
                "</tr>"
            )
            for serie in series
        )

        # Construimos el cuerpo completo con formato HTML para Outlook.
        return f"""
        <html>
        <body style="font-family:Segoe UI, Arial, sans-serif; font-size:11pt; color:#16324a;">
            {self._configuracion.texto_inicial_correo}
            <table style="border-collapse:collapse; width:100%; max-width:750px; margin-bottom:16px;">
                <tr>
                    <td colspan="2" style="background:#123b5d;color:white;padding:8px;font-weight:bold;">
                        SOLICITUD DE REFACCION
                    </td>
                </tr>
                <tr>
                    <td style="padding:6px;border:1px solid #c8d5e1;font-weight:bold;">CLIENTE RA</td>
                    <td style="padding:6px;border:1px solid #c8d5e1;">{self._configuracion.cliente_ra}</td>
                </tr>
                <tr>
                    <td style="padding:6px;border:1px solid #c8d5e1;font-weight:bold;">SITE ID</td>
                    <td style="padding:6px;border:1px solid #c8d5e1;">{self._configuracion.site_id}</td>
                </tr>
                <tr>
                    <td colspan="2" style="padding:8px;border:1px solid #c8d5e1;font-weight:bold;background:#eef3f8;">
                        DATOS DEL EQUIPO - {dia}
                    </td>
                </tr>
                <tr>
                    <td style="padding:6px;border:1px solid #c8d5e1;font-weight:bold;background:#f8fbfd;">Marca / Modelo</td>
                    <td style="padding:6px;border:1px solid #c8d5e1;font-weight:bold;background:#f8fbfd;">Numero de serie</td>
                </tr>
                {filas_series}
                <tr>
                    <td style="padding:6px;border:1px solid #c8d5e1;font-weight:bold;">REFACCIONES REQUERIDAS</td>
                    <td style="padding:6px;border:1px solid #c8d5e1;">{self._configuracion.refacciones_requeridas}</td>
                </tr>
                <tr>
                    <td style="padding:6px;border:1px solid #c8d5e1;font-weight:bold;">TROUBLESHOOTING</td>
                    <td style="padding:6px;border:1px solid #c8d5e1;">{self._configuracion.troubleshooting}</td>
                </tr>
                <tr>
                    <td style="padding:6px;border:1px solid #c8d5e1;font-weight:bold;">DIA Y HORA DE VISITA</td>
                    <td style="padding:6px;border:1px solid #c8d5e1;">{fecha_visita}</td>
                </tr>
                <tr>
                    <td style="padding:6px;border:1px solid #c8d5e1;font-weight:bold;">DIRECCION</td>
                    <td style="padding:6px;border:1px solid #c8d5e1;">{self._configuracion.direccion}</td>
                </tr>
                <tr>
                    <td style="padding:6px;border:1px solid #c8d5e1;font-weight:bold;">CONTACTO</td>
                    <td style="padding:6px;border:1px solid #c8d5e1;">{self._configuracion.contacto}</td>
                </tr>
            </table>
            {self._configuracion.firma_correo}
        </body>
        </html>
        """

    def construir_html_libre(self, mensaje: str) -> str:
        # Convertimos saltos de linea en HTML para un correo libre.
        mensaje_html = "<br>".join(linea.strip() for linea in mensaje.strip().splitlines())
        return (
            "<html>"
            "<body style=\"font-family:Segoe UI, Arial, sans-serif; font-size:11pt; color:#16324a;\">"
            f"{mensaje_html}"
            "</body>"
            "</html>"
        )


class EnviadorCorreoOutlook:
    # Esta clase crea y envia el correo usando Outlook de escritorio.

    def __init__(self, configuracion: ConfiguracionApp) -> None:
        # Guardamos la configuracion fija de destinatarios.
        self._configuracion = configuracion

    def enviar(
        self,
        asunto: str,
        html: str,
        mostrar_antes_de_enviar: bool,
        para: str | None = None,
        cc: str | None = None,
    ) -> None:
        # Validamos que la libreria de Outlook este disponible.
        if win32com is None:
            raise RuntimeError(
                "No se encontro win32com. Instala pywin32 para usar Outlook con Python."
            )

        # Creamos la instancia de Outlook y un correo nuevo.
        outlook = win32com.client.Dispatch("Outlook.Application")
        correo = outlook.CreateItem(0)
        if para is None:
            correo.To = self._configuracion.correo_para
        else:
            correo.To = para

        if cc is None:
            correo.CC = self._configuracion.correos_cc
        else:
            correo.CC = cc
        correo.Subject = asunto
        correo.HTMLBody = html

        # Si se desea revisar antes, solo lo mostramos.
        if mostrar_antes_de_enviar:
            correo.Display()
            return

        # Si no, lo enviamos directamente.
        correo.Send()


class CoordinadorEnviosPersonalizados:
    # Esta clase procesa correos puntuales programados por fecha exacta.

    def __init__(
        self,
        gestor_envios: GestorEnviosPersonalizados,
        constructor_correo: ConstructorCorreoOutlook,
        enviador_correo: EnviadorCorreoOutlook,
    ) -> None:
        # Guardamos las dependencias necesarias para el flujo.
        self._gestor_envios = gestor_envios
        self._constructor_correo = constructor_correo
        self._enviador_correo = enviador_correo

    def enviar_pendientes(self, mostrar_antes_de_enviar: bool = False) -> int:
        # Buscamos todos los correos puntuales que ya deben salir.
        pendientes = self._gestor_envios.obtener_pendientes()
        enviados = 0

        for envio in pendientes:
            html = self._constructor_correo.construir_html_libre(str(envio["mensaje"]))
            self._enviador_correo.enviar(
                asunto=str(envio["asunto"]),
                html=html,
                mostrar_antes_de_enviar=mostrar_antes_de_enviar,
                para=str(envio["para"]),
                cc=str(envio["cc"]),
            )
            if not mostrar_antes_de_enviar:
                self._gestor_envios.marcar_como_enviado(str(envio["id"]))
            enviados += 1

        return enviados
