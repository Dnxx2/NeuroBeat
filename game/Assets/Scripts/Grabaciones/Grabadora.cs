using UnityEngine;
using System.Collections.Generic;
using System.IO;
using System; // Necesario para DateTime

public class Grabadora : MonoBehaviour
{
    [Header("Configuración")]
    private int frecuencia;
    private int canales = 2; 
    private bool estaGrabando = false;
    private List<float> bufferDeGrabacion = new List<float>();

    [Header("Referencias")]
    public AudioSource altavozPrincipal;

    public static Grabadora instancia;

    void Awake()
    {
        // Si ya existe una grabadora, destruye esta para que no haya duplicados
        if (instancia == null)
        {
            instancia = this;
            DontDestroyOnLoad(gameObject); // Esto la hace persistente entre escenas
        }
        else
        {
            Destroy(gameObject);
        }
    }

    void Start()
    {
        frecuencia = AudioSettings.outputSampleRate;

        if (altavozPrincipal != null)
        {
            altavozPrincipal.Play(); 
        }
    }

    void OnAudioFilterRead(float[] data, int channels)
    {
        if (estaGrabando)
        {
            this.canales = channels;
            for (int i = 0; i < data.Length; i++)
            {
                bufferDeGrabacion.Add(data[i] * 0.7f);
            }
        }
    }

    public void EmpezarGrabacion()
    {
        bufferDeGrabacion.Clear();
        estaGrabando = true;
        Debug.Log(">>> GRABANDO...");
    }

    public void PararGrabacion()
    {
        if (!estaGrabando) return;
        estaGrabando = false;

        if (bufferDeGrabacion.Count > 0)
        {
            GenerarYGuardar();
        }
    }

    private void GenerarYGuardar()
    {
        int muestrasPorCanal = bufferDeGrabacion.Count / canales;
        AudioClip clipFinal = AudioClip.Create("SecuenciaFinal", muestrasPorCanal, canales, frecuencia, false);
        clipFinal.SetData(bufferDeGrabacion.ToArray(), 0);

        // 1. Definir la ruta local (Carpeta raíz del proyecto / Grabaciones)
        string rutaBase = Directory.GetParent(Application.dataPath).FullName;
        string carpetaGrabaciones = Path.Combine(rutaBase, "Grabaciones");

        // 2. Crear la carpeta si no existe
        if (!Directory.Exists(carpetaGrabaciones))
        {
            Directory.CreateDirectory(carpetaGrabaciones);
        }

        // 3. Generar un nombre basado en la fecha y hora actual
        // Formato: Grabacion_2024-05-20_14-30-05.wav
        string nombreArchivo = "Grabacion_" + DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss") + ".wav";
        string rutaFinal = Path.Combine(carpetaGrabaciones, nombreArchivo);
        
        // 4. Guardar usando SavWav
        SavWav.SaveAbsolute(rutaFinal, clipFinal);

        Debug.Log(">>> GRABACIÓN GUARDADA EN: " + rutaFinal);
    }
}