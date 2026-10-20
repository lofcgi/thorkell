using System;
using System.Collections.Generic;
using System.Globalization;
using HarmonyLib;
using Newtonsoft.Json.Linq;
using Thorkell.Body.Perception;
using Thorkell.Core;
using UnityEngine;

namespace Thorkell.Body.Events;

// 처음 하는 사람이 겪는 것과 같은 신호를 이벤트로 만든다: 맞음/때림(피해 텍스트), 새 재료·레시피·제작대,
// 까마귀·룬스톤 글, 새 바이옴, 스킬 상승, 게임 메시지, 채팅, 죽음. 모두 로컬 플레이어(봇)에 대해서만.
[HarmonyPatch]
internal static class Hooks
{
    internal static readonly DamageAttribution Attribution = new DamageAttribution(windowSeconds: 0.6, radius: 8f);
    static bool blockedInThisHit;

    static bool IsBot(Character character) => BodyPlugin.Active && character != null && character == Player.m_localPlayer;

    static string L(string token) => Snapshot.Localize(token);

    // --- 맞음 -------------------------------------------------------------------------------
    [HarmonyPatch(typeof(Character), "RPC_Damage")]
    [HarmonyPrefix]
    static void DamagePrefix(Character __instance, ref float __state)
    {
        __state = IsBot(__instance) ? __instance.GetHealth() : -1f;
        blockedInThisHit = false;
    }

    [HarmonyPatch(typeof(Character), "RPC_Damage")]
    [HarmonyPostfix]
    static void DamagePostfix(Character __instance, HitData hit, float __state)
    {
        if (__state < 0 || hit == null)
            return;
        var attacker = hit.GetAttacker();
        var types = new JObject();
        void Add(string name, float value) { if (value > 0) types[name] = Math.Round(value, 1); }
        Add("blunt", hit.m_damage.m_blunt);
        Add("slash", hit.m_damage.m_slash);
        Add("pierce", hit.m_damage.m_pierce);
        Add("fire", hit.m_damage.m_fire);
        Add("frost", hit.m_damage.m_frost);
        Add("lightning", hit.m_damage.m_lightning);
        Add("poison", hit.m_damage.m_poison);
        Add("spirit", hit.m_damage.m_spirit);
        var data = new JObject
        {
            ["amount"] = Math.Round(__state - __instance.GetHealth(), 1),
            ["hp_after"] = Math.Round(__instance.GetHealth(), 1),
            ["types"] = types,
            ["blocked"] = blockedInThisHit,
            ["hit_type"] = hit.m_hitType.ToString(),
        };
        if (attacker != null)
        {
            Reflex.Reflexes.OnDamagedBy(attacker);
            data["attacker_id"] = Ids.Of(attacker);
            data["attacker_name"] = attacker.GetHoverName();
            data["attacker_kind"] = attacker.IsPlayer() ? "player" : "creature";
            // 때린 상대의 덩치는 맞는 순간 보인다. 나타나자마자 한 방에 죽어도 무엇에 당했는지 안다.
            data["attacker_size"] = Scanner.SizeOf(attacker);
        }
        EventSink.Emit("damage_taken", data);
    }

    // 생물이 쓰러지면 게임은 그 자리에 시체(Ragdoll)를 만든다. 모든 클라이언트에 같이 생긴다.
    // 사람은 쓰러지는 것을 본다. 보이는 거리 안이면 그 자리에 있던 생물이 쓰러졌다고 알린다(사라진 것과 구분한다).
    [HarmonyPatch(typeof(Ragdoll), "Awake")]
    [HarmonyPostfix]
    static void Fell(Ragdoll __instance)
    {
        var self = Player.m_localPlayer;
        if (!BodyPlugin.Active || self == null)
            return;
        var at = __instance.transform.position;
        if (Vector3.Distance(self.transform.position, at) > FallSeenDistance)
            return;
        var characters = new List<Character>();
        var around = new List<(bool IsPlayer, float Distance)>();
        foreach (var character in Character.GetAllCharacters())
        {
            if (character == null)
                continue;
            characters.Add(character);
            around.Add((character.IsPlayer(), Vector3.Distance(character.transform.position, at)));
        }
        var playerRagdoll = __instance.name.StartsWith("Player_ragdoll", StringComparison.Ordinal);
        if (playerRagdoll)
        {
            PlayerFell(self, at);
            return;
        }
        var index = Falls.Fallen(playerRagdoll, around, FallMatchDistance);
        if (index < 0)
            return;
        var fallen = characters[index];
        EventSink.Emit("creature_died", new JObject
        {
            ["id"] = Ids.Of(fallen),
            ["size"] = Scanner.SizeOf(fallen),
            ["pos"] = new JArray(Math.Round(at.x, 2), Math.Round(at.y, 2), Math.Round(at.z, 2)),
        });
    }

