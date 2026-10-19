using System;
using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using Thorkell.Core;
using UnityEngine;

namespace Thorkell.Body.Perception;

internal sealed class Entity
{
    public string Id;
    public string Kind;
    public string Name;
    public string Key;
    public Component Component;
    public Vector3 Point;
    public float Distance;
    public float Bearing;
    public bool LineOfSight;
    public float? HealthFraction;
    public int? Stars;
    public bool? Alerted;
    public int? Stack;
    public string Size;
    public float? HeightM;
    public bool? TopBar;
    public bool? Open;
    public string Tag;
    public bool? Connected;
}

// 주변 개체를 사람이 볼 수 있는 만큼만 모은다. prefab 이름·도구 tier·AI 내부값은 담지 않는다.
// 이름은 게임이 보여주는 hover 이름(사용자 언어), Key는 개체 구분용 로컬라이즈 토큰이며 모델 프롬프트에 쓰지 않는다.
internal sealed class Scanner
{
    static readonly System.Reflection.MethodInfo TargetFound = HarmonyLib.AccessTools.Method(typeof(TeleportWorld), "TargetFound")
        ?? throw new MissingMethodException("TeleportWorld", "TargetFound");

    public const float Range = 40f;
    // 큰 생물은 멀리서도 보인다(사람은 키 3m짜리 사슴을 40m 밖에서도 본다). 보스 체력바가 뜨는 거리와 같다.
    public const float LargeRange = Parity.BossHudRadius;
    public const int MaxEntities = 48;

    readonly Collider[] buffer = new Collider[4096];
    readonly Dictionary<string, float> hovered = new Dictionary<string, float>();

    // 매 프레임 부른다. 게임은 화면 가운데 광선이 처음 닿은 생물(GetHoverCreature)의 이름표를 60초 동안 띄운다.
    // 잠깐 쳐다본 것도 놓치지 않도록 관측 주기(2Hz)가 아니라 프레임마다 기록한다.
    public void NoteHover(Player self)
    {
        var now = Time.time;
        var creature = self.GetHoverCreature();
        if (creature != null && Ids.Of(creature) is string creatureId)
            hovered[creatureId] = now;
        var hoverObject = self.GetHoverObject();
        if (hoverObject != null && Ids.Of(hoverObject.transform) is string hoverId)
            hovered[hoverId] = now;
    }

    public double SinceHover(string id) => hovered.TryGetValue(id, out var at) ? Time.time - at : double.MaxValue;

    public List<Entity> Scan(Player self)
    {
        var now = Time.time;

        var seen = new HashSet<ZNetView>();
        var seenLandmarks = new HashSet<int>();
        var found = new List<Entity>();
        int count = Physics.OverlapSphereNonAlloc(self.transform.position, Range, buffer, ~0, QueryTriggerInteraction.Collide);
        for (int i = 0; i < count; i++)
        {
            var collider = buffer[i];
            if (collider == null)
                continue;
            var landmark = Landmark(collider);
            if (landmark != null)
            {
                if (!seenLandmarks.Add(landmark.Component.gameObject.GetInstanceID()))
                    continue;
                landmark.Id = Ids.Static(landmark.Component);
                if (Place(self, landmark, Range))
                    found.Add(landmark);
                continue;
            }
            var view = collider.GetComponentInParent<ZNetView>();
            if (view == null || !view.IsValid() || !seen.Add(view))
                continue;
            var entity = Classify(self, view);
            if (entity == null)
                continue;

            entity.Id = Ids.Format(view.GetZDO().m_uid);
            if (!Place(self, entity, Range))
                continue;
            if (entity.Component is Character creature)
                DescribeCreature(entity, creature);
            found.Add(entity);
        }
        // 몸 둘레(40m) 밖의 큰 생물은 따로 찾는다.
        foreach (var creature in Character.GetAllCharacters())
        {
            if (creature == null || creature == self || creature.IsDead() || SizeOf(creature) != "large")
                continue;
            var view = creature.GetComponent<ZNetView>();
            if (view == null || !view.IsValid() || !seen.Add(view))
                continue;
            var entity = Classify(self, view);
            if (entity == null)
                continue;
            entity.Id = Ids.Format(view.GetZDO().m_uid);
            if (!Place(self, entity, LargeRange))
                continue;
            DescribeCreature(entity, creature);
            found.Add(entity);
        }
        // 가까운 것부터 MaxEntities개, 그리고 그 밖의 큰 생물(나무가 많아도 보스를 빠뜨리지 않는다).
        var nearest = found.OrderBy(e => e.Distance).ToList();
        var shown = nearest.Take(MaxEntities).ToList();
        shown.AddRange(nearest.Skip(MaxEntities).Where(e => e.Size == "large"));
        return shown;
    }

