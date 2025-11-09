"""
Análisis topográfico y de terreno
"""

import math
import numpy as np
import rasterio
import rasterio.mask
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import unary_union
from typing import Dict, Tuple, List, Optional

from ..config import CFG


def get_z_at_point(raster_path: str, point: Point) -> float:
    """
    Obtiene la cota Z en un punto específico

    Args:
        raster_path: Ruta al archivo raster MDT
        point: Punto geométrico

    Returns:
        Cota Z o np.nan si no disponible
    """
    if raster_path is None:
        return np.nan

    try:
        with rasterio.open(raster_path) as src:
            samples = list(src.sample([(point.x, point.y)]))
            z = float(samples[0][0])

            if src.nodata is not None and z == src.nodata:
                return np.nan

            return z
    except:
        return np.nan


def compute_volume_metrics(
    pad_gdf: gpd.GeoDataFrame,
    raster_path: str
) -> Dict:
    """
    Calcula métricas de volumen de movimiento de tierras

    Args:
        pad_gdf: GeoDataFrame con la huella de la plataforma
        raster_path: Ruta al archivo raster MDT

    Returns:
        Dict con z_optimal_m, cut_m3, fill_m3, balance_m3
    """
    if raster_path is None:
        return {
            "z_optimal_m": 0.0,
            "cut_m3": 0.0,
            "fill_m3": 0.0,
            "balance_m3": 0.0
        }

    try:
        with rasterio.open(raster_path) as src:
            if pad_gdf.crs != src.crs:
                pad_gdf = pad_gdf.to_crs(src.crs)

            out_image, out_transform = rasterio.mask.mask(
                src,
                pad_gdf.geometry,
                crop=True,
                filled=False,
                all_touched=True
            )

            if hasattr(out_image, 'mask'):
                out_float = out_image[0].astype(float)
                if hasattr(out_image[0], 'fill_value'):
                    fill_val = float(out_image[0].fill_value)
                    data = np.ma.filled(out_float, fill_value=fill_val)
                    data[data == fill_val] = np.nan
                else:
                    data = np.ma.filled(out_float, fill_value=np.nan)
            else:
                data = out_image[0].astype(float)

            if src.nodata is not None:
                data[data == src.nodata] = np.nan

            z_valid = data[~np.isnan(data)]

            if z_valid.size == 0:
                return {
                    "z_optimal_m": 0.0,
                    "cut_m3": 0.0,
                    "fill_m3": 0.0,
                    "balance_m3": 0.0
                }

            z_opt = float(np.mean(z_valid))
            diff = data - z_opt
            pixel_area = abs(src.transform.a * src.transform.e)
            diff_valid = diff[~np.isnan(diff)]

            cut_m3 = float(np.sum(diff_valid[diff_valid > 0]) * pixel_area)
            fill_m3 = float(np.sum(np.abs(diff_valid[diff_valid < 0])) * pixel_area)

            return {
                "z_optimal_m": z_opt,
                "cut_m3": cut_m3,
                "fill_m3": fill_m3,
                "balance_m3": cut_m3 - fill_m3
            }

    except Exception as e:
        print(f"  ⚠️  Error calculando volúmenes: {e}")
        return {
            "z_optimal_m": 0.0,
            "cut_m3": 0.0,
            "fill_m3": 0.0,
            "balance_m3": 0.0
        }


def calc_pendiente(xs, ys, zs) -> Tuple:
    """
    Calcula pendiente mediante ajuste de plano

    Args:
        xs: Array de coordenadas X
        ys: Array de coordenadas Y
        zs: Array de cotas Z

    Returns:
        Tuple (pendiente_EO_%, pendiente_NS_%, pendiente_total_%, dirección_deg)
    """
    if xs is None or len(xs) < 3:
        return 0.0, 0.0, 0.0, 0.0

    try:
        A = np.c_[xs, ys, np.ones_like(xs)]
        C, *_ = np.linalg.lstsq(A, zs, rcond=None)
        a, b = float(C[0]), float(C[1])
        p_EO = float(a * 100.0)
        p_NS = float(b * 100.0)
        p_tot = float(np.hypot(p_EO, p_NS))
        dir_deg = float(np.degrees(np.arctan2(p_NS, p_EO)))
        return p_EO, p_NS, p_tot, dir_deg
    except:
        return 0.0, 0.0, 0.0, 0.0


def get_xyz_from_pad(
    pad_gdf: gpd.GeoDataFrame,
    raster_path: str
):
    """
    Extrae coordenadas XYZ de todos los puntos de la huella

    Args:
        pad_gdf: GeoDataFrame con la huella
        raster_path: Ruta al raster MDT

    Returns:
        Tuple (xs, ys, zs) como arrays numpy o (None, None, None)
    """
    if raster_path is None:
        return None, None, None

    try:
        pad_geom = unary_union(list(pad_gdf.geometry.values))

        with rasterio.open(raster_path) as src:
            out_image, out_transform = rasterio.mask.mask(
                src,
                [pad_geom],
                crop=True,
                filled=False
            )

            band = out_image[0]
            data = np.ma.filled(band.astype("float32"), np.nan)
            ii, jj = np.where(~np.isnan(data))

            xs, ys, zs = [], [], []
            for i, j in zip(ii, jj):
                x, y = rasterio.transform.xy(out_transform, int(i), int(j))
                if pad_geom.contains(Point(x, y)):
                    xs.append(x)
                    ys.append(y)
                    zs.append(float(data[i, j]))

            return np.array(xs), np.array(ys), np.array(zs)

    except Exception as e:
        print(f"Error XYZ: {e}")
        return None, None, None


