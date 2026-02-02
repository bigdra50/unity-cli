using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.UIElements;
using UnityBridge.Helpers;

namespace UnityBridge.Tools
{
    /// <summary>
    /// Handler for UIToolkit VisualElement tree inspection commands.
    /// Provides dump, query, and inspect operations for UI panels.
    /// </summary>
    [BridgeTool("uitree")]
    public static class UITree
    {
        private static Dictionary<string, WeakReference<VisualElement>> s_RefMap = new();
        private static int s_NextRefId = 1;

        /// <summary>
        /// Dispatches a UITree command described by the provided parameters to the appropriate action handler.
        /// </summary>
        /// <param name="parameters">JSON object containing at minimum an "action" string (case-insensitive). Additional keys depend on the action: 
        /// "dump" (panel, depth, format), "query" (panel, type, name, class_name), "inspect" (ref or panel/name, include_style, include_children),
        /// "click" (ref or panel/name, button, click_count), "scroll" (ref or panel/name, x, y, to_child), and "text" (ref or panel/name).</param>
        /// <returns>Action-specific result as a JSON object (structure varies by action).</returns>
        /// <exception cref="ProtocolException">Thrown when the "action" value is unknown or invalid.</exception>
        public static JObject HandleCommand(JObject parameters)
        {
            var action = parameters["action"]?.Value<string>() ?? "";

            return action.ToLowerInvariant() switch
            {
                "dump" => HandleDump(parameters),
                "query" => HandleQuery(parameters),
                "inspect" => HandleInspect(parameters),
                "click" => HandleClick(parameters),
                "scroll" => HandleScroll(parameters),
                "text" => HandleText(parameters),
                _ => throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    $"Unknown action: {action}. Valid actions: dump, query, inspect, click, scroll, text")
            };
        }

        #region Actions

