using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using HarmonyLib;
using Newtonsoft.Json.Linq;
using Thorkell.Body.Perception;
using UnityEngine;

namespace Thorkell.Body.Actions;

// 사람이 하는 그대로 만든다: 제작대를 열고(E, 맨손이면 Tab), 목록에서 레시피를 고르고, 제작 버튼을 누른다.
// 게임은 제작 시간(m_craftDuration)이 지나면 InventoryGui.DoCrafting으로 재료를 쓰고 물건을 넣는다.
// 만들었는지는 인벤토리 증가로 본다. 제작대를 못 쓰면(지붕 없음, 불 없음) 게임 메시지가 game_message로 따로 간다.
internal sealed class Craft : IAction
{
    static readonly AccessTools.FieldRef<InventoryGui, IList> Available = AccessTools.FieldRefAccess<InventoryGui, IList>("m_availableRecipes");
    static readonly System.Reflection.MethodInfo SetRecipe = AccessTools.Method(typeof(InventoryGui), "SetRecipe");
    static readonly System.Reflection.MethodInfo CraftPressed = AccessTools.Method(typeof(InventoryGui), "OnCraftPressed");
    static readonly System.Reflection.MethodInfo UpdatePanel = AccessTools.Method(typeof(InventoryGui), "UpdateCraftingPanel");
    static readonly System.Reflection.MethodInfo PlayerInteract = AccessTools.Method(typeof(Player), "Interact");
    const float CraftTimeout = 8f;

    readonly string item;
    readonly int count;
    readonly string stationId;
    string token;
    int made, before;
    float pressedAt = -1f, openedAt = -1f;

    public string Phase { get; private set; } = "opening";

    public Craft(string item, int count, string stationId)
    {
        this.item = item;
        this.count = count;
        this.stationId = stationId;
    }

    public Outcome Tick(Player self, float now)
    {
        var gui = InventoryGui.instance;
        if (gui == null)
            return Outcome.Failed("no_gui");
        switch (Phase)
        {
            case "opening":
                return Open(self, gui, now);
            case "selecting":
                return Select(self, gui, now);
            default:
                return Wait(self, gui, now);
        }
    }

    Outcome Open(Player self, InventoryGui gui, float now)
    {
        if (stationId != null)
        {
            var station = Ids.Find(stationId)?.GetComponentInParent<CraftingStation>();
            if (station == null)
                return Outcome.Failed("station_not_found");
            if (!station.InUseDistance(self))
                return Outcome.Failed("out_of_reach", new JObject { ["distance_m"] = Math.Round(Vector3.Distance(self.transform.position, station.transform.position), 2) });
            var direction = station.transform.position - self.transform.position;
            direction.y = 0;
            if (direction.sqrMagnitude > .0001f)
                Motor.Intent.LookWorld = direction.normalized;
            PlayerInteract.Invoke(self, new object[] { station.gameObject, false, false });
            if (self.GetCurrentCraftingStation() != station || !InventoryGui.IsVisible())
                return Outcome.Failed("station_unusable", new JObject { ["station"] = Snapshot.Localize(station.m_name) });
        }
        else
        {
            self.SetCraftingStation(null);
            gui.Show(null);
        }
        openedAt = now;
        Phase = "selecting";
        return null;
    }

