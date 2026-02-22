using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using NUnit.Framework;

namespace UnityBridge
{
    /// <summary>
    /// BridgeManager の DI (Dependency Injection) 対応を検証するテスト。
    /// ICommandDispatcher / IRelayClient インターフェースを注入し、
    /// 具象クラスに依存せずにコマンド実行フローが動作することを確認する。
    /// </summary>
    [TestFixture]
    public class BridgeManagerDITest
    {
        /// <summary>
        /// ICommandDispatcher のスタブ実装。
        /// 登録されたコマンドを実行し、結果を返す。
        /// </summary>
        private sealed class StubCommandDispatcher : ICommandDispatcher
        {
            private readonly Dictionary<string, Func<JObject, Task<JObject>>> _handlers = new();

            public IEnumerable<string> RegisteredCommands => _handlers.Keys;

            public bool InitializeCalled { get; private set; }

            public void Initialize()
            {
                InitializeCalled = true;
            }

            public Task<JObject> ExecuteAsync(string commandName, JObject parameters)
            {
                if (_handlers.TryGetValue(commandName, out var handler))
                    return handler(parameters);

                throw new ProtocolException(ErrorCode.CommandNotFound, $"Unknown command: {commandName}");
            }

            public void Register(string commandName, Func<JObject, Task<JObject>> handler)
            {
                _handlers[commandName] = handler;
            }
        }

        /// <summary>
        /// IRelayClient のスタブ実装。
        /// 接続・送信操作を記録する。
        /// </summary>
        private sealed class StubRelayClient : IRelayClient
        {
            public string InstanceId => "/stub/project";
            public bool IsConnected { get; set; }
            public ConnectionStatus Status => IsConnected ? ConnectionStatus.Connected : ConnectionStatus.Disconnected;
            public string ProjectName => "StubProject";
            public string UnityVersion => "6000.0.0f1";
            public string[] Capabilities { get; set; } = Array.Empty<string>();

            public event EventHandler<ConnectionStatusChangedEventArgs> StatusChanged;
            public event EventHandler<CommandReceivedEventArgs> CommandReceived;

            public bool ConnectCalled { get; private set; }
            public bool DisconnectCalled { get; private set; }
            public bool DisposeCalled { get; private set; }

            public List<(string Id, JObject Data)> SentResults { get; } = new();
            public List<(string Id, string Code, string Message)> SentErrors { get; } = new();

            public Task ConnectAsync(CancellationToken cancellationToken = default)
            {
                ConnectCalled = true;
                IsConnected = true;
                StatusChanged?.Invoke(this,
                    new ConnectionStatusChangedEventArgs(ConnectionStatus.Disconnected, ConnectionStatus.Connected));
                return Task.CompletedTask;
            }

            public Task DisconnectAsync()
            {
                DisconnectCalled = true;
                IsConnected = false;
                return Task.CompletedTask;
            }

            public Task SendStatusAsync(string status, string detail = null) => Task.CompletedTask;
            public Task SendReloadingStatusAsync() => Task.CompletedTask;
            public Task SendReadyStatusAsync() => Task.CompletedTask;

            public Task SendCommandResultAsync(string id, JObject data)
            {
                SentResults.Add((id, data));
                return Task.CompletedTask;
            }

            public Task SendCommandErrorAsync(string id, string code, string message)
            {
                SentErrors.Add((id, code, message));
                return Task.CompletedTask;
            }

            public void SimulateCommandReceived(string id, string command, JObject parameters)
            {
                CommandReceived?.Invoke(this, new CommandReceivedEventArgs(id, command, parameters, 30000));
            }

            public void Dispose()
            {
                DisposeCalled = true;
            }

            public ValueTask DisposeAsync()
            {
                DisposeCalled = true;
                return default;
            }
        }

        /// <summary>
        /// ICommandDispatcher を注入して BridgeManager が生成できること。
        /// </summary>
        [Test]
        public void Constructor_WithInjectedDispatcher_SetsDispatcherProperty()
        {
            var stubDispatcher = new StubCommandDispatcher();

            var sut = new BridgeManager(stubDispatcher);

            Assert.That(sut.Dispatcher, Is.SameAs(stubDispatcher));
        }

