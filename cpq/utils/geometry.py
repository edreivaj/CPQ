"""
Utilidades geométricas
"""

import math
import geopandas as gpd
from shapely.geometry import box
from typing import Tuple, Optional

from ..config import CFG


def safe_float(value, default=0.0) -> float:
    """
    Convierte un valor a float de forma segura

    Args:
        value: Valor a convertir
        default: Valor por defecto si falla

    Returns:
        Float válido o valor por defecto
    """
    try:
        if hasattr(value, '__len__') and len(value) == 1:
            value = value[0]

        if hasattr(value, '__array__'):
            import numpy as np
            if np.isnan(value).any():
                return default

        f = float(value)

        if math.isnan(f) or math.isinf(f):
            return default

        return f

    except (ValueError, TypeError, AttributeError):
        return default


def bbox_from_gdf(
    gdf: gpd.GeoDataFrame,
    buffer: float = 20.0
) -> Tuple[float, float, float, float]:
    """
    Calcula bounding box desde GeoDataFrame con buffer

    Args:
        gdf: GeoDataFrame
        buffer: Buffer a añadir en todas direcciones

    Returns:
        Tuple (minx, miny, maxx, maxy)
    """
    minx, miny, maxx, maxy = gdf.total_bounds
    return (minx - buffer, miny - buffer, maxx + buffer, maxy + buffer)


def create_house_pad(
    buildable_gdf: gpd.GeoDataFrame,
    width_m: float,
    length_m: float
) -> Optional[gpd.GeoDataFrame]:
    """
    Crea la huella de una casa centrada en zona edificable

    Args:
        buildable_gdf: GeoDataFrame con zona edificable
        width_m: Ancho de la huella
        length_m: Largo de la huella

    Returns:
        GeoDataFrame con la huella o None si falla
    """
    try:
        if buildable_gdf.crs != CFG.ETRS89_UTM30N:
            buildable_gdf = buildable_gdf.to_crs(CFG.ETRS89_UTM30N)

        geom = buildable_gdf.geometry.iloc[0]
        centroid = geom.centroid
        cx, cy = centroid.x, centroid.y

        half_w, half_l = width_m / 2, length_m / 2
        pad_polygon = box(cx - half_w, cy - half_l, cx + half_w, cy + half_l)

        pad_gdf = gpd.GeoDataFrame(
            [{"geometry": pad_polygon}],
            crs=CFG.ETRS89_UTM30N
        )

        return pad_gdf

    except Exception as e:
        print(f"Error creando huella: {e}")
        return None
