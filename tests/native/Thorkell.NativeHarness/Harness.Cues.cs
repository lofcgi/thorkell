using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Reflection;
using System.Text;
using HarmonyLib;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace Thorkell.NativeHarness;

// 대화 시나리오에서 리더(사람 역할)가 할 일. 러너가 leader-cue.jsonl에 한 줄씩 덧붙이면 순서대로 한다.
//  {"id": 1, "say": "따라와", "talker": "normal"}  사람이 채팅창에 친 것처럼 말한다(Chat.SendText).
//  {"id": 2, "move": [15, 0]}                      지금 자리에서 동쪽 x, 북쪽 z만큼 옮긴다(테스트 전용 순간이동).
//  {"id": 3, "site": [120, 160]}                   그 거리 고리 안에서 곧게 걸어갈 수 있는 마른 평지로 옮긴다.
//  {"id": 4, "share_position": true}               지도에서 위치 공개를 켠다.
//  {"id": 5, "spawn": "Boar", "near_bot": [20, 0]}   시험용: 봇이 보는 방향 앞 20m(오른쪽 0m)에 생물을 내보낸다.
//  {"id": 6, "global_key": "defeated_eikthyr"}      서버의 전역 키가 있는지 detail에 "set"/"unset"으로 알린다(보스 처치 확인).
//  {"id": 8, "morning": true}                      시험용(녹화): 밤이나 오후면 잠잘 때처럼 다음 아침으로 넘긴다(12초쯤).
//                                                  넘기는 동안은 밤을 지나므로 다 넘긴 뒤에 끝났다고 알린다.
//  {"id": 7, "fight": "Eikthyr", "weapon": "Club"}  시험용: 리더가 그 생물 곁에 붙어 휘두르며 주의를 끈다(무적).
//                                                  weapon을 빼면 맨손이다(리더 혼자 잡지 못하게). 바로 끝나고 뒤에서 계속한다.
//      "mortal": true, "eat": ["CookedMeat"]       무적을 끄고 그 음식을 먹고 싸운다(사람 리더처럼 맞으면 죽는다).
//                                                  죽으면 싸움을 멈추고 leader-events.jsonl에 {"event":"died"}를 남긴다.
// 끝나면 leader-cue-done.jsonl에 {"id", "ok", "detail", "pos"}를 쓴다.
// 사람 화면의 채팅창에 찍힌 줄은 host-chat.jsonl로 내보낸다(토르켈의 말이 어떤 이름으로 찍히는지 본다).
public sealed partial class Harness
{
    static readonly FieldInfo ChatBuffer = AccessTools.Field(typeof(Terminal), "m_chatBuffer");
    int cuesRead, chatMirrored;
    JObject cue;
    string fightPrefab;
    Character fightTarget;
    Player fighter;
    bool mortalFighter;
    float nextSwing;
    Vector3? cueTarget;
    bool cueTeleported;

    bool skippingToMorning;

    void Morning()
    {
        var env = EnvMan.instance;
        if (skippingToMorning)
        {
            if (!env.IsTimeSkipping())
            {
                skippingToMorning = false;
                CueDone(true, "morning");
            }
            return;
        }
        // 이미 이른 낮이면 넘기지 않는다(넘기면 하루를 돌아 밤을 지난다).
        if (!EnvMan.IsNight() && env.GetDayFraction() < MorningUntil)
        {
            CueDone(true, "already morning");
            return;
        }
        env.SkipToMorning();
        skippingToMorning = true;
    }

    // 하루(0~1) 중 이때까지를 아침으로 친다. 녹화할 장면(20분 남짓)이 밤 전에 끝날 만큼.
    const float MorningUntil = 0.4f;

    void LeaderCues(Player local)
    {
        LeaderFights(local);
        if (cue == null && !NextCue())
            return;
        try
        {
            if (cue["say"] != null)
            {
                var talker = (string)cue["talker"];
                var type = talker == "shout" ? Talker.Type.Shout : talker == "whisper" ? Talker.Type.Whisper : Talker.Type.Normal;
                Chat.instance.SendText(type, (string)cue["say"]);
                CueDone(true, "said");
            }
            else if (cue["share_position"] != null)
            {
                ZNet.instance.SetPublicReferencePosition((bool)cue["share_position"]);
                CueDone(true, "position public: " + ZNet.instance.IsReferencePositionPublic());
            }
            else if (cue["move"] != null || cue["site"] != null)
                MoveLeader(local);
            else if (cue["spawn"] != null)
                SpawnNearBot(local);
            else if (cue["global_key"] != null)
                CueDone(true, ZoneSystem.instance.GetGlobalKey((string)cue["global_key"]) ? "set" : "unset");
            else if (cue["fight"] != null)
                StartLeaderFight(local);
            else if (cue["morning"] != null)
                Morning();
            else
                CueDone(false, "unknown cue " + cue.ToString(Formatting.None));
        }
        catch (Exception e)
        {
            CueDone(false, e.GetType().Name + ": " + e.Message);
        }
    }

