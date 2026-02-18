using System;
using System.IO;
using Newtonsoft.Json;
using NUnit.Framework;
using UnityBridge.Helpers;

namespace Game.Tests.Editor
{
    /// <summary>
    /// BridgeJobStateStore の状態永続化を検証するテスト。
    /// LoadState は JsonException を catch し BridgeLog.Warn で記録、default を返す。
    /// </summary>
    [TestFixture]
    public class BridgeJobStateStoreTests
    {
        private const string TestToolName = "BridgeJobStateStoreTest";

        [Serializable]
        private class SampleState
        {
            public string Name;
            public int Value;
        }

        [TearDown]
        public void TearDown()
        {
            BridgeJobStateStore.ClearState(TestToolName);
        }

        /// <summary>
        /// 正常なJSONの保存と読み込みが往復できることを確認する基本テスト。
        /// </summary>
        [Test]
        public void SaveAndLoadState_ValidData_RoundTrips()
        {
            var original = new SampleState { Name = "test", Value = 42 };

            BridgeJobStateStore.SaveState(TestToolName, original);
            var loaded = BridgeJobStateStore.LoadState<SampleState>(TestToolName);

            Assert.That(loaded, Is.Not.Null);
            Assert.That(loaded.Name, Is.EqualTo("test"));
            Assert.That(loaded.Value, Is.EqualTo(42));
        }

        /// <summary>
        /// ファイルが存在しない場合、LoadState は default を返す。
        /// これは正常な動作。
        /// </summary>
        [Test]
        public void LoadState_FileNotExists_ReturnsDefault()
        {
            var result = BridgeJobStateStore.LoadState<SampleState>("nonexistent-tool-xyz");

            Assert.That(result, Is.Null);
        }

        /// <summary>
        /// 破損JSONに対して JsonException を catch し default を返すことを検証。
        /// </summary>
        [Test]
        public void LoadState_CorruptedJson_ReturnsDefault()
        {
            BridgeJobStateStore.SaveState(TestToolName, new SampleState { Name = "valid", Value = 1 });

            var libraryPath = Path.Combine(UnityEngine.Application.dataPath, "..", "Library");
            var stateFilePath = Path.GetFullPath(
                Path.Combine(libraryPath, $"UnityBridgeState_{TestToolName}.json"));

            File.WriteAllText(stateFilePath, "CORRUPTED JSON DATA !!!!");

            var actual = BridgeJobStateStore.LoadState<SampleState>(TestToolName);

            Assert.That(actual, Is.Null);
        }

        /// <summary>
        /// 型不一致のJSONの場合、JsonException を catch し default を返す。
        /// </summary>
        [Test]
        public void LoadState_TypeMismatchJson_ReturnsDefault()
        {
            BridgeJobStateStore.SaveState(TestToolName, 42);

            var loaded = BridgeJobStateStore.LoadState<SampleState>(TestToolName);

            Assert.That(loaded, Is.Null);
        }

        [Test]
        public void SaveState_NullToolName_Throws()
        {
            Assert.That(() => BridgeJobStateStore.SaveState<SampleState>(null, new SampleState()),
                Throws.TypeOf<ArgumentException>());
        }

        [Test]
        public void SaveState_EmptyToolName_Throws()
        {
            Assert.That(() => BridgeJobStateStore.SaveState("", new SampleState()),
                Throws.TypeOf<ArgumentException>());
        }

        [Test]
        public void ClearState_RemovesFile()
        {
            BridgeJobStateStore.SaveState(TestToolName, new SampleState { Name = "to-delete", Value = 0 });
            Assert.That(BridgeJobStateStore.HasState(TestToolName), Is.True);

            BridgeJobStateStore.ClearState(TestToolName);

            Assert.That(BridgeJobStateStore.HasState(TestToolName), Is.False);
        }
    }
}
