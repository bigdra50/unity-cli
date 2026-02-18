using System;
using System.Reflection;
using NUnit.Framework;

namespace UnityBridge
{
    /// <summary>
    /// UnityBridge 全体のマジックナンバーを監査するテスト。
    /// 定数化されていないリテラル値を記録し、将来の定数化時の回帰テストとする。
    ///
    /// 監査対象:
    ///   1. RelayServerLauncher.cs:145 - Thread.Sleep(500) ポート解放待機
    ///   2. RelayClient.cs:490         - Task.Delay(500) Dispose時タスク待機
    ///   3. Screenshot.cs:95           - timeoutSeconds = 10 GameViewキャプチャタイムアウト
    ///   4. Screenshot.cs:156-157      - 1920/1080 デフォルトカメラ解像度
    ///   5. Tests.cs:266               - timeoutSeconds = 30 テスト実行タイムアウト
    ///   6. Package.cs:101             - Thread.Sleep(100) パッケージ操作ポーリング
    ///   7. PortManager.cs:31          - timeoutMs = 5000 ポート解放待機タイムアウト
    ///
    /// このテストの目的:
    ///   - ToolConstants / ProtocolConstants に定数が定義されていることを検証
    ///   - 現時点では定数が存在しないため失敗する (RED)
    ///   - 定数化リファクタリング後に通過する (GREEN)
    /// </summary>
    [TestFixture]
    public class MagicNumberAuditTest
    {
        /// <summary>
        /// ProtocolConstants にプロトコル関連の定数が存在すること。
        /// 既存の定数が削除されていないことを確認する回帰テスト。
        /// </summary>
        [TestCase("DefaultPort", 6500)]
        [TestCase("HeartbeatIntervalMs", 5000)]
        [TestCase("HeartbeatTimeoutMs", 15000)]
        [TestCase("CommandTimeoutMs", 30000)]
        [TestCase("ReloadTimeoutMs", 30000)]
        [TestCase("HeaderSize", 4)]
        public void ProtocolConstants_ExistingConstants_HaveExpectedValues(string fieldName, int expected)
        {
            var field = typeof(ProtocolConstants).GetField(fieldName,
                BindingFlags.Public | BindingFlags.Static);

            Assert.That(field, Is.Not.Null);

            var actual = (int)field.GetValue(null);

            Assert.That(actual, Is.EqualTo(expected));
        }

        /// <summary>
        /// ToolConstants クラスが存在すること。
        /// 各ツール固有のマジックナンバーをまとめる定数クラスとして期待。
        ///
        /// 現状: ToolConstants クラスは存在しない → RED
        /// リファクタリング後: 定数クラスが追加される → GREEN
        /// </summary>
        [Test]
        public void ToolConstants_ClassExists()
        {
            var type = FindTypeByName("ToolConstants");

            Assert.That(type, Is.Not.Null,
                "ToolConstants class should exist to hold tool-specific constants. "
                + "Magic numbers in Screenshot.cs, Tests.cs, Package.cs should be moved here.");
        }

        /// <summary>
        /// Screenshot 用の定数が ToolConstants に定義されていること。
        ///
        /// 対象マジックナンバー:
        ///   - Screenshot.cs:95  const int timeoutSeconds = 10 → ToolConstants に移動すべき
        ///   - Screenshot.cs:156 ?? 1920 → デフォルトカメラ幅
        ///   - Screenshot.cs:157 ?? 1080 → デフォルトカメラ高さ
        /// </summary>
        [TestCase("ScreenshotTimeoutSeconds")]
        [TestCase("DefaultCameraWidth")]
        [TestCase("DefaultCameraHeight")]
        public void ToolConstants_ScreenshotConstants_Exist(string fieldName)
        {
            var toolConstantsType = FindTypeByName("ToolConstants");
            Assume.That(toolConstantsType, Is.Not.Null, "ToolConstants class not found");

            var field = toolConstantsType.GetField(fieldName,
                BindingFlags.Public | BindingFlags.Static);

            Assert.That(field, Is.Not.Null,
                $"ToolConstants.{fieldName} should be defined for Screenshot magic number.");
        }

