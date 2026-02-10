using System.Collections;
using UnityEngine;
using UnityEngine.UIElements;

[RequireComponent(typeof(UIDocument))]
public class SampleHUDController : MonoBehaviour
{
    private VisualElement _root;
    private Label _profileSub;
    private Label _progressPercent;
    private VisualElement _xpFill;
    private VisualElement _toast;
    private Label _toastMessage;
    private VisualElement[] _chapters;
    private VisualElement[] _tabs;
    private int _selectedChapter;

    private void Awake()
    {
        var uiDocument = GetComponent<UIDocument>();

        if (uiDocument.panelSettings == null)
        {
            var ps = Resources.Load<PanelSettings>("SamplePanelSettings");
            if (ps != null)
            {
                ps.scaleMode = PanelScaleMode.ScaleWithScreenSize;
                ps.screenMatchMode = PanelScreenMatchMode.MatchWidthOrHeight;
                ps.match = 0.5f;
                ps.referenceResolution = new Vector2Int(1920, 1080);
                uiDocument.panelSettings = ps;
            }
        }

        if (uiDocument.visualTreeAsset == null)
        {
            var vta = Resources.Load<VisualTreeAsset>("SampleHUD");
            if (vta != null)
                uiDocument.visualTreeAsset = vta;
        }
    }

    private void OnEnable()
    {
        StartCoroutine(InitAfterLayout());
    }

    private IEnumerator InitAfterLayout()
    {
        yield return null;

        var uiDocument = GetComponent<UIDocument>();
        _root = uiDocument.rootVisualElement;
        if (_root == null) yield break;

        _profileSub = _root.Q<Label>("ProfileSub");
        _progressPercent = _root.Q<Label>("ProgressPercent");
        _xpFill = _root.Q("XpFill");
        _toast = _root.Q("Toast");
        _toastMessage = _root.Q<Label>("ToastMessage");

        SetupChapters();
        SetupMenu();
        SetupTabs();
        UpdateClock();
    }

    private void Update()
    {
        UpdateClock();
    }

    private void UpdateClock()
    {
        var timeLabel = _root?.Q<Label>("StatusTime");
        if (timeLabel != null)
            timeLabel.text = System.DateTime.Now.ToString("HH:mm");
    }

    private void SetupChapters()
    {
        _chapters = new[]
        {
            _root.Q("Chapter1"),
            _root.Q("Chapter2"),
            _root.Q("Chapter3")
        };
        _selectedChapter = 0;

        for (var i = 0; i < _chapters.Length; i++)
        {
            var index = i;
            _chapters[i].RegisterCallback<ClickEvent>(_ => SelectChapter(index));
        }
    }

    private void SelectChapter(int index)
    {
        if (index == 2)
        {
            ShowToast("Chapter III is locked");
            return;
        }

        for (var i = 0; i < _chapters.Length; i++)
        {
            _chapters[i].EnableInClassList("card-selected", i == index);
        }
        _selectedChapter = index;

        var chapterNames = new[] { "I - Awakening", "II - Shadow Rift", "III - Final Dawn" };
        if (_profileSub != null)
            _profileSub.text = $"Chapter {chapterNames[index]}  |  12:34:56";

        ShowToast($"Chapter {index + 1} selected");
    }

    private void SetupMenu()
    {
        var btnContinue = _root.Q("BtnContinue");
        var btnNewGame = _root.Q("BtnNewGame");
        var btnSettings = _root.Q("BtnSettings");

        btnContinue?.RegisterCallback<ClickEvent>(_ => OnContinue());
        btnNewGame?.RegisterCallback<ClickEvent>(_ => OnNewGame());
        btnSettings?.RegisterCallback<ClickEvent>(_ => OnSettings());

        RegisterPressEffect(btnContinue);
        RegisterPressEffect(btnNewGame);
        RegisterPressEffect(btnSettings);
    }

    private void RegisterPressEffect(VisualElement element)
    {
        if (element == null) return;
        element.RegisterCallback<PointerDownEvent>(_ => element.AddToClassList("btn-pressed"));
        element.RegisterCallback<PointerUpEvent>(_ => element.RemoveFromClassList("btn-pressed"));
        element.RegisterCallback<PointerLeaveEvent>(_ => element.RemoveFromClassList("btn-pressed"));
    }

    private void OnContinue()
    {
        ShowToast("Loading save data...");
        StartCoroutine(AnimateProgress(65, 100));
    }

    private void OnNewGame()
    {
        ShowToast("New game started");
        StartCoroutine(AnimateProgress(65, 0));

        if (_profileSub != null)
            _profileSub.text = "Chapter I - Awakening  |  00:00:00";

        var name = _root.Q<Label>("ProfileName");
        if (name != null)
            name.text = "Aria  Lv.1";

        SelectChapter(0);
    }

    private void OnSettings()
    {
        ShowToast("Settings opened");
    }

    private IEnumerator AnimateProgress(int from, int to)
    {
        var duration = 0.5f;
        var elapsed = 0f;

        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            var t = Mathf.Clamp01(elapsed / duration);
            var current = Mathf.RoundToInt(Mathf.Lerp(from, to, t));
            SetProgress(current);
            yield return null;
        }
        SetProgress(to);
    }

    private void SetProgress(int percent)
    {
        if (_xpFill != null)
            _xpFill.style.width = new Length(percent, LengthUnit.Percent);
        if (_progressPercent != null)
            _progressPercent.text = $"{percent}%";
    }

    private void SetupTabs()
    {
        _tabs = new[]
        {
            _root.Q("TabHome"),
            _root.Q("TabQuest"),
            _root.Q("TabCodex"),
            _root.Q("TabConfig")
        };

        for (var i = 0; i < _tabs.Length; i++)
        {
            var index = i;
            _tabs[i].RegisterCallback<ClickEvent>(_ => SelectTab(index));
        }
    }

    private void SelectTab(int index)
    {
        var tabNames = new[] { "Home", "Quest", "Codex", "Config" };

        for (var i = 0; i < _tabs.Length; i++)
        {
            var isActive = i == index;
            _tabs[i].EnableInClassList("tab-active", isActive);
            var label = _tabs[i].Q<Label>();
            label?.EnableInClassList("tab-label-active", isActive);
        }

        ShowToast($"{tabNames[index]} tab");
    }

    private void ShowToast(string message)
    {
        StopCoroutine(nameof(HideToastAfterDelay));

        if (_toast == null || _toastMessage == null) return;
        _toastMessage.text = message;
        _toast.RemoveFromClassList("hidden");

        StartCoroutine(nameof(HideToastAfterDelay));
    }

    private IEnumerator HideToastAfterDelay()
    {
        yield return new WaitForSeconds(1.5f);
        _toast?.AddToClassList("hidden");
    }
}
