using System.Threading;
using UnityBridge.Helpers;
using UnityEditor;

namespace UnityBridge.Tests
{
    /// <summary>
    /// Menu items to trigger domain reload with configurable delays for testing.
    /// </summary>
    public static class DomainReloadTestHelper
    {
        private const string SessionStateKeySlowReloadEnabled = "UnityBridge.Test.SlowReloadEnabled";
        private const string SessionStateKeySlowReloadDelayMs = "UnityBridge.Test.SlowReloadDelayMs";

        [MenuItem("UnityBridge/Test/Trigger Slow Reload (5s delay)")]
        public static void TriggerSlowReload()
        {
            TriggerReloadWithDelay(5000);
        }

        [MenuItem("UnityBridge/Test/Trigger Slow Reload (10s delay)")]
        public static void TriggerVerySlowReload()
        {
            TriggerReloadWithDelay(10000);
        }

        private static void TriggerReloadWithDelay(int delayMs)
        {
            SessionState.SetBool(SessionStateKeySlowReloadEnabled, true);
            SessionState.SetInt(SessionStateKeySlowReloadDelayMs, delayMs);

            BridgeLog.Info($"Triggering domain reload with {delayMs}ms delay");
            AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);
        }

        internal static bool IsSlowReloadEnabled => SessionState.GetBool(SessionStateKeySlowReloadEnabled, false);
        internal static int SlowReloadDelayMs => SessionState.GetInt(SessionStateKeySlowReloadDelayMs, 0);
        internal static void ClearSlowReloadFlag() => SessionState.SetBool(SessionStateKeySlowReloadEnabled, false);
    }

    /// <summary>
    /// Simulates slow domain reload by blocking during assembly reload.
    /// Used for testing relay server's RELOADING state handling.
    /// </summary>
    [InitializeOnLoad]
    internal static class SlowReloadSimulator
    {
        static SlowReloadSimulator()
        {
            if (!DomainReloadTestHelper.IsSlowReloadEnabled)
            {
                return;
            }

            var delayMs = DomainReloadTestHelper.SlowReloadDelayMs;
            DomainReloadTestHelper.ClearSlowReloadFlag();

            BridgeLog.Warn($"SlowReloadSimulator: Simulating slow reload ({delayMs}ms delay)");
            Thread.Sleep(delayMs);
            BridgeLog.Warn("SlowReloadSimulator: Slow reload simulation complete");
        }
    }
}
