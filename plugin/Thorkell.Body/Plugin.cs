using System;
using System.IO;
using System.Linq;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using Thorkell.Body.Link;
using Thorkell.Compat;
using Thorkell.Core;
using UnityEngine;

namespace Thorkell.Body;

// 봇 클라이언트 전용. `-thorkell-body` 없이 뜬 게임(사람의 게임)에서는 아무것도 하지 않는다.
[BepInPlugin(Guid, "Thorkell Body", PluginVersion)]
public sealed class BodyPlugin : BaseUnityPlugin
{
    public const string Guid = "thorkell.body";
    public const string PluginVersion = "0.2.0";

    public static BodyPlugin Instance { get; private set; }
    public static bool Active { get; private set; }

    internal ConfigEntry<string> JoinHost;
    internal ConfigEntry<int> JoinPort;
    internal ConfigEntry<string> JoinPassword;
    internal ConfigEntry<string> CharacterFile;
    internal ConfigEntry<string> CharacterName;
    internal ConfigEntry<string> LeaderName;
    internal ConfigEntry<bool> ShowOnMap;
    internal ConfigEntry<int> BridgePort;
    internal ConfigEntry<string> BridgeToken;
    internal ConfigEntry<string> Language;

    internal ManualLogSource Log => Logger;
    public string RuntimeRoot { get; private set; }
    public string State { get; private set; } = "starting";

    Harmony harmony;
    BodyLink link;
    float started;
    bool joinRequested;
    bool sharedOnMap;
    float nextQuitCheck;

    void Awake()
    {
        if (!Environment.GetCommandLineArgs().Contains("-thorkell-body"))
        {
            enabled = false;
            return;
        }
        Instance = this;

        harmony = new Harmony(Guid);
        try
        {
            RuntimeRoot = Isolation.Enforce(harmony, "body");
        }
        catch (Exception e)
        {
            Logger.LogError("THORKELL: isolation failed, quitting bot client: " + e);
            Application.Quit(2);
            return;
        }

        var gate = GameApi.CheckBuild(out var build);
        if (!gate.Ok)
        {
            Logger.LogError("THORKELL: untested game build, quitting bot client: " + string.Join("; ", gate.Problems));
            Application.Quit(3);
            return;
        }

        Config.SaveOnConfigSet = false;
        JoinHost = Config.Bind("Join", "Host", "127.0.0.1", "loopback address of the Thorkell.Host listener");
        JoinPort = Config.Bind("Join", "Port", 54880, "Thorkell.Host loopback listener port");
        JoinPassword = Config.Bind("Join", "Password", "", "server password (secret, never logged)");
        CharacterFile = Config.Bind("Body", "CharacterFile", "thorkell", "character file name under saves/characters_local");
        CharacterName = Config.Bind("Body", "CharacterName", "Thorkell", "display name for a newly created character");
        LeaderName = Config.Bind("Body", "LeaderName", "", "the human leader's character name");
        ShowOnMap = Config.Bind("Body", "ShowOnMap", true, "share the bot's position on other players' maps so the leader can find it");
        BridgePort = Config.Bind("Bridge", "Port", 47811, "brain bridge port on 127.0.0.1");
        BridgeToken = Config.Bind("Bridge", "Token", "", "per-run bridge token (secret, never logged)");
        Language = Config.Bind("Game", "Language", "", "the game language Thorkell plays in (English, Korean); the brain reads and speaks it");
        try
        {
            GameLanguage.Apply(harmony, Language.Value);
        }
        catch (Exception e)
        {
            Logger.LogError("THORKELL: game language failed, quitting bot client: " + e);
            Application.Quit(2);
            return;
        }

        // 봇 창이 포커스를 잃어도 계속 돌고, 소리는 내지 않는다. 설정은 메모리에서만 바꾸고 저장하지 않는다.
        Application.runInBackground = true;
        Application.targetFrameRate = 30;
        QualitySettings.vSyncCount = 0;
        AudioListener.volume = 0f;

        harmony.PatchAll(typeof(Actions.Motor));
        harmony.PatchAll(typeof(Actions.PlaceAim));
        harmony.PatchAll(typeof(Events.Hooks));
        harmony.PatchAll(typeof(Events.OwnHits));
        harmony.PatchAll(typeof(Events.OwnChatName));
        Active = true;
        started = Time.realtimeSinceStartup;
        State = "waiting_for_menu";

        if (BridgeToken.Value.Length == 64)
            link = new BodyLink(this, build, BridgePort.Value, BridgeToken.Value);
        else
            Logger.LogWarning("THORKELL: no bridge token configured; body runs without a brain");
        Logger.LogInfo("THORKELL: body ready on Valheim " + build.Game + " (network " + build.Network + "), runtime " + RuntimeRoot);
    }

    void Update()
    {
        if (!Active)
            return;
        // 봇 게임은 소리를 내지 않는다. 시작할 때 0으로 해 둬도 게임(AudioMan.Start, 컷신)이 다시 1로 올리므로 매 프레임 지킨다.
        if (AudioListener.volume != 0f)
            AudioListener.volume = 0f;
        if (Time.realtimeSinceStartup >= nextQuitCheck)
        {
            nextQuitCheck = Time.realtimeSinceStartup + 1f;
            if (File.Exists(Path.Combine(RuntimeRoot, "quit.txt")))
            {
                SaveAndQuit();
                return;
            }
        }
        if (!joinRequested && Isolation.Verified && FejdStartup.instance != null && ObjectDB.instance != null && Time.realtimeSinceStartup - started > 5f)
        {
            joinRequested = true;
            try
            {
                Join.Start(this);
                State = "joining";
                Logger.LogInfo("THORKELL: joining " + JoinHost.Value + ":" + JoinPort.Value + " as " + CharacterFile.Value);
            }
            catch (Exception e)
            {
                State = "join_failed";
                Logger.LogError("THORKELL: join failed: " + e);
            }
        }
        if (State == "joining" && Player.m_localPlayer != null)
        {
            State = "in_world";
            Logger.LogInfo("THORKELL: spawned as " + Player.m_localPlayer.GetPlayerName() + " in " + ZNet.instance.GetWorldName());
        }
        // 사람이 지도에서 토르켈을 찾을 수 있게 지도의 '위치 공개'를 켠다. 지도 데이터를 읽을 때 저장된 값으로
        // 돌아갈 수 있어서 꺼져 있을 때마다 다시 켠다. 봇 캐릭터의 지도 데이터(격리된 세이브)에만 저장된다.
        if (State == "in_world" && ShowOnMap.Value && ZNet.instance != null && !ZNet.instance.IsReferencePositionPublic())
        {
            ZNet.instance.SetPublicReferencePosition(true);
            if (!sharedOnMap)
                Logger.LogInfo("THORKELL: position shared on the map");
            sharedOnMap = true;
        }
        link?.Update();
    }

    // 실행기(`thorkell play`)가 끝낼 때 런타임 루트에 quit.txt를 놓는다. 캐릭터를 로그아웃 지점과 함께 저장하고 종료한다.
    // 종료할 때 Unity가 공용 prefs에 쓰려는 것은 런타임 샌드박스가 막는다.
    void SaveAndQuit()
    {
        Active = false;
        if (Game.instance != null && Player.m_localPlayer != null)
            Game.instance.SavePlayerProfile(true);
        Logger.LogInfo("THORKELL: quit requested; character saved, quitting");
        Application.Quit();
    }

    void OnDestroy()
    {
        Active = false;
        link?.Dispose();
        harmony?.UnpatchSelf();
    }
}