    // 알아챈 보스의 체력바는 화면 위쪽에 이름과 함께 뜬다(EnemyHud). 나무 뒤로 가려져도 뜬다.
    public List<JObject> BossBars(Player self)
    {
        var bars = new List<JObject>();
        foreach (var creature in Character.GetAllCharacters())
        {
            if (creature == null || creature.IsDead() || !creature.IsBoss())
                continue;
            var ai = creature.GetBaseAI();
            var distance = Vector3.Distance(self.transform.position, creature.transform.position);
            if (!Parity.ShowsStats(distance, true, ai != null && ai.IsAlerted(), double.MaxValue))
                continue;
            bars.Add(new JObject
            {
                ["id"] = Ids.Of(creature),
                ["name"] = creature.GetHoverName(),
                ["health"] = Math.Round(creature.GetHealthPercentage(), 2),
            });
        }
        return bars;
    }

    void DescribeCreature(Entity entity, Character creature)
    {
        var sinceHover = SinceHover(entity.Id);
        var ai = creature.GetBaseAI();
        var alerted = ai != null && ai.IsAlerted();
        // 생물의 이름·체력바는 게임이 머리 위 HUD를 띄울 때만 보인다. 멀리 있는 생물은 생김새(크기)만 안다.
        if (Parity.ShowsStats(entity.Distance, creature.IsBoss(), alerted, sinceHover))
        {
            entity.HealthFraction = creature.GetHealthPercentage();
            entity.Stars = creature.GetLevel() - 1;
            entity.Alerted = alerted;
            // 보스의 체력바는 머리 위가 아니라 화면 위쪽에 이름과 함께 크게 뜬다(EnemyHud 보스 HUD).
            if (creature.IsBoss())
                entity.TopBar = true;
        }
        else if (!creature.IsPlayer())
            entity.Name = "";
        entity.Size = SizeOf(creature);
        // 사람은 생물의 키를 눈대중으로 안다. 0.5m 단위로만 준다.
        entity.HeightM = Mathf.Round(creature.GetHeight() * 2f) / 2f;
    }

    // 거리·시야를 재고, 보이는 것이면 true.
    static bool Place(Player self, Entity entity, float range)
    {
        entity.Point = Geometry.ApproachPoint(self, entity.Component);
        entity.Distance = Vector3.Distance(self.transform.position, entity.Point);
        entity.LineOfSight = entity.Component is Character creature
            ? Geometry.SeesCreature(self, creature)
            : Geometry.LineOfSight(self, entity.Component.gameObject, entity.Point + Vector3.up * .5f);
        if (!Parity.Perceived(entity.Distance, entity.LineOfSight, range))
            return false;
        entity.Bearing = Geometry.Bearing(self, entity.Point);
        return true;
    }

    // 장소에 딸린 고정 물체. 사람에게는 그 이름(hover)으로 보인다.
    static Entity Landmark(Collider collider)
    {
        if (collider.GetComponentInParent<Vegvisir>() is Vegvisir vegvisir)
            return New("vegvisir", vegvisir, vegvisir.GetHoverName() + " " + vegvisir.m_hoverName, vegvisir.m_name);
        if (collider.GetComponentInParent<OfferingBowl>() is OfferingBowl bowl && bowl.GetComponent<ZNetView>() == null)
            return New("altar", bowl, bowl.m_name, bowl.m_name);
        if (collider.GetComponentInParent<RuneStone>() is RuneStone stone && stone.GetComponent<ZNetView>() == null)
            return New("runestone", stone, stone.m_name, stone.m_name);
        if (collider.GetComponentInParent<ItemStand>() is ItemStand stand && stand.GetComponent<ZNetView>() == null)
            return New("item_stand", stand, stand.m_name, stand.m_name);
        return null;
    }

