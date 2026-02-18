using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using NUnit.Framework;
using UnityBridge;

namespace Game.Tests.Editor
{
    /// <summary>
    /// RelayClient の IAsyncDisposable 実装を検証するテスト。
    /// DisposeAsync() で DisconnectInternalAsync を await し、
    /// 呼び出し後にソケットが確実にクローズされることを保証する。
    /// </summary>
    [TestFixture]
    public class RelayClientDisposeAsyncTests
    {
        private const int ServerTimeoutMs = 5000;

        /// <summary>
        /// DisposeAsync 後にクライアントが Disconnected 状態であることを検証。
        /// </summary>
        [Test, Explicit("TCP接続テスト: Relay接続と干渉するためCIでは除外")]
        public async Task DisposeAsync_AfterConnect_StatusIsDisconnected()
        {
            var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            try
            {
                var port = ((IPEndPoint)listener.LocalEndpoint).Port;
                using var cts = new CancellationTokenSource(ServerTimeoutMs);

                var serverTask = Task.Run(async () =>
                {
                    using var serverClient = await listener.AcceptTcpClientAsync();
                    using var serverStream = serverClient.GetStream();

                    await Framing.ReadFrameAsync(serverStream, cts.Token);

                    var registered = new Newtonsoft.Json.Linq.JObject
                    {
                        ["type"] = MessageType.Registered,
                        ["success"] = true,
                        ["heartbeat_interval_ms"] = 5000
                    };
                    await Framing.WriteFrameAsync(serverStream, registered);

                    try
                    {
                        while (true)
                            await Framing.ReadFrameAsync(serverStream, cts.Token);
                    }
                    catch { }
                });

                var client = new RelayClient("127.0.0.1", port);
                await client.ConnectAsync();

                Assert.That(client.Status, Is.EqualTo(ConnectionStatus.Connected));

                await client.DisposeAsync();

                Assert.That(client.Status, Is.EqualTo(ConnectionStatus.Disconnected));

                try { await serverTask; } catch { }
            }
            finally
            {
                listener.Stop();
            }
        }

        /// <summary>
        /// 未接続状態での DisposeAsync が例外なく完了することを検証。
        /// </summary>
        [Test]
        public async Task DisposeAsync_NotConnected_DoesNotThrow()
        {
            var client = new RelayClient("127.0.0.1", 0);

            Assert.DoesNotThrowAsync(async () => await client.DisposeAsync());
        }

        /// <summary>
        /// DisposeAsync を2回呼んでも例外にならないことを検証。
        /// </summary>
        [Test, Explicit("TCP接続テスト: Relay接続と干渉するためCIでは除外")]
        public async Task DisposeAsync_CalledTwice_DoesNotThrow()
        {
            var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            try
            {
                var port = ((IPEndPoint)listener.LocalEndpoint).Port;
                using var cts = new CancellationTokenSource(ServerTimeoutMs);

                var serverTask = Task.Run(async () =>
                {
                    using var serverClient = await listener.AcceptTcpClientAsync();
                    using var serverStream = serverClient.GetStream();

                    await Framing.ReadFrameAsync(serverStream, cts.Token);

                    var registered = new Newtonsoft.Json.Linq.JObject
                    {
                        ["type"] = MessageType.Registered,
                        ["success"] = true,
                        ["heartbeat_interval_ms"] = 5000
                    };
                    await Framing.WriteFrameAsync(serverStream, registered);

                    try
                    {
                        while (true)
                            await Framing.ReadFrameAsync(serverStream, cts.Token);
                    }
                    catch { }
                });

                var client = new RelayClient("127.0.0.1", port);
                await client.ConnectAsync();

                await client.DisposeAsync();

                Assert.DoesNotThrowAsync(async () => await client.DisposeAsync());

                try { await serverTask; } catch { }
            }
            finally
            {
                listener.Stop();
            }
        }

        /// <summary>
        /// IAsyncDisposable インターフェースが実装されていることを型レベルで検証。
        /// </summary>
        [Test]
        public void RelayClient_ImplementsIAsyncDisposable()
        {
            Assert.That(typeof(IAsyncDisposable).IsAssignableFrom(typeof(RelayClient)),
                "RelayClient は IAsyncDisposable を実装すべき");
        }

        /// <summary>
        /// IRelayClient インターフェースが IAsyncDisposable を継承していることを検証。
        /// </summary>
        [Test]
        public void IRelayClient_ExtendsIAsyncDisposable()
        {
            Assert.That(typeof(IAsyncDisposable).IsAssignableFrom(typeof(IRelayClient)),
                "IRelayClient は IAsyncDisposable を継承すべき");
        }
    }
}
