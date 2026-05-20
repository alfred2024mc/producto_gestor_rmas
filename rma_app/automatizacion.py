from rma_app.correo import (
    ConstructorCorreoOutlook,
    EnviadorCorreoOutlook,
    GestorProgramacionSemanal,
)


class CoordinadorEnvioProgramado:
    # Esta clase une la programacion semanal con el envio por Outlook.

    def __init__(
        self,
        gestor_programacion: GestorProgramacionSemanal,
        constructor_correo: ConstructorCorreoOutlook,
        enviador_correo: EnviadorCorreoOutlook,
    ) -> None:
        # Guardamos las dependencias necesarias para el flujo.
        self._gestor_programacion = gestor_programacion
        self._constructor_correo = constructor_correo
        self._enviador_correo = enviador_correo

    def enviar_correo_de_hoy(self, mostrar_antes_de_enviar: bool = False) -> str:
        # Recuperamos el dia actual y su configuracion asociada.
        dia_hoy, configuracion_hoy = self._gestor_programacion.obtener_para_hoy()

        if not dia_hoy:
            raise RuntimeError("Hoy no es un dia habil para envio automatico.")

        if not configuracion_hoy:
            raise RuntimeError(f"No existe programacion guardada para {dia_hoy}.")

        # Extraemos los datos variables del dia.
        fecha_visita = str(configuracion_hoy["fecha_visita"])
        series = [str(serie) for serie in configuracion_hoy["series"]]

        # Construimos el correo y lo enviamos.
        asunto = self._constructor_correo.construir_asunto()
        html = self._constructor_correo.construir_html(dia_hoy, fecha_visita, series)
        self._enviador_correo.enviar(asunto, html, mostrar_antes_de_enviar)

        return dia_hoy