        /// <summary>
        /// null の dispatcher を渡すと ArgumentNullException がスローされること。
        /// </summary>
        [Test]
        public void Constructor_NullDispatcher_ThrowsArgumentNullException()
        {
            Assert.Throws<ArgumentNullException>(() => new BridgeManager(null));
        }

        /// <summary>
        /// IRelayClient ファクトリを注入して ConnectAsync でスタブクライアントが使われること。
        /// </summary>
        [Test]
        public async Task ConnectAsync_WithInjectedClientFactory_UsesFactory()
        {
            var stubDispatcher = new StubCommandDispatcher();
            var stubClient = new StubRelayClient();
            var sut = new BridgeManager(stubDispatcher, (_, _) => stubClient);

            await sut.ConnectAsync("127.0.0.1", 6500);

            Assert.That(sut.Client, Is.SameAs(stubClient));
            Assert.That(stubClient.ConnectCalled, Is.True);
        }

        /// <summary>
        /// DisconnectAsync でスタブクライアントの DisposeAsync が呼ばれること。
        /// BridgeManager.DisconnectAsync は DisconnectAsync ではなく DisposeAsync を呼ぶ設計。
        /// </summary>
        [Test]
        public async Task DisconnectAsync_WithInjectedClient_CallsDisposeAsync()
        {
            var stubDispatcher = new StubCommandDispatcher();
            var stubClient = new StubRelayClient();
            var sut = new BridgeManager(stubDispatcher, (_, _) => stubClient);

            await sut.ConnectAsync("127.0.0.1", 6500);
            await sut.DisconnectAsync();

            Assert.That(stubClient.DisposeCalled, Is.True);
        }

        /// <summary>
        /// 接続していない状態では IsConnected が false であること。
        /// </summary>
        [Test]
        public void IsConnected_BeforeConnect_ReturnsFalse()
        {
            var sut = new BridgeManager(new StubCommandDispatcher());

            Assert.That(sut.IsConnected, Is.False);
        }

        /// <summary>
        /// 接続後は IsConnected が true であること。
        /// </summary>
        [Test]
        public async Task IsConnected_AfterConnect_ReturnsTrue()
        {
            var stubClient = new StubRelayClient();
            var sut = new BridgeManager(new StubCommandDispatcher(), (_, _) => stubClient);

            await sut.ConnectAsync();

            Assert.That(sut.IsConnected, Is.True);
        }

        /// <summary>
        /// SetCapabilities がスタブクライアントに反映されること。
        /// </summary>
        [Test]
        public async Task SetCapabilities_AfterConnect_SetsOnClient()
        {
            var stubClient = new StubRelayClient();
            var sut = new BridgeManager(new StubCommandDispatcher(), (_, _) => stubClient);

            await sut.ConnectAsync();
            sut.SetCapabilities("uitree", "screenshot");

            Assert.That(stubClient.Capabilities, Is.EqualTo(new[] { "uitree", "screenshot" }));
        }

        /// <summary>
        /// Dispatcher プロパティの型が ICommandDispatcher であること（DIP準拠）。
        /// </summary>
        [Test]
        public void DispatcherProperty_IsInterfaceType()
        {
            var property = typeof(BridgeManager).GetProperty("Dispatcher");

            Assert.That(property, Is.Not.Null);
            Assert.That(property.PropertyType, Is.EqualTo(typeof(ICommandDispatcher)));
        }

        /// <summary>
        /// Client プロパティの型が IRelayClient であること（DIP準拠）。
        /// </summary>
        [Test]
        public void ClientProperty_IsInterfaceType()
        {
            var property = typeof(BridgeManager).GetProperty("Client");

            Assert.That(property, Is.Not.Null);
            Assert.That(property.PropertyType, Is.EqualTo(typeof(IRelayClient)));
        }
    }
}
