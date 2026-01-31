# Urbanismo Proxy - Motor de Inferencia Urbanística

## 🎯 Qué es y Para Qué Sirve

El **Urbanismo Proxy** es un sistema de **inferencia estadística basada en contexto** que aprende de las edificaciones vecinas para estimar parámetros urbanísticos reales.

### Problema que Resuelve

En CPQ usamos valores por defecto del config:
```python
RETRANQUEO_FRONTAL_M = 5.0
RETRANQUEO_LATERAL_M = 3.0
OCUPACION_PORCENTAJE = 30.0
EDIFICABILIDAD_M2T_M2S = 0.4
```

**Pero la realidad construida es diferente en cada zona:**
- En barrios antiguos: retranqueos ~2m, ocupación ~50%
- En urbanizaciones nuevas: retranqueos ~4m, ocupación ~25%
- En zona industrial: ocupación ~70%

### Solución

El proxy **analiza 250m alrededor de tu parcela** y calcula:

1. **Retranqueos reales** (frontal/lateral/fondo) observados
2. **Ocupación típica** del entorno
3. **Edificabilidad inferida** (ocupación × plantas)
4. **Confianza estadística** del resultado

Si la confianza es **alta o media**, sustituye los defaults.

---

## 🧠 Cómo Funciona (Arquitectura)

### 1. Inputs Necesarios

```python
from cpq.analysis import compute_urbanismo_proxy, ProxyConfig

# 3 capas GIS obligatorias:
target_parcel_gdf   # Tu parcela (1 polígono)
parcels_gdf         # Parcelas vecinas (catastro)
buildings_gdf       # Huellas edificaciones (catastro)

# 1 capa opcional (mejora mucho):
roads_gdf           # Viales OSM (para detectar frente)
```

### 2. Configuración

```python
cfg = ProxyConfig(
    radius_m=250,                       # búsqueda 250m
    min_neighbors=10,                   # mínimo 10 vecinos
    min_building_area_m2=35,           # ignora trasteros <35m²
    use_comparable_parcels=True,        # solo parcelas ±50% área
    comparable_area_tolerance=0.50,     # rango ±50%
    building_selection_mode="smart",    # edificio principal
    use_road_classification=True,       # usar OSM para frente
    road_buffer_m=15.0                  # 15m desde vial = frente
)
```

### 3. Ejecución

```python
result = compute_urbanismo_proxy(
    target_parcel_gdf=target_gdf,
    parcels_gdf=all_parcels,
    buildings_gdf=all_buildings,
    roads_gdf=osm_roads,    # opcional
    cfg=cfg
)
```

### 4. Outputs

```python
# Parámetros inferidos (listos para usar):
result.retranqueo_frontal_m      # ej: 3.2m (vs default 5m)
result.retranqueo_lateral_m      # ej: 2.8m (vs default 3m)
result.retranqueo_fondo_m        # ej: 2.5m
result.ocupacion_max             # ej: 0.42 (vs default 0.30)
result.edificabilidad_m2t_m2s    # ej: 0.63 (vs default 0.40)

# Confianza:
result.confidence_score          # 0.78 (score 0-1)
result.confidence_label          # "alta" / "media" / "baja"
result.use_proxy                 # True si score >= 0.50

# Envolvente edificable:
result.buildable_envelope        # Polygon con retranqueos
result.buildable_area_m2         # Área edificable real

# Estadísticos detallados:
result.stats.distances_frontal_m  # {p10, p25, p50, p75, p90, mean, std, iqr}
result.stats.occupancy            # estadísticos de ocupación
result.df_neighbors               # DataFrame con cada vecino
```

---

## 🔍 Mejoras Clave vs. Código Original

### ✅ 1. Retranqueos por Lado (Frente/Lateral/Fondo)

**Antes**: Solo distancia mínima global
**Ahora**: Retranqueos diferenciados

**Método**:
```python
def classify_parcel_sides(parcel_geom, roads_gdf):
    # 1. Si hay viales OSM cercanos:
    #    - El lado que toca vial buffereado → FRONTAL
    #    - El opuesto → FONDO
    #    - Los otros dos → LATERAL

    # 2. Si no hay viales:
    #    - Lado más largo → FRONTAL (heurística)
```

