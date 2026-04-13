using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using NUnit.Framework;

namespace UnityBridge
{
    /// <summary>
    /// BridgeManager のスレッディング契約を検証するテスト。
    ///
    /// 背景: <see cref="BridgeManager.OnCommandReceived"/> は <see cref="RelayClient.ReceiveLoopAsync"/>
    /// から発火するためバックグラウンドスレッド上で呼ばれる。Unity の <c>EditorApplication</c> 系 API は
    /// メインスレッド専用で、バックグラウンドスレッドからの呼び出しは例外を出さずに無視されるため、
    /// <c>EditorApplication.update</c> へのハンドラ登録は接続時 (メインスレッド) に済ませておく必要がある。
    /// </summary>
    [TestFixture]
    public class BridgeManagerThreadingTests
    {
        [Test]
        public async Task ConnectAsync_RegistersEditorApplicationUpdate_OnConnect()
        {
            var stubClient = new StubRelayClient();
            var manager = new BridgeManager(new StubCommandDispatcher(), (_, _) => stubClient);

            try
            {
                await manager.ConnectAsync();

                Assert.That(GetUpdateRegistered(manager), Is.True,
                    "ConnectAsync は EditorApplication.update へのハンドラ登録をメインスレッドで完了させること。");
            }
            finally
            {
                await manager.DisconnectAsync();
            }
        }

        [Test]
        public async Task ConnectAsync_AfterDisconnect_ReRegistersEditorApplicationUpdate()
        {
            var stubClient1 = new StubRelayClient();
            var stubClient2 = new StubRelayClient();
            var clients = new Queue<IRelayClient>(new IRelayClient[] { stubClient1, stubClient2 });
            var manager = new BridgeManager(new StubCommandDispatcher(), (_, _) => clients.Dequeue());

            try
            {
                await manager.ConnectAsync();
                await manager.DisconnectAsync();

                Assert.That(GetUpdateRegistered(manager), Is.False,
                    "DisconnectAsync 後はハンドラ登録が解除されていること。");

                await manager.ConnectAsync();

                Assert.That(GetUpdateRegistered(manager), Is.True,
                    "再接続時に EditorApplication.update へのハンドラが再登録されること。");
            }
            finally
            {
                await manager.DisconnectAsync();
            }
        }

        [Test]
        public void ConnectAsync_WhenClientConnectThrows_RollsBackState()
        {
            var stubClient = new StubRelayClient { ConnectThrows = true };
            var manager = new BridgeManager(new StubCommandDispatcher(), (_, _) => stubClient);

            Assert.ThrowsAsync<InvalidOperationException>(async () => await manager.ConnectAsync());

            Assert.That(GetUpdateRegistered(manager), Is.False,
                "ConnectAsync が失敗した場合、UnregisterUpdate でハンドラ登録が解除されていること。");
            Assert.That(manager.Client, Is.Null,
                "ConnectAsync が失敗した場合、Client プロパティは null に戻っていること。");
            Assert.That(stubClient.DisposeCalled, Is.True,
                "ConnectAsync が失敗した場合、Client.DisposeAsync が呼ばれていること。");
        }

        private static bool GetUpdateRegistered(BridgeManager manager)
            => manager.IsUpdateRegistered;

        private sealed class StubCommandDispatcher : ICommandDispatcher
        {
            public IEnumerable<string> RegisteredCommands => Array.Empty<string>();
            public void Initialize() { }
            public Task<JObject> ExecuteAsync(string commandName, JObject parameters)
                => Task.FromResult(new JObject());
        }

        private sealed class StubRelayClient : IRelayClient
        {
            public string InstanceId => "/stub/project";
            public bool IsConnected { get; private set; }
            public ConnectionStatus Status => IsConnected ? ConnectionStatus.Connected : ConnectionStatus.Disconnected;
            public string ProjectName => "StubProject";
            public string UnityVersion => "6000.0.0f1";
            public string[] Capabilities { get; set; } = Array.Empty<string>();

            public bool ConnectThrows { get; set; }
            public bool DisposeCalled { get; private set; }

            public event EventHandler<ConnectionStatusChangedEventArgs> StatusChanged;
            public event EventHandler<CommandReceivedEventArgs> CommandReceived;

            public Task ConnectAsync(CancellationToken cancellationToken = default)
            {
                if (ConnectThrows)
                    throw new InvalidOperationException("stub connect failure");

                IsConnected = true;
                StatusChanged?.Invoke(this,
                    new ConnectionStatusChangedEventArgs(ConnectionStatus.Disconnected, ConnectionStatus.Connected));
                return Task.CompletedTask;
            }

            public Task DisconnectAsync()
            {
                IsConnected = false;
                return Task.CompletedTask;
            }

            public Task SendStatusAsync(string status, string detail = null) => Task.CompletedTask;
            public Task SendReloadingStatusAsync() => Task.CompletedTask;
            public Task SendReadyStatusAsync() => Task.CompletedTask;
            public Task SendCommandResultAsync(string id, JObject data) => Task.CompletedTask;
            public Task SendCommandErrorAsync(string id, string code, string message) => Task.CompletedTask;
            public void Dispose() { DisposeCalled = true; }
            public ValueTask DisposeAsync() { DisposeCalled = true; return default; }
        }
    }
}
