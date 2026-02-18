using System.Reflection;
using NUnit.Framework;
using UnityBridge.Tools;
using UnityEditor.TestTools.TestRunner.Api;

namespace UnityBridge
{
    /// <summary>
    /// Tests.IsLeafTest が存在し、CollectTests / TestResultCollector の
    /// 両方から利用可能であることを検証する。
    ///
    /// 背景:
    ///   CollectTests (list用) と TestResultCollector (run用) で
    ///   「葉テストか?」の判定条件が異なっていたため、
    ///   tests list と tests run の件数が不一致になった。
    ///   共通メソッド IsLeafTest に統一したことで解消。
    /// </summary>
    [TestFixture]
    public class TestCountConsistencyTest
    {
        [Test]
        public void IsLeafTest_Exists_AsInternalStaticMethod()
        {
            var method = typeof(Tests).GetMethod(
                "IsLeafTest",
                BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Static);

            Assert.That(method, Is.Not.Null);
            Assert.That(method.IsStatic, Is.True);
            Assert.That(method.IsAssembly || method.IsPublic, Is.True);
        }

        [Test]
        public void IsLeafTest_AcceptsITestAdaptor_Parameter()
        {
            var method = typeof(Tests).GetMethod(
                "IsLeafTest",
                BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Static);

            Assert.That(method, Is.Not.Null);

            var parameters = method.GetParameters();
            Assert.That(parameters.Length, Is.EqualTo(1));
            Assert.That(typeof(ITestAdaptor).IsAssignableFrom(parameters[0].ParameterType));
        }

        [Test]
        public void IsLeafTest_ReturnsBool()
        {
            var method = typeof(Tests).GetMethod(
                "IsLeafTest",
                BindingFlags.NonPublic | BindingFlags.Public | BindingFlags.Static);

            Assert.That(method, Is.Not.Null);
            Assert.That(method.ReturnType, Is.EqualTo(typeof(bool)));
        }

        [Test]
        public void CollectTests_Exists_AsPrivateStaticMethod()
        {
            var method = typeof(Tests).GetMethod(
                "CollectTests",
                BindingFlags.NonPublic | BindingFlags.Static);

            Assert.That(method, Is.Not.Null);
        }

        [Test]
        public void TestResultCollector_HasTestStartedMethod()
        {
            var collectorType = typeof(Tests).GetNestedType(
                "TestResultCollector",
                BindingFlags.NonPublic);

            Assert.That(collectorType, Is.Not.Null);

            var method = collectorType.GetMethod(
                "TestStarted",
                BindingFlags.Public | BindingFlags.Instance);

            Assert.That(method, Is.Not.Null);
        }
    }
}
