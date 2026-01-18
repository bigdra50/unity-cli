using UnityEngine;

[CreateAssetMenu(fileName = "TestData", menuName = "Test/TestData")]
public class TestScriptableObject : ScriptableObject
{
    public string label = "Default";
    public int value = 0;

    [ContextMenu("Log Info")]
    private void LogInfo()
    {
        Debug.Log($"[TestScriptableObject] Label: {label}, Value: {value}");
    }

    [ContextMenu("Increment Value")]
    private void IncrementValue()
    {
        value++;
        Debug.Log($"[TestScriptableObject] Value incremented to: {value}");
    }
}
