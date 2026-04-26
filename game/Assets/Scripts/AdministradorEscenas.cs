using UnityEngine;

using UnityEngine;
using UnityEngine.SceneManagement; // Necesario para cambiar escenas

public class AdministradorEscenas : MonoBehaviour
{
    public void IrAEscena(string nombreEscena)
    {
        SceneManager.LoadScene(nombreEscena);
    }
}