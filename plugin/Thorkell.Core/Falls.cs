using System.Collections.Generic;

namespace Thorkell.Core;

// 시체(Ragdoll)에는 주인이 적혀 있지 않다. 생긴 자리에서 가장 가까운 캐릭터로 누가 쓰러졌는지 짐작한다.
// 플레이어의 시체는 생물이 쓰러진 것이 아니다. 죽은 리더 곁에 서 있던 보스를 쓰러졌다고 했다(2026-10-18).
public static class Falls
{
    // 쓰러진 생물의 번호. 플레이어의 시체이거나, 가장 가까운 캐릭터가 플레이어이거나, 가까이 아무도 없으면 -1.
    public static int Fallen(bool playerRagdoll, IReadOnlyList<(bool IsPlayer, float Distance)> characters, float matchDistance)
    {
        if (playerRagdoll)
            return -1;
        var nearest = -1;
        var best = matchDistance;
        for (var i = 0; i < characters.Count; i++)
        {
            if (characters[i].Distance < best)
            {
                best = characters[i].Distance;
                nearest = i;
            }
        }
        return nearest >= 0 && !characters[nearest].IsPlayer ? nearest : -1;
    }

    // 쓰러진 플레이어(리더)의 번호. 죽은 플레이어의 캐릭터는 시체가 생길 때 이미 없을 수 있어서, 조금 전에 본 자리로 맞춘다.
    // 사람은 친구가 쓰러지는 것을 본다(실게임 2026-10-20: 앞에서 막던 리더가 쓰러진 것을 몰랐다).
    // seen: 각 플레이어를 마지막으로 본 자리와 시체 사이 거리, 본 지 몇 초. 맞는 사람이 없으면 -1.
    public static int FallenPlayer(IReadOnlyList<(float Distance, float AgeS)> seen, float matchDistance, float maxAgeS)
    {
        var nearest = -1;
        var best = matchDistance;
        for (var i = 0; i < seen.Count; i++)
        {
            if (seen[i].AgeS <= maxAgeS && seen[i].Distance < best)
            {
                best = seen[i].Distance;
                nearest = i;
            }
        }
        return nearest;
    }
}
