
import tkinter as tk
from calendar import month_name, monthcalendar
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from rma_app.automatizacion import CoordinadorEnvioProgramado
from rma_app.audio import ReproductorSonidos
from rma_app.correo import CoordinadorEnviosPersonalizados, GestorEnviosPersonalizados, GestorProgramacionSemanal
from rma_app.models import EstadoBusqueda, ResultadoBusqueda
from rma_app.services import (
    GeneradorVaciadoRma,
    GestorRmasSemanales,
    ServicioBusquedaRma,
    ServicioCargaExcel,
)


class SelectorFechaHoraVisita:
    # Selector encapsulado con calendario emergente y hora dentro del mismo cuadro.

    FORMATOS_ENTRADA = (
        "%d/%m/%Y %I:%M %p",
        "%d/%m/%y %I:%M %p",
        "%d/%m/%Y %H:%M",
        "%d/%m/%y %H:%M",
        "%d/%m/%Y",
        "%d/%m/%y",
    )

    def __init__(self, contenedor: tk.Widget) -> None:
        self._fecha = datetime.now()
        self.frame = tk.Frame(contenedor)
        self._texto_boton = tk.StringVar()
        self._dialogo: tk.Toplevel | None = None
        self._mes_visible = self._fecha.month
        self._anio_visible = self._fecha.year
        self._hora_dialogo = tk.StringVar()
        self._minuto_dialogo = tk.StringVar()
        self._periodo_dialogo = tk.StringVar()
        self._construir()
        self._refrescar_texto()

    def obtener_valor(self) -> str:
        # Consolidamos la fecha/hora en el formato historico que ya usa la app.
        return self._fecha.strftime("%d/%m/%Y %I:%M %p")

    def obtener_solo_fecha(self) -> str:
        # Exponemos la fecha en el formato requerido por correos personalizados.
        return self._fecha.strftime("%d/%m/%Y")

    def obtener_solo_hora_24(self) -> str:
        # Exponemos la hora en 24 horas para el flujo de correos personalizados.
        return self._fecha.strftime("%H:%M")

    def establecer_desde_texto(self, valor: str) -> None:
        # Cargamos textos guardados previamente aunque vengan de versiones anteriores.
        texto = valor.strip()
        if not texto:
            self.restablecer()
            return

        fecha = None
        for formato in self.FORMATOS_ENTRADA:
            try:
                fecha = datetime.strptime(texto, formato)
                break
            except ValueError:
                continue

        if fecha is None:
            return

        self._fecha = fecha
        self._mes_visible = fecha.month
        self._anio_visible = fecha.year
        self._refrescar_texto()

    def restablecer(self) -> None:
        # Regresamos el selector al momento actual.
        self._fecha = datetime.now()
        self._mes_visible = self._fecha.month
        self._anio_visible = self._fecha.year
        self._refrescar_texto()

    def _construir(self) -> None:
        ttk.Button(
            self.frame,
            textvariable=self._texto_boton,
            command=self._abrir_dialogo,
            style="Secundario.TButton",
        ).pack(side="left")

    def _refrescar_texto(self) -> None:
        self._texto_boton.set(self._fecha.strftime("%d/%m/%Y %I:%M %p"))

    def _abrir_dialogo(self) -> None:
        if self._dialogo is not None and self._dialogo.winfo_exists():
            self._dialogo.focus_force()
            return

        self._mes_visible = self._fecha.month
        self._anio_visible = self._fecha.year
        self._hora_dialogo.set(self._fecha.strftime("%I"))
        self._minuto_dialogo.set(self._fecha.strftime("%M"))
        self._periodo_dialogo.set(self._fecha.strftime("%p"))

        self._dialogo = tk.Toplevel(self.frame)
        self._dialogo.title("Seleccionar fecha y hora")
        self._dialogo.resizable(False, False)
        self._dialogo.transient(self.frame.winfo_toplevel())
        self._dialogo.grab_set()
        self._dialogo.configure(padx=14, pady=14)
        self._dialogo.protocol("WM_DELETE_WINDOW", self._cerrar_dialogo)

        encabezado = tk.Frame(self._dialogo)
        encabezado.pack(fill="x", pady=(0, 10))

        ttk.Button(
            encabezado,
            text="<",
            width=3,
            command=lambda: self._cambiar_mes(-1),
        ).pack(side="left")
        self._titulo_mes = tk.Label(
            encabezado,
            font=("Segoe UI", 11, "bold"),
            anchor="center",
        )
        self._titulo_mes.pack(side="left", fill="x", expand=True)
        ttk.Button(
            encabezado,
            text=">",
            width=3,
            command=lambda: self._cambiar_mes(1),
        ).pack(side="right")

        self._marco_calendario = tk.Frame(self._dialogo)
        self._marco_calendario.pack(fill="both")

        marco_hora = ttk.LabelFrame(self._dialogo, text="Hora")
        marco_hora.pack(fill="x", pady=(12, 0))

        ttk.Combobox(
            marco_hora,
            textvariable=self._hora_dialogo,
            state="readonly",
            values=[f"{numero:02d}" for numero in range(1, 13)],
            width=4,
        ).pack(side="left", padx=(10, 4), pady=10)
        ttk.Label(marco_hora, text=":").pack(side="left")
        ttk.Combobox(
            marco_hora,
            textvariable=self._minuto_dialogo,
            state="readonly",
            values=[f"{numero:02d}" for numero in range(0, 60, 5)],
            width=4,
        ).pack(side="left", padx=4, pady=10)
        ttk.Combobox(
            marco_hora,
            textvariable=self._periodo_dialogo,
            state="readonly",
            values=["AM", "PM"],
            width=4,
        ).pack(side="left", padx=(4, 10), pady=10)

        fila_acciones = tk.Frame(self._dialogo)
        fila_acciones.pack(fill="x", pady=(12, 0))
        ttk.Button(
            fila_acciones,
            text="Aceptar",
            command=self._confirmar_dialogo,
            style="Corporativo.TButton",
        ).pack(side="right")

        self._dibujar_calendario()

    def _cerrar_dialogo(self) -> None:
        if self._dialogo is None:
            return
        self._dialogo.grab_release()
        self._dialogo.destroy()
        self._dialogo = None

    def _cambiar_mes(self, desplazamiento: int) -> None:
        self._mes_visible += desplazamiento
        if self._mes_visible < 1:
            self._mes_visible = 12
            self._anio_visible -= 1
        elif self._mes_visible > 12:
            self._mes_visible = 1
            self._anio_visible += 1
        self._dibujar_calendario()

    def _dibujar_calendario(self) -> None:
        if self._dialogo is None:
            return

        self._titulo_mes.configure(text=f"{month_name[self._mes_visible]} {self._anio_visible}")

        for widget in self._marco_calendario.winfo_children():
            widget.destroy()

        nombres_dias = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]
        for columna, nombre in enumerate(nombres_dias):
            tk.Label(
                self._marco_calendario,
                text=nombre,
                font=("Segoe UI", 9, "bold"),
                width=4,
            ).grid(row=0, column=columna, padx=2, pady=(0, 4))

        semanas = monthcalendar(self._anio_visible, self._mes_visible)
        for fila, semana in enumerate(semanas, start=1):
            for columna, dia in enumerate(semana):
                if dia == 0:
                    tk.Label(self._marco_calendario, text="", width=4).grid(
                        row=fila,
                        column=columna,
                        padx=2,
                        pady=2,
                    )
                    continue

                estilo = "Secundario.TButton"
                if (
                    self._fecha.year == self._anio_visible
                    and self._fecha.month == self._mes_visible
                    and self._fecha.day == dia
                ):
                    estilo = "Corporativo.TButton"

                ttk.Button(
                    self._marco_calendario,
                    text=f"{dia:02d}",
                    width=4,
                    style=estilo,
                    command=lambda numero_dia=dia: self._seleccionar_dia(numero_dia),
                ).grid(row=fila, column=columna, padx=2, pady=2)

    def _seleccionar_dia(self, dia: int) -> None:
        self._fecha = self._fecha.replace(
            year=self._anio_visible,
            month=self._mes_visible,
            day=dia,
        )
        self._dibujar_calendario()

    def _confirmar_dialogo(self) -> None:
        hora_24 = int(self._hora_dialogo.get())
        if self._periodo_dialogo.get() == "PM" and hora_24 != 12:
            hora_24 += 12
        if self._periodo_dialogo.get() == "AM" and hora_24 == 12:
            hora_24 = 0

        self._fecha = self._fecha.replace(
            hour=hora_24,
            minute=int(self._minuto_dialogo.get()),
            second=0,
            microsecond=0,
        )
        self._refrescar_texto()
        self._cerrar_dialogo()


