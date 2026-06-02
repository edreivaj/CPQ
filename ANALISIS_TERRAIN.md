# Análisis de cpq/analysis/terrain.py

## Resumen de funcionamiento

Este documento describe cómo funciona el módulo de análisis topográfico del sistema CPQ.

---

## 1. Cómo calcula la pendiente

**Método:** Ajuste de plano por mínimos cuadrados sobre **todos los puntos del raster dentro de la huella**.

```python
# Líneas 128-153: calc_pendiente()
A = np.c_[xs, ys, np.ones_like(xs)]
C, *_ = np.linalg.lstsq(A, zs, rcond=None)  # Ajuste plano Z = ax + by + c
a, b = float(C[0]), float(C[1])
p_tot = float(np.hypot(a*100, b*100))  # Pendiente total en %
```

**NO es celda a celda.** Extrae todas las coordenadas XYZ de los píxeles del MDT que caen dentro de la huella (`get_xyz_from_pad`, líneas 156-200), y luego ajusta un único plano 3D. El resultado es la **pendiente media del plano ajustado**, no un promedio de pendientes locales.

---

## 2. Cómo calcula el volumen de desmonte y terraplén

**Método:** Acumulación **celda a celda** sobre la **huella de la vivienda** (no sobre la parcela).

```python
# Líneas 44-125: compute_volume_metrics()

# 1. Recorta el raster a la huella
out_image, out_transform = rasterio.mask.mask(src, pad_gdf.geometry, ...)

# 2. Calcula cota óptima como MEDIA de elevaciones
z_opt = float(np.mean(z_valid))

# 3. Diferencia por píxel
diff = data - z_opt

# 4. Área de cada píxel
pixel_area = abs(src.transform.a * src.transform.e)

# 5. Suma volúmenes
cut_m3 = float(np.sum(diff_valid[diff_valid > 0]) * pixel_area)   # Desmonte
fill_m3 = float(np.sum(np.abs(diff_valid[diff_valid < 0])) * pixel_area)  # Terraplén
```

**NO aplica coeficiente sobre pendiente.** Calcula la diferencia real de cada celda respecto a la cota óptima y multiplica por el área del píxel. Es un cálculo volumétrico real celda a celda.

---

## 3. Cómo determina la cota de la plataforma

**Método:** **Media aritmética** de todas las elevaciones dentro de la huella.

```python
# Línea 103
z_opt = float(np.mean(z_valid))
```

**NO es la mínima, ni la máxima, ni minimiza el volumen total.** Simplemente calcula el promedio de las cotas Z de todos los píxeles válidos dentro de la huella.

Esto implica que el desmonte y terraplén tienden a equilibrarse (balance ≈ 0 en terrenos simétricos), pero **no es un cálculo de optimización** que busque minimizar el volumen total de tierra movida.

---

## 4. Cómo calcula los muros de contención

**Método:** Calcula la **diferencia real de cota entre la plataforma y el terreno natural en cada punto del perímetro**.

```python
# Líneas 203-380: dimensionar_muro_perimetral_real()

# Para cada punto del perímetro de la huella (cada 1m):
for k in range(n_perfiles + 1):
    # 1. Calcula vector normal al lado (perpendicular hacia fuera)
    nx, ny = normal_sign * nx, normal_sign * ny
    
    # 2. Lanza rayo hacia el límite de la parcela
    ray = LineString([(x, y), (x + nx * ray_len, y + ny * ray_len)])
    
    # 3. Muestrea el MDT cada 1m a lo largo del rayo
    for s in range(1, n_muestras + 1):
        z_nat = float(data_band[row, col])  # Cota terreno natural
        h_local = max(cota_plataforma - z_nat, 0.0)  # Altura necesaria
        alturas.append(h_local)
    
    # 4. Toma la altura máxima en ese perfil
    h_perfil = max(alturas) if alturas else 0.0
    
    # 5. Calcula espesor según altura
    esp = espesor_por_altura(h_perfil)  # 0.30m, 0.50m, o 0.70m
    
    # 6. Calcula volumen del perfil
    vol_perfil = h_perfil * esp * paso_perfil
```

**NO usa altura estimada genérica.** Es un cálculo real punto a punto:
- Recorre el perímetro de la plataforma cada `paso_perfil` metros (default 1.0m)
- En cada punto, lanza un rayo perpendicular hacia el límite de la parcela
- Muestrea el terreno natural cada 1m a lo largo de ese rayo
- Calcula `altura_muro = max(cota_plataforma - z_terreno, 0)` para cada muestra
- Toma la altura máxima del perfil
- Calcula volumen con espesor variable según altura

---

## 5. ¿Sobre toda la parcela o solo la huella?

**Los cálculos de movimiento de tierras se hacen ÚNICAMENTE sobre la huella de la vivienda (`pad_gdf`)**, no sobre toda la parcela.

```python
# Línea 71-77 en compute_volume_metrics():
out_image, out_transform = rasterio.mask.mask(
    src,
    pad_gdf.geometry,  # ← Solo la huella, no la parcela
    crop=True,
    ...
)
```

Lo mismo aplica para:
- `get_xyz_from_pad()`: extrae XYZ solo de la huella
- `dimensionar_muro_perimetral_real()`: recorre el perímetro de la huella (`pad_gdf`), no de la parcela

La **parcela** (`parcel_geom`) solo se usa para determinar hasta dónde llega el rayo al calcular muros (el límite exterior).

---

## Tabla resumen

| Aspecto | Método |
|---------|--------|
| **Pendiente** | Ajuste plano único (mínimos cuadrados) sobre todos los puntos de la huella |
| **Volúmenes** | Suma celda a celda sobre la huella (no coeficiente) |
| **Cota plataforma** | Media aritmética (no optimizada) |
| **Muros** | Altura real punto a punto cada 1m del perímetro |
| **Área de cálculo** | Solo la huella de la vivienda |

---

## Funciones principales

| Función | Líneas | Propósito |
|---------|--------|-----------|
| `get_z_at_point()` | 17-41 | Obtiene cota Z en un punto específico |
| `compute_volume_metrics()` | 44-125 | Calcula desmonte, terraplén y cota óptima |
| `calc_pendiente()` | 128-153 | Calcula pendiente mediante ajuste de plano |
| `get_xyz_from_pad()` | 156-200 | Extrae coordenadas XYZ de la huella |
| `dimensionar_muro_perimetral_real()` | 203-380 | Dimensiona muros de contención |

---

## Constantes de muros de contención

```python
COSTES_MURO = {
    "escollera":        {"coste_m3": 180, "h_max": 2.5},
    "bloque":           {"coste_m3": 320, "h_max": 3.0},
    "hormigon_armado":  {"coste_m3": 450, "h_max": 8.0}
}
```

Espesor según altura:
- h < 1.5m → 0.30m
- h < 3.0m → 0.50m
- h ≥ 3.0m → 0.70m