    Outcome Select(Player self, InventoryGui gui, float now)
    {
        if (!InventoryGui.IsVisible())
            return now - openedAt > 1f ? Outcome.Failed("menu_closed") : null;
        UpdatePanel.Invoke(gui, new object[] { false });
        var recipes = Available(gui);
        int index = -1;
        Recipe recipe = null;
        for (var i = 0; i < recipes.Count; i++)
        {
            var pair = Traverse.Create(recipes[i]);
            var candidate = pair.Property<Recipe>("Recipe").Value;
            var upgrade = pair.Property<ItemDrop.ItemData>("ItemData").Value;
            if (candidate == null || upgrade != null)
                continue;
            var shared = candidate.m_item.m_itemData.m_shared;
            if (shared.m_name == item || string.Equals(Snapshot.Localize(shared.m_name), item, StringComparison.OrdinalIgnoreCase))
            {
                index = i;
                recipe = candidate;
                break;
            }
        }
        if (recipe == null)
            return Close(Outcome.Failed("recipe_not_in_menu", new JObject { ["item"] = item, ["station"] = StationName(self), ["made"] = made }));
        token = recipe.m_item.m_itemData.m_shared.m_name;
        if (!self.HaveRequirements(recipe, false, 1))
            return Close(Outcome.Failed("missing_requirements", new JObject { ["item"] = Snapshot.Localize(token), ["missing"] = Missing(self, recipe), ["made"] = made }));
        SetRecipe.Invoke(gui, new object[] { index, false });
        before = self.GetInventory().CountItems(token);
        CraftPressed.Invoke(gui, Array.Empty<object>());
        pressedAt = now;
        Phase = "crafting";
        return null;
    }

    Outcome Wait(Player self, InventoryGui gui, float now)
    {
        if (self.GetInventory().CountItems(token) > before)
        {
            made++;
            if (made >= count)
                return Close(Outcome.Succeeded("crafted", Evidence(self)));
            Phase = "selecting";
            return null;
        }
        if (!InventoryGui.IsVisible())
            return Outcome.Failed("menu_closed", Evidence(self));
        return now - pressedAt > CraftTimeout ? Close(Outcome.Failed("craft_timeout", Evidence(self))) : null;
    }

    JObject Evidence(Player self) => new JObject
    {
        ["item"] = Snapshot.Localize(token),
        ["made"] = made,
        ["have"] = self.GetInventory().CountItems(token),
        ["station"] = StationName(self),
    };

    static string StationName(Player self)
    {
        var station = self.GetCurrentCraftingStation();
        return station != null ? Snapshot.Localize(station.m_name) : "";
    }

    internal static JArray Missing(Player self, Recipe recipe)
    {
        var missing = new JArray();
        foreach (var requirement in recipe.m_resources)
        {
            if (requirement.m_resItem == null || requirement.m_upgraderResource)
                continue;
            var need = requirement.GetAmount(1);
            var have = self.GetInventory().CountItems(requirement.m_resItem.m_itemData.m_shared.m_name);
            if (have < need)
                missing.Add(new JObject { ["name"] = Snapshot.Localize(requirement.m_resItem.m_itemData.m_shared.m_name), ["need"] = need, ["have"] = have });
        }
        return missing;
    }

    static Outcome Close(Outcome outcome)
    {
        if (InventoryGui.IsVisible())
            InventoryGui.instance.Hide();
        return outcome;
    }

    public JObject Progress(Player self) => new JObject { ["phase"] = Phase, ["made"] = made };

    public void Stop(Player self)
    {
        if (InventoryGui.IsVisible())
            InventoryGui.instance.Hide();
        Motor.Intent.LookWorld = null;
    }
}

// 망치로 건축물 하나를 짓는다. 사람은 망치를 들고 건축 메뉴에서 고르고, 조준점을 지을 자리에 두고, 휠로 돌린 뒤 클릭한다.
// 고르기와 돌리기는 게임의 메뉴 함수(SetBuildCategory, SetSelectedPiece, m_placeRotation)로 하고, 조준점은 PlaceAim이
// 정한다(Player.PieceRayTest가 카메라 대신 눈에서 그 자리로 쏜 광선을 쓴다). 클릭은 m_placePressedTime으로 누르고,
// 나머지(위치 검사, 스냅, 재료·스태미나 소모)는 게임의 UpdatePlacement가 그대로 한다.
// 지었는지는 그 자리 근처에 토르켈이 만든 새 건축물이 생겼는지로 본다.
internal sealed class Place : IAction
{
    static readonly AccessTools.FieldRef<Player, float> PlacePressed = AccessTools.FieldRefAccess<Player, float>("m_placePressedTime");
    static readonly AccessTools.FieldRef<Player, int> PlaceRotation = AccessTools.FieldRefAccess<Player, int>("m_placeRotation");
    static readonly AccessTools.FieldRef<Player, PieceTable> BuildPieces = AccessTools.FieldRefAccess<Player, PieceTable>("m_buildPieces");
    static readonly AccessTools.FieldRef<Player, Player.PlacementStatus> Status = AccessTools.FieldRefAccess<Player, Player.PlacementStatus>("m_placementStatus");
    static readonly System.Reflection.MethodInfo UpdateGhost = AccessTools.Method(typeof(Player), "UpdatePlacementGhost");
    // 겨눈 자리가 안 되면 사람이 조준점을 조금씩 옮겨 보듯 둘레를 훑는다(반지름 m, 각 반지름에서 8방향).
    static readonly float[] SlideRadii = { .75f, 1.5f, 2.25f, 3f };
    const float SettleSeconds = 1.5f;

