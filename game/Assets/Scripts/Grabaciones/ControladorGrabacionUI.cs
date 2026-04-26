using UnityEngine;
using UnityEngine.UI;

public class ControladorGrabacionUI : MonoBehaviour
{
    // Estos métodos los llamaremos desde los botones
    public void BotonEmpezar()
    {
        if (Grabadora.instancia != null)
            Grabadora.instancia.EmpezarGrabacion();
    }

    public void BotonParar()
    {
        if (Grabadora.instancia != null)
            Grabadora.instancia.PararGrabacion();
    }
}