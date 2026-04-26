using UnityEngine;
using TMPro;
using System.Collections;
using UnityEngine.InputSystem;
using UnityEngine.SceneManagement;

public class JuegoRitmoUnificado : MonoBehaviour
{
    [Header("1. Textos y UI")]
    public TextMeshProUGUI textoContador;
    public TextMeshProUGUI textoPuntuacion;
    public GameObject objetoMetronomo;

    [Header("2. Sonidos")]
    public AudioSource sonidoAgudo;
    public AudioSource sonidoGrave;
    public float inicioSonidoAgudo = 0f;
    public float inicioSonidoGrave = 0f;

    [Header("3. Efecto Visual (Feedback)")]
    public RectTransform contenedorEfecto; 
    public Transform estrellaVisual;      
    public Transform twirlVisual;         

    [Header("4. Configuración del Nivel")]
    [Tooltip("Cuántos golpes suenan para que el jugador aprenda el ritmo")]
    public int beatsAprendizaje = 4;
    [Tooltip("Cuántos golpes debe acertar el jugador en silencio")]
    public int beatsJugador = 8;
    
    [Header("5. Configuración de Tiempos")]
    public float duracionPopNormal = 0.3f;
    public float duracionEfecto = 1.0f;
    [Tooltip("Pixeles que subirá el efecto en la pantalla")]
    public float alturaDeVuelo = 150f;     

    // Variables internas de Animación
    private AnimationCurve curvaPop;
    private AnimationCurve curvaEscalaEfecto;
    private AnimationCurve curvaElevacionEfecto;
    private Coroutine rutinaEfecto;
    private Vector2 posicionInicialEfecto; 

    // Variables internas de Lógica
    private float[] tiemposEsperados;
    private bool[] beatAceptado;
    private int beatsCompletados = 0;
    private float sumaPuntuaciones = 0f;
    private bool esperandoInput = false;
    private bool juegoTerminado = false; 
    private bool puedeReiniciar = false; 

    void Awake()
    {
        curvaPop = new AnimationCurve(new Keyframe(0, 0), new Keyframe(0.6f, 1.2f), new Keyframe(1, 1));
        curvaEscalaEfecto = new AnimationCurve(new Keyframe(0, 0), new Keyframe(0.2f, 1.2f), new Keyframe(1, 0));
        curvaElevacionEfecto = AnimationCurve.EaseInOut(0, 0, 1, 1);
    }

    void Start()
    {
        if (textoPuntuacion != null) textoPuntuacion.text = "Haz  clic en esta ventana para jugar";
        if (textoContador != null) textoContador.text = "";
        if (objetoMetronomo != null) objetoMetronomo.SetActive(false);
        
        // --- BLINDAJE TOTAL DE LA ESTRELLA ---
        if (contenedorEfecto != null)
        {
            // 1. Obligamos a que se dibuje POR ENCIMA de todos los demás elementos del Canvas
            contenedorEfecto.SetAsLastSibling();

            // 2. Centramos el contenedor principal pero lo SUBIMOS un poco (ej: 150 px) para no chocar con el contador
            contenedorEfecto.anchoredPosition = new Vector2(0f, 150f);
            posicionInicialEfecto = contenedorEfecto.anchoredPosition;
            contenedorEfecto.localScale = Vector3.zero;
            
            // 3. Forzamos a los hijos a estar en el centro y tener un TAMAÑO REAL (250x250 px)
            if (estrellaVisual != null) 
            {
                estrellaVisual.localPosition = Vector3.zero;
                estrellaVisual.localScale = Vector3.one;
                RectTransform rtEstrella = estrellaVisual.GetComponent<RectTransform>();
                if (rtEstrella != null) rtEstrella.sizeDelta = new Vector2(250, 250);
            }
            if (twirlVisual != null) 
            {
                twirlVisual.localPosition = Vector3.zero;
                twirlVisual.localScale = Vector3.one;
                RectTransform rtTwirl = twirlVisual.GetComponent<RectTransform>();
                if (rtTwirl != null) rtTwirl.sizeDelta = new Vector2(250, 250);
            }

            contenedorEfecto.gameObject.SetActive(false);
        }

        StartCoroutine(SecuenciaPrincipal());
    }

