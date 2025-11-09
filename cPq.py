#!/usr/bin/env python3
"""
Buildlovers - Calculadora de Implantación v4.5 Refactorizada
Script principal ejecutable

NOTA: Archivo consolidado. En producción, separar en módulos.
"""

# ==============================================================================
# IMPORTS
# ==============================================================================

import os
import sys
import math
import requests
import numpy as np
import geopandas as gpd
import rasterio
import rasterio.mask
import zipfile
from io import BytesIO
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, MultiPolygon, Point, box, LineString
from shapely.ops import unary_union, nearest_points

# ==============================================================================
# CONFIG
# ==============================================================================

@dataclass
class Config:
    ETRS89_UTM30N = CRS.from_epsg(25830)
    WGS84 = CRS.from_epsg(4326)

    BBOX_BUFFER = 20.0
    SEGMENT_BUFFER = 0.30
    OUTSIDE_RING_WIDTH = 1.20
    NEIGHBOR_EPSILON = 0.20
    AREA_TOLERANCE = 1e-4
    STREET_COMPACT_MAX = 0.30
    STREET_AR_MIN = 2.20
    ROAD_DISTANCE_MAX = 4.0
    ROAD_BUFFER = 6.0

    CATASTRO_WFS_URL = "https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx"
    CATASTRO_TIMEOUT = 60

    MDT_OUTPUT_PATH = "/tmp/mdt.tif"
    MDT_TIMEOUT = 120

    OSM_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    OSM_TIMEOUT = 40
    OSM_HIGHWAY_EXCLUDE = [
        "footway", "path", "cycleway", "bridleway", "steps",
        "proposed", "construction", "corridor", "escalator",
        "platform", "track", "service"
    ]

    # Costes
    COSTE_LOSA_M2 = 180.00
    COSTE_DESMONTE_M3 = 20.50
    COSTE_TERRAPLEN_M3 = 35.00
    COSTE_GESTION_EXCEDENTE_M3 = 15.00
    COSTE_VALLADO_FRONTAL_ML = 110.00
    COSTE_VALLADO_LATERAL_ML = 60.00
    COSTE_PUERTA_ACCESO = 4990.00
    COSTE_PAV_PEATONAL_ML = 50.00
    COSTE_PAV_VEHICULO_ML = 80.00
    COSTE_FIJO_CONEXIONES_REDES = 5500.00
    COSTE_FIJO_HONORARIOS_TECNICOS = 23450.00
    HON_CALC_ESTRUCTURAL = 2600.00
    HON_ESTUDIO_GEOTECNICO = 700.00
    HON_LEV_TOPOGRAFICO = 500.00
    HON_LEGALIZACIONES = 1200.00
    PARKING_ANCHO_M = 2.5
    PARKING_LARGO_M = 5.0
    DEFAULT_INTERES_HIPOTECA = 2.5
    DEFAULT_PLAZO_HIPOTECA_ANOS = 30

    # Normativa
    OCUPACION_PORCENTAJE = 30.0
    EDIFICABILIDAD_M2T_M2S = 0.4
    RETRANQUEO_FRONTAL_M = 5.0
    RETRANQUEO_LATERAL_M = 3.0

    # Matrices
    MATRIZ_CIMENTACION_PENDIENTE = [
        {"max_pendiente": 5, "coste_adicional": 0},
        {"max_pendiente": 10, "coste_adicional": 4500.00},
        {"max_pendiente": 99, "coste_adicional": 9000.00}
    ]

    MATRIZ_COSTE_ACCESO_VERTICAL = [
        {"max_dif_metros": 0.5, "coste_adicional": 0},
        {"max_dif_metros": 1.0, "coste_adicional": 3000.00},
        {"max_dif_metros": 2.0, "coste_adicional": 7500.00},
        {"max_dif_metros": 99, "coste_adicional": 14000.00}
    ]

CFG = Config()

# ==============================================================================
# MODELOS
# ==============================================================================

MODELS_DATABASE = [
    {"model_id":"BL_1D1P_01","nombre":"1D Lineal 45","numero_dormitorios":1,"numero_baños":1,"plantas":1,"superficie_m2":45,"huella_ancho_m":7.5,"huella_largo_m":6.0,"maqueta_ref_id":"MAQ_1D1P_01"},
    {"model_id":"BL_2D1P_01","nombre":"2D Compacto 70","numero_dormitorios":2,"numero_baños":1,"plantas":1,"superficie_m2":70,"huella_ancho_m":9.0,"huella_largo_m":7.8,"maqueta_ref_id":"MAQ_2D1P_01"},
    {"model_id":"BL_3D1P_01","nombre":"3D Lineal 100","numero_dormitorios":3,"numero_baños":2,"plantas":1,"superficie_m2":100,"huella_ancho_m":12.0,"huella_largo_m":8.5,"maqueta_ref_id":"MAQ_3D1P_01"},
    {"model_id":"BL_3D2P_01","nombre":"3D Duplex 118","numero_dormitorios":3,"numero_baños":3,"plantas":2,"superficie_m2":118,"huella_ancho_m":8.6,"huella_largo_m":7.0,"maqueta_ref_id":"MAQ_3D2P_01"},
    {"model_id":"BL_4D1P_01","nombre":"4D Lineal 130","numero_dormitorios":4,"numero_baños":3,"plantas":1,"superficie_m2":130,"huella_ancho_m":15.0,"huella_largo_m":9.0,"maqueta_ref_id":"MAQ_4D1P_01"},
    {"model_id":"BL_5D2P_01","nombre":"5D Duplex 190","numero_dormitorios":5,"numero_baños":4,"plantas":2,"superficie_m2":190,"huella_ancho_m":11.0,"huella_largo_m":9.0,"maqueta_ref_id":"MAQ_5D2P_01"},
]

# ==============================================================================
# PRECIOS
# ==============================================================================

CONSTRUCTION_PRICES = {
    "steelframe": {"essencial": 1340, "premium": 1530, "excellence": 1750},
    "madera": {"essencial": 1450, "premium": 1600, "excellence": 1750},
    "hormigon": {"essencial": 1650, "premium": 1700, "excellence": 1850}
}

EXTRAS_CATALOG = {
    "piscina_6x3": {"label": "Piscina 6x3 m (clorada)", "type": "fixed", "price": 21000.0, "group": "piscina"},
    "piscina_8x4": {"label": "Piscina 8x4 m (clorada)", "type": "fixed", "price": 32000.0, "group": "piscina"},
    "pergola_2c": {"label": "Pérgola 2 coches", "type": "fixed", "price": 4500.0, "group": None},
    "porche_20m2": {"label": "Porche 20 m²", "type": "fixed", "price": 7800.0, "group": None},
    "pv_3kw": {"label": "Placas fotovoltaicas 3 kW", "type": "fixed", "price": 5700.0, "group": None},
    "pv_5kw": {"label": "Placas fotovoltaicas 5 kW", "type": "fixed", "price": 8900.0, "group": None},
    "punto_ev": {"label": "Punto de carga vehículo eléctrico", "type": "fixed", "price": 1200.0, "group": None},
    "domotica_basic": {"label": "Domótica básica", "type": "fixed", "price": 1500.0, "group": None},
    "arboles": {"label": "Arbolado ornamental (unidad)", "type": "unit", "unit_price": 180.0, "group": None},
}

# ==============================================================================
# SERVICIOS GIS
# ==============================================================================

