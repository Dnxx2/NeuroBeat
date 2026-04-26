using UnityEngine;

public class ButtonController : MonoBehaviour
{
    private SpriteRenderer theSR;
    public Sprite defaultImage;
    public Sprite pressedImage;

    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {
        theSR = GetComponent<SpriteRenderer>();
    }

    // Update is called once per frame
    void Update()
    {
        // El 0 significa "Clic Izquierdo" o "Tocar la pantalla" en el celular
        if (Input.GetMouseButtonDown(0))
        {
            theSR.sprite = pressedImage;
        }

        if (Input.GetMouseButtonUp(0))
        {
            theSR.sprite = defaultImage;
        }
    }
}