    IEnumerator SecuenciaPrincipal()
    {
        yield return new WaitForSeconds(1.5f); 
        if (textoPuntuacion != null) textoPuntuacion.text = "";

        string[] cuenta = { "3", "2", "1", "¡GO!" };
        
        foreach (string paso in cuenta)
        {
            if (textoContador != null) textoContador.text = paso;
            if (textoContador != null) StartCoroutine(EfectoPopUp(textoContador.transform, false));
            yield return new WaitForSeconds(1f);
        }
        if (textoContador != null) textoContador.text = ""; 

        float bpm = Random.Range(60f, 150f);
        float intervalo = 60f / bpm;

        for (int i = 0; i < beatsAprendizaje; i++)
        {
            ReproducirSonido(i == 0); 
            if (objetoMetronomo != null) StartCoroutine(EfectoPopUp(objetoMetronomo.transform, true));
            yield return new WaitForSeconds(intervalo);
        }

        if (objetoMetronomo != null) objetoMetronomo.SetActive(false);

        tiemposEsperados = new float[beatsJugador];
        beatAceptado = new bool[beatsJugador];
        beatsCompletados = 0;
        sumaPuntuaciones = 0f;

        float tiempoActual = Time.time;
        for(int i = 0; i < beatsJugador; i++)
        {
            tiemposEsperados[i] = tiempoActual + (i * intervalo); 
        }

        esperandoInput = true;
        
        // UI: Contador EN LA PARTE INFERIOR
        if (textoPuntuacion != null) 
        {
            // false = Abajo
            AlinearTexto(textoPuntuacion, false);
            textoPuntuacion.fontSize = 120; 
            textoPuntuacion.text = "0";
        }
        
        yield return new WaitForSeconds((beatsJugador * intervalo) + 1.0f); 
        
        if (esperandoInput) 
        {
            FinalizarJuego(); 
        }
    }

    void Update()
    {
        if (Pointer.current != null && Pointer.current.press.wasPressedThisFrame)
        {
            if (juegoTerminado)
            {
                if (puedeReiniciar) SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
                return; 
            }

            // MODIFICACIÓN: La estrella y el cálculo de golpes SOLO ocurren cuando es el turno del jugador
            if (esperandoInput)
            {
                if (contenedorEfecto != null) MostrarEfectoEstrella();
                RegistrarGolpe();
            }
        }
    }

    void RegistrarGolpe()
    {
        float tiempoPresionado = Time.time;
        float menorDiferencia = float.MaxValue;
        int indiceMasCercano = -1;

        for (int i = 0; i < beatsJugador; i++)
        {
            if (!beatAceptado[i]) 
            {
                float diff = Mathf.Abs(tiempoPresionado - tiemposEsperados[i]);
                if (diff < menorDiferencia)
                {
                    menorDiferencia = diff;
                    indiceMasCercano = i;
                }
            }
        }

        if (indiceMasCercano != -1)
        {
            beatAceptado[indiceMasCercano] = true;
            beatsCompletados++; 

            float margenError = 0.3f; 
            float porcentaje = Mathf.Clamp01(1f - (menorDiferencia / margenError)) * 100f;
            sumaPuntuaciones += porcentaje;

            if (textoPuntuacion != null)
            {
                textoPuntuacion.text = beatsCompletados.ToString();
            }

            if (beatsCompletados >= beatsJugador)
            {
                FinalizarJuego();
            }
        }
    }

    void FinalizarJuego()
    {
        esperandoInput = false;
        juegoTerminado = true; 

        // ELIMINAR ANIMACIONES RESIDUALES
        if (rutinaEfecto != null) StopCoroutine(rutinaEfecto);
        if (contenedorEfecto != null) contenedorEfecto.gameObject.SetActive(false);

        float scoreFinal = sumaPuntuaciones / beatsJugador;

        // UI: Resultado CENTRADO
        if (textoPuntuacion != null)
        {
            // true = Al centro perfecto
            AlinearTexto(textoPuntuacion, true);
            
            textoPuntuacion.fontSize = 60; 
            textoPuntuacion.text = $"FIN DEL JUEGO\n<size=80>{scoreFinal:F0}%</size>";
        }

        StartCoroutine(HabilitarReinicio());
    }