class CatastroService:
    def get_parcel_geometry(self, refcat14: str) -> Optional[gpd.GeoDataFrame]:
        print(f"[Catastro] Obteniendo parcela {refcat14}...")
        params = {
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "STOREDQUERY_ID": "GetParcel", "refcat": refcat14, "SRSNAME": "EPSG:25830"
        }
        try:
            r = requests.get(CFG.CATASTRO_WFS_URL, params=params, timeout=CFG.CATASTRO_TIMEOUT)
            r.raise_for_status()
            if len(r.content) < 1000 or "Exception" in r.text:
                return None
            gdf = gpd.read_file(BytesIO(r.content))
            if gdf.empty:
                return None
            if gdf.crs is None:
                gdf.set_crs(epsg=25830, inplace=True)
            elif gdf.crs != CFG.ETRS89_UTM30N:
                gdf = gdf.to_crs(CFG.ETRS89_UTM30N)
            gdf = gdf[gdf.is_valid]
            return gdf.iloc[[0]].copy() if not gdf.empty else None
        except Exception as e:
            print(f"[Catastro] Error: {e}")
            return None

    def get_neighbor_parcels(self, refcat14: str) -> Optional[gpd.GeoDataFrame]:
        print(f"[Catastro] Obteniendo vecinos...")
        params = {
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "STOREDQUERY_ID": "GetNeighbourParcel", "REFCAT": refcat14, "SRSNAME": "EPSG:25830"
        }
        try:
            r = requests.get(CFG.CATASTRO_WFS_URL, params=params, timeout=CFG.CATASTRO_TIMEOUT)
            if r.status_code != 200 or len(r.content) < 1000:
                return None
            gdf = gpd.read_file(BytesIO(r.content))
            if gdf.empty:
                return None
            if gdf.crs != CFG.ETRS89_UTM30N:
                gdf = gdf.to_crs(CFG.ETRS89_UTM30N)
            return gdf
        except Exception as e:
            print(f"[Catastro] Error vecinos: {e}")
            return None


class MDTService:
    """
    Descarga MDT probando (en este orden):
    1) MDT02 (2 m) desde el catálogo de descargas del CNIG (GeoJSON de índice → ZIP/TIF)
    2) MDT02 (2 m) vía WCS, si existiera
    3) MDT05 (5 m) vía WCS
    4) MDT25 (25 m) vía WCS
    5) Servicio antiguo
    """
    MDT02_INDEX_URL = "https://centrodedescargas.cnig.es/CentroDescargas/geojson/MDT02_ETRS89.geojson"

    def _expand_bbox(self, bbox: Tuple[float, float, float, float], extra: float):
        minx, miny, maxx, maxy = bbox
        return (minx - extra, miny - extra, maxx + extra, maxy + extra)

    def _download_mdt02_from_index(self, bbox: Tuple[float, float, float, float], out_dir: str = "/tmp/mdt02") -> Optional[str]:
        try:
            os.makedirs(out_dir, exist_ok=True)
            idx_gdf = gpd.read_file(self.MDT02_INDEX_URL)
            if idx_gdf.crs is None:
                idx_gdf.set_crs(epsg=25830, inplace=True)
            else:
                idx_gdf = idx_gdf.to_crs(25830)

            minx, miny, maxx, maxy = map(float, bbox)
            bbox_poly = box(minx, miny, maxx, maxy)
            hits = idx_gdf[idx_gdf.intersects(bbox_poly)]
            if hits.empty:
                print("[MDT] MDT02 índice: ninguna hoja intersecta el bbox")
                return None

            row = hits.iloc[0]
            download_url = None
            for field in ["link", "enlace", "url", "download"]:
                if field in hits.columns and isinstance(row[field], str):
                    download_url = row[field]
                    break

            if not download_url:
                print("[MDT] MDT02 índice: no se encontró campo de descarga en el GeoJSON")
                return None

            local_path = os.path.join(out_dir, os.path.basename(download_url))
            print(f"[MDT] Descargando MDT02 por índice: {download_url}")
            r = requests.get(download_url, stream=True, timeout=CFG.MDT_TIMEOUT)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            if local_path.lower().endswith(".zip"):
                with zipfile.ZipFile(local_path, "r") as zf:
                    zf.extractall(out_dir)
                for fn in os.listdir(out_dir):
                    if fn.lower().endswith(".tif"):
                        tif_path = os.path.join(out_dir, fn)
                        print(f"[MDT] MDT02 por índice OK → {tif_path}")
                        return tif_path
                print("[MDT] MDT02 por índice: ZIP descargado pero sin .tif dentro")
                return None
            else:
                print(f"[MDT] MDT02 por índice OK → {local_path}")
                return local_path

        except Exception as e:
            print(f"[MDT] MDT02 por índice falló: {e}")
            return None

    def _try_download_for_bbox(self, bbox: Tuple[float, float, float, float]) -> Optional[str]:
        minx, miny, maxx, maxy = map(float, bbox)
        attempts = [
            ("https://servicios.idee.es/wcs-inspire/mdt02", [
                ("SERVICE","WCS"), ("VERSION","2.0.1"), ("REQUEST","GetCoverage"),
                ("COVERAGEID","Elevacion25830_2"),
                ("FORMAT","image/tiff"),
                ("SUBSETTINGCRS","EPSG:25830"),
                ("SUBSET", f"x({minx},{maxx})"),
                ("SUBSET", f"y({miny},{maxy})"),
            ]),
            ("https://servicios.idee.es/wcs-inspire/mdt", [
                ("SERVICE","WCS"), ("VERSION","2.0.1"), ("REQUEST","GetCoverage"),
                ("COVERAGEID","Elevacion25830_5"),
                ("FORMAT","image/tiff"),
                ("SUBSETTINGCRS","EPSG:25830"),
                ("SUBSET", f"x({minx},{maxx})"),
                ("SUBSET", f"y({miny},{maxy})"),
            ]),
            ("https://servicios.idee.es/wcs-inspire/mdt", [
                ("SERVICE","WCS"), ("VERSION","2.0.1"), ("REQUEST","GetCoverage"),
                ("COVERAGEID","Elevacion25830_25"),
                ("FORMAT","image/tiff"),
                ("SUBSETTINGCRS","EPSG:25830"),
                ("SUBSET", f"x({minx},{maxx})"),
                ("SUBSET", f"y({miny},{maxy})"),
            ]),
            ("https://www.ign.es/wcs/mdt", {
                "SERVICE": "WCS",
                "VERSION": "1.0.0",
                "REQUEST": "GetCoverage",
                "COVERAGE": "mdt:Elevacion25830_25",
                "CRS": "EPSG:25830",
                "BBOX": f"{minx},{miny},{maxx},{maxy}",
                "WIDTH": "200",
                "HEIGHT": "200",
                "FORMAT": "GeoTIFF",
            })
        ]

        for url, params in attempts:
            try:
                r = requests.get(url, params=params, timeout=CFG.MDT_TIMEOUT)
                ct = r.headers.get("Content-Type","").lower()
                head4 = r.content[:4]
                is_tiff = ct.endswith("tiff") or head4 in (b"II*\x00", b"MM\x00*")
                if r.status_code == 200 and is_tiff and len(r.content) > 1000:
                    with open(CFG.MDT_OUTPUT_PATH, "wb") as f:
                        f.write(r.content)
                    print(f"[MDT] ✓ Descargado MDT vía WCS desde {url}")
                    return CFG.MDT_OUTPUT_PATH
                else:
                    print(f"[MDT] ✗ {url} no devolvió un TIFF válido")
            except Exception as e:
                print(f"[MDT] ✗ Error con {url}: {e}")

        return None

    def download_mdt(self, bbox: Tuple[float, float, float, float]) -> Optional[str]:
        print("[MDT] Solicitando topografía (prioridad MDT02 por índice)…")
        path = self._download_mdt02_from_index(bbox)
        if path:
            return path
        print("[MDT] Pasando a WCS (2 m → 5 m → 25 m)…")
        path = self._try_download_for_bbox(bbox)
        if path:
            return path
        bbox_big = self._expand_bbox(bbox, 25.0)
        print("[MDT] Reintentando WCS con bbox +25 m…")
        path = self._try_download_for_bbox(bbox_big)
        if path:
            return path
        bbox_bigger = self._expand_bbox(bbox, 50.0)
        print("[MDT] Reintentando WCS con bbox +50 m…")
        path = self._try_download_for_bbox(bbox_bigger)
        if path:
            return path
        print("[MDT] ✗ No se pudo descargar ningún MDT")
        return None