**Ejemplo visual**:
```
    [VIAL OSM]
    +---------+
    | FRONTAL | ← detectado por proximidad a vial
    |         |
LAT |  CASA   | LAT
    |         |
    |  FONDO  |
    +---------+
```

### ✅ 2. Selección Inteligente de Edificio Principal

**Antes**: Solo edificio más grande
**Ahora**: 3 modos

**Modo "smart" (default)**:
```python
score = 0.50 × área_normalizada
      + 0.30 × centralidad          # cerca del centroide
      + 0.20 × compacidad           # forma compacta
```

**Por qué**:
- Evita marcar retranqueo=0 por un cobertizo pegado a la linde
- El edificio "principal" está centrado y es compacto

**Ejemplo**:
```
Parcela con 3 edificios:
┌──────────────────────┐
│ [Trastero 20m²]      │ ← grande pero no central
│                      │
│    [Casa 85m²]       │ ← PRINCIPAL (smart)
│                      │
│ [Piscina 40m²]       │ ← compacta pero pequeña
└──────────────────────┘
```

### ✅ 3. Filtro por Parcelas Comparables

**Antes**: Todas las parcelas en radio
**Ahora**: Solo las de área similar

```python
# Si target = 800 m² y tolerance = 0.50:
# Solo usa parcelas entre 400-1200 m²
```

**Por qué**:
- Evita contaminar con parcelas de diferente tipología
- Una parcela de 2000m² tiene diferente ocupación que una de 500m²

### ✅ 4. Estadísticos Robustos

**Métricas calculadas**:
- **Percentiles**: p10, p25, **p50** (mediana), p75, p90
- **Dispersión**: IQR (rango intercuartílico)
- **Media y desviación típica**

**Uso recomendado**:
```python
# Retranqueo CONSERVADOR (seguro):
usar p25 o p10

# Retranqueo TÍPICO (equilibrado):
usar p50 (mediana) ← DEFAULT

# Retranqueo AGRESIVO (optimista):
usar p75 o p90
```

---

## 📊 Sistema de Confianza

### Componentes del Score

```python
score = 0.40 × tamaño_muestra      # ≥10 vecinos → mejor
      + 0.25 × dispersión_frontal   # IQR bajo → mejor
      + 0.20 × dispersión_lateral
      + 0.15 × dispersión_ocupación
```

### Interpretación

| Score | Label | Acción CPQ |
|-------|-------|-----------|
| ≥0.75 | **Alta** | Usar proxy con confianza |
| 0.50-0.75 | **Media** | Usar proxy (avisar usuario) |
| <0.50 | **Baja** | Usar defaults (entorno heterogéneo) |

### Factores que Bajan Confianza

1. **Pocos vecinos**: <10 parcelas comparables
2. **Alta dispersión**: IQR > 50% de la mediana
3. **Entorno mixto**: residencial + industrial
4. **Datos faltantes**: muchos solares vacíos

---

## 🔗 Integración en CPQ

### Flujo Propuesto

