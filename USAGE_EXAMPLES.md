# Ejemplos de Uso - CPQ v4.5

Este documento muestra cómo usar los módulos internos del sistema para casos de uso avanzados.

---

## 📚 Tabla de Contenidos

- [Uso Básico](#uso-básico)
- [Servicios Externos](#servicios-externos)
- [Análisis de Parcela](#análisis-de-parcela)
- [Cálculos Topográficos](#cálculos-topográficos)
- [Cálculos de Costes](#cálculos-de-costes)
- [Utilidades](#utilidades)
- [Integración en Otros Proyectos](#integración-en-otros-proyectos)

---

## Uso Básico

### Ejecutar el programa interactivo

```bash
python main.py
```

---

## Servicios Externos

### Consultar Catastro

```python
from cpq.services import CatastroService

# Inicializar servicio
catastro = CatastroService()

# Obtener geometría de parcela
refcat = "1234567AB1234C"
gdf = catastro.get_parcel_geometry(refcat)

if gdf is not None:
    print(f"Área: {gdf.geometry.iloc[0].area:.2f} m²")
    print(f"CRS: {gdf.crs}")

# Obtener parcelas vecinas
neighbors = catastro.get_neighbor_parcels(refcat)
if neighbors is not None:
    print(f"Vecinos: {len(neighbors)}")
```

### Descargar MDT

```python
from cpq.services import MDTService

mdt = MDTService()

# Definir bbox (minx, miny, maxx, maxy)
bbox = (300000, 4500000, 301000, 4501000)

# Descargar MDT (intenta varias fuentes)
mdt_path = mdt.download_mdt(bbox)

if mdt_path:
    print(f"MDT descargado en: {mdt_path}")
else:
    print("No se pudo descargar MDT")
```

### Consultar OSM

```python
from cpq.services import OSMService

osm = OSMService()

# Consultar carreteras en bbox
bbox = (300000, 4500000, 301000, 4501000)
roads = osm.fetch_roads(bbox)

print(f"Carreteras encontradas: {len(roads)}")
for idx, road in roads.iterrows():
    print(f"  - Longitud: {road.geometry.length:.2f} m")
```

---

## Análisis de Parcela

### Analizar límites y vallado

```python
from cpq.services import CatastroService, OSMService
from cpq.analysis import ParcelBoundaryAnalyzer
from cpq.utils import bbox_from_gdf

# Inicializar servicios
catastro = CatastroService()
osm = OSMService()

# Obtener parcela
refcat = "1234567AB1234C"
gdf = catastro.get_parcel_geometry(refcat)

# Crear analizador
analyzer = ParcelBoundaryAnalyzer(catastro, osm)

# Analizar
bbox = bbox_from_gdf(gdf, buffer=20.0)
result = analyzer.analyze(gdf, refcat, bbox)

# Resultados
print(f"Coste de vallado: {result.fence_cost:,.2f} €")
print(f"Longitud frontal: {result.frontal_length_m:.2f} m")
print(f"Longitud lateral: {result.lateral_length_m:.2f} m")
print(f"Área edificable: {result.buildable_geometry.area:.2f} m²")
print(f"Punto de acceso: {result.access_point}")
```

---

## Cálculos Topográficos

### Calcular volúmenes de movimiento de tierras

```python
from cpq.analysis import compute_volume_metrics
import geopandas as gpd

# Suponer que ya tienes huella_gdf y mdt_path
vol_metrics = compute_volume_metrics(huella_gdf, mdt_path)

print(f"Cota óptima: {vol_metrics['z_optimal_m']:.2f} m")
print(f"Desmonte: {vol_metrics['cut_m3']:.2f} m³")
print(f"Terraplén: {vol_metrics['fill_m3']:.2f} m³")
print(f"Balance: {vol_metrics['balance_m3']:.2f} m³")
```

### Calcular pendiente

```python
from cpq.analysis import get_xyz_from_pad, calc_pendiente

# Extraer puntos XYZ
xs, ys, zs = get_xyz_from_pad(huella_gdf, mdt_path)

if xs is not None:
    # Calcular pendiente
    p_eo, p_ns, p_total, direccion = calc_pendiente(xs, ys, zs)

    print(f"Pendiente Este-Oeste: {p_eo:.2f}%")
    print(f"Pendiente Norte-Sur: {p_ns:.2f}%")
    print(f"Pendiente total: {p_total:.2f}%")
    print(f"Dirección: {direccion:.2f}°")
```

### Dimensionar muros de contención

```python
from cpq.analysis import dimensionar_muro_perimetral_real

# Suponer que tienes mdt_path, huella_gdf, parcel_geom, cota_plataforma
muro = dimensionar_muro_perimetral_real(
    mdt_path=mdt_path,
    pad_gdf=huella_gdf,
    parcel_geom=parcel_geom,
    cota_plataforma=100.5,  # metros
    paso_perfil=1.0,
    terreno_blando=False
)

print(f"Tipo de muro: {muro['tipo_muro_elegido']}")
print(f"Volumen total: {muro['total_volumen_m3']:.2f} m³")
print(f"Coste total: {muro['total_coste_€']:,.2f} €")
print(f"Altura máxima: {muro['h_max_global_m']:.2f} m")
```

---

## Cálculos de Costes

### Calcular costes de accesos

```python
from cpq.analysis import (
    compute_horizontal_access_costs,
    compute_vertical_access_costs
)
from shapely.geometry import Point

access_point = Point(300500, 4500500)

# Accesos horizontales
dist_p, dist_v, cost_p, cost_v, p_house = \
    compute_horizontal_access_costs(access_point, huella_gdf)

print(f"Distancia: {dist_p:.2f} m")
print(f"Coste peatonal: {cost_p:,.2f} €")
print(f"Coste vehicular: {cost_v:,.2f} €")

# Acceso vertical
delta, cost_vert = compute_vertical_access_costs(
    access_point, p_house, mdt_path
)

print(f"Diferencia de cota: {delta:.2f} m")
print(f"Coste adaptación: {cost_vert:,.2f} €")
```

### Calcular costes de construcción

```python
from cpq.analysis import (
    compute_construction_cost,
    compute_slab_cost,
    compute_earthworks_cost,
    compute_fees_total
)

# Construcción
cost_const = compute_construction_cost(
    superficie_m2=100,
    price_per_m2=1500
)
print(f"Construcción: {cost_const:,.2f} €")

# Losa
cost_slab = compute_slab_cost(superficie_huella_m2=85)
print(f"Losa: {cost_slab:,.2f} €")

# Movimiento de tierras
vol_metrics = {
    'cut_m3': 50,
    'fill_m3': 30,
    'balance_m3': 20
}
cost_cut, cost_fill, cost_excess, total = \
    compute_earthworks_cost(vol_metrics)

print(f"Desmonte: {cost_cut:,.2f} €")
print(f"Terraplén: {cost_fill:,.2f} €")
print(f"Excedente: {cost_excess:,.2f} €")
print(f"Total tierras: {total:,.2f} €")

# Honorarios
fees = compute_fees_total()
print(f"Honorarios: {fees:,.2f} €")
```

---

## Utilidades

### Crear huella de casa

```python
from cpq.utils import create_house_pad
import geopandas as gpd
from shapely.geometry import box

# Crear zona edificable (ejemplo)
buildable_geom = box(300000, 4500000, 300100, 4500100)
buildable_gdf = gpd.GeoDataFrame(
    [{"geometry": buildable_geom}],
    crs="EPSG:25830"
)

# Crear huella centrada
huella_gdf = create_house_pad(
    buildable_gdf,
    width_m=10.0,
    length_m=12.0
)

print(f"Huella creada: {huella_gdf.geometry.iloc[0].area:.2f} m²")
```

### Calcular cuota hipoteca

```python
from cpq.utils import compute_monthly_payment

monthly = compute_monthly_payment(
    principal=200000,      # € prestados
    annual_rate=2.5,       # % TIN anual
    years=30              # años
)

print(f"Cuota mensual: {monthly:,.2f} €/mes")

# Calcular total a pagar
total_paid = monthly * 30 * 12
interest_paid = total_paid - 200000

print(f"Total a pagar: {total_paid:,.2f} €")
print(f"Intereses: {interest_paid:,.2f} €")
```

### Trabajar con bbox

```python
from cpq.utils import bbox_from_gdf
import geopandas as gpd
from shapely.geometry import box

# Crear GeoDataFrame
geom = box(300000, 4500000, 300500, 4500500)
gdf = gpd.GeoDataFrame([{"geometry": geom}], crs="EPSG:25830")

# Obtener bbox con buffer
bbox = bbox_from_gdf(gdf, buffer=50.0)
print(f"BBox: {bbox}")
# Output: (299950.0, 4499950.0, 300550.0, 4500550.0)
```

---

## Integración en Otros Proyectos

### Usar como biblioteca en tu proyecto

```python
# tu_proyecto.py

import sys
sys.path.append('/ruta/a/CPQ')

from cpq.services import CatastroService
from cpq.analysis import ParcelBoundaryAnalyzer
from cpq.models import MODELS_DATABASE

def analyze_parcel(refcat):
    """Analiza una parcela y retorna información básica"""
    catastro = CatastroService()
    gdf = catastro.get_parcel_geometry(refcat)

    if gdf is None:
        return None

    return {
        'refcat': refcat,
        'area_m2': gdf.geometry.iloc[0].area,
        'perimeter_m': gdf.geometry.iloc[0].length,
        'geometry': gdf.geometry.iloc[0]
    }

# Usar
info = analyze_parcel("1234567AB1234C")
if info:
    print(f"Parcela {info['refcat']}: {info['area_m2']:.2f} m²")
```

### Crear API REST con FastAPI

```python
# api.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
sys.path.append('/ruta/a/CPQ')

from cpq.services import CatastroService

app = FastAPI(title="CPQ API")

class ParcelRequest(BaseModel):
    refcat: str

@app.post("/parcel/info")
def get_parcel_info(request: ParcelRequest):
    """Obtiene información de una parcela"""
    catastro = CatastroService()
    gdf = catastro.get_parcel_geometry(request.refcat)

    if gdf is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")

    geom = gdf.geometry.iloc[0]

    return {
        "refcat": request.refcat,
        "area_m2": float(geom.area),
        "perimeter_m": float(geom.length),
        "bounds": list(geom.bounds)
    }

# Ejecutar: uvicorn api:app --reload
```

### Script batch para múltiples parcelas

```python
# batch_analysis.py

import sys
sys.path.append('/ruta/a/CPQ')

from cpq.services import CatastroService
import pandas as pd

def analyze_multiple_parcels(refcats):
    """Analiza múltiples parcelas y genera CSV"""
    catastro = CatastroService()
    results = []

    for refcat in refcats:
        print(f"Analizando {refcat}...")
        gdf = catastro.get_parcel_geometry(refcat)

        if gdf is not None:
            geom = gdf.geometry.iloc[0]
            results.append({
                'refcat': refcat,
                'area_m2': geom.area,
                'perimeter_m': geom.length,
                'status': 'OK'
            })
        else:
            results.append({
                'refcat': refcat,
                'area_m2': None,
                'perimeter_m': None,
                'status': 'Error'
            })

    # Guardar a CSV
    df = pd.DataFrame(results)
    df.to_csv('parcels_analysis.csv', index=False)
    print(f"Análisis completado: {len(results)} parcelas")

# Usar
parcels = ["1234567AB1234C", "9876543CD5678E", "1111111EF1111G"]
analyze_multiple_parcels(parcels)
```

---

## 🔧 Configuración Avanzada

### Modificar timeouts para conexiones lentas

```python
from cpq.config import CFG

# Aumentar timeouts
CFG.CATASTRO_TIMEOUT = 120  # 2 minutos
CFG.MDT_TIMEOUT = 300       # 5 minutos
CFG.OSM_TIMEOUT = 60        # 1 minuto
```

### Usar configuración personalizada

```python
from dataclasses import dataclass
from cpq.config import Config

@dataclass
class MyConfig(Config):
    # Override algunos valores
    COSTE_LOSA_M2 = 200.00  # Más caro
    RETRANQUEO_FRONTAL_M = 6.0  # Más retranqueo

# Usar
from cpq import config
config.CFG = MyConfig()
```

---

## 📊 Ejemplos de Filtrado de Modelos

```python
from cpq.model_filter import filter_valid_models
from cpq.models import MODELS_DATABASE

# Parámetros de ejemplo
num_bedrooms = 3
parcel_area_m2 = 800.0
buildable_area_m2 = 600.0

# Filtrar
valid = filter_valid_models(num_bedrooms, parcel_area_m2, buildable_area_m2)

print(f"Modelos válidos: {len(valid)}")
for model in valid:
    print(f"  - {model['nombre']}: {model['superficie_m2']} m²")
```

---

## 🎯 Tips y Buenas Prácticas

### 1. Manejo de errores

```python
from cpq.services import CatastroService

catastro = CatastroService()

try:
    gdf = catastro.get_parcel_geometry(refcat)
    if gdf is None:
        print("Parcela no encontrada o error en el servicio")
    else:
        # Procesar geometría
        pass
except Exception as e:
    print(f"Error inesperado: {e}")
```

### 2. Verificar CRS

```python
from cpq.config import CFG

if gdf.crs != CFG.ETRS89_UTM30N:
    gdf = gdf.to_crs(CFG.ETRS89_UTM30N)
```

### 3. Validar geometrías

```python
if not geom.is_valid:
    # Intentar reparar
    geom = geom.buffer(0)

if geom.is_empty:
    print("Geometría vacía")
```

---

**Última actualización**: 2025-11-09
**Versión**: 4.5.0
