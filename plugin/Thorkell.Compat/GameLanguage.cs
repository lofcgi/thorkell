#nullable enable
using System;
using System.Reflection;
using HarmonyLib;
using UnityEngine;

namespace Thorkell.Compat;

// 토르켈이 플레이하는 언어로 게임을 띄운다. 두뇌는 몸이 보내는 이름(메뉴·이름표·인벤토리)을 그 언어로 읽고
// 같은 언어로 말한다. 게임은 시작할 때 사람의 prefs에서 언어를 읽는다(SetStartupLanguage). 그 자리에서
// 설정한 언어를 대신 불러오고, prefs에는 쓰지 않는다(SetLanguage는 prefs에 쓴다).
internal static class GameLanguage
{
    static string? wanted;

    // 사람에게 보여 주는 플러그인 글(HUD)과 게임에 이름이 없는 것(맨손)을 고르는 데 쓴다.
    public static bool English => wanted == "English";

    public static void Apply(Harmony harmony, string language)
    {
        if (string.IsNullOrEmpty(language))
            throw new ArgumentException("game language is not configured");
        wanted = language;
        var startup = AccessTools.Method(typeof(Localization), "SetStartupLanguage")
            ?? throw new MissingMethodException("Localization", "SetStartupLanguage");
        harmony.Patch(startup, prefix: new HarmonyMethod(typeof(GameLanguage).GetMethod(nameof(Startup), BindingFlags.NonPublic | BindingFlags.Static)));
        // 플러그인보다 먼저 언어를 불러왔으면 지금 바꾼다.
        var made = AccessTools.Field(typeof(Localization), "m_instance") ?? throw new MissingFieldException("Localization", "m_instance");
        if (made.GetValue(null) is Localization instance)
        {
            var clear = AccessTools.Method(typeof(Localization), "Clear") ?? throw new MissingMethodException("Localization", "Clear");
            clear.Invoke(instance, null);
            Load(instance);
        }
    }

    static bool Startup(Localization __instance)
    {
        Load(__instance);
        return false;
    }

    static void Load(Localization localization)
    {
        if (!localization.SetupLanguage(wanted))
            throw new InvalidOperationException("the game has no language " + wanted);
        Debug.Log("THORKELL: game language " + wanted);
    }
}
