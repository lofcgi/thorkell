using System;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using BepInEx.Logging;
using HarmonyLib;

namespace Thorkell.Host;

// crossplay(PlayFab) 호스트에서 ZNet.RPC_PeerInfo는 백엔드가 PlayFab이면
// (peer.m_socket as ZPlayFabSocket).m_remotePlayerId를 null 검사 없이 읽는다. 루프백으로 들어온 Steam 봇이면 NRE로 핸드셰이크가 멈춘다.
// RPC_PeerInfo 안의 m_onlineBackend 읽기 두 곳만, 루프백 피어일 때 Steamworks로 보이게 바꾼다.
// 그러면 봇에는 Steam 세션 티켓 검증이 그대로 적용되고, 다른 메서드(SendPlayerList 등)는 영향을 받지 않는다.
internal static class CrossplayPeerShim
{
    public const int ExpectedReads = 2;
    public static bool Ready { get; private set; }

    static readonly FieldInfo Backend = AccessTools.Field(typeof(ZNet), nameof(ZNet.m_onlineBackend));
    static readonly MethodInfo BackendForMethod = AccessTools.Method(typeof(CrossplayPeerShim), nameof(BackendFor));

    public static void Install(Harmony harmony, ManualLogSource log)
    {
        try
        {
            harmony.Patch(AccessTools.Method(typeof(ZNet), "RPC_PeerInfo"),
                transpiler: new HarmonyMethod(typeof(CrossplayPeerShim), nameof(Transpile)));
            Ready = true;
        }
        catch (Exception e)
        {
            Ready = false;
            log.LogError("THORKELL: crossplay shim not applied (listener will stay closed in crossplay mode): " + e.Message);
        }
    }

    public static OnlineBackendType BackendFor(ZRpc rpc)
    {
        var socket = rpc?.GetSocket();
        if (socket != null && LoopbackListener.IsLoopbackPeer(socket))
            return OnlineBackendType.Steamworks;
        return ZNet.m_onlineBackend;
    }

    static IEnumerable<CodeInstruction> Transpile(IEnumerable<CodeInstruction> instructions)
    {
        var output = new List<CodeInstruction>();
        int replaced = 0;
        foreach (var instruction in instructions)
        {
            if (instruction.opcode == OpCodes.Ldsfld && Equals(instruction.operand, Backend))
            {
                // RPC_PeerInfo(ZRpc rpc, ZPackage pkg): arg0=this, arg1=rpc
                output.Add(new CodeInstruction(OpCodes.Ldarg_1).MoveLabelsFrom(instruction).MoveBlocksFrom(instruction));
                output.Add(new CodeInstruction(OpCodes.Call, BackendForMethod));
                replaced++;
                continue;
            }
            output.Add(instruction);
        }
        if (replaced != ExpectedReads)
            throw new InvalidOperationException("expected " + ExpectedReads + " m_onlineBackend reads in RPC_PeerInfo, found " + replaced);
        return output;
    }
}
