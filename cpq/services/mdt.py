"""
Servicio de descarga de Modelo Digital del Terreno (MDT)
"""

import os
import requests
import zipfile
import geopandas as gpd
from shapely.geometry import box
from typing import Optional, Tuple

from ..config import CFG


class MDTService:
    """
    Servicio para descargar MDT desde diferentes fuentes.
    Prioridad: MDT02 (2m) > MDT05 (5m) > MDT25 (25m)
    """

    MDT02_INDEX_URL = "https://centrodedescargas.cnig.es/CentroDescargas/geojson/MDT02_ETRS89.geojson"

    def _expand_bbox(
        self,
        bbox: Tuple[float, float, float, float],
        extra: float
    ) -> Tuple[float, float, float, float]:
        """Expande un bbox en todas direcciones"""
        minx, miny, maxx, maxy = bbox
        return (minx - extra, miny - extra, maxx + extra, maxy + extra)

    def _download_mdt02_from_index(
        self,
        bbox: Tuple[float, float, float, float],
        out_dir: str = "/tmp/mdt02"
    ) -> Optional[str]:
        """
        Descarga MDT02 usando el índice GeoJSON del CNIG

        Args:
            bbox: Bounding box (minx, miny, maxx, maxy)
            out_dir: Directorio de salida

        Returns:
            Ruta al archivo TIF descargado o None si falla
        """
        try:
            os.makedirs(out_dir, exist_ok=True)

            # Leer índice
            idx_gdf = gpd.read_file(self.MDT02_INDEX_URL)

            if idx_gdf.crs is None:
                idx_gdf.set_crs(epsg=25830, inplace=True)
            else:
                idx_gdf = idx_gdf.to_crs(25830)

            # Buscar hojas que intersectan
            minx, miny, maxx, maxy = map(float, bbox)
            bbox_poly = box(minx, miny, maxx, maxy)
            hits = idx_gdf[idx_gdf.intersects(bbox_poly)]

            if hits.empty:
                print("[MDT] MDT02 índice: ninguna hoja intersecta el bbox")
                return None

            # Obtener URL de descarga
            row = hits.iloc[0]
            download_url = None
            for field in ["link", "enlace", "url", "download"]:
                if field in hits.columns and isinstance(row[field], str):
                    download_url = row[field]
                    break

            if not download_url:
                print("[MDT] MDT02 índice: no se encontró campo de descarga en el GeoJSON")
                return None

            # Descargar
            local_path = os.path.join(out_dir, os.path.basename(download_url))
            print(f"[MDT] Descargando MDT02 por índice: {download_url}")

            r = requests.get(download_url, stream=True, timeout=CFG.MDT_TIMEOUT)
            r.raise_for_status()

            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Extraer si es ZIP
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

    def _try_download_for_bbox(
        self,
        bbox: Tuple[float, float, float, float]
    ) -> Optional[str]:
        """
        Intenta descargar MDT vía WCS en diferentes resoluciones

        Args:
            bbox: Bounding box (minx, miny, maxx, maxy)

        Returns:
            Ruta al archivo descargado o None
        """
        minx, miny, maxx, maxy = map(float, bbox)

        attempts = [
            # MDT02 (2m)
            ("https://servicios.idee.es/wcs-inspire/mdt02", [
                ("SERVICE", "WCS"),
                ("VERSION", "2.0.1"),
                ("REQUEST", "GetCoverage"),
                ("COVERAGEID", "Elevacion25830_2"),
                ("FORMAT", "image/tiff"),
                ("SUBSETTINGCRS", "EPSG:25830"),
                ("SUBSET", f"x({minx},{maxx})"),
                ("SUBSET", f"y({miny},{maxy})"),
            ]),
            # MDT05 (5m)
            ("https://servicios.idee.es/wcs-inspire/mdt", [
                ("SERVICE", "WCS"),
                ("VERSION", "2.0.1"),
                ("REQUEST", "GetCoverage"),
                ("COVERAGEID", "Elevacion25830_5"),
                ("FORMAT", "image/tiff"),
                ("SUBSETTINGCRS", "EPSG:25830"),
                ("SUBSET", f"x({minx},{maxx})"),
                ("SUBSET", f"y({miny},{maxy})"),
            ]),
            # MDT25 (25m)
            ("https://servicios.idee.es/wcs-inspire/mdt", [
                ("SERVICE", "WCS"),
                ("VERSION", "2.0.1"),
                ("REQUEST", "GetCoverage"),
                ("COVERAGEID", "Elevacion25830_25"),
                ("FORMAT", "image/tiff"),
                ("SUBSETTINGCRS", "EPSG:25830"),
                ("SUBSET", f"x({minx},{maxx})"),
                ("SUBSET", f"y({miny},{maxy})"),
            ]),
            # Servicio antiguo
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
                ct = r.headers.get("Content-Type", "").lower()
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
        """
        Descarga MDT con estrategia de fallback

        Args:
            bbox: Bounding box (minx, miny, maxx, maxy)

        Returns:
            Ruta al archivo MDT descargado o None si falla
        """
        print("[MDT] Solicitando topografía (prioridad MDT02 por índice)…")

        # Intento 1: MDT02 por índice
        path = self._download_mdt02_from_index(bbox)
        if path:
            return path

        # Intento 2: WCS bbox original
        print("[MDT] Pasando a WCS (2 m → 5 m → 25 m)…")
        path = self._try_download_for_bbox(bbox)
        if path:
            return path

        # Intento 3: bbox +25m
        bbox_big = self._expand_bbox(bbox, 25.0)
        print("[MDT] Reintentando WCS con bbox +25 m…")
        path = self._try_download_for_bbox(bbox_big)
        if path:
            return path

        # Intento 4: bbox +50m
        bbox_bigger = self._expand_bbox(bbox, 50.0)
        print("[MDT] Reintentando WCS con bbox +50 m…")
        path = self._try_download_for_bbox(bbox_bigger)
        if path:
            return path

        print("[MDT] ✗ No se pudo descargar ningún MDT")
        return None
