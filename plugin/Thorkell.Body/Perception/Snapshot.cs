using System.Collections.Generic;
using System.Linq;
using Newtonsoft.Json.Linq;
using Thorkell.Compat;
using UnityEngine;

namespace Thorkell.Body.Perception;

// 두뇌로 보내는 관측. state(10Hz)는 작고 자주, scene(2Hz)은 전체 그림.
internal static class Snapshot
{
    public static JObject State(Player self, JObject action, string reflex)
    {
        var p = self.transform.position;
        var v = self.GetVelocity();
        var data = new JObject
        {
            ["pos"] = Vec(p),
            ["yaw"] = Round(self.transform.eulerAngles.y),
            ["vel"] = Vec(v),
            ["hp"] = Round(self.GetHealth()),
            ["hp_max"] = Round(self.GetMaxHealth()),
            ["stamina"] = Round(self.GetStamina()),
            ["stamina_max"] = Round(self.GetMaxStamina()),
            ["eitr"] = Round(self.GetEitr()),
            ["eitr_max"] = Round(self.GetMaxEitr()),
            ["swimming"] = self.IsSwimming(),
            ["in_water"] = self.InWater(),
            ["encumbered"] = self.IsEncumbered(),
            ["blocking"] = self.IsBlocking(),
            ["running"] = self.IsRunning(),
            ["walking"] = self.GetWalk(),
            ["crouching"] = self.IsCrouching(),
            ["in_attack"] = self.InAttack(),
            ["on_ground"] = self.IsOnGround(),
            ["dead"] = self.IsDead(),
            ["in_bed"] = self.InBed(),
        };
        if (action != null)
            data["action"] = action;
        if (reflex != null)
            data["reflex"] = reflex;
        if (Attention.Target != null)
            data["glancing_at"] = Attention.Target;
        return data;
    }

    public static JObject Scene(Player self, List<Entity> nearby, List<JObject> bossBars, Player leader, ZNet.PlayerInfo? leaderOnMap)
    {
        var inventory = self.GetInventory();
        var data = new JObject
        {
            ["nearby"] = new JArray(nearby.Select(EntityJson)),
            ["inventory"] = new JArray(inventory.GetAllItems().Select(i => ItemJson(self, i))),
            ["weight"] = Round(inventory.GetTotalWeight()),
            ["weight_max"] = Round(self.GetMaxCarryWeight()),
            ["foods"] = new JArray(self.GetFoods().Select(f => new JObject
            {
                ["name"] = Localize(f.m_item.m_shared.m_name),
                ["remaining_s"] = Mathf.RoundToInt(f.m_time),
                ["health"] = Round(f.m_health),
                ["stamina"] = Round(f.m_stamina),
            })),
            ["biome"] = Localize("$biome_" + self.GetCurrentBiome().ToString().ToLowerInvariant()),
            ["env"] = Environment(),
            ["effects"] = Effects(self),
        };
        if (bossBars.Count > 0)
            data["boss_bars"] = new JArray(bossBars);
        var raven = Raven(self);
        if (raven != null)
            data["raven"] = raven;
        var pins = Pins();
        if (pins.Count > 0)
            data["pins"] = pins;
        var hover = self.GetHoverObject();
        if (hover != null)
        {
            var id = Ids.Of(hover.transform);
            var named = hover.GetComponentInParent<Hoverable>();
            data["hover"] = new JObject { ["id"] = id, ["name"] = named != null ? Localize(named.GetHoverName()) : "" };
        }
        if (leader != null)
        {
            data["leader"] = new JObject
            {
                ["id"] = Ids.Of(leader),
                ["name"] = leader.GetPlayerName(),
                ["distance"] = Round(Vector3.Distance(self.transform.position, leader.transform.position)),
                ["bearing"] = Round(Geometry.Bearing(self, leader.transform.position)),
                ["pos"] = Vec(leader.transform.position),
                // 친구 캐릭터가 어느 쪽을 보고 서 있는지는 보인다(북 0°, 동 90°). "이거 보여?"는 그쪽을 묻는 것이다.
                ["facing"] = Round(Mathf.Atan2(leader.transform.forward.x, leader.transform.forward.z) * Mathf.Rad2Deg),
                // 누워 있는 모습은 보인다. 리더가 누우면 밤을 넘기려는 것이다(모두 누워야 넘어간다).
                ["in_bed"] = leader.InBed(),
            };
        }
        else if (leaderOnMap.HasValue)
        {
            // 멀어서 보이지 않지만 지도에 표시된 리더. 지도 표시는 몇 초 늦을 수 있다.
            var at = leaderOnMap.Value.m_position;
            data["leader_on_map"] = new JObject
            {
                ["name"] = leaderOnMap.Value.m_name,
                ["distance"] = Round(Vector3.Distance(self.transform.position, at)),
                ["pos"] = Vec(at),
            };
        }
        return data;
    }

