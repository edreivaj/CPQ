"""
Análisis de normativa urbanística por contexto (Proxy Urbanístico)

Infiere parámetros urbanísticos observando el entorno construido:
- Retranqueos por lado (frontal/lateral/fondo)
- Ocupación real
- Edificabilidad observada

Sustituye valores por defecto del config cuando hay suficiente confianza.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple, List
import math

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, LineString, Point
from shapely.ops import unary_union, nearest_points

from ..config import CFG


# ==============================================================================
# GEOMETRÍA: Helpers
# ==============================================================================

def _ensure_projected_in_meters(gdf: gpd.GeoDataFrame) -> None:
    """Valida que el CRS esté proyectado (unidades métricas)"""
    if gdf.crs is None:
        raise ValueError(
            "GeoDataFrame sin CRS. Asigna gdf.set_crs(...) "
            "y reproyecta a un CRS métrico."
        )
    if gdf.crs.is_geographic:
        raise ValueError(
            "CRS geográfico (lat/lon). Reproyecta a un CRS proyectado "
            "en metros (p.ej. EPSG:25830)."
        )


def _fix_geom(geom):
    """Repara geometrías inválidas"""
    if geom is None or geom.is_empty:
        return None
    if not geom.is_valid:
        geom = geom.buffer(0)
    if geom.is_empty:
        return None
    return geom


def _largest_polygon(geom):
    """Para MultiPolygon, devuelve el polígono de mayor área"""
    if geom is None:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        polys = [p for p in geom.geoms if p.area > 0]
        return max(polys, key=lambda p: p.area) if polys else None
    return None


def _polygon_compactness(geom: Polygon) -> float:
    """
    Compacidad: 4π·A / P²
    Círculo = 1.0, formas irregulares → 0
    """
    if geom is None or geom.is_empty:
        return 0.0
    try:
        area = geom.area
        perimeter = geom.length
        if perimeter <= 0:
            return 0.0
        return float((4 * math.pi * area) / (perimeter * perimeter))
    except:
        return 0.0


def _centroid_distance(geom1, geom2) -> float:
    """Distancia entre centroides"""
    try:
        return float(geom1.centroid.distance(geom2.centroid))
    except:
        return float('inf')


# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

@dataclass
class ProxyConfig:
    """Configuración del análisis proxy"""

    # Búsqueda espacial
    radius_m: float = 250.0
    min_neighbors: int = 10

    # Filtrado de edificios
    min_building_area_m2: float = 35.0
    max_buildings_per_parcel: Optional[int] = None

    # Filtrado de parcelas comparables
    use_comparable_parcels: bool = True
    comparable_area_tolerance: float = 0.50  # ±50% área

    # Selección edificio principal
    building_selection_mode: str = "smart"  # "smart", "largest", "centroid"

    # Límites de ocupación
    occupancy_clip: Tuple[float, float] = (0.01, 0.95)

    # Clasificación de lados
    use_road_classification: bool = True
    road_buffer_m: float = 15.0  # buffer desde vial para detectar frente


@dataclass
class ProxyStats:
    """Estadísticos agregados del análisis"""
    n_parcels_total: int
    n_parcels_used: int
    n_comparables: int

    # Por lado
    distances_frontal_m: Dict[str, float]
    distances_lateral_m: Dict[str, float]
    distances_fondo_m: Dict[str, float]

    # Ocupación y edificabilidad
    occupancy: Dict[str, float]
    building_footprint_m2: Dict[str, float]
    floors_avg: float

    # Confianza
    confidence: Dict[str, Any]


@dataclass
class ProxyResult:
    """Resultado completo del análisis proxy"""

    # Parámetros inferidos (listos para sustituir defaults)
    retranqueo_frontal_m: float
    retranqueo_lateral_m: float
    retranqueo_fondo_m: float
    ocupacion_max: float
    edificabilidad_m2t_m2s: float

    # Estadísticos detallados
    stats: ProxyStats

    # DataFrame con vecinos analizados
    df_neighbors: pd.DataFrame

    # Envolvente edificable
    buildable_envelope: Optional[Polygon]
    buildable_area_m2: float

    # Confianza global
    confidence_score: float
    confidence_label: str

    # Flags
    use_proxy: bool  # True si la confianza es suficiente


# ==============================================================================
# CLASIFICACIÓN DE LADOS: Frente/Lateral/Fondo
# ==============================================================================

def classify_parcel_sides(
    parcel_geom: Polygon,
    roads_gdf: Optional[gpd.GeoDataFrame],
    road_buffer_m: float = 15.0
) -> Dict[str, List[LineString]]:
    """
    Clasifica los lados de una parcela en frontal/lateral/fondo

    Usa viales cercanos (OSM) para identificar frente.
    Si no hay viales, usa el lado más largo como frente.

    Returns:
        Dict con keys: 'frontal', 'lateral', 'fondo'
        Cada uno contiene lista de segmentos LineString
    """

    if not isinstance(parcel_geom, Polygon):
        parcel_geom = _largest_polygon(parcel_geom)

    if parcel_geom is None:
        return {'frontal': [], 'lateral': [], 'fondo': []}

    # Obtener segmentos del perímetro
    coords = list(parcel_geom.exterior.coords)
    segments = []

    for i in range(len(coords) - 1):
        seg = LineString([coords[i], coords[i + 1]])
        segments.append({
            'geometry': seg,
            'length': seg.length,
            'index': i
        })

    if not segments:
        return {'frontal': [], 'lateral': [], 'fondo': []}

    # Estrategia 1: Usar viales si disponibles
    if roads_gdf is not None and not roads_gdf.empty:
        # Unir todos los viales y hacer buffer
        roads_union = unary_union(roads_gdf.geometry.tolist())
        roads_buffered = roads_union.buffer(road_buffer_m)

        # Calcular intersección de cada segmento con zona vial
        for seg_info in segments:
            seg = seg_info['geometry']
            # Longitud del segmento que intersecta con buffer vial
            inter = seg.intersection(roads_buffered)
            if not inter.is_empty:
                seg_info['road_proximity'] = inter.length / seg.length
            else:
                seg_info['road_proximity'] = 0.0

        # El segmento con mayor proximidad a vial es frontal
        segments_sorted = sorted(
            segments,
            key=lambda s: s['road_proximity'],
            reverse=True
        )

        if segments_sorted[0]['road_proximity'] > 0.3:  # al menos 30% toca vial
            frontal_idx = segments_sorted[0]['index']
        else:
            # No hay contacto claro con vial, usar lado más largo
            frontal_idx = max(segments, key=lambda s: s['length'])['index']
    else:
        # Estrategia 2: Lado más largo como frente
        frontal_idx = max(segments, key=lambda s: s['length'])['index']

    # Clasificar segmentos
    n_segs = len(segments)
    frontal = []
    lateral = []
    fondo = []

    for i, seg_info in enumerate(segments):
        seg = seg_info['geometry']

        if i == frontal_idx:
            frontal.append(seg)
        elif i == (frontal_idx + 2) % n_segs:  # opuesto al frente
            fondo.append(seg)
        else:
            lateral.append(seg)

    return {
        'frontal': frontal,
        'lateral': lateral,
        'fondo': fondo
    }


# ==============================================================================
# DETECCIÓN EDIFICIO PRINCIPAL (MEJORADA)
# ==============================================================================

def select_main_building(
    buildings_gdf: gpd.GeoDataFrame,
    parcel_geom: Polygon,
    mode: str = "smart"
) -> Tuple[Optional[Polygon], float]:
    """
    Selecciona el edificio principal de una parcela

    Modos:
    - "largest": edificio de mayor área (clásico)
    - "centroid": edificio cuyo centroide está más cerca del centroide parcela
    - "smart": combina área, compacidad y centralidad

    Returns:
        (geometría edificio principal, área)
    """

    if buildings_gdf.empty:
        return None, 0.0

    buildings = buildings_gdf.copy()
    buildings['b_area'] = buildings.geometry.area
    buildings['compactness'] = buildings.geometry.apply(_polygon_compactness)
    buildings['centroid_dist'] = buildings.geometry.apply(
        lambda g: _centroid_distance(g, parcel_geom)
    )

    if mode == "largest":
        main = buildings.loc[buildings['b_area'].idxmax()]
        return main.geometry, float(main['b_area'])

    elif mode == "centroid":
        main = buildings.loc[buildings['centroid_dist'].idxmin()]
        return main.geometry, float(main['b_area'])

    elif mode == "smart":
        # Normalizar métricas [0, 1]
        buildings['area_norm'] = (
            buildings['b_area'] / buildings['b_area'].max()
            if buildings['b_area'].max() > 0 else 0
        )

        max_dist = buildings['centroid_dist'].max()
        if max_dist > 0:
            buildings['centrality'] = 1.0 - (
                buildings['centroid_dist'] / max_dist
            )
        else:
            buildings['centrality'] = 1.0

        # Score ponderado
        # 50% área, 30% centralidad, 20% compacidad
        buildings['score'] = (
            0.50 * buildings['area_norm'] +
            0.30 * buildings['centrality'] +
            0.20 * buildings['compactness']
        )

        main = buildings.loc[buildings['score'].idxmax()]
        return main.geometry, float(main['b_area'])

    else:
        raise ValueError(f"Modo desconocido: {mode}")


# ==============================================================================
# FILTRADO DE PARCELAS COMPARABLES
# ==============================================================================

def filter_comparable_parcels(
    parcels_gdf: gpd.GeoDataFrame,
    target_area_m2: float,
    tolerance: float = 0.50
) -> gpd.GeoDataFrame:
    """
    Filtra parcelas comparables por área ±tolerance

    Args:
        parcels_gdf: Parcelas vecinas
        target_area_m2: Área de la parcela objetivo
        tolerance: Tolerancia (0.5 = ±50%)

    Returns:
        GeoDataFrame filtrado
    """

    parcels = parcels_gdf.copy()
    parcels['p_area'] = parcels.geometry.area

    min_area = target_area_m2 * (1 - tolerance)
    max_area = target_area_m2 * (1 + tolerance)

    comparables = parcels[
        (parcels['p_area'] >= min_area) &
        (parcels['p_area'] <= max_area)
    ].copy()

    return comparables


# ==============================================================================
# CÁLCULO DE RETRANQUEOS POR LADO
# ==============================================================================

def compute_setbacks_by_side(
    parcel_geom: Polygon,
    building_geom: Polygon,
    sides: Dict[str, List[LineString]]
) -> Dict[str, float]:
    """
    Calcula retranqueo mínimo para cada tipo de lado

    Returns:
        Dict con keys: 'frontal', 'lateral', 'fondo'
    """

    result = {
        'frontal': float('inf'),
        'lateral': float('inf'),
        'fondo': float('inf')
    }

    building_boundary = building_geom.boundary

    for side_type, segments in sides.items():
        if not segments:
            result[side_type] = float('nan')
            continue

        min_dist = float('inf')

        for seg in segments:
            # Distancia del segmento del lado al contorno del edificio
            dist = seg.distance(building_boundary)
            min_dist = min(min_dist, dist)

        result[side_type] = float(min_dist) if np.isfinite(min_dist) else float('nan')

    return result


# ==============================================================================
# ESTADÍSTICOS
# ==============================================================================

def _percentiles(x: np.ndarray, ps=(25, 50, 75)) -> Dict[str, float]:
    """Calcula percentiles de un array"""
    x = x[~np.isnan(x)]
    if x.size == 0:
        return {f"p{p}": float("nan") for p in ps}
    vals = np.percentile(x, ps)
    return {f"p{p}": float(v) for p, v in zip(ps, vals)}


def _iqr(x: np.ndarray) -> float:
    """Calcula rango intercuartílico"""
    x = x[~np.isnan(x)]
    if x.size < 2:
        return float("nan")
    q75 = np.percentile(x, 75)
    q25 = np.percentile(x, 25)
    return float(q75 - q25)


def _compute_stats_dict(arr: np.ndarray) -> Dict[str, float]:
    """Calcula estadísticos completos de un array"""
    return {
        **_percentiles(arr, ps=(10, 25, 50, 75, 90)),
        "mean": float(np.nanmean(arr)),
        "std": float(np.nanstd(arr)),
        "iqr": _iqr(arr),
        "min": float(np.nanmin(arr)) if arr.size > 0 else float('nan'),
        "max": float(np.nanmax(arr)) if arr.size > 0 else float('nan'),
    }


# ==============================================================================
# MOTOR PRINCIPAL: Análisis Proxy
# ==============================================================================

def compute_urbanismo_proxy(
    target_parcel_gdf: gpd.GeoDataFrame,
    parcels_gdf: gpd.GeoDataFrame,
    buildings_gdf: gpd.GeoDataFrame,
    roads_gdf: Optional[gpd.GeoDataFrame] = None,
    cfg: ProxyConfig = ProxyConfig(),
) -> ProxyResult:
    """
    Análisis completo de urbanismo por contexto

    Args:
        target_parcel_gdf: Parcela objetivo (1 fila)
        parcels_gdf: Todas las parcelas del área
        buildings_gdf: Huellas de edificaciones
        roads_gdf: Viales (opcional, mejora clasificación de frente)
        cfg: Configuración

    Returns:
        ProxyResult con parámetros inferidos listos para CPQ
    """

    if len(target_parcel_gdf) != 1:
        raise ValueError("target_parcel_gdf debe tener exactamente 1 fila")

    # Validar CRS
    _ensure_projected_in_meters(target_parcel_gdf)
    _ensure_projected_in_meters(parcels_gdf)
    _ensure_projected_in_meters(buildings_gdf)
    if roads_gdf is not None:
        _ensure_projected_in_meters(roads_gdf)

    # Alinear CRS
    target_crs = target_parcel_gdf.crs
    if parcels_gdf.crs != target_crs:
        parcels_gdf = parcels_gdf.to_crs(target_crs)
    if buildings_gdf.crs != target_crs:
        buildings_gdf = buildings_gdf.to_crs(target_crs)
    if roads_gdf is not None and roads_gdf.crs != target_crs:
        roads_gdf = roads_gdf.to_crs(target_crs)

    # Geometría target
    target_geom = _largest_polygon(_fix_geom(target_parcel_gdf.geometry.iloc[0]))
    if target_geom is None:
        raise ValueError("Geometría target inválida")

    target_area = target_geom.area

    # Reparar geometrías
    parcels = parcels_gdf.copy()
    parcels['geometry'] = parcels.geometry.apply(
        lambda g: _largest_polygon(_fix_geom(g))
    )
    parcels = parcels[parcels.geometry.notna()].copy()

    buildings = buildings_gdf.copy()
    buildings['geometry'] = buildings.geometry.apply(
        lambda g: _largest_polygon(_fix_geom(g))
    )
    buildings = buildings[buildings.geometry.notna()].copy()

    # Búsqueda espacial
    search_area = target_geom.buffer(cfg.radius_m)
    parcels_near = parcels[parcels.intersects(search_area)].copy()

    n_total = len(parcels_near)

    # Filtrar comparables por área
    if cfg.use_comparable_parcels:
        parcels_near = filter_comparable_parcels(
            parcels_near,
            target_area,
            cfg.comparable_area_tolerance
        )

    n_comparables = len(parcels_near)

    # Clasificar lados de la parcela target (para envolvente final)
    target_sides = classify_parcel_sides(
        target_geom,
        roads_gdf,
        cfg.road_buffer_m
    )

    # Índice espacial de edificios
    b_sindex = buildings.sindex

    # Analizar cada parcela vecina
    rows = []

    for idx, prow in parcels_near.iterrows():
        pgeom = prow.geometry
        if pgeom is None or pgeom.is_empty:
            continue

        # Buscar edificios en esta parcela
        cand_idx = list(b_sindex.intersection(pgeom.bounds))
        b_cand = buildings.iloc[cand_idx]
        b_cand = b_cand[b_cand.intersects(pgeom)].copy()

        # Filtrar por tamaño mínimo
        b_cand = b_cand[b_cand.geometry.area >= cfg.min_building_area_m2]

        if b_cand.empty:
            continue

        # Seleccionar edificio principal
        main_building, b_area = select_main_building(
            b_cand,
            pgeom,
            mode=cfg.building_selection_mode
        )

        if main_building is None:
            continue

        p_area = pgeom.area
        if p_area <= 0:
            continue

        occ = b_area / p_area

        # Filtrar ocupaciones absurdas
        if occ < cfg.occupancy_clip[0] or occ > cfg.occupancy_clip[1]:
            continue

        # Clasificar lados de esta parcela
        p_sides = classify_parcel_sides(
            pgeom,
            roads_gdf,
            cfg.road_buffer_m
        )

        # Calcular retranqueos por lado
        setbacks = compute_setbacks_by_side(pgeom, main_building, p_sides)

        rows.append({
            'parcel_index': idx,
            'parcel_area_m2': p_area,
            'building_area_m2': b_area,
            'occupancy': occ,
            'setback_frontal_m': setbacks['frontal'],
            'setback_lateral_m': setbacks['lateral'],
            'setback_fondo_m': setbacks['fondo'],
        })

    df = pd.DataFrame(rows)
    n_used = len(df)

    if n_used == 0:
        # No hay datos suficientes, devolver valores por defecto
        return _create_default_result(target_geom, target_area)

    # Calcular estadísticos por lado
    frontal_arr = df['setback_frontal_m'].to_numpy(dtype=float)
    lateral_arr = df['setback_lateral_m'].to_numpy(dtype=float)
    fondo_arr = df['setback_fondo_m'].to_numpy(dtype=float)
    occ_arr = df['occupancy'].to_numpy(dtype=float)
    b_arr = df['building_area_m2'].to_numpy(dtype=float)

    frontal_stats = _compute_stats_dict(frontal_arr)
    lateral_stats = _compute_stats_dict(lateral_arr)
    fondo_stats = _compute_stats_dict(fondo_arr)
    occ_stats = _compute_stats_dict(occ_arr)
    b_stats = _compute_stats_dict(b_arr)

    # Calcular plantas promedio (estimación tosca: edificabilidad/ocupación)
    floors_avg = float(np.nanmedian(occ_arr) * 1.5)  # Estimación conservadora

    # Confianza
    confidence = _compute_confidence(
        n_used=n_used,
        n_target=cfg.min_neighbors,
        frontal_stats=frontal_stats,
        lateral_stats=lateral_stats,
        occ_stats=occ_stats
    )

    # Crear stats
    stats = ProxyStats(
        n_parcels_total=n_total,
        n_parcels_used=n_used,
        n_comparables=n_comparables,
        distances_frontal_m=frontal_stats,
        distances_lateral_m=lateral_stats,
        distances_fondo_m=fondo_stats,
        occupancy=occ_stats,
        building_footprint_m2=b_stats,
        floors_avg=floors_avg,
        confidence=confidence
    )

    # PARÁMETROS INFERIDOS (para sustituir defaults)
    retranqueo_frontal = frontal_stats.get('p50', CFG.RETRANQUEO_FRONTAL_M)
    retranqueo_lateral = lateral_stats.get('p50', CFG.RETRANQUEO_LATERAL_M)
    retranqueo_fondo = lateral_stats.get('p50', CFG.RETRANQUEO_LATERAL_M)

    ocupacion_max = occ_stats.get('p75', CFG.OCUPACION_PORCENTAJE / 100.0)
    edificabilidad = ocupacion_max * floors_avg

    # Si valores son NaN, usar defaults
    if not np.isfinite(retranqueo_frontal):
        retranqueo_frontal = CFG.RETRANQUEO_FRONTAL_M
    if not np.isfinite(retranqueo_lateral):
        retranqueo_lateral = CFG.RETRANQUEO_LATERAL_M
    if not np.isfinite(retranqueo_fondo):
        retranqueo_fondo = CFG.RETRANQUEO_LATERAL_M
    if not np.isfinite(ocupacion_max):
        ocupacion_max = CFG.OCUPACION_PORCENTAJE / 100.0
    if not np.isfinite(edificabilidad):
        edificabilidad = CFG.EDIFICABILIDAD_M2T_M2S

    # Envolvente edificable
    buildable_envelope, buildable_area = _create_buildable_envelope(
        target_geom,
        target_sides,
        retranqueo_frontal,
        retranqueo_lateral,
        retranqueo_fondo
    )

    # Decidir si usar proxy o defaults
    use_proxy = confidence['score'] >= 0.50  # umbral mínimo

    return ProxyResult(
        retranqueo_frontal_m=float(retranqueo_frontal),
        retranqueo_lateral_m=float(retranqueo_lateral),
        retranqueo_fondo_m=float(retranqueo_fondo),
        ocupacion_max=float(ocupacion_max),
        edificabilidad_m2t_m2s=float(edificabilidad),
        stats=stats,
        df_neighbors=df,
        buildable_envelope=buildable_envelope,
        buildable_area_m2=float(buildable_area),
        confidence_score=float(confidence['score']),
        confidence_label=confidence['label'],
        use_proxy=use_proxy
    )


def _compute_confidence(
    n_used: int,
    n_target: int,
    frontal_stats: Dict,
    lateral_stats: Dict,
    occ_stats: Dict
) -> Dict[str, Any]:
    """Calcula score de confianza del análisis"""

    # Componente tamaño de muestra
    size_score = min(1.0, n_used / max(1, n_target))

    # Dispersión relativa
    def rel_disp(stats):
        iqr = stats.get('iqr', float('nan'))
        med = stats.get('p50', float('nan'))
        if not np.isfinite(iqr) or not np.isfinite(med) or med <= 0:
            return 1.0
        return iqr / med

    frontal_rel = rel_disp(frontal_stats)
    lateral_rel = rel_disp(lateral_stats)
    occ_rel = rel_disp(occ_stats)

    # Convertir dispersión a score (menos dispersión = mejor)
    def disp_to_score(rel):
        return float(np.clip(1.0 - (rel - 0.25) / (1.0 - 0.25), 0.0, 1.0))

    frontal_score = disp_to_score(frontal_rel)
    lateral_score = disp_to_score(lateral_rel)
    occ_score = disp_to_score(occ_rel)

    # Score global ponderado
    score = (
        0.40 * size_score +
        0.25 * frontal_score +
        0.20 * lateral_score +
        0.15 * occ_score
    )

    if score >= 0.75:
        label = "alta"
    elif score >= 0.50:
        label = "media"
    else:
        label = "baja"

    return {
        'score': float(score),
        'label': label,
        'n_used': int(n_used),
        'size_score': float(size_score),
        'frontal_score': float(frontal_score),
        'lateral_score': float(lateral_score),
        'occ_score': float(occ_score)
    }


def _create_buildable_envelope(
    parcel_geom: Polygon,
    sides: Dict[str, List[LineString]],
    setback_frontal: float,
    setback_lateral: float,
    setback_fondo: float
) -> Tuple[Optional[Polygon], float]:
    """
    Crea envolvente edificable con retranqueos diferenciados

    Simplificación: buffer general con la media de retranqueos
    (Implementación completa requeriría buffer por lado)
    """

    # Usar buffer promedio ponderado
    avg_setback = (
        setback_frontal * 0.4 +
        setback_lateral * 0.4 +
        setback_fondo * 0.2
    )

    if avg_setback <= 0:
        return parcel_geom, parcel_geom.area

    try:
        envelope = parcel_geom.buffer(-avg_setback)
        envelope = _largest_polygon(_fix_geom(envelope))

        if envelope is None or envelope.is_empty:
            return None, 0.0

        return envelope, envelope.area
    except:
        return None, 0.0


def _create_default_result(
    target_geom: Polygon,
    target_area: float
) -> ProxyResult:
    """Crea resultado con valores por defecto cuando no hay datos"""

    return ProxyResult(
        retranqueo_frontal_m=CFG.RETRANQUEO_FRONTAL_M,
        retranqueo_lateral_m=CFG.RETRANQUEO_LATERAL_M,
        retranqueo_fondo_m=CFG.RETRANQUEO_LATERAL_M,
        ocupacion_max=CFG.OCUPACION_PORCENTAJE / 100.0,
        edificabilidad_m2t_m2s=CFG.EDIFICABILIDAD_M2T_M2S,
        stats=ProxyStats(
            n_parcels_total=0,
            n_parcels_used=0,
            n_comparables=0,
            distances_frontal_m={},
            distances_lateral_m={},
            distances_fondo_m={},
            occupancy={},
            building_footprint_m2={},
            floors_avg=1.0,
            confidence={'score': 0.0, 'label': 'baja'}
        ),
        df_neighbors=pd.DataFrame(),
        buildable_envelope=target_geom.buffer(-CFG.RETRANQUEO_LATERAL_M),
        buildable_area_m2=target_geom.buffer(-CFG.RETRANQUEO_LATERAL_M).area,
        confidence_score=0.0,
        confidence_label='baja',
        use_proxy=False
    )
