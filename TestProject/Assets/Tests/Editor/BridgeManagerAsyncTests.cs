using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityBridge;

namespace Game.Tests.Editor
{
    /// <summary>
    /// BridgeManager.ExecuteCommandOnMainThreadAsync の async void → Task 修正を検証するテスト。
    ///
    /// 修正前: async void ExecuteCommandOnMainThread で例外が呼び出し元に伝播しない。
    /// 修正後: async Task ExecuteCommandOnMainThreadAsync で例外を Task 経由で捕捉可能。
    /// </summary>
    [TestFixture]
    public class BridgeManagerAsyncTests
    {
        /// <summary>
        /// Dispatcher が例外を投げた場合、Task 経由で例外情報が保持されることを検証。
        /// 修正前の async void では例外が SynchronizationContext に投げられるため、
        /// テストから例外を観測できなかった。
        /// </summary>
        [Test]
        public async Task ExecuteCommandOnMainThreadAsync_DispatcherThrows_SendsErrorViaClient()
        {
            var sentErrors = new List<(string id, string code, string message)>();
            var mockClient = new MockRelayClient
            {
                IsConnectedValue = true,
                OnSendCommandError = (id, code, msg) => sentErrors.Add((id, code, msg))
            };
            var mockDispatcher = new MockCommandDispatcher
            {
                OnExecute = (_, _) => throw new InvalidOperationException("test error")
            };

            var manager = new BridgeManager(mockDispatcher);
            manager.SetClientForTesting(mockClient);

            var args = new CommandReceivedEventArgs("req-1", "test_command", new JObject(), 30000);

            // async Task なので await で例外ハンドリングを確認できる
            // 内部 catch で SendCommandErrorAsync が呼ばれるため、例外は伝播しない
            await manager.ExecuteCommandOnMainThreadAsync(args);

            Assert.That(sentErrors.Count, Is.EqualTo(1));
            Assert.That(sentErrors[0].id, Is.EqualTo("req-1"));
            Assert.That(sentErrors[0].code, Is.EqualTo(ErrorCode.InternalError));
            Assert.That(sentErrors[0].message, Is.EqualTo("test error"));
        }

        /// <summary>
        /// ProtocolException が投げられた場合、エラーコードが正しく伝達されることを検証。
        /// </summary>
        [Test]
        public async Task ExecuteCommandOnMainThreadAsync_ProtocolException_SendsProtocolError()
        {
            var sentErrors = new List<(string id, string code, string message)>();
            var mockClient = new MockRelayClient
            {
                IsConnectedValue = true,
                OnSendCommandError = (id, code, msg) => sentErrors.Add((id, code, msg))
            };
            var mockDispatcher = new MockCommandDispatcher
            {
                OnExecute = (_, _) => throw new ProtocolException(ErrorCode.InvalidParams, "bad params")
            };

            var manager = new BridgeManager(mockDispatcher);
            manager.SetClientForTesting(mockClient);

            var args = new CommandReceivedEventArgs("req-2", "bad_command", new JObject(), 30000);
            await manager.ExecuteCommandOnMainThreadAsync(args);

            Assert.That(sentErrors.Count, Is.EqualTo(1));
            Assert.That(sentErrors[0].code, Is.EqualTo(ErrorCode.InvalidParams));
            Assert.That(sentErrors[0].message, Is.EqualTo("bad params"));
        }

        /// <summary>
        /// 正常系: コマンド実行結果が SendCommandResultAsync で送信されることを検証。
        /// </summary>
        [Test]
        public async Task ExecuteCommandOnMainThreadAsync_Success_SendsResult()
        {
            var sentResults = new List<(string id, JObject data)>();
            var expectedResult = new JObject { ["status"] = "ok" };
            var mockClient = new MockRelayClient
            {
                IsConnectedValue = true,
                OnSendCommandResult = (id, data) => sentResults.Add((id, data))
            };
            var mockDispatcher = new MockCommandDispatcher
            {
                OnExecute = (_, _) => expectedResult
            };

            var manager = new BridgeManager(mockDispatcher);
            manager.SetClientForTesting(mockClient);

            var args = new CommandReceivedEventArgs("req-3", "good_command", new JObject(), 30000);
            await manager.ExecuteCommandOnMainThreadAsync(args);

            Assert.That(sentResults.Count, Is.EqualTo(1));
            Assert.That(sentResults[0].id, Is.EqualTo("req-3"));
            Assert.That(sentResults[0].data["status"]?.Value<string>(), Is.EqualTo("ok"));
        }

