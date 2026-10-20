using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using BepInEx;
using BepInEx.Configuration;
using HarmonyLib;
using Newtonsoft.Json.Linq;
using Thorkell.Compat;
using UnityEngine;

namespace Thorkell.NativeHarness;

// 실게임 시나리오 하네스. 테스트 런타임에만 설치된다.
//  - host: 격리된 일회용 월드를 열고(사람 역할 "Leader"), 봇이 들어오는지 본다.
//  - client: 봇 런타임에서 Thorkell.Body가 접속한 결과를 관찰한다(격리는 Body가 이미 걸었다).
// 결과는 런타임 루트에 파일로 남기고, 종료는 러너가 SIGKILL로 한다(정상 종료 시 Unity가 공용 prefs에 해상도를 쓴다).
[BepInPlugin("thorkell.harness", "Thorkell Native Harness", "0.1.0")]
public sealed partial class Harness : BaseUnityPlugin
{
    ConfigEntry<string> role, backend, world, seed, password, leaderName, botName, locations;
    Vector3? leaderLocation;
    bool farMoved;
    ConfigEntry<bool> existingWorld;
    ConfigEntry<int> timeoutSeconds;
    ConfigEntry<string> inventoryFixtures, worldFixtures, existingTargets, moveOffset;
    bool fixturesPlaced, moving, worldFixturesPending, fixturesSettling;
    readonly List<GameObject> spawnedFixtures = new List<GameObject>();
    readonly List<Vector3> spawnPoints = new List<Vector3>();
    readonly JArray placedFixtures = new JArray();
    float placeStarted, settleStarted, settledSince = -1f, placedRelief, leaderSiteRelief = -1f;
    string root;
    Harmony harmony;
    float started, nextPerf, teleportFirstTry = -1f;
    bool booted, finished, hostReady, peerSeen, clientReady;
    string phase = "start";
    readonly List<float> frames = new List<float>(4096);
    static Harness instance;

    void Awake()
    {
        if (!Environment.GetCommandLineArgs().Contains("-thorkell-harness"))
        {
            enabled = false;
            return;
        }
        instance = this;
        Config.SaveOnConfigSet = false;
        role = Config.Bind("Harness", "Role", "", "host | client");
        backend = Config.Bind("Harness", "Backend", "steam", "host backend: steam | playfab");
        world = Config.Bind("Harness", "World", "ThorkellLab", "disposable world name");
        seed = Config.Bind("Harness", "Seed", "ThorkellMeadows1", "world seed");
        existingWorld = Config.Bind("Harness", "ExistingWorld", false, "host only: load World from the runtime saves instead of creating a disposable one");
        password = Config.Bind("Harness", "Password", "", "disposable server password (secret)");
        leaderName = Config.Bind("Harness", "LeaderName", "Leader", "host character name");
        botName = Config.Bind("Harness", "BotName", "Thorkell", "bot character name");
        timeoutSeconds = Config.Bind("Harness", "TimeoutSeconds", 300, "fail after this many seconds");
        inventoryFixtures = Config.Bind("Harness", "InventoryFixtures", "", "client only: prefab:count,... added to the bot as cheated test items");
        worldFixtures = Config.Bind("Harness", "WorldFixtures", "", "client only: prefab[#tag]@forward,right;... spawned around the bot");
        existingTargets = Config.Bind("Harness", "ExistingTargets", "", "client only: 'tree' picks the nearest standing tree a stone axe can chop");
        locations = Config.Bind("Harness", "Locations", "", "host only: location prefabs to generate besides StartTemple, comma separated (e.g. Eikthyrnir)");
        moveOffset = Config.Bind("Harness", "MoveOffset", "", "fixture move before ready: host 'x,z' from spawn, 'flat' or 'location:<name>:<near>:<far>', client 'forward,right' from leader");

        harmony = new Harmony("thorkell.harness");
        try
        {
            root = role.Value == "host" ? Isolation.Enforce(harmony, "host-test") : RootFromDataPath();
            if (role.Value != "host" && role.Value != "client")
                throw new IsolationException("unknown harness role '" + role.Value + "'");
        }
        catch (Exception e)
        {
            Logger.LogError("HARNESS: setup failed, quitting: " + e);
            enabled = false;
            Application.Quit(2);
            return;
        }

        if (role.Value == "host")
            harmony.Patch(AccessTools.Method(typeof(ZoneSystem), nameof(ZoneSystem.GenerateLocations)),
                prefix: new HarmonyMethod(typeof(Harness), nameof(SmallFixtureWorld)));

        Application.runInBackground = true;
        Application.targetFrameRate = 30;
        AudioListener.volume = 0f;
        started = Time.realtimeSinceStartup;
        Write("harness-started.json", new JObject { ["role"] = role.Value, ["backend"] = backend.Value });
        Logger.LogInfo("HARNESS: " + role.Value + " ready in " + root);
    }

