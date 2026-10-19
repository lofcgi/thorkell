using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Steamworks;
using Thorkell.Compat;

namespace Thorkell.Host;

// 같은 Steam 계정의 두 프로세스는 P2P로 만날 수 없으므로 127.0.0.1 IP 리스너를 따로 연다.
//  - crossplay 끔(Steam 백엔드): OpenServer가 만든 정적 ZSteamSocket 호스트로 모든 Steam 연결이 라우팅되므로
//    IP 리스너만 추가하면 accept·티켓 검증까지 네이티브가 처리한다.
//  - crossplay 켬(PlayFab 백엔드): ZNet은 PlayFab 소켓만 accept하므로 우리 ZSteamSocket을 직접 만들고,
//    CheckForIncommingServerConnections 뒤에서 그 소켓을 accept해 OnNewConnection에 넘긴다.
[HarmonyPatch]
internal static class LoopbackListener
{
    static string state = "closed";

    public static string State
    {
        get => state;
        internal set
        {
            state = value;
            HostStatus.Write();
        }
    }

    static HSteamListenSocket handle = HSteamListenSocket.Invalid;
    static ZSteamSocket ours;
    static readonly HashSet<ISocket> accepted = new HashSet<ISocket>();

    static readonly FieldInfo ListenSocketField = AccessTools.Field(typeof(ZSteamSocket), "m_listenSocket");
    static readonly FieldInfo HostSocketField = AccessTools.Field(typeof(ZSteamSocket), "m_hostSocket");
    static readonly FieldInfo ConnectionField = AccessTools.Field(typeof(ZSteamSocket), "m_con");
    static readonly MethodInfo OnNewConnection = AccessTools.Method(typeof(ZNet), "OnNewConnection");

    // 우리 127.0.0.1 리스너로 들어온 연결(토르켈)인가.
    //  - crossplay 켬: 우리가 직접 accept한 소켓이다.
    //  - crossplay 끔: 네이티브가 accept하지만 연결 정보의 리스너가 우리 IP 리스너다.
    //    소켓의 호스트 이름(Steam ID)으로는 못 가린다: 토르켈은 사람과 같은 Steam 계정이다.
    public static bool IsLoopbackPeer(ISocket socket)
    {
        if (accepted.Contains(socket))
            return true;
        if (handle == HSteamListenSocket.Invalid || !(socket is ZSteamSocket steam))
            return false;
        var connection = (HSteamNetConnection)ConnectionField.GetValue(steam);
        return SteamNetworkingSockets.GetConnectionInfo(connection, out var info) && info.m_hListenSocket == handle;
    }

    public static bool IsLoopbackPeer(long uid)
    {
        var peer = ZNet.instance != null ? ZNet.instance.GetPeer(uid) : null;
        return peer != null && IsLoopbackPeer(peer.m_socket);
    }

    public static ZNetPeer BotPeer() =>
        ZNet.instance == null ? null : ZNet.instance.GetPeers().FirstOrDefault(p => p.IsReady() && IsLoopbackPeer(p.m_socket));

