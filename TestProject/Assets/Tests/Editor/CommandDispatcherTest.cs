using System.Linq;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using NUnit.Framework;

namespace UnityBridge
{
    /// <summary>
    /// CommandDispatcher のテスト。
    /// ReflectionTypeLoadException 発生時にもハンドラ検出が中断されないことを検証する。
    /// </summary>
    [TestFixture]
    public class CommandDispatcherTest
    {
        /// <summary>
        /// Initialize() 後に BridgeTool 属性付きハンドラが登録されていること。
        /// ReflectionTypeLoadException が発生するアセンブリがあっても、
        /// 他のアセンブリからのハンドラ検出が正常に完了する。
        /// </summary>
        [Test]
        public void Initialize_DiscoverHandlers_RegistersAtLeastOneHandler()
        {
            var sut = new CommandDispatcher();

            sut.Initialize();

            Assert.That(sut.RegisteredCommands.Any(), Is.True);
        }

        /// <summary>
        /// "component" コマンドが登録されていること。
        /// ReflectionTypeLoadException でスキップされるアセンブリがあっても、
        /// UnityBridge.Editor アセンブリのハンドラは確実に登録される。
        /// </summary>
        [Test]
        public void Initialize_DiscoverHandlers_ComponentHandlerRegistered()
        {
            var sut = new CommandDispatcher();

            sut.Initialize();

            Assert.That(sut.RegisteredCommands, Does.Contain("component"));
        }

        /// <summary>
        /// 存在しないコマンドを実行すると CommandNotFound エラーになること。
        /// </summary>
        [Test]
        public void ExecuteAsync_UnknownCommand_ThrowsCommandNotFound()
        {
            var sut = new CommandDispatcher();
            sut.Initialize();

            var ex = Assert.ThrowsAsync<ProtocolException>(async () =>
                await sut.ExecuteAsync("nonexistent_command_xyz", new JObject()));

            Assert.That(ex.Code, Is.EqualTo(ErrorCode.CommandNotFound));
        }

        /// <summary>
        /// Initialize() を2回呼んでもハンドラが重複登録されないこと。
        /// </summary>
        [Test]
        public void Initialize_CalledTwice_DoesNotDuplicateHandlers()
        {
            var sut = new CommandDispatcher();

            sut.Initialize();
            var countAfterFirst = sut.RegisteredCommands.Count();

            sut.Initialize();
            var countAfterSecond = sut.RegisteredCommands.Count();

            Assert.That(countAfterSecond, Is.EqualTo(countAfterFirst));
        }

        /// <summary>
        /// 手動登録したハンドラが ExecuteAsync で実行できること。
        /// </summary>
        [Test]
        public async Task ExecuteAsync_ManuallyRegisteredHandler_ReturnsResult()
        {
            var sut = new CommandDispatcher();
            var expected = new JObject { ["status"] = "ok" };
            sut.Register("test_command", (JObject _) => expected);

            var actual = await sut.ExecuteAsync("test_command", new JObject());

            Assert.That(actual["status"]?.Value<string>(), Is.EqualTo("ok"));
        }
    }
}
