"""
Utilidades varias (geometría, finanzas)
"""

from .geometry import safe_float, bbox_from_gdf, create_house_pad
from .finance import compute_monthly_payment

__all__ = [
    'safe_float',
    'bbox_from_gdf',
    'create_house_pad',
    'compute_monthly_payment'
]
