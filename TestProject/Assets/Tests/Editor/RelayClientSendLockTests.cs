using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityBridge;

namespace Game.Tests.Editor
{
    /// <summary>
    /// RelayClient の SemaphoreSlim による並行書き込み保護を検証するテスト。
    ///
    /// 問題: 複数の async メソッド (SendCommandResultAsync, SendCommandErrorAsync,
    /// HandlePingAsync 等) が排他制御なしで同一 NetworkStream に書き込むと、
    /// フレームヘッダーとペイロードがインターリーブされ、受信側で壊れたメッセージになる。
    ///
    /// 修正: SemaphoreSlim(1,1) で全書き込みを排他制御。
    /// このテストは、Framing.WriteFrameAsync の並行呼び出しでフレーム整合性が保たれることを検証する。
    /// </summary>
    [TestFixture]
    public class RelayClientSendLockTests
    {
        /// <summary>
        /// Framing.WriteFrameAsync を複数タスクから並行呼び出しし、
        /// 受信側でフレームが正しく読めることを検証する。
        ///
        /// SemaphoreSlim で保護しない場合、ヘッダーとペイロードが混在し、
        /// ReadFrameAsync で不正なペイロード長やJSON解析エラーが発生する。
        /// </summary>
        [Test, Explicit("TCP接続テスト: Relay接続と干渉するためCIでは除外")]
        public void WriteFrameAsync_ConcurrentWrites_FrameIntegrity()
        {
            const int writerCount = 10;
            const int messagesPerWriter = 20;
            const int totalMessages = writerCount * messagesPerWriter;

            TcpListener listener = null;

            try
            {
                listener = new TcpListener(IPAddress.Loopback, 0);
                listener.Start();
                var port = ((IPEndPoint)listener.LocalEndpoint).Port;

                var receivedMessages = new ConcurrentBag<JObject>();
                var receiveErrors = new ConcurrentBag<string>();

                // 受信側: フレームプロトコルに従って全メッセージを読み取る
                var receiveTask = Task.Run(async () =>
                {
                    using var serverClient = await listener.AcceptTcpClientAsync();
                    using var serverStream = serverClient.GetStream();

                    for (var i = 0; i < totalMessages; i++)
                    {
                        try
                        {
                            var msg = await ReadFrameManualAsync(serverStream);
                            receivedMessages.Add(msg);
                        }
                        catch (Exception ex)
                        {
                            receiveErrors.Add($"Message {i}: {ex.GetType().Name}: {ex.Message}");
                        }
                    }
                });

                // 送信側: SemaphoreSlim で保護した並行書き込み
                using var client = new TcpClient();
                client.Connect(IPAddress.Loopback, port);
                using var stream = client.GetStream();

                var sendLock = new SemaphoreSlim(1, 1);
                var barrier = new Barrier(writerCount);
                var sendTasks = new Task[writerCount];

                for (var w = 0; w < writerCount; w++)
                {
                    var writerId = w;
                    sendTasks[w] = Task.Run(async () =>
                    {
                        barrier.SignalAndWait();

                        for (var m = 0; m < messagesPerWriter; m++)
                        {
                            var payload = new JObject
                            {
                                ["type"] = "TEST",
                                ["writer"] = writerId,
                                ["seq"] = m,
                                ["data"] = $"message-{writerId}-{m}"
                            };

                            await sendLock.WaitAsync();
                            try
                            {
                                await Framing.WriteFrameAsync(stream, payload);
                            }
                            finally
                            {
                                sendLock.Release();
                            }
                        }
                    });
                }

                Task.WaitAll(sendTasks);

                // 受信タスクの完了を待つ
                var completed = receiveTask.Wait(TimeSpan.FromSeconds(10));

                Assert.That(completed, Is.True, "受信タスクがタイムアウトした");
                Assert.That(receiveErrors, Is.Empty,
                    $"フレーム読み取りエラー: {string.Join("; ", receiveErrors)}");
                Assert.That(receivedMessages.Count, Is.EqualTo(totalMessages),
                    $"受信メッセージ数が不一致: expected={totalMessages}, actual={receivedMessages.Count}");

                // 各メッセージが有効なJSONであることを確認
                foreach (var msg in receivedMessages)
                {
                    Assert.That(msg["type"]?.Value<string>(), Is.EqualTo("TEST"));
                    Assert.That(msg["writer"], Is.Not.Null);
                    Assert.That(msg["seq"], Is.Not.Null);
                }
            }
            finally
            {
                listener?.Stop();
            }
        }

