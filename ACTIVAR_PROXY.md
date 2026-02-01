# Activar el Urbanismo Proxy en CPQ

## 🎯 El Proxy Está Integrado pero Desactivado

El motor de Urbanismo Proxy ya está **completamente integrado** en `main.py`, pero está **desactivado por defecto** porque requiere capas adicionales del Catastro que no se obtienen automáticamente.

---

## 🔧 Cómo Activar el Proxy

### Paso 1: Obtener las Capas Necesarias

El proxy necesita **3 capas GIS**:

1. ✅ **Parcela objetivo** - Ya se obtiene automáticamente
2. ❌ **Parcelas vecinas** - Necesitas implementar
3. ❌ **Edificios/huellas** - Necesitas implementar
4. ✅ **Viales OSM** - Ya se obtiene automáticamente

---

## 📁 Opción A: Usar Archivos Locales (Más Fácil)

### 1.1 Descargar Capas del Catastro

Descarga las capas completas de tu municipio desde:
- **Catastro INSPIRE**: https://www.catastro.meh.es/webinspire/index.html
- **Centro de Descargas del CNIG**: https://centrodedescargas.cnig.es/

Necesitas:
- `CATASTRAL_PARCELS.shp` o `.gpkg` - Parcelas catastrales
- `CATASTRAL_BUILDINGS.shp` o `.gpkg` - Edificaciones

### 1.2 Guardar en el Proyecto

```bash
mkdir -p /home/user/CPQ/data

# Copiar tus archivos aquí:
cp ruta/a/parcelas.gpkg /home/user/CPQ/data/parcels.gpkg
cp ruta/a/edificios.gpkg /home/user/CPQ/data/buildings.gpkg
```

### 1.3 Modificar main.py

En `main.py`, línea ~115, reemplaza:

```python
# Por ahora, simulamos que no están disponibles
parcels_nearby = None
buildings_nearby = None
```

Por:

```python
# Leer desde archivos locales
import geopandas as gpd
from shapely.geometry import box

# Crear bbox para filtro espacial
bbox_geom = box(*bbox_proxy)

# Leer solo las geometrías dentro del bbox (más eficiente)
parcels_nearby = gpd.read_file(
    "/home/user/CPQ/data/parcels.gpkg",
    bbox=bbox_proxy
)

buildings_nearby = gpd.read_file(
    "/home/user/CPQ/data/buildings.gpkg",
    bbox=bbox_proxy
)

print(f"  ✓ Parcelas cargadas: {len(parcels_nearby)}")
print(f"  ✓ Edificios cargados: {len(buildings_nearby)}")
```

### 1.4 Activar el Flag

En `main.py`, línea ~89, cambiar:

```python
USE_PROXY = False  # Cambiar a True
```

A:

```python
USE_PROXY = True  # ¡ACTIVADO!
```

---

## 📡 Opción B: Usar Servicios WFS (Más Avanzado)

### 2.1 Extender CatastroService

Añadir métodos para obtener múltiples parcelas y edificios:

```python
# En cpq/services/catastro.py

def get_parcels_in_bbox(self, bbox: Tuple) -> Optional[gpd.GeoDataFrame]:
    """
    Obtiene todas las parcelas en un bbox

    Args:
        bbox: (minx, miny, maxx, maxy) en EPSG:25830

    Returns:
        GeoDataFrame con parcelas
    """
    minx, miny, maxx, maxy = bbox

    # WFS GetFeature con filtro espacial
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAME": "CP.CadastralParcel",  # Revisar nombre exacto
        "SRSNAME": "EPSG:25830",
        "BBOX": f"{minx},{miny},{maxx},{maxy},EPSG:25830"
    }

    try:
        r = requests.get(self.WFS_URL, params=params, timeout=60)
        r.raise_for_status()

        gdf = gpd.read_file(BytesIO(r.content))
        if gdf.crs != CFG.ETRS89_UTM30N:
            gdf = gdf.to_crs(CFG.ETRS89_UTM30N)

        return gdf

    except Exception as e:
        print(f"Error obteniendo parcelas: {e}")
        return None


def get_buildings_in_bbox(self, bbox: Tuple) -> Optional[gpd.GeoDataFrame]:
    """
    Obtiene edificios/huellas en un bbox

    Similar a get_parcels_in_bbox pero con typename para edificios
    """
    # Implementación similar...
    pass
```

### 2.2 Usar en main.py

```python
# En main.py, línea ~106
parcels_nearby = catastro_svc.get_parcels_in_bbox(bbox_proxy)
buildings_nearby = catastro_svc.get_buildings_in_bbox(bbox_proxy)
```

---

## 🧪 Verificar que Funciona

### Ejecutar con Proxy Activado

```bash
python main.py
```

Deberías ver:

