using UnityEngine;
using System.IO;
using System.Collections;
using UnityEngine.Networking;
using System.Collections.Generic;

public class ListaAudiosManager : MonoBehaviour
{
    public GameObject prefabFila;      // El objeto con el diseño de la fila
    public Transform contenedorLista; // El objeto 'Content' del ScrollView
    public AudioSource altavozGlobal;

    void Start()
    {
        CargarArchivos();
    }

    void CargarArchivos()
    {
        // 'Application.dataPath' apunta a la carpeta 'Assets' de tu proyecto.
        // Usamos 'Directory.GetParent' para subir un nivel y crearla en la carpeta principal del juego.
        string rutaBase = Directory.GetParent(Application.dataPath).FullName;
        string rutaGrabaciones = Path.Combine(rutaBase, "Grabaciones");

        // Si la carpeta no existe, la creamos
        if (!Directory.Exists(rutaGrabaciones))
        {
            Directory.CreateDirectory(rutaGrabaciones);
            Debug.Log("Carpeta creada en: " + rutaGrabaciones);
        }

        // Ahora buscamos los archivos en esa carpeta específica
        string[] archivos = Directory.GetFiles(rutaGrabaciones, "*.wav");

        foreach (string rutaArchivo in archivos)
        {
            GameObject nuevaFila = Instantiate(prefabFila, contenedorLista);
            string nombreArchivo = Path.GetFileNameWithoutExtension(rutaArchivo);
            nuevaFila.GetComponent<FilaAudio>().Configurar(nombreArchivo, rutaArchivo, this);
        }
    }

    public void ReproducirAudio(string ruta)
    {
        StartCoroutine(CargarYPlay(ruta));
    }

    IEnumerator CargarYPlay(string ruta)
    {
        // Añadimos el prefijo "file://" para que Unity sepa que es un archivo local
        string rutaFormateada = "file://" + ruta;

        using (UnityWebRequest uwr = UnityWebRequestMultimedia.GetAudioClip(rutaFormateada, AudioType.WAV))
        {
            yield return uwr.SendWebRequest();

            if (uwr.result == UnityWebRequest.Result.Success)
            {
                AudioClip clip = DownloadHandlerAudioClip.GetContent(uwr);
                
                if (clip != null)
                {
                    altavozGlobal.clip = clip;
                    altavozGlobal.Play();
                    Debug.Log("Reproduciendo: " + clip.name);
                }
            }
            else
            {
                // Revisa la Consola si sale este error
                Debug.LogError("Error de Unity: " + uwr.error + " en la ruta: " + rutaFormateada);
            }
        }
    }
}