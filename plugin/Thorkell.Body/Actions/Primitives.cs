using System;
using System.Linq;
using HarmonyLib;
using Newtonsoft.Json.Linq;
using Thorkell.Body.Perception;
using UnityEngine;

namespace Thorkell.Body.Actions;

// 두뇌가 조합해서 쓰는 원자 행동. 모두 월드 변화로 결과를 확인하고, 실패하면 이유를 코드로 돌려준다.
// M2: 직선 이동(장애물 우회 각도 탐색), 바라보기, 말하기, 장착/해제, 먹기, 줍기, 상호작용, 공격(한 번 또는 n번), 기다리기.
internal static class Primitives
{
    // 걸음이나 조준이 필요 없는 명령은 행동 슬롯·모터를 차지하지 않고 바로 실행한다.
    // 반사가 몸을 잡고 있어도(예: 맞으며 반격 중) 두뇌가 무기를 바꾸거나 먹을 수 있어야 한다.
    public static bool IsInstant(string op) => op == "say" || op == "equip" || op == "unequip" || op == "eat";

    public static IAction Create(string op, JObject args, Player self)
    {
        switch (op)
        {
            case "move_to":
                return new MoveTo(Target.Parse(args["target"]), Bool(args, "run", false),
                    Float(args, "arrive_radius", 1.5f, 0.3f, 50f), Float(args, "timeout_s", 60f, 1f, 600f), Bool(args, "sneak", false));
            case "look_at":
                return new LookAt(Target.Parse(args["target"]));
            case "say":
                return new Say(Talker(args), Text(args, "text", 200));
            case "equip":
                return new Equip(Text(args, "item", 80), equip: true);
            case "unequip":
                return new Equip(Text(args, "item", 80), equip: false);
            case "eat":
                return new Eat(Text(args, "item", 80));
            case "pickup":
                return new Pickup(Text(args, "id", 40));
            case "interact":
                return new Interact(Text(args, "id", 40), Bool(args, "alt", false));
            case "use_item":
                return new UseItem(Text(args, "item", 80), Text(args, "id", 40));
            case "drop":
                return new Drop(Text(args, "item", 80), (int)Float(args, "count", 1, 1, 999), args["toward"] != null ? Target.Parse(args["toward"]) : null);
            case "craft":
                return new Craft(Text(args, "item", 80), (int)Float(args, "count", 1, 1, 50), args["station_id"]?.Type == JTokenType.String ? (string)args["station_id"] : null);
            case "place":
                return new Place(Text(args, "piece", 80), Point(args, "pos"), Float(args, "yaw", 0f, -360f, 360f), Bool(args, "exact", false), Float(args, "within_m", 0f, 0f, 3f));
            case "shoot":
                return new Shoot(Text(args, "id", 40), args["strafe"] is JArray ? Point(args, "strafe") : (Vector3?)null, Bool(args, "wait_hit", true));
            case "attack":
                return new Attack(args["id"]?.Type == JTokenType.String ? (string)args["id"] : null, (int)Float(args, "swings", 1, 1, 10), Bool(args, "sneak", false));
            case "wait":
                return new Wait(Float(args, "seconds", 1f, 0.1f, 60f));
            case "dodge":
                return new Dodge(args["toward"] != null ? Point(args, "toward") : (Vector3?)null);
            default:
                throw new ArgumentException("unknown_op");
        }
    }

    static bool Bool(JObject args, string key, bool fallback) =>
        args[key] == null ? fallback : args[key].Type == JTokenType.Boolean ? (bool)args[key] : throw new ArgumentException("bad_args:" + key);

    static float Float(JObject args, string key, float fallback, float min, float max)
    {
        if (args[key] == null)
            return fallback;
        if (args[key].Type != JTokenType.Float && args[key].Type != JTokenType.Integer)
            throw new ArgumentException("bad_args:" + key);
        var value = (float)args[key];
        if (value < min || value > max)
            throw new ArgumentException("bad_args:" + key + "_range");
        return value;
    }

    static Vector3 Point(JObject args, string key)
    {
        if (args[key] is JArray pos && pos.Count == 3 && pos.All(p => p.Type == JTokenType.Float || p.Type == JTokenType.Integer))
            return new Vector3((float)pos[0], (float)pos[1], (float)pos[2]);
        throw new ArgumentException("bad_args:" + key);
    }

    static string Text(JObject args, string key, int maxLength)
    {
        var token = args[key];
        if (token == null || token.Type != JTokenType.String || ((string)token).Length == 0 || ((string)token).Length > maxLength)
            throw new ArgumentException("bad_args:" + key);
        return (string)token;
    }

    static global::Talker.Type Talker(JObject args)
    {
        switch ((string)args["talker"] ?? "normal")
        {
            case "whisper": return global::Talker.Type.Whisper;
            case "normal": return global::Talker.Type.Normal;
            case "shout": return global::Talker.Type.Shout;
            default: throw new ArgumentException("bad_args:talker");
        }
    }

    // 인벤토리에서 이름(사용자 언어) 또는 토큰으로 아이템을 찾는다.
    internal static ItemDrop.ItemData FindItem(Player self, string item) =>
        self.GetInventory().GetAllItems().FirstOrDefault(i => Named(i, item));

    // 같은 이름이 여럿이면(부러진 도끼와 새로 만든 도끼) 사람은 부러지지 않은 것, 더 성한 것을 집는다.
    internal static ItemDrop.ItemData FindUsable(Player self, string item) =>
        self.GetInventory().GetAllItems().Where(i => Named(i, item))
            .OrderByDescending(i => !i.m_shared.m_useDurability || i.m_durability > 0f)
            .ThenByDescending(i => i.m_shared.m_useDurability ? i.m_durability / Mathf.Max(1f, i.GetMaxDurability()) : 1f)
            .FirstOrDefault();

    static bool Named(ItemDrop.ItemData i, string item) =>
        string.Equals(Snapshot.Localize(i.m_shared.m_name), item, StringComparison.OrdinalIgnoreCase) || i.m_shared.m_name == item;