class OSMService:
    def fetch_roads(self, bbox: Tuple) -> gpd.GeoDataFrame:
        print("[OSM] Consultando red viaria...")
        try:
            minx, miny, maxx, maxy = bbox
            to_wgs84 = Transformer.from_crs(CFG.ETRS89_UTM30N, CFG.WGS84, always_xy=True)
            west, south = to_wgs84.transform(minx, miny)
            east, north = to_wgs84.transform(maxx, maxy)
            if west > east:
                west, east = east, west
            if south > north:
                south, north = north, south

            exclude = "|".join(CFG.OSM_HIGHWAY_EXCLUDE)
            query = f"""[out:json][timeout:{CFG.OSM_TIMEOUT}];
            (way["highway"]["highway"!~"{exclude}"]({south},{west},{north},{east}););
            out geom;"""

            r = requests.post(CFG.OSM_OVERPASS_URL, data={"data": query}, timeout=CFG.OSM_TIMEOUT + 10)
            r.raise_for_status()
            data = r.json()

            lines = []
            to_utm = Transformer.from_crs(CFG.WGS84, CFG.ETRS89_UTM30N, always_xy=True)
            for el in data.get("elements", []):
                if el.get("type") != "way":
                    continue
                geom = el.get("geometry", [])
                if not geom:
                    continue
                coords_utm = []
                for p in geom:
                    x, y = to_utm.transform(p["lon"], p["lat"])
                    coords_utm.append((x, y))
                if len(coords_utm) >= 2:
                    lines.append(LineString(coords_utm))

            if not lines:
                return gpd.GeoDataFrame(geometry=[], crs=CFG.ETRS89_UTM30N)
            print(f"[OSM] {len(lines)} segmentos")
            return gpd.GeoDataFrame({"geometry": lines}, crs=CFG.ETRS89_UTM30N)
        except Exception as e:
            print(f"[OSM] Error: {e}")
            return gpd.GeoDataFrame(geometry=[], crs=CFG.ETRS89_UTM30N)

# ==============================================================================
# UTILIDADES RASTER
# ==============================================================================

def get_z_at_point(raster_path: str, point: Point) -> float:
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


def compute_volume_metrics(pad_gdf: gpd.GeoDataFrame, raster_path: str) -> Dict:
    if raster_path is None:
        return {"z_optimal_m": 0.0, "cut_m3": 0.0, "fill_m3": 0.0, "balance_m3": 0.0}
    try:
        with rasterio.open(raster_path) as src:
            if pad_gdf.crs != src.crs:
                pad_gdf = pad_gdf.to_crs(src.crs)
            out_image, out_transform = rasterio.mask.mask(
                src, pad_gdf.geometry, crop=True, filled=False, all_touched=True
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
                return {"z_optimal_m": 0.0, "cut_m3": 0.0, "fill_m3": 0.0, "balance_m3": 0.0}
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
        return {"z_optimal_m": 0.0, "cut_m3": 0.0, "fill_m3": 0.0, "balance_m3": 0.0}


def calc_pendiente(xs, ys, zs) -> Tuple:
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


def get_xyz_from_pad(pad_gdf: gpd.GeoDataFrame, raster_path: str):
    if raster_path is None:
        return None, None, None
    try:
        pad_geom = unary_union(list(pad_gdf.geometry.values))
        with rasterio.open(raster_path) as src:
            out_image, out_transform = rasterio.mask.mask(src, [pad_geom], crop=True, filled=False)
            band = out_image[0]
            data = np.ma.filled(band.astype("float32"), np.nan)
            ii, jj = np.where(~np.isnan(data))
            xs, ys, zs = [], [], []
            for i, j in zip(ii, jj):
                x, y = rasterio.transform.xy(out_transform, int(i), int(j))
                if pad_geom.contains(Point(x, y)):
                    xs.append(x); ys.append(y); zs.append(float(data[i, j]))
            return np.array(xs), np.array(ys), np.array(zs)
    except Exception as e:
        print(f"Error XYZ: {e}")
        return None, None, None


def dimensionar_muro_unico_tipo_from_pad(
    mdt_path: str,
    pad_gdf: gpd.GeoDataFrame,
    cota_plataforma: float,
    terreno_blando: bool = False,
    offset_muro: float = 1.5,
    paso_muestreo_lado: float = 1.0,
    offsets_fuera: List[float] = None,
):
    """
    Dimensiona un único tipo de muro alrededor de la huella.
    Para MDT grueso, muestrea varias distancias hacia fuera y ajusta una pendiente local.
    """
    import math
    import rasterio

    if offsets_fuera is None:
        # distancias crecientes hacia fuera para pillar alguna celda que cambie
        offsets_fuera = [1.5, 3.0, 4.5, 6.0, 8.0, 10.0]

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

    # 1) asegurar orientación
    if plataforma_poly.exterior.is_ccw:
        normal_sign = 1.0
    else:
        normal_sign = -1.0

    lados_data = []

    with rasterio.open(mdt_path) as src:
        data_band = src.read(1)
        coords = list(plataforma_poly.exterior.coords)

        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i + 1]
            lado = LineString([p1, p2])
            longitud = lado.length

            n_muestras = max(1, int(math.ceil(longitud / paso_muestreo_lado)))
            alturas_punto = []

            for k in range(n_muestras + 1):
                t = min(1.0, k / n_muestras)
                x = p1[0] + (p2[0] - p1[0]) * t
                y = p1[1] + (p2[1] - p1[1]) * t

                # vector y normal
                vx, vy = p2[0] - p1[0], p2[1] - p1[1]
                nx, ny = -vy, vx
                long_n = math.hypot(nx, ny)
                if long_n == 0:
                    continue
                nx, ny = nx / long_n, ny / long_n

                # 2) muestrear varias distancias hacia fuera
                distancias_validas = []
                cotas_validas = []
                for d in offsets_fuera:
                    xx = x + normal_sign * nx * d
                    yy = y + normal_sign * ny * d
                    try:
                        row, col = src.index(xx, yy)
                        cota_nat = float(data_band[row, col])
                        # nodata → ignorar
                        if src.nodata is not None and cota_nat == src.nodata:
                            continue
                        distancias_validas.append(d)
                        cotas_validas.append(cota_nat)
                    except Exception:
                        # punto fuera del raster → lo ignoramos
                        continue

                if not distancias_validas:
                    # no tenemos info fuera → asumimos mismo nivel que plataforma
                    h_punto = 0.0
                else:
                    # 3) ajustar pendiente 1D distancia–cota
                    if len(distancias_validas) == 1:
                        cota_estimada_en_offset_muro = cotas_validas[0]
                    else:
                        D = np.array(distancias_validas, dtype=float)
                        Z = np.array(cotas_validas, dtype=float)
                        A = np.c_[D, np.ones_like(D)]
                        sol, _, _, _ = np.linalg.lstsq(A, Z, rcond=None)
                        a, b = sol[0], sol[1]
                        cota_estimada_en_offset_muro = a * offset_muro + b

                    h_punto = max(cota_plataforma - cota_estimada_en_offset_muro, 0.0)

                alturas_punto.append(h_punto)

            if alturas_punto:
                h_media = sum(alturas_punto) / len(alturas_punto)
                h_max = max(alturas_punto)
            else:
                h_media = 0.0
                h_max = 0.0

            e = espesor_por_altura(h_media) if h_media > 0 else 0.0
            volumen = longitud * h_media * e

            lados_data.append({
                "lado": i + 1,
                "longitud_m": longitud,
                "altura_media_m": h_media,
                "altura_max_m": h_max,
                "espesor_m": e,
                "volumen_m3": volumen
            })

    # elegir un único tipo válido
    h_max_global = max((l["altura_max_m"] for l in lados_data), default=0.0)
    opciones = []
    for tipo, props in COSTES_MURO.items():
        if terreno_blando and tipo == "escollera":
            continue
        if h_max_global > props["h_max"]:
            continue
        coste_unit = props["coste_m3"]
        coste_total = sum(l["volumen_m3"] * coste_unit for l in lados_data)
        opciones.append((tipo, coste_total, coste_unit))

    if not opciones:
        tipo_elegido = "hormigon_armado"
        coste_unit = COSTES_MURO["hormigon_armado"]["coste_m3"]
        coste_total = sum(l["volumen_m3"] * coste_unit for l in lados_data)
    else:
        tipo_elegido, coste_total, coste_unit = min(opciones, key=lambda x: x[1])

    detalle_lados = []
    for l in lados_data:
        detalle_lados.append({
            "lado": l["lado"],
            "longitud_m": round(l["longitud_m"], 2),
            "altura_media_m": round(l["altura_media_m"], 2),
            "altura_max_m": round(l["altura_max_m"], 2),
            "espesor_m": round(l["espesor_m"], 2),
            "volumen_m3": round(l["volumen_m3"], 2),
            "tipo_muro": tipo_elegido,
            "coste_unit_€_m3": coste_unit,
            "coste_€": round(l["volumen_m3"] * coste_unit, 2)
        })

    total_volumen = sum(l["volumen_m3"] for l in lados_data)

    return {
        "tipo_muro_elegido": tipo_elegido,
        "coste_unit_€_m3": coste_unit,
        "total_volumen_m3": round(total_volumen, 2),
        "total_coste_€": round(coste_total, 2),
        "detalle_lados": detalle_lados,
        "h_max_global_m": round(h_max_global, 2)
    }