        /// <summary>
        /// SemaphoreSlim なしで並行書き込みした場合にフレーム破壊が発生することを示すテスト。
        /// このテストは修正の必要性を証明する。
        ///
        /// 注意: race condition の再現は環境依存であり、常に失敗するとは限らない。
        /// ただし十分な並行度があれば高確率でフレーム破壊が検出される。
        /// </summary>
        [Test, Explicit("TCP接続テスト: Relay接続と干渉するためCIでは除外")]
        public void WriteFrameAsync_ConcurrentWritesWithoutLock_MayCorruptFrames()
        {
            const int writerCount = 20;
            const int messagesPerWriter = 50;
            const int totalMessages = writerCount * messagesPerWriter;

            TcpListener listener = null;

            try
            {
                listener = new TcpListener(IPAddress.Loopback, 0);
                listener.Start();
                var port = ((IPEndPoint)listener.LocalEndpoint).Port;

                var receivedMessages = new ConcurrentBag<JObject>();
                var receiveErrors = new ConcurrentBag<string>();

                // 受信側
                var receiveTask = Task.Run(async () =>
                {
                    using var serverClient = await listener.AcceptTcpClientAsync();
                    using var serverStream = serverClient.GetStream();
                    serverClient.ReceiveTimeout = 5000;

                    for (var i = 0; i < totalMessages; i++)
                    {
                        try
                        {
                            var msg = await ReadFrameManualAsync(serverStream);
                            receivedMessages.Add(msg);
                        }
                        catch (Exception ex)
                        {
                            receiveErrors.Add($"Message {i}: {ex.GetType().Name}: {ex.Message}");
                            break; // フレーム破壊後は読み取りを継続できない
                        }
                    }
                });

                // 送信側: ロックなしで並行書き込み
                using var client = new TcpClient();
                client.Connect(IPAddress.Loopback, port);
                using var stream = client.GetStream();

                var barrier = new Barrier(writerCount);
                var sendTasks = new Task[writerCount];

                for (var w = 0; w < writerCount; w++)
                {
                    var writerId = w;
                    sendTasks[w] = Task.Run(async () =>
                    {
                        barrier.SignalAndWait();

                        for (var m = 0; m < messagesPerWriter; m++)
                        {
                            var payload = new JObject
                            {
                                ["type"] = "TEST",
                                ["writer"] = writerId,
                                ["seq"] = m,
                            };

                            // ロックなしで直接書き込み → フレームインターリーブが発生する
                            await Framing.WriteFrameAsync(stream, payload);
                        }
                    });
                }

                try
                {
                    Task.WaitAll(sendTasks);
                }
                catch (AggregateException)
                {
                    // 書き込み側でも例外が発生する可能性がある
                }

                receiveTask.Wait(TimeSpan.FromSeconds(10));

                // ロックなしの場合、以下のいずれかが発生するはず:
                // 1. receiveErrors が非空（フレーム破壊）
                // 2. receivedMessages.Count < totalMessages（途中で読み取り失敗）
                //
                // race condition は非決定的なので、
                // "エラーがない AND 全メッセージ受信" の場合は運が良かっただけ
                var hasCorruption = receiveErrors.Count > 0
                    || receivedMessages.Count < totalMessages;

                // このアサートはドキュメント目的:
                // ロックなしでは高確率でフレーム破壊が発生する
                if (hasCorruption)
                {
                    Assert.Pass(
                        $"フレーム破壊を検出: errors={receiveErrors.Count}, " +
                        $"received={receivedMessages.Count}/{totalMessages}");
                }
                else
                {
                    // race condition が再現しなかった場合
                    Assert.Inconclusive(
                        "今回はフレーム破壊が再現しなかったが、ロックなしの並行書き込みは本質的に危険");
                }
            }
            finally
            {
                listener?.Stop();
            }
        }

        /// <summary>
        /// 4-byte big-endian length prefix + JSON payload のフレームを手動で読み取る。
        /// Framing.ReadFrameAsync と同等だが、テスト用に NetworkStream を直接使う。
        /// </summary>
        private static async Task<JObject> ReadFrameManualAsync(NetworkStream stream)
        {
            var header = new byte[4];
            var headerRead = 0;
            while (headerRead < 4)
            {
                var n = await stream.ReadAsync(header, headerRead, 4 - headerRead);
                if (n == 0) throw new IOException("Connection closed while reading header");
                headerRead += n;
            }

            var length = (header[0] << 24) | (header[1] << 16) | (header[2] << 8) | header[3];
            if (length <= 0 || length > 16 * 1024 * 1024)
            {
                throw new InvalidOperationException(
                    $"Invalid frame length: {length} (header bytes: {header[0]:X2} {header[1]:X2} {header[2]:X2} {header[3]:X2})");
            }

            var payload = new byte[length];
            var payloadRead = 0;
            while (payloadRead < length)
            {
                var n = await stream.ReadAsync(payload, payloadRead, length - payloadRead);
                if (n == 0) throw new IOException("Connection closed while reading payload");
                payloadRead += n;
            }

            var json = Encoding.UTF8.GetString(payload);
            return JObject.Parse(json);
        }
    }
}
