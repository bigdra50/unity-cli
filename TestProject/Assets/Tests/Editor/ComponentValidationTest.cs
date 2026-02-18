using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEngine;

namespace UnityBridge.Tools
{
    /// <summary>
    /// Component.cs のターゲット検証ロジック5箇所の一貫性を検証するテスト。
    /// 各アクション（list, inspect, add, remove, modify）で同じ不正入力に対し
    /// 同一のエラーメッセージが返ることを確認する。
    ///
    /// 問題: 5箇所の検証ロジックが重複しており、エラーメッセージに微妙な差異がある。
    /// 例: inspect は "Component '...' not found on GameObject '...'" だが
    ///      remove は "Component '...' not found on '...'" と "GameObject" が抜けている。
    /// </summary>
    [TestFixture]
    public class ComponentValidationTest
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
        /// target も targetId も指定しない場合、全アクションが同一のエラーメッセージをスローすること。
        /// </summary>
        [TestCase("list")]
        [TestCase("inspect")]
        [TestCase("add")]
        [TestCase("remove")]
        [TestCase("modify")]
        public void HandleCommand_NoTargetSpecified_ThrowsConsistentMessage(string action)
        {
            var parameters = new JObject
            {
                ["action"] = action,
                ["type"] = "BoxCollider",
                ["prop"] = "size",
                ["value"] = 1
            };

            var ex = Assert.Throws<ProtocolException>(() => Component.HandleCommand(parameters));

            Assert.That(ex.Message, Is.EqualTo("Either 'target' (name) or 'targetId' (instanceID) is required"));
        }

        /// <summary>
        /// 存在しない GameObject 名を指定した場合、全アクションが同一のエラーメッセージフォーマットを使うこと。
        /// </summary>
        [TestCase("list")]
        [TestCase("inspect")]
        [TestCase("add")]
        [TestCase("remove")]
        [TestCase("modify")]
        public void HandleCommand_NonExistentTarget_ThrowsConsistentMessage(string action)
        {
            var targetName = "NonExistent_GameObject_For_Test_12345";
            var parameters = new JObject
            {
                ["action"] = action,
                ["target"] = targetName,
                ["type"] = "BoxCollider",
                ["prop"] = "size",
                ["value"] = 1
            };

            var ex = Assert.Throws<ProtocolException>(() => Component.HandleCommand(parameters));

            Assert.That(ex.Message, Is.EqualTo($"GameObject not found: {targetName}"));
        }

        /// <summary>
        /// 存在しない instanceID を指定した場合、全アクションが同一のエラーメッセージフォーマットを使うこと。
        /// </summary>
        [TestCase("list")]
        [TestCase("inspect")]
        [TestCase("add")]
        [TestCase("remove")]
        [TestCase("modify")]
        public void HandleCommand_NonExistentTargetId_ThrowsConsistentMessage(string action)
        {
            var invalidId = -99999;
            var parameters = new JObject
            {
                ["action"] = action,
                ["targetId"] = invalidId,
                ["type"] = "BoxCollider",
                ["prop"] = "size",
                ["value"] = 1
            };

            var ex = Assert.Throws<ProtocolException>(() => Component.HandleCommand(parameters));

            Assert.That(ex.Message, Is.EqualTo($"GameObject not found: {invalidId}"));
        }

        /// <summary>
        /// 存在しない型名を指定した場合、inspect/add/remove/modify が同一のエラーメッセージを返すこと。
        /// (list は type パラメータを使用しないため除外)
        /// </summary>
        [TestCase("inspect")]
        [TestCase("add")]
        [TestCase("remove")]
        [TestCase("modify")]
        public void HandleCommand_NonExistentComponentType_ThrowsConsistentMessage(string action)
        {
            var sut = CreateGameObject("TestGO_TypeNotFound");
            var invalidType = "NonExistent.Component.Type.XYZ";
            var parameters = new JObject
            {
                ["action"] = action,
                ["target"] = sut.name,
                ["type"] = invalidType,
                ["prop"] = "size",
                ["value"] = 1
            };

            var ex = Assert.Throws<ProtocolException>(() => Component.HandleCommand(parameters));

            Assert.That(ex.Message, Is.EqualTo($"Component type not found: {invalidType}"));
        }

