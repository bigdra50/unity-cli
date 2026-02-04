using System;
using System.IO;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace UnityBridge.Tools
{
    /// <summary>
    /// Handler for screenshot commands.
    /// Captures screenshots from SceneView or GameView.
    /// </summary>
    [BridgeTool("screenshot")]
    public static class Screenshot
    {
        private static readonly Type GameViewType = Type.GetType("UnityEditor.GameView,UnityEditor");

        public static Task<JObject> HandleCommand(JObject parameters)
        {
            var action = parameters["action"]?.Value<string>() ?? "capture";

            return action.ToLowerInvariant() switch
            {
                "capture" => Capture(parameters),
                _ => throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    $"Unknown action: {action}. Valid actions: capture")
            };
        }

        private static Task<JObject> Capture(JObject parameters)
        {
            var source = parameters["source"]?.Value<string>() ?? "game";
            var path = parameters["path"]?.Value<string>();
            var superSize = parameters["superSize"]?.Value<int>() ?? 1;

            if (string.IsNullOrEmpty(path))
            {
                var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                var projectPath = Directory.GetCurrentDirectory();
                path = Path.Combine(projectPath, $"Screenshots/screenshot_{timestamp}.png");
            }

            var directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }

            return source.ToLowerInvariant() switch
            {
                "game" => CaptureGameViewAsync(path, superSize),
                "scene" => Task.FromResult(CaptureSceneView(path)),
                "camera" => Task.FromResult(CaptureCamera(parameters)),
                _ => throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    $"Unknown source: {source}. Valid sources: game, scene, camera")
            };
        }

        private static Task<JObject> CaptureGameViewAsync(string path, int superSize)
        {
            if (!EditorApplication.isPlaying)
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    "GameView screenshot requires Play Mode. Enter play mode first with action 'enter'.");
            }

            superSize = Mathf.Clamp(superSize, 1, 4);

            if (GameViewType == null)
            {
                throw new ProtocolException(
                    ErrorCode.InternalError,
                    "GameView type not found via reflection");
            }

            var gameView = EditorWindow.GetWindow(GameViewType, false, null, true);
            if (gameView == null)
            {
                throw new ProtocolException(
                    ErrorCode.InternalError,
                    "Failed to get GameView window");
            }

            gameView.Focus();
            gameView.Repaint();

            var tcs = new TaskCompletionSource<JObject>(TaskCreationOptions.RunContinuationsAsynchronously);
            var framesToWait = 2;
            var captured = false;
            var startTime = DateTime.UtcNow;
            const int timeoutSeconds = 10;

            void OnUpdate()
            {
                try
                {
                    if ((DateTime.UtcNow - startTime).TotalSeconds > timeoutSeconds)
                    {
                        EditorApplication.update -= OnUpdate;
                        tcs.TrySetException(new ProtocolException(
                            ErrorCode.InternalError,
                            "GameView screenshot capture timed out"));
                        return;
                    }

                    // Wait frames for GameView to render after Focus + Repaint
                    if (framesToWait > 0)
                    {
                        framesToWait--;
                        return;
                    }

                    // Trigger capture once
                    if (!captured)
                    {
                        ScreenCapture.CaptureScreenshot(path, superSize);
                        captured = true;
                        return;
                    }

                    // Poll for file save completion
                    if (File.Exists(path) && new FileInfo(path).Length > 0)
                    {
                        EditorApplication.update -= OnUpdate;
                        tcs.TrySetResult(new JObject
                        {
                            ["message"] = "GameView screenshot captured",
                            ["path"] = path,
                            ["source"] = "game",
                            ["superSize"] = superSize
                        });
                    }
                }
                catch (Exception ex)
                {
                    EditorApplication.update -= OnUpdate;
                    tcs.TrySetException(ex is ProtocolException ? ex :
                        new ProtocolException(ErrorCode.InternalError,
                            $"GameView screenshot failed: {ex.Message}"));
                }
            }

            EditorApplication.update += OnUpdate;
            EditorApplication.QueuePlayerLoopUpdate();

            return tcs.Task;
        }

        private static JObject CaptureCamera(JObject parameters)
        {
            var path = parameters["path"]?.Value<string>();
            var width = parameters["width"]?.Value<int>() ?? 1920;
            var height = parameters["height"]?.Value<int>() ?? 1080;
            var cameraName = parameters["camera"]?.Value<string>();

            if (string.IsNullOrEmpty(path))
            {
                var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                var projectPath = Directory.GetCurrentDirectory();
                path = Path.Combine(projectPath, $"Screenshots/camera_{timestamp}.png");
            }

            var directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }

            Camera camera = null;
            if (!string.IsNullOrEmpty(cameraName))
            {
                var cameraGo = GameObject.Find(cameraName);
                if (cameraGo != null)
                {
                    camera = cameraGo.GetComponent<Camera>();
                }
            }

            if (camera == null)
            {
                camera = Camera.main;
            }

            if (camera == null)
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    "No camera found. Specify camera name or ensure a Main Camera exists.");
            }

            width = Mathf.Max(1, width);
            height = Mathf.Max(1, height);

            var prevTarget = camera.targetTexture;
            var prevActive = RenderTexture.active;
            var renderTexture = RenderTexture.GetTemporary(width, height, 24, RenderTextureFormat.ARGB32);

            try
            {
                camera.targetTexture = renderTexture;
                camera.Render();

                RenderTexture.active = renderTexture;
                var texture = new Texture2D(width, height, TextureFormat.RGBA32, false);
                texture.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                texture.Apply();

                var bytes = texture.EncodeToPNG();
                File.WriteAllBytes(path, bytes);

                UnityEngine.Object.DestroyImmediate(texture);

                return new JObject
                {
                    ["message"] = "Camera screenshot captured",
                    ["path"] = path,
                    ["source"] = "camera",
                    ["width"] = width,
                    ["height"] = height,
                    ["camera"] = camera.name
                };
            }
            finally
            {
                camera.targetTexture = prevTarget;
                RenderTexture.active = prevActive;
                RenderTexture.ReleaseTemporary(renderTexture);
            }
        }

        private static JObject CaptureSceneView(string path)
        {
            var sceneView = SceneView.lastActiveSceneView;

            if (sceneView == null)
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    "No active SceneView found");
            }

            var camera = sceneView.camera;
            var width = (int)sceneView.position.width;
            var height = (int)sceneView.position.height;

            var renderTexture = new RenderTexture(width, height, 24);
            var previousTarget = camera.targetTexture;

            try
            {
                camera.targetTexture = renderTexture;
                camera.Render();

                var texture = new Texture2D(width, height, TextureFormat.RGB24, false);
                RenderTexture.active = renderTexture;
                texture.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                texture.Apply();

                var bytes = texture.EncodeToPNG();
                File.WriteAllBytes(path, bytes);

                UnityEngine.Object.DestroyImmediate(texture);

                return new JObject
                {
                    ["message"] = "SceneView screenshot captured",
                    ["path"] = path,
                    ["source"] = "scene",
                    ["width"] = width,
                    ["height"] = height
                };
            }
            finally
            {
                camera.targetTexture = previousTarget;
                RenderTexture.active = null;
                UnityEngine.Object.DestroyImmediate(renderTexture);
            }
        }
    }
}
