using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using HarmonyLib;
using Newtonsoft.Json.Linq;
using Thorkell.Body.Actions;
using Thorkell.Body.Events;
using Thorkell.Body.Perception;
using Thorkell.Body.Reflex;
using Thorkell.Core;
using Thorkell.Wire;
using UnityEngine;

namespace Thorkell.Body.Link;

// 두뇌와의 연결. 메인 스레드에서 매 프레임: 받은 메시지 처리 → 행동 진행 → 이벤트 송신 → state/scene/status 발행.
internal sealed class BodyLink
{
    // "Thorkell 멈춰", "토르켈 그만", "thorkell stop" 같은 채팅은 두뇌를 거치지 않고 바로 멈춘다.
    static readonly Regex StopPhrase = new Regex(@"(thorkell|토르켈).{0,8}(stop|멈춰|그만|정지)", RegexOptions.IgnoreCase);

    readonly BodyPlugin plugin;
    readonly GameBuild build;
    readonly BridgeClient client;
    readonly ActionRunner runner;
    readonly Scanner scanner = new Scanner();
    float nextState, nextScene, nextStatus;
    HashSet<string> players = new HashSet<string>();
    bool? wasNight;
    string lastWeather;

    public BodyLink(BodyPlugin plugin, GameBuild build, int port, string token)
    {
        this.plugin = plugin;
        this.build = build;
        client = new BridgeClient("127.0.0.1", port, token, MakeHello);
        runner = new ActionRunner(message => client.Send(message));
        client.Start();
    }

    Hello MakeHello() => new Hello
    {
        Role = Roles.Body,
        Plugin = BodyPlugin.PluginVersion,
        Game = new GameInfo { Version = build.Game, Network = build.Network, AssemblySha256 = build.Sha256["assembly_valheim.dll"] },
        Caps = new[] { "observe", "move", "act", "say" },
    };

    // 리더가 서버에 접속해 있으면 arm한다. 멀리 있어 리더 캐릭터가 이 클라이언트에 로드되지 않았어도
    // 말하고 찾아갈 수 있어야 한다(전에는 로드된 캐릭터를 요구해서, 멀리 스폰하면 말 한마디도 못 했다).
    public bool Armed(Player self) =>
        self != null && !self.IsDead() && plugin.State == "in_world" && client.Connected && client.Welcome != null && LeaderInfo(self).HasValue;

    // 멀리 간 플레이어의 캐릭터는 위치 갱신이 끊겨 예전 자리에 서 있는 채로 남는다(실게임 2026-10-17: 280m 떨어진 리더가
    // 봇 곁에 서 있어서 "따라와"에 제자리에서 기다렸다). 리더가 지도에 위치를 공개했으면 그 위치와 이만큼 넘게 다를 때
    // 눈앞의 캐릭터는 낡은 모습으로 보고 지도 위치를 쓴다. 지도 위치는 몇 초 늦으므로 달리는 거리만큼 여유를 둔다.
    const float StaleLeaderM = 40f;

    // 가까이 있어 캐릭터가 로드된 리더.
    Player Leader(Player self)
    {
        var name = plugin.LeaderName.Value;
        var leader = Player.GetAllPlayers().FirstOrDefault(p => p != Player.m_localPlayer && (name.Length == 0 || p.GetPlayerName() == name));
        var map = LeaderOnMap(self);
        if (leader != null && map.HasValue && Vector3.Distance(leader.transform.position, map.Value.m_position) > StaleLeaderM)
            return null;
        return leader;
    }

    // 서버의 플레이어 목록에 있는 리더(접속 여부, 지도에 공개한 위치).
    ZNet.PlayerInfo? LeaderInfo(Player self)
    {
        if (ZNet.instance == null || self == null)
            return null;
        var name = plugin.LeaderName.Value;
        var me = self.GetZDOID();
        foreach (var info in ZNet.instance.GetPlayerList())
        {
            if (info.m_characterID != me && (name.Length == 0 || info.m_name == name))
                return info;
        }
        return null;
    }

    // 리더가 지도에서 위치 공개를 켰을 때 지도에 보이는 위치. 사람 플레이어도 지도에서 보는 정보다.
    ZNet.PlayerInfo? LeaderOnMap(Player self)
    {
        var info = LeaderInfo(self);
        return info.HasValue && info.Value.m_publicPosition ? info : null;
    }

