using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json.Linq;
using UnityBridge.Helpers;

namespace UnityBridge.Tools
{
    [BridgeTool("api-schema")]
    public static class ApiSchema
    {
        public static JObject HandleCommand(JObject parameters)
        {
            var nsFilter = parameters["namespace"]?.ToObject<string[]>();
            var typeFilter = parameters["type"]?.Value<string>();
            var methodFilter = parameters["method"]?.Value<string>();
            var cacheAll = parameters["cache_all"]?.Value<bool>() ?? false;
            var limit = parameters["limit"]?.Value<int>() ?? 100;
            var offset = parameters["offset"]?.Value<int>() ?? 0;

            var allMethods = CollectMethods(nsFilter, typeFilter, methodFilter);
            var total = allMethods.Count;
            var page = cacheAll ? allMethods : allMethods.Skip(offset).Take(limit).ToList();

            var methodsArray = new JArray();
            foreach (var mi in page)
            {
                var paramsArray = new JArray();
                foreach (var p in mi.GetParameters())
                {
                    paramsArray.Add(new JObject
                    {
                        ["name"] = p.Name,
                        ["type"] = p.ParameterType.Name,
                        ["hasDefault"] = p.HasDefaultValue
                    });
                }

                methodsArray.Add(new JObject
                {
                    ["type"] = mi.DeclaringType?.FullName,
                    ["method"] = mi.Name,
                    ["returnType"] = mi.ReturnType.Name,
                    ["parameters"] = paramsArray
                });
            }

            return new JObject
            {
                ["methods"] = methodsArray,
                ["total"] = total,
                ["hasMore"] = offset + limit < total
            };
        }

        private static List<MethodInfo> CollectMethods(
            string[] nsFilter, string typeFilter, string methodFilter)
        {
            var results = new List<MethodInfo>();

            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type[] types;
                try
                {
                    types = assembly.GetTypes();
                }
                catch (ReflectionTypeLoadException ex)
                {
                    types = ex.Types.Where(t => t != null).ToArray();
                }

                foreach (var type in types)
                {
                    if (!type.IsPublic) continue;
                    if (!ApiSafetyGuard.IsNamespaceAllowed(type)) continue;
                    if (ApiSafetyGuard.IsObsolete(type)) continue;

                    if (nsFilter != null && nsFilter.Length > 0)
                    {
                        var ns = type.Namespace ?? "";
                        if (!nsFilter.Any(f => ns.StartsWith(f, StringComparison.OrdinalIgnoreCase)))
                            continue;
                    }

                    if (!string.IsNullOrEmpty(typeFilter))
                    {
                        if (!type.Name.Equals(typeFilter, StringComparison.OrdinalIgnoreCase)
                            && !(type.FullName?.Equals(typeFilter, StringComparison.OrdinalIgnoreCase) ?? false))
                            continue;
                    }

                    var methods = type.GetMethods(BindingFlags.Public | BindingFlags.Static | BindingFlags.DeclaredOnly);
                    foreach (var mi in methods)
                    {
                        if (ApiSafetyGuard.IsObsolete(mi)) continue;
                        if (!ApiSafetyGuard.HasAllSupportedParams(mi)) continue;
                        if (mi.IsGenericMethod) continue;

                        if (!string.IsNullOrEmpty(methodFilter))
                        {
                            if (!mi.Name.Equals(methodFilter, StringComparison.OrdinalIgnoreCase))
                                continue;
                        }

                        results.Add(mi);
                    }
                }
            }

            return results.OrderBy(m => m.DeclaringType?.FullName).ThenBy(m => m.Name).ToList();
        }
    }
}
