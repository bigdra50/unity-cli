using System;
using System.Reflection;
using NUnit.Framework;

namespace Game.Tests.Editor
{
    /// <summary>
    /// Asset.cs と Component.cs に重複する FindType 実装の不一致を検証するテスト。
    ///
    /// 問題:
    /// - Asset.FindType (Asset.cs:273): Type.GetType を呼ばず、直接アセンブリ走査
    /// - Component.FindType (Component.cs:558): 先に Type.GetType を呼び、その後アセンブリ走査
    /// - Asset.FindType は bare catch だが、Component.FindType は ReflectionTypeLoadException のみキャッチ
    ///
    /// 同じ型名に対して異なる結果を返す可能性がある。
    /// </summary>
    [TestFixture]
    public class FindTypeConsistencyTests
    {
        private MethodInfo _assetFindType;
        private MethodInfo _componentFindType;

        [OneTimeSetUp]
        public void OneTimeSetUp()
        {
            // Asset.FindType は private static なのでリフレクションでアクセス
            var assetType = typeof(UnityBridge.Tools.Asset);
            _assetFindType = assetType.GetMethod("FindType",
                BindingFlags.NonPublic | BindingFlags.Static);

            var componentType = typeof(UnityBridge.Tools.Component);
            _componentFindType = componentType.GetMethod("FindType",
                BindingFlags.NonPublic | BindingFlags.Static);

            Assert.That(_assetFindType, Is.Not.Null,
                "Asset.FindType メソッドが見つからない");
            Assert.That(_componentFindType, Is.Not.Null,
                "Component.FindType メソッドが見つからない");
        }

        private Type InvokeAssetFindType(string typeName)
        {
            return (Type)_assetFindType.Invoke(null, new object[] { typeName });
        }

        private Type InvokeComponentFindType(string typeName)
        {
            return (Type)_componentFindType.Invoke(null, new object[] { typeName });
        }

        /// <summary>
        /// 完全修飾名での検索結果が一致することを確認。
        /// 両実装とも assembly.GetType で見つかるため一致するはず。
        /// </summary>
        [Test]
        public void FindType_FullyQualifiedName_BothReturnSameType()
        {
            const string typeName = "UnityEngine.Transform";

            var assetResult = InvokeAssetFindType(typeName);
            var componentResult = InvokeComponentFindType(typeName);

            Assert.That(assetResult, Is.Not.Null, "Asset.FindType が null を返した");
            Assert.That(componentResult, Is.Not.Null, "Component.FindType が null を返した");
            Assert.That(assetResult, Is.EqualTo(componentResult),
                "同一の完全修飾名に対して異なる型を返した");
        }

        /// <summary>
        /// 短い型名での検索結果が一致することを確認。
        /// "Transform" のような短い名前で検索した場合、
        /// アセンブリの列挙順序により結果が異なる可能性がある。
        /// </summary>
        [Test]
        public void FindType_ShortName_BothReturnSameType()
        {
            const string typeName = "Transform";

            var assetResult = InvokeAssetFindType(typeName);
            var componentResult = InvokeComponentFindType(typeName);

            Assert.That(assetResult, Is.Not.Null, "Asset.FindType が null を返した");
            Assert.That(componentResult, Is.Not.Null, "Component.FindType が null を返した");
            Assert.That(assetResult, Is.EqualTo(componentResult),
                $"短い名前 '{typeName}' に対して異なる型を返した: " +
                $"Asset={assetResult.FullName}, Component={componentResult.FullName}");
        }

        /// <summary>
        /// Component.FindType は Type.GetType を最初に呼ぶが Asset.FindType は呼ばない。
        /// Type.GetType は AssemblyQualifiedName でないと mscorlib/System 以外の型を見つけられない。
        /// この差異により、特定の型名で結果が分岐する可能性を検証。
        ///
        /// Type.GetType("System.String") は成功するが、
        /// Type.GetType("UnityEngine.Transform") は null を返す（アセンブリ修飾なし）。
        /// 両実装とも最終的にアセンブリ走査で見つけるため、結果は同じになるはず。
        /// </summary>
        [Test]
        public void FindType_SystemType_BothReturnSameType()
        {
            const string typeName = "System.String";

            var assetResult = InvokeAssetFindType(typeName);
            var componentResult = InvokeComponentFindType(typeName);

            Assert.That(assetResult, Is.Not.Null);
            Assert.That(componentResult, Is.Not.Null);
            Assert.That(assetResult, Is.EqualTo(componentResult));
        }

