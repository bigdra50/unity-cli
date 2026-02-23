using System;
using System.Reflection;
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
            if (TrySyncViaRider())
                return;

            SyncFallback();
        }

        private static bool TrySyncViaRider()
        {
            var generatorType = Type.GetType(
                "Unity.Rider.Editor.ProjectGeneration, Unity.Rider.Editor");
            if (generatorType == null)
                return false;

            var instance = generatorType
                .GetMethod("GetInstance", BindingFlags.Public | BindingFlags.Static)
                ?.Invoke(null, null);
            if (instance == null)
                return false;

            generatorType
                .GetMethod("Sync", BindingFlags.Public | BindingFlags.Instance)
                ?.Invoke(instance, null);
            return true;
        }

        private static void SyncFallback()
        {
#if UNITY_6000_0_OR_NEWER
            // Unity 6 で SyncVS が internal になったためリフレクション経由
            var syncVsType = typeof(Editor).Assembly.GetType("UnityEditor.SyncVS");
            syncVsType?.GetMethod("SyncSolution",
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static)
                ?.Invoke(null, null);
#else
            SyncVS.SyncSolution();
#endif
        }
    }
}
