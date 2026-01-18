using UnityEngine;

public class ContextMenuTest : MonoBehaviour
{
    public string message = "Hello";
    public int counter = 0;

    [ContextMenu("Say Hello")]
    private void SayHello()
    {
        Debug.Log($"[ContextMenuTest] {message}! Counter: {counter}");
    }

    [ContextMenu("Increment Counter")]
    private void IncrementCounter()
    {
        counter++;
        Debug.Log($"[ContextMenuTest] Counter incremented to: {counter}");
    }

    [ContextMenu("Reset Counter")]
    private void ResetCounter()
    {
        counter = 0;
        Debug.Log("[ContextMenuTest] Counter reset to 0");
    }
}
