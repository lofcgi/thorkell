using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Thorkell.Body.Perception;

// Eira에서 실게임으로 검증한 기하 헬퍼(Survival.ApproachPoint/SurfacePoint, PlayerBot.Clearance)를 옮겼다.
internal static class Geometry
{
    static readonly int GroundMask = LayerMask.GetMask("Default", "static_solid", "Default_small", "piece", "terrain");
    static readonly int LowMask = LayerMask.GetMask("Default", "static_solid", "Default_small", "piece");
    public static readonly int SightMask = LayerMask.GetMask("Default", "static_solid", "piece", "terrain");

    // 다가가거나 조준할 지점. 서 있는 나무는 줄기의 타격 높이, 통나무·바위는 표면 최근접점, 생물은 중심.
    // 근접 공격 방향은 시선의 기울기를 따른다(Attack.GetMeleeAttackDir: GetAimDir = GetLookDir, m_maxYAngle까지).
    // 사람처럼 땅에 누운 통나무는 내려다보고, 생물은 몸 가운데를 본다. 수평으로만 보면 가슴 높이로 휘둘러 통나무를 놓친다.
    // 화면 가운데(카메라 광선)가 생물 몸 가운데를 지나게 하는 시선. 게임은 카메라 광선에 처음 걸린 생물에게 이름표를
    // 띄운다(FindHoverObject). 카메라는 머리 뒤·위에 있어서 눈 기준으로 겨누면 16m 앞 멧돼지 위로 지나갔다.
    // 카메라는 시선을 따라 돌므로 매 프레임 다시 잰다.
    public static Vector3 CrosshairDirection(Player actor, Character target)
    {
        var camera = GameCamera.instance;
        var from = camera != null ? camera.transform.position : actor.GetEyePoint();
        var direction = target.GetCenterPoint() - from;
        return direction.sqrMagnitude > .0001f ? direction.normalized : actor.transform.forward;
    }

    // 카메라 광선이 처음 닿는 것(자기 몸 제외). 조준이 왜 빗나갔는지 볼 때 쓴다.
    public static string CrosshairHit(Player actor)
    {
        var camera = GameCamera.instance;
        if (camera == null)
            return "no_camera";
        var hits = Physics.RaycastAll(camera.transform.position, camera.transform.forward, 50f);
        System.Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
        foreach (var hit in hits)
        {
            if (hit.collider.attachedRigidbody != null && hit.collider.attachedRigidbody.gameObject == actor.gameObject)
                continue;
            return hit.collider.transform.root.name + "@" + System.Math.Round(hit.distance, 1);
        }
        return "none";
    }

    public static Vector3 AimDirection(Player actor, Component target)
    {
        var point = target is Character character ? character.GetCenterPoint() : ApproachPoint(actor, target);
        var direction = point - actor.GetEyePoint();
        return direction.sqrMagnitude > .0001f ? direction.normalized : actor.transform.forward;
    }

    public static Vector3 ApproachPoint(Player actor, Component target)
    {
        if (target is Character)
            return target.transform.position;
        var origin = actor.transform.position + Vector3.up * .8f;
        if (target is TreeBase)
        {
            var stem = target.transform.position;
            stem.y = origin.y;
            var delta = stem - origin;
            var hits = new List<Vector3>();
            if (delta.sqrMagnitude > .0001f)
                foreach (var collider in target.GetComponentsInChildren<Collider>())
                    if (collider.enabled && !collider.isTrigger && collider.Raycast(new Ray(origin, delta.normalized), out var hit, delta.magnitude + 2))
                        hits.Add(hit.point);
            return hits.Count > 0 ? hits.OrderBy(p => (p - origin).sqrMagnitude).First() : stem;
        }
        var points = target.GetComponentsInChildren<Collider>().Where(c => c.enabled && !c.isTrigger)
            .Select(c => SurfacePoint(c, origin)).OrderBy(p => (p - origin).sqrMagnitude).ToList();
        return points.Count > 0 ? points[0] : target.transform.position;
    }

    // 비볼록 메시에 Collider.ClosestPoint를 쓰면 입력점을 그대로 돌려줘 가짜 0거리가 된다. 메시를 레이캐스트한다.
    static Vector3 SurfacePoint(Collider collider, Vector3 origin)
    {
        if (collider is MeshCollider mesh && !mesh.convex)
        {
            var delta = collider.bounds.center - origin;
            if (delta.sqrMagnitude > .0001f && collider.Raycast(new Ray(origin, delta.normalized), out var hit, delta.magnitude + collider.bounds.size.magnitude))
                return hit.point;
            var point = collider.bounds.ClosestPoint(origin);
            return (point - origin).sqrMagnitude > .0001f ? point : collider.bounds.center;
        }
        return collider.ClosestPoint(origin);
    }

    public static float HorizontalDistance(Vector3 a, Vector3 b)
    {
        var d = b - a;
        d.y = 0;
        return d.magnitude;
    }

