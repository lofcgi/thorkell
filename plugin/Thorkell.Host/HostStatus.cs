using System;
using System.IO;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace Thorkell.Host;

// `thorkell play`가 읽는 호스트 상태: 루프백 리스너 상태, 월드, 백엔드, 사람(리더)의 캐릭터 이름,
// 리더와 토르켈의 위치. 위치는 사람에게 "토르켈이 어디 있는지" 보여 주는 데만 쓴다(두뇌에는 넘기지 않는다).
// 런타임 루트의 thorkell-host-status.json에 통째로 다시 쓴다. 비밀번호 같은 비밀은 넣지 않는다.
internal static class HostStatus
{
    public const string FileName = "thorkell-host-status.json";
    const float MovedM = 1f;

    static string path;
    static string world;
    static string leader;
    static Vector3? leaderPos;
    static string thorkellName;
    static Vector3? thorkellPos;

    public static void Init(string runtimeRoot)
    {
        path = Path.Combine(runtimeRoot, FileName);
        Write();
    }

    public static void SetWorld(string name)
    {
        world = name;
        Write();
    }

    public static void SetLeader(string name)
    {
        if (name == leader)
            return;
        leader = name;
        Write();
    }

    // 호스트는 접속한 모든 피어의 기준 위치(ZNetPeer.m_refPos)를 안다. 토르켈이 지도에 위치를 공개하지 않아도 보인다.
    public static void SetPositions(Vector3? leaderAt, ZNetPeer bot)
    {
        var botAt = bot != null ? bot.m_refPos : (Vector3?)null;
        var botName = bot != null ? bot.m_playerName : null;
        if (!Moved(leaderPos, leaderAt) && !Moved(thorkellPos, botAt) && botName == thorkellName)
            return;
        leaderPos = leaderAt;
        thorkellPos = botAt;
        thorkellName = botName;
        Write();
    }

    static bool Moved(Vector3? before, Vector3? now) =>
        before.HasValue != now.HasValue || (now.HasValue && Vector3.Distance(before.Value, now.Value) > MovedM);

    static JToken Vec(Vector3? v) =>
        v.HasValue ? new JArray(Math.Round(v.Value.x, 1), Math.Round(v.Value.y, 1), Math.Round(v.Value.z, 1)) : null;

    public static void Write()
    {
        if (path == null)
            return;
        var status = new JObject
        {
            ["listener"] = LoopbackListener.State,
            ["port"] = HostPlugin.Instance?.ListenerPort?.Value,
            ["world"] = world,
            ["backend"] = ZNet.m_onlineBackend.ToString(),
            ["leader"] = leader,
            ["leader_chat"] = true,  // 리더 채팅을 thorkell-leader-chat.jsonl로 넘긴다(이 버전부터)
            ["leader_pos"] = Vec(leaderPos),
            ["thorkell"] = thorkellPos.HasValue ? new JObject { ["name"] = thorkellName, ["pos"] = Vec(thorkellPos) } : null,
            ["updated"] = DateTime.UtcNow.ToString("o"),
        };
        var temp = path + ".tmp";
        File.WriteAllText(temp, status.ToString());
        if (File.Exists(path))
            File.Replace(temp, path, null);
        else
            File.Move(temp, path);
    }
}
