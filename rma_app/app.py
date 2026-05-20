import tkinter as tk

from rma_app.automatizacion import CoordinadorEnvioProgramado
from rma_app.audio import ReproductorSonidos
from rma_app.config import ConfiguracionApp
from rma_app.correo import (
    CoordinadorEnviosPersonalizados,
    ConstructorCorreoOutlook,
    EnviadorCorreoOutlook,
    GestorEnviosPersonalizados,
    GestorProgramacionSemanal,
    RepositorioEnviosPersonalizados,
    RepositorioProgramacionCorreos,
)


from rma_app.services import (
    FuenteDatosExcel,
    GeneradorVaciadoRma,
    GestorRmasSemanales,
    ServicioBusquedaRma,
    ServicioCargaExcel,
)
from rma_app.ui import VentanaPrincipal


class AplicacionEscanerRma:
    """Clase principal que arma y conecta todas las piezas del sistema."""

    def __init__(self) -> None:
        # Configuración base del sistema
        configuracion = ConfiguracionApp()

        # Fuente de datos y servicios principales
        fuente_datos = FuenteDatosExcel(configuracion)
        servicio_busqueda = ServicioBusquedaRma(configuracion)
        servicio_carga = ServicioCargaExcel(fuente_datos, servicio_busqueda)

        # Componentes auxiliares
        reproductor_sonidos = ReproductorSonidos()
        gestor_rmas = GestorRmasSemanales()
        generador_vaciado = GeneradorVaciadoRma(configuracion, servicio_busqueda)

        # Programación y envío de correos
        repositorio_programacion = RepositorioProgramacionCorreos(
            configuracion.ruta_programacion_correos
        )
        repositorio_envios_personalizados = RepositorioEnviosPersonalizados(
            configuracion.ruta_envios_personalizados
        )
        gestor_programacion = GestorProgramacionSemanal(repositorio_programacion)
        gestor_envios_personalizados = GestorEnviosPersonalizados(
            repositorio_envios_personalizados
        )
        constructor_correo = ConstructorCorreoOutlook(configuracion)
        enviador_correo = EnviadorCorreoOutlook(configuracion)

        coordinador_envio = CoordinadorEnvioProgramado(
            gestor_programacion,
            constructor_correo,
            enviador_correo,
        )
        coordinador_envios_personalizados = CoordinadorEnviosPersonalizados(
            gestor_envios_personalizados,
            constructor_correo,
            enviador_correo,
        )

        

        # Ventana raíz de Tkinter
        self._raiz = tk.Tk()

        # Ventana principal
        self._ventana = VentanaPrincipal(
            raiz=self._raiz,
            servicio_carga=servicio_carga,
            servicio_busqueda=servicio_busqueda,
            reproductor_sonidos=reproductor_sonidos,
            gestor_rmas=gestor_rmas,
            generador_vaciado=generador_vaciado,
            gestor_programacion=gestor_programacion,
            coordinador_envio=coordinador_envio,
            gestor_envios_personalizados=gestor_envios_personalizados,
            coordinador_envios_personalizados=coordinador_envios_personalizados,
        )

    def ejecutar(self) -> None:
        """Inicia el ciclo principal de la interfaz gráfica."""
        self._raiz.mainloop()
        