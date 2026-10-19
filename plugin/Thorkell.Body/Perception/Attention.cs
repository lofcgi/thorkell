using System.Collections.Generic;
using Thorkell.Body.Actions;
using Thorkell.Core;
using UnityEngine;

namespace Thorkell.Body.Perception;

// 사람은 시야에 생물이 들어오면 잠깐 쳐다본다. 게임도 쳐다본(조준한) 생물에게만 이름표를 띄운다(EnemyHud).
// 서 있을 때(행동이 없거나 기다리는 중)만, 이름표가 꺼진 가까운 생물을 0.5초 본다.
// 걷는 중에는 보지 않는다: 시선을 돌리면 몸도 돌아서 걸음이 초당 4m에서 1m로 느려졌다(실게임 2026-10-17).
// 쳐다봐도 이름표가 안 잡힌 생물(가려졌거나 너무 작음)은 한동안 다시 보지 않는다.
internal static class Attention
{
    static readonly HashSet<string> StandingOps = new HashSet<string> { "wait" };
    const float RetryAfter = 20f;
    static readonly Dictionary<string, float> tried = new Dictionary<string, float>();
    const float GlanceSeconds = .5f;
    const float Interval = 1f;
    // 이름표가 꺼지기(60초) 조금 전에 다시 본다.
    const double Refresh = Parity.HoverPersistSeconds - 10;
    static Character target;
    static float until, next;

    public static string Target => target != null ? Ids.Of(target) : null;

    public static void Update(Player self, Scanner scanner, string activeOp, bool reflex)
    {
        var now = Time.time;
        if (reflex || (activeOp != null && !StandingOps.Contains(activeOp)))
        {
            target = null;
            return;
        }
        if (target != null && now < until && !target.IsDead())
        {
            Motor.Intent.LookWorld = Geometry.CrosshairDirection(self, target);
            return;
        }
        target = null;
        if (now < next)
            return;
        next = now + Interval;
        var best = float.MaxValue;
        foreach (var character in Character.GetAllCharacters())
        {
            if (character == self || character.IsPlayer() || character.IsDead())
                continue;
            var distance = Vector3.Distance(self.transform.position, character.transform.position);
            var id = Ids.Of(character);
            if (distance > Parity.HudRadius || distance >= best || id == null || scanner.SinceHover(id) < Refresh)
                continue;
            if (tried.TryGetValue(id, out var at) && now - at < RetryAfter)
                continue;
            if (!Geometry.SeesCreature(self, character))
                continue;
            best = distance;
            target = character;
        }
        if (target != null)
        {
            until = now + GlanceSeconds;
            tried[Ids.Of(target)] = now;
        }
    }
}