    // 러너가 쓰는 중인 마지막 줄(줄바꿈 전)은 읽지 않는다.
    bool NextCue()
    {
        var path = Path.Combine(root, "leader-cue.jsonl");
        if (!File.Exists(path))
            return false;
        var text = File.ReadAllText(path);
        var lines = text.Substring(0, text.LastIndexOf('\n') + 1).Split(new[] { '\n' }, StringSplitOptions.RemoveEmptyEntries);
        if (cuesRead >= lines.Length)
            return false;
        cue = JObject.Parse(lines[cuesRead++]);
        cueTarget = null;
        cueTeleported = false;
        return true;
    }

    void MoveLeader(Player local)
    {
        if (cueTarget == null)
        {
            if (cue["move"] is JArray move)
            {
                var point = local.transform.position + new Vector3((float)move[0], 0, (float)move[1]);
                point.y = WorldGenerator.instance.GetHeight(point.x, point.z) + .5f;
                cueTarget = point;
            }
            else
            {
                var ring = (JArray)cue["site"];
                cueTarget = WalkableSite(local.transform.position, (float)ring[0], (float)ring[1]);
            }
        }
        if (!cueTeleported)
        {
            cueTeleported = FixtureTeleport(local, cueTarget.Value, local.transform.rotation, "leader cue");
            return;
        }
        if (local.IsTeleporting())
            return;
        CueDone(true, "moved");
    }

    // 시험 전용: 필요한 순간에 봇 앞에 생물을 내보낸다(사냥 시험). 사람 플레이에는 없는 일이다.
    void SpawnNearBot(Player local)
    {
        var bot = Player.GetAllPlayers().FirstOrDefault(p => p != local && p.GetPlayerName() == botName.Value);
        if (bot == null)
        {
            CueDone(false, "bot not loaded");
            return;
        }
        var offset = (JArray)cue["near_bot"];
        var forward = bot.transform.forward;
        forward.y = 0;
        forward.Normalize();
        var right = Vector3.Cross(Vector3.up, forward);
        var point = bot.transform.position + forward * (float)offset[0] + right * (float)offset[1];
        point.y = ZoneSystem.instance.GetGroundHeight(point) + .3f;
        var prefab = ZNetScene.instance.GetPrefab((string)cue["spawn"]) ?? throw new InvalidOperationException("no prefab " + cue["spawn"]);
        var spawned = Instantiate(prefab, point, Quaternion.LookRotation(-forward));
        var view = spawned.GetComponent<ZNetView>();
        CueDone(true, "spawned " + (view != null && view.IsValid() ? view.GetZDO().m_uid.ToString() : "?") + " at " + point.ToString("F1"));
    }

    // 시험 전용: 사람이 앞에서 싸워 주는 같이 하기를 흉내 낸다. 무적이고, 걷는 입력이 없어 곁으로 옮겨 붙는다.
    void StartLeaderFight(Player local)
    {
        var mortal = cue["mortal"] != null && (bool)cue["mortal"];
        local.SetGodMode(!mortal);
        mortalFighter = mortal;
        fighter = local;
        foreach (var food in cue["eat"]?.Values<string>() ?? Enumerable.Empty<string>())
        {
            var item = local.GetInventory().AddItem(food, 1, 1, 0, 0L, "thorkell test fixture", true)
                ?? throw new InvalidOperationException("no item " + food);
            if (!local.EatFood(item))
                throw new InvalidOperationException("leader could not eat " + food);
        }
        var weapon = (string)cue["weapon"];
        if (!string.IsNullOrEmpty(weapon))
        {
            var item = local.GetInventory().AddItem(weapon, 1, 1, 0, 0L, "thorkell test fixture", true)
                ?? throw new InvalidOperationException("no item " + weapon);
            local.EquipItem(item);
        }
        fightPrefab = (string)cue["fight"];
        fightTarget = null;
        CueDone(true, "fighting " + fightPrefab + " with " + (string.IsNullOrEmpty(weapon) ? "bare hands" : weapon)
            + (mortal ? ", mortal, health " + local.GetMaxHealth().ToString("F0") : ", god mode"));
    }

    // 죽은 리더의 Player는 없어지고(m_localPlayer가 비었다가) 다시 태어나면 새 Player가 된다.
    // 다시 태어난 리더가 보스 곁으로 옮겨 붙지 않게 싸움을 멈추고 죽음을 남긴다.
    void WatchLeaderDeath()
    {
        if (!mortalFighter || fightPrefab == null || (fighter != null && !fighter.IsDead()))
            return;
        var died = new JObject { ["event"] = "died", ["fighting"] = fightPrefab, ["unix"] = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0 };
        File.AppendAllText(Path.Combine(root, "leader-events.jsonl"), died.ToString(Formatting.None) + "\n");
        Logger.LogInfo("HARNESS: the leader died fighting " + fightPrefab);
        fightPrefab = null;
    }