    IEnumerator HabilitarReinicio()
    {
        yield return new WaitForSeconds(2f); 
        puedeReiniciar = true; 

        if (textoPuntuacion != null)
        {
            textoPuntuacion.text += "\n<size=30>CLIC para reiniciar</size>";
        }
    }

    // --- HERRAMIENTA NUEVA: Alineación Dinámica de UI ---
    void AlinearTexto(TextMeshProUGUI texto, bool alCentro)
    {
        texto.alignment = TextAlignmentOptions.Center;
        RectTransform rt = texto.rectTransform;
        
        if (alCentro)
        {
            // Le damos una caja grande para el texto de resultado final
            rt.sizeDelta = new Vector2(800f, 300f);

            // Colocamos pivote y anclas en el centro exacto
            rt.anchorMin = new Vector2(0.5f, 0.5f);
            rt.anchorMax = new Vector2(0.5f, 0.5f);
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.anchoredPosition = Vector2.zero;
        }
        else
        {
            // Reducimos la altura de la caja para el contador (así no "trepa" hacia el centro)
            rt.sizeDelta = new Vector2(400f, 150f);

            // Colocamos pivote y anclas en la parte inferior central
            rt.anchorMin = new Vector2(0.5f, 0f);
            rt.anchorMax = new Vector2(0.5f, 0f);
            rt.pivot = new Vector2(0.5f, 0f);
            
            // Lo pegamos al borde inferior, subiéndolo solo 50 píxeles
            rt.anchoredPosition = new Vector2(0f, 50f);
        }
    }

    void ReproducirSonido(bool esAgudo)
    {
        AudioSource source = esAgudo ? sonidoAgudo : sonidoGrave;
        float recorte = esAgudo ? inicioSonidoAgudo : inicioSonidoGrave;

        if (source != null && source.clip != null)
        {
            source.gameObject.SetActive(true);
            if (recorte > 0 && recorte < source.clip.length) source.time = recorte;
            source.Play();
        }
    }

    void RepararObjetoVisual(Transform obj)
    {
        Animator anim = obj.GetComponent<Animator>();
        if (anim != null) anim.enabled = false;

        UnityEngine.UI.Graphic[] graficos = obj.GetComponentsInChildren<UnityEngine.UI.Graphic>(true);
        foreach (var g in graficos)
        {
            Color c = g.color; 
            c.a = 1f; 
            g.color = c;
        }
    }

    IEnumerator EfectoPopUp(Transform obj, bool rotar)
    {
        RepararObjetoVisual(obj); 

        obj.gameObject.SetActive(true);
        if (rotar) obj.localRotation = Quaternion.Euler(0, 0, Random.Range(-15f, 15f));
        else obj.localRotation = Quaternion.identity;

        float t = 0;
        while (t < duracionPopNormal)
        {
            t += Time.deltaTime;
            float escala = curvaPop.Evaluate(t / duracionPopNormal);
            obj.localScale = new Vector3(escala, escala, 1f);
            yield return null;
        }
        obj.localScale = Vector3.one; 
    }

    void MostrarEfectoEstrella()
    {
        if (rutinaEfecto != null) StopCoroutine(rutinaEfecto);
        rutinaEfecto = StartCoroutine(RutinaEstrella());
    }

    IEnumerator RutinaEstrella()
    {
        contenedorEfecto.gameObject.SetActive(true);
        RepararObjetoVisual(contenedorEfecto); 

        estrellaVisual.localRotation = Quaternion.identity;
        twirlVisual.localRotation = Quaternion.identity;
        float t = 0;

        while (t < duracionEfecto)
        {
            t += Time.deltaTime;
            float porcentaje = t / duracionEfecto;

            float escala = curvaEscalaEfecto.Evaluate(porcentaje);
            contenedorEfecto.localScale = new Vector3(escala, escala, 1f);
            
            contenedorEfecto.anchoredPosition = posicionInicialEfecto + new Vector2(0, curvaElevacionEfecto.Evaluate(porcentaje) * alturaDeVuelo);

            twirlVisual.Rotate(Vector3.forward, -360f * Time.deltaTime);
            estrellaVisual.Rotate(Vector3.forward, Mathf.Sin(porcentaje * Mathf.PI * 2) * 45f * Time.deltaTime);

            yield return null;
        }
        contenedorEfecto.gameObject.SetActive(false);
    }
}