    // 상호작용·공격 대상이 되는 주 컴포넌트.
    internal static Component Primary(GameObject go)
    {
        if (go == null)
            return null;
        return (Component)go.GetComponent<Character>() ?? go.GetComponent<TreeBase>() ?? (Component)go.GetComponent<TreeLog>()
            ?? go.GetComponent<MineRock5>() ?? (Component)go.GetComponent<MineRock>() ?? go.GetComponent<Destructible>()
            ?? (Component)go.GetComponent<ItemDrop>() ?? go.GetComponent<Pickable>() ?? (Component)go.transform;
    }

    internal static float? TargetHealth(Component target)
    {
        if (target is Character character)
            return character.GetHealth();
        var view = target != null ? target.GetComponent<ZNetView>() : null;
        if (view == null || !view.IsValid())
            return null;
        float max = target is TreeBase tree ? tree.m_health : target is TreeLog log ? log.m_health : target is Destructible d ? d.m_health : -1f;
        return max < 0 ? (float?)null : view.GetZDO().GetFloat(ZDOVars.s_health, max);
    }
}

internal sealed class Target
{
    public string Id;
    public Vector3? Position;

    public static Target Parse(JToken token)
    {
        if (!(token is JObject obj))
            throw new ArgumentException("bad_args:target");
        if (obj["id"]?.Type == JTokenType.String)
            return new Target { Id = (string)obj["id"] };
        if (obj["pos"] is JArray pos && pos.Count == 3 && pos.All(p => p.Type == JTokenType.Float || p.Type == JTokenType.Integer))
            return new Target { Position = new Vector3((float)pos[0], (float)pos[1], (float)pos[2]) };
        throw new ArgumentException("bad_args:target");
    }

    public Component Resolve() => Position.HasValue ? null : Primitives.Primary(Ids.Find(Id));

    public bool TryResolve(Player self, out Vector3 point)
    {
        if (Position.HasValue)
        {
            point = Position.Value;
            return true;
        }
        var component = Resolve();
        point = component != null ? Geometry.ApproachPoint(self, component) : Vector3.zero;
        return component != null;
    }
}

internal sealed class MoveTo : IAction
{
    static readonly float[] Detours = { 0f, 30f, -30f, 60f, -60f, 90f, -90f };
    // 개체 목표는 높이도 본다. 수평으로 가까워도 비탈 위·아래로 이보다 멀면 손이 닿지 않는다.
    const float VerticalArrive = 1.5f;
    readonly Target target;
    readonly bool run, sneak;
    readonly float arrive, timeout;
    readonly System.Collections.Generic.List<Vector3> path = new System.Collections.Generic.List<Vector3>();
    // 이동 진단: 막혀 멈춘 프레임, 비켜 간 프레임, 막은 물체 이름(결과 증거에만 싣는다).
    readonly System.Collections.Generic.Dictionary<string, int> blockers = new System.Collections.Generic.Dictionary<string, int>();
    int frames, stuckFrames, detourFrames;
    // 걸음이 느린 원인을 찾는 표본(게임 내부값이라 결과 증거에만, 두뇌 프롬프트에는 쓰지 않는다).
    readonly JArray motion = new JArray();
    float nextMotionSample;
    static readonly HarmonyLib.AccessTools.FieldRef<Character, Vector3> MoveDir = HarmonyLib.AccessTools.FieldRefAccess<Character, Vector3>("m_moveDir");
    static readonly HarmonyLib.AccessTools.FieldRef<Character, Vector3> CurrentVel = HarmonyLib.AccessTools.FieldRefAccess<Character, Vector3>("m_currentVel");
    readonly Thorkell.Core.StuckDetector stuck = new Thorkell.Core.StuckDetector(3.0, 0.3f);
    float started = -1f, nextPath, remaining = -1f, unstuckUntil = -1f;
    int unstucks, dropHeldBefore, doorsOpened;
    float nextDoor;
    Vector3 unstuckDirection;
    string dropToken;

    public string Phase { get; private set; } = "moving";

    // sneak: 사람처럼 웅크리고 천천히 다가간다(달아나는 동물에게 들키지 않게). 달리면 게임이 웅크리기를 푼다.
    public MoveTo(Target target, bool run, float arrive, float timeout, bool sneak = false)
    {
        this.target = target;
        this.run = run && !sneak;
        this.sneak = sneak;
        this.arrive = arrive;
        this.timeout = timeout;
    }