    [HarmonyPatch(typeof(ZNet), nameof(ZNet.OpenServer))]
    [HarmonyPostfix]
    static void Open(ZNet __instance)
    {
        var host = HostPlugin.Instance;
        var world = __instance.GetWorldName();
        HostStatus.SetWorld(world);
        if (!host.WorldAllowed(world))
        {
            State = "world_not_allowed";
            HostPlugin.Log.LogWarning("THORKELL: world '" + world + "' is not in Listener.Worlds; loopback listener stays closed");
            return;
        }

        var address = default(SteamNetworkingIPAddr);
        if (!address.ParseString("127.0.0.1:" + host.ListenerPort.Value))
        {
            State = "bad_address";
            HostPlugin.Log.LogError("THORKELL: cannot parse loopback address for port " + host.ListenerPort.Value);
            return;
        }

        if (ZNet.m_onlineBackend == OnlineBackendType.PlayFab)
        {
            if (!CrossplayPeerShim.Ready)
            {
                State = "crossplay_shim_unavailable";
                Hud.Say(GameLanguage.English
                    ? "Thorkell: the crossplay patch is unavailable, so the listener stays closed. Host without crossplay."
                    : "Thorkell: crossplay 호환 패치를 쓸 수 없어 리스너를 열지 않았습니다. crossplay를 끄고 호스팅하세요.");
                return;
            }
            if (HostSocketField.GetValue(null) != null)
            {
                State = "steam_host_busy";
                HostPlugin.Log.LogError("THORKELL: a Steam host socket already exists in PlayFab mode; refusing to replace it");
                return;
            }
        }
        else if (ZNet.m_onlineBackend != OnlineBackendType.Steamworks)
        {
            State = "unsupported_backend";
            HostPlugin.Log.LogError("THORKELL: backend " + ZNet.m_onlineBackend + " is not supported");
            return;
        }

        handle = SteamNetworkingSockets.CreateListenSocketIP(ref address, 0, null);
        if (handle == HSteamListenSocket.Invalid)
        {
            State = "listen_failed";
            HostPlugin.Log.LogError("THORKELL: CreateListenSocketIP failed on 127.0.0.1:" + host.ListenerPort.Value);
            return;
        }

        if (ZNet.m_onlineBackend == OnlineBackendType.PlayFab)
        {
            // StartHost()는 P2P 리스너까지 열기 때문에 쓰지 않고, IP 리스너만 가진 호스트 소켓을 만든다.
            ours = new ZSteamSocket();
            ListenSocketField.SetValue(ours, handle);
            HostSocketField.SetValue(null, ours);
            State = "open_playfab";
        }
        else
        {
            State = "open_steam";
        }
        // 봇 클라이언트는 접속한 뒤 월드를 준비하는 동안(평소 20초, 사람 게임이 무거우면 44초) 핑에 답하지 못한다.
        // 기본 제한 30초면 호스트가 끊는다(2026-10-17 실게임). 게임도 크로스플레이 접속에는 같은 이유로 90초를 쓴다.
        ZRpc.SetLongTimeout(true);
        HostPlugin.Log.LogInfo("THORKELL: loopback listener " + State + " on 127.0.0.1:" + host.ListenerPort.Value + " for world " + world);
        Hud.Say((GameLanguage.English ? "Waiting for Thorkell" : "Thorkell 접속 대기 중") + " (127.0.0.1:" + host.ListenerPort.Value + ")");
    }

    [HarmonyPatch(typeof(ZNet), "CheckForIncommingServerConnections")]
    [HarmonyPostfix]
    static void Accept(ZNet __instance)
    {
        if (ours == null)
            return;
        var socket = ours.Accept();
        if (socket == null)
            return;
        if (!socket.IsConnected())
        {
            socket.Dispose();
            return;
        }
        accepted.Add(socket);
        OnNewConnection.Invoke(__instance, new object[] { new ZNetPeer(socket, false) });
        HostPlugin.Log.LogInfo("THORKELL: accepted loopback peer " + socket.GetHostName());
    }

    [HarmonyPatch(typeof(ZNet), "OnDestroy")]
    [HarmonyPostfix]
    static void Shutdown() => Close();

    public static void Close()
    {
        if (ours != null)
        {
            // Dispose가 정적 m_hostSocket과 우리 IP 리스너를 함께 정리한다.
            ours.Dispose();
            ours = null;
            handle = HSteamListenSocket.Invalid;
        }
        else if (handle != HSteamListenSocket.Invalid)
        {
            SteamNetworkingSockets.CloseListenSocket(handle);
            handle = HSteamListenSocket.Invalid;
        }
        accepted.Clear();
        if (State.StartsWith("open"))
            State = "closed";
    }
}