```python
# main.py (simplificado)

# 1. Obtener parcela objetivo
gdf_parcel = catastro_svc.get_parcel_geometry(refcat14)

# 2. Obtener contexto (parcelas + edificios)
bbox = bbox_from_gdf(gdf_parcel, buffer=300)  # +50m extra

parcels_nearby = catastro_svc.get_parcels_in_bbox(bbox)
buildings_nearby = catastro_svc.get_buildings_in_bbox(bbox)
roads_nearby = osm_svc.fetch_roads(bbox)

# 3. Ejecutar proxy
proxy_result = compute_urbanismo_proxy(
    target_parcel_gdf=gdf_parcel,
    parcels_gdf=parcels_nearby,
    buildings_gdf=buildings_nearby,
    roads_gdf=roads_nearby,
    cfg=ProxyConfig()
)

# 4. Decidir: ¿usar proxy o defaults?
if proxy_result.use_proxy:
    print(f"[PROXY] Confianza {proxy_result.confidence_label}")
    print(f"  Retranqueo frontal: {proxy_result.retranqueo_frontal_m:.2f}m")
    print(f"  Retranqueo lateral: {proxy_result.retranqueo_lateral_m:.2f}m")
    print(f"  Ocupación máxima: {proxy_result.ocupacion_max*100:.1f}%")

    # USAR VALORES PROXY
    retranqueo_frontal = proxy_result.retranqueo_frontal_m
    retranqueo_lateral = proxy_result.retranqueo_lateral_m
    max_ocupacion = proxy_result.ocupacion_max

    # Usar envolvente edificable del proxy
    buildable_geom = proxy_result.buildable_envelope

else:
    print(f"[DEFAULT] Confianza {proxy_result.confidence_label} - usando config")

    # USAR DEFAULTS
    retranqueo_frontal = CFG.RETRANQUEO_FRONTAL_M
    retranqueo_lateral = CFG.RETRANQUEO_LATERAL_M
    max_ocupacion = CFG.OCUPACION_PORCENTAJE / 100.0

    # Calcular buildable normal
    buildable_geom = gdf_parcel.geometry.iloc[0].buffer(-retranqueo_lateral)

# 5. Continuar con filtrado de modelos, etc.
valid_models = filter_valid_models(
    num_bedrooms,
    parcel_area_m2,
    buildable_geom.area  # ← área edificable real
)
```

---

## 📈 Ejemplo Real de Salida

```python
# Parcela de 750 m² en urbanización años 90

result = compute_urbanismo_proxy(...)

print(result.stats.distances_frontal_m)
# {
#   'p10': 2.8,
#   'p25': 3.1,
#   'p50': 3.5,   ← MEDIANA (recomendado)
#   'p75': 4.2,
#   'p90': 5.1,
#   'mean': 3.7,
#   'std': 0.9,
#   'iqr': 1.1    ← Dispersión moderada
# }

print(result.stats.occupancy)
# {
#   'p50': 0.38,  ← 38% ocupación típica
#   'iqr': 0.08   ← Muy consistente
# }

print(result.confidence)
# {
#   'score': 0.82,
#   'label': 'alta',
#   'n_used': 18,
#   'size_score': 1.0,      ← 18 vecinos (>10 min)
#   'frontal_score': 0.75,  ← dispersión aceptable
#   'occ_score': 0.90       ← muy consistente
# }

# DECISIÓN:
result.use_proxy = True

# PARÁMETROS INFERIDOS:
result.retranqueo_frontal_m = 3.5    # vs default 5.0
result.retranqueo_lateral_m = 3.2    # vs default 3.0
result.ocupacion_max = 0.42          # vs default 0.30
result.edificabilidad_m2t_m2s = 0.63 # vs default 0.40

# GANANCIA:
# Buildable area aumentó un 15% respecto a defaults
# Ocupación permitida subió de 225 m² a 315 m²
```

---

## ⚠️ Limitaciones y Casos Especiales

### 1. Entornos Heterogéneos

**Problema**: Barrio mixto (casas + naves)
**Síntoma**: Confianza baja, IQR alto
**Solución**: Ajustar `comparable_area_tolerance` a ±30%

### 2. Zonas sin Edificar

**Problema**: Urbanización nueva, muchos solares
**Síntoma**: n_used < 5
**Solución**: Aumentar `radius_m` a 500m

### 3. Catastro con Errores

**Problema**: Huellas mal alineadas o desactualizadas
**Síntoma**: Ocupaciones >0.90 o retranqueos =0
**Solución**: Ajustar `occupancy_clip` y `min_building_area_m2`

### 4. Sin Viales OSM

**Problema**: Zona rural sin viales en OSM
**Síntoma**: Todos los lados clasificados igual
**Solución**: Se usa lado más largo como frente (heurística)

---

## 🛠️ Configuración Avanzada

### Perfil Conservador (Promotor Prudente)

```python
cfg = ProxyConfig(
    radius_m=200,                      # búsqueda más local
    min_neighbors=15,                  # más exigente
    comparable_area_tolerance=0.30,    # solo muy similares
    building_selection_mode="centroid", # edificio más central
)

# Usar percentil bajo:
retranqueo = result.stats.distances_frontal_m['p25']
```

