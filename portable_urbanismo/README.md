# urbanismo_proxy — módulo portable

Copia **autocontenida** de `cpq/analysis/urbanismo_proxy.py`, sin dependencias del
paquete CPQ. Infiere parámetros urbanísticos (retranqueos, ocupación y
edificabilidad) observando las parcelas y edificios del entorno de una parcela.

La lógica de cálculo es **idéntica** al módulo original. Lo único que cambia es
que las 4 constantes por defecto (antes `cpq.config.CFG`) están definidas
localmente dentro del propio archivo, en la clase `_UrbanDefaults`/`CFG`.

## Cómo integrarlo

Es un único archivo. Cópialo a tu proyecto y úsalo como un módulo normal:

```
tu_proyecto/
└── urbanismo_proxy.py   ← copia este archivo
```

```python
from urbanismo_proxy import compute_urbanismo_proxy, ProxyConfig, ProxyResult
```

## Dependencias

```bash
pip install "geopandas>=0.12" "shapely>=2.0" numpy
# pandas y pyproj entran de forma transitiva con geopandas
```

(o `pip install -r requirements.txt`)

## Contrato de entrada

`compute_urbanismo_proxy(target_parcel_gdf, parcels_gdf, buildings_gdf, roads_gdf=None, cfg=ProxyConfig())`

| Argumento           | Tipo                | Descripción                                            |
|---------------------|---------------------|--------------------------------------------------------|
| `target_parcel_gdf` | `GeoDataFrame` (1 fila) | Parcela objetivo                                    |
| `parcels_gdf`       | `GeoDataFrame`      | Parcelas del entorno                                   |
| `buildings_gdf`     | `GeoDataFrame`      | Huellas de edificios                                   |
| `roads_gdf`         | `GeoDataFrame` o `None` | Viales (opcional; mejora la detección de frente)   |
| `cfg`               | `ProxyConfig`       | Parámetros de búsqueda y filtrado                      |

> **Requisito de CRS:** todos los GeoDataFrame deben estar en un CRS **proyectado
> en metros** (p. ej. EPSG:25830). Con lat/lon (EPSG:4326) la función lanza error.
> El módulo solo usa **geometría**: no lee atributos catastrales.

El módulo **no descarga datos**: es una función pura. La obtención de parcelas,
edificios y viales corre por cuenta del proyecto que lo usa (WFS Catastro, ficheros
locales `.gpkg/.shp`, Overpass/OSM, etc.).

## Salida (`ProxyResult`)

```python
res = compute_urbanismo_proxy(target, parcels, buildings, roads)

res.use_proxy              # bool: True si la confianza ≥ 0.50
res.confidence_score       # float [0, 1]
res.confidence_label       # "alta" | "media" | "baja"

res.retranqueo_frontal_m   # mediana (p50) del retranqueo a vial de los vecinos
res.retranqueo_lateral_m   # mediana (p50) del retranqueo lateral
res.retranqueo_fondo_m     # (usa la mediana lateral; ver nota)
res.ocupacion_max          # percentil 75 de la ocupación observada
res.edificabilidad_m2t_m2s # ocupacion_max * floors_avg

res.buildable_envelope     # Polygon: parcela retranqueada (buffer interior)
res.buildable_area_m2      # float
res.stats                  # ProxyStats con percentiles/IQR por lado
res.df_neighbors           # DataFrame con cada vecino analizado
```

## Ejemplo mínimo

```python
import geopandas as gpd
from urbanismo_proxy import compute_urbanismo_proxy, ProxyConfig

target    = gpd.read_file("target.gpkg").to_crs(25830)   # 1 fila
parcels   = gpd.read_file("parcels.gpkg").to_crs(25830)
buildings = gpd.read_file("buildings.gpkg").to_crs(25830)
roads     = gpd.read_file("roads.gpkg").to_crs(25830)    # opcional

res = compute_urbanismo_proxy(
    target_parcel_gdf=target,
    parcels_gdf=parcels,
    buildings_gdf=buildings,
    roads_gdf=roads,
    cfg=ProxyConfig(radius_m=250.0, min_neighbors=10),
)

if res.use_proxy:
    print(f"Retranqueo frontal: {res.retranqueo_frontal_m:.2f} m")
    print(f"Ocupación máx.:     {res.ocupacion_max*100:.1f} %")
    print(f"Edificabilidad:     {res.edificabilidad_m2t_m2s:.2f} m²t/m²s")
else:
    print(f"Confianza {res.confidence_label}: conviene usar tus valores por defecto")
```

## Ajustar los valores por defecto

Los fallbacks (cuando no hay datos o el estadístico es NaN) están al principio del
archivo:

```python
@dataclass(frozen=True)
class _UrbanDefaults:
    OCUPACION_PORCENTAJE: float = 30.0
    EDIFICABILIDAD_M2T_M2S: float = 0.4
    RETRANQUEO_FRONTAL_M: float = 5.0
    RETRANQUEO_LATERAL_M: float = 3.0
```

Edítalos para adaptarlos a tu normativa base.

## Notas / limitaciones heredadas del original

- El **retranqueo de fondo** inferido reutiliza la mediana **lateral** (comportamiento
  idéntico al módulo original); las estadísticas de fondo se calculan y exponen en
  `res.stats` pero no gobiernan ese valor.
- `floors_avg = mediana(ocupación) * 1.5` es una estimación tosca: no se leen plantas
  reales, por lo que la edificabilidad es **derivada**, no observada.
- La envolvente edificable aplica un **buffer interior uniforme** (media ponderada de
  retranqueos), no un retranqueo diferenciado por lado.
- Pensado para parcelas sensiblemente cuadrangulares (la clasificación frente/fondo
  asume el lado opuesto). Para formas muy irregulares la clasificación es aproximada.
