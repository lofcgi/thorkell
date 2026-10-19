using System.Reflection;
using HarmonyLib;
using UnityEngine;

namespace Thorkell.Host;

// 토르켈이 한 말을 채팅창에 토르켈의 캐릭터 이름으로 찍는다.
// 게임은 채팅창의 이름을 보낸 사람의 플랫폼 ID로 플레이어 목록에서 찾는다(Terminal.AddString(PlatformUserID, …)).
// 토르켈은 사람과 같은 Steam 계정으로 접속하므로 그 ID로는 사람의 캐릭터가 먼저 찾아져 사람 이름으로 찍힌다.
// 그래서 루프백으로 들어온 토르켈의 말만, 메시지에 실려 온 캐릭터 이름(UserInfo.Name)으로 찍는다.
[HarmonyPatch]
internal static class ChatNames
{
    static readonly FieldInfo HideTimer = AccessTools.Field(typeof(Chat), "m_hideTimer");
    static readonly MethodInfo AddInworldText = AccessTools.Method(typeof(Chat), "AddInworldText");

    [HarmonyPatch(typeof(Chat), nameof(Chat.OnNewChatMessage))]
    [HarmonyPrefix]
    static bool FromThorkell(Chat __instance, GameObject go, long senderID, Vector3 pos, Talker.Type type, UserInfo sender, string text)
    {
        if (!LoopbackListener.IsLoopbackPeer(senderID))
            return true;
        // 원래 메서드가 권한 확인 뒤에 하는 일과 같다. 같은 계정의 봇이라 플랫폼 권한·검열 확인은 하지 않는다.
        var player = Player.m_localPlayer;
        if (player == null || player.InIntro())
            return false;
        text = text.Replace('<', ' ').Replace('>', ' ');
        if (type != Talker.Type.Ping)
        {
            HideTimer.SetValue(__instance, 0f);
            __instance.AddString(sender.GetDisplayName(), text, type);
        }
        var map = Minimap.instance;
        if (map == null || map.m_mode != Minimap.MapMode.None || Vector3.Distance(player.transform.position, pos) <= map.m_nomapPingDistance)
            AddInworldText.Invoke(__instance, new object[] { go, senderID, pos, type, sender, text });
        return false;
    }
}
