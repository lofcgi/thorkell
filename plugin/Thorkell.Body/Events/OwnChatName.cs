using System.Reflection;
using HarmonyLib;
using UnityEngine;

namespace Thorkell.Body.Events;

// 토르켈 자신의 채팅창에 자기 말을 토르켈 이름으로 찍는다(호스트의 ChatNames와 같은 까닭).
// 게임은 채팅창의 이름을 플랫폼 ID로 찾는데, 토르켈은 사람과 같은 Steam 계정이라 사람의 이름이 찍혔다
// (README 영상 녹화, 2026-10-20: "Leader: Ate some Cooked Boar Meat"). 다른 사람의 말은 원래대로 둔다.
[HarmonyPatch]
internal static class OwnChatName
{
    static readonly FieldInfo HideTimer = AccessTools.Field(typeof(Chat), "m_hideTimer");
    static readonly MethodInfo AddInworldText = AccessTools.Method(typeof(Chat), "AddInworldText");

    [HarmonyPatch(typeof(Chat), nameof(Chat.OnNewChatMessage))]
    [HarmonyPrefix]
    static bool FromMe(Chat __instance, GameObject go, long senderID, Vector3 pos, Talker.Type type, UserInfo sender, string text)
    {
        if (ZNet.instance == null || senderID != ZNet.GetUID())
            return true;
        var player = Player.m_localPlayer;
        if (player == null || player.InIntro())
            return false;
        text = text.Replace('<', ' ').Replace('>', ' ');
        if (type != Talker.Type.Ping)
        {
            HideTimer.SetValue(__instance, 0f);
            __instance.AddString(sender.GetDisplayName(), text, type);
        }
        AddInworldText.Invoke(__instance, new object[] { go, senderID, pos, type, sender, text });
        return false;
    }
}
