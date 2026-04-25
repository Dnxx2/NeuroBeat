# Adquisición de Datos — Unicorn Black

Scripts para conectar el Unicorn Black vía BrainFlow, verificar la señal y visualizarla en tiempo real.

---

## Scripts

| Archivo | Qué hace |
|---------|----------|
| `connection_test.py` | Conecta, graba 5 s y reporta cuántas muestras llegaron — primera prueba de que el hardware funciona |
| `plot_raw.py` | Graba 5 s y grafica los 8 canales crudos con matplotlib |
| `scope.py` | Osciloscopio en tiempo real — muestra los 8 canales en vivo con ventana deslizante de 5 s |

---

## Install

```bash
cd api
pip install -r requirements.txt
```

---

## Configuración del puerto serie

Todos los scripts usan `params.serial_port`. Cambia el valor según tu sistema:

| Sistema | Ejemplo |
|---------|---------|
| Windows | `COM5` (verifica en Administrador de dispositivos) |
| Linux | `/dev/ttyUSB0` |
| macOS | `/dev/tty.usbserial-XXXX` |

---

## Paso 1 — Verificar conexión

Antes de cualquier otra cosa, corre el test de conexión con el Unicorn encendido y pareado:

```bash
python connection_test.py
```

Salida esperada:
```
--- Intentando conexión ---
¡CONECTADO CON ÉXITO!
Recibiendo datos durante 5 segundos...
--- RESULTADO ---
Muestras recibidas: 1250
Shape completo: (25, 1250)
Frecuencia de muestreo esperada: 250 Hz
```

- `1250 muestras` = 5 s × 250 Hz ✓
- `shape (25, 1250)` = 25 canales (8 EEG + acelerómetro + giroscopio + contadores)
- Si el número de muestras es 0 o hay error, revisar el puerto y que el Unicorn esté encendido

---

## Paso 2 — Ver señal cruda (matplotlib)

```bash
python plot_raw.py
```

Graba 5 s y abre una ventana con los 8 canales EEG (FZ, C3, CZ, C4, PZ, PO7, OZ, PO8). Útil para verificar que los electrodos hacen buen contacto antes de una sesión.

---

## Paso 3 — Osciloscopio en vivo

```bash
python scope.py
```

Abre una ventana PyQtGraph con los 8 canales actualizándose a 30 fps. La señal se centra automáticamente (se resta la media) para que sea legible sin importar el offset de DC.

- Línea verde neón, los últimos 5 s por canal
- Cerrar la ventana o Ctrl+C para salir (el puerto se libera en el `finally`)

---

## Relación con el resto del repo

Estos scripts son para **verificación y exploración** del hardware. El pipeline de procesamiento en tiempo real que alimenta a Unity está en `signal-processing/`:

```
api/scope.py          →  confirmar que la señal llega bien
signal-processing/stream.py  →  procesar + clasificar + enviar a Unity
```

El `scope.py` usa BrainFlow directamente. El `stream.py` usa UnicornPy (SDK nativo de g.tec) para compatibilidad con el pipeline de filtrado.

---

## Canales del Unicorn Black

Los canales EEG están en los índices devueltos por `BoardShim.get_eeg_channels(board_id)`:

| Índice EEG | Nombre | Región |
|------------|--------|--------|
| 0 | FZ | Frontal central |
| 1 | C3 | Motor izquierdo |
| 2 | CZ | Motor central |
| 3 | C4 | Motor derecho |
| 4 | PZ | Parietal |
| 5 | PO7 | Occipital izquierdo |
| 6 | OZ | Occipital central |
| 7 | PO8 | Occipital derecho |