    static Entity Classify(Player self, ZNetView view)
    {
        var go = view.gameObject;
        var character = go.GetComponent<Character>();
        if (character != null)
        {
            if (character == self || character.IsDead())
                return null;
            var kind = character.IsPlayer() ? "player" : character.IsTamed() ? "tamed" : "creature";
            return New(kind, character, character.GetHoverName(), character.m_name);
        }
        var drop = go.GetComponent<ItemDrop>();
        if (drop != null)
        {
            var e = New("item", drop, drop.m_itemData.m_shared.m_name, drop.m_itemData.m_shared.m_name);
            e.Stack = drop.m_itemData.m_stack;
            return e;
        }
        var pickable = go.GetComponent<Pickable>();
        if (pickable != null)
            return pickable.CanBePicked() ? New("pickable", pickable, pickable.GetHoverName(), pickable.GetHoverName()) : null;
        if (go.GetComponent<TreeBase>() is TreeBase tree)
            return New("tree", tree, Hover(tree), Hover(tree));
        if (go.GetComponent<TreeLog>() is TreeLog log)
            return New("log", log, Hover(log), Hover(log));
        if (go.GetComponent<MineRock5>() is MineRock5 bigRock)
            return New("rock", bigRock, bigRock.m_name, bigRock.m_name);
        if (go.GetComponent<MineRock>() is MineRock rock)
            return New("rock", rock, rock.m_name, rock.m_name);
        if (go.GetComponent<CraftingStation>() is CraftingStation station)
            return New("station", station, station.m_name, station.m_name);
        if (go.GetComponent<CookingStation>() is CookingStation cooking)
            return New("cooking", cooking, cooking.m_name, cooking.m_name);
        if (go.GetComponent<Fireplace>() is Fireplace fire)
            return New("fire", fire, fire.m_name, fire.m_name);
        if (go.GetComponent<Smelter>() is Smelter smelter)
            return New("smelter", smelter, smelter.m_name, smelter.m_name);
        if (go.GetComponent<Container>() is Container chest)
            return New("chest", chest, chest.m_name, chest.m_name);
        if (go.GetComponent<Bed>() is Bed bed)
            return New("bed", bed, Hover(bed), Hover(bed));
        if (go.GetComponent<RuneStone>() is RuneStone stone)
            return New("runestone", stone, stone.m_name, stone.m_name);
        if (go.GetComponent<OfferingBowl>() is OfferingBowl altar)
            return New("altar", altar, altar.m_name, altar.m_name);
        if (go.GetComponent<Door>() is Door door)
        {
            var entity = New("door", door, door.m_name, door.m_name);
            entity.Open = view.GetZDO().GetInt(ZDOVars.s_state) != 0;  // 열린 문인지는 보인다
            return entity;
        }
        if (go.GetComponent<TeleportWorld>() is TeleportWorld portal)
        {
            // 포털: 걸어 들어가면 같은 이름표의 다른 포털로 간다. 이어져 있으면 소용돌이가 보이고, 이름표는 조준하면 뜬다.
            var entity = New("portal", portal, portal.GetHoverName(), null);
            entity.Tag = portal.GetText();
            entity.Connected = (bool)TargetFound.Invoke(portal, null);
            return entity;
        }
        if (go.GetComponent<TombStone>() is TombStone tomb)
            return New("tombstone", tomb, "$piece_tombstone " + tomb.GetOwnerName(), "$piece_tombstone");
        if (go.GetComponent<ItemStand>() is ItemStand itemStand)
            return New("item_stand", itemStand, itemStand.m_name, itemStand.m_name);
        if (go.GetComponent<Destructible>() is Destructible destructible)
            return New("destructible", destructible, Hover(destructible), Hover(destructible));
        // 그 밖에 조준하면 이름이 뜨는 것(포탈, 표지판, 수레, 배, 벌통…)도 사람은 본다. 종류를 몰라도 이름으로 넘긴다
        // (2026-10-18 리허설: 리더 앞의 포탈을 "안 보인다"고 했다).
        foreach (var component in go.GetComponents<Component>())
        {
            if (component is Hoverable hoverable && !string.IsNullOrEmpty(hoverable.GetHoverName()))
                return New("thing", component, hoverable.GetHoverName(), null);
        }
        return null;
    }

    // 사람이 화면에서 가늠하는 덩치. 눈에 보이는 몸통(콜라이더) 높이로 나눈다.
    public static string SizeOf(Character creature)
    {
        var height = creature.GetHeight();
        return height < 1.0f ? "small" : height < 2.2f ? "medium" : "large";
    }

    static string Hover(Component component) => component is Hoverable hoverable ? hoverable.GetHoverName() : "";

    static Entity New(string kind, Component component, string name, string key)
    {
        var localized = Localization.instance != null ? Localization.instance.Localize(name ?? "") : name ?? "";
        return new Entity
        {
            Kind = kind,
            Component = component,
            Name = localized,
            Key = key != null && key.StartsWith("$", StringComparison.Ordinal) ? key : null,
        };
    }
}