    // 화면 오른쪽 위 상태 아이콘(휴식, 젖음, 추위, 쉼터 등).
    static JArray Effects(Player self)
    {
        var effects = new List<StatusEffect>();
        self.GetSEMan().GetHUDStatusEffects(effects);
        return new JArray(effects.Select(e => Localize(e.m_name)).Where(n => n.Length > 0));
    }

    static readonly System.Reflection.FieldInfo MapPins = HarmonyLib.AccessTools.Field(typeof(Minimap), "m_pins");

    // 지도에 찍힌 표시(베그비시르가 알려 준 보스 자리, 죽은 자리, 직접 찍은 핀). 사람도 지도를 열면 본다.
    static JArray Pins()
    {
        var pins = new JArray();
        if (Minimap.instance == null || !(MapPins.GetValue(Minimap.instance) is List<Minimap.PinData> list))
            return pins;
        foreach (var pin in list)
        {
            if (pin.m_type == Minimap.PinType.Player || pin.m_type == Minimap.PinType.Ping || pin.m_type == Minimap.PinType.Shout)
                continue;
            pins.Add(new JObject { ["name"] = Localize(pin.m_name), ["type"] = pin.m_type.ToString(), ["pos"] = Vec(pin.m_pos) });
        }
        return pins;
    }

    static readonly System.Reflection.FieldInfo RavenInstance = HarmonyLib.AccessTools.Field(typeof(global::Raven), "m_instance");
    static readonly System.Reflection.MethodInfo RavenSpawned = HarmonyLib.AccessTools.Method(typeof(global::Raven), "IsSpawned");

    // 안내하러 내려앉은 까마귀. 사람은 느낌표가 뜬 까마귀를 보고 다가가서(3m) 이야기를 듣는다.
    static JObject Raven(Player self)
    {
        var raven = RavenInstance.GetValue(null) as global::Raven;
        if (raven == null || !(bool)RavenSpawned.Invoke(raven, null))
            return null;
        var position = raven.transform.position;
        var distance = Vector3.Distance(self.transform.position, position);
        if (distance > Scanner.Range || !Geometry.LineOfSight(self, raven.gameObject, position + Vector3.up * .3f))
            return null;
        return new JObject { ["name"] = Localize(raven.m_name), ["pos"] = Vec(position), ["distance"] = Round(distance) };
    }

    static JObject Environment()
    {
        var env = new JObject
        {
            ["night"] = EnvMan.IsNight(),
            ["wet"] = EnvMan.IsWet(),
            ["cold"] = EnvMan.IsCold(),
            ["freezing"] = EnvMan.IsFreezing(),
        };
        if (EnvMan.instance != null)
        {
            env["day"] = EnvMan.instance.GetDay();
            env["day_fraction"] = Round(EnvMan.instance.GetDayFraction());
            var current = EnvMan.instance.GetCurrentEnvironment();
            if (current != null)
                env["weather"] = current.m_name;
        }
        return env;
    }

    const float BedLabelDistance = 8f;

