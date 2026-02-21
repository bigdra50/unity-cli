using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using UnityBridge.Helpers;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace UnityBridge.Tools
{
    [BridgeTool("recorder")]
    public static class Recorder
    {
        private static RecordingSession _session;

        public static Task<JObject> HandleCommand(JObject parameters)
        {
            var action = parameters["action"]?.Value<string>() ?? "status";

            return action.ToLowerInvariant() switch
            {
                "start" => Task.FromResult(Start(parameters)),
                "stop" => Task.FromResult(Stop()),
                "status" => Task.FromResult(GetStatus()),
                _ => throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    $"Unknown action: {action}. Valid actions: start, stop, status")
            };
        }

        private static JObject Start(JObject parameters)
        {
            if (_session != null && _session.IsRecording)
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    "Recording already in progress. Use 'stop' to end current recording.");
            }

            var fps = parameters["fps"]?.Value<int>() ?? 30;
            var format = (parameters["format"]?.Value<string>() ?? "jpg").ToLowerInvariant();
            var quality = parameters["quality"]?.Value<int>() ?? 75;
            var width = parameters["width"]?.Value<int>() ?? 1920;
            var height = parameters["height"]?.Value<int>() ?? 1080;
            var cameraName = parameters["camera"]?.Value<string>();
            var outputDir = parameters["outputDir"]?.Value<string>();

            if (format != "png" && format != "jpg")
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    $"Unknown format: {format}. Valid formats: png, jpg");
            }

            fps = Mathf.Clamp(fps, 1, 120);
            quality = Mathf.Clamp(quality, 1, 100);
            width = Mathf.Max(1, width);
            height = Mathf.Max(1, height);

            if (string.IsNullOrEmpty(outputDir))
            {
                var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                var projectPath = Directory.GetCurrentDirectory();
                outputDir = Path.Combine(projectPath, $"Screenshots/recording_{timestamp}");
            }

            if (!Directory.Exists(outputDir))
            {
                Directory.CreateDirectory(outputDir);
            }

            Camera camera = FindCamera(cameraName);

            _session = new RecordingSession(camera, fps, format, quality, width, height, outputDir);
            _session.Start();

            return new JObject
            {
                ["message"] = $"Recording started at {fps} FPS",
                ["fps"] = fps,
                ["format"] = format,
                ["quality"] = quality,
                ["width"] = width,
                ["height"] = height,
                ["outputDir"] = outputDir,
                ["camera"] = camera.name
            };
        }

        private static JObject Stop()
        {
            if (_session == null || !_session.IsRecording)
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    "No recording in progress.");
            }

            var result = _session.Stop();
            _session = null;
            return result;
        }

        private static JObject GetStatus()
        {
            if (_session == null || !_session.IsRecording)
            {
                return new JObject
                {
                    ["recording"] = false,
                    ["message"] = "No recording in progress"
                };
            }

            return _session.GetStatus();
        }

        private static Camera FindCamera(string cameraName)
        {
            Camera camera = null;
            if (!string.IsNullOrEmpty(cameraName))
            {
                var cameraGo = GameObject.Find(cameraName);
                if (cameraGo != null)
                {
                    camera = cameraGo.GetComponent<Camera>();
                }
            }

            camera ??= Camera.main;

            if (camera == null)
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    "No camera found. Specify camera name or ensure a Main Camera exists.");
            }

            return camera;
        }

        private class RecordingSession
        {
            private readonly Camera _camera;
            private readonly int _targetFps;
            private readonly string _format;
            private readonly int _quality;
            private readonly int _width;
            private readonly int _height;
            private readonly string _outputDir;
            private readonly string _ext;

            private RenderTexture _renderTexture;
            private RenderTexture _prevCameraTarget;
            private RenderTexture _prevActive;

            private int _frameCount;
            private int _pendingWrites;
            private DateTime _startTime;
            private double _frameInterval;
            private double _lastCaptureTime;
            private readonly List<string> _paths = new();

            public bool IsRecording { get; private set; }

            public RecordingSession(Camera camera, int fps, string format, int quality, int width, int height, string outputDir)
            {
                _camera = camera;
                _targetFps = fps;
                _format = format;
                _quality = quality;
                _width = width;
                _height = height;
                _outputDir = outputDir;
                _ext = format == "jpg" ? ".jpg" : ".png";
                _frameInterval = 1.0 / fps;
            }

            public void Start()
            {
                _frameCount = 0;
                _pendingWrites = 0;
                _startTime = DateTime.UtcNow;
                _lastCaptureTime = 0;
                _paths.Clear();
                IsRecording = true;

                _renderTexture = RenderTexture.GetTemporary(_width, _height, 24, RenderTextureFormat.ARGB32);

                EditorApplication.update += OnUpdate;
                EditorApplication.QueuePlayerLoopUpdate();

                BridgeLog.Info($"[Recorder] Started recording at {_targetFps} FPS ({_width}x{_height}, {_format})");
            }

            public JObject Stop()
            {
                IsRecording = false;
                EditorApplication.update -= OnUpdate;

                // Wait briefly for pending writes
                var waitStart = DateTime.UtcNow;
                while (Interlocked.CompareExchange(ref _pendingWrites, 0, 0) > 0
                       && (DateTime.UtcNow - waitStart).TotalSeconds < 5)
                {
                    Thread.Sleep(10);
                }

                if (_renderTexture != null)
                {
                    RenderTexture.ReleaseTemporary(_renderTexture);
                    _renderTexture = null;
                }

                var elapsed = (DateTime.UtcNow - _startTime).TotalSeconds;
                var fps = elapsed > 0 ? _frameCount / elapsed : 0;

                BridgeLog.Info($"[Recorder] Stopped. {_frameCount} frames in {elapsed:F2}s ({fps:F1} FPS)");

                return new JObject
                {
                    ["message"] = $"Recording stopped: {_frameCount} frames",
                    ["frameCount"] = _frameCount,
                    ["elapsed"] = Math.Round(elapsed, 3),
                    ["fps"] = Math.Round(fps, 1),
                    ["outputDir"] = _outputDir,
                    ["format"] = _format
                };
            }

            public JObject GetStatus()
            {
                var elapsed = (DateTime.UtcNow - _startTime).TotalSeconds;
                var fps = elapsed > 0 ? _frameCount / elapsed : 0;

                return new JObject
                {
                    ["recording"] = true,
                    ["frameCount"] = _frameCount,
                    ["elapsed"] = Math.Round(elapsed, 3),
                    ["fps"] = Math.Round(fps, 1),
                    ["pendingWrites"] = Interlocked.CompareExchange(ref _pendingWrites, 0, 0),
                    ["outputDir"] = _outputDir
                };
            }

            private void OnUpdate()
            {
                if (!IsRecording) return;

                try
                {
                    var elapsed = (DateTime.UtcNow - _startTime).TotalSeconds;

                    // FPS throttle
                    if (elapsed - _lastCaptureTime < _frameInterval)
                        return;

                    _lastCaptureTime = elapsed;

                    // Render to texture
                    var prevTarget = _camera.targetTexture;
                    var prevActive = RenderTexture.active;

                    _camera.targetTexture = _renderTexture;
                    _camera.Render();

                    // Use AsyncGPUReadback when available
                    if (SystemInfo.supportsAsyncGPUReadback)
                    {
                        var frameIndex = _frameCount;
                        _frameCount++;

                        AsyncGPUReadback.Request(_renderTexture, 0, TextureFormat.RGBA32, request =>
                        {
                            if (!IsRecording && frameIndex > _frameCount) return;
                            if (request.hasError)
                            {
                                BridgeLog.Warn($"[Recorder] AsyncGPUReadback failed for frame {frameIndex}");
                                return;
                            }

                            var data = request.GetData<byte>();
                            var texture = new Texture2D(_width, _height, TextureFormat.RGBA32, false);
                            texture.LoadRawTextureData(data);
                            texture.Apply();

                            var bytes = _format == "jpg"
                                ? texture.EncodeToJPG(_quality)
                                : texture.EncodeToPNG();

                            UnityEngine.Object.DestroyImmediate(texture);

                            var framePath = Path.Combine(_outputDir, $"frame_{frameIndex:D6}{_ext}");
                            lock (_paths) { _paths.Add(framePath); }

                            Interlocked.Increment(ref _pendingWrites);
                            ThreadPool.QueueUserWorkItem(_ =>
                            {
                                try
                                {
                                    File.WriteAllBytes(framePath, bytes);
                                }
                                catch (Exception ex)
                                {
                                    BridgeLog.Warn($"[Recorder] Failed to write frame {frameIndex}: {ex.Message}");
                                }
                                finally
                                {
                                    Interlocked.Decrement(ref _pendingWrites);
                                }
                            });
                        });
                    }
                    else
                    {
                        // Fallback: synchronous ReadPixels
                        RenderTexture.active = _renderTexture;
                        var texture = new Texture2D(_width, _height, TextureFormat.RGBA32, false);
                        texture.ReadPixels(new Rect(0, 0, _width, _height), 0, 0);
                        texture.Apply();

                        var bytes = _format == "jpg"
                            ? texture.EncodeToJPG(_quality)
                            : texture.EncodeToPNG();

                        UnityEngine.Object.DestroyImmediate(texture);

                        var framePath = Path.Combine(_outputDir, $"frame_{_frameCount:D6}{_ext}");
                        _paths.Add(framePath);
                        _frameCount++;

                        Interlocked.Increment(ref _pendingWrites);
                        ThreadPool.QueueUserWorkItem(_ =>
                        {
                            try
                            {
                                File.WriteAllBytes(framePath, bytes);
                            }
                            catch (Exception ex)
                            {
                                BridgeLog.Warn($"[Recorder] Failed to write frame: {ex.Message}");
                            }
                            finally
                            {
                                Interlocked.Decrement(ref _pendingWrites);
                            }
                        });
                    }

                    _camera.targetTexture = prevTarget;
                    RenderTexture.active = prevActive;
                }
                catch (Exception ex)
                {
                    BridgeLog.Error($"[Recorder] Frame capture error: {ex.Message}");
                }
            }
        }
    }
}
