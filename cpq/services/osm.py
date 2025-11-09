"""
Servicio de acceso a datos de OpenStreetMap
"""

import requests
import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import LineString
from typing import Tuple

from ..config import CFG


class OSMService:
    """Servicio para consultas a OpenStreetMap vía Overpass API"""

    def fetch_roads(self, bbox: Tuple) -> gpd.GeoDataFrame:
        """
        Consulta red viaria desde OSM

        Args:
            bbox: Bounding box en ETRS89 UTM30N (minx, miny, maxx, maxy)

        Returns:
            GeoDataFrame con geometrías de carreteras
        """
        print("[OSM] Consultando red viaria...")

        try:
            minx, miny, maxx, maxy = bbox

            # Transformar a WGS84 para Overpass
            to_wgs84 = Transformer.from_crs(
                CFG.ETRS89_UTM30N,
                CFG.WGS84,
                always_xy=True
            )
            west, south = to_wgs84.transform(minx, miny)
            east, north = to_wgs84.transform(maxx, maxy)

            if west > east:
                west, east = east, west
            if south > north:
                south, north = north, south

            # Construir query Overpass
            exclude = "|".join(CFG.OSM_HIGHWAY_EXCLUDE)
            query = f"""[out:json][timeout:{CFG.OSM_TIMEOUT}];
            (way["highway"]["highway"!~"{exclude}"]({south},{west},{north},{east}););
            out geom;"""

            # Ejecutar consulta
            r = requests.post(
                CFG.OSM_OVERPASS_URL,
                data={"data": query},
                timeout=CFG.OSM_TIMEOUT + 10
            )
            r.raise_for_status()
            data = r.json()

            # Procesar resultados
            lines = []
            to_utm = Transformer.from_crs(
                CFG.WGS84,
                CFG.ETRS89_UTM30N,
                always_xy=True
            )

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
            return gpd.GeoDataFrame(
                {"geometry": lines},
                crs=CFG.ETRS89_UTM30N
            )

        except Exception as e:
            print(f"[OSM] Error: {e}")
            return gpd.GeoDataFrame(geometry=[], crs=CFG.ETRS89_UTM30N)