    public Outcome Tick(Player self, float now)
    {
        if (started < 0)
        {
            started = now;
            // 아이템에 다가가면 게임의 자동 줍기(Player.AutoPickup, 2m)가 먼저 주울 수 있다. 그때 확인할 기준 개수다.
            if (target.Resolve() is ItemDrop drop)
            {
                dropToken = drop.m_itemData.m_shared.m_name;
                dropHeldBefore = self.GetInventory().CountItems(dropToken);
            }
        }
        if (!target.TryResolve(self, out var point))
        {
            var added = dropToken != null ? self.GetInventory().CountItems(dropToken) - dropHeldBefore : 0;
            return added > 0
                ? Outcome.Succeeded("picked_up", new JObject { ["item"] = Snapshot.Localize(dropToken), ["added"] = added, ["auto"] = true })
                : Outcome.Failed("target_lost");
        }
        var position = self.transform.position;
        remaining = Geometry.HorizontalDistance(position, point);
        // 위치 목표의 y는 두뇌의 어림값이라 보지 않는다.
        var vertical = target.Position.HasValue ? 0f : Mathf.Abs(point.y - position.y);
        var evidence = new JObject
        {
            ["remaining_m"] = Math.Round(remaining, 2),
            ["vertical_m"] = Math.Round(vertical, 2),
            ["unstucks"] = unstucks,
            ["frames"] = frames,
            ["stuck_frames"] = stuckFrames,
            ["detour_frames"] = detourFrames,
            ["doors_opened"] = doorsOpened,
        };
        if (blockers.Count > 0)
            evidence["blockers"] = new JObject(blockers.OrderByDescending(b => b.Value).Take(4).Select(b => new JProperty(b.Key, b.Value)));
        if (motion.Count > 0)
            evidence["motion"] = motion;
        if (remaining <= arrive && vertical <= VerticalArrive)
        {
            // 아이템이면 기준점까지 거리도 알려 준다. 게임의 자동 줍기는 이 거리(발에서 1m 위 기준 2m)로 판단한다.
            if (target.Resolve() is ItemDrop left)
                evidence["item_center_m"] = Math.Round(Vector3.Distance(left.transform.position, position + Vector3.up), 2);
            return Outcome.Succeeded("arrived", evidence);
        }
        if (now - started > timeout)
            return Outcome.Failed("timeout", evidence);

        if (now < unstuckUntil)
        {
            Motor.Intent.MoveWorld = unstuckDirection;
            Motor.Intent.LookWorld = unstuckDirection;
            return null;
        }
        if (stuck.Update(now, remaining + Mathf.Max(0f, vertical - VerticalArrive)))
        {
            if (++unstucks > 3)
                return Outcome.Failed("blocked", evidence);
            // 옆으로 비켜서며 점프한다. 방향은 번갈아 바꾼다.
            var forward = point - position;
            forward.y = 0;
            forward.Normalize();
            unstuckDirection = Vector3.Cross(Vector3.up, forward) * (unstucks % 2 == 0 ? 1f : -1f);
            unstuckUntil = now + 0.8f;
            Motor.Intent.Jump = true;
            stuck.Reset();
            nextPath = 0;
            Phase = "unstuck";
            return null;
        }

        if (now >= nextPath)
        {
            nextPath = now + 1f;
            path.Clear();
            var found = Pathfinding.instance != null
                && (Pathfinding.instance.GetPath(position, point, path, Pathfinding.AgentType.HumanoidAvoidWater, false, true, false)
                    || Pathfinding.instance.GetPath(position, point, path, Pathfinding.AgentType.HumanoidNoSwim, false, true, false));
            if (!found)
                path.Clear();
        }
        var waypoint = Thorkell.Core.PathFollow.NextCorner(
            path.Select(c => new System.Numerics.Vector2(c.x, c.z)).ToList(), new System.Numerics.Vector2(position.x, position.z), 1.1f) is System.Numerics.Vector2 next
            ? path.First(c => Mathf.Approximately(c.x, next.X) && Mathf.Approximately(c.z, next.Y))
            : point;

        var direction = waypoint - position;
        direction.y = 0;
        direction.Normalize();
        // 닫힌 문이 길을 막으면 연다(문 앞에서 멈춰 섰다 돌아가지 않는다). 열리는 동안 잠깐 기다린다.
        var toTarget = point - position;
        toTarget.y = 0;
        var door = now >= nextDoor ? Geometry.ClosedDoorAhead(position, direction) ?? Geometry.ClosedDoorAhead(position, toTarget.normalized) : null;
        if (door != null && door.Interact(self, false, false))
        {
            doorsOpened++;
            nextDoor = now + 1.5f;
            stuck.Reset();
            Phase = "opening_door";
            Motor.Intent.MoveWorld = Vector3.zero;
            Motor.Intent.LookWorld = door.transform.position - position;
            return null;
        }
        var need = Mathf.Min(1.2f, remaining);
        var chosen = Vector3.zero;
        foreach (var angle in Detours)
        {
            var candidate = Quaternion.Euler(0, angle, 0) * direction;
            if (Geometry.Clearance(self, position, candidate) >= need)
            {
                chosen = candidate;
                break;
            }
        }
        Phase = chosen == Vector3.zero ? "stuck" : path.Count > 0 ? "path" : "direct";
        frames++;
        if (now >= nextMotionSample && motion.Count < 24)
        {
            nextMotionSample = now + .5f;
            var body = self.GetComponent<Rigidbody>();
            motion.Add(new JObject
            {
                ["want"] = Vec2(chosen),
                ["look"] = Vec2(self.GetLookDir()),
                ["move_dir"] = Vec2(MoveDir(self)),
                ["cur_vel"] = Math.Round(CurrentVel(self).magnitude, 2),
                ["body_vel"] = body != null ? Math.Round(body.linearVelocity.magnitude, 2) : -1,
                ["ground"] = self.IsOnGround(),
                ["can_move"] = self.CanMove(),
                ["run"] = self.IsRunning(),
                ["fps"] = Mathf.RoundToInt(1f / Mathf.Max(.001f, Time.smoothDeltaTime)),
                ["fixed_dt"] = Math.Round(Time.fixedDeltaTime, 3),
            });
        }
        if (chosen == Vector3.zero)
        {
            stuckFrames++;
            if (Geometry.LastBlocker != null)
                blockers[Geometry.LastBlocker] = blockers.TryGetValue(Geometry.LastBlocker, out var seen) ? seen + 1 : 1;
        }
        else if (chosen != direction)
            detourFrames++;
        Motor.Intent.MoveWorld = chosen;
        Motor.Intent.LookWorld = chosen == Vector3.zero ? (Vector3?)null : chosen;
        Motor.Intent.Run = run && remaining > 6f && self.GetStamina() > self.GetMaxStamina() * 0.3f;
        Motor.Intent.Crouch = sneak;
        return null;
    }

    static JArray Vec2(Vector3 v) => new JArray(Math.Round(v.x, 2), Math.Round(v.z, 2));

    public JObject Progress(Player self) => new JObject { ["remaining_m"] = Math.Round(remaining, 2), ["phase"] = Phase, ["unstucks"] = unstucks };

    // 몰래 다가간 뒤에는 웅크린 채로 둔다. 다음 동작(몰래 치기)이 이어서 웅크리기를 정한다.
    public void Stop(Player self)
    {
        Motor.Intent.Clear();
        Motor.Intent.Crouch = sneak;
    }
}

internal sealed class LookAt : IAction
{
    readonly Target target;
    int frames;

    public string Phase => "turning";

    public LookAt(Target target)
    {
        this.target = target;
    }

