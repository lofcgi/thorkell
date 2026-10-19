using System;
using System.IO;
using System.Linq;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using Newtonsoft.Json.Linq;
using Thorkell.Compat;
using UnityEngine;

namespace Thorkell.Host;

// 사람의 호스트 클라이언트 전용. `-thorkell-host`로 띄운 Thorkell 런타임(표시 파일이 있는 복제본)에서만 켜진다.
// 하는 일: 봇이 들어올 127.0.0.1 전용 Steam 리스너를 연다. 사람의 캐릭터를 대신 움직이지 않는다.
// 리허설 런타임(host-rehearsal)에서는 사람의 실제 세이브·클라우드·설정을 건드리지 않게 격리를 건다.
[BepInPlugin(Guid, "Thorkell Host", PluginVersion)]
public sealed class HostPlugin : BaseUnityPlugin
{
    public const string Guid = "thorkell.host";
    public const string PluginVersion = "0.1.0";

    public static HostPlugin Instance { get; private set; }
    internal static ManualLogSource Log { get; private set; }

    internal ConfigEntry<int> ListenerPort;
    internal ConfigEntry<string> AllowedWorlds;
    internal ConfigEntry<string> Language;

    Harmony harmony;

    void Awake()
    {
        if (!Environment.GetCommandLineArgs().Contains("-thorkell-host"))
        {
            enabled = false;
            return;
        }
        Instance = this;
        Log = Logger;

        var role = RuntimeRole(out var root);
        if (role == null)
        {
            LoopbackListener.State = "not_a_thorkell_runtime";
            Logger.LogError("THORKELL: no " + Isolation.MarkerName + " next to this game; host listener stays closed");
            return;
        }
        harmony = new Harmony(Guid);
        if (role == "host-rehearsal")
        {
            try
            {
                Isolation.Enforce(harmony, role);
            }
            catch (Exception e)
            {
                Logger.LogError("THORKELL: rehearsal isolation failed, quitting: " + e);
                Application.Quit(2);
                return;
            }
        }
        HostStatus.Init(root);
        LeaderChat.Init(root);

        var gate = GameApi.CheckBuild(out var found);
        if (!gate.Ok)
        {
            LoopbackListener.State = "untested_build";
            Logger.LogError("THORKELL: untested game build, host listener stays closed: " + string.Join("; ", gate.Problems));
            return;
        }

        Config.SaveOnConfigSet = false;
        ListenerPort = Config.Bind("Listener", "Port", 54880, "127.0.0.1 port for the bot client");
        AllowedWorlds = Config.Bind("Listener", "Worlds", "", "comma-separated world names where the listener may open");
        Language = Config.Bind("Game", "Language", "", "the game language Thorkell plays in (English, Korean); the leader sees the same names");
        try
        {
            GameLanguage.Apply(harmony, Language.Value);
        }
        catch (Exception e)
        {
            LoopbackListener.State = "language_failed";
            Logger.LogError("THORKELL: game language failed, host listener stays closed: " + e);
            return;
        }

        CrossplayPeerShim.Install(harmony, Logger);
        harmony.PatchAll(typeof(LoopbackListener));
        harmony.PatchAll(typeof(LeaderChat));
        harmony.PatchAll(typeof(ChatNames));
        Logger.LogInfo("THORKELL: host loaded on Valheim " + found.Game + " (network " + found.Network +
                       "), crossplay shim " + (CrossplayPeerShim.Ready ? "ready" : "unavailable"));
    }

    float nextPositions;

    // 리더가 게임에 들어오고 나가는 것과, 리더·토르켈의 위치(1초마다)를 상태 파일에 반영한다.
    void Update()
    {
        var local = Player.m_localPlayer;
        HostStatus.SetLeader(local != null ? local.GetPlayerName() : null);
        if (Time.realtimeSinceStartup < nextPositions)
            return;
        nextPositions = Time.realtimeSinceStartup + 1f;
        HostStatus.SetPositions(local != null ? local.transform.position : (Vector3?)null, LoopbackListener.BotPeer());
    }

    // 런타임 표시 파일의 역할(host, host-rehearsal, host-test). Thorkell 런타임이 아니면 null.
    static string RuntimeRole(out string root)
    {
        root = null;
        var app = Directory.GetParent(Path.GetFullPath(Application.dataPath));
        var candidate = app?.Parent?.FullName;
        if (candidate == null || !File.Exists(Path.Combine(candidate, Isolation.MarkerName)))
            return null;
        root = candidate;
        return (string)JObject.Parse(File.ReadAllText(Path.Combine(candidate, Isolation.MarkerName)))["role"];
    }

    internal bool WorldAllowed(string world) =>
        AllowedWorlds.Value.Split(',').Select(w => w.Trim()).Any(w => w.Length > 0 && w == world);

    void OnDestroy()
    {
        LoopbackListener.Close();
        harmony?.UnpatchSelf();
    }
}
