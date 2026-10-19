using System;
using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace Thorkell.Body.Perception;

// 집 지을 터 보기. 사람은 둘러보고 평평하고 덤불·바위·나무가 없는 땅을 고른다. 근처 격자에서 그런 자리를 찾아
// 평평한 순서로 준다. 땅 높이는 지형 콜라이더, 막힌 것은 무릎~머리 높이의 물체(덤불·바위·나무·지은 것)로 본다.
internal static class Sites
{
    static readonly int Ground = LayerMask.GetMask("terrain");
    const float MaxRelief = .4f;
    // 작은 돌·나뭇가지(Default_small)는 사람이 치우고 짓는 것이라 막힌 것으로 치지 않는다.
    static readonly int Blocking = LayerMask.GetMask("Default", "static_solid", "piece");

    public static JArray Find(Player self, JObject args)
    {
        var center = args["near"] is JArray near && near.Count == 3 ? new Vector3((float)near[0], (float)near[1], (float)near[2]) : self.transform.position;
        var width = args["width"] != null ? (float)args["width"] : 6f;
        var depth = args["depth"] != null ? (float)args["depth"] : 5f;
        var radius = args["radius"] != null ? Mathf.Clamp((float)args["radius"], 4f, 40f) : 20f;
        // 평평함 기준(m). 두뇌가 먼저 엄격하게 찾고, 없으면 느슨하게 다시 찾는다.
        var maxRelief = args["max_relief"] != null ? Mathf.Clamp((float)args["max_relief"], .2f, 1f) : MaxRelief;
        var found = new List<(float relief, Vector3 point)>();
        for (var x = -radius; x <= radius; x += 2f)
            for (var z = -radius; z <= radius; z += 2f)
            {
                var point = center + new Vector3(x, 0, z);
                if (Vector3.Distance(point, center) > radius || !Relief(point, width, depth, out var relief, out var ground) || relief >= maxRelief)
                    continue;
                // 시작 신전 둘레처럼 게임이 짓지 못하게 하는 곳(망치를 대면 빨갛게 보인다). 실게임(2026-10-20):
                // 신전 옆을 집터로 골랐다가 "여긴 못 짓네"를 되풀이했다.
                if (Location.IsInsideNoBuildLocation(ground))
                    continue;
                var box = new Vector3(width / 2f, 1.1f, depth / 2f);
                if (Physics.CheckBox(ground + Vector3.up * 1.5f, box, Quaternion.identity, Blocking, QueryTriggerInteraction.Ignore))
                    continue;
                found.Add((relief, ground));
            }
        found.Sort((a, b) => a.relief.CompareTo(b.relief));
        var result = new JArray();
        for (var i = 0; i < found.Count && result.Count < 5; i++)
            result.Add(new JObject { ["pos"] = new JArray(Math.Round(found[i].point.x, 2), Math.Round(found[i].point.y, 2), Math.Round(found[i].point.z, 2)), ["relief_m"] = Math.Round(found[i].relief, 2) });
        return result;
    }

    // 직사각형 안 땅의 높낮이 차. 물 아래이거나 땅이 안 잡히면 false.
    static bool Relief(Vector3 center, float width, float depth, out float relief, out Vector3 ground)
    {
        float low = float.MaxValue, high = float.MinValue;
        ground = center;
        relief = 0f;
        // 5x5 격자로 잰다. 9곳만 보면 벽 자리 땅이 작업대보다 0.7m 낮은 것을 놓쳐 지붕이 작업대보다 낮게 붙었다.
        for (var dx = -width / 2f; dx <= width / 2f + .01f; dx += width / 4f)
            for (var dz = -depth / 2f; dz <= depth / 2f + .01f; dz += depth / 4f)
            {
                var top = center + new Vector3(dx, 50f, dz);
                if (!Physics.Raycast(top, Vector3.down, out var hit, 120f, Ground, QueryTriggerInteraction.Ignore))
                    return false;
                if (Floating.GetLiquidLevel(hit.point, 1f, LiquidType.Water) > hit.point.y)
                    return false;
                low = Mathf.Min(low, hit.point.y);
                high = Mathf.Max(high, hit.point.y);
                if (Mathf.Abs(dx) < .01f && Mathf.Abs(dz) < .01f)
                    ground = hit.point;
            }
        relief = high - low;
        return true;
    }
}