def dimensionar_muro_perimetral_real(
    mdt_path: str,
    pad_gdf: gpd.GeoDataFrame,
    parcel_geom,
    cota_plataforma: float,
    paso_perfil: float = 1.0,
    terreno_blando: bool = False,
) -> Dict:
    """
    Dimensiona muro perimetral de contención de forma realista.

    Recorre el perímetro de la plataforma lanzando rayos ortogonales
    hacia el límite de la parcela, muestreando el MDT para calcular
    alturas de muro necesarias.

    Args:
        mdt_path: Ruta al MDT
        pad_gdf: GeoDataFrame con la huella
        parcel_geom: Geometría de la parcela
        cota_plataforma: Cota de la plataforma
        paso_perfil: Distancia entre perfiles (m)
        terreno_blando: Si True, excluye escollera

    Returns:
        Dict con información del muro
    """
    if mdt_path is None:
        return {
            "tipo_muro_elegido": "indeterminado",
            "coste_unit_€_m3": 0.0,
            "total_volumen_m3": 0.0,
            "total_coste_€": 0.0,
            "detalle_lados": [],
            "h_max_global_m": 0.0
        }

    COSTES_MURO = {
        "escollera": {"coste_m3": 180, "h_max": 2.5},
        "bloque": {"coste_m3": 320, "h_max": 3.0},
        "hormigon_armado": {"coste_m3": 450, "h_max": 8.0}
    }

    def espesor_por_altura(h):
        if h < 1.5:
            return 0.30
        elif h < 3.0:
            return 0.50
        else:
            return 0.70

    plataforma_poly = pad_gdf.geometry.iloc[0]

    # Orientación
    if plataforma_poly.exterior.is_ccw:
        normal_sign = 1.0
    else:
        normal_sign = -1.0

    coords = list(plataforma_poly.exterior.coords)
    detalle_perfiles = []
    volumen_total = 0.0
    h_max_global = 0.0

    with rasterio.open(mdt_path) as src:
        from shapely.geometry import LineString
        from shapely.ops import nearest_points

        data_band = src.read(1)

        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i + 1]
            lado = LineString([p1, p2])
            longitud_lado = lado.length
            n_perfiles = max(1, int(math.ceil(longitud_lado / paso_perfil)))

            for k in range(n_perfiles + 1):
                t = min(1.0, k / n_perfiles)
                x = p1[0] + (p2[0] - p1[0]) * t
                y = p1[1] + (p2[1] - p1[1]) * t

                # Vector del lado y normal
                vx, vy = p2[0] - p1[0], p2[1] - p1[1]
                nx, ny = -vy, vx
                long_n = math.hypot(nx, ny)
                if long_n == 0:
                    continue
                nx, ny = nx / long_n, ny / long_n
                nx, ny = normal_sign * nx, normal_sign * ny

                # Rayo hacia fuera
                ray_len = 200.0
                ray = LineString([(x, y), (x + nx * ray_len, y + ny * ray_len)])
                inter = ray.intersection(parcel_geom.boundary)

                if inter.is_empty:
                    continue

                # Punto límite más cercano
                if inter.geom_type == "MultiPoint":
                    dmin = 1e9
                    closest = None
                    for pt in inter.geoms:
                        d = Point(x, y).distance(pt)
                        if d < dmin:
                            dmin = d
                            closest = pt
                    limite_pt = closest
                elif inter.geom_type == "Point":
                    limite_pt = inter
                else:
                    limite_pt = nearest_points(Point(x, y), inter)[1]

                dist_out = Point(x, y).distance(limite_pt)

                if dist_out < 0.2:
                    h_perfil = 0.0
                else:
                    # Muestrear terreno cada 1 m
                    paso_mdt = 1.0
                    n_muestras = max(1, int(math.ceil(dist_out / paso_mdt)))
                    alturas = []

                    for s in range(1, n_muestras + 1):
                        xx = x + nx * (s * paso_mdt)
                        yy = y + ny * (s * paso_mdt)
                        try:
                            row, col = src.index(xx, yy)
                            z_nat = float(data_band[row, col])
                            if src.nodata is not None and z_nat == src.nodata:
                                continue
                            h_local = max(cota_plataforma - z_nat, 0.0)
                            alturas.append(h_local)
                        except Exception:
                            continue

                    h_perfil = max(alturas) if alturas else 0.0

                h_max_global = max(h_max_global, h_perfil)

                esp = espesor_por_altura(h_perfil) if h_perfil > 0 else 0.0
                vol_perfil = h_perfil * esp * paso_perfil
                volumen_total += vol_perfil

                detalle_perfiles.append({
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "dist_hasta_linde_m": round(dist_out, 2),
                    "altura_muro_m": round(h_perfil, 2),
                    "espesor_m": round(esp, 2),
                    "volumen_m3": round(vol_perfil, 3)
                })

    # Elegir tipo de muro
    opciones = []
    for tipo, props in COSTES_MURO.items():
        if terreno_blando and tipo == "escollera":
            continue
        if h_max_global > props["h_max"]:
            continue
        coste_total = volumen_total * props["coste_m3"]
        opciones.append((tipo, coste_total, props["coste_m3"]))

    if not opciones:
        tipo_elegido = "hormigon_armado"
        coste_unit = COSTES_MURO["hormigon_armado"]["coste_m3"]
        coste_total = volumen_total * coste_unit
    else:
        tipo_elegido, coste_total, coste_unit = min(opciones, key=lambda x: x[1])

    return {
        "tipo_muro_elegido": tipo_elegido,
        "coste_unit_€_m3": coste_unit,
        "total_volumen_m3": round(volumen_total, 2),
        "total_coste_€": round(coste_total, 2),
        "detalle_lados": detalle_perfiles,
        "h_max_global_m": round(h_max_global, 2)
    }
