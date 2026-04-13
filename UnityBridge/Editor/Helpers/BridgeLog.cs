using System.Diagnostics;
using System.Threading;
using UnityEditor;
using Debug = UnityEngine.Debug;

namespace UnityBridge.Helpers
{
    /// <summary>
    /// Centralized logging for UnityBridge.
    ///
    /// Log levels:
    /// - Info: Important events (connection, disconnection, server start/stop)
    /// - Verbose: Detailed events (status changes, command details) - only with UNITY_BRIDGE_VERBOSE
    /// - Warn: Warnings (recoverable errors)
    /// - Error: Errors (failures)
    ///
    /// To enable verbose logging, add UNITY_BRIDGE_VERBOSE to Scripting Define Symbols.
    /// </summary>
    internal static class BridgeLog
    {
        private const string Prefix = "[UnityBridge]";
        private const string RelayPrefix = "[Relay Server]";

        private const string InfoColor = "#2EA3FF";
        private const string VerboseColor = "#6AA84F";
        private const string WarnColor = "#cc7a00";
        private const string ErrorColor = "#cc3333";

        private const string EnabledKey = "UnityBridge.LogEnabled";

        // EditorPrefs is main-thread only. The send path in RelayClient runs
        // continuations on the thread pool (ConfigureAwait(false)) so PONG cannot be
        // starved by a stalled main thread, which means BridgeLog must be safe to call
        // from any thread. Cache the toggle here and refresh it on the main thread via
        // [InitializeOnLoadMethod] and the setter.
        private static int _enabledCache = 1;

        [InitializeOnLoadMethod]
        private static void RefreshEnabledCache()
        {
            try
            {
                Volatile.Write(ref _enabledCache, EditorPrefs.GetBool(EnabledKey, true) ? 1 : 0);
            }
            catch
            {
                // Fall back to enabled if EditorPrefs is unavailable (e.g. batch mode init order)
                Volatile.Write(ref _enabledCache, 1);
            }
        }

        /// <summary>
        /// Enable or disable all console logging.
        /// </summary>
        public static bool Enabled
        {
            get => Volatile.Read(ref _enabledCache) != 0;
            set
            {
                EditorPrefs.SetBool(EnabledKey, value);
                Volatile.Write(ref _enabledCache, value ? 1 : 0);
            }
        }

        /// <summary>
        /// Log important events (always shown).
        /// Use for: connection established, server started/stopped, critical state changes.
        /// </summary>
        public static void Info(string message)
        {
            if (!Enabled) return;
            Debug.Log(Format(Prefix, message, InfoColor));
        }

        /// <summary>
        /// Log detailed events (only with UNITY_BRIDGE_VERBOSE define).
        /// Use for: status transitions, command details, heartbeat, protocol messages.
        /// </summary>
        [Conditional("UNITY_BRIDGE_VERBOSE")]
        public static void Verbose(string message)
        {
            if (!Enabled) return;
            Debug.Log(Format(Prefix, message, VerboseColor));
        }

        /// <summary>
        /// Log warnings (always shown).
        /// Use for: recoverable errors, unexpected but handled situations.
        /// </summary>
        public static void Warn(string message)
        {
            if (!Enabled) return;
            Debug.LogWarning(Format(Prefix, message, WarnColor));
        }

        /// <summary>
        /// Log errors (always shown).
        /// Use for: failures, unrecoverable errors.
        /// </summary>
        public static void Error(string message)
        {
            if (!Enabled) return;
            Debug.LogError(Format(Prefix, message, ErrorColor));
        }

        /// <summary>
        /// Log relay server output (always shown).
        /// </summary>
        public static void Relay(string message)
        {
            if (!Enabled) return;
            Debug.Log(Format(RelayPrefix, message, InfoColor));
        }

        /// <summary>
        /// Log relay server error output (always shown).
        /// </summary>
        public static void RelayError(string message)
        {
            if (!Enabled) return;
            Debug.LogError(Format(RelayPrefix, message, ErrorColor));
        }

        private static string Format(string prefix, string message, string color)
        {
            return $"<color={color}>{prefix}</color> {message}";
        }
    }
}
