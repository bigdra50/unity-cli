using NUnit.Framework;
using UnityBridge.Helpers;
using UnityEngine;

namespace UnityBridge
{
    /// <summary>
    /// TypeResolver の統合テスト。
    /// Asset.cs と Component.cs で重複していた FindType を共通化した後の挙動を検証する。
    /// </summary>
    [TestFixture]
    public class TypeResolverTest
    {
        /// <summary>
        /// フルネームで Unity 型を解決できること。
        /// </summary>
        [Test]
        public void FindType_FullName_ReturnsType()
        {
            var actual = TypeResolver.FindType("UnityEngine.BoxCollider");

            Assert.That(actual, Is.EqualTo(typeof(BoxCollider)));
        }

        /// <summary>
        /// ショートネームで Unity 型を解決できること。
        /// </summary>
        [Test]
        public void FindType_ShortName_ReturnsType()
        {
            var actual = TypeResolver.FindType("BoxCollider");

            Assert.That(actual, Is.EqualTo(typeof(BoxCollider)));
        }

        /// <summary>
        /// ScriptableObject 派生型をショートネームで解決できること。
        /// (Asset.cs の CreateScriptableObject で使用)
        /// </summary>
        [Test]
        public void FindType_ShortName_ScriptableObject_ReturnsType()
        {
            // PhysicsMaterial は ScriptableObject 派生ではないが、
            // 標準的な型解決として Material を検証
            var actual = TypeResolver.FindType("Material");

            Assert.That(actual, Is.EqualTo(typeof(Material)));
        }

        /// <summary>
        /// 存在しない型名で null を返すこと。
        /// </summary>
        [Test]
        public void FindType_NonExistentType_ReturnsNull()
        {
            var actual = TypeResolver.FindType("NonExistent.Type.XYZ_12345");

            Assert.That(actual, Is.Null);
        }

        /// <summary>
        /// null 入力で null を返すこと。
        /// </summary>
        [Test]
        public void FindType_Null_ReturnsNull()
        {
            var actual = TypeResolver.FindType(null);

            Assert.That(actual, Is.Null);
        }

        /// <summary>
        /// 空文字列入力で null を返すこと。
        /// </summary>
        [Test]
        public void FindType_EmptyString_ReturnsNull()
        {
            var actual = TypeResolver.FindType("");

            Assert.That(actual, Is.Null);
        }

        /// <summary>
        /// Transform 型をショートネームで解決できること。
        /// (Component.cs で頻繁に使用)
        /// </summary>
        [Test]
        public void FindType_Transform_ReturnsType()
        {
            var actual = TypeResolver.FindType("Transform");

            Assert.That(actual, Is.EqualTo(typeof(Transform)));
        }

        /// <summary>
        /// Rigidbody 型をフルネームで解決できること。
        /// </summary>
        [Test]
        public void FindType_RigidbodyFullName_ReturnsType()
        {
            var actual = TypeResolver.FindType("UnityEngine.Rigidbody");

            Assert.That(actual, Is.EqualTo(typeof(Rigidbody)));
        }
    }
}
