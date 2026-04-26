# Control

Scripts que traducen señales EEG e IMU en acciones de control del sistema operativo.

---

## Scripts

| Archivo | Qué hace |
|---------|----------|
| `gyro_mouse.py` | Mueve el cursor con el giroscopio y hace click izquierdo por parpadeo deliberado |

---

## `gyro_mouse.py`

### Fuente de datos

Lee el paquete UDP que emite `signal-processing/stream.py` en el puerto **5005**.
Usa `SO_REUSEADDR` para compartir el puerto con Unity — los dos reciben el mismo datagrama simultáneamente, sin conflicto.

```
stream.py → UDP:5005 ──┬── Unity  (EEGReceiver.cs)   game input
                       └── gyro_mouse.py              OS mouse control
```

Campos utilizados del paquete:

| Campo | Uso |
|-------|-----|
| `gyro_x` | Pitch (asentir) → movimiento Y del cursor |
| `gyro_y` | Yaw (girar cabeza) → movimiento X del cursor |
| `focus` | Probabilidad de parpadeo (0–1, saturado a 1.0 cuando > 0.7) → dispara click izquierdo |

### Lógica de click — Schmitt trigger

El click **no se dispara con un solo pico de focus**. Funciona con dos umbrales:

```
focus
  1.0 ─────────────────────────────────────
  0.7 ─ ─ ─ ─ upper_threshold ─ ─ ─ ─ ─ ─  ← necesita N paquetes aquí → CLICK
                                             ← después del click: WAITING
  0.45 ─ ─ ─ lower_threshold ─ ─ ─ ─ ─ ─  ← bajar aquí para re-armarse
  0.0 ─────────────────────────────────────
```

1. **Armado** (`arm [0/N]`): cuenta paquetes consecutivos con `focus ≥ threshold`
2. **Click**: cuando llega a N paquetes → `pyautogui.click()` → pasa a WAITING
3. **Waiting** (`wait`): ignora focus hasta que baje de `threshold − hysteresis`
4. Regresa a **Armado**

Con los defaults (threshold=0.70, hysteresis=0.25, confirm=3):
- Se necesitan **3 paquetes × 250ms = 0.75s** de focus sostenido para clickear
- Luego hay que bajar el focus a **≤ 0.45** para poder clickear de nuevo

### Procesamiento del giroscopio

```
señal cruda  →  deadzone (ignora < 2°/s)  →  EMA (suavizado)  →  moveRel(dx, dy)
```

- **Deadzone**: filtra la deriva del giroscopio en reposo (jitter ≈ 0-1°/s)
- **EMA**: suaviza los movimientos bruscos sin añadir latencia perceptible

### Uso

**Requisitos previos:**
```bash
pip install -r requirements.txt   # desde la raíz del repo
```

**Con hardware (modo normal):**
```bash
# Terminal 1 — procesar EEG y transmitir
cd signal-processing
python stream.py --model model-finetuning/models/calibrated.pt

# Terminal 2 — control del mouse
python control/gyro_mouse.py
```

**Sin hardware (mock completo):**
```bash
python control/gyro_mouse.py --mock
```

El modo mock genera un giroscopio circular sintético y un focus pulsante que llega al umbral cada ~10 s, lo que permite verificar que el click funciona sin conectar el Unicorn.

**Detener:** `Ctrl+C` o mover el mouse a la **esquina superior izquierda** de la pantalla (pyautogui failsafe).

### Parámetros

| Flag | Default | Descripción |
|------|---------|-------------|
| `--threshold` | `0.70` | Focus mínimo para contar hacia el click |
| `--hysteresis` | `0.25` | Cuánto debe bajar focus tras click para re-armarse |
| `--confirm` | `3` | Paquetes consecutivos sobre umbral = 0.75s |
| `--sensitivity` | `1.0` | Factor °/s → píxeles |
| `--deadzone` | `2.0` | Mínimo °/s para mover cursor |
| `--smoothing` | `0.35` | Coeficiente EMA (0 = sin suavizado) |
| `--rate` | `30` | Hz de actualización del cursor |
| `--port` | `5005` | Puerto UDP del streamer |

```bash
# Ejemplo: click más fácil, movimiento más sensible
python control/gyro_mouse.py --threshold 0.60 --confirm 2 --sensitivity 3
```

### Display en terminal

```
focus=0.73 [###########    ] arm [2/3]  dx=  +8 dy=  -3
focus=0.81 [############   ] arm [3/3]  dx=  +5 dy=  +1  *** CLICK ***
focus=0.78 [############   ] wait       dx=  +3 dy=  +0
focus=0.41 [######         ] arm [0/3]  dx=  +0 dy=  +0
```

- `arm [N/3]` — armado, N paquetes contados hacia el click
- `wait` — esperando que el focus baje del umbral bajo para re-armarse
- `*** CLICK ***` — click disparado este frame