        /// <summary>
        /// 存在しない型名に対して、両実装がともに null を返すことを確認。
        /// </summary>
        [Test]
        public void FindType_NonExistentType_BothReturnNull()
        {
            const string typeName = "This.Type.Does.Not.Exist.Anywhere.XYZ123";

            var assetResult = InvokeAssetFindType(typeName);
            var componentResult = InvokeComponentFindType(typeName);

            Assert.That(assetResult, Is.Null);
            Assert.That(componentResult, Is.Null);
        }

        /// <summary>
        /// 例外ハンドリングの差異テスト。
        /// Asset.FindType は bare catch (すべての例外をキャッチ)
        /// Component.FindType は ReflectionTypeLoadException のみキャッチ
        ///
        /// ReflectionTypeLoadException 以外の例外（例: TypeLoadException）が発生した場合、
        /// Component.FindType は例外を伝播させるが Asset.FindType は握りつぶす。
        /// この差異は直接テストしづらいが、挙動の違いとして文書化する。
        /// </summary>
        [Test]
        public void FindType_ExceptionHandling_DifferenceDocumented()
        {
            // Asset.FindType:  catch { } → すべての例外を無視
            // Component.FindType: catch (ReflectionTypeLoadException) { } → RTLEのみ無視
            //
            // この差異は以下の状況で顕在化する:
            // - 破損したアセンブリが読み込まれている場合
            // - assembly.GetTypes() が ReflectionTypeLoadException 以外を投げる場合
            //
            // 直接的な再現は困難だが、コードレビューで確認できる差異として記録

            // 両実装が同じ「正常な」入力に対して同じ結果を返すことだけ確認
            var testTypes = new[]
            {
                "UnityEngine.GameObject",
                "UnityEngine.Camera",
                "UnityEngine.Rigidbody",
                "UnityEditor.Editor",
                "System.Int32",
            };

            foreach (var typeName in testTypes)
            {
                var assetResult = InvokeAssetFindType(typeName);
                var componentResult = InvokeComponentFindType(typeName);

                Assert.That(assetResult, Is.EqualTo(componentResult),
                    $"型 '{typeName}' に対して異なる結果: " +
                    $"Asset={assetResult?.FullName ?? "null"}, " +
                    $"Component={componentResult?.FullName ?? "null"}");
            }
        }

        /// <summary>
        /// 同一の短い名前が複数アセンブリに存在する場合の挙動を検証。
        /// アセンブリ走査順序が不定なら、返される型が実行ごとに異なる可能性がある。
        /// 両実装が同じ順序で走査するため結果は一致するはずだが、
        /// Component.FindType の Type.GetType 先行チェックが影響する可能性がある。
        /// </summary>
        [Test]
        public void FindType_AmbiguousShortName_BothReturnSameResult()
        {
            // "Object" は System.Object と UnityEngine.Object の両方が存在
            const string typeName = "Object";

            var assetResult = InvokeAssetFindType(typeName);
            var componentResult = InvokeComponentFindType(typeName);

            // 両方とも非null（いずれかの Object 型が見つかる）
            Assert.That(assetResult, Is.Not.Null,
                "Asset.FindType が 'Object' を見つけられなかった");
            Assert.That(componentResult, Is.Not.Null,
                "Component.FindType が 'Object' を見つけられなかった");

            // 問題: 両実装が異なる型を返す可能性がある
            // Component.FindType は Type.GetType("Object") を先に試すが、これは null を返す
            // その後アセンブリ走査に入るため、走査順序次第で結果が変わる
            Assert.That(assetResult, Is.EqualTo(componentResult),
                $"曖昧な短い名前 'Object' に対して異なる型を返した: " +
                $"Asset={assetResult.FullName}, Component={componentResult.FullName}");
        }
    }
}