        /// <summary>
        /// テスト実行タイムアウトの定数が ToolConstants に定義されていること。
        ///
        /// 対象: Tests.cs:266 const int timeoutSeconds = 30
        /// </summary>
        [Test]
        public void ToolConstants_TestRunnerTimeoutSeconds_Exists()
        {
            var toolConstantsType = FindTypeByName("ToolConstants");
            Assume.That(toolConstantsType, Is.Not.Null, "ToolConstants class not found");

            var field = toolConstantsType.GetField("TestRunnerTimeoutSeconds",
                BindingFlags.Public | BindingFlags.Static);

            Assert.That(field, Is.Not.Null,
                "ToolConstants.TestRunnerTimeoutSeconds should be defined. "
                + "Currently a magic number in Tests.cs:266.");
        }

        /// <summary>
        /// パッケージ操作ポーリング間隔の定数が ToolConstants に定義されていること。
        ///
        /// 対象: Package.cs:101 Thread.Sleep(100)
        /// </summary>
        [Test]
        public void ToolConstants_PackagePollingIntervalMs_Exists()
        {
            var toolConstantsType = FindTypeByName("ToolConstants");
            Assume.That(toolConstantsType, Is.Not.Null, "ToolConstants class not found");

            var field = toolConstantsType.GetField("PackagePollingIntervalMs",
                BindingFlags.Public | BindingFlags.Static);

            Assert.That(field, Is.Not.Null,
                "ToolConstants.PackagePollingIntervalMs should be defined. "
                + "Currently a magic number in Package.cs:101.");
        }

        /// <summary>
        /// ポート解放待機の定数が ProtocolConstants に定義されていること。
        ///
        /// 対象:
        ///   - RelayServerLauncher.cs:145 Thread.Sleep(500) ポート解放待機
        ///   - RelayClient.cs:490 Task.Delay(500) Dispose時タスク待機
        /// </summary>
        [Test]
        public void ProtocolConstants_PortReleaseWaitMs_Exists()
        {
            var field = typeof(ProtocolConstants).GetField("PortReleaseWaitMs",
                BindingFlags.Public | BindingFlags.Static);

            Assert.That(field, Is.Not.Null,
                "ProtocolConstants.PortReleaseWaitMs should be defined. "
                + "Thread.Sleep(500) in RelayServerLauncher.cs:145 and "
                + "Task.Delay(500) in RelayClient.cs:490 use this value.");
        }

        /// <summary>
        /// Dispose時のタスク待機タイムアウトが定数化されていること。
        ///
        /// 対象: RelayClient.cs:490 Task.Delay(500)
        /// </summary>
        [Test]
        public void ProtocolConstants_DisposeTaskWaitMs_Exists()
        {
            var field = typeof(ProtocolConstants).GetField("DisposeTaskWaitMs",
                BindingFlags.Public | BindingFlags.Static);

            Assert.That(field, Is.Not.Null,
                "ProtocolConstants.DisposeTaskWaitMs should be defined. "
                + "Currently a magic number (500) in RelayClient.cs:490.");
        }

        /// <summary>
        /// PortManager のデフォルトタイムアウトが定数化されていること。
        ///
        /// 対象: PortManager.cs:31 timeoutMs = 5000
        /// PortManager.PollingIntervalMs (100) は既にローカル定数化されている。
        /// ただしデフォルト引数の 5000 は定数参照であるべき。
        /// </summary>
        [Test]
        public void ProtocolConstants_PortWaitTimeoutMs_Exists()
        {
            var field = typeof(ProtocolConstants).GetField("PortWaitTimeoutMs",
                BindingFlags.Public | BindingFlags.Static);

            Assert.That(field, Is.Not.Null,
                "ProtocolConstants.PortWaitTimeoutMs should be defined. "
                + "Currently a default argument (5000) in PortManager.cs:31.");
        }

        /// <summary>
        /// 全アセンブリから型名で検索するヘルパー。
        /// </summary>
        private static Type FindTypeByName(string typeName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                try
                {
                    foreach (var type in assembly.GetTypes())
                    {
                        if (type.Name == typeName)
                            return type;
                    }
                }
                catch (ReflectionTypeLoadException)
                {
                    // Skip assemblies that can't be loaded
                }
            }

            return null;
        }
    }
}