        /// <summary>
        /// type パラメータが未指定の場合、inspect/add/remove/modify が同一のエラーメッセージを返すこと。
        /// </summary>
        [TestCase("inspect")]
        [TestCase("add")]
        [TestCase("remove")]
        [TestCase("modify")]
        public void HandleCommand_MissingTypeParameter_ThrowsConsistentMessage(string action)
        {
            var sut = CreateGameObject("TestGO_MissingType");
            var parameters = new JObject
            {
                ["action"] = action,
                ["target"] = sut.name,
                ["prop"] = "size",
                ["value"] = 1
            };

            var ex = Assert.Throws<ProtocolException>(() => Component.HandleCommand(parameters));

            Assert.That(ex.Message, Is.EqualTo("'type' parameter is required"));
        }

        /// <summary>
        /// Component not found エラーメッセージが inspect と remove で一貫していること。
        ///
        /// 現状の問題:
        ///   inspect: "Component 'Rigidbody' not found on GameObject 'TestGO'"
        ///   remove:  "Component 'Rigidbody' not found on 'TestGO'"
        /// "GameObject" というワードの有無が異なる。
        ///
        /// このテストは全アクション間でメッセージが一致することを検証するため、
        /// 現状では失敗する（RED）。
        /// </summary>
        [Test]
        public void HandleCommand_ComponentNotFoundOnGameObject_InspectAndRemoveReturnConsistentMessage()
        {
            var sut = CreateGameObject("TestGO_CompNotFound");
            var typeName = "Rigidbody";

            var inspectEx = Assert.Throws<ProtocolException>(() =>
                Component.HandleCommand(new JObject
                {
                    ["action"] = "inspect",
                    ["target"] = sut.name,
                    ["type"] = typeName
                }));

            var removeEx = Assert.Throws<ProtocolException>(() =>
                Component.HandleCommand(new JObject
                {
                    ["action"] = "remove",
                    ["target"] = sut.name,
                    ["type"] = typeName
                }));

            // inspect と remove のエラーメッセージは同一であるべき
            Assert.That(removeEx.Message, Is.EqualTo(inspectEx.Message));
        }

        /// <summary>
        /// Component not found エラーメッセージが inspect と modify で一貫していること。
        /// </summary>
        [Test]
        public void HandleCommand_ComponentNotFoundOnGameObject_InspectAndModifyReturnConsistentMessage()
        {
            var sut = CreateGameObject("TestGO_CompNotFound2");
            var typeName = "Rigidbody";

            var inspectEx = Assert.Throws<ProtocolException>(() =>
                Component.HandleCommand(new JObject
                {
                    ["action"] = "inspect",
                    ["target"] = sut.name,
                    ["type"] = typeName
                }));

            var modifyEx = Assert.Throws<ProtocolException>(() =>
                Component.HandleCommand(new JObject
                {
                    ["action"] = "modify",
                    ["target"] = sut.name,
                    ["type"] = typeName,
                    ["prop"] = "mass",
                    ["value"] = 1.0
                }));

            // inspect と modify のエラーメッセージは同一であるべき
            Assert.That(modifyEx.Message, Is.EqualTo(inspectEx.Message));
        }

        /// <summary>
        /// 全アクションで ErrorCode が一貫して INVALID_PARAMS であること。
        /// </summary>
        [TestCase("list")]
        [TestCase("inspect")]
        [TestCase("add")]
        [TestCase("remove")]
        [TestCase("modify")]
        public void HandleCommand_NoTargetSpecified_ErrorCodeIsInvalidParams(string action)
        {
            var parameters = new JObject
            {
                ["action"] = action,
                ["type"] = "BoxCollider",
                ["prop"] = "size",
                ["value"] = 1
            };

            var ex = Assert.Throws<ProtocolException>(() => Component.HandleCommand(parameters));

            Assert.That(ex.Code, Is.EqualTo(ErrorCode.InvalidParams));
        }

        private GameObject CreateGameObject(string name)
        {
            var go = new GameObject(name);
            _createdObjects.Add(go);
            return go;
        }
    }
}
