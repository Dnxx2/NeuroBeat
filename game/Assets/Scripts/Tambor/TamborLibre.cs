using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.EventSystems;

public class TamborLibre : MonoBehaviour
{
    private AudioSource miAltavoz;

    void Start()
    {
        // Buscamos el componente Audio Source al iniciar
        miAltavoz = GetComponent<AudioSource>();
    }

    void Update()
    {
        if (Pointer.current != null && Pointer.current.press.wasPressedThisFrame)
        {
            Debug.Log("Clic detectado");
            // Reproducir el sonido de tambor
            ReproducirSonido();
        }
    }

    void ReproducirSonido()
    {
        // Verificamos si el clic fue sobre un botón de la UI
        if (EventSystem.current.IsPointerOverGameObject())
        {
            // Si el mouse está sobre un botón, entramos aquí y nos salimos
            // sin reproducir el sonido.
            return; 
        }

        if (miAltavoz != null)
        {
            // Cambia el tono un poco hacia arriba o hacia abajo en cada clic
            miAltavoz.pitch = Random.Range(0.9f, 1.1f);

            // PlayOneShot es genial porque permite que el sonido 
            // se solape si haces clics muy rápidos
            miAltavoz.PlayOneShot(miAltavoz.clip);
        }
    }
}
