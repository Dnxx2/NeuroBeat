# Game — Unity

Juego de ritmo (Piano Tiles) controlado por señales EEG del Unicorn Black.

---

## Creacion juego

**Pasos para integrar:**

1. Abrir Unity Hub → **New Project** → elegir cualquier template 2D
2. En **Location**, apuntar a la carpeta `game/` de este repo
3. Unity creará `ProjectSettings/`, `Packages/`, etc. dentro de `game/`
4. El script `Assets/Scripts/EEGReceiver.cs` ya estará ahí al abrir el proyecto

---

## Recibir señal EEG en Unity

### Setup (una sola vez)

1. En la jerarquía de la escena, crear un **GameObject vacío** → renombrarlo `EEGReceiver`
2. Arrastrar `Assets/Scripts/EEGReceiver.cs` al GameObject
3. Verificar que el puerto coincide con el de `stream.py` (default: **5005**)

### Correr

1. Primero arrancar el streamer Python:
   ```bash
   cd signal-processing
   python stream.py --model model-finetuning/models/subject_01.pt --mock
   ```
2. Luego dar Play en Unity

### Usar los valores en tus scripts

```csharp
public class TileController : MonoBehaviour
{
    public EEGReceiver eeg;     // arrastrar el GameObject EEGReceiver aquí
    public float minSpeed = 3f;
    public float maxSpeed = 12f;

    void Update()
    {
        // Velocidad de tiles según concentración del modelo
        float speed = Mathf.Lerp(minSpeed, maxSpeed, eeg.focus);

        // Multiplicador por concentración sostenida (DSP manual)
        float multiplier = eeg.engagement > 0.7f ? 2f : 1f;
    }
}
```

### Valores disponibles en `EEGReceiver`

| Campo | Rango | Fuente | Uso sugerido |
|-------|-------|--------|--------------|
| `focus` | 0–1 | Modelo EEGNet | Velocidad de tiles, dificultad |
| `engagement` | 0–1 | DSP (β/α+β) | Multiplicador de puntos |
| `alpha` | 0–1 | DSP (normalizado) | Efectos visuales de relajación |
| `beta` | 0–1 | DSP (normalizado) | Intensidad de efectos de concentración |
| `theta` | 0–1 | DSP (normalizado) | Somnolencia / advertencia al jugador |

Todos se actualizan automáticamente cada ~250 ms. Son thread-safe — el receptor UDP corre en un thread propio y copia los valores al main thread en `Update()`.

---

## Sin hardware — modo mock

Para desarrollar el juego sin el Unicorn conectado:

```bash
python stream.py --model model-finetuning/models/subject_01.pt --mock
```

Envía valores sintéticos (señal aleatoria) al mismo puerto UDP. Unity no distingue la diferencia.
