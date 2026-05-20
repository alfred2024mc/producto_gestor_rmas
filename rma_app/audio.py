try:
    # Intentamos importar la librería nativa de Windows
    # llamada "winsound".
    #
    # Esta librería permite:
    # - reproducir pitidos
    # - emitir sonidos simples
    # - reproducir archivos WAV
    #
    # IMPORTANTE:
    # winsound SOLO existe en Windows.
    import winsound

except ImportError:
    # Si el sistema operativo NO es Windows,
    # Python lanzará:
    #
    # ImportError
    #
    # Para evitar que toda la aplicación falle,
    # guardamos None en la variable winsound.
    #
    # Más adelante verificaremos esto antes
    # de intentar reproducir sonidos.
    winsound = None


# Importamos un Enum llamado EstadoBusqueda.
#
# Probablemente contiene estados como:
#
# CON_RMA
# SIN_CONTRATO
# SIN_RMA
#
# Esto permite trabajar con estados claros
# y tipados en vez de strings sueltos.
from rma_app.models import EstadoBusqueda


class ReproductorSonidos:
    """
    Esta clase concentra toda la lógica relacionada
    con reproducción de sonidos.

    Su responsabilidad es:
    - recibir un estado
    - decidir qué sonido corresponde
    - reproducir el patrón adecuado

    Beneficios:
    - código organizado
    - reutilización
    - desacoplamiento
    - fácil mantenimiento
    """

    def reproducir_para(self, estado: EstadoBusqueda) -> None:
        """
        Método principal.

        Recibe un EstadoBusqueda y decide
        qué patrón de sonido reproducir.
        """

        # ---------------------------------------------------------
        # VALIDACIÓN DE COMPATIBILIDAD
        # ---------------------------------------------------------

        # Si winsound es None significa:
        # - no estamos en Windows
        # - la librería no existe
        #
        # Entonces salimos inmediatamente
        # sin intentar reproducir sonidos.
        #
        # Esto evita errores como:
        #
        # AttributeError:
        # 'NoneType' object has no attribute 'Beep'
        if winsound is None:
            return

        # ---------------------------------------------------------
        # CASO: RMA ENCONTRADO
        # ---------------------------------------------------------

        # Verificamos si el estado indica
        # que se encontró un RMA válido.
        if estado == EstadoBusqueda.CON_RMA:

            # Reproducimos sonido positivo/agudo.
            self._reproducir_encontrado()

            # Terminamos el método inmediatamente.
            return

        # ---------------------------------------------------------
        # CASO: SIN CONTRATO
        # ---------------------------------------------------------

        # Verificamos si la serie existe
        # pero no tiene contrato/cobertura.
        if estado == EstadoBusqueda.SIN_CONTRATO:

            # Reproducimos patrón intermedio.
            self._reproducir_sin_contrato()

            # Terminamos el método.
            return

        # ---------------------------------------------------------
        # CASO POR DEFECTO
        # ---------------------------------------------------------

        # Si no fue:
        # - CON_RMA
        # - SIN_CONTRATO
        #
        # entonces usamos sonido de:
        # - sin RMA
        # - error
        # - no encontrado
        self._reproducir_sin_rma()

    # =============================================================
    # SONIDO: RMA ENCONTRADO
    # =============================================================

    def _reproducir_encontrado(self) -> None:
        """
        Reproduce sonido de éxito.

        Usamos pitidos:
        - agudos
        - cortos
        - rápidos

        para comunicar visualmente:
        "resultado positivo".
        """

        # ---------------------------------------------------------
        # winsound.Beep(frecuencia, duracion)
        #
        # frecuencia:
        #   medida en Hertz (Hz)
        #
        # duracion:
        #   medida en milisegundos (ms)
        # ---------------------------------------------------------

        # Primer pitido agudo.
        #
        # 1800 Hz:
        # sonido bastante agudo
        #
        # 400 ms:
        # duración corta
        winsound.Beep(1800, 400)

        # Segundo pitido agudo.
        winsound.Beep(1800, 400)

    # =============================================================
    # SONIDO: SIN CONTRATO
    # =============================================================

    def _reproducir_sin_contrato(self) -> None:
        """
        Reproduce sonido intermedio.

        Este estado representa:
        - existe la serie
        - pero no tiene contrato
        - o no tiene cobertura

        Usamos pitidos medios para diferenciarlo
        del éxito y del error grave.
        """

        # Primer pitido medio.
        #
        # 1000 Hz:
        # frecuencia intermedia
        #
        # 250 ms:
        # sonido rápido
        winsound.Beep(1000, 250)

        # Segundo pitido medio.
        winsound.Beep(1000, 250)

        # Tercer pitido medio.
        winsound.Beep(1000, 250)

    # =============================================================
    # SONIDO: SIN RMA
    # =============================================================

    def _reproducir_sin_rma(self) -> None:
        """
        Reproduce sonido de error/no encontrado.

        Usamos:
        - frecuencia grave
        - duración larga

        porque psicológicamente los sonidos graves
        suelen asociarse con:
        - fallo
        - alerta
        - ausencia
        """

        # 300 Hz:
        # sonido grave
        #
        # 600 ms:
        # sonido largo
        winsound.Beep(300, 600)