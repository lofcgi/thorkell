using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using Thorkell.Body.Actions;
using Thorkell.Body.Events;
using Thorkell.Body.Perception;
using Thorkell.Core;
using UnityEngine;

namespace Thorkell.Body.Reflex;

// 프레임 단위 반사. 두뇌보다 빨라야 하는 것만 여기 둔다:
//  - self_preservation: 물에서 힘이 빠짐, 불·타르 안, 굴러오는 통나무 → 안전한 쪽으로 피한다.
//  - self_defense: 다른 일을 하다 생물에게 맞으면 바로 그쪽을 보고 반격(상대가 휘두르면 막기).
//    두뇌가 그 상황을 넘겨받아 공격 명령을 내리면 즉시 물러난다.
// 낮은 체력에서 도망칠지 끝까지 싸울지 같은 전술은 두뇌가 정한다.
internal static class Reflexes
{
    public static readonly ModeArbiter Arbiter = new ModeArbiter(quietSeconds: 1.0);

    static readonly int[] Angles = { 0, 45, -45, 90, -90, 135, -135, 180 };
    static readonly Collider[] buffer = new Collider[256];
    static Character attacker;
    static float lastHitAt = -100f, nextSwing, brainFightingUntil = -100f;
    // 두뇌의 공격 명령은 한 번씩 끊어서 온다. 명령 사이 틈마다 반사가 다시 잡았다 놓지 않게 잠시 두뇌 몫으로 둔다.
    const float BrainGraceSeconds = 2.5f;
    static Vector3 escape;
    static string reason = "";

    public static string Owner => Arbiter.Owner.HasValue ? Name(Arbiter.Owner.Value) : null;

    public static void OnDamagedBy(Character who)
    {
        if (who == null || who.IsPlayer())
            return;
        attacker = who;
        lastHitAt = Time.time;
    }

    // 두뇌가 공격 명령을 보냈다: 반격은 두뇌 몫이다.
    public static Transition BrainTookOver()
    {
        attacker = null;
        brainFightingUntil = Time.time + BrainGraceSeconds;
        return Arbiter.Owner == ReflexMode.SelfDefense ? Arbiter.ReleaseNow() : Transition.Nothing;
    }

    public static Transition Update(Player self, string activeOp)
    {
        var active = new List<ReflexMode>(2);
        if (Hazard(self))
            active.Add(ReflexMode.SelfPreservation);
        var defending = Defending(self, activeOp);
        if (defending)
            active.Add(ReflexMode.SelfDefense);
        var transition = Arbiter.Update(active, Time.time);
        switch (Arbiter.Owner)
        {
            case ReflexMode.SelfPreservation:
                Motor.Intent.MoveWorld = escape;
                Motor.Intent.LookWorld = escape;
                Motor.Intent.Run = true;
                Motor.Intent.Block = false;
                break;
            case ReflexMode.SelfDefense:
                // 싸울 이유가 없어진 뒤에도 중재기는 1초 조용히 기다렸다 놓는다. 그동안은 서 있는다.
                // 사라진(쓰러져 없어진) 상대를 쫓다가 매 프레임 예외가 나 링크 갱신이 멈췄다(2026-10-18 실게임).
                if (defending)
                    DriveDefense(self);
                else
                {
                    Motor.Intent.MoveWorld = Vector3.zero;
                    Motor.Intent.Block = false;
                }
                break;
        }
        if (transition.Kind == TransitionKind.Released)
            Motor.Intent.Clear();
        return transition;
    }

    public static JObject Describe(Transition transition)
    {
        var data = new JObject { ["mode"] = Name((transition.To ?? transition.From).Value), ["reason"] = reason };
        if (transition.To == ReflexMode.SelfDefense && attacker != null)
        {
            data["attacker_id"] = Ids.Of(attacker);
            data["attacker_name"] = attacker.GetHoverName();
            if (Player.m_localPlayer != null)
                data["weapon"] = Snapshot.WeaponJson(Player.m_localPlayer);
        }
        return data;
    }

    static string Name(ReflexMode mode) => mode == ReflexMode.SelfPreservation ? "self_preservation"
        : mode == ReflexMode.SelfDefense ? "self_defense" : mode == ReflexMode.Unstuck ? "unstuck" : "hard_stop";