    static string RootFromDataPath()
    {
        var root = Directory.GetParent(Directory.GetParent(Path.GetFullPath(Application.dataPath))!.FullName)!.FullName;
        if (!File.Exists(Path.Combine(root, Isolation.MarkerName)))
            throw new IsolationException("not inside a Thorkell runtime: " + root);
        return root;
    }

    // 접속 시험에는 시작 신전만 있으면 된다. 수천 개 던전 생성으로 시간을 쓰지 않는다(테스트 월드에서만).
    // 시나리오가 필요한 장소(보스 제단 등)는 Locations 설정으로 더 만든다.
    static void SmallFixtureWorld(ZoneSystem __instance)
    {
        if (instance == null || ZNet.instance == null || ZNet.instance.GetWorldName() != instance.world.Value)
            return;
        var keep = new HashSet<string>(instance.locations.Value.Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries)) { "StartTemple" };
        foreach (var location in __instance.m_locations)
            if (!keep.Contains(location.m_prefabName))
                location.m_enable = false;
    }

    void Update()
    {
        // 시험용 게임(호스트·봇 모두)은 소리를 내지 않는다. 게임이 시작·컷신 때 볼륨을 다시 올리므로 매 프레임 지킨다.
        if (AudioListener.volume != 0f)
            AudioListener.volume = 0f;
        if (finished)
            return;
        frames.Add(Time.unscaledDeltaTime * 1000f);
        if (Time.realtimeSinceStartup >= nextPerf)
        {
            nextPerf = Time.realtimeSinceStartup + 10f;
            WritePerf();
        }
        if (Time.realtimeSinceStartup - started > timeoutSeconds.Value)
        {
            Finish(false, "timeout in phase " + phase);
            return;
        }
        if (File.Exists(Path.Combine(root, "stop.txt")))
        {
            bool passed = role.Value == "host" ? peerSeen : clientReady;
            Finish(passed, "stop requested in phase " + phase);
            return;
        }
        try
        {
            if (role.Value == "host")
                HostUpdate();
            else
                ClientUpdate();
        }
        catch (Exception e)
        {
            Finish(false, "harness exception in phase " + phase + ": " + e);
        }
    }

    void HostUpdate()
    {
        if (!booted)
        {
            if (!Isolation.Verified)
            {
                phase = "waiting_isolation_verify";
                return;
            }
            if (FejdStartup.instance == null || ObjectDB.instance == null || Time.realtimeSinceStartup - started < 5f)
                return;
            var wanted = backend.Value == "playfab" ? OnlineBackendType.PlayFab : OnlineBackendType.Steamworks;
            if (wanted == OnlineBackendType.PlayFab && !PlayFabManager.IsLoggedIn)
            {
                phase = "waiting_playfab_login";
                return;
            }
            booted = true;
            BootHost(wanted);
            phase = "loading_world";
            return;
        }

        WatchLeaderDeath();
        var local = Player.m_localPlayer;
        if (local == null)
            return;
        if (phase == "loading_world" && moveOffset.Value.Length > 0)
        {
            Vector3 point;
            if (moveOffset.Value.StartsWith("location:", StringComparison.Ordinal))
            {
                // 시험 전용: "location:<이름>:<가까이>:<멀리>" 그 장소(예: Eikthyrnir 제단) 둘레의 걸을 수 있는 평지로 옮긴다.
                // 새 월드는 장소를 나눠서 만든다. 찾을 때까지 매 프레임 다시 본다.
                // FindClosestLocation은 m_prefab.Name(애셋 참조 이름)으로 비교해서 찾지 못했다. m_prefabName으로 직접 찾는다.
                var parts = moveOffset.Value.Split(':');
                var instances = ZoneSystem.instance.m_locationInstances.Values;
                var found = instances.Where(l => l.m_location != null && l.m_location.m_prefabName == parts[1])
                    .OrderBy(l => l.m_position.magnitude).ToList();
                if (found.Count == 0)
                {
                    if (Time.realtimeSinceStartup - started > 120f)
                        throw new InvalidOperationException("location " + parts[1] + " not among " + instances.Count + " placed: "
                            + string.Join(",", instances.Select(l => l.m_location?.m_prefabName).Distinct().Take(40)));
                    return;
                }
                var location = found[0];
                // 봇은 시작 신전에서 들어온다. 멀리 있는 리더를 봇 하네스가 찾아오도록 지도에 위치를 공개한다.
                ZNet.instance.SetPublicReferencePosition(true);
                point = WalkableSite(location.m_position, float.Parse(parts[2], System.Globalization.CultureInfo.InvariantCulture), float.Parse(parts[3], System.Globalization.CultureInfo.InvariantCulture));
                leaderLocation = location.m_position;
            }
            else if (moveOffset.Value == "flat")
            {
                point = FlatSite(local.transform.position, out leaderSiteRelief);
                point.y = WorldGenerator.instance.GetHeight(point.x, point.z) + .5f;
            }
            else
            {
                var o = Offsets(moveOffset.Value);
                point = local.transform.position + new Vector3(o.x, 0, o.y);
                point.y = ZoneSystem.instance.GetGroundHeight(point) + .1f;
            }
            if (!FixtureTeleport(local, point, local.transform.rotation, "leader"))
                return;
            phase = "moving_leader";
            return;
        }
        if (phase == "moving_leader" && local.IsTeleporting())
            return;
        if (phase == "loading_world" || phase == "moving_leader")
        {
            phase = "host_ready";
            hostReady = true;
            Write("host-ready.json", new JObject
            {
                ["backend"] = ZNet.m_onlineBackend.ToString(),
                ["listener"] = ReadStatic("Thorkell.Host.LoopbackListener, Thorkell.Host", "State"),
                ["world"] = ZNet.instance.GetWorldName(),
                ["leader_site_relief_m"] = Math.Round(leaderSiteRelief, 2),
                ["leader_site"] = SiteReport(local.transform.position),
                ["location"] = leaderLocation.HasValue ? new JArray(Math.Round(leaderLocation.Value.x, 1), Math.Round(leaderLocation.Value.y, 1), Math.Round(leaderLocation.Value.z, 1)) : null,
            });
        }
        if (!peerSeen)
        {
            var bot = Player.GetAllPlayers().FirstOrDefault(p => p != local && p.GetPlayerName() == botName.Value);
            if (bot != null)
            {
                peerSeen = true;
                phase = "peer_seen";
                Write("host-peer-seen.json", new JObject
                {
                    ["peers"] = ZNet.instance.GetPeers().Count,
                    ["backend"] = ZNet.m_onlineBackend.ToString(),
                    ["listener"] = ReadStatic("Thorkell.Host.LoopbackListener, Thorkell.Host", "State"),
                    ["elapsed_s"] = Time.realtimeSinceStartup - started,
                });
            }
        }
        if (hostReady)
        {
            LeaderCues(local);
            MirrorChat();
        }
    }

    void BootHost(OnlineBackendType wanted)
    {
        if (!SteamManager.Initialize())
            throw new InvalidOperationException("Steam initialization refused");
        var profile = new PlayerProfile("thorkell_leader", FileHelpers.FileSource.Local);
        profile.SetName(leaderName.Value);
        profile.m_firstSpawn = false;
        if (!profile.Save())
            throw new InvalidOperationException("could not save leader profile");
        Game.SetProfile("thorkell_leader", FileHelpers.FileSource.Local);
        World served;
        if (existingWorld.Value)
        {
            // 백업에서 복사해 둔 월드를 그대로 연다. 없거나 읽다 실패하면 새로 만들지 않고 실패한다.
            if (!World.HaveWorld(world.Value))
                throw new InvalidOperationException("world " + world.Value + " is not in the runtime saves");
            served = World.GetCreateWorld(world.Value, FileHelpers.FileSource.Local);
            if (served.m_dataError != World.SaveDataError.None)
                throw new InvalidOperationException("world " + world.Value + " failed to load: " + served.m_dataError);
        }
        else
            served = new World(world.Value, seed.Value) { m_fileSource = FileHelpers.FileSource.Local };
        ZNet.m_onlineBackend = wanted;
        ZNet.SetServer(true, true, false, world.Value, password.Value, served);
        ZNet.ResetServerHost();
        // 테스트 리더는 마네킹이다. 사람처럼 근처 아이템을 자동으로 주우면 봇 근처에 놓은 fixture를 가져간다.
        var autoPickup = AccessTools.Field(typeof(Player), "m_enableAutoPickup")
            ?? throw new InvalidOperationException("Player.m_enableAutoPickup missing");
        autoPickup.SetValue(null, false);
        AccessTools.Method(typeof(FejdStartup), "LoadMainScene").Invoke(FejdStartup.instance, null);
        Logger.LogInfo("HARNESS: booting disposable world " + world.Value + " with backend " + wanted);
    }

    void ClientUpdate()
    {
        var body = ReadBodyState();
        if (body != null && body != phase && !clientReady)
            phase = body;
        if (body == "join_failed")
        {
            Finish(false, "body join failed");
            return;
        }
        var status = ZNet.GetConnectionStatus().ToString();
        if (status.StartsWith("Error", StringComparison.Ordinal))
        {
            Finish(false, "connection refused: " + status);
            return;
        }
        if (clientReady)
        {
            UpdateFixtures();
            return;
        }
        var local = Player.m_localPlayer;
        if (local == null || ZNet.instance == null)
            return;
        var leader = Player.GetAllPlayers().FirstOrDefault(p => p != local && p.GetPlayerName() == leaderName.Value);
        if (local.GetPlayerName() == botName.Value && leader == null && moveOffset.Value.Length > 0 && !farMoved)
        {
            // 시험 전용: 리더가 멀리(보스 제단 근처) 있어 로드되지 않았으면 지도에 공개된 리더 위치 곁으로 옮긴다.
            var info = ZNet.instance.GetPlayerList().FirstOrDefault(p => p.m_name == leaderName.Value && p.m_publicPosition);
            if (info.m_name != null && Vector3.Distance(info.m_position, local.transform.position) > 60f)
            {
                var near = info.m_position + new Vector3(4f, 0f, 0f);
                near.y = WorldGenerator.instance.GetHeight(near.x, near.z) + .5f;
                farMoved = FixtureTeleport(local, near, local.transform.rotation, "bot to far leader");
            }
            return;
        }
        if (farMoved && local.IsTeleporting())
            return;
        if (local.GetPlayerName() == botName.Value && ZNet.instance.GetWorldName() == world.Value && leader != null
            && moveOffset.Value.Length > 0 && !moving)
        {
            var o = Offsets(moveOffset.Value);
            var forward = leader.transform.forward;
            forward.y = 0;
            forward.Normalize();
            var point = leader.transform.position + forward * o.x + Vector3.Cross(Vector3.up, forward) * o.y;
            point.y = ZoneSystem.instance.GetGroundHeight(point) + .1f;
            moving = FixtureTeleport(local, point, Quaternion.LookRotation(-forward), "bot");
            return;
        }
        if (moving && local.IsTeleporting())
            return;
        if (local.GetPlayerName() == botName.Value && ZNet.instance.GetWorldName() == world.Value && leader != null)
        {
            clientReady = true;
            phase = "client_ready";
            PlaceInventoryFixtures(local);
            worldFixturesPending = true;
            placeStarted = Time.realtimeSinceStartup;
            Write("client-ready.json", new JObject
            {
                ["character"] = local.GetPlayerName(),
                ["world"] = ZNet.instance.GetWorldName(),
                ["connection"] = status,
                ["elapsed_s"] = Time.realtimeSinceStartup - started,
            });
        }
    }

    // 스폰 순간이동 중이거나 직전 순간이동 후 2초 안에는 게임이 TeleportTo를 거절한다(Player.m_teleportCooldown).
    // 그래서 거절은 바로 실패로 보지 않고 20초까지 매 프레임 다시 시도한다.
    bool FixtureTeleport(Player local, Vector3 point, Quaternion rotation, string who)
    {
        if (teleportFirstTry < 0)
            teleportFirstTry = Time.realtimeSinceStartup;
        if (local.TeleportTo(point, rotation, false))
        {
            teleportFirstTry = -1f;  // 다음 순간이동(대화 시나리오의 리더 이동)은 20초를 새로 센다
            return true;
        }
        if (Time.realtimeSinceStartup - teleportFirstTry > 20f)
            throw new InvalidOperationException("fixture " + who + " teleport refused for 20s");
        return false;
    }

    // 테스트 전용 준비물. 인벤토리 아이템은 cheated로 표시되고, 월드 물체는 봇 기준 상대 위치에 놓는다.
    void PlaceInventoryFixtures(Player bot)
    {
        if (fixturesPlaced)
            return;
        fixturesPlaced = true;
        foreach (var entry in inventoryFixtures.Value.Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries))
        {
            var parts = entry.Split(':');
            var item = bot.GetInventory().AddItem(parts[0].Trim(), int.Parse(parts[1]), 1, 0, 0L, "thorkell test fixture", true);
            if (item == null)
                throw new InvalidOperationException("fixture item unavailable: " + parts[0]);
            placedFixtures.Add(new JObject { ["prefab"] = parts[0].Trim(), ["name"] = Localization.instance.Localize(item.m_shared.m_name), ["where"] = "inventory" });
        }
    }

    // 순간이동이 끝나도 옆 구역의 지형은 아직 안 불러왔을 수 있다. 그 위에 놓으면 물체가 땅을 뚫고 떨어진다.
    // 그래서 fixture 자리의 지형이 모두 잡힐 때까지 기다렸다가 놓는다. 아직이면 false.
    bool TryPlaceWorldFixtures(Player bot)
    {
        var entries = worldFixtures.Value.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries)
            .Select(entry => entry.Split('@')).Select(parts => (prefab: parts[0].Trim(), offset: Offsets(parts[1]), yaw: Yaw(parts[1]))).ToList();
        var origin = bot.transform.position;
        var leader = Player.GetAllPlayers().FirstOrDefault(p => p != bot && p.GetPlayerName() == leaderName.Value);
        if (existingTargets.Value.Split(',').Contains("tree") && !placedFixtures.Any(f => (string)f["prefab"] == "tree"))
        {
            var tree = NearestChoppableTree(bot, leader);
            if (tree == null)
                return false;
            placedFixtures.Add(new JObject { ["prefab"] = "tree", ["where"] = "existing", ["id"] = IdOf(tree.gameObject), ["kind"] = tree.name });
        }
        if (entries.Count == 0)
            return true;
        var heading = FlatHeading(origin, leader, entries.Select(e => e.offset).ToList(), out var relief);
        if (heading == null)
            return false;
        var forward = heading.Value;
        var right = Vector3.Cross(Vector3.up, forward);
        var points = entries.Select(e => origin + forward * e.offset.x + right * e.offset.y).ToList();
        if (!points.All(point => ZNetScene.instance.IsAreaReady(point)))
            return false;
        placedRelief = relief;
        // 지각은 시야 안이나 4m 안의 것만 넘긴다(정보 동등성). 준비 단계에서 봇이 fixture 쪽을 보게 돌려 둔다.
        bot.SetLookDir(forward);
        for (var i = 0; i < entries.Count; i++)
        {
            var point = points[i];
            // 지은 것(각도를 준 것)은 땅에 붙어야 버틴다(떠 있으면 무너진다). 물건은 조금 띄워 떨어뜨린다.
            point.y = ZoneSystem.instance.GetGroundHeight(point) + (entries[i].yaw.HasValue ? -.05f : .3f);
            // "Wood#2"처럼 '#' 뒤는 같은 prefab을 여럿 놓을 때 구분하는 이름표다.
            var prefabName = entries[i].prefab.Split('#')[0];
            var prefab = ZNetScene.instance.GetPrefab(prefabName) ?? throw new InvalidOperationException("fixture prefab missing: " + prefabName);
            // 세 번째 숫자는 봇 앞쪽에서 돌린 각도다(벽을 둘러 집을 지을 때). 없으면 예전처럼 비탈 아래·앞쪽을 본다.
            var facing = entries[i].yaw.HasValue
                ? Quaternion.LookRotation(Quaternion.Euler(0, entries[i].yaw.Value, 0) * forward)
                : Quaternion.LookRotation(Downhill(point) ?? forward);
            var spawned = Instantiate(prefab, point, facing);
            // 포털은 '#' 뒤를 이름표로 단다. 이름표가 같은 두 포털이 이어진다.
            var label = entries[i].prefab.Contains('#') ? entries[i].prefab.Split('#')[1] : null;
            if (label != null && spawned.GetComponent<TeleportWorld>() is TeleportWorld portal)
                portal.SetText(label);
            if (!entries[i].yaw.HasValue)
                LiftAboveGround(spawned);
            spawnedFixtures.Add(spawned);
            spawnPoints.Add(point);
            placedFixtures.Add(new JObject { ["prefab"] = entries[i].prefab, ["where"] = "world", ["id"] = IdOf(spawned) });
        }
        return true;
    }

    // 진단: 고른 자리의 실제 지형(콜라이더)과 생성 높이를 비교한다.
    static JObject SiteReport(Vector3 center)
    {
        float low = float.MaxValue, high = float.MinValue;
        for (var dx = -10f; dx <= 10f; dx += 2.5f)
            for (var dz = -10f; dz <= 10f; dz += 2.5f)
            {
                var height = ZoneSystem.instance.GetGroundHeight(center + new Vector3(dx, 0, dz));
                low = Mathf.Min(low, height);
                high = Mathf.Max(high, height);
            }
        return new JObject
        {
            ["pos"] = center.ToString("F1"),
            ["ground"] = Math.Round(ZoneSystem.instance.GetGroundHeight(center), 2),
            ["generated"] = Math.Round(WorldGenerator.instance.GetHeight(center.x, center.z), 2),
            ["terrain_relief_m"] = Math.Round(high - low, 2),
        };
    }

    // 시작 신전 둘레는 언덕일 수 있다. 출발점에서 15~60m 사이에서 반지름 10m 안의 높낮이 차가 가장 작은 마른 땅을 고른다.
    // 아직 안 불러온 구역도 볼 수 있게 지형 콜라이더 대신 월드 생성 높이를 쓴다.
    static Vector3 FlatSite(Vector3 origin, out float relief)
    {
        var generator = WorldGenerator.instance ?? throw new InvalidOperationException("WorldGenerator not ready");
        relief = float.MaxValue;
        var best = origin;
        for (var radius = 15f; radius <= 60f; radius += 5f)
            for (var i = 0; i < 24; i++)
            {
                var angle = i * 15f * Mathf.Deg2Rad;
                var center = origin + new Vector3(Mathf.Cos(angle), 0, Mathf.Sin(angle)) * radius;
                float low = float.MaxValue, high = float.MinValue;
                for (var dx = -10f; dx <= 10f; dx += 2.5f)
                    for (var dz = -10f; dz <= 10f; dz += 2.5f)
                    {
                        var height = generator.GetHeight(center.x + dx, center.z + dz);
                        low = Mathf.Min(low, height);
                        high = Mathf.Max(high, height);
                    }
                if (low < ZoneSystem.instance.m_waterLevel + 1f || high - low >= relief)
                    continue;
                relief = high - low;
                best = center;
            }
        if (relief == float.MaxValue)
            throw new InvalidOperationException("no dry site within 60m of spawn");
        return best;
    }

    // 비탈에 두면 통나무가 굴러간다. 봇 둘레 16방향 가운데 fixture 자리가 물 위가 아니고 리더와 5m 이상 떨어진 방향을 고르고,
    // 그중 높낮이 차(relief)가 가장 작은 방향을 쓴다. 테스트 리더 근처에 두면 리더 몫이 되고, 근처에서 휘두르게 된다.
    // 지형을 아직 못 잡는 지점이 있으면 null(나중에 다시 본다).
    static Vector3? FlatHeading(Vector3 origin, Player leader, List<Vector2> offsets, out float relief)
    {
        relief = float.MaxValue;
        Vector3? best = null;
        var ring = new[] { Vector3.zero, Vector3.forward, Vector3.back, Vector3.left, Vector3.right };
        if (!ZoneSystem.instance.GetGroundHeight(origin, out var originHeight))
            return null;
        for (var i = 0; i < 16; i++)
        {
            var forward = Quaternion.Euler(0, i * 22.5f, 0) * Vector3.forward;
            var right = Vector3.Cross(Vector3.up, forward);
            float low = originHeight, high = originHeight;
            var usable = true;
            foreach (var offset in offsets)
            {
                var center = origin + forward * offset.x + right * offset.y;
                if (leader != null && Vector3.Distance(center, leader.transform.position) < 5f)
                {
                    usable = false;
                    break;
                }
                foreach (var step in ring)
                {
                    if (!ZoneSystem.instance.GetGroundHeight(center + step * 1.5f, out var height))
                        return null;
                    if (height < ZoneSystem.instance.m_waterLevel + .5f)
                        usable = false;
                    low = Mathf.Min(low, height);
                    high = Mathf.Max(high, height);
                }
                if (!usable)
                    break;
            }
            if (usable && high - low < relief)
            {
                relief = high - low;
                best = forward;
            }
        }
        if (best == null)
            throw new InvalidOperationException("no dry fixture site at least 5m from the leader");
        return best;
    }

    // 이미 서 있는 나무 중 돌도끼로 벨 수 있는 것(최소 도구 등급 0). 봇과 같은 높이, 리더와 6m 이상, 봇에서 3~15m.
    static TreeBase NearestChoppableTree(Player bot, Player leader)
    {
        var origin = bot.transform.position;
        return UnityEngine.Object.FindObjectsByType<TreeBase>(FindObjectsSortMode.None)
            .Where(tree => tree.m_minToolTier <= 0 && tree.GetComponent<ZNetView>() is ZNetView view && view.IsValid())
            .Where(tree =>
            {
                var p = tree.transform.position;
                var flat = new Vector3(p.x - origin.x, 0, p.z - origin.z).magnitude;
                return flat >= 3f && flat <= 15f && Mathf.Abs(p.y - origin.y) <= 1.5f
                    && (leader == null || Vector3.Distance(p, leader.transform.position) >= 6f);
            })
            .OrderBy(tree => Vector3.Distance(tree.transform.position, origin))
            .FirstOrDefault();
    }

    // 통나무처럼 긴 물체는 가운데만 땅 위에 두면 비탈 쪽 끝이 지형 안에 박혀 시작하고, 물리 엔진이 지형 아래로 밀어낸다.
    // 콜라이더 바닥이 자기 발밑에서 가장 높은 지면보다 위에 오도록 들어 올린다.
    static void LiftAboveGround(GameObject spawned)
    {
        var colliders = spawned.GetComponentsInChildren<Collider>().Where(c => c.enabled && !c.isTrigger).ToList();
        if (colliders.Count == 0)
            return;
        var bounds = colliders[0].bounds;
        foreach (var collider in colliders)
            bounds.Encapsulate(collider.bounds);
        var top = float.MinValue;
        for (var fx = 0f; fx <= 1f; fx += .25f)
            for (var fz = 0f; fz <= 1f; fz += .25f)
                top = Mathf.Max(top, ZoneSystem.instance.GetGroundHeight(new Vector3(
                    Mathf.Lerp(bounds.min.x, bounds.max.x, fx), 0, Mathf.Lerp(bounds.min.z, bounds.max.z, fz))));
        var lift = top + .15f - bounds.min.y;
        if (lift <= 0)
            return;
        spawned.transform.position += Vector3.up * lift;
        var body = spawned.GetComponentInChildren<Rigidbody>();
        if (body != null)
            body.position = spawned.transform.position;
    }

    // 통나무는 긴 축이 비탈 방향과 나란하면 구르지 않는다. 경사가 거의 없으면 null.
    static Vector3? Downhill(Vector3 point)
    {
        float H(Vector3 p) => ZoneSystem.instance.GetGroundHeight(p);
        var gradient = new Vector3(H(point + Vector3.right) - H(point - Vector3.right), 0, H(point + Vector3.forward) - H(point - Vector3.forward));
        return gradient.magnitude < .05f ? (Vector3?)null : -gradient.normalized;
    }

    // 놓을 수 있을 때 놓고, 떨어뜨린 물체가 멈춘 뒤에 준비 완료로 본다. 비탈에서 구르는 통나무는 봇의 반사(rolling_log)를 깨운다.
    void UpdateFixtures()
    {
        var now = Time.realtimeSinceStartup;
        if (worldFixturesPending)
        {
            if (TryPlaceWorldFixtures(Player.m_localPlayer))
            {
                worldFixturesPending = false;
                fixturesSettling = true;
                settleStarted = now;
                phase = "settling_fixtures";
            }
            else if (now - placeStarted > 30f)
                throw new InvalidOperationException("terrain around the bot did not load within 30s");
            return;
        }
        if (!fixturesSettling)
            return;
        // 생물은 제 발로 돌아다닌다. 멈추기를 기다리는 것은 굴러가는 물건뿐이다(멧돼지가 계속 걸어 20초를 넘겼다).
        var anyMoving = spawnedFixtures.Any(go => go != null && go.GetComponent<Character>() == null
            && go.GetComponentInChildren<Rigidbody>() is Rigidbody body
            && (body.linearVelocity.magnitude > .1f || body.angularVelocity.magnitude > .2f));
        if (anyMoving)
            settledSince = -1f;
        else if (settledSince < 0)
            settledSince = now;
        if (settledSince >= 0 && now - settledSince > 1.5f)
        {
            // 멈춘 자리가 봇과 같은 높이의 마른 땅인지 본다. 아니면 나중 단계의 실패로 오해하지 않게 여기서 멈춘다.
            var feet = Player.m_localPlayer.transform.position.y;
            var unusable = spawnedFixtures.Where(go => go != null).Select(go =>
            {
                var p = go.transform.position;
                var wet = Floating.GetLiquidLevel(p) > ZoneSystem.instance.GetGroundHeight(p) + .1f;
                return Mathf.Abs(p.y - feet) > 2f || wet
                    ? go.name + " pos=" + p.ToString("F1") + " feet_y=" + feet.ToString("F1") + " ground=" + ZoneSystem.instance.GetGroundHeight(p).ToString("F1")
                        + " liquid=" + Floating.GetLiquidLevel(p).ToString("F1") + " spawned_from=" + spawnPoints[spawnedFixtures.IndexOf(go)].ToString("F1") + (wet ? " in water" : "")
                    : null;
            }).Where(text => text != null).ToList();
            if (unusable.Count > 0)
                throw new InvalidOperationException("fixture site unusable: " + string.Join("; ", unusable));
            fixturesSettling = false;
            phase = "client_ready";
            // 진단: 각 물체의 기준점과 콜라이더 위치(자동 줍기는 기준점까지 거리로 판단한다).
            for (var i = 0; i < spawnedFixtures.Count; i++)
            {
                var go = spawnedFixtures[i];
                var entry = placedFixtures.OfType<JObject>().FirstOrDefault(f => (string)f["id"] == IdOf(go));
                if (go == null || entry == null)
                    continue;
                entry["pos"] = go.transform.position.ToString("F2");
                entry["colliders"] = new JArray(go.GetComponentsInChildren<Collider>().Where(c => c.enabled && !c.isTrigger)
                    .Select(c => c.GetType().Name + " " + c.bounds.center.ToString("F2") + "/" + c.bounds.size.ToString("F2")));
            }
            Write("fixtures-ready.json", new JObject
            {
                ["placed"] = placedFixtures,
                ["settle_s"] = Math.Round(now - settleStarted, 2),
                ["site_relief_m"] = Math.Round(placedRelief, 2),
            });
            return;
        }
        if (now - settleStarted > 20f)
            throw new InvalidOperationException("world fixtures still moving after 20s: " + string.Join("; ", spawnedFixtures.Where(go => go != null).Select(go =>
            {
                var body = go.GetComponentInChildren<Rigidbody>();
                var p = go.transform.position;
                return go.name + " pos=" + p.ToString("F1") + " ground=" + ZoneSystem.instance.GetGroundHeight(p).ToString("F1")
                    + " water=" + ZoneSystem.instance.m_waterLevel.ToString("F1") + " speed=" + (body != null ? body.linearVelocity.magnitude.ToString("F2") : "none");
            })));
    }

    static float? Yaw(string text)
    {
        var parts = text.Split(',');
        return parts.Length > 2 ? float.Parse(parts[2], System.Globalization.CultureInfo.InvariantCulture) : (float?)null;
    }

    static Vector2 Offsets(string text)
    {
        var parts = text.Split(',');
        return new Vector2(float.Parse(parts[0], System.Globalization.CultureInfo.InvariantCulture),
            float.Parse(parts[1], System.Globalization.CultureInfo.InvariantCulture));
    }

    static string IdOf(GameObject go)
    {
        var view = go.GetComponent<ZNetView>();
        var zdo = view != null && view.IsValid() ? view.GetZDO() : null;
        return zdo == null ? null : zdo.m_uid.UserID + ":" + zdo.m_uid.ID;
    }

    static string ReadBodyState()
    {
        var type = Type.GetType("Thorkell.Body.BodyPlugin, Thorkell.Body");
        var plugin = type?.GetProperty("Instance", BindingFlags.Public | BindingFlags.Static)?.GetValue(null);
        return plugin == null ? null : (string)type.GetProperty("State")!.GetValue(plugin);
    }

    static string ReadStatic(string typeName, string property)
    {
        var type = Type.GetType(typeName);
        if (type == null)
            return "not_installed";
        var value = type.GetProperty(property, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static)?.GetValue(null);
        return value?.ToString() ?? "unknown";
    }

    void WritePerf()
    {
        if (frames.Count == 0)
            return;
        var sorted = frames.OrderBy(f => f).ToList();
        float Percentile(double p) => sorted[Math.Min(sorted.Count - 1, (int)(p * sorted.Count))];
        Write("perf.json", new JObject
        {
            ["frames"] = sorted.Count,
            ["frame_ms_p50"] = Percentile(0.50),
            ["frame_ms_p95"] = Percentile(0.95),
            ["frame_ms_p99"] = Percentile(0.99),
            ["gc_count"] = GC.CollectionCount(0),
            ["phase"] = phase,
        });
        frames.Clear();
    }

    void Finish(bool passed, string detail)
    {
        finished = true;
        WritePerf();
        Write("result.json", new JObject
        {
            ["role"] = role.Value,
            ["passed"] = passed,
            ["detail"] = detail,
            ["phase"] = phase,
            ["elapsed_s"] = Time.realtimeSinceStartup - started,
        });
        Logger.LogInfo("HARNESS RESULT: " + (passed ? "PASS" : "FAIL") + ": " + detail);
    }

    void Write(string name, JObject content)
    {
        var path = Path.Combine(root, name);
        var temporary = path + ".tmp";
        File.WriteAllText(temporary, content.ToString());
        if (File.Exists(path))
            File.Delete(path);
        File.Move(temporary, path);
    }
}