    static JObject EntityJson(Entity e)
    {
        var json = new JObject
        {
            ["id"] = e.Id,
            ["kind"] = e.Kind,
            ["name"] = e.Name,
            ["distance"] = Round(e.Distance),
            ["bearing"] = Round(e.Bearing),
            ["pos"] = Vec(e.Point),
            ["visible"] = e.LineOfSight,
        };
        if (e.Stack.HasValue)
            json["stack"] = e.Stack.Value;
        if (e.HealthFraction.HasValue)
            json["health"] = Round(e.HealthFraction.Value);
        if (e.Stars.HasValue)
            json["stars"] = e.Stars.Value;
        if (e.Alerted.HasValue)
            json["alerted"] = e.Alerted.Value;
        // 생물의 종류 구분용 키(로컬라이즈 토큰). 두뇌가 "가까이서 이름을 본 그 생물"을 멀리서도 알아보는 데만 쓰고 모델 프롬프트에는 넣지 않는다.
        if (e.Kind == "creature" && e.Key != null)
            json["key"] = e.Key;
        if (e.Size != null)
            json["size"] = e.Size;
        if (e.HeightM.HasValue)
            json["height_m"] = e.HeightM.Value;
        if (e.TopBar.HasValue)
            json["top_bar"] = e.TopBar.Value;
        if (e.Open.HasValue)
            json["open"] = e.Open.Value;
        if (e.Tag != null)
            json["tag"] = e.Tag;
        if (e.Connected.HasValue)
            json["connected"] = e.Connected.Value;
        // 지은 것이 서 있는 자리(가운데)와 방향. pos는 다가갈 지점(가장 가까운 겉면)이라 폭 3m 작업대에서는 가운데와
        // 1.6m 차이가 났다. 둘레에 벽을 세우려면 가운데를 알아야 한다(사람은 눈으로 안다).
        if (e.Kind == "station" || e.Kind == "bed" || e.Kind == "fire" || e.Kind == "cooking" || e.Kind == "portal")
        {
            json["center"] = Vec(e.Component.transform.position);
            json["yaw"] = Round(e.Component.transform.eulerAngles.y);
        }
        // 침대에 가까이 가서 보면 주인 이름이 뜬다("<이름>'s 침대", 주인이 없으면 "주인 없는 침대").
        // 내 침대면 [E] 줄이 붙는다. 사람이 보는 그 글에서 읽는다.
        if (e.Kind == "bed" && e.Distance <= BedLabelDistance && e.Component is Bed bed)
        {
            var lines = bed.GetHoverText().Split('\n');
            var owned = lines[0].IndexOf("'s ", System.StringComparison.Ordinal);
            json["owner"] = owned > 0 ? lines[0].Substring(0, owned) : "";
            json["mine"] = owned > 0 && lines.Length > 1;
        }
        return json;
    }

    public static JObject ItemJson(Player self, ItemDrop.ItemData item)
    {
        var shared = item.m_shared;
        var json = new JObject
        {
            ["name"] = Localize(shared.m_name),
            ["stack"] = item.m_stack,
            ["quality"] = item.m_quality,
            ["type"] = shared.m_itemType.ToString(),
            ["weight"] = Round(item.GetWeight(-1)),
            ["equipped"] = self.IsItemEquiped(item),
        };
        if (shared.m_useDurability)
            json["durability"] = Round(item.m_durability / Mathf.Max(1f, item.GetMaxDurability()));
        // 사람이 툴팁에서 읽는 피해 수치. 처음 하는 사람도 "둔기 12" 같은 걸 보고 무기를 고른다.
        var damages = DamageJson(item);
        if (damages.Count > 0)
            json["damage"] = damages;
        // 먹을 수 있는 것(소모품)만 툴팁에 음식 수치가 나온다. 날고기는 수치는 있어도 재료라 먹을 수 없다.
        if (shared.m_itemType == ItemDrop.ItemData.ItemType.Consumable && (shared.m_food > 0 || shared.m_foodStamina > 0))
            json["food"] = new JObject
            {
                ["health"] = Round(shared.m_food),
                ["stamina"] = Round(shared.m_foodStamina),
                ["eitr"] = Round(shared.m_foodEitr),
                ["duration_s"] = Mathf.RoundToInt(shared.m_foodBurnTime),
            };
        return json;
    }

    public static JObject DamageJson(ItemDrop.ItemData item)
    {
        var damage = item.GetDamage();
        var damages = new JObject();
        void Add(string name, float value) { if (value > 0) damages[name] = Round(value); }
        Add("blunt", damage.m_blunt);
        Add("slash", damage.m_slash);
        Add("pierce", damage.m_pierce);
        Add("chop", damage.m_chop);
        Add("pickaxe", damage.m_pickaxe);
        Add("fire", damage.m_fire);
        Add("frost", damage.m_frost);
        Add("lightning", damage.m_lightning);
        Add("poison", damage.m_poison);
        Add("spirit", damage.m_spirit);
        return damages;
    }

    // 지금 손에 든 것(없으면 맨손). 타격 순간의 무기를 이벤트에 실어 엉뚱한 무기에 귀속되지 않게 한다.
    public static JObject WeaponJson(Player self)
    {
        var weapon = self.GetCurrentWeapon();
        return weapon == null
            ? new JObject { ["name"] = GameLanguage.English ? "Fists" : "맨손" }
            : new JObject { ["name"] = Localize(weapon.m_shared.m_name), ["damage"] = DamageJson(weapon) };
    }

    public static string Localize(string token) =>
        Localization.instance != null ? Localization.instance.Localize(token ?? "") : token ?? "";

    static JArray Vec(Vector3 v) => new JArray(Round(v.x), Round(v.y), Round(v.z));

    static double Round(float value) => System.Math.Round(value, 2);
}