class VentanaPrincipal:
    # Esta clase concentra toda la interfaz grafica.

    def __init__(
        self,
        raiz: tk.Tk,
        servicio_carga: ServicioCargaExcel,
        servicio_busqueda: ServicioBusquedaRma,
        reproductor_sonidos: ReproductorSonidos,
        gestor_rmas: GestorRmasSemanales,
        generador_vaciado: GeneradorVaciadoRma,
        gestor_programacion: GestorProgramacionSemanal,
        coordinador_envio: CoordinadorEnvioProgramado,
        gestor_envios_personalizados: GestorEnviosPersonalizados,
        coordinador_envios_personalizados: CoordinadorEnviosPersonalizados,
    ) -> None:
        # Guardamos la ventana principal de Tkinter.
        self._raiz = raiz

        # Guardamos el servicio que carga el Excel.
        self._servicio_carga = servicio_carga

        # Guardamos el servicio que busca la serie.
        self._servicio_busqueda = servicio_busqueda

        # Guardamos el reproductor de sonidos.
        self._reproductor_sonidos = reproductor_sonidos

        # Guardamos el gestor de RMAs semanales escritos manualmente.
        self._gestor_rmas = gestor_rmas
        # Guardamos el generador del vaciado final.
        self._generador_vaciado = generador_vaciado
        # Guardamos el gestor que persiste series por dia para correos.
        self._gestor_programacion = gestor_programacion
        # Guardamos el coordinador que arma y envia el correo Outlook.
        self._coordinador_envio = coordinador_envio
        # Guardamos el gestor de correos puntuales a destinatarios libres.
        self._gestor_envios_personalizados = gestor_envios_personalizados
        # Guardamos el coordinador que procesa correos puntuales vencidos.
        self._coordinador_envios_personalizados = coordinador_envios_personalizados

        # Acumulamos el avance de series encontradas por RMA durante la sesion.
        self._ruta_seleccionada = tk.StringVar()

        # Variable que contiene la serie capturada.
        self._serie = tk.StringVar()

        # Variable para mostrar el mensaje principal del resultado.
        self._mensaje_estado = tk.StringVar(value="Carga un archivo para comenzar.")

        # Variable para mostrar detalles adicionales.
        self._mensaje_detalle = tk.StringVar(value="Esperando archivo de Excel.")
        # RMA actual para permitir saltar directo a su bloque de progreso.
        self._rma_actual_consultado = tk.StringVar(value="")
        # Dia seleccionado para programar correo.
        self._dia_programado = tk.StringVar(value="Lunes")
        # Fecha y hora de visita para el dia seleccionado.
        self._fecha_visita = tk.StringVar()
        # Datos del formulario de correo personalizado.
        self._correo_personalizado_para = tk.StringVar()
        self._correo_personalizado_cc = tk.StringVar()
        self._correo_personalizado_asunto = tk.StringVar()
        self._correo_personalizado_fecha = tk.StringVar()
        self._correo_personalizado_hora = tk.StringVar()

        # Acumulamos el avance de series encontradas por RMA durante la sesion.
        self._progreso_rmas: dict[str, dict[str, object]] = {}
        # Evitamos pintar varias veces el mismo RMA completo en el Excel.
        self._rmas_completos_marcados: set[str] = set()

        # Definimos una paleta de color corporativa sobria y consistente.
        self._colores = {
            "fondo": "#e7edf3",
            "panel": "#fbfdff",
            "panel_alt": "#f2f6fa",
            "primario": "#123b5d",
            "secundario": "#2e6f95",
            "acento": "#8fb7d1",
            "texto": "#16324a",
            "texto_suave": "#5c7288",
            "borde": "#c8d5e1",
            "exito": "#0f766e",
            "alerta": "#b45309",
            "error": "#b91c1c",
        }

        # Construimos la ventana base.
        self._construir_ventana()

        # Configuramos estilos visuales reutilizables de ttk.
        self._configurar_estilos()

        # Construimos todos los controles visuales.
        self._construir_widgets()

        # Registramos eventos de teclado.
        self._registrar_eventos()
        # Activamos el envio automatico de correos personalizados vencidos.
        self._iniciar_procesamiento_automatico_personalizados()

        # Intentamos cargar el archivo predeterminado al abrir la app.
        self._intentar_cargar_archivo_predeterminado()
        # Si ya habia informacion guardada para el dia seleccionado, la mostramos.
        self._cargar_programacion_dia_en_formulario()

    def _construir_ventana(self) -> None:
        # Definimos el titulo de la ventana.
        self._raiz.title("Consulta de RMA")

        # Definimos el tamano inicial.
        self._raiz.geometry("860x680")

        # Definimos el tamano minimo permitido.
        self._raiz.minsize(760, 560)

        # Agregamos margenes internos para que respire la interfaz.
        self._raiz.configure(padx=20, pady=20, bg=self._colores["fondo"])

    def _configurar_estilos(self) -> None:
        # Creamos el objeto de estilos de ttk.
        estilo = ttk.Style()

        # Usamos el tema clam porque permite personalizar mejor los colores.
        estilo.theme_use("clam")

        # Fondo general de controles y paneles.
        estilo.configure(
            ".",
            background=self._colores["fondo"],
            foreground=self._colores["texto"],
        )

        # Estilo de los cuadros agrupados.
        estilo.configure(
            "TLabelframe",
            background=self._colores["panel"],
            bordercolor=self._colores["borde"],
            borderwidth=1,
            relief="solid",
            padding=10,
        )
        estilo.configure(
            "TLabelframe.Label",
            background=self._colores["panel"],
            foreground=self._colores["primario"],
            font=("Segoe UI", 10, "bold"),
        )

        # Estilo de etiquetas comunes.
        estilo.configure(
            "TLabel",
            background=self._colores["panel"],
            foreground=self._colores["texto"],
            font=("Segoe UI", 10),
        )

        # Estilo del campo de entrada.
        estilo.configure(
            "TEntry",
            fieldbackground="#f8fbfd",
            foreground=self._colores["texto"],
            bordercolor=self._colores["borde"],
            lightcolor=self._colores["borde"],
            darkcolor=self._colores["borde"],
            padding=8,
        )

        # Estilo principal de botones.
        estilo.configure(
            "Corporativo.TButton",
            background=self._colores["primario"],
            foreground="#ffffff",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10, "bold"),
            padding=(14, 8),
        )
        estilo.map(
            "Corporativo.TButton",
            background=[("active", self._colores["secundario"])],
            foreground=[("disabled", "#d6dee6"), ("!disabled", "#ffffff")],
        )

        # Estilo secundario para acciones menos importantes.
        estilo.configure(
            "Secundario.TButton",
            background="#d9e6f2",
            foreground=self._colores["primario"],
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10, "bold"),
            padding=(14, 8),
        )
        estilo.map(
            "Secundario.TButton",
            background=[("active", "#c8dced")],
            foreground=[("!disabled", self._colores["primario"])],
        )

        # Estilos para el control de pestanas.
        estilo.configure(
            "TNotebook",
            background=self._colores["fondo"],
            borderwidth=0,
        )
        estilo.configure(
            "TNotebook.Tab",
            background="#d9e6f2",
            foreground=self._colores["primario"],
            font=("Segoe UI", 10, "bold"),
            padding=(14, 8),
        )
        estilo.map(
            "TNotebook.Tab",
            background=[("selected", self._colores["panel"]), ("active", "#c8dced")],
            foreground=[("selected", self._colores["primario"])],
        )

    def _construir_widgets(self) -> None:
        # Franja superior para dar identidad visual a la pantalla.
        encabezado = tk.Frame(self._raiz, bg=self._colores["primario"], height=88)
        encabezado.pack(fill="x", pady=(0, 18))
        encabezado.pack_propagate(False)

        # Titulo principal del sistema.
        tk.Label(
            encabezado,
            text="CONSULTA DE RMA",
            bg=self._colores["primario"],
            fg="#ffffff",
            font=("Segoe UI", 19, "bold"),
        ).pack(anchor="w", padx=20, pady=(14, 0))

        # Subtitulo breve para contexto operativo.
        tk.Label(
            encabezado,
            text="Busqueda rapida de series con alertas visuales y sonoras",
            bg=self._colores["primario"],
            fg="#d5e4ef",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=20, pady=(2, 10))

        # Contenedor principal del dashboard.
        tablero = tk.Frame(self._raiz, bg=self._colores["fondo"])
        tablero.pack(fill="both", expand=True)

        # Creamos un control de pestanas para separar actividades.
        pestañas = ttk.Notebook(tablero)
        pestañas.pack(fill="both", expand=True)

        # Primera pestana: operacion normal y RMAs semanales.
        pestaña_consulta = tk.Frame(pestañas, bg=self._colores["fondo"])
        pestañas.add(pestaña_consulta, text="Consulta y RMAs")

        # Segunda pestana: programacion de correos.
        pestaña_programacion = tk.Frame(pestañas, bg=self._colores["fondo"])
        pestañas.add(pestaña_programacion, text="Programacion de correos")

        # Layout de la pestana de consulta.
        contenido_consulta = tk.Frame(pestaña_consulta, bg=self._colores["fondo"])
        contenido_consulta.pack(fill="both", expand=True)

        # Columna izquierda para acciones y captura.
        columna_izquierda = tk.Frame(contenido_consulta, bg=self._colores["fondo"])
        columna_izquierda.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Columna derecha para el resultado protagonista.
        columna_derecha = tk.Frame(contenido_consulta, bg=self._colores["fondo"])
        columna_derecha.pack(side="left", fill="both", expand=True)

        # Creamos el contenedor superior para el manejo del archivo.
        marco_archivo = ttk.LabelFrame(columna_izquierda, text="Archivo de datos")
        marco_archivo.pack(fill="x", pady=(0, 14))

        # Mostramos la ruta del archivo actual en modo solo lectura.
        ttk.Entry(
            marco_archivo,
            textvariable=self._ruta_seleccionada,
            state="readonly",
        ).pack(fill="x", padx=12, pady=(12, 8))

        # Creamos un marco para agrupar los botones del archivo.
        marco_botones = ttk.Frame(marco_archivo)
        marco_botones.pack(fill="x", padx=12, pady=(0, 12))

        # Boton para seleccionar un nuevo Excel.
        ttk.Button(
            marco_botones,
            text="Seleccionar Excel",
            command=self._seleccionar_archivo,
            style="Corporativo.TButton",
        ).pack(side="left")

        # Boton para recargar el archivo actual.
        ttk.Button(
            marco_botones,
            text="Recargar",
            command=self._recargar_archivo_actual,
            style="Secundario.TButton",
        ).pack(side="left", padx=(8, 0))

        # Creamos el contenedor central para capturar la serie.
        marco_busqueda = ttk.LabelFrame(columna_izquierda, text="Consulta por serie")
        marco_busqueda.pack(fill="x", pady=(0, 14))

        # Etiqueta que indica la caja de entrada.
        ttk.Label(marco_busqueda, text="Serie").pack(anchor="w", padx=12, pady=(12, 4))

        # Caja de texto donde el usuario escribe o escanea la serie.
        self._entrada_serie = ttk.Entry(
            marco_busqueda,
            textvariable=self._serie,
            font=("Segoe UI", 14),
        )
        self._entrada_serie.pack(fill="x", padx=12, pady=(0, 12))

        # Boton para ejecutar la busqueda manualmente.
        ttk.Button(
            marco_busqueda,
            text="Buscar",
            command=self._buscar_serie,
            style="Corporativo.TButton",
        ).pack(anchor="e", padx=12, pady=(0, 12))

        # Tarjeta informativa para reforzar el flujo de uso.
        tarjeta_info = tk.Frame(
            columna_izquierda,
            bg=self._colores["panel_alt"],
            highlightbackground=self._colores["borde"],
            highlightthickness=1,
        )
        tarjeta_info.pack(fill="x", pady=(0, 14))


        # Creamos el contenedor derecho con scroll para mostrar resultados extensos.
        marco_resultado_exterior = tk.Frame(
            columna_derecha,
            bg=self._colores["panel"],
            highlightbackground=self._colores["borde"],
            highlightthickness=1,
        )
        marco_resultado_exterior.pack(fill="both", expand=True)

        barra_resultado = ttk.Scrollbar(marco_resultado_exterior, orient="vertical")
        barra_resultado.pack(side="right", fill="y")

        self._canvas_resultado = tk.Canvas(
            marco_resultado_exterior,
            bg=self._colores["panel"],
            highlightthickness=0,
            yscrollcommand=barra_resultado.set,
        )
        self._canvas_resultado.pack(side="left", fill="both", expand=True)
        barra_resultado.configure(command=self._canvas_resultado.yview)

        marco_resultado = tk.Frame(self._canvas_resultado, bg=self._colores["panel"])
        self._ventana_canvas_resultado = self._canvas_resultado.create_window(
            (0, 0),
            window=marco_resultado,
            anchor="nw",
        )

        def _actualizar_scroll_resultado(_evento) -> None:
            self._canvas_resultado.configure(
                scrollregion=self._canvas_resultado.bbox("all")
            )

        def _ajustar_ancho_resultado(evento) -> None:
            self._canvas_resultado.itemconfigure(
                self._ventana_canvas_resultado,
                width=evento.width,
            )

        def _desplazar_rueda_resultado(evento) -> None:
            self._canvas_resultado.yview_scroll(
                int(-1 * (evento.delta / 120)),
                "units",
            )

        def _activar_rueda_resultado(_evento) -> None:
            self._canvas_resultado.bind_all("<MouseWheel>", _desplazar_rueda_resultado)

        def _desactivar_rueda_resultado(_evento) -> None:
            self._canvas_resultado.unbind_all("<MouseWheel>")

        marco_resultado.bind("<Configure>", _actualizar_scroll_resultado)
        self._canvas_resultado.bind("<Configure>", _ajustar_ancho_resultado)
        self._canvas_resultado.bind("<Enter>", _activar_rueda_resultado)
        self._canvas_resultado.bind("<Leave>", _desactivar_rueda_resultado)

        # Encabezado del panel de resultado.
        tk.Label(
            marco_resultado,
            text="Resultado",
            bg=self._colores["panel"],
            fg=self._colores["primario"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=18, pady=(16, 6))

        # Franja decorativa superior de la tarjeta resultado.
        self._franja_estado = tk.Frame(
            marco_resultado,
            bg=self._colores["primario"],
            height=10,
        )
        self._franja_estado.pack(fill="x", padx=18, pady=(0, 18))

        # Etiqueta principal donde se mostrara el estado final.
        self._etiqueta_estado = tk.Label(
            marco_resultado,
            textvariable=self._mensaje_estado,
            bg=self._colores["panel"],
            fg=self._colores["primario"],
            font=("Segoe UI", 16, "bold"),
            wraplength=320,
            justify="left",
        )
        self._etiqueta_estado.pack(anchor="w", padx=18, pady=(0, 10))

        # Etiqueta secundaria donde se mostraran detalles adicionales.
        tk.Label(
            marco_resultado,
            textvariable=self._mensaje_detalle,
            bg=self._colores["panel"],
            fg=self._colores["texto_suave"],
            font=("Segoe UI", 11),
            wraplength=340,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 18))

        # Etiqueta de apoyo para que el panel no se vea vacio.
        self._etiqueta_ayuda = tk.Label(
            marco_resultado,
            text="Esperando una consulta...",
            bg=self._colores["panel"],
            fg=self._colores["acento"],
            font=("Segoe UI", 18, "bold"),
        )
        self._etiqueta_ayuda.pack(anchor="w", padx=18, pady=(14, 0))

        self._boton_enfocar_rma_actual = ttk.Button(
            marco_resultado,
            text="Ver progreso del RMA actual",
            command=self._enfocar_rma_actual,
            style="Secundario.TButton",
        )
        self._boton_enfocar_rma_actual.pack(anchor="w", padx=18, pady=(10, 0))
        self._boton_enfocar_rma_actual.state(["disabled"])

        self._etiqueta_series_rma = tk.Label(
            marco_resultado,
            text="",
            bg=self._colores["panel"],
            fg=self._colores["primario"],
            font=("Segoe UI", 11, "bold"),
        )
        self._etiqueta_series_rma.pack(anchor="w", padx=18, pady=(18, 6))

        self._visor_series_rma = tk.Text(
            marco_resultado,
            height=12,
            wrap="word",
            font=("Consolas", 10),
            bg="#f8fbfd",
            fg=self._colores["texto"],
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self._colores["borde"],
            insertbackground=self._colores["primario"],
        )
        self._visor_series_rma.tag_configure(
            "encontrada",
            foreground=self._colores["exito"],
        )
        self._visor_series_rma.tag_configure(
            "pendiente",
            foreground=self._colores["texto"],
        )
        self._visor_series_rma.tag_configure(
            "rma_enfocado",
            background="#d9f99d",
            foreground=self._colores["primario"],
        )
        self._visor_series_rma.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self._visor_series_rma.configure(state="disabled")

        self._etiqueta_rmas_completos = tk.Label(
            marco_resultado,
            text="",
            bg=self._colores["panel"],
            fg=self._colores["exito"],
            font=("Segoe UI", 11, "bold"),
        )
        self._etiqueta_rmas_completos.pack(anchor="w", padx=18, pady=(0, 6))

        self._boton_copiar_rmas_completos = ttk.Button(
            marco_resultado,
            text="Copiar RMAs completos",
            command=self._copiar_rmas_completos,
            style="Secundario.TButton",
        )
        self._boton_copiar_rmas_completos.pack(anchor="w", padx=18, pady=(0, 8))
        self._boton_copiar_rmas_completos.state(["disabled"])

        self._visor_rmas_completos = tk.Text(
            marco_resultado,
            height=7,
            wrap="word",
            font=("Consolas", 10),
            bg="#f8fbfd",
            fg=self._colores["exito"],
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self._colores["borde"],
            insertbackground=self._colores["primario"],
        )
        self._visor_rmas_completos.pack(fill="x", padx=18, pady=(0, 18))
        self._visor_rmas_completos.configure(state="disabled")

        ttk.Button(
            marco_resultado,
            text="Generar vaciado",
            command=self._generar_vaciado_rma,
            style="Corporativo.TButton",
        ).pack(anchor="e", padx=18, pady=(0, 18))

        # Aplicamos color base inicial al resultado antes de cualquier consulta.
        self._etiqueta_estado.configure(foreground=self._colores["primario"])

        # Construimos por separado la pestana dedicada a programacion de correos.
        self._construir_pestaña_programacion(pestaña_programacion)

    def _construir_pestaña_programacion(self, contenedor: tk.Frame) -> None:
        # Creamos un canvas con scroll vertical para poder recorrer toda la pestana.
        marco_scroll = tk.Frame(contenedor, bg=self._colores["fondo"])
        marco_scroll.pack(fill="both", expand=True)

        barra_vertical = ttk.Scrollbar(marco_scroll, orient="vertical")
        barra_vertical.pack(side="right", fill="y")

        canvas = tk.Canvas(
            marco_scroll,
            bg=self._colores["fondo"],
            highlightthickness=0,
            yscrollcommand=barra_vertical.set,
        )
        canvas.pack(side="left", fill="both", expand=True)
        barra_vertical.configure(command=canvas.yview)

        # Contenedor interno real donde vive el contenido de la pestana.
        panel = tk.Frame(canvas, bg=self._colores["fondo"])
        ventana_canvas = canvas.create_window((0, 0), window=panel, anchor="nw")

        def _actualizar_scroll(_evento: tk.Event | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _ajustar_ancho_panel(_evento: tk.Event) -> None:
            canvas.itemconfigure(ventana_canvas, width=_evento.width)

        panel.bind("<Configure>", _actualizar_scroll)
        canvas.bind("<Configure>", _ajustar_ancho_panel)

        def _desplazar_rueda(_evento: tk.Event) -> None:
            if _evento.delta == 0:
                return
            canvas.yview_scroll(int((_evento.delta / 120) * -1), "units")

        def _activar_scroll(_evento: tk.Event) -> None:
            canvas.bind_all("<MouseWheel>", _desplazar_rueda)

        def _desactivar_scroll(_evento: tk.Event) -> None:
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _activar_scroll)
        canvas.bind("<Leave>", _desactivar_scroll)

        tarjeta_programacion = tk.Frame(
            panel,
            bg=self._colores["panel_alt"],
            highlightbackground=self._colores["borde"],
            highlightthickness=1,
        )
        tarjeta_programacion.pack(fill="both", expand=True)

        tk.Label(
            tarjeta_programacion,
            text="Programacion de correos",
            bg=self._colores["panel_alt"],
            fg=self._colores["primario"],
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 8))

        tk.Label(
            tarjeta_programacion,
            text=(
                "Configura las series por dia para que Outlook prepare y envie "
                "el correo automatico de lunes a viernes."
            ),
            bg=self._colores["panel_alt"],
            fg=self._colores["texto_suave"],
            justify="left",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(0, 12))

        tk.Label(
            tarjeta_programacion,
            text="El boton Enviar hoy usa el dia actual del sistema, no el dia seleccionado.",
            bg=self._colores["panel_alt"],
            fg=self._colores["alerta"],
            justify="left",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=16, pady=(0, 12))

        fila_programacion = tk.Frame(
            tarjeta_programacion,
            bg=self._colores["panel_alt"],
        )
        fila_programacion.pack(fill="x", padx=16, pady=(0, 10))

        ttk.Label(fila_programacion, text="Dia").pack(side="left")
        self._combo_dias = ttk.Combobox(
            fila_programacion,
            state="readonly",
            values=self._gestor_programacion.DIAS_HABILES,
            textvariable=self._dia_programado,
            width=12,
        )
        self._combo_dias.pack(side="left", padx=(8, 12))
        self._combo_dias.bind(
            "<<ComboboxSelected>>",
            lambda _evento: self._cargar_programacion_dia_en_formulario(),
        )

        ttk.Label(fila_programacion, text="Fecha / hora visita").pack(side="left")
        self._selector_fecha_visita = SelectorFechaHoraVisita(fila_programacion)
        self._selector_fecha_visita.frame.pack(side="left", padx=(8, 0))

        tk.Label(
            tarjeta_programacion,
            text="Series del dia seleccionado, una por linea.",
            bg=self._colores["panel_alt"],
            fg=self._colores["texto_suave"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self._texto_series_programadas = tk.Text(
            tarjeta_programacion,
            height=12,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#f8fbfd",
            fg=self._colores["texto"],
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self._colores["borde"],
            highlightcolor=self._colores["secundario"],
            insertbackground=self._colores["primario"],
        )
        self._texto_series_programadas.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        fila_botones_programacion = tk.Frame(
            tarjeta_programacion,
            bg=self._colores["panel_alt"],
        )
        fila_botones_programacion.pack(fill="x", padx=16, pady=(0, 16))

        ttk.Button(
            fila_botones_programacion,
            text="Guardar dia",
            command=self._guardar_programacion_dia,
            style="Corporativo.TButton",
        ).pack(side="left")
        ttk.Button(
            fila_botones_programacion,
            text="Ver programacion",
            command=self._mostrar_programacion_semanal,
            style="Secundario.TButton",
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            fila_botones_programacion,
            text="Enviar hoy",
            command=self._enviar_correo_hoy,
            style="Secundario.TButton",
        ).pack(side="left", padx=(8, 0))

        tarjeta_personalizada = tk.Frame(
            panel,
            bg=self._colores["panel_alt"],
            highlightbackground=self._colores["borde"],
            highlightthickness=1,
        )
        tarjeta_personalizada.pack(fill="both", expand=True, pady=(14, 0))

        tk.Label(
            tarjeta_personalizada,
            text="Correos personalizados programados",
            bg=self._colores["panel_alt"],
            fg=self._colores["primario"],
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 8))

        tk.Label(
            tarjeta_personalizada,
            text=(
                "Programa un correo para cualquier destinatario con fecha y hora exacta."
            ),
            bg=self._colores["panel_alt"],
            fg=self._colores["texto_suave"],
            justify="left",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(0, 12))

        tk.Label(
            tarjeta_personalizada,
            text=(
                "Fecha: DD/MM/AAAA, por ejemplo 15/03/2026. "
                "Hora: HH:MM en 24 horas, por ejemplo 09:30 o 18:45."
            ),
            bg=self._colores["panel_alt"],
            fg=self._colores["alerta"],
            justify="left",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=16, pady=(0, 12))

        fila_destinatarios = tk.Frame(
            tarjeta_personalizada,
            bg=self._colores["panel_alt"],
        )
        fila_destinatarios.pack(fill="x", padx=16, pady=(0, 10))

        ttk.Label(fila_destinatarios, text="Para").pack(side="left")
        ttk.Entry(
            fila_destinatarios,
            textvariable=self._correo_personalizado_para,
            width=34,
        ).pack(side="left", padx=(8, 12))

        ttk.Label(fila_destinatarios, text="CC").pack(side="left")
        ttk.Entry(
            fila_destinatarios,
            textvariable=self._correo_personalizado_cc,
            width=30,
        ).pack(side="left", padx=(8, 0))

        fila_asunto_fecha = tk.Frame(
            tarjeta_personalizada,
            bg=self._colores["panel_alt"],
        )
        fila_asunto_fecha.pack(fill="x", padx=16, pady=(0, 10))

        ttk.Label(fila_asunto_fecha, text="Asunto").pack(side="left")
        ttk.Entry(
            fila_asunto_fecha,
            textvariable=self._correo_personalizado_asunto,
            width=42,
        ).pack(side="left", padx=(8, 12))

        ttk.Label(fila_asunto_fecha, text="Fecha / hora").pack(side="left")
        self._selector_fecha_correo_personalizado = SelectorFechaHoraVisita(
            fila_asunto_fecha
        )
        self._selector_fecha_correo_personalizado.frame.pack(side="left", padx=(8, 0))

        tk.Label(
            tarjeta_personalizada,
            text="Mensaje del correo",
            bg=self._colores["panel_alt"],
            fg=self._colores["texto_suave"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self._texto_correo_personalizado = tk.Text(
            tarjeta_personalizada,
            height=8,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#f8fbfd",
            fg=self._colores["texto"],
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self._colores["borde"],
            highlightcolor=self._colores["secundario"],
            insertbackground=self._colores["primario"],
        )
        self._texto_correo_personalizado.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        fila_botones_personalizados = tk.Frame(
            tarjeta_personalizada,
            bg=self._colores["panel_alt"],
        )
        fila_botones_personalizados.pack(fill="x", padx=16, pady=(0, 16))

        ttk.Button(
            fila_botones_personalizados,
            text="Programar correo",
            command=self._guardar_envio_personalizado,
            style="Corporativo.TButton",
        ).pack(side="left")
        ttk.Button(
            fila_botones_personalizados,
            text="Ver programados",
            command=self._mostrar_envios_personalizados,
            style="Secundario.TButton",
        ).pack(side="left", padx=(8, 0))

    def _registrar_eventos(self) -> None:
        # Hacemos que la tecla Enter dispare la busqueda.
        self._raiz.bind("<Return>", lambda _evento: self._buscar_serie())

    def _intentar_cargar_archivo_predeterminado(self) -> None:
        # Intentamos leer el archivo configurado al iniciar la app.
        try:
            # Cargamos el archivo predeterminado.
            marco_datos = self._servicio_carga.cargar_predeterminado()

            # Leemos la ruta configurada actualmente.
            ruta_actual = self._servicio_carga.configuracion_actual.ruta_excel

            # Mostramos la ruta en la interfaz.
            self._ruta_seleccionada.set(str(ruta_actual))

            # Mostramos mensaje de exito.
            self._mensaje_estado.set("Archivo cargado correctamente.")

            # Informamos cuantos registros se cargaron.
            self._mensaje_detalle.set(f"Registros cargados: {len(marco_datos)}")
        except Exception as error:
            # Si algo falla, recuperamos la ruta configurada.
            ruta_predeterminada = self._servicio_carga.configuracion_actual.ruta_excel

            # Mostramos la ruta aunque no haya cargado.
            self._ruta_seleccionada.set(str(ruta_predeterminada))

            # Indicamos que hubo un problema al cargar.
            self._mensaje_estado.set("No se pudo cargar el archivo inicial.")

            # Mostramos el detalle tecnico del error.
            self._mensaje_detalle.set(str(error))

    def _seleccionar_archivo(self) -> None:
        # Abrimos el explorador para que el usuario elija un Excel.
        archivo_seleccionado = filedialog.askopenfilename(
            title="Selecciona un archivo de Excel",
            filetypes=[("Archivos de Excel", "*.xlsx *.xls")],
        )

        # Si el usuario cancela, no hacemos nada.
        if not archivo_seleccionado:
            return

        # Si eligio un archivo, intentamos cargarlo.
        self._cargar_archivo(Path(archivo_seleccionado))

    def _recargar_archivo_actual(self) -> None:
        # Leemos la ruta mostrada actualmente en pantalla.
        ruta_actual = self._ruta_seleccionada.get().strip()

        # Si no existe ruta, avisamos al usuario.
        if not ruta_actual:
            messagebox.showwarning("Archivo faltante", "Primero selecciona un archivo.")
            return

        # Volvemos a cargar la misma ruta.
        self._cargar_archivo(Path(ruta_actual))

    def _cargar_archivo(self, ruta_archivo: Path) -> None:
        # Intentamos cargar el archivo indicado.
        try:
            # Pedimos al servicio que lea el Excel.
            marco_datos = self._servicio_carga.cargar_desde_ruta(ruta_archivo)

            # Reflejamos la ruta cargada en la interfaz.
            self._ruta_seleccionada.set(str(ruta_archivo))

            # Mostramos mensaje de exito.
            self._mensaje_estado.set("Archivo cargado correctamente.")

            # Mostramos cuantos registros se leyeron.
            self._mensaje_detalle.set(f"Registros cargados: {len(marco_datos)}")

            # Reiniciamos el progreso visual porque puede tratarse de otro Excel.
            self._reiniciar_panel_series_rma()

            # Devolvemos el foco a la caja de serie.
            self._entrada_serie.focus_set()
        except Exception as error:
            # Mostramos una alerta emergente con el error.
            messagebox.showerror("Error al cargar", str(error))

            # Reflejamos el error en el area principal.
            self._mensaje_estado.set("Error al cargar el archivo.")

            # Mostramos el detalle tecnico en la interfaz.
            self._mensaje_detalle.set(str(error))

    
    
    
    
    

    def _buscar_serie(self) -> None:
        # Leemos la serie capturada por el usuario o el escaner.
        serie = self._serie.get().strip()

        # Si no hay texto, avisamos y terminamos.
        if not serie:
            self._mensaje_estado.set("Ingresa una serie.")
            self._mensaje_detalle.set("La caja de texto no puede estar vacia.")
            return

        # Si aun no hay datos cargados, mostramos aviso.
        if not self._servicio_busqueda.tiene_datos():
            messagebox.showwarning("Sin datos", "Primero debes cargar un archivo Excel.")
            return

        # Ejecutamos la busqueda de la serie.
        resultado = self._servicio_busqueda.buscar(serie)
        if resultado.estado == EstadoBusqueda.CON_RMA and resultado.rma:
            self._rma_actual_consultado.set(resultado.rma)
            self._boton_enfocar_rma_actual.state(["!disabled"])
        else:
            self._rma_actual_consultado.set("")
            self._boton_enfocar_rma_actual.state(["disabled"])

        # Mostramos el mensaje principal del resultado.
        self._mensaje_estado.set(resultado.mensaje)

        # Mostramos el mensaje de detalle.
        self._mensaje_detalle.set(self._construir_mensaje_detalle(resultado))

        # Mostramos las series relacionadas con el mismo RMA, si existen.
        self._actualizar_series_relacionadas(resultado)

        # Cambiamos el color visual segun el estado.
        self._pintar_estado(resultado.estado)

        # Ocultamos el texto de ayuda una vez que ya hubo una consulta.
        self._etiqueta_ayuda.configure(text="Consulta procesada")

        # Reproducimos el sonido correspondiente.
        self._reproductor_sonidos.reproducir_para(resultado.estado)

        # Limpiamos la caja para recibir una nueva serie.
        self._serie.set("")

        # Dejamos el cursor listo para la siguiente captura.
        self._entrada_serie.focus_set()

    def _construir_mensaje_detalle(self, resultado: ResultadoBusqueda) -> str:
        # Si el estado es CON_RMA, devolvemos serie y RMA.
        if resultado.estado == EstadoBusqueda.CON_RMA:
            detalles = [
                f"Serie consultada: {resultado.serie}",
                f"RMA: {resultado.rma}",
            ]
            if resultado.rma_age:
                detalles.append(f"RMA Age: {resultado.rma_age}")
            if resultado.condicion_rma:
                detalles.append(f"Condicion: {resultado.condicion_rma}")
            return " | ".join(detalles)

        # Si el estado es SIN_CONTRATO, lo aclaramos explicitamente.
        if resultado.estado == EstadoBusqueda.SIN_CONTRATO:
            detalles = [
                f"Serie consultada: {resultado.serie}",
                "Estado detectado: SIN CONTRATO",
            ]
            if resultado.rma_age:
                detalles.append(f"RMA Age: {resultado.rma_age}")
            if resultado.condicion_rma:
                detalles.append(f"Condicion: {resultado.condicion_rma}")
            return " | ".join(detalles)

        # En cualquier otro caso indicamos que no existe un RMA utilizable.
        return f"Serie consultada: {resultado.serie} | No existe RMA utilizable."

    def _pintar_estado(self, estado: EstadoBusqueda) -> None:
        # Elegimos un color distinto para cada estado.
        color = {
            EstadoBusqueda.CON_RMA: self._colores["exito"],
            EstadoBusqueda.SIN_CONTRATO: self._colores["alerta"],
            EstadoBusqueda.SIN_RMA: self._colores["error"],
        }[estado]

        # Aplicamos el color a la etiqueta principal del resultado.
        self._etiqueta_estado.configure(foreground=color)
        # Aplicamos el mismo color a la franja decorativa.
        self._franja_estado.configure(bg=color)

    def _actualizar_series_relacionadas(self, resultado: ResultadoBusqueda) -> None:
        # Pintamos en el panel el progreso acumulado de series encontradas por RMA.
        self._visor_series_rma.configure(state="normal")
        self._visor_series_rma.delete("1.0", "end")

        if resultado.estado == EstadoBusqueda.CON_RMA and resultado.rma and resultado.series_relacionadas:
            self._registrar_progreso_rma(resultado)

        if not self._progreso_rmas:
            self._etiqueta_series_rma.configure(text="")
            self._visor_series_rma.configure(state="disabled")
            self._actualizar_lista_rmas_completos()
            return

        self._etiqueta_series_rma.configure(
            text="Progreso acumulado por RMA durante la sesion"
        )

        for posicion, (rma, datos) in enumerate(self._progreso_rmas.items(), start=1):
            series = list(datos["series"])
            encontradas = set(datos["encontradas"])
            total_series = len(series)
            faltantes = total_series - len(encontradas)
            rma_age = str(datos.get("rma_age", "")).strip()
            condicion_rma = str(datos.get("condicion_rma", "")).strip()
            detalles_rma = []
            if rma_age:
                detalles_rma.append(f"RMA Age: {rma_age}")
            if condicion_rma:
                detalles_rma.append(f"Condicion: {condicion_rma}")
            texto_detalles_rma = (
                " | " + " | ".join(detalles_rma)
                if detalles_rma
                else ""
            )
            inicio_bloque = self._visor_series_rma.index("end")
            self._visor_series_rma.insert(
                "end",
                (
                    f"RMA {rma} | Encontradas: {len(encontradas)} | "
                    f"Faltan: {faltantes} | Total: {total_series}{texto_detalles_rma}\n"
                ),
            )
            for indice, serie in enumerate(series, start=1):
                if serie in encontradas:
                    prefijo = "[OK]"
                    etiqueta = "encontrada"
                else:
                    prefijo = "[  ]"
                    etiqueta = "pendiente"

                self._visor_series_rma.insert(
                    "end",
                    f"{indice:02d}. {prefijo} {serie}\n",
                    etiqueta,
                )

            if posicion < len(self._progreso_rmas):
                self._visor_series_rma.insert("end", "\n")
            fin_bloque = self._visor_series_rma.index("end")
            self._visor_series_rma.tag_add(
                self._tag_rma_progreso(rma),
                inicio_bloque,
                fin_bloque,
            )

        self._visor_series_rma.configure(state="disabled")
        self._actualizar_lista_rmas_completos()
        self._marcar_rmas_completos_en_excel()

    def _registrar_progreso_rma(self, resultado: ResultadoBusqueda) -> None:
        # Guardamos el avance del RMA actual sin perder lo ya encontrado antes.
        if not resultado.rma:
            return

        datos_rma = self._progreso_rmas.get(resultado.rma)
        if datos_rma is None:
            datos_rma = {
                "series": list(resultado.series_relacionadas),
                "encontradas": set(),
                "rma_age": resultado.rma_age,
                "condicion_rma": resultado.condicion_rma,
            }
            self._progreso_rmas[resultado.rma] = datos_rma
        else:
            series_existentes = list(datos_rma["series"])
            for serie in resultado.series_relacionadas:
                if serie not in series_existentes:
                    series_existentes.append(serie)
            datos_rma["series"] = series_existentes
            if resultado.rma_age:
                datos_rma["rma_age"] = resultado.rma_age
            if resultado.condicion_rma:
                datos_rma["condicion_rma"] = resultado.condicion_rma

        datos_rma["encontradas"].add(resultado.serie)

    def _reiniciar_panel_series_rma(self) -> None:
        # Limpiamos el progreso visual cuando cambia la fuente de datos.
        self._progreso_rmas = {}
        self._rmas_completos_marcados = set()
        self._rma_actual_consultado.set("")
        self._boton_enfocar_rma_actual.state(["disabled"])
        self._etiqueta_series_rma.configure(text="")
        self._visor_series_rma.configure(state="normal")
        self._visor_series_rma.delete("1.0", "end")
        self._visor_series_rma.configure(state="disabled")
        self._actualizar_lista_rmas_completos()

    def _obtener_rmas_completos_sesion(self) -> list[str]:
        # Detectamos solo los RMA que ya tienen todas sus series encontradas.
        rmas_completos: list[str] = []
        for rma, datos in self._progreso_rmas.items():
            series = list(datos["series"])
            encontradas = set(datos["encontradas"])
            if series and len(series) == len(encontradas):
                rmas_completos.append(rma)
        return rmas_completos

    def _actualizar_lista_rmas_completos(self) -> None:
        # Mostramos un resumen separado de los RMAs que ya se completaron.
        rmas_completos = self._obtener_rmas_completos_sesion()
        self._visor_rmas_completos.configure(state="normal")
        self._visor_rmas_completos.delete("1.0", "end")

        if not rmas_completos:
            self._etiqueta_rmas_completos.configure(text="")
            self._boton_copiar_rmas_completos.state(["disabled"])
            self._visor_rmas_completos.insert(
                "1.0",
                "Todavia no hay RMAs completos en esta sesion.\n",
            )
            self._visor_rmas_completos.configure(state="disabled")
            return

        self._etiqueta_rmas_completos.configure(text="RMAs completos")
        self._boton_copiar_rmas_completos.state(["!disabled"])
        for indice, rma in enumerate(rmas_completos, start=1):
            self._visor_rmas_completos.insert(
                "end",
                self._construir_linea_rma_completo(indice, rma) + "\n",
            )
        self._visor_rmas_completos.configure(state="disabled")

    def _copiar_rmas_completos(self) -> None:
        rmas_completos = self._obtener_rmas_completos_sesion()
        if not rmas_completos:
            messagebox.showwarning(
                "Sin RMAs completos",
                "Todavia no hay RMAs completos para copiar.",
            )
            return

        texto = ",".join(str(rma).strip() for rma in rmas_completos if str(rma).strip())
        self._raiz.clipboard_clear()
        self._raiz.clipboard_append(texto)
        self._raiz.update()
        self._mensaje_detalle.set(f"RMAs completos copiados: {texto}")

    def _construir_linea_rma_completo(self, indice: int, rma: str) -> str:
        datos = self._progreso_rmas.get(rma, {})
        rma_age = str(datos.get("rma_age", "")).strip()
        condicion_rma = str(datos.get("condicion_rma", "")).strip()
        detalles = []
        if rma_age:
            detalles.append(f"RMA Age: {rma_age}")
        if condicion_rma:
            detalles.append(f"Condicion: {condicion_rma}")

        texto_detalles = " | " + " | ".join(detalles) if detalles else ""
        return f"{indice:02d}. {rma}{texto_detalles}"

    def _tag_rma_progreso(self, rma: str) -> str:
        return "progreso_rma_" + "".join(
            caracter if caracter.isalnum() else "_"
            for caracter in str(rma)
        )

    def _enfocar_rma_actual(self) -> None:
        rma = self._rma_actual_consultado.get().strip()
        if not rma:
            return
        self._enfocar_rma_en_progreso(rma)

    def _enfocar_rma_en_progreso(self, rma: str) -> None:
        # Al seleccionar un RMA completo, saltamos a su bloque en el visor superior.
        tag = self._tag_rma_progreso(rma)
        rangos = self._visor_series_rma.tag_ranges(tag)
        if not rangos:
            return

        self._visor_series_rma.configure(state="normal")
        self._visor_series_rma.tag_remove("rma_enfocado", "1.0", "end")
        self._visor_series_rma.tag_add("rma_enfocado", rangos[0], rangos[1])
        self._visor_series_rma.see(rangos[0])
        self._visor_series_rma.configure(state="disabled")
        self._canvas_resultado.yview_moveto(0.45)

    def _marcar_rmas_completos_en_excel(self) -> None:
        # Marcamos en el Excel solo los RMAs que se completan por primera vez.
        rmas_completos = set(self._obtener_rmas_completos_sesion())
        rmas_nuevos = sorted(rmas_completos - self._rmas_completos_marcados)
        if not rmas_nuevos:
            return

        try:
            self._servicio_busqueda.marcar_rmas_completos_en_excel(rmas_nuevos)
        except PermissionError:
            self._mensaje_detalle.set(
                "RMA completo detectado, pero no se pudo pintar el Excel porque el archivo esta abierto."
            )
            return
        except Exception as error:
            self._mensaje_detalle.set(
                f"RMA completo detectado, pero no se pudo pintar el Excel: {error}"
            )
            return

        self._rmas_completos_marcados.update(rmas_nuevos)

    def _generar_vaciado_rma(self) -> None:
        # Generamos el archivo Excel final solo con los RMA completos en la sesion.
        rmas_completos = self._obtener_rmas_completos_sesion()
        if not rmas_completos:
            messagebox.showwarning(
                "Sin RMAs completos",
                (
                    "Primero debes completar al menos un RMA durante la sesion para "
                    "poder generar el vaciado."
                ),
            )
            return

        try:
            ruta_archivo = self._generador_vaciado.generar_desde_rmas_completos(
                rmas_completos
            )
        except Exception as error:
            messagebox.showerror("No se pudo generar el vaciado", str(error))
            return

        messagebox.showinfo(
            "Vaciado generado",
            f"Se genero correctamente el archivo:\n{ruta_archivo}",
        )

    

    

    def _guardar_programacion_dia(self) -> None:
        # Leemos el dia, fecha y series capturadas por el usuario.
        dia = self._dia_programado.get().strip()
        fecha_visita = self._selector_fecha_visita.obtener_valor().strip()
        series = self._texto_series_programadas.get("1.0", "end").splitlines()

        try:
            # Guardamos la configuracion del dia seleccionado.
            self._gestor_programacion.guardar_dia(dia, fecha_visita, series)
        except Exception as error:
            messagebox.showerror("No se pudo guardar", str(error))
            return

        # Limpiamos solo el cuadro de series para agilizar la captura siguiente.
        self._texto_series_programadas.delete("1.0", "end")
        messagebox.showinfo(
            "Programacion guardada",
            f"Se guardo correctamente la programacion de {dia}.",
        )
        self._cargar_programacion_dia_en_formulario()

    

    def _obtener_series_programadas_actuales(self) -> list[str]:
        # Tomamos las series vigentes del formulario de programacion.
        return [
            serie.strip().upper()
            for serie in self._texto_series_programadas.get("1.0", "end").splitlines()
            if serie.strip()
        ]

    def _cargar_programacion_dia_en_formulario(self) -> None:
        # Buscamos la configuracion guardada para el dia actualmente seleccionado.
        datos_dia = self._gestor_programacion.obtener_dia(self._dia_programado.get())

        # Limpiamos el formulario antes de cargar nuevos datos.
        self._selector_fecha_visita.restablecer()
        self._texto_series_programadas.delete("1.0", "end")

        # Si no habia datos, dejamos el formulario vacio.
        if not datos_dia:
            return

        # Cargamos la fecha y hora guardadas.
        self._selector_fecha_visita.establecer_desde_texto(str(datos_dia["fecha_visita"]))

        # Cargamos las series, una en cada linea.
        self._texto_series_programadas.insert(
            "1.0",
            "\n".join(str(serie) for serie in datos_dia["series"]),
        )

    def _mostrar_programacion_semanal(self) -> None:
        # Recuperamos toda la programacion semanal persistida.
        programacion = self._gestor_programacion.obtener_todo()
        if not programacion:
            messagebox.showinfo(
                "Sin programacion",
                "Aun no existe programacion semanal guardada.",
            )
            return

        ventana = tk.Toplevel(self._raiz)
        ventana.title("Programacion semanal")
        ventana.geometry("560x460")
        ventana.configure(bg=self._colores["panel"], padx=16, pady=16)

        tk.Label(
            ventana,
            text="Series programadas para correo",
            bg=self._colores["panel"],
            fg=self._colores["primario"],
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        visor = tk.Text(
            ventana,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#f8fbfd",
            fg=self._colores["texto"],
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self._colores["borde"],
        )
        visor.pack(fill="both", expand=True)

        for dia in self._gestor_programacion.DIAS_HABILES:
            datos_dia = programacion.get(dia)
            if not datos_dia:
                visor.insert("end", f"{dia}: sin programacion\n\n")
                continue

            visor.insert("end", f"{dia}\n")
            visor.insert("end", f"Fecha visita: {datos_dia['fecha_visita']}\n")
            visor.insert("end", "Series:\n")
            for serie in datos_dia["series"]:
                visor.insert("end", f"- {serie}\n")
            visor.insert("end", "\n")

        visor.configure(state="disabled")

    def _enviar_correo_hoy(self) -> None:
        # Ejecutamos una prueba del correo del dia actual mostrando Outlook antes.
        try:
            dia = self._coordinador_envio.enviar_correo_de_hoy(
                mostrar_antes_de_enviar=True
            )
        except Exception as error:
            messagebox.showerror(
                "No se pudo preparar el correo",
                (
                    f"{error}\n\n"
                    "Recuerda que este boton prepara el correo del dia actual "
                    "segun la fecha del equipo."
                ),
            )
            return

        messagebox.showinfo(
            "Correo preparado",
            f"Se preparo el correo correspondiente a {dia} en Outlook.",
        )

    def _guardar_envio_personalizado(self) -> None:
        # Leemos todos los campos del formulario de correo puntual.
        para = self._correo_personalizado_para.get().strip()
        cc = self._correo_personalizado_cc.get().strip()
        asunto = self._correo_personalizado_asunto.get().strip()
        fecha_programada = self._selector_fecha_correo_personalizado.obtener_solo_fecha().strip()
        hora_programada = self._selector_fecha_correo_personalizado.obtener_solo_hora_24().strip()
        mensaje = self._texto_correo_personalizado.get("1.0", "end").strip()

        try:
            envio = self._gestor_envios_personalizados.guardar_envio(
                para=para,
                cc=cc,
                asunto=asunto,
                mensaje=mensaje,
                fecha_programada=fecha_programada,
                hora_programada=hora_programada,
            )
        except Exception as error:
            messagebox.showerror("No se pudo programar", str(error))
            return

        self._correo_personalizado_para.set("")
        self._correo_personalizado_cc.set("")
        self._correo_personalizado_asunto.set("")
        self._selector_fecha_correo_personalizado.restablecer()
        self._texto_correo_personalizado.delete("1.0", "end")

        messagebox.showinfo(
            "Correo programado",
            (
                "Se programo el correo para "
                f"{envio['fecha_programada']} con destino a {envio['para']}."
            ),
        )

    def _mostrar_envios_personalizados(self) -> None:
        # Recuperamos todos los correos puntuales programados.
        envios = self._gestor_envios_personalizados.obtener_todos()
        if not envios:
            messagebox.showinfo(
                "Sin correos programados",
                "Aun no existe ningun correo puntual programado.",
            )
            return

        ventana = tk.Toplevel(self._raiz)
        ventana.title("Correos personalizados programados")
        ventana.geometry("700x460")
        ventana.configure(bg=self._colores["panel"], padx=16, pady=16)

        tk.Label(
            ventana,
            text="Correos personalizados programados",
            bg=self._colores["panel"],
            fg=self._colores["primario"],
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        visor = tk.Text(
            ventana,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#f8fbfd",
            fg=self._colores["texto"],
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=self._colores["borde"],
        )
        visor.pack(fill="both", expand=True)

        for indice, envio in enumerate(envios, start=1):
            estado = "ENVIADO" if bool(envio["enviado"]) else "PENDIENTE"
            visor.insert("end", f"{indice}. {estado}\n")
            visor.insert("end", f"Para: {envio['para']}\n")
            visor.insert("end", f"CC: {envio['cc'] or 'Sin copia'}\n")
            visor.insert("end", f"Asunto: {envio['asunto']}\n")
            visor.insert("end", f"Fecha programada: {envio['fecha_programada']}\n")
            visor.insert("end", f"Creado en: {envio['creado_en']}\n")
            if envio["enviado"]:
                visor.insert("end", f"Enviado en: {envio['enviado_en']}\n")
            visor.insert("end", f"Mensaje:\n{envio['mensaje']}\n")
            visor.insert("end", "\n" + ("-" * 72) + "\n\n")

        visor.configure(state="disabled")


    def _iniciar_procesamiento_automatico_personalizados(self) -> None:
        # Revisamos periodicamente si ya hay correos puntuales listos para salir.
        self._raiz.after(30000, self._procesar_envios_personalizados_en_segundo_plano)

    def _procesar_envios_personalizados_en_segundo_plano(self) -> None:
        # Enviamos silenciosamente correos puntuales vencidos.
        try:
            self._coordinador_envios_personalizados.enviar_pendientes(
                mostrar_antes_de_enviar=False
            )
        except Exception:
            pass
        finally:
            self._iniciar_procesamiento_automatico_personalizados()
