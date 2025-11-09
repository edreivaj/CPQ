"""
Buildlovers - Modelos de datos y catálogos
"""

from dataclasses import dataclass
from typing import Optional
from shapely.geometry import Polygon, Point


# ==============================================================================
# CATÁLOGO DE MODELOS DE CASAS
# ==============================================================================

MODELS_DATABASE = [
    {
        "model_id": "BL_1D1P_01",
        "nombre": "1D Lineal 45",
        "numero_dormitorios": 1,
        "numero_baños": 1,
        "plantas": 1,
        "superficie_m2": 45,
        "huella_ancho_m": 7.5,
        "huella_largo_m": 6.0,
        "maqueta_ref_id": "MAQ_1D1P_01"
    },
    {
        "model_id": "BL_2D1P_01",
        "nombre": "2D Compacto 70",
        "numero_dormitorios": 2,
        "numero_baños": 1,
        "plantas": 1,
        "superficie_m2": 70,
        "huella_ancho_m": 9.0,
        "huella_largo_m": 7.8,
        "maqueta_ref_id": "MAQ_2D1P_01"
    },
    {
        "model_id": "BL_3D1P_01",
        "nombre": "3D Lineal 100",
        "numero_dormitorios": 3,
        "numero_baños": 2,
        "plantas": 1,
        "superficie_m2": 100,
        "huella_ancho_m": 12.0,
        "huella_largo_m": 8.5,
        "maqueta_ref_id": "MAQ_3D1P_01"
    },
    {
        "model_id": "BL_3D2P_01",
        "nombre": "3D Duplex 118",
        "numero_dormitorios": 3,
        "numero_baños": 3,
        "plantas": 2,
        "superficie_m2": 118,
        "huella_ancho_m": 8.6,
        "huella_largo_m": 7.0,
        "maqueta_ref_id": "MAQ_3D2P_01"
    },
    {
        "model_id": "BL_4D1P_01",
        "nombre": "4D Lineal 130",
        "numero_dormitorios": 4,
        "numero_baños": 3,
        "plantas": 1,
        "superficie_m2": 130,
        "huella_ancho_m": 15.0,
        "huella_largo_m": 9.0,
        "maqueta_ref_id": "MAQ_4D1P_01"
    },
    {
        "model_id": "BL_5D2P_01",
        "nombre": "5D Duplex 190",
        "numero_dormitorios": 5,
        "numero_baños": 4,
        "plantas": 2,
        "superficie_m2": 190,
        "huella_ancho_m": 11.0,
        "huella_largo_m": 9.0,
        "maqueta_ref_id": "MAQ_5D2P_01"
    },
]


# ==============================================================================
# PRECIOS DE CONSTRUCCIÓN
# ==============================================================================

CONSTRUCTION_PRICES = {
    "steelframe": {
        "essencial": 1340,
        "premium": 1530,
        "excellence": 1750
    },
    "madera": {
        "essencial": 1450,
        "premium": 1600,
        "excellence": 1750
    },
    "hormigon": {
        "essencial": 1650,
        "premium": 1700,
        "excellence": 1850
    }
}


# ==============================================================================
# CATÁLOGO DE EXTRAS
# ==============================================================================

EXTRAS_CATALOG = {
    "piscina_6x3": {
        "label": "Piscina 6x3 m (clorada)",
        "type": "fixed",
        "price": 21000.0,
        "group": "piscina"
    },
    "piscina_8x4": {
        "label": "Piscina 8x4 m (clorada)",
        "type": "fixed",
        "price": 32000.0,
        "group": "piscina"
    },
    "pergola_2c": {
        "label": "Pérgola 2 coches",
        "type": "fixed",
        "price": 4500.0,
        "group": None
    },
    "porche_20m2": {
        "label": "Porche 20 m²",
        "type": "fixed",
        "price": 7800.0,
        "group": None
    },
    "pv_3kw": {
        "label": "Placas fotovoltaicas 3 kW",
        "type": "fixed",
        "price": 5700.0,
        "group": None
    },
    "pv_5kw": {
        "label": "Placas fotovoltaicas 5 kW",
        "type": "fixed",
        "price": 8900.0,
        "group": None
    },
    "punto_ev": {
        "label": "Punto de carga vehículo eléctrico",
        "type": "fixed",
        "price": 1200.0,
        "group": None
    },
    "domotica_basic": {
        "label": "Domótica básica",
        "type": "fixed",
        "price": 1500.0,
        "group": None
    },
    "arboles": {
        "label": "Arbolado ornamental (unidad)",
        "type": "unit",
        "unit_price": 180.0,
        "group": None
    },
}


# ==============================================================================
# DATACLASSES
# ==============================================================================

@dataclass
class ParcelAnalysisResult:
    """Resultado del análisis de límites de parcela"""
    fence_cost: float
    buildable_geometry: Optional[Polygon]
    frontal_length_m: float
    lateral_length_m: float
    access_point: Point
