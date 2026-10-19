#nullable enable
using System;
using System.IO;
using System.Reflection;
using HarmonyLib;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace Thorkell.Compat;

public sealed class IsolationException : Exception
{
    public IsolationException(string message) : base(message) { }
}

// 봇·테스트 클라이언트가 사람의 세이브·클라우드·설정·로그를 건드리지 못하게 한다.
// 하나라도 실패하면 예외를 던지고, 호출한 쪽은 게임을 즉시 끈다(fail-closed).
// 사람의 실제 호스트(Thorkell.Host)에서는 부르지 않는다: 그 게임은 진짜 세이브를 써야 한다.
internal static class Isolation
{
    public const string MarkerName = "thorkell-runtime.json";

    static readonly string[] PlatformPrefsWrites = { "SetFloat", "SetInt", "SetString", "SetBool", "DeleteKey", "DeleteAll", "Save" };
    static readonly string[] PlayerPrefsWrites = { "SetFloat", "SetInt", "SetString", "DeleteKey", "DeleteAll", "Save" };

    static string? expectedSaves;

    // 저장소 초기화 직전 검사를 통과했는가. 세이브를 읽거나 쓰는 일(접속, 월드 생성)은 이게 true일 때만 한다.
    public static bool Verified { get; private set; }

    // 반환값은 런타임 루트(<root>/Valheim.app/Contents가 Application.dataPath).
    // 플러그인 Awake는 플랫폼 초기화(PlatformInitializer, BeforeSceneLoad)보다 먼저라서 클라우드 상태를 아직 물을 수 없다.
    // 그래서 여기서는 패치만 걸고, 확인은 저장소 초기화 직전(BeforeSaveData)에 한다.
    public static string Enforce(Harmony harmony, string expectedRole)
    {
        var contents = Path.GetFullPath(Application.dataPath);
        var app = Directory.GetParent(contents) ?? throw new IsolationException("no app bundle above " + contents);
        var root = app.Parent?.FullName ?? throw new IsolationException("no runtime root above " + app.FullName);
        var marker = Path.Combine(root, MarkerName);
        if (!File.Exists(marker))
            throw new IsolationException("runtime marker missing: " + marker);
        var role = (string?)JObject.Parse(File.ReadAllText(marker))["role"];
        if (role != expectedRole)
            throw new IsolationException("runtime role is " + role + ", expected " + expectedRole);

        var skip = new HarmonyMethod(typeof(Isolation).GetMethod(nameof(Skip), BindingFlags.NonPublic | BindingFlags.Static));
        var no = new HarmonyMethod(typeof(Isolation).GetMethod(nameof(False), BindingFlags.NonPublic | BindingFlags.Static));

        // 클라우드: FileHelpers의 작은 getter는 인라인될 수 있어서 Steam 구현의 가상 getter를 막는다.
        var steamCloud = Type.GetType("Splatform.Steam.SteamCloud, Splatform.Steam")
            ?? throw new IsolationException("Splatform.Steam.SteamCloud not found");
        harmony.Patch(AccessTools.PropertyGetter(steamCloud, "IsEnabled") ?? throw new IsolationException("SteamCloud.IsEnabled missing"), prefix: no);

        // prefs: 같은 bundle id라 사람의 plist를 공유한다. 읽기는 허용하고 쓰기만 막는다.
        foreach (var name in PlatformPrefsWrites)
            foreach (var method in Methods(typeof(PlatformPrefs), name))
                harmony.Patch(method, prefix: skip);
        foreach (var name in PlayerPrefsWrites)
            foreach (var method in Methods(typeof(PlayerPrefs), name))
                harmony.Patch(method, prefix: skip);

        // 로그 심볼릭 링크는 persistentDataPath(사람 쪽)에 만들어지므로 건너뛴다. 봇 로그는 -logFile로 분리한다.
        foreach (var method in Methods(AccessTools.TypeByName("CustomLogger"), "SetupSymbolicLink"))
            harmony.Patch(method, prefix: skip);

        expectedSaves = Path.GetFullPath(Path.Combine(root, "saves"));
        Utils.SetSaveDataPath(expectedSaves);

        var storageInit = AccessTools.Method(typeof(PlatformInitializer), "InitializeSaveDataStorage")
            ?? throw new IsolationException("PlatformInitializer.InitializeSaveDataStorage missing");
        harmony.Patch(storageInit, prefix: new HarmonyMethod(typeof(Isolation).GetMethod(nameof(BeforeSaveData), BindingFlags.NonPublic | BindingFlags.Static)));
        return root;
    }

    // 플랫폼이 올라온 뒤, 클라우드 저장소를 마운트하기 직전이다. 실패하면 저장소 초기화를 건너뛰고 게임을 끈다.
    static bool BeforeSaveData()
    {
        string? problem = null;
        if (FileHelpers.CloudStorageSupportedAndEnabled)
            problem = "cloud storage still enabled after patch";
        else if (Path.GetFullPath(Utils.GetSaveDataPath(FileHelpers.FileSource.Local)) != expectedSaves)
            problem = "save path is " + Utils.GetSaveDataPath(FileHelpers.FileSource.Local) + ", expected " + expectedSaves;
        if (problem != null)
        {
            Debug.LogError("THORKELL: isolation check failed before save data init, quitting: " + problem);
            Application.Quit(2);
            return false;
        }
        Verified = true;
        Debug.Log("THORKELL: isolation verified (cloud off, saves at " + expectedSaves + ")");
        return true;
    }

    // 같은 이름의 오버로드를 모두 돌려준다. 하나도 없으면 실패다.
    static System.Collections.Generic.List<MethodInfo> Methods(Type? type, string name)
    {
        if (type == null)
            throw new IsolationException("type missing for " + name);
        var found = AccessTools.GetDeclaredMethods(type).FindAll(m => m.Name == name);
        if (found.Count == 0)
            throw new IsolationException(type.Name + "." + name + " missing");
        return found;
    }

    static bool Skip() => false;

    static bool False(ref bool __result)
    {
        __result = false;
        return false;
    }
}