    public Outcome Tick(Player self, float now)
    {
        if (!target.TryResolve(self, out var point))
            return Outcome.Failed("target_lost");
        // 생물은 화면 가운데(조준점)를 몸 가운데에 맞춘다(위아래 각도까지). 수평으로만 보면 작은 짐승 위로 지나간다.
        if (target.Resolve() is Character creature)
            Motor.Intent.LookWorld = Geometry.CrosshairDirection(self, creature);
        else
        {
            var direction = point - self.transform.position;
            direction.y = 0;
            if (direction.sqrMagnitude > .0001f)
                Motor.Intent.LookWorld = direction.normalized;
        }
        if (startedAt < 0)
            startedAt = now;
        var hovered = self.GetHoverCreature();
        // 몸과 카메라가 돌아가는 데 시간이 걸린다. 생물은 조준점이 그 생물에 닿을 때까지(최대 1.2초) 본다.
        var settled = target.Resolve() is Character wanted ? hovered == wanted || now - startedAt > CreatureSeconds : ++frames >= 6;
        if (!settled)
            return null;
        var hover = self.GetHoverObject();
        return Outcome.Succeeded("facing", new JObject
        {
            ["hover_id"] = hover != null ? Ids.Of(hover.transform) : null,
            ["hover_creature_id"] = hovered != null ? Ids.Of(hovered) : null,
            ["turned_s"] = Math.Round(now - startedAt, 2),
            ["crosshair"] = hovered == null ? Geometry.CrosshairHit(self) : null,
        });
    }

    const float CreatureSeconds = 1.2f;
    float startedAt = -1f;

    public JObject Progress(Player self) => new JObject();

    public void Stop(Player self) => Motor.Intent.LookWorld = null;
}

internal sealed class Say : IAction
{
    readonly global::Talker.Type type;
    readonly string text;

    public string Phase => "speaking";

    public Say(global::Talker.Type type, string text)
    {
        this.type = type;
        this.text = text;
    }

    public Outcome Tick(Player self, float now)
    {
        if (Chat.instance == null)
            return Outcome.Failed("chat_unavailable");
        Chat.instance.SendText(type, text);
        return Outcome.Succeeded("said");
    }

    public JObject Progress(Player self) => new JObject();

    public void Stop(Player self) { }
}

internal sealed class Equip : IAction
{
    readonly string item;
    readonly bool equip;

    public string Phase => equip ? "equipping" : "unequipping";

    public Equip(string item, bool equip)
    {
        this.item = item;
        this.equip = equip;
    }

    public Outcome Tick(Player self, float now)
    {
        var found = equip ? Primitives.FindUsable(self, item) : Primitives.FindItem(self, item);
        if (found == null)
            return Outcome.Failed("not_found");
        var evidence = new JObject { ["item"] = Snapshot.Localize(found.m_shared.m_name) };
        if (equip)
        {
            if (self.IsItemEquiped(found))
                return Outcome.Succeeded("already_equipped", evidence);
            self.EquipItem(found, true);
            return self.IsItemEquiped(found) ? Outcome.Succeeded("equipped", evidence) : Outcome.Failed("cannot_equip", evidence);
        }
        if (!self.IsItemEquiped(found))
            return Outcome.Succeeded("not_equipped", evidence);
        self.UnequipItem(found, true);
        return !self.IsItemEquiped(found) ? Outcome.Succeeded("unequipped", evidence) : Outcome.Failed("cannot_unequip", evidence);
    }

    public JObject Progress(Player self) => new JObject();

    public void Stop(Player self) { }
}

internal sealed class Eat : IAction
{
    readonly string item;

    public string Phase => "eating";

    public Eat(string item)
    {
        this.item = item;
    }

    public Outcome Tick(Player self, float now)
    {
        var found = Primitives.FindItem(self, item);
        if (found == null)
            return Outcome.Failed("not_found");
        var evidence = new JObject { ["item"] = Snapshot.Localize(found.m_shared.m_name), ["foods_before"] = self.GetFoods().Count };
        if (found.m_shared.m_food <= 0 && found.m_shared.m_foodStamina <= 0 && found.m_shared.m_foodEitr <= 0)
            return Outcome.Failed("not_food", evidence);
        if (!self.CanConsumeItem(found, true))
            return Outcome.Failed("cannot_eat_now", evidence);
        var eaten = self.ConsumeItem(self.GetInventory(), found, true);
        evidence["foods_after"] = self.GetFoods().Count;
        return eaten ? Outcome.Succeeded("eaten", evidence) : Outcome.Failed("consume_failed", evidence);
    }

    public JObject Progress(Player self) => new JObject();

    public void Stop(Player self) { }
}

internal sealed class Pickup : IAction
{
    const float Reach = 2.5f;
    readonly string id;
    string token, name;
    int before = -1;
    float requestedAt = -1f;

    public string Phase { get; private set; } = "reaching";

    public Pickup(string id)
    {
        this.id = id;
    }

    public Outcome Tick(Player self, float now)
    {
        var inventory = self.GetInventory();
        var drop = Ids.Find(id)?.GetComponent<ItemDrop>();
        if (before >= 0 && drop == null)
        {
            var added = inventory.CountItems(token) - before;
            var evidence = new JObject { ["item"] = name, ["added"] = added, ["phase"] = Phase };
            return added > 0 ? Outcome.Succeeded("picked_up", evidence) : Outcome.Failed("taken_by_someone_else", evidence);
        }
        if (drop == null)
            return Outcome.Failed("not_found");
        token = drop.m_itemData.m_shared.m_name;
        name = Snapshot.Localize(token);
        // move_to의 도착 판정과 같은 기준(가장 가까운 콜라이더 표면)으로 잰다. 기준이 다르면 "도착했는데 손이 안 닿는" 일이 생긴다.
        var distance = Geometry.HorizontalDistance(self.transform.position, Geometry.ApproachPoint(self, drop));
        if (distance > Reach)
            return Outcome.Failed("out_of_reach", new JObject { ["distance_m"] = Math.Round(distance, 2) });
        if (drop.InTar())
            return Outcome.Failed("in_tar");
        if (before < 0)
            before = inventory.CountItems(token);
        if (!drop.CanPickup(false))
        {
            // 서버나 다른 피어가 소유한 드롭은 게임의 소유권 요청을 거친다. 소유자를 덮어쓰지 않는다.
            if (requestedAt < 0)
            {
                drop.RequestOwn();
                requestedAt = now;
                Phase = "requesting_ownership";
            }
            return now - requestedAt > 3f ? Outcome.Failed("ownership_timeout") : null;
        }
        Phase = "picking_up";
        if (!self.Pickup(drop.gameObject, true, false))
            return Outcome.Failed(inventory.HaveEmptySlot() ? "pickup_failed" : "inventory_full", new JObject { ["item"] = name });
        var count = inventory.CountItems(token) - before;
        return count > 0 ? Outcome.Succeeded("picked_up", new JObject { ["item"] = name, ["added"] = count }) : null;
    }