        /// <summary>
        /// クライアント未接続時はコマンドが実行されないことを検証。
        /// </summary>
        [Test]
        public async Task ExecuteCommandOnMainThreadAsync_NotConnected_SkipsExecution()
        {
            var executedCommands = new List<string>();
            var mockClient = new MockRelayClient { IsConnectedValue = false };
            var mockDispatcher = new MockCommandDispatcher
            {
                OnExecute = (cmd, _) =>
                {
                    executedCommands.Add(cmd);
                    return new JObject();
                }
            };

            var manager = new BridgeManager(mockDispatcher);
            manager.SetClientForTesting(mockClient);

            var args = new CommandReceivedEventArgs("req-4", "should_not_run", new JObject(), 30000);
            await manager.ExecuteCommandOnMainThreadAsync(args);

            Assert.That(executedCommands, Is.Empty);
        }

        #region Mock implementations

        private class MockRelayClient : IRelayClient
        {
            public string InstanceId => "mock-instance";
            public bool IsConnected => IsConnectedValue;
            public bool IsConnectedValue { get; set; }
            public ConnectionStatus Status => IsConnected ? ConnectionStatus.Connected : ConnectionStatus.Disconnected;
            public string ProjectName => "MockProject";
            public string UnityVersion => "6000.0.0f1";
            public string[] Capabilities { get; set; } = Array.Empty<string>();

            public event EventHandler<ConnectionStatusChangedEventArgs> StatusChanged;
            public event EventHandler<CommandReceivedEventArgs> CommandReceived;

            public Action<string, JObject> OnSendCommandResult { get; set; }
            public Action<string, string, string> OnSendCommandError { get; set; }

            public Task ConnectAsync(CancellationToken cancellationToken = default) => Task.CompletedTask;
            public Task DisconnectAsync() => Task.CompletedTask;
            public Task SendReloadingStatusAsync() => Task.CompletedTask;
            public Task SendReadyStatusAsync() => Task.CompletedTask;

            public Task SendCommandResultAsync(string id, JObject data)
            {
                OnSendCommandResult?.Invoke(id, data);
                return Task.CompletedTask;
            }

            public Task SendCommandErrorAsync(string id, string code, string message)
            {
                OnSendCommandError?.Invoke(id, code, message);
                return Task.CompletedTask;
            }

            public void Dispose() { }
            public ValueTask DisposeAsync() => default;
        }

        private class MockCommandDispatcher : ICommandDispatcher
        {
            public IEnumerable<string> RegisteredCommands => Array.Empty<string>();
            public Func<string, JObject, JObject> OnExecute { get; set; }

            public void Initialize() { }

            public Task<JObject> ExecuteAsync(string commandName, JObject parameters)
            {
                if (OnExecute == null)
                    return Task.FromResult(new JObject());
                return Task.FromResult(OnExecute(commandName, parameters));
            }
        }

        #endregion
    }

    /// <summary>
    /// BridgeManager のテスト用拡張。
    /// Client プロパティの setter が private なため、テストからモックを設定するヘルパー。
    /// </summary>
    internal static class BridgeManagerTestExtensions
    {
        internal static void SetClientForTesting(this BridgeManager manager, IRelayClient client)
        {
            // Client プロパティは private set なので、リフレクションで設定
            var prop = typeof(BridgeManager).GetProperty("Client");
            prop?.SetValue(manager, client);
        }
    }
}
