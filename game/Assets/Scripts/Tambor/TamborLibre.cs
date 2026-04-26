using UnityEngine;
using UnityEngine.InputSystem;

public class TamborLibre : MonoBehaviour
{
    private AudioSource miAltavoz;

    public void Start()
    {
        // Buscamos el componente Audio Source al iniciar
        miAltavoz = GetComponent<AudioSource>();
    }

    public void Update()
    {
        if (Pointer.current != null && Pointer.current.press.wasPressedThisFrame)
        {
            Debug.Log("Clic detectado");
            // Reproducir el sonido de tambor
            ReproducirSonido();
        }
    }

    public void ReproducirSonido()
    {
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
