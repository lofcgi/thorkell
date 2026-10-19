namespace Thorkell.Host;

// 사람에게 보이는 짧은 안내. HUD가 아직 없으면(메뉴 등) 로그로만 남는다.
internal static class Hud
{
    public static void Say(string text)
    {
        HostPlugin.Log.LogInfo("THORKELL HUD: " + text);
        if (MessageHud.instance != null)
            MessageHud.instance.ShowMessage(MessageHud.MessageType.TopLeft, text);
    }
}
