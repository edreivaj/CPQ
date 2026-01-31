"""
Servicio de acceso a datos del Catastro
"""

import requests
import geopandas as gpd
from io import BytesIO
from typing import Optional, Tuple
from shapely.geometry import box

from ..config import CFG


class CatastroService:
    """Servicio para consultas al Catastro mediante WFS"""

    def get_parcel_geometry(self, refcat14: str) -> Optional[gpd.GeoDataFrame]:
        """
        Obtiene la geometría de una parcela catastral

        Args:
            refcat14: Referencia catastral (14 caracteres)

        Returns:
            GeoDataFrame con la geometría de la parcela o None si falla
        """
        print(f"[Catastro] Obteniendo parcela {refcat14}...")
        params = {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "STOREDQUERY_ID": "GetParcel",
            "refcat": refcat14,
            "SRSNAME": "EPSG:25830"
        }

        try:
            r = requests.get(
                CFG.CATASTRO_WFS_URL,
                params=params,
                timeout=CFG.CATASTRO_TIMEOUT
            )
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
        """
        Obtiene las parcelas vecinas a una referencia catastral

        Args:
            refcat14: Referencia catastral (14 caracteres)

        Returns:
            GeoDataFrame con las parcelas vecinas o None si falla
        """
        print(f"[Catastro] Obteniendo vecinos...")
        params = {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "STOREDQUERY_ID": "GetNeighbourParcel",
            "REFCAT": refcat14,
            "SRSNAME": "EPSG:25830"
        }

        try:
            r = requests.get(
                CFG.CATASTRO_WFS_URL,
                params=params,
                timeout=CFG.CATASTRO_TIMEOUT
            )

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

    def get_parcels_in_bbox(self, bbox: Tuple[float, float, float, float]) -> Optional[gpd.GeoDataFrame]:
        """
        Obtiene todas las parcelas catastrales dentro de un bbox

        Args:
            bbox: (minx, miny, maxx, maxy) en EPSG:25830

        Returns:
            GeoDataFrame con parcelas o None si falla
        """
        minx, miny, maxx, maxy = bbox
        print(f"[Catastro] Obteniendo parcelas en bbox ({maxx-minx:.0f}m x {maxy-miny:.0f}m)...")

        # NOTA: El Catastro WFS estándar usa STOREDQUERY_ID, no soporta BBOX directo
        # Este método intenta usar la API INSPIRE, que puede tener restricciones
        # Para producción, considera usar archivos descargados del Centro de Descargas CNIG

        params = {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAME": "CP.CadastralParcel",  # Nombre de capa INSPIRE
            "SRSNAME": "EPSG:25830",
            "BBOX": f"{minx},{miny},{maxx},{maxy},EPSG:25830"
        }

        try:
            r = requests.get(
                CFG.CATASTRO_WFS_URL,
                params=params,
                timeout=60  # Timeout más largo para consultas grandes
            )

            # El servicio del Catastro puede rechazar consultas muy grandes
            if r.status_code != 200:
                print(f"[Catastro] Error HTTP {r.status_code} - consulta bbox no soportada")
                print(f"[Catastro] Recomendación: usar archivos locales de CNIG")
                return None

            if len(r.content) < 1000 or "Exception" in r.text:
                print(f"[Catastro] Respuesta vacía o con excepción")
                return None

            gdf = gpd.read_file(BytesIO(r.content))

            if gdf.empty:
                print(f"[Catastro] No se encontraron parcelas en el área")
                return None

            # Asegurar CRS correcto
            if gdf.crs is None:
                gdf.set_crs(epsg=25830, inplace=True)
            elif gdf.crs != CFG.ETRS89_UTM30N:
                gdf = gdf.to_crs(CFG.ETRS89_UTM30N)

            # Filtrar geometrías válidas
            gdf = gdf[gdf.is_valid]

            print(f"[Catastro] ✓ {len(gdf)} parcelas obtenidas")
            return gdf

        except Exception as e:
            print(f"[Catastro] Error obteniendo parcelas bbox: {e}")
            print(f"[Catastro] Recomendación: usar archivos locales (.gpkg/.shp)")
            return None

    def get_buildings_in_bbox(self, bbox: Tuple[float, float, float, float]) -> Optional[gpd.GeoDataFrame]:
        """
        Obtiene todas las edificaciones/huellas dentro de un bbox

        Args:
            bbox: (minx, miny, maxx, maxy) en EPSG:25830

        Returns:
            GeoDataFrame con edificios o None si falla
        """
        minx, miny, maxx, maxy = bbox
        print(f"[Catastro] Obteniendo edificios en bbox ({maxx-minx:.0f}m x {maxy-miny:.0f}m)...")

        # NOTA: El Catastro INSPIRE tiene capas de edificios (BU.Building)
        # Pero puede tener restricciones de área máxima por consulta

        params = {
            "SERVICE": "WFS",
            "VERSION": "2.0.0",
            "REQUEST": "GetFeature",
            "TYPENAME": "BU.Building",  # Nombre de capa INSPIRE para edificios
            "SRSNAME": "EPSG:25830",
            "BBOX": f"{minx},{miny},{maxx},{maxy},EPSG:25830"
        }

        try:
            r = requests.get(
                CFG.CATASTRO_WFS_URL,
                params=params,
                timeout=60  # Timeout más largo para consultas grandes
            )

            if r.status_code != 200:
                print(f"[Catastro] Error HTTP {r.status_code} - consulta bbox no soportada")
                print(f"[Catastro] Recomendación: usar archivos locales de CNIG")
                return None

            if len(r.content) < 1000 or "Exception" in r.text:
                print(f"[Catastro] Respuesta vacía o con excepción")
                return None

            gdf = gpd.read_file(BytesIO(r.content))

            if gdf.empty:
                print(f"[Catastro] No se encontraron edificios en el área")
                return None

            # Asegurar CRS correcto
            if gdf.crs is None:
                gdf.set_crs(epsg=25830, inplace=True)
            elif gdf.crs != CFG.ETRS89_UTM30N:
                gdf = gdf.to_crs(CFG.ETRS89_UTM30N)

            # Filtrar geometrías válidas
            gdf = gdf[gdf.is_valid]

            print(f"[Catastro] ✓ {len(gdf)} edificios obtenidos")
            return gdf

        except Exception as e:
            print(f"[Catastro] Error obteniendo edificios bbox: {e}")
            print(f"[Catastro] Recomendación: usar archivos locales (.gpkg/.shp)")
            return None
