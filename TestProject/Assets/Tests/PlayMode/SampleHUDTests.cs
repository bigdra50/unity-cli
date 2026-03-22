using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.UIElements;

namespace Game.Tests.PlayMode
{
    [TestFixture]
    public class SampleHUDTests
    {
        private GameObject _hudObject;
        private UIDocument _uiDocument;
        private VisualElement _root;

        [UnitySetUp]
        public IEnumerator SetUp()
        {
            _hudObject = new GameObject("TestHUD");
            _hudObject.AddComponent<SampleHUDController>();
            _uiDocument = _hudObject.GetComponent<UIDocument>();

            yield return null; // Awake + OnEnable
            yield return null; // InitAfterLayout coroutine

            _root = _uiDocument.rootVisualElement;
            Assert.IsNotNull(_root, "Root visual element should be initialized");
        }

        [TearDown]
        public void TearDown()
        {
            Object.Destroy(_hudObject);
        }

        // --- Functional tests ---

        [UnityTest]
        public IEnumerator BtnContinue_ShowsLoadingSaveDataToast()
        {
            var btn = _root.Q("BtnContinue");
            Assert.IsNotNull(btn, "BtnContinue should exist");

            Click(btn);
            yield return null;

            var label = _root.Q<Label>("ToastMessage");
            Assert.AreEqual("Loading save data...", label.text);
        }

        [UnityTest]
        public IEnumerator BtnNewGame_ShowsNewGameStartedToast()
        {
            var btn = _root.Q("BtnNewGame");
            Assert.IsNotNull(btn, "BtnNewGame should exist");

            Click(btn);
            yield return null;

            var label = _root.Q<Label>("ToastMessage");
            Assert.AreEqual("New game started", label.text);
        }

        [UnityTest]
        public IEnumerator BtnSettings_ShowsSettingsOpenedToast()
        {
            var btn = _root.Q("BtnSettings");
            Assert.IsNotNull(btn, "BtnSettings should exist");

            Click(btn);
            yield return null;

            var label = _root.Q<Label>("ToastMessage");
            Assert.AreEqual("Settings opened", label.text);
        }

        // --- Smoke tests ---

        [UnityTest]
        public IEnumerator AllButtons_ClickableWithoutErrors()
        {
            var buttons = new[] { "BtnContinue", "BtnNewGame", "BtnSettings" };

            foreach (var name in buttons)
            {
                var element = _root.Q(name);
                Assert.IsNotNull(element, $"{name} should exist");
                Click(element);
                yield return null;
            }

            LogAssert.NoUnexpectedReceived();
        }

        [UnityTest]
        public IEnumerator AllTabs_ClickableWithoutErrors()
        {
            var tabs = new[] { "TabHome", "TabQuest", "TabCodex", "TabConfig" };

            foreach (var name in tabs)
            {
                var element = _root.Q(name);
                Assert.IsNotNull(element, $"{name} should exist");
                Click(element);
                yield return null;
            }

            LogAssert.NoUnexpectedReceived();
        }

        // --- Helper ---

        private static void Click(VisualElement element)
        {
            using var evt = ClickEvent.GetPooled();
            evt.target = element;
            element.panel.visualTree.SendEvent(evt);
        }
    }
}
