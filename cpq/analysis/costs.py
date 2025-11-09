"""
Cálculos de costes de implantación
"""

import numpy as np
from shapely.geometry import Point
from shapely.ops import nearest_points
import geopandas as gpd
from typing import Tuple

from ..config import CFG
from .terrain import get_z_at_point


def compute_horizontal_access_costs(
    access_point: Point,
    huella_gdf: gpd.GeoDataFrame
) -> Tuple[float, float, float, float, Point]:
    """
    Calcula costes de accesos horizontales

    Args:
        access_point: Punto de acceso desde la calle
        huella_gdf: GeoDataFrame con la huella de la casa

    Returns:
        Tuple (dist_peatonal, dist_vehicular, coste_peatonal,
               coste_vehicular, punto_casa)
    """
    try:
        pad_geom = huella_gdf.geometry.iloc[0]
        _, p_house = nearest_points(access_point, pad_geom)
        dist = float(access_point.distance(p_house))

        coste_peat = float(dist * CFG.COSTE_PAV_PEATONAL_ML)
        coste_veh = float(dist * CFG.COSTE_PAV_VEHICULO_ML)

        return dist, dist, coste_peat, coste_veh, p_house

    except Exception as e:
        print(f"Error accesos horizontales: {e}")
        return 0.0, 0.0, 0.0, 0.0, None


def compute_vertical_access_costs(
    access_point: Point,
    p_parking: Point,
    mdt_path: str
) -> Tuple[float, float]:
    """
    Calcula costes de acceso vertical según matriz de costes

    Args:
        access_point: Punto de acceso desde la calle
        p_parking: Punto de parking/casa
        mdt_path: Ruta al MDT

    Returns:
        Tuple (diferencia_cota_m, coste_adaptacion)
    """
    try:
        if mdt_path is None:
            return 0.0, 0.0

        z_calle = get_z_at_point(mdt_path, access_point)
        z_parking = get_z_at_point(
            mdt_path,
            p_parking if p_parking else access_point
        )

        if np.isnan(z_calle) or np.isnan(z_parking):
            return 0.0, 0.0

        delta = float(abs(z_parking - z_calle))
        coste = 0.0

        for tramo in CFG.MATRIZ_COSTE_ACCESO_VERTICAL:
            if delta <= tramo["max_dif_metros"]:
                coste = float(tramo["coste_adicional"])
                break

        return delta, coste

    except Exception as e:
        print(f"Error acceso vertical: {e}")
        return 0.0, 0.0


def compute_construction_cost(
    superficie_m2: float,
    price_per_m2: float
) -> float:
    """
    Calcula coste de construcción base

    Args:
        superficie_m2: Superficie construida
        price_per_m2: Precio por m2 según sistema y nivel

    Returns:
        Coste total de construcción
    """
    return superficie_m2 * price_per_m2


def compute_slab_cost(superficie_huella_m2: float) -> float:
    """
    Calcula coste de losa de cimentación

    Args:
        superficie_huella_m2: Superficie de la huella

    Returns:
        Coste de losa
    """
    return superficie_huella_m2 * CFG.COSTE_LOSA_M2


def compute_earthworks_cost(vol_metrics: dict) -> Tuple[float, float, float, float]:
    """
    Calcula costes de movimiento de tierras

    Args:
        vol_metrics: Diccionario con cut_m3, fill_m3, balance_m3

    Returns:
        Tuple (coste_desmonte, coste_terraplen, coste_excedente, total)
    """
    cost_cut = vol_metrics['cut_m3'] * CFG.COSTE_DESMONTE_M3
    cost_fill = vol_metrics['fill_m3'] * CFG.COSTE_TERRAPLEN_M3

    excess_m3 = max(0.0, vol_metrics['balance_m3'])
    cost_excess = excess_m3 * CFG.COSTE_GESTION_EXCEDENTE_M3

    total = cost_cut + cost_fill + cost_excess

    return cost_cut, cost_fill, cost_excess, total


def compute_containment_cost(
    muro_result: dict,
    slope_pct: float
) -> Tuple[float, float, float]:
    """
    Calcula coste total de contención (muro + pendiente)

    Args:
        muro_result: Resultado del dimensionamiento de muro
        slope_pct: Pendiente del terreno en %

    Returns:
        Tuple (coste_muro, sobrecoste_pendiente, total)
    """
    coste_muro = muro_result.get('total_coste_€', 0.0) if muro_result else 0.0

    # Sobrecoste por pendiente
    sobrecoste_pendiente = 0.0
    for tier in CFG.MATRIZ_CIMENTACION_PENDIENTE:
        if slope_pct <= tier['max_pendiente']:
            sobrecoste_pendiente = tier['coste_adicional']
            break

    total = coste_muro + sobrecoste_pendiente

    return coste_muro, sobrecoste_pendiente, total


def compute_fees_total() -> float:
    """
    Calcula total de honorarios técnicos

    Returns:
        Total de honorarios
    """
    return (
        CFG.COSTE_FIJO_HONORARIOS_TECNICOS +
        CFG.HON_CALC_ESTRUCTURAL +
        CFG.HON_ESTUDIO_GEOTECNICO +
        CFG.HON_LEV_TOPOGRAFICO +
        CFG.HON_LEGALIZACIONES
    )
