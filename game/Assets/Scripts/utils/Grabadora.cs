using UnityEngine;
using System.Collections.Generic;
using System.IO;

public class Grabadora : MonoBehaviour
{
    [Header("Configuración")]
    private int frecuencia;
    private int canales = 2; 
    private bool estaGrabando = false;
    private List<float> bufferDeGrabacion = new List<float>();

    [Header("Referencias")]
    public AudioSource altavozPrincipal;

    void Start()
    {
        // Se sincroniza con la frecuencia de tu tarjeta de sonido
        frecuencia = AudioSettings.outputSampleRate;

        if (altavozPrincipal != null)
        {
            altavozPrincipal.Play(); // Activa el flujo de datos
        }
    }

    void OnAudioFilterRead(float[] data, int channels)
    {
        if (estaGrabando)
        {
            this.canales = channels;

            for (int i = 0; i < data.Length; i++)
            {
                // ATENUACIÓN: Multiplicamos por 0.7f para que los sonidos
                // mezclados no saturen el archivo final.
                bufferDeGrabacion.Add(data[i] * 0.7f);
            }
        }
    }

    public void EmpezarGrabacion()
    {
        Debug.Log(">>> GRABANDO... Presiona tus botones ahora.");
        bufferDeGrabacion.Clear();
        estaGrabando = true;
    }

    public void PararGrabacion()
    {
        if (!estaGrabando) return;
        estaGrabando = false;

        if (bufferDeGrabacion.Count > 0)
        {
            GenerarYGuardar();
        }
        else
        {
            Debug.LogWarning("No se capturó audio. ¿El script está en la cámara?");
        }
    }

    private void GenerarYGuardar()
    {
        int muestrasPorCanal = bufferDeGrabacion.Count / canales;

        AudioClip clipFinal = AudioClip.Create("SecuenciaFinal", muestrasPorCanal, canales, frecuencia, false);
        clipFinal.SetData(bufferDeGrabacion.ToArray(), 0);

        // Ruta: Escritorio del usuario actual
        string escritorio = System.Environment.GetFolderPath(System.Environment.SpecialFolder.Desktop);
        string rutaFinal = Path.Combine(escritorio, "MiGrabacion_Limpia.wav");
        
        SavWav.SaveAbsolute(rutaFinal, clipFinal);

        Debug.Log(">>> ARCHIVO CREADO EXITOSAMENTE: " + rutaFinal);
    }
}