    static bool Defending(Player self, string activeOp)
    {
        if (attacker == null || Time.time < brainFightingUntil)
            return false;
        // 큰 적(보스)이나 활을 든 싸움은 두뇌가 맡는다. 활을 든 채 보스에게 달려가 근접 반격하다 뿔에 세 번 맞았다.
        var weapon = self.GetCurrentWeapon();
        if (Scanner.SizeOf(attacker) == "large" || (weapon != null && weapon.m_shared.m_attack.m_bowDraw))
            return false;
        if (activeOp == "attack" || attacker.IsDead() || Time.time - lastHitAt > 10f
            || Vector3.Distance(self.transform.position, attacker.transform.position) > 12f)
        {
            attacker = null;
            return false;
        }
        reason = "attacked";
        return true;
    }

    static void DriveDefense(Player self)
    {
        var point = Geometry.ApproachPoint(self, attacker);
        var direction = point - self.transform.position;
        direction.y = 0;
        var distance = direction.magnitude;
        Motor.Intent.LookWorld = Geometry.AimDirection(self, attacker);
        var weapon = self.GetCurrentWeapon();
        var reach = weapon != null && weapon.m_shared.m_attack != null && weapon.m_shared.m_attack.m_attackRange > 0
            ? weapon.m_shared.m_attack.m_attackRange : 1.5f;
        if (distance > reach)
        {
            Motor.Intent.MoveWorld = direction / Mathf.Max(distance, .01f);
            Motor.Intent.Run = self.GetStamina() > self.GetMaxStamina() * .3f;
            Motor.Intent.Block = false;
            return;
        }
        Motor.Intent.MoveWorld = Vector3.zero;
        Motor.Intent.Block = attacker.InAttack() && self.GetStamina() > self.GetMaxStamina() * .2f;
        if (Motor.Intent.Block || self.InAttack() || Time.time < nextSwing)
            return;
        Events.Hooks.SwingAt(attacker);
        if (self.StartAttack(attacker, false))
            nextSwing = Time.time + .4f;
    }

    static bool Hazard(Player self)
    {
        var position = self.transform.position;
        if (self.IsSwimming() && self.GetStamina() < self.GetMaxStamina() * .3f)
        {
            reason = "tired_in_water";
            return Escape(self, position, toLand: true);
        }
        if (EffectArea.IsPointPlus025InsideBurningArea(position)
            || Floating.GetLiquidLevel(position, 1f, LiquidType.Tar) > position.y)
        {
            reason = "fire_or_tar";
            return Escape(self, position, toLand: false);
        }
        if (RollingLog(self, position, out var away))
        {
            reason = "rolling_log";
            escape = away;
            return true;
        }
        return false;
    }

    static bool Escape(Player self, Vector3 position, bool toLand)
    {
        // 방금 때린 상대가 있으면 그 반대쪽부터 본다(보스의 번개 불 속에서 보스 쪽으로 피했다).
        var forward = self.transform.forward;
        if (attacker != null && Time.time - lastHitAt < 10f)
            forward = position - attacker.transform.position;
        forward.y = 0;
        forward.Normalize();
        foreach (var angle in Angles)
        {
            var direction = Quaternion.Euler(0, angle, 0) * forward;
            if (toLand)
            {
                foreach (var distance in new[] { 3f, 6f, 12f })
                {
                    var probe = position + direction * distance;
                    if (ZoneSystem.instance != null && ZoneSystem.instance.GetGroundHeight(probe) > Floating.GetLiquidLevel(probe, 1f, LiquidType.Water))
                    {
                        escape = direction;
                        return true;
                    }
                }
            }
            else if (Geometry.Clearance(self, position, direction) > 1.5f)
            {
                escape = direction;
                return true;
            }
        }
        escape = -forward;
        return true;
    }

    // 쓰러지거나 구르는 통나무가 가까우면 굴러오는 방향의 옆으로 비킨다(Eira에서 통나무에 깔려 죽은 사례).
    static bool RollingLog(Player self, Vector3 position, out Vector3 away)
    {
        away = Vector3.zero;
        int count = Physics.OverlapSphereNonAlloc(position, 6f, buffer, ~0, QueryTriggerInteraction.Ignore);
        for (int i = 0; i < count; i++)
        {
            var log = buffer[i].GetComponentInParent<TreeLog>();
            var body = log != null ? log.GetComponent<Rigidbody>() : null;
            if (body == null)
                continue;
            var velocity = body.linearVelocity;
            velocity.y = 0;
            if (velocity.magnitude < 1.0f && body.angularVelocity.magnitude < 1.0f)
                continue;
            var fromLog = position - log.transform.position;
            fromLog.y = 0;
            var side = Vector3.Cross(Vector3.up, velocity.sqrMagnitude > .01f ? velocity.normalized : fromLog.normalized);
            away = Vector3.Dot(side, fromLog) >= 0 ? side : -side;
            return true;
        }
        return false;
    }
}
