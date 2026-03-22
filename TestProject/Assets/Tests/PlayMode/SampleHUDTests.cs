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

            // Wait for InitAfterLayout coroutine
            yield return null;
            yield return null;

            _root = _uiDocument.rootVisualElement;
            Assert.IsNotNull(_root, "Root visual element should be initialized");
        }

        [TearDown]
        public void TearDown()
        {
            Object.Destroy(_hudObject);
        }

        #region Menu Button Tests

        [UnityTest]
        public IEnumerator BtnContinue_ShowsLoadingToast()
        {
            var btn = _root.Q("BtnContinue");
            Assert.IsNotNull(btn);

            Click(btn);
            yield return null;

            var toast = _root.Q<Label>("ToastMessage");
            Assert.AreEqual("Loading save data...", toast.text);
        }

        [UnityTest]
        public IEnumerator BtnNewGame_ResetsProfile()
        {
            var btn = _root.Q("BtnNewGame");
            Assert.IsNotNull(btn);

            Click(btn);
            yield return null;

            var profileName = _root.Q<Label>("ProfileName");
            Assert.AreEqual("Aria  Lv.1", profileName.text);

            var toast = _root.Q<Label>("ToastMessage");
            Assert.AreEqual("Chapter 1 selected", toast.text);
        }

        [UnityTest]
        public IEnumerator BtnSettings_ShowsSettingsToast()
        {
            var btn = _root.Q("BtnSettings");
            Assert.IsNotNull(btn);

            Click(btn);
            yield return null;

            var toast = _root.Q<Label>("ToastMessage");
            Assert.AreEqual("Settings opened", toast.text);
        }

        #endregion

        #region Chapter Selection Tests

        [UnityTest]
        public IEnumerator Chapter1_SelectsAndShowsToast()
        {
            var chapter = _root.Q("Chapter1");
            Assert.IsNotNull(chapter);

            Click(chapter);
            yield return null;

            var toast = _root.Q<Label>("ToastMessage");
            Assert.AreEqual("Chapter 1 selected", toast.text);
            Assert.IsTrue(chapter.ClassListContains("card-selected"));
        }

        [UnityTest]
        public IEnumerator Chapter3_ShowsLockedToast()
        {
            var chapter = _root.Q("Chapter3");
            Assert.IsNotNull(chapter);

            Click(chapter);
            yield return null;

            var toast = _root.Q<Label>("ToastMessage");
            Assert.AreEqual("Chapter III is locked", toast.text);
            Assert.IsFalse(chapter.ClassListContains("card-selected"));
        }

        #endregion

        #region Tab Tests

        [UnityTest]
        public IEnumerator TabQuest_ActivatesAndShowsToast()
        {
            var tabQuest = _root.Q("TabQuest");
            var tabHome = _root.Q("TabHome");
            Assert.IsNotNull(tabQuest);
            Assert.IsNotNull(tabHome);

            Click(tabQuest);
            yield return null;

            Assert.IsTrue(tabQuest.ClassListContains("tab-active"));
            Assert.IsFalse(tabHome.ClassListContains("tab-active"));

            var toast = _root.Q<Label>("ToastMessage");
            Assert.AreEqual("Quest tab", toast.text);
        }

        #endregion

        #region Smoke Test

        [UnityTest]
        public IEnumerator AllButtons_ClickableWithoutErrors()
        {
            var buttons = new[]
            {
                "BtnContinue", "BtnNewGame", "BtnSettings",
                "Chapter1", "Chapter2", "Chapter3",
                "TabHome", "TabQuest", "TabCodex", "TabConfig"
            };

            foreach (var name in buttons)
            {
                var element = _root.Q(name);
                Assert.IsNotNull(element, $"{name} should exist");
                Click(element);
                yield return null;
            }

            // If we reach here without exceptions, all buttons are clickable
            LogAssert.NoUnexpectedReceived();
        }

        #endregion

        private static void Click(VisualElement element)
        {
            using var evt = new NavigationSubmitEvent { target = element };
            element.SendEvent(evt);
        }
    }
}