    readonly string pieceName;
    readonly Vector3 point;
    readonly float yaw;
    Piece prefab;
    HashSet<ZDOID> existing;
    Vector3? aimAt;
    int tried, rechecks;
    int presses;
    float pressedAt = -1f, readyAt = -1f;

    public string Phase { get; private set; } = "selecting";

    readonly bool exact;
    readonly float within;

    // exact: 땅이 아니라 그 지점(이미 지은 벽 위 등)을 겨눈다. 지붕처럼 공중에 놓는 것에 쓴다.
    // within(m, 0이면 없음): 미리보기가 그 지점에서 이만큼 안에 있어야만 짓는다. 둘레로 옮기지 않는다(불 위 요리대).
    public Place(string pieceName, Vector3 point, float yaw, bool exact, float within)
    {
        this.pieceName = pieceName;
        this.point = point;
        this.yaw = yaw;
        this.exact = exact;
        this.within = within;
    }

    public Outcome Tick(Player self, float now)
    {
        var table = BuildPieces(self);
        if (table == null)
            return Outcome.Failed("no_build_tool");
        if (prefab == null)
        {
            prefab = table.m_availablePieces.FirstOrDefault(p => p.m_name == pieceName || string.Equals(Snapshot.Localize(p.m_name), pieceName, StringComparison.OrdinalIgnoreCase));
            if (prefab == null)
                return Outcome.Failed("piece_not_known", new JObject { ["piece"] = pieceName });
            if (!table.GetPieceIndex(prefab, out var index, out var category))
                return Outcome.Failed("piece_not_in_menu", new JObject { ["piece"] = pieceName });
            self.SetBuildCategory(category);
            self.SetSelectedPiece(index);
            PlaceRotation(self) = Mathf.RoundToInt(yaw / 22.5f) & 15;
            existing = new HashSet<ZDOID>(Nearby().Select(p => p.GetComponent<ZNetView>().GetZDO().m_uid));
        }
        var eye = self.GetEyePoint();
        var reach = Vector3.Distance(eye, point);
        if (reach > self.m_maxPlaceDistance + prefab.m_extraPlacementDistance)
            return Outcome.Failed("out_of_reach", new JObject { ["distance_m"] = Math.Round(reach, 2) });
        if (!aimAt.HasValue)
            aimAt = Find(self);
        PlaceAim.Point = aimAt ?? (exact ? point : Ground(point));
        Motor.Intent.LookWorld = (PlaceAim.Point.Value - eye).normalized;

        var built = Nearby().FirstOrDefault(p => !existing.Contains(p.GetComponent<ZNetView>().GetZDO().m_uid) && IsMine(self, p));
        if (built != null)
            return Outcome.Succeeded("placed", new JObject
            {
                ["piece"] = Snapshot.Localize(built.m_name),
                ["id"] = Ids.Of(built),
                ["pos"] = new JArray(Math.Round(built.transform.position.x, 2), Math.Round(built.transform.position.y, 2), Math.Round(built.transform.position.z, 2)),
                ["offset_m"] = Math.Round(Vector3.Distance(built.transform.position, point), 2),
                ["off_aim_m"] = aimAt.HasValue ? Math.Round(Geometry.HorizontalDistance(built.transform.position, aimAt.Value), 2) : -1,
                ["first_status"] = FirstStatus,
                ["ground_y"] = GroundY(built.transform.position),
            });

        if (Phase == "selecting")
        {
            // 조준점을 옮긴 뒤 게임이 유령(미리보기)을 그 자리에 다시 놓을 때까지 몇 프레임 기다린다.
            if (readyAt < 0)
                readyAt = now + .3f;
            if (now < readyAt)
                return null;
            if (!self.HaveRequirements(prefab, Player.RequirementMode.CanBuild))
                return Outcome.Failed("missing_requirements", new JObject { ["piece"] = Snapshot.Localize(prefab.m_name), ["missing"] = MissingFor(self, prefab), ["needs_station"] = prefab.m_craftingStation != null ? Snapshot.Localize(prefab.m_craftingStation.m_name) : null });
            // 누르기 직전에 미리보기를 다시 본다. 고른 뒤 몇 프레임 사이에 덤불 위로 옮겨 간 일이 있었다.
            if (aimAt.HasValue && !StillOnTarget(self, aimAt.Value) && rechecks++ < 3)
            {
                aimAt = Find(self);
                readyAt = -1f;
                return null;
            }
            var status = Status(self);
            if (status != Player.PlacementStatus.Valid || !aimAt.HasValue)
                return Outcome.Failed("invalid_placement", new JObject
                {
                    ["status"] = status.ToString(),
                    ["spots_tried"] = tried,
                    ["first_status"] = FirstStatus,
                    ["ray"] = PlaceAim.LastRay,
                    ["ghost_off_m"] = Ghost(self) != null ? Math.Round(Geometry.HorizontalDistance(Ghost(self).transform.position, point), 2) : -1,
                });
            PlacePressed(self) = Time.time;
            pressedAt = now;
            presses++;
            Phase = "placing";
            return null;
        }
        if (now - pressedAt < SettleSeconds)
            return null;
        if (presses < 2)
        {
            Phase = "selecting";
            readyAt = -1f;
            return null;
        }
        return Outcome.Failed("not_placed", new JObject { ["status"] = Status(self).ToString() });
    }

