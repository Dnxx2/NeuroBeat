using UnityEngine;
using UnityEngine.Events; // Esto nos permite usar los eventos del Inspector

public class EEGBlinkTrigger : MonoBehaviour
{
    public EEGReceiver eeg;
    public float umbralParpadeo = 0.95f; 
    private bool estabaParpadeando = false;

    [Header("¿Qué script quieres activar?")]
    // Esta variable crea una cajita mágica en el Inspector
    public UnityEvent accionAlParpadear; 

    void Update()
    {
        if (eeg == null) 
        {
            Debug.LogWarning("Falta asignar el EEGReceiver.");
            return;
        }

        bool estaParpadeando = eeg.focus >= umbralParpadeo;

        if (estaParpadeando && !estabaParpadeando)
        {
            Debug.Log("🟢 ¡Parpadeo global detectado! Ejecutando acción...");
            
            // Esto dispara automáticamente cualquier script que hayas configurado en el Inspector
            accionAlParpadear.Invoke(); 
        }

        estabaParpadeando = estaParpadeando;
    }
}