    // 다른 플레이어를 마지막으로 본 자리. 죽은 플레이어의 캐릭터는 시체가 생길 때 이미 없을 수 있다.
    static readonly Dictionary<string, (Vector3 Pos, float At)> playersSeen = new Dictionary<string, (Vector3, float)>();
    const float PlayerSeenMaxAgeS = 2f;

    internal static void NotePlayers(Player self)
    {
        foreach (var player in Player.GetAllPlayers())
        {
            if (player != null && player != self && !player.IsDead())
                playersSeen[Ids.Of(player)] = (player.transform.position, Time.time);
        }
    }

    static void PlayerFell(Player self, Vector3 at)
    {
        var ids = new List<string>();
        var seen = new List<(float Distance, float AgeS)>();
        foreach (var entry in playersSeen)
        {
            ids.Add(entry.Key);
            seen.Add((Vector3.Distance(entry.Value.Pos, at), Time.time - entry.Value.At));
        }
        var index = Falls.FallenPlayer(seen, FallMatchDistance, PlayerSeenMaxAgeS);
        if (index < 0)
            return;
        playersSeen.Remove(ids[index]);
        EventSink.Emit("creature_died", new JObject
        {
            ["id"] = ids[index],
            ["size"] = "medium",
            ["player"] = true,
            ["pos"] = new JArray(Math.Round(at.x, 2), Math.Round(at.y, 2), Math.Round(at.z, 2)),
        });
    }

    const float FallSeenDistance = 80f;
    const float FallMatchDistance = 3f;

    [HarmonyPatch(typeof(Humanoid), "BlockAttack")]
    [HarmonyPostfix]
    static void Blocked(Humanoid __instance, bool __result)
    {
        if (IsBot(__instance) && __result)
            blockedInThisHit = true;
    }

    // --- 때림 -------------------------------------------------------------------------------
    // 게임이 봇의 근접 판정을 실제로 몇 번 돌렸는가. 휘두르기 애니메이션의 판정 이벤트가 왔는지 확인하는 데 쓴다.
    public static int MeleeChecks;

    // 휘두를 때 겨냥한 대상과, 봇의 타격이 실제로 맞힌 물체·지점. 한 번 휘두르면 범위 안의 여러 물체가 맞는데,
    // 피해 숫자는 맞은 지점(hit.m_point, 막힘은 0.5m 위)에 뜬다. 그래서 숫자 위치가 겨냥한 대상의 타격 지점과 같을 때만 on_target이다.
    // (콜라이더 범위로 판단하면 나무 수관처럼 큰 콜라이더 안의 옆 덤불까지 대상으로 셌다.)
    static string swingTargetId;
    static float swingAt = -100f;
    static readonly List<(string id, Vector3 point, float time)> ownHits = new List<(string, Vector3, float)>();

    public static void SwingAt(Component target)
    {
        swingTargetId = target != null ? Ids.Of(target) : null;
        swingAt = Time.time;
    }

    internal static void RecordOwnHit(Component damaged, Vector3 point)
    {
        var now = Time.time;
        ownHits.RemoveAll(hit => now - hit.time > 5f);
        ownHits.Add((Ids.Of(damaged), point, now));
    }

    // 봇의 공격(화살 포함)이 그 대상의 피해 처리에 들어갔는가. 체력은 대상 소유자(호스트)에서 깎여 늦게 보이므로
    // 화살은 이것으로 맞았는지 본다.
    public static bool HitSince(string id, float since)
    {
        foreach (var (hitId, _, time) in ownHits)
            if (hitId == id && time >= since)
                return true;
        return false;
    }

    static bool OnTarget(Vector3 pos)
    {
        if (swingTargetId == null || Time.time - swingAt > 5f)
            return false;
        foreach (var (id, point, time) in ownHits)
            if (id == swingTargetId && Time.time - time <= 5f
                && ((point - pos).sqrMagnitude < .0025f || (point + Vector3.up * .5f - pos).sqrMagnitude < .0025f))
                return true;
        return false;
    }