    public void Update()
    {
        while (client.Notices.TryDequeue(out var notice))
            plugin.Log.LogInfo("THORKELL bridge: " + notice);

        var self = Player.m_localPlayer;
        while (client.Incoming.TryDequeue(out var message))
            Dispatch(message, self);

        if (self != null)
        {
            if (self.IsDead())
                runner.StopAll("dead", self);
            else
            {
                var transition = Reflexes.Update(self, runner.ActiveOp);
                Announce(transition, self);
                if (Reflexes.Arbiter.Owner == null)
                    runner.Tick(self);
                Attention.Update(self, scanner, runner.ActiveOp, Reflexes.Arbiter.Owner != null);
            }
            scanner.NoteHover(self);
            Events.Hooks.NotePlayers(self);
            if (!self.IsDead())
                AttackWatch.Update(self);
            PollWorld(self);
        }

        while (EventSink.TryTake(out var e))
        {
            if (e.Kind == "chat" && self != null && StopPhrase.IsMatch((string)e.Data["text"] ?? ""))
            {
                runner.StopAll("chat_stop_phrase", self);
                e.Data["stop_phrase"] = true;
            }
            client.Send(e);
        }

        if (!client.Connected || client.Welcome == null)
            return;
        var now = Time.realtimeSinceStartup;
        if (self != null && now >= nextState)
        {
            nextState = now + 1f / Mathf.Max(1, client.Welcome.StateHz);
            client.Send(new State { Tick = Time.frameCount, Data = Snapshot.State(self, runner.Describe(), Reflexes.Owner) });
        }
        if (self != null && now >= nextScene)
        {
            nextScene = now + 1f / Mathf.Max(1, client.Welcome.SceneHz);
            client.Send(new Scene { Tick = Time.frameCount, Data = Snapshot.Scene(self, scanner.Scan(self), scanner.BossBars(self), Leader(self), LeaderOnMap(self)) });
        }
        if (now >= nextStatus)
        {
            nextStatus = now + 1f;
            client.Send(StatusMessage(self));
        }
    }

    void Announce(Transition transition, Player self)
    {
        switch (transition.Kind)
        {
            case TransitionKind.Engaged:
            case TransitionKind.Switched:
                runner.Preempt(Reflexes.Owner, self);
                EventSink.Emit("reflex_engaged", Reflexes.Describe(transition));
                break;
            case TransitionKind.Released:
                EventSink.Emit("reflex_released", Reflexes.Describe(transition));
                break;
        }
    }

    Status StatusMessage(Player self)
    {
        var reasons = new List<string>();
        if (plugin.State != "in_world")
            reasons.Add(plugin.State);
        if (self != null && self.IsDead())
            reasons.Add("dead");
        if (self != null && !LeaderInfo(self).HasValue)
            reasons.Add("leader_absent");
        return new Status
        {
            Armed = Armed(self),
            Ready = plugin.State == "in_world",
            Reasons = reasons.ToArray(),
            VersionGate = new VersionGateInfo { Ok = true, Found = build.Game, Tested = build.Game },
            Perf = new JObject { ["fps"] = Mathf.RoundToInt(1f / Mathf.Max(0.001f, Time.smoothDeltaTime)), ["outbox_overflows"] = client.OutboxOverflows },
        };
    }

    void Dispatch(Message message, Player self)
    {
        switch (message)
        {
            case Command command:
                // 싸우는 명령(때리기·쏘기·구르기)은 두뇌가 싸움을 넘겨받는 것이다. 반사(self_defense)를 바로 놓는다.
                if (command.Op == "attack" || command.Op == "shoot" || command.Op == "dodge")
                    Announce(Reflexes.BrainTookOver(), self);
                runner.Submit(command, self, Armed(self), Reflexes.Owner);
                break;
            case Cancel cancel:
                runner.Cancel(cancel.CmdId, cancel.Reason, self);
                break;
            case StopAll stop:
                runner.StopAll(stop.Reason, self);
                break;
            case Query query:
                client.Send(Answer(query, self));
                break;
            default:
                plugin.Log.LogWarning("THORKELL bridge: ignoring " + message.Type);
                break;
        }
    }

