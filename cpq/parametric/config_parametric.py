"""
Estructuras de datos para configuración paramétrica de viviendas.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
from shapely.geometry import Polygon


class ShapeType(Enum):
    """Formas válidas para la planta de la vivienda."""
    BAR = "_"
    I_SHAPE = "I"
    L_SHAPE = "L"
    U_SHAPE = "U"


@dataclass
class TechnicalConstraints:
    """Restricciones técnicas mínimas para habitabilidad."""

    min_wing_width_m: float = 3.5
    min_corridor_width_m: float = 1.2
    min_stair_width_m: float = 0.90
    min_stair_length_m: float = 3.0

    min_bedroom_m2: float = 9.0
    min_bathroom_m2: float = 3.5
    min_kitchen_m2: float = 7.0
    min_living_m2: float = 14.0

    max_aspect_ratio: float = 4.0
    min_aspect_ratio: float = 0.25


@dataclass
class FloorConfig:
    """Configuración de una planta individual."""

    floor_number: int
    area_m2: float
    shape: ShapeType

    envelope_width_m: float
    envelope_length_m: float

    wing_a_width_m: Optional[float] = None
    wing_a_length_m: Optional[float] = None
    wing_b_width_m: Optional[float] = None
    wing_b_length_m: Optional[float] = None
    wing_c_width_m: Optional[float] = None

    geometry: Optional[Polygon] = None


@dataclass
class ParametricConfig:
    """Configuración paramétrica completa de una vivienda."""

    config_id: str = ""

    parcel_area_m2: float = 0.0
    buildable_box: Optional[Polygon] = None
    buildable_area_m2: float = 0.0
    max_ocupacion_m2: float = 0.0
    max_edificabilidad_m2: float = 0.0

    num_floors: int = 2
    ground_floor: Optional[FloorConfig] = None
    first_floor: Optional[FloorConfig] = None

    total_footprint_m2: float = 0.0
    total_built_m2: float = 0.0

    estimated_bedrooms: int = 0
    estimated_bathrooms: int = 0

    is_valid: bool = False
    validation_errors: List[str] = field(default_factory=list)

    overall_shape: ShapeType = ShapeType.BAR


@dataclass
class ParametricLimits:
    """Límites máximos calculados para una parcela."""

    parcel_area_m2: float
    buildable_box: Polygon
    buildable_area_m2: float

    max_footprint_m2: float
    max_built_area_m2: float

    box_width_m: float
    box_length_m: float

    suggested_pb_m2: float
    suggested_p1_m2: float
    suggested_shape: ShapeType
