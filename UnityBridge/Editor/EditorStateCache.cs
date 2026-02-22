using System;
using System.Reflection;
using System.Threading;
using UnityBridge.Helpers;
using UnityBridge.Tools;
using UnityEditor;
using UnityEditor.Compilation;

namespace UnityBridge
{
    /// <summary>
    /// Monitors editor activity phases and sends STATUS messages to the relay server.
    /// Single source of truth for STATUS publishing — BridgeReloadHandler delegates here.
    /// </summary>
    [InitializeOnLoad]
    internal static class EditorStateCache
    {
        private static string _currentPhase = ActivityPhase.Idle;
        private static string _lastSentPhase;
        private static bool _domainReloadPending;
        private static bool _compilationEventActive;
        private static double _lastUpdateTime;
        private const double MinUpdateIntervalSeconds = 1.0;

        private static readonly Func<bool> s_isCompiling;

        static EditorStateCache()
        {
            // Cache CompilationPipeline.isCompiling as a delegate to avoid reflection per tick
            var prop = typeof(CompilationPipeline)
                .GetProperty("isCompiling", BindingFlags.Static | BindingFlags.Public);
            if (prop != null)
                s_isCompiling = (Func<bool>)Delegate.CreateDelegate(
                    typeof(Func<bool>), prop.GetGetMethod());
            else
                s_isCompiling = () => EditorApplication.isCompiling;

            CompilationPipeline.compilationStarted += _ =>
            {
                _compilationEventActive = true;
                EvaluatePhase();
            };
            // compilationFinished: clear flag only. Actual transition deferred to watchdog tick
            // because Unity's isCompiling may still return true immediately after this event.
            CompilationPipeline.compilationFinished += _ => { _compilationEventActive = false; };

            EditorApplication.playModeStateChanged += _ => EvaluatePhase();
            EditorApplication.update += OnUpdate;

            BridgeLog.Verbose("[EditorStateCache] Initialized");
        }

        /// <summary>
        /// Called by BridgeReloadHandler before domain reload.
        /// </summary>
        public static void SetDomainReloading(bool value)
        {
            _domainReloadPending = value;
        }

        /// <summary>
        /// Synchronously flush STATUS "reloading" before domain reload destroys this class.
        /// </summary>
        public static void FlushStatus()
        {
            var manager = BridgeManager.Instance;
            if (manager?.Client is not { IsConnected: true }) return;

            try
            {
                using var cts = new CancellationTokenSource(500);
                var task = manager.Client.SendReloadingStatusAsync();
                task.Wait(cts.Token);
                _lastSentPhase = "reloading";
            }
            catch (OperationCanceledException)
            {
                BridgeLog.Verbose("[EditorStateCache] FlushStatus timed out, relying on status file");
            }
            catch (AggregateException ex)
            {
                BridgeLog.Warn($"[EditorStateCache] FlushStatus failed: {ex.InnerException?.Message ?? ex.Message}");
            }
        }

        /// <summary>
        /// Called after reconnect to force-send the current phase.
        /// </summary>
        public static void SyncCurrentState()
        {
            var manager = BridgeManager.Instance;
            if (manager?.Client is not { IsConnected: true }) return;

            _domainReloadPending = false;
            _lastSentPhase = null; // force re-send
            EvaluatePhase();
        }

        private static void OnUpdate()
        {
            // Skip evaluation when not connected — no one to send STATUS to
            var manager = BridgeManager.Instance;
            if (manager?.Client is not { IsConnected: true }) return;

            double now = EditorApplication.timeSinceStartup;
            if (now - _lastUpdateTime < MinUpdateIntervalSeconds) return;
            _lastUpdateTime = now;
            EvaluatePhase();
        }

        private static void EvaluatePhase()
        {
            if (_domainReloadPending) return; // BridgeReloadHandler owns this state

            string phase;
            if (Tests.IsRunning)
                phase = ActivityPhase.RunningTests;
            else if (_compilationEventActive || s_isCompiling())
                phase = ActivityPhase.Compiling;
            else if (EditorApplication.isUpdating)
                phase = ActivityPhase.AssetImport;
            else if (EditorApplication.isPlayingOrWillChangePlaymode && !EditorApplication.isPlaying)
                phase = ActivityPhase.PlaymodeTransition;
            else
                phase = ActivityPhase.Idle;

            _currentPhase = phase;
            SendIfChanged(phase);
        }

        private static async void SendIfChanged(string phase)
        {
            if (phase == _lastSentPhase) return;

            var manager = BridgeManager.Instance;
            if (manager?.Client is not { IsConnected: true }) return;

            try
            {
                if (phase == ActivityPhase.Idle)
                    await manager.Client.SendStatusAsync(InstanceStatus.Ready);
                else
                    await manager.Client.SendStatusAsync(InstanceStatus.Busy, phase);

                _lastSentPhase = phase;
            }
            catch (Exception ex)
            {
                BridgeLog.Warn($"[EditorStateCache] Failed to send phase '{phase}': {ex.Message}");
                // _lastSentPhase not updated — will retry on next evaluation
            }
        }

        public static string CurrentPhase => _currentPhase;
    }
}