    public JObject Progress(Player self) => new JObject { ["phase"] = Phase };

    public void Stop(Player self) { }
}

internal sealed class Interact : IAction
{
    static readonly System.Reflection.MethodInfo PlayerInteract = AccessTools.Method(typeof(Player), "Interact");
    readonly string id;
    readonly bool alt;
    int frames;

    public string Phase => "interacting";

    public Interact(string id, bool alt)
    {
        this.id = id;
        this.alt = alt;
    }

    public Outcome Tick(Player self, float now)
    {
        var go = Ids.Find(id);
        var target = Primitives.Primary(go);
        if (target == null)
            return Outcome.Failed("not_found");
        var point = Geometry.ApproachPoint(self, target);
        var eye = self.m_eye != null ? self.m_eye.position : self.transform.position + Vector3.up * 1.6f;
        var distance = Vector3.Distance(eye, point);
        if (distance > self.m_maxInteractDistance + 0.5f)
            return Outcome.Failed("out_of_reach", new JObject { ["distance_m"] = Math.Round(distance, 2) });
        var direction = point - self.transform.position;
        direction.y = 0;
        if (direction.sqrMagnitude > .0001f)
            Motor.Intent.LookWorld = direction.normalized;
        if (++frames < 3)
            return null;
        if (self.InAttack() || self.InDodge())
            return now > 0 && frames > 90 ? Outcome.Failed("busy") : null;
        PlayerInteract.Invoke(self, new object[] { go, false, alt });
        // 룬스톤 글 창과 베그비시르가 연 큰 지도는 사람이 읽고 닫는다. 열려 있으면 몸이 입력을 받지 않는다(TakeInput).
        var evidence = new JObject { ["target"] = Snapshot.Localize((target as Hoverable)?.GetHoverName() ?? "") };
        // 제작대를 열어 본 것이면 열렸는지(못 쓰면 게임이 이유를 메시지로 띄운다) 알리고 창은 닫는다.
        if (go.GetComponentInParent<CraftingStation>() != null)
        {
            evidence["opened"] = InventoryGui.IsVisible();
            if (InventoryGui.IsVisible())
                InventoryGui.instance.Hide();
        }
        if (TextViewer.instance != null && TextViewer.instance.IsVisible())
        {
            TextViewer.instance.Hide();
            evidence["read"] = true;
        }
        // 침대: 누웠는지(못 누우면 게임이 이유를 메시지로 띄운다).
        if (go.GetComponentInParent<Bed>() != null)
            evidence["in_bed"] = self.InBed();
        if (Minimap.IsOpen())
        {
            Minimap.instance.SetMapMode(Minimap.MapMode.Small);
            evidence["map_opened"] = true;
        }
        return Outcome.Succeeded("interacted", evidence);
    }

    public JObject Progress(Player self) => new JObject();

    public void Stop(Player self) => Motor.Intent.LookWorld = null;
}

// 인벤토리의 물건을 대상에 쓴다: 제단에 트로피, 요리대에 날고기, 불에 장작. 사람은 대상을 보고 그 물건의 단축키를 누르고,
// 게임은 시선 대상의 Interactable.UseItem을 부른다(Humanoid.UseItem). 몸이 대상을 보게 돌린 뒤 같은 인터페이스를 부른다.
// 쓰였는지는 대상의 반환값과 인벤토리 감소로 본다. 거절되면 게임이 띄우는 메시지(예: 잘못된 제물)가 game_message로 따로 간다.
internal sealed class UseItem : IAction
{
    readonly string item, id;
    int frames;

    public string Phase => "using";

    public UseItem(string item, string id)
    {
        this.item = item;
        this.id = id;
    }

    public Outcome Tick(Player self, float now)
    {
        var go = Ids.Find(id);
        var target = go != null ? go.GetComponentInParent<Interactable>() : null;
        if (target == null)
            return Outcome.Failed(go == null ? "not_found" : "not_usable");
        var component = (Component)target;
        var point = Geometry.ApproachPoint(self, component);
        var distance = Vector3.Distance(self.GetEyePoint(), point);
        if (distance > self.m_maxInteractDistance + 0.5f)
            return Outcome.Failed("out_of_reach", new JObject { ["distance_m"] = Math.Round(distance, 2) });
        Motor.Intent.LookWorld = (point - self.GetEyePoint()).normalized;
        if (++frames < 3)
            return null;
        var found = Primitives.FindItem(self, item);
        if (found == null)
            return Outcome.Failed("item_not_found");
        var token = found.m_shared.m_name;
        var before = self.GetInventory().CountItems(token);
        self.FaceLookDirection();
        var used = target.UseItem(self, found);
        var evidence = new JObject
        {
            ["item"] = Snapshot.Localize(token),
            ["used"] = before - self.GetInventory().CountItems(token),
            ["target"] = Snapshot.Localize((target as Hoverable)?.GetHoverName() ?? ""),
        };
        return used ? Outcome.Succeeded("used", evidence) : Outcome.Failed("refused", evidence);
    }

    public JObject Progress(Player self) => new JObject();

    public void Stop(Player self) => Motor.Intent.LookWorld = null;
}

// 물건을 내려놓는다(건네기). 게임은 시선이 아니라 몸이 향한 방향으로 던지므로(Humanoid.DropItem) 받을 쪽으로 몸을 먼저 돌린다.
internal sealed class Drop : IAction
{
    readonly string item;
    readonly int count;
    readonly Target toward;
    int frames;

    public string Phase => "dropping";

    public Drop(string item, int count, Target toward)
    {
        this.item = item;
        this.count = count;
        this.toward = toward;
    }

