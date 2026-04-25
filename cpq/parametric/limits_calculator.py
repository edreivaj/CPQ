"""
Calculador de límites máximos para configuración paramétrica.
"""

import math
from typing import Tuple

from shapely.geometry import Polygon

from ..config import CFG
from .config_parametric import ParametricLimits, ShapeType


class ParametricLimitsCalculator:
    """Calcula los límites máximos permitidos para construcción paramétrica."""

    def calculate_limits(
        self,
        parcel_area_m2: float,
        buildable_geometry: Polygon,
        ocupacion_pct: float = None,
        edificabilidad: float = None,
    ) -> ParametricLimits:
        """
        Calcula todos los límites máximos para la parcela.

        Args:
            parcel_area_m2: Superficie de la parcela
            buildable_geometry: Polígono de la caja edificable
            ocupacion_pct: % ocupación (usa CFG si None)
            edificabilidad: Edificabilidad m2t/m2s (usa CFG si None)

        Returns:
            ParametricLimits con todos los máximos calculados
        """
        ocupacion = ocupacion_pct if ocupacion_pct else (CFG.OCUPACION_PORCENTAJE / 100.0)
        edif = edificabilidad if edificabilidad else CFG.EDIFICABILIDAD_M2T_M2S

        max_footprint = parcel_area_m2 * ocupacion
        max_built = parcel_area_m2 * edif

        parking_area = CFG.PARKING_ANCHO_M * CFG.PARKING_LARGO_M
        max_footprint_neto = max_footprint - parking_area

        box_width, box_length = self._get_box_dimensions(buildable_geometry)

        suggested_pb, suggested_p1, suggested_shape = self._calculate_optimal_2floor(
            max_footprint_neto, max_built, box_width, box_length
        )

        return ParametricLimits(
            parcel_area_m2=parcel_area_m2,
            buildable_box=buildable_geometry,
            buildable_area_m2=buildable_geometry.area,
            max_footprint_m2=max_footprint_neto,
            max_built_area_m2=max_built,
            box_width_m=box_width,
            box_length_m=box_length,
            suggested_pb_m2=suggested_pb,
            suggested_p1_m2=suggested_p1,
            suggested_shape=suggested_shape,
        )

    def _get_box_dimensions(self, geometry: Polygon) -> Tuple[float, float]:
        """Extrae dimensiones de la caja edificable."""
        mrr = geometry.minimum_rotated_rectangle
        coords = list(mrr.exterior.coords)

        edge1 = math.sqrt(
            (coords[1][0] - coords[0][0]) ** 2 + (coords[1][1] - coords[0][1]) ** 2
        )
        edge2 = math.sqrt(
            (coords[2][0] - coords[1][0]) ** 2 + (coords[2][1] - coords[1][1]) ** 2
        )

        width = min(edge1, edge2)
        length = max(edge1, edge2)

        return width, length

    def _calculate_optimal_2floor(
        self,
        max_footprint: float,
        max_built: float,
        box_width: float,
        box_length: float,
    ) -> Tuple[float, float, ShapeType]:
        """Calcula la distribución óptima para 2 plantas."""
        if max_built >= max_footprint * 2:
            suggested_pb = max_footprint
            suggested_p1 = max_footprint
        else:
            half_built = max_built / 2
            if half_built <= max_footprint:
                suggested_pb = half_built
                suggested_p1 = half_built
            else:
                suggested_pb = max_footprint
                suggested_p1 = max_built - max_footprint

        aspect_ratio = box_length / box_width if box_width > 0 else 1

        if aspect_ratio <= 1.5:
            suggested_shape = ShapeType.BAR
        elif aspect_ratio <= 2.5:
            suggested_shape = ShapeType.L_SHAPE
        else:
            suggested_shape = ShapeType.I_SHAPE

        return suggested_pb, suggested_p1, suggested_shape
