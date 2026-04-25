using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

/// <summary>
/// Recibe el paquete UDP de signal-processing/stream.py cada ~250 ms
/// y expone los valores como campos públicos para otros scripts.
///
/// Setup:
///   1. Adjuntar este script a un GameObject vacío llamado "EEGReceiver"
///   2. Asegurarse de que stream.py corre en la misma máquina (127.0.0.1:5005)
///   3. Leer los valores desde cualquier otro script:
///        float speed = eegReceiver.focus * maxSpeed;
/// </summary>
public class EEGReceiver : MonoBehaviour
{
    [Header("Valores EEG — actualizados cada ~250 ms")]
    [Tooltip("Probabilidad de FOCUS del modelo EEGNet (0 = relajado, 1 = concentrado)")]
    public float focus      = 0f;

    [Tooltip("Potencia alpha frontal normalizada (relajación)")]
    public float alpha      = 0f;

    [Tooltip("Potencia beta frontal normalizada (concentración)")]
    public float beta       = 0f;

    [Tooltip("Potencia theta frontal normalizada (somnolencia)")]
    public float theta      = 0f;

    [Tooltip("beta / (alpha + beta) — índice clásico de engagement (0-1)")]
    public float engagement = 0f;

    [Header("Config")]
    public int port = 5005;

    // ── Internals ─────────────────────────────────────────────────────────────
    UdpClient _udp;
    Thread    _thread;
    bool      _running;

    // Staging buffer — el thread UDP escribe aquí, Update() copia al main thread
    float _sFocus, _sAlpha, _sBeta, _sTheta, _sEngagement;
    readonly object _lock = new object();

    void Start()
    {
        _udp     = new UdpClient(port);
        _running = true;
        _thread  = new Thread(ReceiveLoop) { IsBackground = true };
        _thread.Start();
        Debug.Log($"[EEGReceiver] Escuchando UDP en puerto {port}");
    }

    void ReceiveLoop()
    {
        var ep = new IPEndPoint(IPAddress.Any, 0);
        while (_running)
        {
            try
            {
                byte[] data = _udp.Receive(ref ep);
                string json = Encoding.UTF8.GetString(data);
                lock (_lock)
                {
                    _sFocus      = ParseFloat(json, "focus");
                    _sAlpha      = ParseFloat(json, "alpha");
                    _sBeta       = ParseFloat(json, "beta");
                    _sTheta      = ParseFloat(json, "theta");
                    _sEngagement = ParseFloat(json, "engagement");
                }
            }
            catch { /* ignorar errores de red durante shutdown */ }
        }
    }

    // Unity solo permite leer/escribir sus variables en el main thread
    void Update()
    {
        lock (_lock)
        {
            focus      = _sFocus;
            alpha      = _sAlpha;
            beta       = _sBeta;
            theta      = _sTheta;
            engagement = _sEngagement;
        }
    }

    void OnDestroy()
    {
        _running = false;
        _udp?.Close();
        _thread?.Join(300);
    }

    // Parseo manual de JSON para no requerir dependencias externas
    static float ParseFloat(string json, string key)
    {
        int i = json.IndexOf($"\"{key}\":");
        if (i < 0) return 0f;
        int start = json.IndexOf(':', i) + 1;
        int end   = json.IndexOfAny(new[] { ',', '}' }, start);
        return float.TryParse(
            json.Substring(start, end - start).Trim(),
            System.Globalization.NumberStyles.Float,
            System.Globalization.CultureInfo.InvariantCulture,
            out float v) ? v : 0f;
    }
}