    // 조준점을 옮겨 가며 게임이 초록(Valid)으로 보여 주는 첫 자리를 찾는다. 판정은 게임의 미리보기 갱신 그대로다.
    // 처음 겨눈 자리의 판정(그 자리가 왜 안 됐는지). 결과 증거에 싣는다.
    static string FirstStatus;
    static readonly AccessTools.FieldRef<Player, GameObject> Ghost = AccessTools.FieldRefAccess<Player, GameObject>("m_placementGhost");
    const float GhostTolerance = .6f;
    const float HitTolerance = .35f;

    Vector3? Find(Player self) =>
        within > 0f ? Nudge(self, exact ? point : Ground(point), within, out tried)
        : exact ? FindValidSpot(self, point, out tried, slide: false)
        : FindValidSpot(self, Ground(point), out tried);

    bool StillOnTarget(Player self, Vector3 aim)
    {
        PlaceAim.Point = aim;
        UpdateGhost.Invoke(self, new object[] { false });
        return within > 0f ? GhostWithin(self, point, within) : OnTarget(self, aim, exact);
    }

    // 게임의 미리보기가 겨눈 자리에 있는가. 땅에 지을 때는 광선이 그 땅에 맞아야 한다(먼저 덤불·바위에 맞으면
    // 미리보기가 그 위에 뜬다: 작업대가 0.8m 떠 있었다). 지붕처럼 면을 겨눌 때는 조각이 면 안쪽으로 붙으므로 넉넉히 본다.
    static bool OnTarget(Player self, Vector3 aim, bool exact)
    {
        var ghost = Ghost(self);
        if (Status(self) != Player.PlacementStatus.Valid || ghost == null)
            return false;
        if (exact)
            return Geometry.HorizontalDistance(ghost.transform.position, aim) < ExactTolerance;
        return PlaceAim.LastHit.HasValue && Vector3.Distance(PlaceAim.LastHit.Value, aim) < HitTolerance
            && Geometry.HorizontalDistance(ghost.transform.position, aim) < GhostTolerance;
    }