    QueryResult Answer(Query query, Player self)
    {
        if (self == null)
            return new QueryResult { Id = query.Id, Ok = false, Error = "not_in_world" };
        switch (query.What)
        {
            case "item":
            {
                // 사람이 툴팁에서 읽는 설명을 그대로 준다.
                var item = Primitives.FindItem(self, (string)query.Args["item"] ?? "");
                return item == null
                    ? new QueryResult { Id = query.Id, Ok = false, Error = "not_found" }
                    : new QueryResult { Id = query.Id, Ok = true, Data = new JObject { ["name"] = Snapshot.Localize(item.m_shared.m_name), ["tooltip"] = Snapshot.Localize(item.GetTooltip(-1)) } };
            }
            case "known":
            {
                var traverse = Traverse.Create(self);
                return new QueryResult
                {
                    Id = query.Id,
                    Ok = true,
                    Data = new JObject
                    {
                        ["recipes"] = new JArray(traverse.Field<HashSet<string>>("m_knownRecipes").Value.Select(Snapshot.Localize)),
                        ["materials"] = new JArray(traverse.Field<HashSet<string>>("m_knownMaterial").Value.Select(Snapshot.Localize)),
                        ["stations"] = new JArray(traverse.Field<Dictionary<string, int>>("m_knownStations").Value.Select(p => Snapshot.Localize(p.Key) + " " + p.Value)),
                        ["texts"] = new JArray(self.GetKnownTexts().Select(p => Snapshot.Localize(p.Key))),
                    },
                };
            }
            case "recipes":
                return new QueryResult { Id = query.Id, Ok = true, Data = new JObject { ["recipes"] = Menus.Recipes(self) } };
            case "cover":
            {
                // 시험 진단용: 제작대가 지붕·벽 판정을 통과하는지(사람은 제작대를 열어 보고 안다).
                var station = Ids.Find((string)query.Args["id"] ?? "")?.GetComponentInParent<CraftingStation>();
                if (station == null)
                    return new QueryResult { Id = query.Id, Ok = false, Error = "not_found" };
                var check = Traverse.Create(station).Field<Transform>("m_roofCheckPoint").Value ?? station.transform;
                Cover.GetCoverForPoint(check.position, out var cover, out var underRoof);
                var near = new List<Piece>();
                Piece.GetAllPiecesInRadius(check.position, 4f, near);
                var up = Physics.SphereCastAll(check.position, 0.1f, Vector3.up, 100f, LayerMask.GetMask("Default", "static_solid", "Default_small", "piece", "terrain", "vehicle"));
                return new QueryResult
                {
                    Id = query.Id,
                    Ok = true,
                    Data = new JObject
                    {
                        ["usable"] = station.CheckUsable(self, false),
                        ["cover"] = Math.Round(cover, 2),
                        ["under_roof"] = underRoof,
                        ["check_point"] = new JArray(Math.Round(check.position.x, 2), Math.Round(check.position.y, 2), Math.Round(check.position.z, 2)),
                        ["pieces"] = new JArray(near.Select(n => Snapshot.Localize(n.m_name) + "@" + n.transform.position.ToString("F2"))),
                        ["up_hits"] = new JArray(up.Select(h => h.collider.name + ":" + h.collider.tag + ":" + h.distance.ToString("F1"))),
                    },
                };
            }
            case "site":
                return new QueryResult { Id = query.Id, Ok = true, Data = new JObject { ["sites"] = Perception.Sites.Find(self, query.Args) } };
            case "pieces":
                return new QueryResult { Id = query.Id, Ok = true, Data = new JObject { ["pieces"] = Menus.Pieces(self) } };
            case "look":
                return new QueryResult { Id = query.Id, Ok = true, Data = Perception.Sight.Look(query.Args) };
            default:
                return new QueryResult { Id = query.Id, Ok = false, Error = "unknown_query" };
        }
    }

    // 사람도 화면으로 알아채는 변화: 해 짐/뜸, 날씨, 다른 플레이어의 접속·퇴장.
    void PollWorld(Player self)
    {
        var night = EnvMan.IsNight();
        if (wasNight.HasValue && wasNight.Value != night)
            EventSink.Emit("env_changed", new JObject { ["night"] = night });
        wasNight = night;
        var weather = EnvMan.instance?.GetCurrentEnvironment()?.m_name;
        if (weather != null && lastWeather != null && weather != lastWeather)
            EventSink.Emit("env_changed", new JObject { ["weather"] = weather });
        lastWeather = weather ?? lastWeather;

        var now = new HashSet<string>(Player.GetAllPlayers().Where(p => p != self).Select(p => p.GetPlayerName()));
        foreach (var joined in now.Except(players))
            EventSink.Emit("peer_joined", new JObject { ["name"] = joined });
        foreach (var left in players.Except(now))
            EventSink.Emit("peer_left", new JObject { ["name"] = left });
        players = now;
    }

    public void Dispose() => client.Dispose();
}
