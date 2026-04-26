using UnityEngine;
using UnityEngine.UI;
using TMPro; // Asegúrate de usar TextMeshPro para mejor calidad visual

public class FilaAudio : MonoBehaviour
{
    public TextMeshProUGUI textoNombre;
    private string rutaCompleta;
    private ListaAudiosManager manager;

    // Este método lo llama el Manager al crear la fila
    public void Configurar(string nombre, string ruta, ListaAudiosManager managerPadre)
    {
        textoNombre.text = nombre;
        rutaCompleta = ruta;
        manager = managerPadre;
    }

    // Método que se asigna al botón en el Inspector (On Click)
    public void ClickEnReproducir()
    {
        manager.ReproducirAudio(rutaCompleta);
    }
}