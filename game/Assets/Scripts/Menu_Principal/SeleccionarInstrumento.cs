using System.Collections;
using System.Collections.Generic; 
using UnityEngine;
using UnityEngine.SceneManagement;

public class SeleccionarInstrumento : MonoBehaviour
{
    public GameObject nivelButtonPrefab;
    public Transform nivelButtonContainer;
    public int totalInstrumentos = 3; // Total de instrumentos disponibles

    void Start()
    {
        GenerarNivelButtons();
    }
    void GenerarNivelButtons()
    {
        for (int i = 1; i <= totalInstrumentos; i++)
        {
            GameObject button = Instantiate(nivelButtonPrefab, nivelButtonContainer);
            button.GetComponentInChildren<UnityEngine.UI.Text>().text = "Instrumento " + i;
            int instrumentoIndex = i; // Captura el índice para el listener
            button.GetComponent<UnityEngine.UI.Button>().onClick.AddListener(() => SceneManager.LoadScene("Nivel_" + instrumentoIndex));
        }
    }
}