    static bool GhostWithin(Player self, Vector3 target, float within)
    {
        var ghost = Ghost(self);
        return Status(self) == Player.PlacementStatus.Valid && ghost != null
            && Geometry.HorizontalDistance(ghost.transform.position, target) < within;
    }

    const float ExactTolerance = 1.6f;
    const int NudgeSteps = 6;

    // 사람이 미리보기를 보며 조준점을 조금씩 옮기듯, 미리보기가 목표에서 비켜난 만큼 조준점을 반대로 옮긴다.
    // 모닥불 위 요리대: 불 가운데를 겨누면 광선이 앞쪽 돌테에 먼저 맞아 미리보기가 0.4m 앞에 떴다.
    static Vector3? Nudge(Player self, Vector3 target, float within, out int tried)
    {
        tried = 0;
        var aim = target;
        for (var i = 0; i < NudgeSteps; i++)
        {
            tried++;
            PlaceAim.Point = aim;
            UpdateGhost.Invoke(self, new object[] { false });
            if (tried == 1)
                FirstStatus = Status(self).ToString() + " ray=" + PlaceAim.LastRay;
            var ghost = Ghost(self);
            if (ghost == null)
                return null;
            if (GhostWithin(self, target, within))
                return aim;
            var off = ghost.transform.position - target;
            off.y = 0f;
            aim -= off;
        }
        return null;
    }

    static Vector3? FindValidSpot(Player self, Vector3 center, out int tried, bool slide = true)
    {
        tried = 0;
        var reach = self.m_maxPlaceDistance;
        foreach (var radius in slide ? new[] { 0f }.Concat(SlideRadii) : new[] { 0f })
            for (var i = 0; i < (radius == 0f ? 1 : 8); i++)
            {
                var angle = i * 45f * Mathf.Deg2Rad;
                var candidate = radius == 0f && !slide ? center : Ground(center + new Vector3(Mathf.Sin(angle), 0, Mathf.Cos(angle)) * radius);
                if (Vector3.Distance(self.GetEyePoint(), candidate) > reach)
                    continue;
                tried++;
                PlaceAim.Point = candidate;
                UpdateGhost.Invoke(self, new object[] { false });
                if (tried == 1)
                    FirstStatus = Status(self).ToString() + " ray=" + PlaceAim.LastRay;
                // 판정이 Valid여도 미리보기가 겨눈 자리에서 벗어났으면(광선이 사이의 언덕에 맞음) 그 자리가 아니다.
                if (OnTarget(self, candidate, !slide))
                    return candidate;
            }
        return null;
    }

    static double GroundY(Vector3 at) =>
        Physics.Raycast(at + Vector3.up * 20f, Vector3.down, out var hit, 60f, LayerMask.GetMask("terrain"), QueryTriggerInteraction.Ignore) ? Math.Round(hit.point.y, 2) : double.NaN;

    // 두뇌가 준 높이는 어림값이다. 사람이 땅을 가리키듯 그 자리의 땅(또는 이미 지은 것) 표면을 겨눈다.
    static Vector3 Ground(Vector3 point)
    {
        var top = point + Vector3.up * 6f;
        // 표면에서 조금 아래를 겨눈다. 표면 그 점을 겨누면 광선이 땅을 스치고 지나가 뒤의 물체(작업대)에 맞았다.
        return Physics.Raycast(top, Vector3.down, out var hit, 20f, LayerMask.GetMask("terrain"), QueryTriggerInteraction.Ignore)
            ? hit.point + Vector3.down * .05f
            : point;
    }

    IEnumerable<Piece> Nearby()
    {
        var pieces = new List<Piece>();
        Piece.GetAllPiecesInRadius(point, 4f, pieces);
        return pieces.Where(p => p != null && p.m_name == prefab.m_name && p.GetComponent<ZNetView>()?.GetZDO() != null);
    }

