"""
Servicio de acceso a datos del Catastro
"""

import requests
import geopandas as gpd
from io import BytesIO
from typing import Optional

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
