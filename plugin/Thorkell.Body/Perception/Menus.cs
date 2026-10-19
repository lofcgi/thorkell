using System.Collections.Generic;
using HarmonyLib;
using Newtonsoft.Json.Linq;

namespace Thorkell.Body.Perception;

// 제작·건축 메뉴에서 사람이 보는 것. 게임이 알려 준(열어 준) 레시피와 건축물만, 메뉴에 나오는 재료·필요한 제작대와 함께 준다.
// 사람은 한 번 본 메뉴를 기억하므로 지금 제작대 앞이 아니어도 알려진 것은 모두 준다.
internal static class Menus
{
    static HashSet<string> Known(Player self) => Traverse.Create(self).Field<HashSet<string>>("m_knownRecipes").Value;

    public static JArray Recipes(Player self)
    {
        var known = Known(self);
        var list = new JArray();
        foreach (var recipe in ObjectDB.instance.m_recipes)
        {
            if (!recipe.m_enabled || recipe.m_item == null || !known.Contains(recipe.m_item.m_itemData.m_shared.m_name))
                continue;
            list.Add(new JObject
            {
                ["name"] = Snapshot.Localize(recipe.m_item.m_itemData.m_shared.m_name),
                ["amount"] = recipe.m_amount,
                ["station"] = recipe.m_craftingStation != null ? Snapshot.Localize(recipe.m_craftingStation.m_name) : null,
                ["station_level"] = recipe.m_minStationLevel,
                ["resources"] = Resources(self, recipe.m_resources, quality: 1),
                ["have_materials"] = Enough(self, recipe.m_resources, quality: 1),
                ["type"] = recipe.m_item.m_itemData.m_shared.m_itemType.ToString(),
            });
        }
        return list;
    }

    // 건축 도구(망치 등)를 가지고 있을 때 그 도구의 건축 메뉴에서 알려진 것.
    public static JArray Pieces(Player self)
    {
        var known = Known(self);
        var list = new JArray();
        var seen = new HashSet<string>();
        foreach (var tool in self.GetInventory().GetAllItems())
        {
            var table = tool.m_shared.m_buildPieces;
            if (table == null)
                continue;
            foreach (var prefab in table.m_pieces)
            {
                var piece = prefab != null ? prefab.GetComponent<Piece>() : null;
                if (piece == null || !piece.m_enabled || !known.Contains(piece.m_name) || !seen.Add(piece.m_name))
                    continue;
                list.Add(new JObject
                {
                    ["name"] = Snapshot.Localize(piece.m_name),
                    ["tool"] = Snapshot.Localize(tool.m_shared.m_name),
                    ["category"] = piece.m_category.ToString(),
                    ["station"] = piece.m_craftingStation != null ? Snapshot.Localize(piece.m_craftingStation.m_name) : null,
                    ["resources"] = Resources(self, piece.m_resources, quality: 0),
                    ["have_materials"] = Enough(self, piece.m_resources, quality: 0),
                });
            }
        }
        return list;
    }

    // 재료만 본다. 게임의 HaveRequirements는 지금 그 제작대 앞에 있는지도 함께 따져서, 떨어져 있으면 재료가 넉넉해도 false다.
    static bool Enough(Player self, Piece.Requirement[] requirements, int quality)
    {
        foreach (var requirement in requirements)
        {
            if (requirement.m_resItem == null || requirement.m_upgraderResource)
                continue;
            var amount = quality == 0 ? requirement.m_amount : requirement.GetAmount(quality);
            if (amount > 0 && self.GetInventory().CountItems(requirement.m_resItem.m_itemData.m_shared.m_name) < amount)
                return false;
        }
        return true;
    }

    static JArray Resources(Player self, Piece.Requirement[] requirements, int quality)
    {
        var list = new JArray();
        foreach (var requirement in requirements)
        {
            // 강화대 전용 재료와 이 품질에서 0개인 재료는 제작 메뉴에 나오지 않는다(Player.HaveRequirements와 같은 기준).
            if (requirement.m_resItem == null || requirement.m_upgraderResource)
                continue;
            var amount = quality == 0 ? requirement.m_amount : requirement.GetAmount(quality);
            if (amount <= 0)
                continue;
            var token = requirement.m_resItem.m_itemData.m_shared.m_name;
            list.Add(new JObject { ["name"] = Snapshot.Localize(token), ["amount"] = amount, ["have"] = self.GetInventory().CountItems(token) });
        }
        return list;
    }
}