    // 방향 d로 얼마나 비어 있는지(최대 4m). 0이면 그 방향으로 한 걸음도 안전하지 않다:
    // 절벽·급경사·불·물(무릎 이상)·타르, 몸통과 발 높이 장애물을 본다.
    // 가는 쪽 바로 앞(2.5m 안)을 막은 닫힌 문. 사람은 문 앞에서 열고 지나간다(리허설: 집에 못 들어왔다).
    public static Door ClosedDoorAhead(Vector3 p, Vector3 d)
    {
        if (!Physics.SphereCast(p + Vector3.up * 1f, .3f, d, out var hit, 2.5f, GroundMask, QueryTriggerInteraction.Ignore))
            return null;
        var door = hit.collider.GetComponentInParent<Door>();
        if (door == null)
            return null;
        var view = door.GetComponent<ZNetView>();
        return view != null && view.IsValid() && view.GetZDO().GetInt(ZDOVars.s_state) == 0 ? door : null;
    }

    public static float Clearance(Player actor, Vector3 p, Vector3 d)
    {
        if (!Physics.Raycast(p + d * .9f + Vector3.up * 1.2f, Vector3.down, out var ground, 2.4f, GroundMask, QueryTriggerInteraction.Ignore)
            || ground.normal.y < .65f || ground.point.y - p.y > .7f || p.y - ground.point.y > 1f
            || EffectArea.IsPointPlus025InsideBurningArea(p + d * .9f))
            return 0;
        float wade = Mathf.Clamp(actor.m_swimDepth - .6f, 0, .4f);
        if (Floating.GetLiquidLevel(ground.point, 1f, LiquidType.Water) - ground.point.y > wade
            || Floating.GetLiquidLevel(ground.point, 1f, LiquidType.Tar) > ground.point.y)
            return 0;
        float clear = Physics.SphereCast(p + Vector3.up * .8f, .2f, d, out var hit, 4, GroundMask, QueryTriggerInteraction.Ignore) ? hit.distance : 4;
        // 발 높이 장애물. 나뭇가지·돌·버섯처럼 사람이 그냥 밟고 지나가는 낮은 것은 막힌 것으로 치지 않는다
        // (초원에서 이런 것마다 멈추거나 비켜 가서 걸음이 초당 1m로 느렸다, 실게임 2026-10-17).
        var lowHits = Physics.SphereCastAll(p + Vector3.up * .3f, .2f, d, 4, LowMask, QueryTriggerInteraction.Ignore);
        foreach (var low in lowHits)
        {
            if (low.distance >= clear || WalkOver(low.collider, p.y))
                continue;
            clear = low.distance;
            LastBlocker = low.collider.name;
        }
        return clear;
    }

    public static string LastBlocker;

    static bool WalkOver(Collider collider, float feet) =>
        collider.bounds.max.y < feet + StepHeight || collider.GetComponentInParent<Pickable>() != null || collider.GetComponentInParent<ItemDrop>() != null;

    const float StepHeight = .45f;

    // 눈에서 대상까지 가리는 것이 없는지. 대상 자신의 콜라이더에 먼저 닿으면 보이는 것이다.
    public static bool LineOfSight(Player actor, GameObject target, Vector3 targetPoint)
    {
        var eye = actor.m_eye != null ? actor.m_eye.position : actor.transform.position + Vector3.up * 1.6f;
        var delta = targetPoint - eye;
        if (!Physics.Raycast(eye, delta.normalized, out var hit, delta.magnitude, SightMask, QueryTriggerInteraction.Ignore))
            return true;
        return hit.collider.transform.IsChildOf(target.transform) || (hit.point - targetPoint).sqrMagnitude < .5f;
    }

    // 생물은 몸 어디라도 보이면 보이는 것이다. 몸 가운데는 땅에 가깝게 낮아서 작은 언덕에도 가린다(실게임: 16m 앞 멧돼지).
    public static bool SeesCreature(Player actor, Character creature) =>
        LineOfSight(actor, creature.gameObject, creature.GetCenterPoint()) || LineOfSight(actor, creature.gameObject, creature.GetTopPoint());

    // 시야를 막은 것(진단용, 두뇌가 아니라 결과 증거와 로그에만 싣는다).
    public static string Blocker(Player actor, Vector3 targetPoint)
    {
        var eye = actor.m_eye != null ? actor.m_eye.position : actor.transform.position + Vector3.up * 1.6f;
        var delta = targetPoint - eye;
        if (!Physics.Raycast(eye, delta.normalized, out var hit, delta.magnitude, SightMask, QueryTriggerInteraction.Ignore))
            return "nothing";
        return hit.collider.name + "@" + LayerMask.LayerToName(hit.collider.gameObject.layer) + " " + hit.distance.ToString("F1") + "/" + delta.magnitude.ToString("F1") + "m";
    }

    // 몸이 향한 방향 기준 각도(도). 양수가 오른쪽.
    public static float Bearing(Player actor, Vector3 point)
    {
        var to = point - actor.transform.position;
        to.y = 0;
        var forward = actor.transform.forward;
        forward.y = 0;
        return to.sqrMagnitude < .0001f ? 0 : Vector3.SignedAngle(forward, to, Vector3.up);
    }
}
