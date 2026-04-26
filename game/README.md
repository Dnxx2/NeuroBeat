# Game — Unity

Juego de ritmo con cuatro modos controlados por señales EEG del Unicorn Black.

---

## Modos de juego

| Escena | Modo | Descripción |
|--------|------|-------------|
| **TamborMelodia** | Ritmo clásico | Notas caen desde arriba; hay que darles click en la zona de activación. Puntuación por precisión (Perfect / Good / Normal / Miss) y rango final S–D |
| **Ritmo** | Reproducción de ritmo | El juego toca un patrón de 4–8 beats; el jugador debe reproducirlo a ciegas con la misma cadencia. Puntuación = % de precisión temporal |
| **Tambor** | Batería libre | Modo libre: cada click toca un golpe de batería con pitch aleatorio |
| **Piano** | Piano libre | Teclado de una octava (Do–Si); cada tecla reproduce su nota |

Desde **Menu** se navega a los tres modos principales (Batería → TamborMelodia, Piano, Ritmo).

---

## Integración EEG

### `EEGReceiver.cs` — recepción de datos

Escucha el paquete UDP de `stream.py` en el puerto **5005** en un thread de fondo. Expone todos los valores como campos públicos, actualizados en `Update()` (thread-safe).

### `EEGMouseClicker.cs` — trigger de parpadeo

Detecta un parpadeo deliberado cuando `focus >= 0.95` y lanza un `UnityEvent` configurable desde el Inspector. Dispara una sola vez por transición (no se repite mientras focus esté alto).

```
EEGReceiver.focus >= 0.95  →  EEGMouseClicker  →  UnityEvent (acción configurada en Inspector)
```

Uso típico: confirmar selección en menú, activar habilidad especial, disparar acción puntual.

### `EEGReceiverMock.cs` — pruebas sin hardware

Simula `focus = 1.0` mientras se mantiene presionado el botón del mouse, y `focus = 0.0` en caso contrario. Permite probar la lógica de blink sin conectar el Unicorn.

---

## Valores disponibles en `EEGReceiver`

**EEG — actualizados cada ~250 ms**

| Campo | Rango | Fuente | Uso actual |
|-------|-------|--------|------------|
| `focus` | 0–1 | EEGNet | Probabilidad de parpadeo; saturado a 1.0 cuando > 0.7 — trigger via `EEGMouseClicker` (umbral 0.95) |
| `engagement` | 0–1 | DSP (β/α+β) | Disponible; no conectado a mecánica activa actualmente |
| `alpha` | 0–1 | DSP (normalizado) | Disponible |
| `beta` | 0–1 | DSP (normalizado) | Disponible |
| `theta` | 0–1 | DSP (normalizado) | Disponible |

**IMU — pass-through sin filtro**

| Campo | Unidad | En reposo | Uso actual |
|-------|--------|-----------|------------|
| `accelX` / `accelY` | mg | ≈ 0 | Disponible; no conectado a mecánica activa actualmente |
| `accelZ` | mg | ≈ 1000 (1g) | Disponible |
| `gyroX` / `gyroY` / `gyroZ` | °/s | ≈ 0 | Usado por `control/gyro_mouse.py` (fuera de Unity) |

---

## Crear el proyecto Unity

1. Abrir Unity Hub → **Open** → seleccionar la carpeta `game/` de este repo
2. Si es un proyecto nuevo: **New Project** → template 2D → apuntar Location a `game/`
3. Unity creará `ProjectSettings/`, `Packages/`, `Library/`, etc. dentro de `game/`
4. Los scripts en `Assets/Scripts/` ya estarán disponibles al abrir el proyecto

---

## Setup EEG en escena

1. Crear un **GameObject vacío** → renombrarlo `EEGReceiver`
2. Añadirle el componente `EEGReceiver.cs`
3. Para usar blink detection: añadir `EEGMouseClicker.cs` al mismo u otro GameObject, asignar la referencia a `EEGReceiver` y conectar el `UnityEvent` en el Inspector
4. Para desarrollo sin hardware: usar `EEGReceiverMock.cs` en lugar de `EEGReceiver.cs`

---

## Correr

1. Arrancar el streamer Python en otra terminal:
   ```bash
   cd signal-processing
   python stream.py --model model-finetuning/models/calibrated.pt [--mock]
   ```
2. Dar **Play** en Unity

---

## Grabaciones

`Grabadora` es un **Singleton** con `DontDestroyOnLoad` — se instancia una vez y persiste entre escenas. Graba el audio del `AudioSource` principal y al parar guarda el archivo en `game/Grabaciones/` con nombre basado en fecha y hora: `Grabacion_yyyy-MM-dd_HH-mm-ss.wav`.

`ControladorGrabacionUI` expone dos métodos para conectar a botones en el Inspector:
- `BotonEmpezar()` — inicia la grabación
- `BotonParar()` — detiene y guarda el archivo WAV

La escena **Grabaciones** lista los `.wav` de `game/Grabaciones/` y permite reproducirlos desde la UI.

> **Nota:** `Grabaciones.unity` y las escenas de `TamborMelodia/` no están registradas en `EditorBuildSettings.asset`. Solo Menu, Piano, Ritmo y Tambor están habilitadas para build. Para incluirlas en un build, abrirlas y usar **File → Build Settings → Add Open Scenes**.

---

## Estructura de scripts

```
Assets/Scripts/
├── Data_Receiver/
│   ├── EEGReceiver.cs          recibe paquete UDP de stream.py
│   ├── EEGMouseClicker.cs      dispara UnityEvent al detectar blink (focus >= 0.95)
│   └── EEGReceiverMock.cs      mock para desarrollo sin hardware
├── Menu_Principal/
│   ├── MenuSystem.cs           carga escena de juego / salir
│   └── SeleccionarInstrumento.cs genera botones de selección de nivel
├── Menu/
│   └── MenuManager.cs          navegación entre escenas (Batería / Piano / Ritmo / Menú)
├── TamborMelodia/
│   ├── GameManager.cs          scoring, rango final, flujo de partida
│   ├── Beatscroller.cs         scrollea notas a velocidad en BPM
│   ├── NodeObject.cs           tile individual — zonas Perfect / Good / Normal / Miss
│   ├── ButtonController.cs     feedback visual de botones
│   └── EffectObject.cs         efectos visuales temporales de acierto/fallo
├── Ritmo/
│   └── JuegoRitmoUnificado.cs  aprendizaje + reproducción de ritmo, scoring por %
├── Piano/
│   └── MusicNotes.cs           reproduce notas (Do–Si) via AudioSource
├── Tambor/
│   └── TamborLibre.cs          batería libre con pitch aleatorio; ignora clicks sobre UI
└── Grabaciones/
    ├── Grabadora.cs            Singleton — graba audio a WAV en game/Grabaciones/ con nombre por fecha
    ├── ControladorGrabacionUI.cs UI bridge: BotonEmpezar() / BotonParar() → Grabadora.instancia
    ├── SavWav.cs               utilidad de escritura de archivos WAV (PCM 16-bit)
    ├── ListaAudiosManager.cs   lista y reproduce .wav de la carpeta Grabaciones/
    └── FilaAudio.cs            fila de UI por cada archivo de grabación
```

---

## Notas de Unity

- Versión recomendada: **Unity 2022 LTS** o posterior
- Carpetas generadas automáticamente (`Library/`, `Temp/`, `Obj/`, `Builds/`) están en `.gitignore`
- No subir `Library/` al repositorio — se regenera al abrir el proyecto
