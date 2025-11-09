"""
Buildlovers - Configuración y constantes
"""

from dataclasses import dataclass
from pyproj import CRS


@dataclass
class Config:
    """Configuración centralizada del sistema"""

    # Sistemas de referencia
    ETRS89_UTM30N = CRS.from_epsg(25830)
    WGS84 = CRS.from_epsg(4326)

    # Parámetros geométricos
    BBOX_BUFFER = 20.0
    SEGMENT_BUFFER = 0.30
    OUTSIDE_RING_WIDTH = 1.20
    NEIGHBOR_EPSILON = 0.20
    AREA_TOLERANCE = 1e-4
    STREET_COMPACT_MAX = 0.30
    STREET_AR_MIN = 2.20
    ROAD_DISTANCE_MAX = 4.0
    ROAD_BUFFER = 6.0

    # URLs de servicios
    CATASTRO_WFS_URL = "https://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx"
    CATASTRO_TIMEOUT = 60

    # MDT
    MDT_OUTPUT_PATH = "/tmp/mdt.tif"
    MDT_TIMEOUT = 120

    # OpenStreetMap
    OSM_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    OSM_TIMEOUT = 40
    OSM_HIGHWAY_EXCLUDE = [
        "footway", "path", "cycleway", "bridleway", "steps",
        "proposed", "construction", "corridor", "escalator",
        "platform", "track", "service"
    ]

    # Costes de construcción
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

    # Parámetros de parking
    PARKING_ANCHO_M = 2.5
    PARKING_LARGO_M = 5.0

    # Financiación
    DEFAULT_INTERES_HIPOTECA = 2.5
    DEFAULT_PLAZO_HIPOTECA_ANOS = 30

    # Normativa urbanística
    OCUPACION_PORCENTAJE = 30.0
    EDIFICABILIDAD_M2T_M2S = 0.4
    RETRANQUEO_FRONTAL_M = 5.0
    RETRANQUEO_LATERAL_M = 3.0

    # Matrices de costes
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


# Instancia global de configuración
CFG = Config()