# ======================================================================
# NUEVA FUNCIÓN: dimensionar_muro_perimetral_real
# ======================================================================

def dimensionar_muro_perimetral_real(
    mdt_path: str,
    pad_gdf: gpd.GeoDataFrame,
    parcel_geom,
    cota_plataforma: float,
    paso_perfil: float = 1.0,
    terreno_blando: bool = False,
):
    """
    Versión más "real":
    - Recorre el perímetro de la plataforma cada `paso_perfil` metros
    - Desde cada punto lanza un rayo ortogonal hacia fuera hasta el límite de la parcela
    - Muestra el MDT cada 1 m (o menos) en ese rayo
    - Toma la altura máxima que encuentra (plataforma - terreno)
    - Calcula volumen = h * espesor(h) * paso_perfil
    - Al final elige un único tipo de muro que valga para todas las alturas
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

    # orientación de la plataforma para saber hacia dónde es "fuera"
    if plataforma_poly.exterior.is_ccw:
        normal_sign = 1.0
    else:
        normal_sign = -1.0

    coords = list(plataforma_poly.exterior.coords)
    detalle_perfiles = []
    volumen_total = 0.0
    h_max_global = 0.0

    with rasterio.open(mdt_path) as src:
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

                # vector del lado y normal
                vx, vy = p2[0] - p1[0], p2[1] - p1[1]
                nx, ny = -vy, vx
                long_n = math.hypot(nx, ny)
                if long_n == 0:
                    continue
                nx, ny = nx / long_n, ny / long_n
                nx, ny = normal_sign * nx, normal_sign * ny

                # rayo hacia fuera (suficientemente largo)
                ray_len = 200.0
                ray = LineString([(x, y), (x + nx * ray_len, y + ny * ray_len)])
                inter = ray.intersection(parcel_geom.boundary)

                if inter.is_empty:
                    # no hemos encontrado límite dentro de 200 m → no se calcula
                    continue

                # la intersección puede ser multipunto, cogemos el más cercano
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
                    # por si es una LineString corta, cogemos el punto más cercano
                    limite_pt = nearest_points(Point(x, y), inter)[1]

                dist_out = Point(x, y).distance(limite_pt)
                if dist_out < 0.2:
                    # muy pegado al límite, no hay muro
                    h_perfil = 0.0
                else:
                    # muestrear terreno cada 1 m hasta el límite
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
                                # si no hay dato, lo saltamos
                                continue
                            h_local = max(cota_plataforma - z_nat, 0.0)
                            alturas.append(h_local)
                        except Exception:
                            # fuera de raster
                            continue

                    if alturas:
                        h_perfil = max(alturas)
                    else:
                        h_perfil = 0.0

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

    # elegir tipo de muro que pueda con la altura máxima
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

# ==============================================================================
# ANALIZADOR DE LÍMITES
# ==============================================================================

@dataclass
class ParcelAnalysisResult:
    fence_cost: float
    buildable_geometry: Optional[Polygon]
    frontal_length_m: float
    lateral_length_m: float
    access_point: Point


class ParcelBoundaryAnalyzer:
    """Analizador de límites v4.4/4.5"""

    def __init__(self, catastro_svc, osm_svc):
        self.catastro = catastro_svc
        self.osm = osm_svc

    def analyze(self, parcel_gdf, refcat14, bbox) -> ParcelAnalysisResult:
        print("\n--- Analizando Límites ---")
        parcel_geom = parcel_gdf.geometry.iloc[0]
        polys = [parcel_geom] if parcel_geom.geom_type == 'Polygon' else list(parcel_geom.geoms)
        total_perim = parcel_geom.length

        # Vecinos
        gdf_nei = self.catastro.get_neighbor_parcels(refcat14)
        merged_priv, merged_pub = self._classify_neighbors(gdf_nei, refcat14)

        if merged_priv is None or merged_priv.is_empty:
            return self._all_frontal(parcel_geom, total_perim)

        # Street zone
        street_zone = self._detect_street_zone(merged_pub, parcel_geom)

        # Zonas
        outside_ring = parcel_geom.buffer(CFG.OUTSIDE_RING_WIDTH, join_style=2).difference(parcel_geom.buffer(0, join_style=2))
        priv_out = self._safe_int(outside_ring, merged_priv, CFG.NEIGHBOR_EPSILON)
        pub_cat_out = self._safe_int(outside_ring, street_zone, CFG.NEIGHBOR_EPSILON) if street_zone else None

        # OSM
        pub_osm_out = self._fetch_osm_zone(bbox, outside_ring)

        # Clasificar
        front_segs, lat_segs, stats = self._classify_segments(polys, pub_cat_out, pub_osm_out, priv_out)

        front_len = unary_union(front_segs).length if front_segs else 0.0
        lat_len = unary_union(lat_segs).length if lat_segs else 0.0

        if (front_len + lat_len) > total_perim * 0.995:
            lat_len = max(0.0, total_perim - front_len)

        # Rescate
        if front_len < 0.05 and (pub_osm_out or merged_pub):
            print("RESCATE aplicado")
            front_segs, lat_segs = self._rescue(stats)
            front_len = unary_union(front_segs).length if front_segs else 0.0
            lat_len = unary_union(lat_segs).length if lat_segs else 0.0
            if (front_len + lat_len) > total_perim * 0.995:
                lat_len = max(0.0, total_perim - front_len)

        fence_cost = self._fence_cost(front_len, lat_len)
        access_pt = self._access_point(parcel_geom, front_segs)
        buildable = self._buildable(parcel_geom, front_segs)

        print(f"Vallado: {front_len:.2f} ml frontal, {lat_len:.2f} ml lateral = {fence_cost:,.2f} €")

        return ParcelAnalysisResult(fence_cost, buildable, front_len, lat_len, access_pt)

    def _classify_neighbors(self, gdf_nei, refcat14):
        if gdf_nei is None or gdf_nei.empty:
            return None, None
        id_col = 'localId' if 'localId' in gdf_nei.columns else ('label' if 'label' in gdf_nei.columns else None)
        if id_col is None:
            return unary_union(gdf_nei.geometry).buffer(0), None
        gdf_nei = gdf_nei[gdf_nei[id_col].astype(str) != str(refcat14)]
        priv = gdf_nei[gdf_nei[id_col].notna()]
        pub = gdf_nei[gdf_nei[id_col].isna()]
        mp = unary_union(priv.geometry).buffer(0) if not priv.empty else None
        mu = unary_union(pub.geometry).buffer(0) if not pub.empty else None
        return mp, mu

    def _detect_street_zone(self, merged_pub, parcel_geom):
        if merged_pub is None or merged_pub.is_empty:
            return None
        pubs = [merged_pub] if merged_pub.geom_type == 'Polygon' else list(merged_pub.geoms)
        boundary_buf = parcel_geom.boundary.buffer(0.10)
        best_len, best_poly = -1.0, None
        for p in pubs:
            if not p.intersects(boundary_buf):
                continue
            A, P = p.area, p.length if hasattr(p, "length") else p.boundary.length
            compact = (4.0 * math.pi * A) / (P * P) if P > 0 else 0.0
            try:
                mbr = p.minimum_rotated_rectangle
                coords = list(mbr.exterior.coords)
                edges = [LineString([coords[i], coords[i+1]]) for i in range(4)]
                lens = sorted([e.length for e in edges], reverse=True)
                ar = float('inf') if lens[1] == 0 else lens[0] / lens[1]
            except:
                ar = 1.0
            if not (compact <= CFG.STREET_COMPACT_MAX or ar >= CFG.STREET_AR_MIN):
                continue
            shared = boundary_buf.intersection(p.boundary.buffer(0.10)).length
            if shared > best_len:
                best_len, best_poly = shared, p
        if best_poly:
            print(f"Street zone detectada (shared≈{best_len:.2f} m)")
            return best_poly.buffer(0.60)
        return None

    def _safe_int(self, g1, g2, eps):
        if g2 is None or g2.is_empty:
            return None
        result = g1.intersection(g2.buffer(eps))
        return result.buffer(0) if not result.is_empty else None

    def _fetch_osm_zone(self, bbox, outside_ring):
        try:
            gdf_roads = self.osm.fetch_roads(bbox)
            if gdf_roads.empty:
                return None
            roads_buf = unary_union(gdf_roads.buffer(CFG.ROAD_BUFFER, cap_style=2, join_style=2))
            pub_osm = outside_ring.intersection(roads_buf.buffer(CFG.NEIGHBOR_EPSILON))
            return pub_osm.buffer(0) if not pub_osm.is_empty else None
        except:
            return None

    def _classify_segments(self, polys, pub_cat, pub_osm, priv):
        front, lat, stats = [], [], []
        for poly in polys:
            coords = list(poly.exterior.coords)
            for i in range(len(coords) - 1):
                seg = LineString([coords[i], coords[i+1]])
                if seg.length <= 1e-6:
                    continue
                seg_buf = seg.buffer(CFG.SEGMENT_BUFFER, cap_style=2, join_style=2)
                area_cat = self._int_area(seg_buf, pub_cat)
                area_osm = self._int_area(seg_buf, pub_osm)
                area_priv = self._int_area(seg_buf, priv)
                decided = False
                if area_osm > max(area_cat, area_priv) + CFG.AREA_TOLERANCE:
                    front.append(seg)
                    decided = True
                elif area_cat > max(area_osm, area_priv) + CFG.AREA_TOLERANCE:
                    front.append(seg)
                    decided = True
                else:
                    if pub_osm and not pub_osm.is_empty:
                        c = seg_buf.representative_point()
                        d = c.distance(pub_osm.boundary)
                        if d <= CFG.ROAD_DISTANCE_MAX:
                            front.append(seg)
                            decided = True
                if not decided:
                    lat.append(seg)
                cpt = seg_buf.representative_point()
                d_osm_c = cpt.distance(pub_osm) if pub_osm else float('inf')
                d_cat_c = cpt.distance(pub_cat) if pub_cat else float('inf')
                score = 1.0 * area_osm + 0.7 * area_cat + 0.25 / (d_osm_c + 0.1) + 0.10 / (d_cat_c + 0.1)
                stats.append((seg, score, area_osm, area_cat, area_priv))
        return front, lat, stats

    def _int_area(self, g1, g2):
        if g2 is None or g2.is_empty:
            return 0.0
        inter = g1.intersection(g2)
        return inter.area if not inter.is_empty else 0.0

    def _rescue(self, stats):
        ranked = sorted(stats, key=lambda t: t[1], reverse=True)
        if not ranked:
            return [], []
        max_score = ranked[0][1]
        thr = max_score * 0.50
        cands = [t[0] for t in ranked if t[1] >= thr]
        if len(cands) == 1:
            rescue_front = cands[0]
        else:
            ru = unary_union(cands)
            rescue_front = ru if ru.geom_type == "LineString" else sorted(list(ru.geoms), key=lambda s: s.length, reverse=True)[0]
        new_front = [seg for seg, *_ in stats if seg.buffer(1e-6).intersects(rescue_front.buffer(1e-6))]
        new_lat = [seg for seg, *_ in stats if not seg.buffer(1e-6).intersects(rescue_front.buffer(1e-6))]
        return new_front, new_lat

    def _fence_cost(self, front_ml, lat_ml):
        GATE_ML = 4.0
        front_ml_facturable = max(front_ml - GATE_ML, 0.0)
        cost = front_ml_facturable * CFG.COSTE_VALLADO_FRONTAL_ML + lat_ml * CFG.COSTE_VALLADO_LATERAL_ML
        return float(cost)

    def _access_point(self, parcel_geom, front_segs):
        try:
            if front_segs:
                seg_longest = max(front_segs, key=lambda s: s.length)
                return seg_longest.interpolate(0.5, normalized=True)
            return parcel_geom.representative_point()
        except:
            return parcel_geom.representative_point()

    def _buildable(self, parcel_geom, front_segs):
        try:
            r_lat = CFG.RETRANQUEO_LATERAL_M
            r_fro = CFG.RETRANQUEO_FRONTAL_M
            buildable = parcel_geom.buffer(-r_lat, join_style=2)
            r_extra = max(0.0, r_fro - r_lat)
            if r_extra > 0 and front_segs:
                frontal_union = unary_union(front_segs)
                frontal_corridor = frontal_union.buffer(r_extra, join_style=2)
                buildable = buildable.difference(frontal_corridor)
            if buildable.is_empty or not buildable.is_valid:
                print("Advertencia: Caja edificable vacía")
                return None
            print(f"Caja Edificable: {buildable.area:,.2f} m²")
            return buildable
        except Exception as e:
            print(f"Error caja edificable: {e}")
            return None

    def _all_frontal(self, parcel_geom, total_perim):
        fence_cost = self._fence_cost(total_perim, 0.0)
        buildable = parcel_geom.buffer(-CFG.RETRANQUEO_FRONTAL_M, join_style=2)
        access_pt = parcel_geom.representative_point()
        return ParcelAnalysisResult(fence_cost, buildable, total_perim, 0.0, access_pt)

# ==============================================================================
# AUX
# ==============================================================================

def safe_float(value, default=0.0):
    try:
        if hasattr(value, '__len__') and len(value) == 1:
            value = value[0]
        if hasattr(value, '__array__'):
            if np.isnan(value).any():
                return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError, AttributeError):
        return default

def bbox_from_gdf(gdf, buffer=20.0):
    minx, miny, maxx, maxy = gdf.total_bounds
    return (minx - buffer, miny - buffer, maxx + buffer, maxy + buffer)

def create_house_pad(buildable_gdf, width_m, length_m):
    try:
        if buildable_gdf.crs != CFG.ETRS89_UTM30N:
            buildable_gdf = buildable_gdf.to_crs(CFG.ETRS89_UTM30N)
        geom = buildable_gdf.geometry.iloc[0]
        centroid = geom.centroid
        cx, cy = centroid.x, centroid.y
        half_w, half_l = width_m / 2, length_m / 2
        pad_polygon = box(cx - half_w, cy - half_l, cx + half_w, cy + half_l)
        pad_gdf = gpd.GeoDataFrame([{"geometry": pad_polygon}], crs=CFG.ETRS89_UTM30N)
        return pad_gdf
    except Exception as e:
        print(f"Error creando huella: {e}")
        return None

def compute_horizontal_access_costs(access_point, huella_gdf):
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

def compute_vertical_access_costs(access_point, p_parking, mdt_path):
    try:
        if mdt_path is None:
            return 0.0, 0.0
        z_calle = get_z_at_point(mdt_path, access_point)
        z_parking = get_z_at_point(mdt_path, p_parking if p_parking else access_point)
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

def compute_monthly_payment(principal, annual_rate, years):
    try:
        principal = float(principal)
        annual_rate = float(annual_rate)
        years = int(years)
    except (ValueError, TypeError):
        return 0.0
    if principal <= 0:
        return 0.0
    n = years * 12
    r = (annual_rate / 100.0) / 12.0
    if r == 0:
        return round(principal / n, 2)
    factor = (1 + r) ** n
    denom = factor - 1
    if denom == 0:
        return 0.0
    monthly = principal * (r * factor) / denom
    monthly = float(monthly)
    if math.isnan(monthly) or math.isinf(monthly):
        return 0.0
    return round(monthly, 2)

# ==============================================================================
# FILTRO DE MODELOS
# ==============================================================================

def filter_valid_models(num_bedrooms, parcel_area_m2, buildable_area_m2):
    print("\n==========================================================")
    print("--- Pre-Filtrado Inteligente (RF-1.1.d) ---")
    models_by_bedrooms = [m for m in MODELS_DATABASE if m['numero_dormitorios'] == num_bedrooms]
    if not models_by_bedrooms:
        print(f"Error: No hay modelos de {num_bedrooms} dormitorios")
        return []
    print(f"Encontrados {len(models_by_bedrooms)} modelos de {num_bedrooms} dormitorios")
    parking_area = CFG.PARKING_ANCHO_M * CFG.PARKING_LARGO_M
    max_edif = parcel_area_m2 * CFG.EDIFICABILIDAD_M2T_M2S
    max_ocup = parcel_area_m2 * (CFG.OCUPACION_PORCENTAJE / 100.0)
    print(f"\nDatos de Parcela:")
    print(f"  -> Superficie: {parcel_area_m2:,.2f} m²")
    print(f"  -> Max Edificabilidad: {max_edif:,.2f} m²t")
    print(f"  -> Max Ocupación: {max_ocup:,.2f} m²")
    print(f"  -> Área Caja Edificable: {buildable_area_m2:,.2f} m²")
    print(f"  -> Parking (reserva): {parking_area:.2f} m²")
    valid_models = []
    for m in models_by_bedrooms:
        m_copy = m.copy()
        m_copy['superficie_huella_m2'] = round(m['huella_ancho_m'] * m['huella_largo_m'], 2)
        m2t = m['superficie_m2']
        huella = m_copy['superficie_huella_m2']
        pass_A = m2t <= max_edif
        ocup_req = huella + parking_area
        pass_B = ocup_req <= max_ocup
        area_req = huella + parking_area
        pass_C = area_req <= buildable_area_m2
        if pass_A and pass_B and pass_C:
            valid_models.append(m_copy)
    print(f"\nModelos válidos después de filtrado: {len(valid_models)}")
    return valid_models

# ==============================================================================
# INTERFAZ CLI
# ==============================================================================

def select_model_interactive(valid_models):
    if not valid_models:
        return None
    grouped = {}
    for m in valid_models:
        d = m['numero_dormitorios']
        grouped.setdefault(d, []).append(m)
    print("\n==========================================================")
    print("Modelos Válidos (Agrupados por dormitorios):")
    print("==========================================================")
    options = {}
    idx = 1
    for d in sorted(grouped.keys()):
        print(f"\n--- {d} Dormitorios ---")
        for m in grouped[d]:
            print(f"  [{idx}] {m['nombre']} ({m['huella_ancho_m']}x{m['huella_largo_m']}m = {m['superficie_huella_m2']} m²)")
            options[str(idx)] = m
            idx += 1
    while True:
        sel = input("\nIntroduce el número [N] del modelo a analizar: ").strip()
        if sel in options:
            return options[sel]
        print("Opción no válida. Inténtalo de nuevo.")

def select_construction_system():
    systems = list(CONSTRUCTION_PRICES.keys())
    print("\n==========================================================")
    print("[Bloque 1] Sistema Constructivo:")
    print("==========================================================")
    options = {}
    for i, sys in enumerate(systems, 1):
        print(f"  [{i}] {sys.capitalize()}")
        options[str(i)] = sys
    selected_sys = None
    while selected_sys is None:
        choice = input("Selecciona sistema [N]: ").strip()
        if choice in options:
            selected_sys = options[choice]
        else:
            print("Opción inválida.")
    levels = list(CONSTRUCTION_PRICES[selected_sys].keys())
    print(f"\n[Bloque 1] Nivel de Acabado para {selected_sys.capitalize()}:")
    level_options = {}
    for i, lvl in enumerate(levels, 1):
        price = CONSTRUCTION_PRICES[selected_sys][lvl]
        print(f"  [{i}] {lvl.capitalize()} ({price:,.0f} €/m²)")
        level_options[str(i)] = lvl
    selected_level = None
    while selected_level is None:
        choice = input("Selecciona nivel [N]: ").strip()
        if choice in level_options:
            selected_level = level_options[choice]
        else:
            print("Opción inválida.")
    return selected_sys, selected_level

def select_extras():
    print("\n==========================================================")
    print("[Bloque 6] Extras Disponibles:")
    print("==========================================================")
    extras_list = list(EXTRAS_CATALOG.keys())
    for i, key in enumerate(extras_list, 1):
        ex = EXTRAS_CATALOG[key]
        if ex["type"] == "fixed":
            print(f"  [{i}] {ex['label']} — {ex['price']:,.2f} €")
        else:
            print(f"  [{i}] {ex['label']} — {ex['unit_price']:,.2f} €/ud")
    sel_input = input("\nIntroduce los números separados por comas (o Enter para ninguno): ").strip()
    if not sel_input:
        return []
    selected_extras = []
    seen_groups = set()
    for token in sel_input.split(","):
        token = token.strip()
        if not token.isdigit():
            continue
        idx = int(token)
        if idx < 1 or idx > len(extras_list):
            continue
        key = extras_list[idx - 1]
        ex = EXTRAS_CATALOG[key]
        group = ex.get("group")
        if group is not None:
            if group in seen_groups:
                print(f"  (Aviso) Ya hay un extra del grupo '{group}'. Omitiendo: {ex['label']}")
                continue
            seen_groups.add(group)
        if ex["type"] == "unit":
            while True:
                qty_input = input(f"  Cantidad para '{ex['label']}' (número entero ≥0): ").strip()
                if qty_input.isdigit():
                    qty = int(qty_input)
                    selected_extras.append({
                        "label": f"{ex['label']} × {qty}",
                        "cost": qty * ex['unit_price']
                    })
                    break
                else:
                    print("  Valor inválido.")
        else:
            selected_extras.append({
                "label": ex['label'],
                "cost": ex['price']
            })
    return selected_extras

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("="*60)
    print("Buildlovers — Calculadora de Implantación v4.5 (Refactorizada)")
    print("="*60)

    # === PASO 1: Input usuario ===
    refcat_full = input("\nIntroduce la referencia catastral completa: ").strip().replace(" ", "")
    refcat14 = refcat_full[:14]

    num_bedrooms = None
    while num_bedrooms is None:
        try:
            val = int(input("Número de dormitorios deseado: ").strip())
            if val > 0:
                num_bedrooms = val
            else:
                print("Debe ser un número positivo.")
        except ValueError:
            print("Entrada inválida.")

    # === PASO 2: Inicializar servicios ===
    catastro_svc = CatastroService()
    mdt_svc = MDTService()
    osm_svc = OSMService()

    # === PASO 3: Obtener parcela ===
    gdf_parcel = catastro_svc.get_parcel_geometry(refcat14)
    if gdf_parcel is None:
        print("Error: No se pudo obtener la parcela.")
        sys.exit(1)

    parcel_geom = gdf_parcel.geometry.iloc[0]
    parcel_area_m2 = parcel_geom.area

    print(f"\nParcela obtenida. Área: {parcel_area_m2:,.2f} m²")

    # === PASO 4: Análisis de límites ===
    bbox = bbox_from_gdf(gdf_parcel, buffer=20.0)

    analyzer = ParcelBoundaryAnalyzer(catastro_svc, osm_svc)
    analysis_result = analyzer.analyze(gdf_parcel, refcat14, bbox)

    if not analysis_result.buildable_geometry or analysis_result.buildable_geometry.is_empty:
        print("Error: No se pudo calcular la caja edificable.")
        sys.exit(1)

    buildable_area_m2 = analysis_result.buildable_geometry.area

    # === PASO 5: Filtrar modelos válidos ===
    valid_models = filter_valid_models(num_bedrooms, parcel_area_m2, buildable_area_m2)

    if not valid_models:
        print("\n¡Atención! Ningún modelo estándar encaja. Se requiere ITP (Implantación Totalmente Personalizada).")
        sys.exit(0)

    # === PASO 6: Seleccionar modelo ===
    selected_model = select_model_interactive(valid_models)

    if selected_model is None:
        print("No se seleccionó ningún modelo.")
        sys.exit(0)

    print(f"\n✓ Modelo seleccionado: {selected_model['nombre']}")

    # === PASO 7: Descargar MDT ===
    print("\n--- Descargando topografía ---")
    mdt_path = mdt_svc.download_mdt(bbox)

    if mdt_path is None:
        print("⚠️  No se pudo descargar el MDT. Se continuará con volúmenes = 0 y pendiente = 0.")

    # === PASO 8: Crear huella y calcular volúmenes ===
    buildable_gdf = gpd.GeoDataFrame([{"geometry": analysis_result.buildable_geometry}], crs=CFG.ETRS89_UTM30N)

    huella_gdf = create_house_pad(
        buildable_gdf,
        selected_model['huella_ancho_m'],
        selected_model['huella_largo_m']
    )

    if huella_gdf is None:
        print("Error: No se pudo crear la huella.")
        sys.exit(1)

    # Volúmenes - ASEGURAR QUE NUNCA SEAN NAN
    print("\n  [DEBUG MAIN] Calculando volúmenes...")
    vol_metrics = compute_volume_metrics(huella_gdf, mdt_path)

    # Verificación adicional de seguridad
    for key in ['z_optimal_m', 'cut_m3', 'fill_m3', 'balance_m3']:
        val = vol_metrics.get(key, 0.0)
        if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
            vol_metrics[key] = 0.0

    print(f"  [DEBUG MAIN] Volúmenes OK: cut={vol_metrics['cut_m3']:.2f}, fill={vol_metrics['fill_m3']:.2f}")

    # Pendiente
    print("\n  [DEBUG MAIN] Calculando pendiente...")
    xs, ys, zs = get_xyz_from_pad(huella_gdf, mdt_path)
    print(f"  [DEBUG MAIN] get_xyz_from_pad retornó: xs={'None' if xs is None else len(xs)}, ys={'None' if ys is None else len(ys)}, zs={'None' if zs is None else len(zs)}")

    if xs is None or len(xs) < 3:
        print("⚠️  Advertencia: No se pudo calcular pendiente. Usando 0%")
        slope_pct = 0.0
    else:
        _, _, slope_pct, _ = calc_pendiente(xs, ys, zs)
        if math.isnan(slope_pct) or math.isinf(slope_pct):
            slope_pct = 0.0
        print(f"  [DEBUG MAIN] Pendiente calculada: {slope_pct:.2f}%")

    print(f"\nMétricas topográficas:")
    cut_display = 0.0 if math.isnan(vol_metrics.get('cut_m3', 0.0)) else vol_metrics.get('cut_m3', 0.0)
    fill_display = 0.0 if math.isnan(vol_metrics.get('fill_m3', 0.0)) else vol_metrics.get('fill_m3', 0.0)

    if cut_display == 0.0 and fill_display == 0.0:
        print(f"  ⚠️  Sin datos topográficos válidos")
        print(f"  - Desmonte: 0.00 m³")
        print(f"  - Terraplén: 0.00 m³")
        print(f"  - Pendiente: {slope_pct:.2f} %")
        print(f"  (La huella puede estar fuera del área MDT o sin datos)")
    else:
        print(f"  - Desmonte: {cut_display:.2f} m³")
        print(f"  - Terraplén: {fill_display:.2f} m³")
        print(f"  - Pendiente: {slope_pct:.2f} %")

    # === PASO 9: Seleccionar sistema constructivo ===
    system, level = select_construction_system()
    base_price_m2 = CONSTRUCTION_PRICES[system][level]

    # === PASO 10: CALCULAR COSTES ===
    print("\n" + "="*60)
    print("DESGLOSE DE COSTES")
    print("="*60)

    total_cost = 0.0

    # [1] Construcción
    cost_construction = selected_model['superficie_m2'] * base_price_m2
    total_cost += cost_construction
    print(f"\n[1] Construcción ({system}, {level}):")
    print(f"    {selected_model['superficie_m2']:.2f} m² × {base_price_m2:,.2f} €/m² = {cost_construction:,.2f} €")

    # [2a] Losa
    cost_slab = selected_model['superficie_huella_m2'] * CFG.COSTE_LOSA_M2
    total_cost += cost_slab
    print(f"\n[2a] Losa:")
    print(f"    {selected_model['superficie_huella_m2']:.2f} m² × {CFG.COSTE_LOSA_M2:,.2f} €/m² = {cost_slab:,.2f} €")

    # [3a] Movimiento de tierras
    cost_cut = vol_metrics['cut_m3'] * CFG.COSTE_DESMONTE_M3
    cost_fill = vol_metrics['fill_m3'] * CFG.COSTE_TERRAPLEN_M3
    excess_m3 = max(0.0, vol_metrics['balance_m3'])
    cost_excess = excess_m3 * CFG.COSTE_GESTION_EXCEDENTE_M3
    cost_earthworks = cost_cut + cost_fill + cost_excess
    total_cost += cost_earthworks
    print(f"\n[3a] Movimiento de tierras:")
    print(f"    Desmonte: {cost_cut:,.2f} €")
    print(f"    Terraplén: {cost_fill:,.2f} €")
    print(f"    Excedente: {cost_excess:,.2f} €")
    print(f"    Subtotal: {cost_earthworks:,.2f} €")

    # [3b] Contención (muro + corrección por pendiente)
    print(f"\n[3b] Contención (muro perimetral de plataforma):")
    if mdt_path is not None:
        cota_plataforma = vol_metrics.get('z_optimal_m', 0.0)
        muro_result = dimensionar_muro_perimetral_real(
            mdt_path=mdt_path,
            pad_gdf=huella_gdf,
            parcel_geom=parcel_geom,
            cota_plataforma=cota_plataforma,
            paso_perfil=1.0,
            terreno_blando=False,
        )
        coste_muro = muro_result['total_coste_€']
    else:
        muro_result = None
        coste_muro = 0.0

    # mantenemos tu matriz de sobrecoste por pendiente
    sobrecoste_pendiente = 0.0
    for tier in CFG.MATRIZ_CIMENTACION_PENDIENTE:
        if slope_pct <= tier['max_pendiente']:
            sobrecoste_pendiente = tier['coste_adicional']
            break

    coste_contencion_total = coste_muro + sobrecoste_pendiente
    total_cost += coste_contencion_total

    if muro_result:
        print(f"    Tipo seleccionado: {muro_result['tipo_muro_elegido']}")
        print(f"    Coste muro (según MDT): {coste_muro:,.2f} €")
        print(f"    Altura máxima detectada: {muro_result['h_max_global_m']:.2f} m")
    else:
        print(f"    (No se pudo calcular muro porque no hay MDT. Coste muro = 0 €)")
    print(f"    Sobrecoste por pendiente ({slope_pct:.2f}%): {sobrecoste_pendiente:,.2f} €")
    print(f"    Subtotal contención: {coste_contencion_total:,.2f} €")

    # [4a] Vallado
    total_cost += analysis_result.fence_cost
    print(f"\n[4a] Vallado:")
    print(f"    Frontal: {analysis_result.frontal_length_m:.2f} ml")
    print(f"    Lateral: {analysis_result.lateral_length_m:.2f} ml")
    print(f"    Total: {analysis_result.fence_cost:,.2f} €")

    # [4b] Puerta
    total_cost += CFG.COSTE_PUERTA_ACCESO
    print(f"\n[4b] Puerta de acceso:")
    print(f"    {CFG.COSTE_PUERTA_ACCESO:,.2f} €")

    # [4c] Accesos horizontales
    dist_peat, dist_veh, cost_peat, cost_veh, p_house = compute_horizontal_access_costs(
        analysis_result.access_point, huella_gdf
    )
    total_cost += (cost_peat + cost_veh)
    print(f"\n[4c] Accesos horizontales:")
    print(f"    Peatonal: {dist_peat:.2f} m × {CFG.COSTE_PAV_PEATONAL_ML:,.2f} €/ml = {cost_peat:,.2f} €")
    print(f"    Vehicular: {dist_veh:.2f} m × {CFG.COSTE_PAV_VEHICULO_ML:,.2f} €/ml = {cost_veh:,.2f} €")

    # [4d] Acceso vertical
    delta_cota, cost_vertical = compute_vertical_access_costs(
        analysis_result.access_point, p_house, mdt_path
    )
    total_cost += cost_vertical
    print(f"\n[4d] Adaptación vertical:")
    print(f"    Δcota: {delta_cota:.2f} m → {cost_vertical:,.2f} €")

    # [4e] Conexiones
    total_cost += CFG.COSTE_FIJO_CONEXIONES_REDES
    print(f"\n[4e] Conexiones a redes:")
    print(f"    {CFG.COSTE_FIJO_CONEXIONES_REDES:,.2f} €")

    # [5] Honorarios
    cost_fees_total = (
        CFG.COSTE_FIJO_HONORARIOS_TECNICOS +
        CFG.HON_CALC_ESTRUCTURAL +
        CFG.HON_ESTUDIO_GEOTECNICO +
        CFG.HON_LEV_TOPOGRAFICO +
        CFG.HON_LEGALIZACIONES
    )
    total_cost += cost_fees_total
    print(f"\n[5] Honorarios técnicos:")
    print(f"    Arquitectura: {CFG.COSTE_FIJO_HONORARIOS_TECNICOS:,.2f} €")
    print(f"    Cálculo estructural: {CFG.HON_CALC_ESTRUCTURAL:,.2f} €")
    print(f"    Estudio geotécnico: {CFG.HON_ESTUDIO_GEOTECNICO:,.2f} €")
    print(f"    Levantamiento topográfico: {CFG.HON_LEV_TOPOGRAFICO:,.2f} €")
    print(f"    Legalizaciones: {CFG.HON_LEGALIZACIONES:,.2f} €")
    print(f"    Subtotal: {cost_fees_total:,.2f} €")

    # [6] Extras
    selected_extras = select_extras()
    cost_extras = sum(ex['cost'] for ex in selected_extras)
    total_cost += cost_extras

    if selected_extras:
        print(f"\n[6] Extras:")
        for ex in selected_extras:
            print(f"    {ex['label']}: {ex['cost']:,.2f} €")
        print(f"    Subtotal: {cost_extras:,.2f} €")
    else:
        print(f"\n[6] Extras: 0.00 € (ninguno)")

    # === TOTAL ===
    print("\n" + "-"*60)
    print(f"TOTAL PARCIAL: {total_cost:,.2f} €")
    print("="*60)

    # === PASO 11: Financiación ===
    print("\n[7] Financiación — Cálculo de cuota de hipoteca")

    base_financiable = max(total_cost - cost_fees_total, 0.0)

    use_default = input(f"¿Usar interés/plazo por defecto ({CFG.DEFAULT_INTERES_HIPOTECA}% a {CFG.DEFAULT_PLAZO_HIPOTECA_ANOS} años)? [S/n]: ").strip().lower()

    if use_default in ("", "s", "si", "sí", "y", "yes"):
        interest_rate = CFG.DEFAULT_INTERES_HIPOTECA
        years = CFG.DEFAULT_PLAZO_HIPOTECA_ANOS
    else:
        try:
            interest_rate = float(input("TIN anual (%): ").strip().replace(",", "."))
            years = int(input("Plazo (años): ").strip())
        except ValueError:
            print("Entrada no válida. Usando valores por defecto.")
            interest_rate = CFG.DEFAULT_INTERES_HIPOTECA
            years = CFG.DEFAULT_PLAZO_HIPOTECA_ANOS

    monthly_payment = compute_monthly_payment(base_financiable, interest_rate, years)

    print("-"*60)
    print(f"[7] Base financiable (Total - Honorarios): {base_financiable:,.2f} €")
    print(f"[7] Cuota mensual estimada: {monthly_payment:,.2f} €/mes")
    print("="*60)

    print("\n✓ Cálculo completado con éxito.")

# ==============================================================================
# ENTRY
# ==============================================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
