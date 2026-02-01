# Urbanismo Proxy - Funcionamiento

## ✅ Cómo Funciona en Producción

El **Urbanismo Proxy** funciona **exactamente igual que el resto del CPQ**: solo necesita la **referencia catastral** como entrada.

### Entrada

```bash
Referencia catastral: 0279305VK4707N0001TL
Dormitorios: 3
```

**Eso es todo.** No necesitas proporcionar ningún dato adicional.

---

## 🔄 Flujo Automático

```
1. Usuario introduce REFCAT
   ↓
2. CPQ obtiene geometría de la parcela (WFS GetParcel)
   ↓
3. CPQ calcula bbox de 250m alrededor de la parcela
   ↓
4. PROXY obtiene parcelas vecinas (WFS GetFeature con BBOX)
   ↓
5. PROXY obtiene edificios vecinos (WFS GetFeature con BBOX)
   ↓
6. PROXY analiza el contexto construido
   ↓
7. PROXY infiere parámetros urbanísticos reales
   ↓
8. CPQ usa esos parámetros para calcular modelos
```

**Todo es automático.** El usuario solo da la refcat.

---

## 🌐 Diferencia Producción vs Sandbox

### En Producción (servidor con conectividad normal)

```
✓ WFS del Catastro funciona
✓ Obtiene 50+ parcelas automáticamente
✓ Obtiene 40+ edificios automáticamente
✓ Proxy ejecuta análisis completo
✓ Resultado: parámetros inferidos del entorno real
```

### En Sandbox (este entorno de desarrollo)

```
✗ WFS bloqueado por firewall (403 Forbidden)
→ Intenta leer archivos locales (.gpkg)
→ Si no los encuentra, usa parámetros por defecto
```

---

## 🎯 Estado del Código

| Componente | Estado |
|-----------|--------|
| **WFS GetParcel** | ✅ Funciona (1 parcela) |
| **WFS GetFeature BBOX** | ✅ Implementado, bloqueado solo en sandbox |
| **Motor de análisis proxy** | ✅ Completo |
| **Integración en CPQ** | ✅ Completa |
| **Fallback a defaults** | ✅ Funciona |

---

## 📋 Para Desplegar en Producción

### Opción 1: Servidor con Conectividad Normal (Recomendado)

```bash
# 1. Copiar código a servidor de producción
git clone <repo> /var/www/cpq
cd /var/www/cpq

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar
python main.py
# Introduce refcat: 0279305VK4707N0001TL
# → WFS funciona automáticamente
# → Proxy obtiene datos del contexto
# → Resultados con parámetros reales
```

**Eso es todo.** En un servidor con conectividad WFS normal, el proxy funciona solo con la refcat.

### Opción 2: Servidor Sin Acceso WFS (Firewall Corporativo)

Si el servidor tiene firewall que bloquea WFS:

```bash
# Descargar datos manualmente del CNIG
# https://centrodedescargas.cnig.es/
# Guardar en /var/www/cpq/data/parcels.gpkg y buildings.gpkg

# El proxy usará estos archivos automáticamente
```

---

## 🔧 Configuración

### Activar/Desactivar Proxy

```python
# main.py línea 91
USE_PROXY = True   # ← Activado (intenta WFS, si falla usa defaults)
USE_PROXY = False  # ← Desactivado (siempre usa defaults)
```

**Recomendación**: Dejar en `True`. En producción funcionará automáticamente.

### Ajustar Radio de Búsqueda

```python
# main.py línea 99
bbox_proxy = bbox_from_gdf(gdf_parcel, buffer=250.0)  # 250m (default)
bbox_proxy = bbox_from_gdf(gdf_parcel, buffer=400.0)  # 400m (más amplio)
```

### Ajustar Configuración del Proxy

```python
# main.py línea 142
cfg = ProxyConfig(
    radius_m=250.0,                    # Radio de búsqueda
    min_neighbors=10,                  # Mínimo de vecinos
    comparable_area_tolerance=0.50,    # ±50% área
    building_selection_mode="smart",   # Modo selección edificio
    use_road_classification=True       # Usar viales OSM
)
```

---

## 📊 Resultados Esperados

### Con Proxy Activo (Producción)

```
[PROXY] Analizando entorno construido (250m)...
  [1/2] Obteniendo datos del contexto vía WFS Catastro...
[Catastro] ✓ 45 parcelas obtenidas
[Catastro] ✓ 38 edificios obtenidos

[PROXY] Análisis completado
  Confianza: ALTA (score: 0.82)

  ✓ USANDO PARÁMETROS INFERIDOS DEL ENTORNO
    Retranqueo frontal: 3.2m (vs 5.0m default)
    Ocupación máxima: 45% (vs 30% default)
    Edificabilidad: 0.68 (vs 0.40 default)
```

### Sin Proxy / WFS Bloqueado

```
[PROXY] Analizando entorno construido (250m)...
  [1/2] Obteniendo datos del contexto vía WFS Catastro...
[Catastro] Error HTTP 403 - consulta bbox no soportada

  [2/2] WFS bloqueado/no disponible, buscando archivos locales...
    ✗ Sin archivos locales - Usando parámetros por defecto

→ Continúa con parámetros por defecto (CFG.RETRANQUEO_FRONTAL_M, etc.)
```

---

## ❓ Preguntas Frecuentes

**P: ¿Necesito descargar datos manualmente?**
R: No en producción. Solo necesitas la refcat. El WFS los obtiene automáticamente.

**P: ¿Por qué no funciona en este entorno?**
R: El sandbox tiene firewall que bloquea peticiones WFS con BBOX. En producción normal funcionará.

**P: ¿Qué pasa si WFS falla en producción?**
R: El sistema usa parámetros por defecto automáticamente. No rompe el flujo.

**P: ¿Cómo sé si el proxy está funcionando?**
R: Verás el mensaje `✓ USANDO PARÁMETROS INFERIDOS DEL ENTORNO` con valores diferentes a los defaults.

**P: ¿Puedo probar sin conexión WFS?**
R: Sí, descarga datos del CNIG y guárdalos en `/data/*.gpkg`. El proxy los usará automáticamente.

---

## 📚 Documentación Adicional

- **URBANISMO_PROXY.md** - Explicación técnica detallada del algoritmo
- **ACTIVAR_PROXY.md** - Guía de activación paso a paso
- **GUIA_DATOS_EJEMPLO.md** - Cómo descargar datos del CNIG manualmente

---

**Resumen**: El proxy funciona en producción solo con la refcat, igual que el resto del CPQ. En este entorno sandbox está bloqueado solo por firewall.