    // 근접 공격 판정 시각을 기록해 두고, 그 직후 근처에 뜬 피해 텍스트만 자기 것으로 본다.
    [HarmonyPatch(typeof(Attack), "DoMeleeAttack")]
    [HarmonyPrefix]
    static void MeleeHit(Attack __instance, Humanoid ___m_character)
    {
        if (IsBot(___m_character))
        {
            MeleeChecks++;
            var p = ___m_character.transform.position;
            Attribution.RecordOwnHit(Time.time, new System.Numerics.Vector3(p.x, p.y, p.z));
        }
    }

    [HarmonyPatch(typeof(DamageText), "AddInworldText")]
    [HarmonyPrefix]
    static void DamageText(DamageText.TextType type, Vector3 pos, string text)
    {
        if (!BodyPlugin.Active || Player.m_localPlayer == null)
            return;
        if (!Attribution.IsOwn(Time.time, new System.Numerics.Vector3(pos.x, pos.y, pos.z)))
            return;
        var data = new JObject
        {
            ["type"] = Snake(type.ToString()),
            ["text"] = L(text),
            ["pos"] = new JArray(pos.x, pos.y, pos.z),
            ["weapon"] = Snapshot.WeaponJson(Player.m_localPlayer),
            ["on_target"] = OnTarget(pos),
        };
        if (float.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out var amount))
            data["amount"] = amount;
        EventSink.Emit("damage_dealt", data);
    }

    // --- 알게 됨 ----------------------------------------------------------------------------
    [HarmonyPatch(typeof(Player), nameof(Player.AddKnownItem))]
    [HarmonyPrefix]
    static void KnownItem(Player __instance, ItemDrop.ItemData item)
    {
        if (IsBot(__instance) && item != null && !__instance.IsMaterialKnown(item.m_shared.m_name))
            EventSink.Emit("item_discovered", new JObject { ["name"] = L(item.m_shared.m_name), ["type"] = item.m_shared.m_itemType.ToString() });
    }

    [HarmonyPatch(typeof(Player), "AddKnownRecipe")]
    [HarmonyPrefix]
    static void KnownRecipe(Player __instance, Recipe recipe)
    {
        if (!IsBot(__instance) || recipe == null || recipe.m_item == null)
            return;
        var key = recipe.m_item.m_itemData.m_shared.m_name;
        if (!__instance.IsRecipeKnown(key))
            EventSink.Emit("recipe_unlocked", new JObject
            {
                ["name"] = L(key),
                ["station"] = recipe.m_craftingStation != null ? L(recipe.m_craftingStation.m_name) : "",
            });
    }

    [HarmonyPatch(typeof(Player), "AddKnownPiece")]
    [HarmonyPrefix]
    static void KnownPiece(Player __instance, Piece piece)
    {
        if (IsBot(__instance) && piece != null && !__instance.IsRecipeKnown(piece.m_name))
            EventSink.Emit("piece_unlocked", new JObject { ["name"] = L(piece.m_name), ["category"] = piece.m_category.ToString() });
    }

    [HarmonyPatch(typeof(Player), nameof(Player.AddKnownStation))]
    [HarmonyPrefix]
    static void KnownStation(Player __instance, CraftingStation station, Dictionary<string, int> ___m_knownStations)
    {
        if (!IsBot(__instance) || station == null)
            return;
        var level = station.GetLevel();
        if (!___m_knownStations.TryGetValue(station.m_name, out var known) || known < level)
            EventSink.Emit("station_discovered", new JObject { ["name"] = L(station.m_name), ["level"] = level });
    }

    [HarmonyPatch(typeof(Player), nameof(Player.AddKnownText))]
    [HarmonyPrefix]
    static void KnownText(Player __instance, string label, string text, Dictionary<string, string> ___m_knownTexts)
    {
        if (IsBot(__instance) && !___m_knownTexts.ContainsKey(label))
            EventSink.Emit("text_read", new JObject { ["label"] = L(label), ["text"] = L(text) });
    }

    // 룬스톤 글은 이름표(label)가 없으면 백과사전에 남지 않는다(Eikthyr 제단 석판). 사람은 글 창에서 읽으므로 창에 뜬 글을 알린다.
    [HarmonyPatch(typeof(TextViewer), nameof(TextViewer.ShowText))]
    [HarmonyPostfix]
    static void TextShown(string topic, string textId)
    {
        if (BodyPlugin.Active && Player.m_localPlayer != null && !string.IsNullOrEmpty(textId))
            EventSink.Emit("text_read", new JObject { ["label"] = L(topic ?? ""), ["text"] = L(textId) });
    }

    // 같은 까마귀 글이 여러 번 다시 등록된다(실게임에서 빈 제목의 Munin 글이 수십 번). 처음 본 글만 알린다.
    static readonly HashSet<string> ravenKeys = new HashSet<string>();

    [HarmonyPatch(typeof(Raven), nameof(Raven.AddTempText))]
    [HarmonyPostfix]
    static void RavenAppeared(string key, string topic, bool munin)
    {
        if (!BodyPlugin.Active || Player.m_localPlayer == null || string.IsNullOrEmpty(topic) || !ravenKeys.Add(key ?? topic))
            return;
        EventSink.Emit("raven_appeared", new JObject { ["topic"] = L(topic), ["munin"] = munin });
    }

    [HarmonyPatch(typeof(Player), "AddKnownBiome")]
    [HarmonyPrefix]
    static void KnownBiome(Player __instance, BiomeSector biome)
    {
        if (IsBot(__instance) && !__instance.IsBiomeKnown(biome))
            EventSink.Emit("biome_entered", new JObject { ["name"] = L(biome.GetName()) });
    }

    [HarmonyPatch(typeof(Player), nameof(Player.OnSkillLevelup))]
    [HarmonyPostfix]
    static void SkillUp(Player __instance, Skills.SkillType skill, float level)
    {
        if (IsBot(__instance))
            EventSink.Emit("skill_up", new JObject { ["skill"] = L("$skill_" + skill.ToString().ToLowerInvariant()), ["level"] = Math.Round(level, 1) });
    }

    [HarmonyPatch(typeof(Player), nameof(Player.OnDeath))]
    [HarmonyPrefix]
    static void Death(Player __instance)
    {
        if (IsBot(__instance))
            EventSink.Emit("death", new JObject { ["pos"] = new JArray(__instance.transform.position.x, __instance.transform.position.y, __instance.transform.position.z) });
    }

    // HUD가 숨겨져 있으면 원본이 바로 반환하므로 prefix에서 잡는다. 텍스트는 Localize 전 토큰일 수 있다.
    [HarmonyPatch(typeof(MessageHud), nameof(MessageHud.ShowMessage))]
    [HarmonyPrefix]
    static void Message(MessageHud.MessageType type, string text, int amount)
    {
        if (BodyPlugin.Active && Player.m_localPlayer != null && !string.IsNullOrEmpty(text))
            EventSink.Emit("game_message", new JObject { ["where"] = type == MessageHud.MessageType.Center ? "center" : "top_left", ["text"] = L(text), ["amount"] = amount });
    }

    [HarmonyPatch(typeof(Chat), nameof(Chat.OnNewChatMessage))]
    [HarmonyPostfix]
    static void ChatMessage(long senderID, Vector3 pos, Talker.Type type, UserInfo sender, string text)
    {
        if (!BodyPlugin.Active || ZNet.instance == null || Player.m_localPlayer == null)
            return;
        if (senderID == ZNet.GetUID())
            return;
        EventSink.Emit("chat", new JObject
        {
            ["from"] = sender.Name,
            ["talker"] = type.ToString().ToLowerInvariant(),
            ["text"] = text,
            ["distance"] = Math.Round(Vector3.Distance(Player.m_localPlayer.transform.position, pos), 1),
        });
    }

    static string Snake(string pascal)
    {
        var builder = new System.Text.StringBuilder();
        for (int i = 0; i < pascal.Length; i++)
        {
            if (char.IsUpper(pascal[i]) && i > 0)
                builder.Append('_');
            builder.Append(char.ToLowerInvariant(pascal[i]));
        }
        return builder.ToString();
    }
}

// 봇이 직접 입힌 피해를 맞은 물체의 Damage 입구에서 기록한다. 소유자가 다른 피어여도 공격한 쪽에서 먼저 불린다.
[HarmonyPatch]
internal static class OwnHits
{
    static IEnumerable<System.Reflection.MethodBase> TargetMethods()
    {
        var types = new[] { typeof(Character), typeof(TreeBase), typeof(TreeLog), typeof(Destructible), typeof(MineRock), typeof(MineRock5), typeof(WearNTear) };
        foreach (var type in types)
            yield return AccessTools.Method(type, "Damage", new[] { typeof(HitData) })
                ?? throw new MissingMethodException(type.Name, "Damage(HitData)");
    }

    static void Prefix(Component __instance, HitData hit)
    {
        if (!BodyPlugin.Active || hit == null || Player.m_localPlayer == null || hit.GetAttacker() != Player.m_localPlayer)
            return;
        Hooks.RecordOwnHit(__instance, hit.m_point);
    }
}
