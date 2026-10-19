using UnityEngine;

namespace Thorkell.Body.Perception;

// 개체 id는 ZDOID를 "userid:id" 문자열로 쓴다. 64비트 값이 JSON 숫자에서 정밀도를 잃지 않게 하기 위해서다.
internal static class Ids
{
    public static string Of(Component component)
    {
        var view = component == null ? null : component.GetComponentInParent<ZNetView>();
        var zdo = view != null && view.IsValid() ? view.GetZDO() : null;
        return zdo == null ? null : Format(zdo.m_uid);
    }

    public static string Format(ZDOID id) => id.UserID + ":" + id.ID;

    public static bool TryParse(string text, out ZDOID id)
    {
        id = ZDOID.None;
        if (string.IsNullOrEmpty(text))
            return false;
        var parts = text.Split(':');
        if (parts.Length != 2 || !long.TryParse(parts[0], out var user) || !uint.TryParse(parts[1], out var local))
            return false;
        id = new ZDOID(user, local);
        return true;
    }

    // 장소(시작 신전, 제단)에 딸린 고정 물체(베그비시르, 룬스톤, 제물 그릇)는 따로 네트워크 id가 없다.
    // 이번 실행 동안만 쓰는 "s:<인스턴스 id>"로 부른다.
    static readonly System.Collections.Generic.Dictionary<int, GameObject> statics = new System.Collections.Generic.Dictionary<int, GameObject>();

    public static string Static(Component component)
    {
        var go = component.gameObject;
        statics[go.GetInstanceID()] = go;
        return "s:" + go.GetInstanceID();
    }

    public static GameObject Find(string text)
    {
        if (text != null && text.StartsWith("s:", System.StringComparison.Ordinal))
            return int.TryParse(text.Substring(2), out var key) && statics.TryGetValue(key, out var go) && go != null ? go : null;
        return TryParse(text, out var id) && ZNetScene.instance != null ? ZNetScene.instance.FindInstance(id) : null;
    }
}
