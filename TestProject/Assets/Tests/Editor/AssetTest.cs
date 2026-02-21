using System.Reflection;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace UnityBridge.Tools
{
    [TestFixture]
    public class AssetTest
    {
        private const string TempAssetPath = "Assets/Tests/Editor/TestData/AssetTest_Temp.anim";

        [OneTimeSetUp]
        public void OneTimeSetUp()
        {
            var directory = System.IO.Path.GetDirectoryName(TempAssetPath);
            if (!AssetDatabase.IsValidFolder(directory))
            {
                var parts = directory.Split('/');
                var current = parts[0];
                for (var i = 1; i < parts.Length; i++)
                {
                    var next = current + "/" + parts[i];
                    if (!AssetDatabase.IsValidFolder(next))
                        AssetDatabase.CreateFolder(current, parts[i]);
                    current = next;
                }
            }

            if (AssetDatabase.LoadMainAssetAtPath(TempAssetPath) != null)
                AssetDatabase.DeleteAsset(TempAssetPath);

            var asset = new AnimationClip();
            AssetDatabase.CreateAsset(asset, TempAssetPath);
            AssetDatabase.SaveAssets();
        }

        [OneTimeTearDown]
        public void OneTimeTearDown()
        {
            AssetDatabase.DeleteAsset(TempAssetPath);
        }

        /// <summary>
        /// deps アクションが有効なアセットパスで正常に動作すること。
        /// AssetPathExists が存在しない Unity 2022.3 でもコンパイル・実行できることを保証する。
        /// </summary>
        [Test]
        public void HandleCommand_Deps_ValidAsset_ReturnsDependencies()
        {
            var actual = Asset.HandleCommand(new JObject
            {
                ["action"] = "deps",
                ["path"] = TempAssetPath
            });

            Assert.That(actual["path"]?.Value<string>(), Is.EqualTo(TempAssetPath));
        }

        /// <summary>
        /// deps アクションが存在しないパスで InvalidParams をスローすること。
        /// バージョンに依存しない存在チェックの動作を検証する。
        /// </summary>
        [Test]
        public void HandleCommand_Deps_NonExistentAsset_ThrowsInvalidParams()
        {
            var ex = Assert.Throws<ProtocolException>(() =>
                Asset.HandleCommand(new JObject
                {
                    ["action"] = "deps",
                    ["path"] = "Assets/NonExistent/Fake.asset"
                }));

            Assert.That(ex.Code, Is.EqualTo(ErrorCode.InvalidParams));
        }

        /// <summary>
        /// refs アクションが有効なアセットパスで正常に動作すること。
        /// AssetPathExists が存在しない Unity 2022.3 でもコンパイル・実行できることを保証する。
        /// </summary>
        [Test]
        public void HandleCommand_Refs_ValidAsset_ReturnsReferencers()
        {
            var actual = Asset.HandleCommand(new JObject
            {
                ["action"] = "refs",
                ["path"] = TempAssetPath
            });

            Assert.That(actual["path"]?.Value<string>(), Is.EqualTo(TempAssetPath));
        }

        /// <summary>
        /// refs アクションが存在しないパスで InvalidParams をスローすること。
        /// バージョンに依存しない存在チェックの動作を検証する。
        /// </summary>
        [Test]
        public void HandleCommand_Refs_NonExistentAsset_ThrowsInvalidParams()
        {
            var ex = Assert.Throws<ProtocolException>(() =>
                Asset.HandleCommand(new JObject
                {
                    ["action"] = "refs",
                    ["path"] = "Assets/NonExistent/Fake.asset"
                }));

            Assert.That(ex.Code, Is.EqualTo(ErrorCode.InvalidParams));
        }

        /// <summary>
        /// AssetDatabase.AssetPathExists の有無が Unity バージョンと一致すること。
        /// Unity 6 以降では存在し、2022.3 では存在しないことをリフレクションで検証する。
        /// #if ディレクティブの分岐が正しいことの裏付けになる。
        /// </summary>
        [Test]
        public void AssetPathExists_Availability_MatchesUnityVersion()
        {
            var method = typeof(AssetDatabase).GetMethod(
                "AssetPathExists",
                BindingFlags.Public | BindingFlags.Static,
                null,
                new[] { typeof(string) },
                null);

#if UNITY_6000_0_OR_NEWER
            Assert.That(method, Is.Not.Null);
#else
            Assert.That(method, Is.Null);
#endif
        }
    }
}
