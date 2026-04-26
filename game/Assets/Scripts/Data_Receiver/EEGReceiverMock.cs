using UnityEngine;

public class EEGMockTester : MonoBehaviour
{
    public EEGReceiver eegReceiver;
    public int port = 5005;
    void Update()
    {
        if (eegReceiver == null) return;

        // Simulamos un parpadeo: si presionas el clic, Focus es 1. Si no, es 0.
        if (Input.GetMouseButton(0)) 
        {
            eegReceiver.focus = 1f;
        } 
        else 
        {
            eegReceiver.focus = 0f;
        }
    }
}