    public Outcome Tick(Player self, float now)
    {
        if (toward != null)
        {
            if (!toward.TryResolve(self, out var point))
                return Outcome.Failed("target_lost");
            var direction = point - self.transform.position;
            direction.y = 0;
            if (direction.sqrMagnitude > .0001f)
                Motor.Intent.LookWorld = direction.normalized;
        }
        if (++frames < 3)
            return null;
        var found = Primitives.FindItem(self, item);
        if (found == null)
            return Outcome.Failed("not_found");
        var token = found.m_shared.m_name;
        var inventory = self.GetInventory();
        var before = inventory.CountItems(token);
        self.FaceLookDirection();
        var dropped = 0;
        // 같은 물건이 여러 칸에 나뉘어 있을 수 있다. 요청한 수만큼 칸마다 내려놓는다.
        while (dropped < count && (found = Primitives.FindItem(self, item)) != null)
        {
            var amount = Math.Min(count - dropped, found.m_stack);
            if (!self.DropItem(inventory, found, amount))
                break;
            dropped = before - inventory.CountItems(token);
        }
        var evidence = new JObject { ["item"] = Snapshot.Localize(token), ["dropped"] = dropped, ["left"] = inventory.CountItems(token) };
        return dropped > 0 ? Outcome.Succeeded("dropped", evidence) : Outcome.Failed("drop_failed", evidence);
    }

    public JObject Progress(Player self) => new JObject();

    public void Stop(Player self) => Motor.Intent.LookWorld = null;
}

internal sealed class Attack : IAction
{
    readonly string id;
    readonly int swings;
    readonly bool sneak;
    int done, notStarted, meleeChecksAtStart = -1;
    bool swingSeen;
    float? hpBefore;
    float swingStarted = -1f, aimSince = -1f;

    public string Phase { get; private set; } = "aiming";

    // sneak: 웅크린 채로 친다(눈치채지 못한 상대에게 몰래 치기).
    public Attack(string id, int swings, bool sneak = false)
    {
        this.id = id;
        this.swings = swings;
        this.sneak = sneak;
    }

    public Outcome Tick(Player self, float now)
    {
        Motor.Intent.Crouch = sneak;
        if (meleeChecksAtStart < 0)
            meleeChecksAtStart = Events.Hooks.MeleeChecks;
        Component target = null;
        if (id != null)
        {
            target = Primitives.Primary(Ids.Find(id));
            if (target == null)
                return done > 0 ? Outcome.Succeeded("destroyed", Evidence(null)) : Outcome.Failed("not_found");
        }

        if (Phase == "swinging")
        {
            // InAttack은 애니메이터 상태 태그를 본다. StartAttack 직후 몇 프레임은 전이가 시작되지 않아 false일 수 있으니,
            // 공격 애니메이션이 실제로 시작된 것을 본 뒤에만 한 번 휘두른 것으로 센다.
            var inAttack = self.InAttack();
            swingSeen |= inAttack;
            if ((!swingSeen && now - swingStarted < 1f) || (inAttack && now - swingStarted < 3f))
                return null;
            if (!swingSeen)
            {
                if (++notStarted >= 3)
                    return Outcome.Failed("swing_not_started", Evidence(target));
                Phase = "aiming";
                aimSince = -1f;
                return null;
            }
            done++;
            if (done >= swings)
            {
                var evidence = Evidence(target);
                if (evidence["hp_before"] != null && (double)evidence["hp_before"] == (double?)evidence["hp_after"])
                    LogMiss(self, target, evidence);
                return Outcome.Succeeded("swung", evidence);
            }
            Phase = "aiming";
            aimSince = -1f;
        }

        if (target != null)
        {
            var point = Geometry.ApproachPoint(self, target);
            var distance = Geometry.HorizontalDistance(self.transform.position, point);
            var reach = Reach(self) + 0.4f;
            if (distance > reach)
                return Outcome.Failed("out_of_reach", new JObject { ["distance_m"] = Math.Round(distance, 2), ["reach_m"] = Math.Round(reach, 2) });
            if (!WithinSwingBand(self, target, distance, out var vertical))
                return Outcome.Failed("out_of_reach", new JObject { ["distance_m"] = Math.Round(distance, 2), ["vertical_m"] = Math.Round(vertical, 2) });
            Motor.Intent.LookWorld = Geometry.AimDirection(self, target);
            if (hpBefore == null)
                hpBefore = Primitives.TargetHealth(target);
        }
        if (aimSince < 0)
            aimSince = now;
        if (now - aimSince < 0.15f)
            return null;
        Events.Hooks.SwingAt(target);
        if (self.StartAttack(target as Character, false))
        {
            Phase = "swinging";
            swingStarted = now;
            swingSeen = false;
            return null;
        }
        return now - aimSince > 1.5f ? Outcome.Failed("cannot_attack", new JObject { ["stamina"] = Math.Round(self.GetStamina(), 1) }) : null;
    }

    // 근접 판정은 공격 기준점 + m_attackHeight 높이에서 반지름 m_attackRayWidth로 수평으로 휩쓸고, 무기가 기울일 수 있는 만큼
    // (m_maxYAngle)만 위아래로 더 닿는다. 생물에게는 m_attackHeightChar1·2 높이에서 반지름을 m_attackRayWidthCharExtra만큼 키운
    // 휩쓸기를 더 한다(Attack.DoMeleeAttack). 대상의 높이 범위가 어느 띠에도 닿지 않으면 휘둘러도 맞지 않는다.
    static bool WithinSwingBand(Player self, Component target, float distance, out float vertical)
    {
        var attack = self.GetCurrentWeapon()?.m_shared.m_attack;
        var origin = self.transform;
        if (attack != null && attack.m_attackOriginJoint.Length > 0)
            origin = Utils.FindChild(self.GetVisual().transform, attack.m_attackOriginJoint) ?? origin;
        var swingY = origin.position.y + (attack != null ? attack.m_attackHeight : 1f);
        var width = attack != null ? attack.m_attackRayWidth : .3f;
        var tilt = attack != null ? distance * Mathf.Tan(attack.m_maxYAngle * Mathf.Deg2Rad) : 0f;
        var bands = new System.Collections.Generic.List<(float y, float width)> { (swingY, width) };
        if (target is Character && attack != null && (attack.m_attackRayWidthCharExtra > 0f || attack.m_attackHeightChar1 != 0f))
        {
            bands.Add((swingY + attack.m_attackHeightChar1, width + attack.m_attackRayWidthCharExtra));
            if (attack.m_attackHeightChar2 != attack.m_attackHeightChar1)
                bands.Add((swingY + attack.m_attackHeightChar2, width + attack.m_attackRayWidthCharExtra));
        }
        float low = float.MaxValue, high = float.MinValue;
        foreach (var collider in target.GetComponentsInChildren<Collider>())
        {
            if (!collider.enabled || collider.isTrigger)
                continue;
            low = Mathf.Min(low, collider.bounds.min.y);
            high = Mathf.Max(high, collider.bounds.max.y);
        }
        if (low > high)
            low = high = target.transform.position.y;
        vertical = bands.Min(band => Mathf.Max(0f, (band.y < low ? low - band.y : band.y > high ? band.y - high : 0f) - band.width - tilt));
        return vertical <= .2f;
    }

