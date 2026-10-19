using System;
using System.IO;
using HarmonyLib;
using Newtonsoft.Json.Linq;

namespace Thorkell.Host;

// 사람(리더)이 게임 채팅으로 보낸 말을 `thorkell play`에 넘긴다. 런타임 루트의 thorkell-leader-chat.jsonl에 한 줄씩 덧붙인다.
// 게임의 채팅 전달로는 토르켈에게 닿지 않기 때문이다: 보내기 전에 받는 사람마다 플랫폼 권한을 확인하는데
// (Chat.CheckPermissionsAndSendChatMessageRPCsAsync), 루프백으로 들어온 토르켈은 플랫폼 ID가 비어 있어 Error로 끝나고 메시지가 나가지 않는다.
[HarmonyPatch]
internal static class LeaderChat
{
    public const string FileName = "thorkell-leader-chat.jsonl";

    static string path;

    public static void Init(string runtimeRoot) => path = Path.Combine(runtimeRoot, FileName);

    [HarmonyPatch(typeof(Chat), nameof(Chat.SendText))]
    [HarmonyPostfix]
    static void Sent(Talker.Type type, string text)
    {
        if (path == null || Player.m_localPlayer == null || string.IsNullOrWhiteSpace(text))
            return;
        // 처음 스폰할 때 게임이 대신 외치는 "내가 왔다!"(Game.SpawnPlayer)는 사람이 한 말이 아니다.
        if (type == Talker.Type.Shout && text == Localization.instance.Localize("$text_player_arrived"))
            return;
        var line = new JObject
        {
            ["from"] = Player.m_localPlayer.GetPlayerName(),
            ["talker"] = type.ToString().ToLowerInvariant(),
            ["text"] = text,
            ["at"] = DateTime.UtcNow.ToString("o"),
        };
        File.AppendAllText(path, line.ToString(Newtonsoft.Json.Formatting.None) + "\n");
    }
}