### Perfil Agresivo (Maximizar Aprovechamiento)

```python
cfg = ProxyConfig(
    radius_m=300,                      # búsqueda más amplia
    min_neighbors=8,                   # menos exigente
    comparable_area_tolerance=0.60,    # rango más amplio
    building_selection_mode="largest",
)

# Usar percentil alto:
retranqueo = result.stats.distances_frontal_m['p75']
ocupacion = result.stats.occupancy['p90']
```

---

## 📚 Casos de Uso en CPQ

### Caso 1: Sustituir Defaults Globalmente

```python
# Ejecutar proxy una vez al inicio
proxy = compute_urbanismo_proxy(...)

if proxy.use_proxy:
    # Sobrescribir config temporalmente
    CFG.RETRANQUEO_FRONTAL_M = proxy.retranqueo_frontal_m
    CFG.RETRANQUEO_LATERAL_M = proxy.retranqueo_lateral_m
    CFG.OCUPACION_PORCENTAJE = proxy.ocupacion_max * 100
    CFG.EDIFICABILIDAD_M2T_M2S = proxy.edificabilidad_m2t_m2s
```

### Caso 2: Usar Solo para Envolvente

```python
# Mantener defaults pero usar envolvente proxy
buildable_gdf = gpd.GeoDataFrame(
    [{"geometry": proxy.buildable_envelope}],
    crs=CFG.ETRS89_UTM30N
)

huella_gdf = create_house_pad(buildable_gdf, width, length)
```

### Caso 3: Modo Híbrido (Conservador)

```python
# Usar el más restrictivo entre proxy y defaults
retranqueo_frontal = max(
    proxy.retranqueo_frontal_m,
    CFG.RETRANQUEO_FRONTAL_M
)
```

---

## 📊 Reportes para Cliente

```python
def generar_informe_proxy(result: ProxyResult):
    """Genera informe legible para el cliente"""

    print("="*60)
    print("ANÁLISIS DE ENTORNO CONSTRUIDO")
    print("="*60)
    print(f"\nConfianza: {result.confidence_label.upper()}")
    print(f"Score: {result.confidence_score:.2f}/1.00")
    print(f"\nVecinos analizados: {result.stats.n_parcels_used}")
    print(f"Parcelas comparables: {result.stats.n_comparables}")

    print("\n--- RETRANQUEOS OBSERVADOS ---")
    print(f"Frontal:  {result.retranqueo_frontal_m:.2f}m "
          f"(rango {result.stats.distances_frontal_m['p25']:.1f}-"
          f"{result.stats.distances_frontal_m['p75']:.1f}m)")
    print(f"Lateral:  {result.retranqueo_lateral_m:.2f}m "
          f"(rango {result.stats.distances_lateral_m['p25']:.1f}-"
          f"{result.stats.distances_lateral_m['p75']:.1f}m)")

    print("\n--- OCUPACIÓN TÍPICA ---")
    print(f"Mediana: {result.stats.occupancy['p50']*100:.1f}%")
    print(f"Rango:   {result.stats.occupancy['p25']*100:.1f}%-"
          f"{result.stats.occupancy['p75']*100:.1f}%")

    print("\n--- RECOMENDACIÓN ---")
    if result.use_proxy:
        print("✓ Usar parámetros inferidos del entorno")
    else:
        print("⚠ Usar valores normativos por defecto")
        print("  (Entorno heterogéneo o datos insuficientes)")

    print("="*60)
```

---

## 🔮 Futuras Mejoras

1. **Plantas por edificio**: OCR de alturas catastro
2. **Tipología edificatoria**: Clasificar adosado/aislado/pareado
3. **Temporalidad**: Pesar más edificios recientes
4. **Machine Learning**: Predicción de parámetros con más features
5. **Validación cruzada**: Comparar con PGOU real

---

**Versión**: 1.0.0
**Integración CPQ**: v4.5+
**Autor**: Buildlovers Tech Team
**Última actualización**: 2025-01-31