    // 맞지 않은 휘두르기의 원인을 찾기 위한 기록. 무기 판정 수치는 두뇌에 보내지 않고(정보 동등성) 플러그인 로그에만 남긴다.
    static void LogMiss(Player self, Component target, JObject evidence)
    {
        var attack = self.GetCurrentWeapon()?.m_shared.m_attack;
        var text = "THORKELL attack missed " + evidence.ToString(Newtonsoft.Json.Formatting.None) + ": weapon=" + (self.GetCurrentWeapon()?.m_shared.m_name ?? "none");
        if (attack != null)
            text += " type=" + attack.m_attackType + " range=" + attack.m_attackRange + " height=" + attack.m_attackHeight
                + " angle=" + attack.m_attackAngle + " ray_width=" + attack.m_attackRayWidth + " max_y=" + attack.m_maxYAngle
                + " offset=" + attack.m_attackOffset;
        if (target != null)
        {
            var point = Geometry.ApproachPoint(self, target);
            text += " feet=" + self.transform.position.ToString("F2") + " eye=" + self.GetEyePoint().ToString("F2")
                + " approach=" + point.ToString("F2") + " look=" + self.GetLookDir().ToString("F2");
            foreach (var collider in target.GetComponentsInChildren<Collider>())
                if (collider.enabled && !collider.isTrigger)
                    text += " collider=" + collider.bounds.center.ToString("F2") + "/" + collider.bounds.size.ToString("F2");
        }
        BodyPlugin.Instance.Log.LogInfo(text);
    }

    JObject Evidence(Component target)
    {
        var after = target != null ? Primitives.TargetHealth(target) : 0f;
        var evidence = new JObject { ["swings"] = done, ["melee_checks"] = Events.Hooks.MeleeChecks - meleeChecksAtStart };
        if (hpBefore.HasValue)
            evidence["hp_before"] = Math.Round(hpBefore.Value, 1);
        if (after.HasValue)
            evidence["hp_after"] = Math.Round(after.Value, 1);
        evidence["destroyed"] = target == null;
        return evidence;
    }

    static float Reach(Player self)
    {
        var weapon = self.GetCurrentWeapon();
        return weapon != null && weapon.m_shared.m_attack != null && weapon.m_shared.m_attack.m_attackRange > 0
            ? weapon.m_shared.m_attack.m_attackRange
            : 1.5f;
    }

    public JObject Progress(Player self) => new JObject { ["phase"] = Phase, ["swings"] = done };

    public void Stop(Player self)
    {
        Motor.Intent.LookWorld = null;
        Motor.Intent.Crouch = false;  // 치고 나면 일어선다
    }
}

// 활 쏘기. 사람처럼 공격 버튼을 누른 채 시위를 끝까지 당기고 놓아서 쏜다(Player.UpdateAttackBowDraw → StartAttack).
// 화살은 시선 방향으로 나가고(Humanoid.GetAimDir = GetLookDir), 중력과 공기저항으로 떨어진다(Projectile.FixedUpdate).
// 그래서 같은 식으로 궤적을 따져 위로 겨누고, 움직이는 대상은 날아가는 동안 갈 자리를 겨눈다(사람이 감으로 하는 것).
// 맞혔는지는 대상 체력 감소로, 쏘았는지는 화살 감소로 본다.
internal sealed class Shoot : IAction
{
    const float MaxRange = 60f;
    const float DrawTimeout = 4f;
    readonly string id;
    readonly Vector3? strafe;
    readonly bool waitHit;
    float started = -1f, releasedAt = -1f, flight;
    float? hpBefore;
    int arrowsBefore = -1;
    string ammoToken;

    public string Phase { get; private set; } = "aiming";

    // strafe: 시위를 당기는 동안 걸어갈 수평 방향(사람이 옆으로 움직이며 당기듯). 없으면 서서 쏜다.
    // waitHit: false면 화살이 나가자마자 끝낸다(사람은 맞는지 보기 전에 다음 화살을 당긴다). 맞힌 것은 피해 이벤트로 안다.
    public Shoot(string id, Vector3? strafe, bool waitHit)
    {
        this.id = id;
        this.waitHit = waitHit;
        if (strafe.HasValue)
        {
            var flat = new Vector3(strafe.Value.x, 0f, strafe.Value.z);
            this.strafe = flat.sqrMagnitude > .0001f ? flat.normalized : (Vector3?)null;
        }
    }

