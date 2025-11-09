"""
Análisis de límites y vallado de parcela
"""

import math
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from typing import List, Tuple, Optional
import geopandas as gpd

from ..config import CFG
from ..models import ParcelAnalysisResult


class ParcelBoundaryAnalyzer:
    """Analizador de límites de parcela para clasificar frontal/lateral"""

    def __init__(self, catastro_svc, osm_svc):
        """
        Args:
            catastro_svc: Servicio de Catastro
            osm_svc: Servicio de OSM
        """
        self.catastro = catastro_svc
        self.osm = osm_svc

    def analyze(
        self,
        parcel_gdf: gpd.GeoDataFrame,
        refcat14: str,
        bbox: Tuple
    ) -> ParcelAnalysisResult:
        """
        Analiza los límites de una parcela

        Args:
            parcel_gdf: GeoDataFrame con la parcela
            refcat14: Referencia catastral
            bbox: Bounding box para consultas

        Returns:
            ParcelAnalysisResult con información de vallado y edificabilidad
        """
        print("\n--- Analizando Límites ---")

        parcel_geom = parcel_gdf.geometry.iloc[0]
        polys = ([parcel_geom] if parcel_geom.geom_type == 'Polygon'
                 else list(parcel_geom.geoms))
        total_perim = parcel_geom.length

        # Obtener vecinos
        gdf_nei = self.catastro.get_neighbor_parcels(refcat14)
        merged_priv, merged_pub = self._classify_neighbors(gdf_nei, refcat14)

        if merged_priv is None or merged_priv.is_empty:
            return self._all_frontal(parcel_geom, total_perim)

        # Detectar zona de calle
        street_zone = self._detect_street_zone(merged_pub, parcel_geom)

        # Crear anillos exteriores
        outside_ring = parcel_geom.buffer(
            CFG.OUTSIDE_RING_WIDTH,
            join_style=2
        ).difference(parcel_geom.buffer(0, join_style=2))

        priv_out = self._safe_int(outside_ring, merged_priv, CFG.NEIGHBOR_EPSILON)
        pub_cat_out = (self._safe_int(outside_ring, street_zone, CFG.NEIGHBOR_EPSILON)
                       if street_zone else None)

        # OSM
        pub_osm_out = self._fetch_osm_zone(bbox, outside_ring)

        # Clasificar segmentos
        front_segs, lat_segs, stats = self._classify_segments(
            polys, pub_cat_out, pub_osm_out, priv_out
        )

        front_len = unary_union(front_segs).length if front_segs else 0.0
        lat_len = unary_union(lat_segs).length if lat_segs else 0.0

        if (front_len + lat_len) > total_perim * 0.995:
            lat_len = max(0.0, total_perim - front_len)

        # Rescate si no hay frontal
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

        return ParcelAnalysisResult(
            fence_cost, buildable, front_len, lat_len, access_pt
        )

    def _classify_neighbors(self, gdf_nei, refcat14):
        """Clasifica vecinos en privados y públicos"""
        if gdf_nei is None or gdf_nei.empty:
            return None, None

        id_col = ('localId' if 'localId' in gdf_nei.columns
                  else ('label' if 'label' in gdf_nei.columns else None))

        if id_col is None:
            return unary_union(gdf_nei.geometry).buffer(0), None

        gdf_nei = gdf_nei[gdf_nei[id_col].astype(str) != str(refcat14)]
        priv = gdf_nei[gdf_nei[id_col].notna()]
        pub = gdf_nei[gdf_nei[id_col].isna()]

        mp = unary_union(priv.geometry).buffer(0) if not priv.empty else None
        mu = unary_union(pub.geometry).buffer(0) if not pub.empty else None

        return mp, mu

    def _detect_street_zone(self, merged_pub, parcel_geom):
        """Detecta zona de calle desde vecinos públicos"""
        if merged_pub is None or merged_pub.is_empty:
            return None

        pubs = ([merged_pub] if merged_pub.geom_type == 'Polygon'
                else list(merged_pub.geoms))

        boundary_buf = parcel_geom.boundary.buffer(0.10)
        best_len, best_poly = -1.0, None

        for p in pubs:
            if not p.intersects(boundary_buf):
                continue

            A, P = p.area, (p.length if hasattr(p, "length")
                           else p.boundary.length)
            compact = (4.0 * math.pi * A) / (P * P) if P > 0 else 0.0

            try:
                mbr = p.minimum_rotated_rectangle
                coords = list(mbr.exterior.coords)
                edges = [LineString([coords[i], coords[i + 1]])
                        for i in range(4)]
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
        """Intersección segura con buffer de epsilon"""
        if g2 is None or g2.is_empty:
            return None
        result = g1.intersection(g2.buffer(eps))
        return result.buffer(0) if not result.is_empty else None

    def _fetch_osm_zone(self, bbox, outside_ring):
        """Obtiene zona OSM buffereada"""
        try:
            gdf_roads = self.osm.fetch_roads(bbox)
            if gdf_roads.empty:
                return None

            roads_buf = unary_union(
                gdf_roads.buffer(CFG.ROAD_BUFFER, cap_style=2, join_style=2)
            )
            pub_osm = outside_ring.intersection(
                roads_buf.buffer(CFG.NEIGHBOR_EPSILON)
            )
            return pub_osm.buffer(0) if not pub_osm.is_empty else None
        except:
            return None

    def _classify_segments(self, polys, pub_cat, pub_osm, priv):
        """Clasifica segmentos del perímetro en frontal/lateral"""
        front, lat, stats = [], [], []

        for poly in polys:
            coords = list(poly.exterior.coords)

            for i in range(len(coords) - 1):
                seg = LineString([coords[i], coords[i + 1]])

                if seg.length <= 1e-6:
                    continue

                seg_buf = seg.buffer(
                    CFG.SEGMENT_BUFFER,
                    cap_style=2,
                    join_style=2
                )

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
                score = (1.0 * area_osm + 0.7 * area_cat +
                        0.25 / (d_osm_c + 0.1) + 0.10 / (d_cat_c + 0.1))

                stats.append((seg, score, area_osm, area_cat, area_priv))

        return front, lat, stats

    def _int_area(self, g1, g2):
        """Área de intersección"""
        if g2 is None or g2.is_empty:
            return 0.0
        inter = g1.intersection(g2)
        return inter.area if not inter.is_empty else 0.0

    def _rescue(self, stats):
        """Rescate cuando no se detecta frontal"""
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
            rescue_front = (ru if ru.geom_type == "LineString"
                          else sorted(list(ru.geoms),
                                    key=lambda s: s.length,
                                    reverse=True)[0])

        new_front = [seg for seg, *_ in stats
                    if seg.buffer(1e-6).intersects(rescue_front.buffer(1e-6))]
        new_lat = [seg for seg, *_ in stats
                  if not seg.buffer(1e-6).intersects(rescue_front.buffer(1e-6))]

        return new_front, new_lat

    def _fence_cost(self, front_ml, lat_ml):
        """Calcula coste de vallado"""
        GATE_ML = 4.0
        front_ml_facturable = max(front_ml - GATE_ML, 0.0)
        cost = (front_ml_facturable * CFG.COSTE_VALLADO_FRONTAL_ML +
                lat_ml * CFG.COSTE_VALLADO_LATERAL_ML)
        return float(cost)

    def _access_point(self, parcel_geom, front_segs):
        """Calcula punto de acceso"""
        try:
            if front_segs:
                seg_longest = max(front_segs, key=lambda s: s.length)
                return seg_longest.interpolate(0.5, normalized=True)
            return parcel_geom.representative_point()
        except:
            return parcel_geom.representative_point()

    def _buildable(self, parcel_geom, front_segs):
        """Calcula caja edificable"""
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
        """Caso especial: todo el perímetro es frontal"""
        fence_cost = self._fence_cost(total_perim, 0.0)
        buildable = parcel_geom.buffer(-CFG.RETRANQUEO_FRONTAL_M, join_style=2)
        access_pt = parcel_geom.representative_point()

        return ParcelAnalysisResult(
            fence_cost, buildable, total_perim, 0.0, access_pt
        )
