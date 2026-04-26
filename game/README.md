# Game — Unity

Rhythm game with four modes controlled by EEG signals from the Unicorn Black.

---

## Game modes

| Scene | Mode | Description |
|-------|------|-------------|
| **TamborMelodia** | Classic rhythm | Notes fall from the top; click them in the activation zone. Scored by accuracy (Perfect / Good / Normal / Miss) with a final rank S–D |
| **Ritmo** | Rhythm reproduction | The game plays a 4–8 beat pattern; the player must reproduce it silently with the same timing. Score = % temporal accuracy |
| **Tambor** | Free drums | Free-play mode: each click plays a drum hit with randomized pitch |
| **Piano** | Free piano | One-octave keyboard (C–B); each key plays its note |

From **Menu** you navigate to the three main modes (Drums → TamborMelodia, Piano, Ritmo).

---

## EEG integration

### `EEGReceiver.cs` — data reception

Listens to the UDP packet from `stream.py` on port **5005** on a background thread. Exposes all values as public fields, updated in `Update()` (thread-safe).

### `EEGMouseClicker.cs` — blink trigger (`EEGBlinkTrigger` class)

Detects a deliberate blink when `focus >= 0.7` and fires a configurable `UnityEvent` from the Inspector. Fires once per transition (does not repeat while focus stays high).

```
EEGReceiver.focus >= 0.7  →  EEGBlinkTrigger  →  UnityEvent (action configured in Inspector)
```

Typical use: confirm menu selection, activate a special ability, trigger a one-shot action.

### `EEGReceiverMock.cs` — testing without hardware

Currently commented out. Simulates `focus = 1.0` while the mouse button is held and `focus = 0.0` otherwise. Re-enable by uncommenting the class body.

---

## Available values in `EEGReceiver`

**EEG — updated every ~250 ms**

| Field | Range | Source | Current use |
|-------|-------|--------|-------------|
| `focus` | 0–1 | EEGNet | Blink probability; saturated to 1.0 when > 0.7 — trigger via `EEGBlinkTrigger` (threshold 0.7) |
| `engagement` | 0–1 | DSP (β/α+β) | Available; not connected to active mechanics |
| `alpha` | 0–1 | DSP (normalized) | Available |
| `beta` | 0–1 | DSP (normalized) | Available |
| `theta` | 0–1 | DSP (normalized) | Available |

**IMU — unfiltered pass-through**

| Field | Unit | At rest | Current use |
|-------|------|---------|-------------|
| `accelX` / `accelY` | mg | ≈ 0 | Available; not connected to active mechanics |
| `accelZ` | mg | ≈ 1000 (1g) | Available |
| `gyroX` / `gyroY` / `gyroZ` | °/s | ≈ 0 | Used by `control/gyro_mouse.py` (outside Unity) |

---

## Create the Unity project

1. Open Unity Hub → **Open** → select the `game/` folder from this repo
2. For a new project: **New Project** → 2D template → set Location to `game/`
3. Unity will create `ProjectSettings/`, `Packages/`, `Library/`, etc. inside `game/`
4. Scripts in `Assets/Scripts/` will be available as soon as the project opens

---

## EEG scene setup

1. Create an empty **GameObject** → rename it `EEGReceiver`
2. Add `EEGReceiver.cs` as a component
3. For blink detection: add `EEGMouseClicker.cs` (`EEGBlinkTrigger` class) to a GameObject, assign the `EEGReceiver` reference, and wire the `UnityEvent` in the Inspector
4. For development without hardware: uncomment `EEGReceiverMock.cs` and use it instead of `EEGReceiver.cs`

---

## Running

1. Start the Python streamer in another terminal:
   ```bash
   cd signal-processing
   python stream.py --model model-finetuning/models/calibrated.pt [--mock]
   ```
2. Press **Play** in Unity

---

## Recordings

`Grabadora` is a **Singleton** with `DontDestroyOnLoad` — instantiated once and persists across scenes. It records audio from the main `AudioSource` and on stop saves the file to `game/Grabaciones/` with a date-based name: `Grabacion_yyyy-MM-dd_HH-mm-ss.wav`.

`ControladorGrabacionUI` exposes two methods to wire to buttons in the Inspector:
- `BotonEmpezar()` — starts recording
- `BotonParar()` — stops and saves the WAV file

The **Grabaciones** scene lists `.wav` files from `game/Grabaciones/` and allows playback from the UI.

Scenes registered in `EditorBuildSettings.asset`: Menu, Piano, Ritmo, Tambor, and Grabaciones. `TamborMelodia/` is not registered — to include it in a build, open it and use **File → Build Settings → Add Open Scenes**.

---

## Script structure

```
Assets/Scripts/
├── Data_Receiver/
│   ├── EEGReceiver.cs              receives UDP packet from stream.py
│   ├── EEGMouseClicker.cs          EEGBlinkTrigger — fires UnityEvent on blink detection (focus >= 0.7)
│   └── EEGReceiverMock.cs          mock for development without hardware  [currently commented out]
├── AdministradorEscenas.cs         generic scene loader: IrAEscena(string nombreEscena)
├── Menu_Principal/
│   ├── MenuSystem.cs               loads game scene / quits
│   └── SeleccionarInstrumento.cs   generates level selection buttons
├── Menu/
│   └── MenuManager.cs              scene navigation (Drums / Piano / Ritmo / Menu / Grabaciones)
├── TamborMelodia/
│   ├── GameManager.cs              scoring, final rank, game flow
│   ├── Beatscroller.cs             scrolls notes at BPM speed
│   ├── NodeObject.cs               individual tile — Perfect / Good / Normal / Miss zones
│   ├── ButtonController.cs         button visual feedback
│   └── EffectObject.cs             temporary hit/miss visual effects
├── Ritmo/
│   └── JuegoRitmoUnificado.cs      learn + reproduce rhythm, scoring by %
├── Piano/
│   └── MusicNotes.cs               plays notes (C–B) via AudioSource
├── Tambor/
│   └── TamborLibre.cs              free drums with random pitch; ignores clicks on UI
└── Grabaciones/
    ├── Grabadora.cs                Singleton — records audio to WAV in game/Grabaciones/ with date-based name
    ├── ControladorGrabacionUI.cs   UI bridge: BotonEmpezar() / BotonParar() → Grabadora.instancia
    ├── SavWav.cs                   WAV file writer utility (16-bit PCM)
    ├── ListaAudiosManager.cs       lists and plays .wav files from the Grabaciones/ folder
    └── FilaAudio.cs                UI row for each recording file
```

---

## Unity notes

- Unity version used: **Unity 6.3**
- Auto-generated folders (`Library/`, `Temp/`, `Obj/`, `Builds/`) are in `.gitignore`
- Do not commit `Library/` — it is regenerated when the project is opened
