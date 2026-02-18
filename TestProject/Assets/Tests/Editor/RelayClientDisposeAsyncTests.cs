using System;
using System.Net;
using System.Net.Sockets;
using System.Threading.Tasks;
using NUnit.Framework;
using UnityBridge;

namespace Game.Tests.Editor
{
    /// <summary>
    /// RelayClient の IAsyncDisposable 実装を検証するテスト。
    ///
    /// 修正前: Dispose() が fire-and-forget で DisconnectInternalAsync を呼び、
    /// ソケット解放完了が保証されない。
    /// 修正後: DisposeAsync() で DisconnectInternalAsync を await し、
    /// 呼び出し後にソケットが確実にクローズされる。
    /// </summary>
    [TestFixture]
    public class RelayClientDisposeAsyncTests
    {
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

                var serverTask = Task.Run(async () =>
                {
                    using var serverClient = await listener.AcceptTcpClientAsync();
                    using var serverStream = serverClient.GetStream();

                    await Framing.ReadFrameAsync(serverStream);

                    var registered = new Newtonsoft.Json.Linq.JObject
                    {
                        ["type"] = MessageType.Registered,
                        ["success"] = true,
                        ["heartbeat_interval_ms"] = 5000
                    };
                    await Framing.WriteFrameAsync(serverStream, registered);

                    try
                    {
                        while (serverClient.Connected)
                        {
                            await Task.Delay(100);
                            if (serverStream.DataAvailable)
                            {
                                await Framing.ReadFrameAsync(serverStream);
                            }
                        }
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

            // 未接続状態で DisposeAsync を呼んでも例外にならないこと
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

                var serverTask = Task.Run(async () =>
                {
                    using var serverClient = await listener.AcceptTcpClientAsync();
                    using var serverStream = serverClient.GetStream();

                    await Framing.ReadFrameAsync(serverStream);

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
                        {
                            await Task.Delay(100);
                            if (!serverClient.Connected) break;
                        }
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