```
============================================================
ANÁLISIS DE CONTEXTO URBANÍSTICO (PROXY)
============================================================

[PROXY] Analizando entorno construido (250m)...
  ✓ Parcelas cargadas: 45
  ✓ Edificios cargados: 38

[PROXY] Análisis completado
  Confianza: ALTA (score: 0.82)
  Vecinos analizados: 18
  Parcelas comparables: 15

  ✓ USANDO PARÁMETROS INFERIDOS DEL ENTORNO
    Retranqueo frontal: 3.5m (default: 5.0m)
    Retranqueo lateral: 2.8m (default: 3.0m)
    Ocupación máxima: 42.0% (default: 30.0%)
    Edificabilidad: 0.63 (default: 0.40)

[PROXY] Usando envolvente edificable inferida: 315.00 m²
```

---

## 📊 Qué Hace el Proxy Cuando Está Activo

1. **Analiza 250m alrededor** de tu parcela
2. **Filtra parcelas comparables** (±50% área similar)
3. **Identifica edificio principal** de cada parcela (smart mode)
4. **Clasifica lados** (frontal/lateral/fondo usando viales OSM)
5. **Calcula retranqueos** por cada lado
6. **Infiere ocupación y edificabilidad** real
7. **Calcula confianza** estadística (alta/media/baja)
8. **Sustituye defaults** si confianza >= 50%

---

## ⚙️ Configuración Avanzada

### Ajustar Parámetros del Proxy

En `main.py`, línea ~129, puedes personalizar:

```python
proxy_result = compute_urbanismo_proxy(
    target_parcel_gdf=gdf_parcel,
    parcels_gdf=parcels_nearby,
    buildings_gdf=buildings_nearby,
    roads_gdf=roads_gdf if not roads_gdf.empty else None,
    cfg=ProxyConfig(
        radius_m=300,                      # Aumentar radio de búsqueda
        min_neighbors=15,                  # Más exigente
        comparable_area_tolerance=0.30,    # Solo parcelas muy similares
        building_selection_mode="smart",   # smart/largest/centroid
        use_road_classification=True       # Usar OSM para detectar frente
    )
)
```

### Perfiles Predefinidos

```python
# CONSERVADOR (promotor prudente)
cfg = ProxyConfig(
    radius_m=200,
    min_neighbors=15,
    comparable_area_tolerance=0.30
)

# EQUILIBRADO (default)
cfg = ProxyConfig()

# AGRESIVO (maximizar aprovechamiento)
cfg = ProxyConfig(
    radius_m=300,
    min_neighbors=8,
    comparable_area_tolerance=0.60
)
```

---

## 🐛 Troubleshooting

### Error: "No se encontraron parcelas/edificios"

**Causa**: El archivo está vacío o el bbox no intersecta
**Solución**: Verifica que los archivos contengan datos del área

```python
import geopandas as gpd
parcels = gpd.read_file("data/parcels.gpkg")
print(f"Total parcelas: {len(parcels)}")
print(f"Bounds: {parcels.total_bounds}")
```

### Error: "CRS no coincide"

**Causa**: Las capas no están en EPSG:25830
**Solución**: Reproyectar antes de usar

```python
parcels = gpd.read_file("data/parcels.gpkg")
if parcels.crs != "EPSG:25830":
    parcels = parcels.to_crs("EPSG:25830")
    parcels.to_file("data/parcels_25830.gpkg", driver="GPKG")
```

### Confianza siempre BAJA

**Causa**: Entorno muy heterogéneo o pocos vecinos
**Solución**:
- Aumentar `radius_m` a 400-500m
- Reducir `comparable_area_tolerance` a 0.30
- Verificar que hay edificios en las parcelas

---

## 📝 Checklist de Activación

- [ ] Descargar capas de parcelas y edificios del Catastro
- [ ] Guardar en `/home/user/CPQ/data/` como `.gpkg` o `.shp`
- [ ] Verificar que están en EPSG:25830
- [ ] Modificar `main.py` línea ~115 para leer archivos
- [ ] Cambiar `USE_PROXY = True` en línea ~89
- [ ] Ejecutar `python main.py` y verificar output
- [ ] Ajustar `ProxyConfig` si es necesario

---

## 🎯 Resultado Esperado

Con el proxy activado, el CPQ usará:

| Parámetro | Sin Proxy (Default) | Con Proxy (Ejemplo) | Ganancia |
|-----------|---------------------|---------------------|----------|
| Retranqueo frontal | 5.0m | 3.5m | +30% superficie |
| Retranqueo lateral | 3.0m | 2.8m | Mejor ajuste |
| Ocupación | 30% | 42% | +40% aprovechamiento |
| Edificabilidad | 0.40 | 0.63 | +57% edificable |
| Área edificable | 225 m² | 315 m² | **+40%** |

---

## 📚 Documentación Completa

- `URBANISMO_PROXY.md` - Arquitectura y funcionamiento
- `example_proxy_integration.py` - Ejemplos de uso
- `cpq/analysis/urbanismo_proxy.py` - Código fuente

---

**Última actualización**: 2025-01-31
**Versión CPQ**: 4.5+
