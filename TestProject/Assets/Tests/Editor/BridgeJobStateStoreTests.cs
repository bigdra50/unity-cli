using System;
using System.IO;
using Newtonsoft.Json;
using NUnit.Framework;
using UnityBridge.Helpers;

namespace Game.Tests.Editor
{
    /// <summary>
    /// BridgeJobStateStore の空 catch 問題を検証するテスト。
    /// LoadState の catch (Exception) { return default; } により、
    /// JSON破損時にエラー情報が呼び出し元に伝わらない。
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
        /// 不正なJSONが書き込まれた場合、LoadState が default を返す。
        /// 問題: ファイル未存在と不正JSONの区別がつかない。
        /// 呼び出し元は「状態がない」と「状態が破損している」を区別できない。
        ///
        /// このテストは、空catchにより例外情報が失われることを明示する。
        /// 現状のコードではこのテストは PASS するが、それ自体が問題を示している。
        /// </summary>
        [Test]
        public void LoadState_CorruptedJson_ReturnsDefaultSilently()
        {
            // まず正常な状態を保存して、ファイルパスを確定させる
            BridgeJobStateStore.SaveState(TestToolName, new SampleState { Name = "valid", Value = 1 });
            Assert.That(BridgeJobStateStore.HasState(TestToolName), Is.True,
                "前提条件: ファイルが存在すること");

            // ファイルを壊す: 保存後に不正JSONで上書き
            // GetStatePath は internal なので、SaveState で作られたファイルの場所を推定する
            // Library/UnityBridgeState_{toolName}.json のパス
            var libraryPath = Path.Combine(UnityEngine.Application.dataPath, "..", "Library");
            var stateFilePath = Path.GetFullPath(
                Path.Combine(libraryPath, $"UnityBridgeState_{TestToolName}.json"));

            File.WriteAllText(stateFilePath, "THIS IS NOT VALID JSON {{{");

            // LoadState は例外を投げずに default を返す（空catchのため）
            var loaded = BridgeJobStateStore.LoadState<SampleState>(TestToolName);

            // 現状のコード: 不正JSONでもdefaultが返る = ファイル未存在と同じ結果
            Assert.That(loaded, Is.Null,
                "不正JSONでも default(null) が返る = 空catchで例外が握りつぶされている");

            // HasState はファイルの存在のみチェックするのでtrueを返す
            Assert.That(BridgeJobStateStore.HasState(TestToolName), Is.True,
                "ファイルは存在するが読み込めない。HasState と LoadState の結果が矛盾する");
        }

        /// <summary>
        /// 破損JSONに対して例外が伝播すべきことを示すテスト。
        /// 現状: 空catchにより例外は伝播しない → このテストは FAIL する。
        /// 修正後: JsonReaderException 等が伝播する → このテストは PASS する。
        ///
        /// RED状態が正しい: 例外が投げられるべきだが、現状は投げられない。
        /// </summary>
        [Test]
        public void LoadState_CorruptedJson_ShouldThrowOrProvideErrorInfo()
        {
            BridgeJobStateStore.SaveState(TestToolName, new SampleState { Name = "valid", Value = 1 });

            var libraryPath = Path.Combine(UnityEngine.Application.dataPath, "..", "Library");
            var stateFilePath = Path.GetFullPath(
                Path.Combine(libraryPath, $"UnityBridgeState_{TestToolName}.json"));

            File.WriteAllText(stateFilePath, "CORRUPTED JSON DATA !!!!");

            // 不正JSONの場合、例外が投げられるべき
            // 現状の空catchにより例外は投げられず、このアサートは失敗する
            Assert.That(() => BridgeJobStateStore.LoadState<SampleState>(TestToolName),
                Throws.InstanceOf<JsonException>(),
                "不正JSONに対して例外が投げられるべきだが、" +
                "catch (Exception) { return default; } により握りつぶされている");
        }

        /// <summary>
        /// 型が一致しないJSONの場合も同様に default が返る。
        /// 例: int型の状態を保存したが、complex type として読み込む場合。
        /// </summary>
        [Test]
        public void LoadState_TypeMismatchJson_ReturnsDefaultSilently()
        {
            // int値を保存
            BridgeJobStateStore.SaveState(TestToolName, 42);

            // SampleState として読み込もうとする
            // デシリアライズの挙動次第だが、型不一致でも静かに失敗する可能性がある
            var loaded = BridgeJobStateStore.LoadState<SampleState>(TestToolName);

            // Newtonsoft.Json は int → SampleState のデシリアライズで例外を投げる場合がある
            // その場合、空catchによりdefaultが返る
            // このテストは型不一致時の挙動を文書化する
            Assert.That(loaded, Is.Null,
                "型不一致のJSONでも空catchにより default が返る");
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