    void LeaderFights(Player local)
    {
        if (fightPrefab == null)
            return;
        if (fightTarget == null || fightTarget.IsDead())
        {
            fightTarget = Character.GetAllCharacters().FirstOrDefault(c =>
                c != null && !c.IsPlayer() && !c.IsDead() && Utils.GetPrefabName(c.gameObject) == fightPrefab
                && Vector3.Distance(c.transform.position, local.transform.position) < 150f);
            if (fightTarget == null)
                return;
        }
        var to = fightTarget.transform.position - local.transform.position;
        to.y = 0;
        var reach = fightTarget.GetRadius() + 1.5f;
        if (to.magnitude > reach + 1.5f)
        {
            var point = fightTarget.transform.position - to.normalized * reach;
            point.y = ZoneSystem.instance.GetGroundHeight(point) + .1f;
            local.transform.position = point;
            var body = local.GetComponent<Rigidbody>();
            if (body != null)
                body.position = point;
            to = fightTarget.transform.position - point;
            to.y = 0;
        }
        if (to.sqrMagnitude < .01f)
            return;
        local.transform.rotation = Quaternion.LookRotation(to.normalized);
        local.SetLookDir(to.normalized);
        if (Time.time >= nextSwing && !local.InAttack() && local.StartAttack(fightTarget, false))
            nextSwing = Time.time + 1.2f;
    }

    void CueDone(bool ok, string detail)
    {
        var local = Player.m_localPlayer;
        var line = new JObject
        {
            ["id"] = cue["id"],
            ["ok"] = ok,
            ["detail"] = detail,
            ["pos"] = local != null ? new JArray(local.transform.position.x, local.transform.position.y, local.transform.position.z) : null,
        };
        File.AppendAllText(Path.Combine(root, "leader-cue-done.jsonl"), line.ToString(Formatting.None) + "\n");
        if (!ok)
            Logger.LogError("HARNESS: leader cue " + cue["id"] + " failed: " + detail);
        cue = null;
    }

    // 리더를 옮길 자리. 봇이 따라올 수 있게 지금 자리에서 곧게 걸어갈 수 있어야 한다:
    // 4m마다 본 땅이 모두 물보다 1m 넘게 높고 이웃 지점끼리 높이 차가 2m 이하인 곳 가운데, 반지름 10m 안이 가장 평평한 곳.
    // 아직 안 불러온 구역도 볼 수 있게 월드 생성 높이를 쓴다.
    static Vector3 WalkableSite(Vector3 origin, float near, float far)
    {
        var generator = WorldGenerator.instance ?? throw new InvalidOperationException("WorldGenerator not ready");
        var water = ZoneSystem.instance.m_waterLevel;
        Vector3? best = null;
        var bestRelief = float.MaxValue;
        for (var radius = near; radius <= far; radius += 10f)
            for (var i = 0; i < 36; i++)
            {
                var angle = i * 10f * Mathf.Deg2Rad;
                var center = origin + new Vector3(Mathf.Cos(angle), 0, Mathf.Sin(angle)) * radius;
                if (!WalkableLine(generator, origin, center, water))
                    continue;
                float low = float.MaxValue, high = float.MinValue;
                for (var dx = -10f; dx <= 10f; dx += 2.5f)
                    for (var dz = -10f; dz <= 10f; dz += 2.5f)
                    {
                        var height = generator.GetHeight(center.x + dx, center.z + dz);
                        low = Mathf.Min(low, height);
                        high = Mathf.Max(high, height);
                    }
                if (low < water + 1f || high - low >= bestRelief)
                    continue;
                bestRelief = high - low;
                best = center;
            }
        if (best == null)
            throw new InvalidOperationException("no dry walkable site " + near + "-" + far + "m away");
        var site = best.Value;
        site.y = generator.GetHeight(site.x, site.z) + .5f;
        return site;
    }

    static bool WalkableLine(WorldGenerator generator, Vector3 from, Vector3 to, float water)
    {
        var steps = Mathf.CeilToInt(Vector3.Distance(from, to) / 4f);
        var last = generator.GetHeight(from.x, from.z);
        for (var i = 1; i <= steps; i++)
        {
            var point = Vector3.Lerp(from, to, (float)i / steps);
            var height = generator.GetHeight(point.x, point.z);
            if (height < water + 1f || Mathf.Abs(height - last) > 2f)
                return false;
            last = height;
        }
        return true;
    }

    // 채팅창 버퍼는 300줄까지만 둔다. 시나리오는 그보다 적게 말한다.
    void MirrorChat()
    {
        if (Chat.instance == null)
            return;
        var buffer = (List<string>)ChatBuffer.GetValue(Chat.instance);
        if (buffer.Count <= chatMirrored)
            return;
        var lines = new StringBuilder();
        for (var i = chatMirrored; i < buffer.Count; i++)
            lines.Append(new JObject { ["line"] = buffer[i], ["at"] = DateTime.UtcNow.ToString("o") }.ToString(Formatting.None)).Append('\n');
        File.AppendAllText(Path.Combine(root, "host-chat.jsonl"), lines.ToString());
        chatMirrored = buffer.Count;
    }
}
