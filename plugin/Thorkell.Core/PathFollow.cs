using System.Collections.Generic;
using System.Numerics;

namespace Thorkell.Core;

// 경로 따라가기에서 다음에 향할 모서리. 길찾기는 1초마다 다시 계산되고 경로의 첫 점은 몸 근처 그물 위의 점이라
// 몸 바로 뒤에 놓이기도 한다. "가까운 점만 건너뛰면" 그 뒤쪽 점으로 돌아서서 앞뒤로 오갔다(실게임: 원하는 방향이
// 0.5초마다 정반대로 바뀌어 초당 1m). 그래서 이미 지나친 점(다음 점까지가 그 점에서보다 몸에서 더 가까운 점)도 건너뛴다.
public static class PathFollow
{
    public static Vector2? NextCorner(IReadOnlyList<Vector2> corners, Vector2 position, float minDistance)
    {
        for (var i = 0; i < corners.Count; i++)
        {
            var corner = corners[i];
            if (Vector2.Distance(position, corner) <= minDistance)
                continue;
            if (i + 1 < corners.Count)
            {
                var next = corners[i + 1];
                if (Vector2.Distance(position, next) < Vector2.Distance(corner, next))
                    continue;
            }
            return corner;
        }
        return null;
    }
}
