using UnityEngine;
using UnityEngine.SceneManagement;

public class MenuManager : MonoBehaviour
{
    public void IrABateria()
    {
        SceneManager.LoadScene("Tambor");
    }

    public void IrAPiano()
    {
        SceneManager.LoadScene("Piano");
    }

    public void IrARitmo()
    {
        SceneManager.LoadScene("Ritmo");
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