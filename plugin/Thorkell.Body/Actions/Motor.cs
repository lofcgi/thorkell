using HarmonyLib;
using UnityEngine;

namespace Thorkell.Body.Actions;

// 행동과 반사가 매 프레임 채우는 모터 의도. 실제 입력은 PlayerController.FixedUpdate 자리에서 한 번에 넣는다.
internal sealed class MotorIntent
{
    public Vector3 MoveWorld;     // 수평 월드 방향(정규화) 또는 0
    public Vector3? LookWorld;    // 바라볼 월드 방향
    public bool Run;
    public bool Block;
    public bool AttackHold;       // 활 시위 당기기: 누르고 있는 동안 당기고, 놓으면 쏜다
    public bool Crouch;           // 웅크리고 있고 싶은지(몰래 걷기). 게임 키는 누를 때마다 켜고 끈다
    public bool Jump;             // 한 프레임짜리
    public bool Dodge;            // 한 프레임짜리

    public void Clear()
    {
        MoveWorld = Vector3.zero;
        LookWorld = null;
        Run = Block = Crouch = Jump = Dodge = AttackHold = false;
    }
}

[HarmonyPatch]
internal static class Motor
{
    public static readonly MotorIntent Intent = new MotorIntent();
    static readonly AccessTools.FieldRef<Player, bool> CrouchToggled = AccessTools.FieldRefAccess<Player, bool>("m_crouchToggled");

    // 사람의 키보드 대신 의도를 SetControls로 넘긴다. movedir은 시선 기준 상대 좌표(z=앞, x=오른쪽)다.
    [HarmonyPatch(typeof(PlayerController), "FixedUpdate")]
    [HarmonyPrefix]
    static bool FixedUpdate(PlayerController __instance)
    {
        var player = __instance.GetComponent<Player>();
        if (!BodyPlugin.Active || player == null || player != Player.m_localPlayer)
            return true;
        var intent = Intent;
        if (intent.LookWorld.HasValue && intent.LookWorld.Value.sqrMagnitude > .0001f)
        {
            var look = intent.LookWorld.Value.normalized;
            player.SetLookDir(look);
            // SetLookDir는 좌우만 돌리고 위아래(m_lookPitch)는 그대로 둔다. 카메라와 화면 가운데 조준점은 그 위아래를 따르므로,
            // 사람이 마우스를 올리고 내리듯 SetMouseLook으로 맞춘다. 안 그러면 조준점이 땅이나 먼 곳을 가리켰다.
            var current = -Mathf.Asin(Mathf.Clamp(player.m_eye.forward.y, -1f, 1f)) * Mathf.Rad2Deg;
            var wanted = -Mathf.Asin(Mathf.Clamp(look.y, -1f, 1f)) * Mathf.Rad2Deg;
            player.SetMouseLook(new Vector2(0f, current - wanted));
        }
        var local = Vector3.zero;
        if (intent.MoveWorld.sqrMagnitude > .0001f)
        {
            var look = player.GetLookDir();
            look.y = 0;
            look.Normalize();
            var right = Vector3.Cross(Vector3.up, look);
            local = new Vector3(Vector3.Dot(intent.MoveWorld, right), 0, Vector3.Dot(intent.MoveWorld, look));
        }
        // 웅크리기 키는 토글이다. 원하는 상태와 다를 때만 누른다.
        var pressCrouch = intent.Crouch != CrouchToggled(player);
        player.SetControls(local, false, intent.AttackHold, false, false, intent.Block, intent.Block, intent.Jump, pressCrouch, intent.Run, false, intent.Dodge);
        intent.Jump = false;
        intent.Dodge = false;
        return false;
    }

    // LateUpdate는 마우스 이동으로 시선을 돌린다. 봇 창에 포커스가 가도 사람의 마우스가 봇을 돌리면 안 된다.
    [HarmonyPatch(typeof(PlayerController), "LateUpdate")]
    [HarmonyPrefix]
    static bool LateUpdate(PlayerController __instance)
    {
        var player = __instance.GetComponent<Player>();
        return !(BodyPlugin.Active && player != null && player == Player.m_localPlayer);
    }
}
