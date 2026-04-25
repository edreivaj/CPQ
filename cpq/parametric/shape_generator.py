"""
Generador de geometrías de planta según forma y dimensiones.
"""

import math
from typing import Tuple, Optional

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from .config_parametric import (
    ShapeType,
    FloorConfig,
    ParametricConfig,
    ParametricLimits,
    TechnicalConstraints,
)


class ShapeGenerator:
    """Genera geometrías de planta según forma y dimensiones."""

    def __init__(self, constraints: TechnicalConstraints = None):
        self.constraints = constraints or TechnicalConstraints()

    def generate_bar(
        self,
        width_m: float,
        length_m: float,
        origin: Tuple[float, float] = (0, 0),
    ) -> Polygon:
        """Genera forma de barra rectangular (_, I)."""
        ox, oy = origin
        return box(ox, oy, ox + width_m, oy + length_m)

    def generate_L(
        self,
        wing_a_width: float,
        wing_a_length: float,
        wing_b_width: float,
        wing_b_length: float,
        origin: Tuple[float, float] = (0, 0),
    ) -> Polygon:
        """Genera forma en L."""
        ox, oy = origin
        rect_a = box(ox, oy, ox + wing_a_width, oy + wing_a_length)
        rect_b = box(
            ox + wing_a_width,
            oy,
            ox + wing_a_width + wing_b_length,
            oy + wing_b_width,
        )
        return unary_union([rect_a, rect_b])

    def generate_U(
        self,
        wing_a_width: float,
        wing_a_length: float,
        wing_b_width: float,
        wing_b_length: float,
        connector_width: float,
        connector_length: float,
        origin: Tuple[float, float] = (0, 0),
    ) -> Polygon:
        """Genera forma en U."""
        ox, oy = origin
        rect_a = box(ox, oy, ox + wing_a_width, oy + wing_a_length)
        rect_conn = box(
            ox + wing_a_width,
            oy,
            ox + wing_a_width + connector_length,
            oy + connector_width,
        )
        rect_b = box(
            ox + wing_a_width + connector_length,
            oy,
            ox + wing_a_width + connector_length + wing_b_width,
            oy + wing_b_length,
        )
        return unary_union([rect_a, rect_conn, rect_b])

    def create_floor_config(
        self,
        floor_number: int,
        area_m2: float,
        shape: ShapeType,
        box_width: float,
        box_length: float,
    ) -> FloorConfig:
        """Crea configuración de una planta individual."""
        if shape in [ShapeType.BAR, ShapeType.I_SHAPE]:
            return self._create_bar_floor(floor_number, area_m2, box_width, box_length)
        elif shape == ShapeType.L_SHAPE:
            return self._create_L_floor(floor_number, area_m2, box_width, box_length)
        elif shape == ShapeType.U_SHAPE:
            return self._create_U_floor(floor_number, area_m2, box_width, box_length)
        else:
            return self._create_bar_floor(floor_number, area_m2, box_width, box_length)

    def _create_bar_floor(
        self,
        floor_number: int,
        area_m2: float,
        box_width: float,
        box_length: float,
    ) -> FloorConfig:
        """Crea planta rectangular."""
        ratio = box_length / box_width if box_width > 0 else 1
        width = math.sqrt(area_m2 / ratio)
        length = width * ratio

        width = min(width, box_width)
        length = min(length, box_length)

        geometry = self.generate_bar(width, length)

        return FloorConfig(
            floor_number=floor_number,
            area_m2=area_m2,
            shape=ShapeType.BAR,
            envelope_width_m=width,
            envelope_length_m=length,
            geometry=geometry,
        )

    def _create_L_floor(
        self,
        floor_number: int,
        area_m2: float,
        box_width: float,
        box_length: float,
    ) -> FloorConfig:
        """Crea planta en L."""
        wing_area = area_m2 / 2
        wing_width = min(4.5, box_width * 0.4)
        wing_width = max(wing_width, self.constraints.min_wing_width_m)

        wing_a_length = wing_area / wing_width
        wing_b_length = wing_area / wing_width

        geometry = self.generate_L(
            wing_width, wing_a_length, wing_width, wing_b_length
        )

        env_width = wing_width + wing_b_length
        env_length = wing_a_length

        return FloorConfig(
            floor_number=floor_number,
            area_m2=area_m2,
            shape=ShapeType.L_SHAPE,
            envelope_width_m=env_width,
            envelope_length_m=env_length,
            wing_a_width_m=wing_width,
            wing_a_length_m=wing_a_length,
            wing_b_width_m=wing_width,
            wing_b_length_m=wing_b_length,
            geometry=geometry,
        )

    def _create_U_floor(
        self,
        floor_number: int,
        area_m2: float,
        box_width: float,
        box_length: float,
    ) -> FloorConfig:
        """Crea planta en U."""
        wing_area = area_m2 * 0.35
        conn_area = area_m2 * 0.30

        wing_width = min(4.0, box_width * 0.3)
        wing_width = max(wing_width, self.constraints.min_wing_width_m)
        wing_length = wing_area / wing_width

        conn_width = min(3.5, wing_width)
        conn_length = conn_area / conn_width

        geometry = self.generate_U(
            wing_width,
            wing_length,
            wing_width,
            wing_length,
            conn_width,
            conn_length,
        )

        env_width = wing_width * 2 + conn_length
        env_length = wing_length

        return FloorConfig(
            floor_number=floor_number,
            area_m2=area_m2,
            shape=ShapeType.U_SHAPE,
            envelope_width_m=env_width,
            envelope_length_m=env_length,
            wing_a_width_m=wing_width,
            wing_a_length_m=wing_length,
            wing_b_width_m=wing_width,
            wing_b_length_m=wing_length,
            wing_c_width_m=conn_length,
            geometry=geometry,
        )