    public Outcome Tick(Player self, float now)
    {
        var target = Primitives.Primary(Ids.Find(id)) as Character;
        if (started < 0)
            started = now;
        var weapon = self.GetCurrentWeapon();
        if (releasedAt >= 0)
            return AfterRelease(self, target, now);
        if (target == null)
            return Outcome.Failed("not_found");
        if (weapon == null || !weapon.m_shared.m_attack.m_bowDraw)
            return Outcome.Failed("no_bow");
        var ammo = self.GetAmmoItem();
        if (ammo == null || !self.GetInventory().ContainsItem(ammo) || ammo.m_shared.m_ammoType != weapon.m_shared.m_ammoType)
            ammo = self.GetInventory().GetAmmoItem(weapon.m_shared.m_ammoType);
        if (ammo == null)
            return Outcome.Failed("no_ammo");
        ammoToken = ammo.m_shared.m_name;
        var center = target.GetCenterPoint();
        var distance = Vector3.Distance(self.GetEyePoint(), center);
        if (distance > MaxRange)
            return Outcome.Failed("out_of_range", new JObject { ["distance_m"] = Math.Round(distance, 1) });
        if (!Geometry.SeesCreature(self, target))
            return Outcome.Failed("no_line_of_sight", new JObject { ["distance_m"] = Math.Round(distance, 1), ["blocked_by"] = Geometry.Blocker(self, target.GetTopPoint()) });
        if (hpBefore == null)
        {
            hpBefore = target.GetHealth();
            arrowsBefore = self.GetInventory().CountItems(ammoToken);
        }

        var projectile = ammo.m_shared.m_attack.m_attackProjectile != null ? ammo.m_shared.m_attack.m_attackProjectile.GetComponent<Projectile>() : null;
        var speed = weapon.m_shared.m_attack.m_projectileVel + ammo.m_shared.m_attack.m_projectileVel;
        var aim = Ballistics.Aim(SpawnPoint(self, weapon.m_shared.m_attack), center, target.GetVelocity(), speed,
            projectile != null ? projectile.m_gravity : 0f, projectile != null ? projectile.m_drag : 0f, out flight);
        Motor.Intent.LookWorld = aim;
        Motor.Intent.AttackHold = true;
        if (strafe.HasValue)
            Motor.Intent.MoveWorld = strafe.Value;
        Phase = "drawing";
        var drawn = self.GetAttackDrawPercentage();
        if (drawn >= .99f && now - started > .3f)
        {
            Motor.Intent.AttackHold = false;
            releasedAt = now;
            Phase = "released";
            return null;
        }
        return now - started > DrawTimeout
            ? Outcome.Failed("cannot_draw", new JObject { ["draw"] = Math.Round(drawn, 2), ["stamina"] = Math.Round(self.GetStamina(), 1) })
            : null;
    }

    // 화살이 나오는 자리(Attack.GetProjectileSpawnPoint와 같은 식). 눈에서 겨누면 활 높이·옆 차이만큼 빗나간다.
    static Vector3 SpawnPoint(Player self, global::Attack attack)
    {
        var origin = attack.m_attackOriginJoint.Length > 0 ? Utils.FindChild(self.GetVisual().transform, attack.m_attackOriginJoint) : null;
        var body = self.transform;
        return (origin != null ? origin.position : body.position) + body.up * attack.m_attackHeight
            + body.forward * attack.m_attackRange + body.right * attack.m_attackOffset;
    }

    Outcome AfterRelease(Player self, Character target, float now)
    {
        var arrows = self.GetInventory().CountItems(ammoToken);
        var fired = arrows < arrowsBefore;
        if (!fired)
            return now - releasedAt > 1f ? Outcome.Failed("not_fired", new JObject { ["arrows"] = arrows }) : null;
        if (!waitHit)
        {
            Motor.Intent.MoveWorld = Vector3.zero;
            return Outcome.Succeeded("fired", new JObject { ["arrows_left"] = arrows });
        }
        Phase = "flying";
        // 대상이 사라진 것(멀어져 안 불러와짐 등)은 죽은 것이 아니다. 죽음은 보이는 IsDead로만 센다.
        var hpAfter = target != null ? target.GetHealth() : 0f;
        var hit = Events.Hooks.HitSince(id, releasedAt) || (target != null && (target.IsDead() || hpAfter < hpBefore - .01f));
        if (!hit && now - releasedAt < flight + .8f)
            return null;
        Motor.Intent.MoveWorld = Vector3.zero;
        // 두뇌에는 체력바(비율)만 준다. 체력 숫자는 화면에 안 나온다.
        var max = target != null ? Mathf.Max(1f, target.GetMaxHealth()) : 1f;
        var evidence = new JObject
        {
            ["hit"] = hit,
            ["health_before"] = Math.Round((hpBefore ?? 0f) / max, 3),
            ["health_after"] = Math.Round(hpAfter / max, 3),
            ["killed"] = target != null && target.IsDead(),
            ["target_gone"] = target == null,
            ["arrows_left"] = arrows,
        };
        return Outcome.Succeeded(hit ? "hit" : "missed", evidence);
    }

    public JObject Progress(Player self) => new JObject { ["phase"] = Phase, ["draw"] = Math.Round(self.GetAttackDrawPercentage(), 2) };

    public void Stop(Player self)
    {
        Motor.Intent.AttackHold = false;
        Motor.Intent.LookWorld = null;
        Motor.Intent.MoveWorld = Vector3.zero;
    }
}

// 구르기. 사람은 막기(오른쪽 버튼)를 누른 채 점프하거나 회피 키를 누른다. 구를 방향은 이동 방향이다.
// 구른 것은 InDodge가 실제로 시작됐는지로 본다(스태미나가 모자라면 시작되지 않는다).
internal sealed class Dodge : IAction
{
    readonly Vector3? toward;
    float started = -1f;
    bool seen;

    public string Phase => seen ? "dodging" : "starting";

    public Dodge(Vector3? toward)
    {
        this.toward = toward;
    }

    public Outcome Tick(Player self, float now)
    {
        if (started < 0)
        {
            started = now;
            var direction = toward.HasValue ? toward.Value - self.transform.position : -self.transform.forward;
            direction.y = 0;
            Motor.Intent.MoveWorld = direction.sqrMagnitude > .0001f ? direction.normalized : -self.transform.forward;
            Motor.Intent.Dodge = true;
            return null;
        }
        seen |= self.InDodge();
        if (seen && !self.InDodge())
            return Outcome.Succeeded("dodged", new JObject { ["stamina"] = Math.Round(self.GetStamina(), 1) });
        if (!seen && now - started > .6f)
            return Outcome.Failed("dodge_not_started", new JObject { ["stamina"] = Math.Round(self.GetStamina(), 1) });
        return now - started > 2f ? Outcome.Succeeded("dodged") : null;
    }

    public JObject Progress(Player self) => new JObject { ["phase"] = Phase };

    public void Stop(Player self) => Motor.Intent.MoveWorld = Vector3.zero;
}

internal sealed class Wait : IAction
{
    readonly float seconds;
    float started = -1f;

    public string Phase => "waiting";

    public Wait(float seconds)
    {
        this.seconds = seconds;
    }

    public Outcome Tick(Player self, float now)
    {
        if (started < 0)
            started = now;
        return now - started >= seconds ? Outcome.Succeeded("waited") : null;
    }

    public JObject Progress(Player self) => new JObject();

    public void Stop(Player self) { }
}
