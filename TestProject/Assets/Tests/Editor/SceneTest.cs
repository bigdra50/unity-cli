using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace UnityBridge.Tools
{
    [TestFixture]
    public class SceneTest
    {
        private readonly List<GameObject> _createdObjects = new();

        [TearDown]
        public void TearDown()
        {
            foreach (var obj in _createdObjects)
            {
                if (obj != null)
                    Object.DestroyImmediate(obj);
            }

            _createdObjects.Clear();
        }

        [Test]
        public void HandleCommand_Hierarchy_ItemsCountDoesNotExceedPageSize()
        {
            var roots = CreateHierarchy(rootCount: 3, childrenPerRoot: 2);
            var pageSize = 3;

            var actual = Scene.HandleCommand(new JObject
            {
                ["action"] = "hierarchy",
                ["depth"] = 2,
                ["page_size"] = pageSize,
                ["cursor"] = CursorForRoots(roots)
            });

            var items = (JArray)actual["items"];
            Assert.That(items.Count, Is.LessThanOrEqualTo(pageSize));
        }

        [Test]
        public void HandleCommand_Hierarchy_ItemsCountDoesNotExceedPageSize_DeepHierarchy()
        {
            var roots = CreateDeepHierarchy(rootCount: 3, depth: 3, childrenPerLevel: 2);
            var pageSize = 5;

            var actual = Scene.HandleCommand(new JObject
            {
                ["action"] = "hierarchy",
                ["depth"] = 3,
                ["page_size"] = pageSize,
                ["cursor"] = CursorForRoots(roots)
            });

            var items = (JArray)actual["items"];
            Assert.That(items.Count, Is.LessThanOrEqualTo(pageSize));
        }

        [Test]
        public void HandleCommand_Hierarchy_PaginationTraversesAllRoots()
        {
            var roots = CreateHierarchy(rootCount: 5, childrenPerRoot: 1);
            var pageSize = 2;
            var startCursor = CursorForRoots(roots);
            var cursor = startCursor;
            var totalCollected = 0;
            var iterations = 0;

            while (cursor != -1 && iterations < 100)
            {
                var result = Scene.HandleCommand(new JObject
                {
                    ["action"] = "hierarchy",
                    ["depth"] = 0,
                    ["page_size"] = pageSize,
                    ["cursor"] = cursor
                });

                var items = (JArray)result["items"];
                totalCollected += items.Count;

                var hasMore = result["hasMore"].Value<bool>();
                cursor = hasMore ? result["nextCursor"].Value<int>() : -1;
                iterations++;
            }

            Assert.That(totalCollected, Is.EqualTo(roots.Count));
        }

        [TestCase(1)]
        [TestCase(2)]
        [TestCase(3)]
        [TestCase(4)]
        [TestCase(7)]
        public void HandleCommand_Hierarchy_ItemsNeverExceedPageSize_VariousSizes(int pageSize)
        {
            var roots = CreateDeepHierarchy(rootCount: 4, depth: 2, childrenPerLevel: 3);

            var actual = Scene.HandleCommand(new JObject
            {
                ["action"] = "hierarchy",
                ["depth"] = 2,
                ["page_size"] = pageSize,
                ["cursor"] = CursorForRoots(roots)
            });

            var items = (JArray)actual["items"];
            Assert.That(items.Count, Is.LessThanOrEqualTo(pageSize));
        }

        private List<GameObject> CreateHierarchy(int rootCount, int childrenPerRoot)
        {
            var roots = new List<GameObject>();

            for (var i = 0; i < rootCount; i++)
            {
                var root = new GameObject($"TestRoot_{i}");
                _createdObjects.Add(root);
                roots.Add(root);

                for (var j = 0; j < childrenPerRoot; j++)
                {
                    var child = new GameObject($"TestChild_{i}_{j}");
                    child.transform.SetParent(root.transform);
                    _createdObjects.Add(child);
                }
            }

            return roots;
        }

        private List<GameObject> CreateDeepHierarchy(int rootCount, int depth, int childrenPerLevel)
        {
            var roots = new List<GameObject>();

            for (var i = 0; i < rootCount; i++)
            {
                var root = new GameObject($"TestRoot_{i}");
                _createdObjects.Add(root);
                roots.Add(root);
                CreateChildrenRecursive(root.transform, depth - 1, childrenPerLevel, $"{i}");
            }

            return roots;
        }

        private void CreateChildrenRecursive(Transform parent, int remainingDepth, int childrenCount, string prefix)
        {
            if (remainingDepth <= 0) return;

            for (var i = 0; i < childrenCount; i++)
            {
                var childName = $"TestChild_{prefix}_{i}";
                var child = new GameObject(childName);
                child.transform.SetParent(parent);
                _createdObjects.Add(child);
                CreateChildrenRecursive(child.transform, remainingDepth - 1, childrenCount, $"{prefix}_{i}");
            }
        }

        private static int CursorForRoots(List<GameObject> roots)
        {
            var scene = SceneManager.GetActiveScene();
            var allRoots = scene.GetRootGameObjects();

            for (var i = 0; i < allRoots.Length; i++)
            {
                if (allRoots[i] == roots[0])
                    return i;
            }

            return 0;
        }
    }
}
