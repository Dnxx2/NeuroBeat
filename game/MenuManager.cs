using UnityEngine;
using UnityEngine.SceneManagement;

public class MenuManager : MonoBehaviour
{
    public void Start()
    {
        Debug.Log("Iniciar el juego");
    }
    public void IrABateria()
    {
        SceneManager.LoadScene("DrumScene");
    }

    public void IrAPiano()
    {
        SceneManager.LoadScene("PianoScene");
    }

    public void IrARitmo()
    {
        SceneManager.LoadScene("RhythmScene");
    }
    public void RegresarAlMenu()
    {
        SceneManager.LoadScene("Menu");
    }

    public void Salir()
    {
        Debug.Log("Salir del juego");
        Application.Quit();
    }
}