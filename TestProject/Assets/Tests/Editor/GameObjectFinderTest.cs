using System.Collections.Generic;
using NUnit.Framework;
using UnityBridge.Helpers;
using UnityEngine;

namespace UnityBridge
{
    /// <summary>
    /// GameObjectFinder の統合テスト。
    /// Asset.cs と Component.cs で重複していた FindGameObject を共通化した後の挙動を検証する。
    ///
    /// 統合により以下の差異が解消された:
    /// - Asset.cs: GameObject.Find のみ（非アクティブ非対応、PrefabStage非対応）
    /// - Component.cs: シーン全検索（非アクティブ対応、PrefabStage対応）
    /// → 共通化後は Component.cs 相当の堅牢な実装に統一
    /// </summary>
    [TestFixture]
    public class GameObjectFinderTest
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

        /// <summary>
        /// 名前でアクティブな GameObject を見つけられること。
        /// </summary>
        [Test]
        public void Find_ByName_ActiveObject_ReturnsGameObject()
        {
            var expected = CreateGameObject("FinderTest_Active");

            var actual = GameObjectFinder.Find("FinderTest_Active", null);

            Assert.That(actual, Is.EqualTo(expected));
        }

        /// <summary>
        /// 名前で非アクティブな GameObject を見つけられること。
        /// (旧 Asset.cs の実装では見つけられなかった)
        /// </summary>
        [Test]
        public void Find_ByName_InactiveObject_ReturnsGameObject()
        {
            var expected = CreateGameObject("FinderTest_Inactive");
            expected.SetActive(false);

            var actual = GameObjectFinder.Find("FinderTest_Inactive", null);

            Assert.That(actual, Is.EqualTo(expected));
        }

        /// <summary>
        /// 名前で子オブジェクトを見つけられること。
        /// </summary>
        [Test]
        public void Find_ByName_ChildObject_ReturnsGameObject()
        {
            var parent = CreateGameObject("FinderTest_Parent");
            var expected = CreateGameObject("FinderTest_Child");
            expected.transform.SetParent(parent.transform);

            var actual = GameObjectFinder.Find("FinderTest_Child", null);

            Assert.That(actual, Is.EqualTo(expected));
        }

        /// <summary>
        /// instanceID で GameObject を見つけられること。
        /// </summary>
        [Test]
        public void Find_ByInstanceId_ReturnsGameObject()
        {
            var expected = CreateGameObject("FinderTest_ById");

            var actual = GameObjectFinder.Find(null, expected.GetInstanceID());

            Assert.That(actual, Is.EqualTo(expected));
        }

        /// <summary>
        /// instanceID が Component を指す場合、その gameObject を返すこと。
        /// (旧 Asset.cs の実装ではこのケースに対応していなかった)
        /// </summary>
        [Test]
        public void Find_ByInstanceId_ComponentId_ReturnsGameObject()
        {
            var expected = CreateGameObject("FinderTest_CompId");
            var transform = expected.transform;

            var actual = GameObjectFinder.Find(null, transform.GetInstanceID());

            Assert.That(actual, Is.EqualTo(expected));
        }

        /// <summary>
        /// 存在しない名前で null を返すこと。
        /// </summary>
        [Test]
        public void Find_NonExistentName_ReturnsNull()
        {
            var actual = GameObjectFinder.Find("NonExistent_GO_12345", null);

            Assert.That(actual, Is.Null);
        }

        /// <summary>
        /// 存在しない instanceID で null を返すこと。
        /// </summary>
        [Test]
        public void Find_NonExistentInstanceId_ReturnsNull()
        {
            var actual = GameObjectFinder.Find(null, -99999);

            Assert.That(actual, Is.Null);
        }

        /// <summary>
        /// name も instanceId も指定しない場合 null を返すこと。
        /// </summary>
        [Test]
        public void Find_NoParameters_ReturnsNull()
        {
            var actual = GameObjectFinder.Find(null, null);

            Assert.That(actual, Is.Null);
        }

        /// <summary>
        /// instanceId が優先されること（name も指定されている場合）。
        /// </summary>
        [Test]
        public void Find_BothNameAndId_InstanceIdTakesPriority()
        {
            var expected = CreateGameObject("FinderTest_Priority");

            var actual = GameObjectFinder.Find("SomeOtherName", expected.GetInstanceID());

            Assert.That(actual, Is.EqualTo(expected));
        }

        private GameObject CreateGameObject(string name)
        {
            var go = new GameObject(name);
            _createdObjects.Add(go);
            return go;
        }
    }
}
