using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class NodeObject : MonoBehaviour
{
    public bool canBePressed;
    public KeyCode keytoPress;
    public GameObject hitEffect, goodEffect, perfectEffect, missEffect;
    private static GameObject efectoActual;
    // Start is called once before the first execution of Update after the MonoBehaviour is created
    void Start()
    {

    }

    void Update()
    {
        if (Input.GetMouseButtonDown(0))
        {
            if (canBePressed)
            {
                gameObject.SetActive(false);
                // ... (tu lógica de puntuación se queda igual)
                if (Mathf.Abs(transform.position.y) > 0.25f)
                {
                    GameManager.instance.NormalHit();

                    // Si ya hay un efecto en pantalla, lo destruimos antes de crear el nuevo
                    if (efectoActual != null) { Destroy(efectoActual); }

                    efectoActual = Instantiate(hitEffect, transform.position, hitEffect.transform.rotation);
                    Destroy(efectoActual, 0.5f);
                }
                else if (Mathf.Abs(transform.position.y) > 0.05f)
                {
                    GameManager.instance.GoodHit();

                    if (efectoActual != null) { Destroy(efectoActual); }

                    efectoActual = Instantiate(goodEffect, transform.position, goodEffect.transform.rotation);
                    Destroy(efectoActual, 0.5f);
                }
                else
                {
                    GameManager.instance.PerfectHit();

                    if (efectoActual != null) { Destroy(efectoActual); }

                    efectoActual = Instantiate(perfectEffect, transform.position, perfectEffect.transform.rotation);
                    Destroy(efectoActual, 0.5f);
                }
            }
        }
    }

  

   
    private void OnTriggerEnter2D(Collider2D other)
    {
        if (other.tag == "Activator")
        {
            canBePressed = true;
        }
    }
    private void OnTriggerExit2D(Collider2D other)
    {
        if (other.tag == "Activator")
        {
            canBePressed = false;
            GameManager.instance.NoteMiss();

            // Hacemos lo mismo para el efecto de Miss
            // ... (código del Miss)
            if (efectoActual != null) { Destroy(efectoActual); }
            efectoActual = Instantiate(missEffect, transform.position, missEffect.transform.rotation);
            Destroy(efectoActual, 0.5f);
        }
    }

}