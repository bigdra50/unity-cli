using UnityEditor;

namespace CI
{
    /// <summary>
    /// CI batch mode 用: .csproj / .sln を生成して終了する。
    /// Usage: Unity -batchmode -quit -executeMethod CI.GenerateProjectFiles.Run
    /// </summary>
    public static class GenerateProjectFiles
    {
        public static void Run()
        {
            // Rider パッケージ (com.unity.ide.rider) の ProjectGeneration を利用
            var generatorType = System.Type.GetType(
                "Unity.Rider.Editor.ProjectGeneration, Unity.Rider.Editor");

            if (generatorType == null)
            {
                // fallback: SyncVS (Visual Studio パッケージ)
                UnityEditor.SyncVS.SyncSolution();
                return;
            }

            var instance = generatorType
                .GetMethod("GetInstance",
                    System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static)
                ?.Invoke(null, null);

            if (instance == null)
            {
                UnityEditor.SyncVS.SyncSolution();
                return;
            }

            generatorType
                .GetMethod("Sync",
                    System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance)
                ?.Invoke(instance, null);
        }
    }
}
