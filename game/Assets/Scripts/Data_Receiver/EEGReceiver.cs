// using System.Net;
// using System.Net.Sockets;
// using System.Text;
// using System.Threading;
// using UnityEngine;

// /// <summary>
// /// Recibe el paquete UDP de signal-processing/stream.py cada ~250 ms
// /// y expone los valores como campos públicos para otros scripts.
// ///
// /// Setup:
// ///   1. Adjuntar este script a un GameObject vacío llamado "EEGReceiver"
// ///   2. Asegurarse de que stream.py corre en la misma máquina (127.0.0.1:5005)
// ///   3. Leer los valores desde cualquier otro script:
// ///        float speed = eegReceiver.focus * maxSpeed;
// /// </summary>
// public class EEGReceiver : MonoBehaviour
// {
//     [Header("Valores EEG — actualizados cada ~250 ms")]
//     [Tooltip("Probabilidad de FOCUS del modelo EEGNet (0 = relajado, 1 = concentrado)")]
//     public float focus      = 0f;

//     [Tooltip("Potencia alpha frontal normalizada (relajación)")]
//     public float alpha      = 0f;

//     [Tooltip("Potencia beta frontal normalizada (concentración)")]
//     public float beta       = 0f;

//     [Tooltip("Potencia theta frontal normalizada (somnolencia)")]
//     public float theta      = 0f;

//     [Tooltip("beta / (alpha + beta) — índice clásico de engagement (0-1)")]
//     public float engagement = 0f;

//     [Header("IMU — actualizados cada muestra (~4 ms)")]
//     [Tooltip("Acelerómetro X en mg (±2g range). En reposo: X≈0, Y≈0, Z≈1000")]
//     public float accelX = 0f;
//     [Tooltip("Acelerómetro Y en mg")]
//     public float accelY = 0f;
//     [Tooltip("Acelerómetro Z en mg")]
//     public float accelZ = 0f;

//     [Tooltip("Giroscopio X en °/s. En reposo ≈ 0")]
//     public float gyroX = 0f;
//     [Tooltip("Giroscopio Y en °/s")]
//     public float gyroY = 0f;
//     [Tooltip("Giroscopio Z en °/s")]
//     public float gyroZ = 0f;

//     [Header("Config")]
//     public int port = 5005;

//     // ── Internals ─────────────────────────────────────────────────────────────
//     UdpClient _udp;
//     Thread    _thread;
//     bool      _running;

//     // Staging buffer — el thread UDP escribe aquí, Update() copia al main thread
//     float _sFocus, _sAlpha, _sBeta, _sTheta, _sEngagement;
//     float _sAccelX, _sAccelY, _sAccelZ;
//     float _sGyroX,  _sGyroY,  _sGyroZ;
//     readonly object _lock = new object();

//     void Start()
//     {
//         _udp     = new UdpClient(port);
//         _running = true;
//         _thread  = new Thread(ReceiveLoop) { IsBackground = true };
//         _thread.Start();
//         Debug.Log($"[EEGReceiver] Escuchando UDP en puerto {port}");
//     }

//     void ReceiveLoop()
//     {
//         var ep = new IPEndPoint(IPAddress.Any, 0);
//         while (_running)
//         {
//             try
//             {
//                 byte[] data = _udp.Receive(ref ep);
//                 string json = Encoding.UTF8.GetString(data);
//                 lock (_lock)
//                 {
//                     _sFocus      = ParseFloat(json, "focus");
//                     _sAlpha      = ParseFloat(json, "alpha");
//                     _sBeta       = ParseFloat(json, "beta");
//                     _sTheta      = ParseFloat(json, "theta");
//                     _sEngagement = ParseFloat(json, "engagement");
//                     _sAccelX     = ParseFloat(json, "accel_x");
//                     _sAccelY     = ParseFloat(json, "accel_y");
//                     _sAccelZ     = ParseFloat(json, "accel_z");
//                     _sGyroX      = ParseFloat(json, "gyro_x");
//                     _sGyroY      = ParseFloat(json, "gyro_y");
//                     _sGyroZ      = ParseFloat(json, "gyro_z");
//                 }
//             }
//             catch { /* ignorar errores de red durante shutdown */ }
//         }
//     }

//     // Unity solo permite leer/escribir sus variables en el main thread
//     void Update()
//     {
//         lock (_lock)
//         {
//             focus      = _sFocus;
//             alpha      = _sAlpha;
//             beta       = _sBeta;
//             theta      = _sTheta;
//             engagement = _sEngagement;
//             accelX     = _sAccelX;
//             accelY     = _sAccelY;
//             accelZ     = _sAccelZ;
//             gyroX      = _sGyroX;
//             gyroY      = _sGyroY;
//             gyroZ      = _sGyroZ;
//         }
//     }

//     void OnDestroy()
//     {
//         _running = false;
//         _udp?.Close();
//         _thread?.Join(300);
//     }

//     // Parseo manual de JSON para no requerir dependencias externas
//     static float ParseFloat(string json, string key)
//     {
//         int i = json.IndexOf($"\"{key}\":");
//         if (i < 0) return 0f;
//         int start = json.IndexOf(':', i) + 1;
//         int end   = json.IndexOfAny(new[] { ',', '}' }, start);
//         return float.TryParse(
//             json.Substring(start, end - start).Trim(),
//             System.Globalization.NumberStyles.Float,
//             System.Globalization.CultureInfo.InvariantCulture,
//             out float v) ? v : 0f;
//     }
// }
