from dataclasses import dataclass
from enum import Enum


class EstadoBusqueda(str, Enum):
    # La serie existe y tiene un RMA valido.
    CON_RMA = "con_rma"
    # La serie existe pero su valor indica SIN CONTRATO.
    SIN_CONTRATO = "sin_contrato"
    # La serie no existe o no tiene un RMA utilizable.
    SIN_RMA = "sin_rma"


@dataclass(frozen=True)
class ResultadoBusqueda:
    # Estado final detectado durante la consulta.
    estado: EstadoBusqueda
    # Serie consultada ya normalizada.
    serie: str
    # RMA encontrado, si aplica.
    rma: str | None = None
    # Antiguedad del RMA tomada de la columna RMA AGE, si existe.
    rma_age: str = ""
    # Condicion del RMA tomada de la columna CONDICION DEL RMA, si existe.
    condicion_rma: str = ""
    # Series relacionadas con el mismo RMA encontrado.
    series_relacionadas: tuple[str, ...] = ()

    @property
    def mensaje(self) -> str:
        # Si el estado es CON_RMA, devolvemos el texto con el folio.
        if self.estado == EstadoBusqueda.CON_RMA:
            return f"SERIE ENCONTRADA -> RMA: {self.rma}"
        # Si el estado es SIN_CONTRATO, avisamos ese caso especial.
        if self.estado == EstadoBusqueda.SIN_CONTRATO:
            return "SERIE ENCONTRADA -> ESTATUS: SIN CONTRATO"
        # En cualquier otro caso informamos que no hay RMA asociado.
        return "SERIE NO TIENE RMA ASOCIADO"
