"""
WhatsAppBot - Clase principal para el bot de WhatsApp.
Maneja series, historial y procesamiento de comandos.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


class WhatsAppBot:
    """Bot que gestiona series, historial y respuestas."""

    RUTA_DATOS = Path("datos")
    ARCHIVO_SERIES = RUTA_DATOS / "whatsapp_series.json"
    ARCHIVO_HISTORIAL = RUTA_DATOS / "whatsapp_historial.json"
    ARCHIVO_ENTREGAS = RUTA_DATOS / "whatsapp_entregas.json"

    def __init__(self) -> None:
        self._series: list[dict] = []
        self._cargar_series()

    def _cargar_series(self) -> None:
        """Carga las series desde el archivo JSON."""
        if self.ARCHIVO_SERIES.exists():
            with open(self.ARCHIVO_SERIES, "r", encoding="utf-8") as f:
                self._series = json.load(f)
        else:
            self._series = []
            self._guardar_series()

    def _guardar_series(self) -> None:
        """Guarda las series en el archivo JSON."""
        self.RUTA_DATOS.mkdir(exist_ok=True)
        with open(self.ARCHIVO_SERIES, "w", encoding="utf-8") as f:
            json.dump(self._series, f, indent=2, ensure_ascii=False)

    def obtener_series(self) -> list[dict]:
        """Devuelve la lista de series disponibles."""
        return self._series.copy()

    def obtener_cantidad_disponibles(self) -> int:
        """Devuelve la cantidad de series disponibles."""
        return len([s for s in self._series if s.get("estado") == "disponible"])

    def agregar_serie(self, codigo: str, nombre: str, genero: str = "", estado: str = "disponible") -> bool:
        """Agrega una nueva serie. Retorna True si se agregó, False si ya existe."""
        if any(s["codigo"] == codigo for s in self._series):
            return False
        self._series.append({
            "codigo": codigo,
            "nombre": nombre,
            "genero": genero,
            "estado": estado,
            "fecha_agregada": datetime.now().isoformat()
        })
        self._guardar_series()
        return True

    def quitar_serie(self, codigo: str) -> bool:
        """Elimina una serie por código. Retorna True si se eliminó."""
        inicial = len(self._series)
        self._series = [s for s in self._series if s["codigo"] != codigo]
        if len(self._series) < inicial:
            self._guardar_series()
            return True
        return False

    def entregar_series(self, cantidad: int) -> dict:
        """
        Entrega la cantidad de series solicitadas y las elimina del inventario.

        Args:
            cantidad: Número de series a entregar.

        Returns:
            dict con "exito", "series_entregadas", "mensaje"
        """
        disponibles = [s for s in self._series if s.get("estado") == "disponible"]

        if not disponibles:
            return {
                "exito": False,
                "series_entregadas": [],
                "mensaje": "No hay series disponibles en el sistema."
            }

        if cantidad > len(disponibles):
            cantidad = len(disponibles)
            if cantidad == 0:
                return {
                    "exito": False,
                    "series_entregadas": [],
                    "mensaje": "No hay series disponibles en el sistema."
                }

        # Tomar las primeras N series disponibles (orden FIFO)
        series_a_entregar = disponibles[:cantidad]
        codigos_entregados = [s["codigo"] for s in series_a_entregar]

        # Remover las series entregadas del inventario
        self._series = [s for s in self._series if s["codigo"] not in codigos_entregados]
        self._guardar_series()

        # Registrar la entrega
        self._registrar_entrega(series_a_entregar, cantidad)

        return {
            "exito": True,
            "series_entregadas": series_a_entregar,
            "mensaje": self._formatear_entrega(series_a_entregar)
        }

    def _formatear_entrega(self, series: list[dict]) -> str:
        """Formatea las series entregadas para WhatsApp."""
        if not series:
            return "No hay series disponibles."

        lineas = [f"Aquí tienes {len(series)} serie(s):"]
        for s in series:
            lineas.append(f"• {s['nombre']}")
        lineas.append("")
        lineas.append(f"Series restantes en inventario: {self.obtener_cantidad_disponibles()}")
        return "\n".join(lineas)

    def procesar_comando(self, mensaje: str) -> Optional[str]:
        """
        Procesa un mensaje y devuelve respuesta si es un comando reconocido.

        Comandos reconocidos:
        - "quiero N series" -> Entrega N series y las elimina del inventario
        - "series" / "ver series" -> Muestra cantidad disponible
        - "help" / "ayuda" -> Muestra comandos disponibles
        """
        msg = mensaje.strip().lower()

        # Comando: "quiero N series" o variaciones
        match = re.match(
            r"quiero\s+(\d+)\s+series?",
            msg
        )
        if match:
            cantidad = int(match.group(1))
            resultado = self.entregar_series(cantidad)
            return resultado["mensaje"]

        # Comando: verificar cantidad disponible
        if msg in ("series", "ver series", "cantidad", "cuantas series"):
            return self._formatear_disponibilidad()

        # Comando: ayuda
        if msg in ("help", "ayuda", "comandos"):
            return self._cmd_help()

        return None

    def _formatear_disponibilidad(self) -> str:
        """Formatea la cantidad de series disponibles."""
        cantidad = self.obtener_cantidad_disponibles()
        return f"Series disponibles en inventario: {cantidad}"

    def _registrar_entrega(self, series: list[dict], cantidad: int) -> None:
        """Registra una entrega en el historial."""
        entrada = {
            "timestamp": datetime.now().isoformat(),
            "cantidad_solicitada": cantidad,
            "series_entregadas": [{"codigo": s["codigo"], "nombre": s["nombre"]} for s in series]
        }
        historial = []
        if self.ARCHIVO_HISTORIAL.exists():
            try:
                with open(self.ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
                    historial = json.load(f)
            except Exception:
                pass
        historial.append(entrada)
        with open(self.ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
            json.dump(historial, f, indent=2, ensure_ascii=False)

    def _cmd_help(self) -> str:
        """Devuelve la ayuda de comandos."""
        cantidad = self.obtener_cantidad_disponibles()
        return (
            f"Comandos disponibles (Inventario: {cantidad} series):\n"
            "• Quiero N series - Solicita N series\n"
            "• Series - Ver cantidad disponible\n"
            "• Help - Mostrar comandos"
        )

    def obtener_historial(self) -> list[dict]:
        """Devuelve el historial de solicitudes."""
        if self.ARCHIVO_HISTORIAL.exists():
            with open(self.ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
                return json.load(f)
        return []