        private static JObject HandleDump(JObject parameters)
        {
            var panelName = parameters["panel"]?.Value<string>();
            var depth = parameters["depth"]?.Value<int>() ?? -1;
            var format = parameters["format"]?.Value<string>() ?? "text";

            if (string.IsNullOrEmpty(panelName))
            {
                return ListPanels();
            }

            var (root, resolvedPanelName) = FindPanelRoot(panelName);
            if (root == null)
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    $"Panel not found: {panelName}");
            }

            ClearRefs();

            var elementCount = 0;

            try
            {
                if (format.Equals("json", StringComparison.OrdinalIgnoreCase))
                {
                    var tree = BuildJsonTree(root, depth, 0, ref elementCount);
                    return new JObject
                    {
                        ["tree"] = tree,
                        ["elementCount"] = elementCount,
                        ["panel"] = resolvedPanelName
                    };
                }
                else
                {
                    var sb = new StringBuilder();
                    BuildTextTree(root, depth, 0, sb, ref elementCount);
                    return new JObject
                    {
                        ["tree"] = sb.ToString().TrimEnd(),
                        ["elementCount"] = elementCount,
                        ["panel"] = resolvedPanelName
                    };
                }
            }
            catch (Exception ex) when (ex is not ProtocolException)
            {
                throw new ProtocolException(
                    ErrorCode.InternalError,
                    $"Failed to traverse panel '{resolvedPanelName}': {ex.GetType().Name}: {ex.Message}");
            }
        }

        /// <summary>
        /// Query the specified UI panel for VisualElements matching optional type, name, and class filters.
        /// </summary>
        /// <param name="parameters">
        /// A JSON object containing query options:
        /// - "panel" (required): panel name to search.
        /// - "type" (optional): substring filter against element type name (case-insensitive).
        /// - "name" (optional): element name to match; a leading '#' is stripped if present.
        /// - "class_name" (optional): class name to match; a leading '.' is stripped if present.
        /// </param>
        /// <returns>
        /// A JObject with:
        /// - "matches": an array of match objects (each includes ref, type, name, classes, path, layout),
        /// - "count": the number of matches,
        /// - "panel": the resolved panel name.
        /// </returns>
        /// <exception cref="ProtocolException">
        /// Thrown with ErrorCode.InvalidParams if "panel" is missing or the named panel cannot be found.
        /// Other exceptions thrown during traversal are wrapped in a ProtocolException with ErrorCode.InternalError.
        /// </exception>
        private static JObject HandleQuery(JObject parameters)
        {
            var panelName = parameters["panel"]?.Value<string>();
            if (string.IsNullOrEmpty(panelName))
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    "'panel' parameter is required for query action");
            }

            var typeFilter = parameters["type"]?.Value<string>();
            var nameFilter = parameters["name"]?.Value<string>();
            var classFilter = parameters["class_name"]?.Value<string>();

            // Strip leading # from name and . from class_name
            if (nameFilter != null && nameFilter.StartsWith("#"))
                nameFilter = nameFilter.Substring(1);
            if (classFilter != null && classFilter.StartsWith("."))
                classFilter = classFilter.Substring(1);

            var (root, resolvedPanelName) = FindPanelRoot(panelName);
            if (root == null)
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    $"Panel not found: {panelName}");
            }

            ClearRefs();

            try
            {
                var matches = new JArray();
                CollectMatches(root, typeFilter, nameFilter, classFilter, matches, "");

                return new JObject
                {
                    ["matches"] = matches,
                    ["count"] = matches.Count,
                    ["panel"] = resolvedPanelName
                };
            }
            catch (Exception ex) when (ex is not ProtocolException)
            {
                throw new ProtocolException(
                    ErrorCode.InternalError,
                    $"Failed to query panel '{resolvedPanelName}': {ex.GetType().Name}: {ex.Message}");
            }
        }

        /// <summary>
        /// Builds an inspection result for the specified UI element.
        /// </summary>
        /// <param name="parameters">A JSON object that identifies the target element and modifies output. Supported keys:
        /// "ref" — element reference id; or "panel" with optional "name" to locate an element by name within that panel;
        /// "include_style" (bool) — include the element's resolved style when true;
        /// "include_children" (bool) — include basic data for immediate children when true.</param>
        /// <returns>A JObject containing the inspected element's properties (ref, type, name, classes, layout, world bounds, etc.), and optionally a "resolvedStyle" object and a "children" array when requested.</returns>
        private static JObject HandleInspect(JObject parameters)
        {
            var includeStyle = parameters["include_style"]?.Value<bool>() ?? false;
            var includeChildren = parameters["include_children"]?.Value<bool>() ?? false;

            var (target, elementRefId) = ResolveTarget(parameters);
            var result = BuildInspectResult(target, elementRefId, includeStyle, includeChildren);
            return result;
        }

        /// <summary>
        /// Locate a VisualElement based on the provided command parameters and return it with an assigned reference id.
        /// </summary>
        /// <param name="parameters">A JObject containing either a "ref" string or both "panel" and "name" (name may be prefixed with '#').</param>
        /// <returns>A tuple where the first item is the resolved VisualElement and the second item is its assigned reference id string.</returns>
        /// <exception cref="ProtocolException">Thrown when the specified ref does not exist or its element was garbage-collected, when the named panel cannot be found, when the named element is not found in the panel, or when neither a valid "ref" nor "panel" + "name" pair is provided.</exception>
        private static (VisualElement element, string refId) ResolveTarget(JObject parameters)
        {
            var refId = parameters["ref"]?.Value<string>();
            var panelName = parameters["panel"]?.Value<string>();
            var nameFilter = parameters["name"]?.Value<string>();

            VisualElement target = null;

            if (!string.IsNullOrEmpty(refId))
            {
                target = ResolveRef(refId);
                if (target == null)
                {
                    throw new ProtocolException(
                        ErrorCode.InvalidParams,
                        $"ref not found or element has been garbage collected: {refId}");
                }
            }
            else if (!string.IsNullOrEmpty(panelName) && !string.IsNullOrEmpty(nameFilter))
            {
                if (nameFilter.StartsWith("#"))
                    nameFilter = nameFilter.Substring(1);

                var (root, _) = FindPanelRoot(panelName);
                if (root == null)
                {
                    throw new ProtocolException(
                        ErrorCode.InvalidParams,
                        $"Panel not found: {panelName}");
                }

                target = FindElementByName(root, nameFilter);
                if (target == null)
                {
                    throw new ProtocolException(
                        ErrorCode.InvalidParams,
                        $"Element with name '{nameFilter}' not found in panel '{panelName}'");
                }
            }
            else
            {
                throw new ProtocolException(
                    ErrorCode.InvalidParams,
                    "Either 'ref' or 'panel' + 'name' parameters are required");
            }

            var elementRefId = FindOrAssignRef(target);
            return (target, elementRefId);
        }

        /// <summary>
        /// Simulates a mouse click on a resolved VisualElement and returns a summary of the interaction.
        /// </summary>
        /// <param name="parameters">JSON object used to locate the target and configure the click. Expected fields:
        /// "button" (int, optional, default 0) and "click_count" (int, optional, default 1). Target resolution uses the same lookup parameters supported by the command (ref or panel/name).</param>
        /// <returns>JSON object containing "ref" (element reference id), "type" (element type name), "action" ("click"), and "message".</returns>
        /// <exception cref="ProtocolException">Thrown when the target element is disabled or not attached to a panel.</exception>
        private static JObject HandleClick(JObject parameters)
        {
            var (target, refId) = ResolveTarget(parameters);
            var button = parameters["button"]?.Value<int>() ?? 0;
            var clickCount = parameters["click_count"]?.Value<int>() ?? 1;

            if (!target.enabledInHierarchy)
                throw new ProtocolException(ErrorCode.InvalidParams,
                    $"Element is disabled: {refId}");

            if (target.panel == null)
                throw new ProtocolException(ErrorCode.InvalidParams,
                    $"Element not connected to a panel: {refId}");

            var center = target.worldBound.center;

            var down = new Event
            {
                type = EventType.MouseDown,
                mousePosition = center,
                button = button,
                clickCount = clickCount
            };
            using (var pd = PointerDownEvent.GetPooled(down))
            {
                pd.target = target;
                target.panel.visualTree.SendEvent(pd);
            }

            var up = new Event
            {
                type = EventType.MouseUp,
                mousePosition = center,
                button = button,
                clickCount = clickCount
            };
            using (var pu = PointerUpEvent.GetPooled(up))
            {
                pu.target = target;
                target.panel.visualTree.SendEvent(pu);
            }

            return new JObject
            {
                ["ref"] = refId,
                ["type"] = target.GetType().Name,
                ["action"] = "click",
                ["message"] = "Clicked element"
            };
        }

        /// <summary>
        /// Scrolls a ScrollView associated with the resolved target either to a child element or by adjusting its scroll offset.
        /// </summary>
        /// <param name="parameters">
        /// JSON object containing target resolution keys (e.g. "ref" or panel/name identifiers) and one of:
        /// - "to_child": string ref of a child element to scroll to, or
        /// - "x" and/or "y": numeric offset values to set on the ScrollView's scrollOffset.
        /// </param>
        /// <returns>
        /// A JObject describing the resulting ScrollView state: contains "ref", "type" ("ScrollView"), "action" ("scroll"),
        /// "scrollOffset" (object with "x" and "y"), and "message".
        /// </returns>
        /// <exception cref="ProtocolException">
        /// Thrown if no ScrollView is found at or above the target, if the provided "to_child" ref does not resolve,
        /// or if neither "to_child" nor at least one of "x"/"y" is provided.
        /// </exception>
        private static JObject HandleScroll(JObject parameters)
        {
            var (target, refId) = ResolveTarget(parameters);
            var scrollView = FindScrollView(target);

            if (scrollView == null)
                throw new ProtocolException(ErrorCode.InvalidParams,
                    $"No ScrollView found at or above element: {refId}");

            var toChild = parameters["to_child"]?.Value<string>();
            if (!string.IsNullOrEmpty(toChild))
            {
                var child = ResolveRef(toChild);
                if (child == null)
                    throw new ProtocolException(ErrorCode.InvalidParams,
                        $"to_child ref not found: {toChild}");

                scrollView.ScrollTo(child);
            }
            else
            {
                var offset = scrollView.scrollOffset;
                var x = parameters["x"];
                var y = parameters["y"];

                if (x == null && y == null)
                    throw new ProtocolException(ErrorCode.InvalidParams,
                        "Either 'x'/'y' or 'to_child' parameter is required for scroll");

                if (x != null) offset.x = x.Value<float>();
                if (y != null) offset.y = y.Value<float>();
                scrollView.scrollOffset = offset;
            }

            var svRefId = FindOrAssignRef(scrollView);
            var finalOffset = scrollView.scrollOffset;
            return new JObject
            {
                ["ref"] = svRefId,
                ["type"] = "ScrollView",
                ["action"] = "scroll",
                ["scrollOffset"] = new JObject
                {
                    ["x"] = finalOffset.x,
                    ["y"] = finalOffset.y
                },
                ["message"] = "Scrolled element"
            };
        }

        /// <summary>
        /// Extracts textual content from a resolved UI element.
        /// </summary>
        /// <param name="parameters">A JSON object specifying the target element (may contain a `ref` or panel/name selection used by ResolveTarget).</param>
        /// <returns>A JObject containing `ref`, `type`, `action` (set to "text"), and `text` with the element's textual content.</returns>
        /// <exception cref="ProtocolException">Thrown when the resolved element has no text content.</exception>
        private static JObject HandleText(JObject parameters)
        {
            var (target, refId) = ResolveTarget(parameters);

            string text = null;

            if (target is TextElement textElement)
            {
                text = textElement.text;
            }
            else if (target is BaseField<string> stringField)
            {
                text = stringField.value;
            }
            else
            {
                var childText = target.Q<TextElement>();
                if (childText != null)
                    text = childText.text;
            }

            if (text == null)
                throw new ProtocolException(ErrorCode.InvalidParams,
                    $"Element has no text content: {refId} ({target.GetType().Name})");

            return new JObject
            {
                ["ref"] = refId,
                ["type"] = target.GetType().Name,
                ["action"] = "text",
                ["text"] = text
            };
        }

        #endregion

        #region Panel Discovery

        private static JObject ListPanels()
        {
            var panels = new JArray();

            // Editor panels via reflection
            foreach (var info in GetEditorPanels())
            {
                panels.Add(new JObject
                {
                    ["name"] = info.Name,
                    ["contextType"] = info.ContextType,
                    ["elementCount"] = info.ElementCount
                });
            }

            // Runtime panels via UIDocument
            foreach (var info in GetRuntimePanels())
            {
                panels.Add(new JObject
                {
                    ["name"] = info.Name,
                    ["contextType"] = info.ContextType,
                    ["elementCount"] = info.ElementCount
                });
            }

            return new JObject
            {
                ["panels"] = panels
            };
        }

        private static (VisualElement root, string panelName) FindPanelRoot(string panelName)
        {
            // Search editor panels
            foreach (var info in GetEditorPanels())
            {
                if (info.Name.Equals(panelName, StringComparison.OrdinalIgnoreCase))
                    return (info.Root, info.Name);
            }

            // Search runtime panels
            foreach (var info in GetRuntimePanels())
            {
                if (info.Name.Equals(panelName, StringComparison.OrdinalIgnoreCase))
                    return (info.Root, info.Name);
            }

            // Partial match fallback
            foreach (var info in GetEditorPanels())
            {
                if (info.Name.IndexOf(panelName, StringComparison.OrdinalIgnoreCase) >= 0)
                    return (info.Root, info.Name);
            }

            foreach (var info in GetRuntimePanels())
            {
                if (info.Name.IndexOf(panelName, StringComparison.OrdinalIgnoreCase) >= 0)
                    return (info.Root, info.Name);
            }

            return (null, null);
        }

        private struct PanelInfo
        {
            public string Name;
            public string ContextType;
            public int ElementCount;
            public VisualElement Root;
        }

        private static List<PanelInfo> GetEditorPanels()
        {
            var results = new List<PanelInfo>();

            // UIElementsUtility.GetPanelsIterator() is internal, use reflection
            var utilityType = Type.GetType(
                "UnityEngine.UIElements.UIElementsUtility, UnityEngine.UIElementsModule");
            if (utilityType == null)
            {
                BridgeLog.Verbose("UIElementsUtility type not found");
                return results;
            }

            var getIteratorMethod = utilityType.GetMethod(
                "GetPanelsIterator",
                BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
            if (getIteratorMethod == null)
            {
                BridgeLog.Verbose("GetPanelsIterator method not found");
                return results;
            }

            object iterator;
            try
            {
                iterator = getIteratorMethod.Invoke(null, null);
            }
            catch (Exception ex)
            {
                BridgeLog.Error($"Failed to get panels iterator: {ex.Message}");
                return results;
            }

            // The iterator is Dictionary<int, Panel>.Enumerator (a struct).
            // Wrap it in IEnumerator to avoid struct boxing issues with repeated MoveNext.
            var iteratorType = iterator.GetType();
            var moveNextMethod = iteratorType.GetMethod("MoveNext");
            var currentProp = iteratorType.GetProperty("Current");
            var disposeMethod = iteratorType.GetMethod("Dispose");

            if (moveNextMethod == null || currentProp == null)
                return results;

            try
            {
                // Use TypedReference / pointer trick not available, so collect all at once
                // by repeatedly calling MoveNext on the boxed struct via interface
                if (iterator is System.Collections.IEnumerator enumerator)
                {
                    while (enumerator.MoveNext())
                    {
                        ProcessPanelEntry(enumerator.Current, results);
                    }
                }
                else
                {
                    // Fallback: use a wrapper that handles the struct enumerator properly
                    // Box once and invoke via reflection on the same boxed reference
                    while ((bool)moveNextMethod.Invoke(iterator, null))
                    {
                        var kvp = currentProp.GetValue(iterator);
                        ProcessPanelEntry(kvp, results);
                    }
                }
            }
            finally
            {
                disposeMethod?.Invoke(iterator, null);
            }

            return results;
        }

        private static void ProcessPanelEntry(object kvp, List<PanelInfo> results)
        {
            if (kvp == null) return;

            var kvpType = kvp.GetType();
            var valueProp = kvpType.GetProperty("Value");
            var panel = valueProp?.GetValue(kvp);

            if (panel == null) return;

            var panelType = panel.GetType();

            // Get contextType
            var contextTypeProp = panelType.GetProperty("contextType",
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            var contextType = contextTypeProp?.GetValue(panel)?.ToString() ?? "Unknown";

            // Get visualTree
            var visualTreeProp = panelType.GetProperty("visualTree",
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            var visualTree = visualTreeProp?.GetValue(panel) as VisualElement;

            if (visualTree == null) return;

            // Derive panel name from ownerObject or type
            var ownerObjectProp = panelType.GetProperty("ownerObject",
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            var ownerObject = ownerObjectProp?.GetValue(panel) as ScriptableObject;

            var panelName = ownerObject != null
                ? ownerObject.GetType().Name
                : $"Panel_{contextType}";

            var elementCount = CountElements(visualTree);

            results.Add(new PanelInfo
            {
                Name = panelName,
                ContextType = contextType,
                ElementCount = elementCount,
                Root = visualTree
            });
        }

        private static List<PanelInfo> GetRuntimePanels()
        {
            var results = new List<PanelInfo>();

            var uiDocuments = UnityEngine.Object.FindObjectsByType<UIDocument>(FindObjectsSortMode.None);

            foreach (var doc in uiDocuments)
            {
                if (doc == null || doc.rootVisualElement == null)
                    continue;

                var panelSettingsName = doc.panelSettings != null
                    ? doc.panelSettings.name
                    : "Unknown";
                var panelName = $"UIDocument {panelSettingsName} ({doc.gameObject.name})";
                var elementCount = CountElements(doc.rootVisualElement);

                results.Add(new PanelInfo
                {
                    Name = panelName,
                    ContextType = "Player",
                    ElementCount = elementCount,
                    Root = doc.rootVisualElement
                });
            }

            return results;
        }

        #endregion

        #region Tree Building

        private static void BuildTextTree(
            VisualElement element, int maxDepth, int currentDepth,
            StringBuilder sb, ref int elementCount)
        {
            if (maxDepth >= 0 && currentDepth > maxDepth)
                return;

            var indent = new string(' ', currentDepth * 2);
            var refId = AssignRef(element);
            elementCount++;

            sb.Append(indent);
            sb.Append(element.GetType().Name);

            if (!string.IsNullOrEmpty(element.name))
            {
                sb.Append($" \"{element.name}\"");
            }

            foreach (var cls in element.GetClasses())
            {
                sb.Append($" .{cls}");
            }

            sb.AppendLine($" {refId}");

            foreach (var child in element.Children())
            {
                BuildTextTree(child, maxDepth, currentDepth + 1, sb, ref elementCount);
            }
        }

        private static JObject BuildJsonTree(
            VisualElement element, int maxDepth, int currentDepth,
            ref int elementCount)
        {
            var refId = AssignRef(element);
            elementCount++;

            var node = new JObject
            {
                ["ref"] = refId,
                ["type"] = element.GetType().Name,
                ["name"] = string.IsNullOrEmpty(element.name) ? null : element.name,
                ["classes"] = new JArray(element.GetClasses().ToArray()),
                ["childCount"] = element.childCount
            };

            if (maxDepth >= 0 && currentDepth >= maxDepth)
            {
                // Don't recurse further, but still report childCount
                return node;
            }

            if (element.childCount > 0)
            {
                var children = new JArray();
                foreach (var child in element.Children())
                {
                    children.Add(BuildJsonTree(child, maxDepth, currentDepth + 1, ref elementCount));
                }
                node["children"] = children;
            }

            return node;
        }

        #endregion

        #region Query

        private static void CollectMatches(
            VisualElement element, string typeFilter, string nameFilter,
            string classFilter, JArray matches, string parentPath)
        {
            var typeName = element.GetType().Name;
            var currentPath = string.IsNullOrEmpty(parentPath)
                ? typeName
                : $"{parentPath} > {typeName}";

            var matchesType = string.IsNullOrEmpty(typeFilter) ||
                              typeName.IndexOf(typeFilter, StringComparison.OrdinalIgnoreCase) >= 0;
            var matchesName = string.IsNullOrEmpty(nameFilter) ||
                              (!string.IsNullOrEmpty(element.name) &&
                               element.name.Equals(nameFilter, StringComparison.OrdinalIgnoreCase));
            var matchesClass = string.IsNullOrEmpty(classFilter) ||
                               element.GetClasses().Any(c =>
                                   c.Equals(classFilter, StringComparison.OrdinalIgnoreCase));

            if (matchesType && matchesName && matchesClass)
            {
                // At least one filter must be specified
                if (!string.IsNullOrEmpty(typeFilter) ||
                    !string.IsNullOrEmpty(nameFilter) ||
                    !string.IsNullOrEmpty(classFilter))
                {
                    var refId = AssignRef(element);
                    var layout = element.layout;
                    matches.Add(new JObject
                    {
                        ["ref"] = refId,
                        ["type"] = typeName,
                        ["name"] = string.IsNullOrEmpty(element.name) ? null : element.name,
                        ["classes"] = new JArray(element.GetClasses().ToArray()),
                        ["path"] = currentPath,
                        ["layout"] = new JObject
                        {
                            ["x"] = layout.x,
                            ["y"] = layout.y,
                            ["width"] = layout.width,
                            ["height"] = layout.height
                        }
                    });
                }
            }

            foreach (var child in element.Children())
            {
                CollectMatches(child, typeFilter, nameFilter, classFilter, matches, currentPath);
            }
        }

        #endregion

        #region Inspect

        private static JObject BuildInspectResult(
            VisualElement element, string refId,
            bool includeStyle, bool includeChildren)
        {
            var layout = element.layout;
            var worldBound = element.worldBound;

            var result = new JObject
            {
                ["ref"] = refId,
                ["type"] = element.GetType().Name,
                ["name"] = string.IsNullOrEmpty(element.name) ? null : element.name,
                ["classes"] = new JArray(element.GetClasses().ToArray()),
                ["visible"] = element.visible,
                ["enabledSelf"] = element.enabledSelf,
                ["enabledInHierarchy"] = element.enabledInHierarchy,
                ["focusable"] = element.focusable,
                ["tooltip"] = element.tooltip ?? "",
                ["path"] = BuildElementPath(element),
                ["layout"] = new JObject
                {
                    ["x"] = layout.x,
                    ["y"] = layout.y,
                    ["width"] = layout.width,
                    ["height"] = layout.height
                },
                ["worldBound"] = new JObject
                {
                    ["x"] = worldBound.x,
                    ["y"] = worldBound.y,
                    ["width"] = worldBound.width,
                    ["height"] = worldBound.height
                },
                ["childCount"] = element.childCount
            };

            if (includeChildren)
            {
                var children = new JArray();
                foreach (var child in element.Children())
                {
                    var childRefId = FindOrAssignRef(child);
                    children.Add(new JObject
                    {
                        ["ref"] = childRefId,
                        ["type"] = child.GetType().Name,
                        ["name"] = string.IsNullOrEmpty(child.name) ? null : child.name,
                        ["classes"] = new JArray(child.GetClasses().ToArray())
                    });
                }
                result["children"] = children;
            }

            if (includeStyle)
            {
                result["resolvedStyle"] = BuildResolvedStyle(element);
            }

            return result;
        }

        private static JObject BuildResolvedStyle(VisualElement element)
        {
            var style = element.resolvedStyle;
            return new JObject
            {
                ["width"] = style.width,
                ["height"] = style.height,
                ["backgroundColor"] = style.backgroundColor.ToString(),
                ["color"] = style.color.ToString(),
                ["fontSize"] = style.fontSize,
                ["display"] = style.display.ToString(),
                ["position"] = style.position.ToString(),
                ["flexDirection"] = style.flexDirection.ToString(),
                ["opacity"] = style.opacity,
                ["visibility"] = style.visibility.ToString(),
                ["marginTop"] = style.marginTop,
                ["marginBottom"] = style.marginBottom,
                ["marginLeft"] = style.marginLeft,
                ["marginRight"] = style.marginRight,
                ["paddingTop"] = style.paddingTop,
                ["paddingBottom"] = style.paddingBottom,
                ["paddingLeft"] = style.paddingLeft,
                ["paddingRight"] = style.paddingRight,
                ["borderTopWidth"] = style.borderTopWidth,
                ["borderBottomWidth"] = style.borderBottomWidth,
                ["borderLeftWidth"] = style.borderLeftWidth,
                ["borderRightWidth"] = style.borderRightWidth
            };
        }

        private static string BuildElementPath(VisualElement element)
        {
            var parts = new List<string>();
            var current = element;

            while (current != null)
            {
                parts.Add(current.GetType().Name);
                current = current.parent;
            }

            parts.Reverse();
            return string.Join(" > ", parts);
        }

        #endregion

        #region Ref ID Management

        private static string AssignRef(VisualElement ve)
        {
            var refId = $"ref_{s_NextRefId++}";
            s_RefMap[refId] = new WeakReference<VisualElement>(ve);
            return refId;
        }

        private static string FindOrAssignRef(VisualElement ve)
        {
            // Check if this element already has a ref
            foreach (var kvp in s_RefMap)
            {
                if (kvp.Value.TryGetTarget(out var existing) && existing == ve)
                    return kvp.Key;
            }

            return AssignRef(ve);
        }

        private static VisualElement ResolveRef(string refId)
        {
            if (s_RefMap.TryGetValue(refId, out var weakRef) && weakRef.TryGetTarget(out var element))
                return element;

            return null;
        }

        private static void ClearRefs()
        {
            s_RefMap.Clear();
            s_NextRefId = 1;
        }

        #endregion

        #region Helpers

        /// <summary>
        /// Finds the nearest ScrollView in the visual tree starting at the specified element and walking up through its ancestors.
        /// </summary>
        /// <param name="element">The element to start the search from.</param>
        /// <returns>The nearest ScrollView that is the element or one of its ancestors, or <c>null</c> if none is found.</returns>
        private static ScrollView FindScrollView(VisualElement element)
        {
            var current = element;
            while (current != null)
            {
                if (current is ScrollView sv) return sv;
                current = current.parent;
            }
            return null;
        }

        /// <summary>
        /// Finds the first VisualElement with the specified name in the subtree rooted at <paramref name="root"/>.
        /// </summary>
        /// <param name="root">The root VisualElement to begin the search from.</param>
        /// <param name="name">The element name to match (case-insensitive).</param>
        /// <returns>The first matching VisualElement, or null if no match is found.</returns>
        private static VisualElement FindElementByName(VisualElement root, string name)
        {
            if (!string.IsNullOrEmpty(root.name) &&
                root.name.Equals(name, StringComparison.OrdinalIgnoreCase))
                return root;

            foreach (var child in root.Children())
            {
                var found = FindElementByName(child, name);
                if (found != null)
                    return found;
            }

            return null;
        }

        private static int CountElements(VisualElement root)
        {
            var count = 1;
            foreach (var child in root.Children())
            {
                count += CountElements(child);
            }
            return count;
        }

        #endregion
    }
}