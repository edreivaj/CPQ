# Guía: Obtener Datos de Ejemplo para el Proxy

## 🎯 Objetivo

Esta guía te ayudará a obtener las capas GIS necesarias para probar el **Urbanismo Proxy** con datos reales del Catastro.

---

## 📦 Opción 1: Descargar Capas del CNIG (Recomendado)

### Paso 1: Acceder al Centro de Descargas

Visita: https://centrodedescargas.cnig.es/CentroDescargas/index.jsp

### Paso 2: Seleccionar Producto

1. **Información Geográfica de Referencia** → **Cartografía Catastral**
2. Buscar tu municipio (ej: "Madrid", "Barcelona", "Valencia")
3. Descargar el archivo ZIP del municipio

### Paso 3: Formato Recomendado

Busca archivos que contengan:
- `CATASTRAL_PARCELS` o similar (parcelas catastrales)
- `CATASTRAL_BUILDINGS` o `BUILDINGPART` (edificaciones)

Formatos aceptados: `.shp` (Shapefile), `.gpkg` (GeoPackage), `.gml`

### Paso 4: Descargar y Extraer

```bash
# Crear directorio de datos
mkdir -p /home/user/CPQ/data

# Descargar (ejemplo para Madrid)
cd /home/user/CPQ/data
wget "URL_DEL_ARCHIVO_ZIP"
unzip archivo_catastro.zip

# Los archivos deben estar en formato EPSG:25830 (ETRS89 UTM 30N)
```

### Paso 5: Identificar los Archivos Correctos

Busca dentro del ZIP:
```bash
ls -lh *.shp *.gpkg *.gml

# Deberías encontrar algo como:
# - 28_PARCELA.shp         (parcelas)
# - 28_BUILDINGPART.shp    (edificios)
# - 28_CONSTRU.shp         (construcciones)
```

### Paso 6: Renombrar para el Proxy

```bash
# Copiar/renombrar los archivos principales
cp 28_PARCELA.shp parcels.shp
cp 28_PARCELA.shx parcels.shx
cp 28_PARCELA.dbf parcels.dbf
cp 28_PARCELA.prj parcels.prj

cp 28_BUILDINGPART.shp buildings.shp
cp 28_BUILDINGPART.shx buildings.shx
cp 28_BUILDINGPART.dbf buildings.dbf
cp 28_BUILDINGPART.prj buildings.prj
```

### Paso 7: (Opcional) Convertir a GeoPackage

GeoPackage es más eficiente para consultas espaciales:

```bash
# Instalar ogr2ogr si no lo tienes
# sudo apt-get install gdal-bin

ogr2ogr -f GPKG parcels.gpkg parcels.shp
ogr2ogr -f GPKG buildings.gpkg buildings.shp

# Verificar CRS
ogrinfo -al -so parcels.gpkg | grep PROJCS
# Debe mostrar: ETRS89 / UTM zone 30N
```

---

## 📦 Opción 2: Usar Script de Descarga Automática

### Paso 1: Ejecutar el Script Helper

```bash
cd /home/user/CPQ
python download_catastro_data.py --municipio MADRID --output data/
```

### Paso 2: El Script Hará

1. Consultar el catálogo del CNIG
2. Buscar el municipio especificado
3. Descargar las capas necesarias
4. Convertir a GeoPackage
5. Verificar CRS (EPSG:25830)

**NOTA**: Este script es un ejemplo - el CNIG no tiene API pública estable, por lo que es posible que necesites descargar manualmente.

---

## 📦 Opción 3: Generar Datos Sintéticos de Prueba

Si solo quieres probar el proxy sin descargar datos reales:

```bash
cd /home/user/CPQ
python generate_synthetic_data.py --refcat 1234567AB1234C --output data/
```

Este script generará:
- 50 parcelas sintéticas alrededor de la referencia
- 40 edificios sintéticos en esas parcelas
- Guardado como `data/parcels.gpkg` y `data/buildings.gpkg`

---

## 🧪 Verificar que los Datos Están Listos

### Opción A: Usar el Script de Verificación

```bash
python verify_proxy_data.py
```

Salida esperada:
```
✓ Archivo de parcelas encontrado: /home/user/CPQ/data/parcels.gpkg
✓ Archivo de edificios encontrado: /home/user/CPQ/data/buildings.gpkg
✓ Parcelas: 1,250 geometrías válidas
✓ Edificios: 987 geometrías válidas
✓ CRS correcto: EPSG:25830
✓ Bbox: (440000.0, 4470000.0, 445000.0, 4475000.0)

🎉 Los datos están listos para usar el proxy!
```

### Opción B: Verificación Manual con Python

