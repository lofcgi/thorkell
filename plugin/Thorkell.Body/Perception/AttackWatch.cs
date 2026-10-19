using System;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using Thorkell.Body.Events;
using Thorkell.Core;
using UnityEngine;

namespace Thorkell.Body.Perception;

// 생물이 공격 동작을 시작하는 것(몸을 젖히고 뿔을 숙이는 것)은 사람이 화면에서 보고 피한다.
// 애니메이션은 모든 클라이언트에 동기화되므로 InAttack(애니메이터 상태 태그)으로 같은 것을 안다.
// 장면은 초당 두 번이라 늦다. 시작하는 순간을 이벤트로 바로 알린다.
internal static class AttackWatch
{
    // 생물의 정면이 나를 향하는지(사람은 누구를 노리는지 몸 방향으로 본다).
    const float FacingDegrees = 45f;

    static readonly HashSet<Character> attacking = new HashSet<Character>();

    public static void Update(Player self)
    {
        attacking.RemoveWhere(c => c == null);
        foreach (var creature in Character.GetAllCharacters())
        {
            if (creature == null || creature.IsPlayer() || creature.IsDead())
                continue;
            if (!creature.InAttack())
            {
                attacking.Remove(creature);
                continue;
            }
            if (!attacking.Add(creature))
                continue;
            var point = Geometry.ApproachPoint(self, creature);
            var distance = Vector3.Distance(self.transform.position, point);
            if (!Parity.Perceived(distance, Geometry.SeesCreature(self, creature), Scanner.Range))
                continue;
            var toMe = self.transform.position - creature.transform.position;
            toMe.y = 0;
            EventSink.Emit("creature_attacking", new JObject
            {
                ["id"] = Ids.Of(creature),
                ["distance"] = Math.Round(distance, 1),
                ["size"] = Scanner.SizeOf(creature),
                ["facing_me"] = Vector3.Angle(creature.transform.forward, toMe) < FacingDegrees,
            });
        }
    }
}
