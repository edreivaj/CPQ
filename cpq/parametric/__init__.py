"""
Módulo paramétrico para configuración de viviendas a medida.

Permite diseñar viviendas dentro de los límites urbanísticos
calculados automáticamente (ocupación, edificabilidad, retranqueos).
"""

from .config_parametric import (
    ShapeType,
    TechnicalConstraints,
    FloorConfig,
    ParametricConfig,
    ParametricLimits,
)
from .limits_calculator import ParametricLimitsCalculator
from .shape_generator import ShapeGenerator
from .validator import ParametricValidator
from .cost_adapter import ParametricModelAdapter

__all__ = [
    "ShapeType",
    "TechnicalConstraints",
    "FloorConfig",
    "ParametricConfig",
    "ParametricLimits",
    "ParametricLimitsCalculator",
    "ShapeGenerator",
    "ParametricValidator",
    "ParametricModelAdapter",
]
