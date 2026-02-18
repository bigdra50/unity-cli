using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityBridge.Helpers;

namespace Game.Tests.Editor
{
    /// <summary>
    /// BridgeStatusFile の race condition を検証するテスト。
    /// BridgeStatusFile._seq が Interlocked を使っていないため、
    /// 複数スレッドからの並行 WriteStatus 呼び出しで seq 値に重複/欠番が発生する。
    /// </summary>
    [TestFixture]
    public class BridgeStatusFileTests
    {
        private string _tempDir;
        private string _originalEnv;

        [SetUp]
        public void SetUp()
        {
            _tempDir = Path.Combine(Path.GetTempPath(), $"bridge-test-{Guid.NewGuid():N}");
            Directory.CreateDirectory(_tempDir);

            // 環境変数でステータスディレクトリを一時ディレクトリに切り替え
            _originalEnv = Environment.GetEnvironmentVariable("UNITY_BRIDGE_STATUS_DIR");
            Environment.SetEnvironmentVariable("UNITY_BRIDGE_STATUS_DIR", _tempDir);
        }

        [TearDown]
        public void TearDown()
        {
            Environment.SetEnvironmentVariable("UNITY_BRIDGE_STATUS_DIR", _originalEnv);

            if (Directory.Exists(_tempDir))
            {
                Directory.Delete(_tempDir, recursive: true);
            }
        }

        /// <summary>
        /// 複数スレッドから WriteStatus を並行呼び出しし、
        /// seq 値が連番として一意であることを検証する。
        ///
        /// 現状: ++_seq が Interlocked なしのため、並行呼び出しで
        /// 同一 seq 値が複数回出現する（重複）可能性がある。
        /// このテストは RED 状態（失敗）が正しい。
        /// </summary>
        [Test]
        public void WriteStatus_ConcurrentCalls_SeqValuesShouldBeUnique()
        {
            const int threadCount = 10;
            const int callsPerThread = 50;
            const int totalCalls = threadCount * callsPerThread;

            // 各スレッドが別インスタンスIDでWriteStatusを呼ぶと
            // ファイル書き込みが干渉するため、同一インスタンスIDを使う。
            // seq値はファイルに最後に書かれた値しか残らないため、
            // ConcurrentBag でスレッド内でseqを収集する方式は使えない。
            //
            // 代替手法: 異なるインスタンスIDを使い、
            // 各ファイルからseq値を読み取る。
            var seqValues = new ConcurrentBag<int>();
            var barrier = new Barrier(threadCount);
            var threads = new Thread[threadCount];

            for (var i = 0; i < threadCount; i++)
            {
                var threadIndex = i;
                threads[i] = new Thread(() =>
                {
                    // 全スレッドが揃ってから一斉に開始
                    barrier.SignalAndWait();

                    for (var j = 0; j < callsPerThread; j++)
                    {
                        var instanceId = $"instance-{threadIndex}-{j}";
                        BridgeStatusFile.WriteStatus(
                            instanceId,
                            "TestProject",
                            "2022.3.0f1",
                            "ready",
                            "localhost",
                            6500);

                        // 書き込まれたファイルからseq値を読み取る
                        var filePath = BridgeStatusFile.GetStatusFilePath(instanceId);
                        if (File.Exists(filePath))
                        {
                            try
                            {
                                var json = File.ReadAllText(filePath);
                                var obj = JObject.Parse(json);
                                var seq = obj["seq"]?.Value<int>() ?? -1;
                                seqValues.Add(seq);
                            }
                            catch
                            {
                                // ファイルの読み書き競合は無視
                            }
                        }
                    }
                });
                threads[i].IsBackground = true;
            }

            foreach (var t in threads) t.Start();
            foreach (var t in threads) t.Join(TimeSpan.FromSeconds(30));

            var values = seqValues.ToList();

            // seq値が一意であるべき（各WriteStatus呼び出しで異なるseqが割り当てられるべき）
            var uniqueCount = new HashSet<int>(values).Count;

            Assert.That(values.Count, Is.GreaterThan(0),
                "seq値が1つも収集できなかった");

            // 重複があればrace conditionの証拠
            // 現状の ++_seq は非スレッドセーフなので、高確率で uniqueCount < values.Count になる
            Assert.That(uniqueCount, Is.EqualTo(values.Count),
                $"seq値に重複あり: 合計{values.Count}個中、ユニーク{uniqueCount}個。" +
                $"++_seq が Interlocked.Increment でないため race condition が発生している");
        }

        /// <summary>
        /// seq値が単調増加（欠番なし）であることを検証する。
        /// シングルスレッドでの連続呼び出しでも、
        /// 前提として seq が 1,2,3,... と連番になるべき。
        /// </summary>
        [Test]
        public void WriteStatus_SequentialCalls_SeqValuesShouldBeMonotonicallyIncreasing()
        {
            const int callCount = 20;
            var seqValues = new List<int>();

            for (var i = 0; i < callCount; i++)
            {
                var instanceId = $"seq-test-{i}";
                BridgeStatusFile.WriteStatus(
                    instanceId,
                    "TestProject",
                    "2022.3.0f1",
                    "ready",
                    "localhost",
                    6500);

                var filePath = BridgeStatusFile.GetStatusFilePath(instanceId);
                var json = File.ReadAllText(filePath);
                var obj = JObject.Parse(json);
                seqValues.Add(obj["seq"].Value<int>());
            }

            // 連続する各seq値が前の値より大きいこと
            for (var i = 1; i < seqValues.Count; i++)
            {
                Assert.That(seqValues[i], Is.GreaterThan(seqValues[i - 1]),
                    $"seq[{i}]={seqValues[i]} が seq[{i - 1}]={seqValues[i - 1]} より大きくない");
            }
        }

        [Test]
        public void ComputeInstanceHash_SameInput_ReturnsSameHash()
        {
            var hash1 = BridgeStatusFile.ComputeInstanceHash("/path/to/project");
            var hash2 = BridgeStatusFile.ComputeInstanceHash("/path/to/project");

            Assert.That(hash1, Is.EqualTo(hash2));
        }

        [Test]
        public void ComputeInstanceHash_ReturnsEightCharHex()
        {
            var hash = BridgeStatusFile.ComputeInstanceHash("test-instance");

            Assert.That(hash.Length, Is.EqualTo(8));
            Assert.That(hash, Does.Match("^[0-9a-f]{8}$"));
        }
    }
}