    static bool IsMine(Player self, Piece piece) =>
        piece.GetComponent<ZNetView>().GetZDO().GetLong(ZDOVars.s_creator, 0L) == self.GetPlayerID();

    internal static JArray MissingFor(Player self, Piece piece)
    {
        var missing = new JArray();
        foreach (var requirement in piece.m_resources)
        {
            if (requirement.m_resItem == null)
                continue;
            var have = self.GetInventory().CountItems(requirement.m_resItem.m_itemData.m_shared.m_name);
            if (have < requirement.m_amount)
                missing.Add(new JObject { ["name"] = Snapshot.Localize(requirement.m_resItem.m_itemData.m_shared.m_name), ["need"] = requirement.m_amount, ["have"] = have });
        }
        return missing;
    }

    public JObject Progress(Player self) => new JObject { ["phase"] = Phase, ["presses"] = presses };

    public void Stop(Player self)
    {
        PlaceAim.Point = null;
        Motor.Intent.LookWorld = null;
    }
}

// 건축 조준점. 사람은 화면 가운데(카메라 광선)로 지을 자리를 가리킨다. 짓는 동안에는 눈에서 그 자리로 쏜 광선을 대신 쓴다.
[HarmonyPatch]
internal static class PlaceAim
{
    public static Vector3? Point;
    public static string LastRay;
    public static Vector3? LastHit;
    static readonly AccessTools.FieldRef<Player, int> RayMask = AccessTools.FieldRefAccess<Player, int>("m_placeRayMask");
    static readonly AccessTools.FieldRef<Player, int> WaterRayMask = AccessTools.FieldRefAccess<Player, int>("m_placeWaterRayMask");

    [HarmonyPatch(typeof(Player), "PieceRayTest")]
    [HarmonyPrefix]
    static bool Aim(Player __instance, ref bool __result, out Vector3 point, out Vector3 normal, out Piece piece, out Heightmap heightmap, out Collider waterSurface, bool water)
    {
        point = normal = Vector3.zero;
        piece = null;
        heightmap = null;
        waterSurface = null;
        if (!BodyPlugin.Active || __instance != Player.m_localPlayer || !Point.HasValue)
            return true;
        var eye = __instance.m_eye.position;
        var direction = Point.Value - eye;
        // 땅에 박힌 지점을 조금 지나서까지 쏘아야 표면에 닿는다.
        __result = Physics.Raycast(eye, direction.normalized, out var hit, direction.magnitude + 1.5f, water ? WaterRayMask(__instance) : RayMask(__instance))
            && hit.collider != null && hit.collider.attachedRigidbody == null;
        LastHit = __result ? hit.point : (Vector3?)null;
        LastRay = __result
            ? hit.collider.name + "(" + (hit.collider.GetComponentInParent<Piece>()?.m_name ?? hit.collider.transform.root.name) + ")@" + Math.Round(hit.distance, 2) + "/" + Math.Round(direction.magnitude, 2)
            : "none/" + Math.Round(direction.magnitude, 2);
        if (!__result)
        {
            // 진단: 어느 레이어의 무엇이 광선 위에 있었는지(마스크와 상관없이) 남긴다.
            var all = Physics.RaycastAll(eye, direction.normalized, direction.magnitude + 1.5f, ~0, QueryTriggerInteraction.Collide);
            LastRay += " eye=" + eye.ToString("F2") + " aim=" + Point.Value.ToString("F2") + " all=" + string.Join(",", all.Select(h => h.collider.name + "@" + LayerMask.LayerToName(h.collider.gameObject.layer) + ":" + h.distance.ToString("F1") + (h.collider.isTrigger ? "T" : "") + (h.collider.attachedRigidbody != null ? "R" : "")));
        }
        if (__result)
        {
            point = hit.point;
            normal = hit.normal;
            piece = hit.collider.GetComponentInParent<Piece>();
            heightmap = hit.collider.GetComponent<Heightmap>();
            waterSurface = hit.collider.gameObject.layer == LayerMask.NameToLayer("Water") ? hit.collider : null;
        }
        return false;
    }
}