```python
import geopandas as gpd

# Leer archivos
parcels = gpd.read_file("/home/user/CPQ/data/parcels.gpkg")
buildings = gpd.read_file("/home/user/CPQ/data/buildings.gpkg")

print(f"Parcelas: {len(parcels)}")
print(f"Edificios: {len(buildings)}")
print(f"CRS parcelas: {parcels.crs}")
print(f"CRS edificios: {buildings.crs}")

# Verificar que están en EPSG:25830
assert str(parcels.crs) == "EPSG:25830", "CRS incorrecto!"
assert str(buildings.crs) == "EPSG:25830", "CRS incorrecto!"

print("✓ Datos válidos!")
```

---

## 🚀 Activar el Proxy

Una vez tengas los datos:

### 1. Verificar que los archivos existen:

```bash
ls -lh /home/user/CPQ/data/
# Debe mostrar:
# parcels.gpkg
# buildings.gpkg
```

### 2. Activar el flag en main.py:

Edita `main.py` línea ~89:

```python
USE_PROXY = True  # ← Cambiar de False a True
```

### 3. Ejecutar el CPQ:

```bash
python main.py
```

### 4. Verificar salida:

Deberías ver algo como:

```
============================================================
ANÁLISIS DE CONTEXTO URBANÍSTICO (PROXY)
============================================================

[PROXY] Analizando entorno construido (250m)...
  [1/3] Intentando obtener datos vía WFS del Catastro...
[Catastro] Error HTTP 403 - consulta bbox no soportada
[Catastro] Recomendación: usar archivos locales de CNIG

  [2/3] WFS no disponible, buscando archivos locales...
    ✓ Encontrados archivos locales
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

## 🗺️ Áreas de Ejemplo Recomendadas

Para probar el proxy, estos municipios tienen buenos datos:

| Municipio | Código INE | Tipología | Notas |
|-----------|-----------|-----------|-------|
| Madrid | 28079 | Urbana densa | Gran cobertura, bien actualizado |
| Barcelona | 08019 | Urbana densa | Excelente calidad de datos |
| Valencia | 46250 | Urbana media | Mezcla interesante |
| Getafe | 28065 | Residencial | Bueno para parcelas unifamiliares |
| Pozuelo | 28115 | Residencial | Parcelas grandes, baja densidad |

**Referencias catastrales de ejemplo:**

```bash
# Madrid (Chamberí - zona residencial densa)
REFCAT: 0279305VK4707N0001TL

# Madrid (Moncloa - zona con edificabilidad media)
REFCAT: 0377201VK4707A0001PU

# Barcelona (Eixample - cuadrícula regular)
REFCAT: 0117901DF2811C0001JI
```

---

## 📊 Estructura de Directorios Final

```
/home/user/CPQ/
├── data/
│   ├── parcels.gpkg          ← Parcelas catastrales
│   ├── buildings.gpkg        ← Edificaciones
│   └── README.txt            ← Info sobre la fuente de datos
├── main.py                   ← USE_PROXY = True
├── cpq/
│   ├── analysis/
│   │   └── urbanismo_proxy.py
│   └── services/
│       └── catastro.py       ← Con métodos WFS nuevos
└── ACTIVAR_PROXY.md
```

---

## 🐛 Troubleshooting

### Error: "No se encontraron archivos locales"

**Causa**: Los archivos no están en la ruta esperada
**Solución**:
```bash
ls -lh /home/user/CPQ/data/
# Verifica que existan parcels.gpkg y buildings.gpkg
```

### Error: "CRS no coincide"

**Causa**: Los archivos no están en EPSG:25830
**Solución**:
```python
import geopandas as gpd

# Leer y reproyectar
parcels = gpd.read_file("data/parcels.gpkg")
parcels = parcels.to_crs("EPSG:25830")
parcels.to_file("data/parcels_25830.gpkg", driver="GPKG")
```

### Error: "WFS HTTP 403"

**Causa**: El servicio WFS del Catastro rechaza consultas grandes
**Solución**: Usar archivos locales (Opción 1)

### Confianza siempre BAJA

**Causa**: Entorno muy heterogéneo o pocos edificios
**Solución**:
```python
# En main.py, ajustar configuración
cfg = ProxyConfig(
    radius_m=400,               # Buscar más lejos
    min_neighbors=8,            # Menos exigente
    comparable_area_tolerance=0.60  # Rango más amplio
)
```

---

## 📚 Recursos

- **CNIG Centro de Descargas**: https://centrodedescargas.cnig.es/
- **Catastro INSPIRE**: https://www.catastro.meh.es/webinspire/
- **QGIS** (para visualizar datos): https://qgis.org/
- **Documentación del Proxy**: `URBANISMO_PROXY.md`
- **Guía de Activación**: `ACTIVAR_PROXY.md`

---

**Última actualización**: 2025-01-31
**Versión CPQ**: 4.5+
