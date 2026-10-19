using System;
using System.IO;
using HarmonyLib;

namespace Thorkell.Body;

// 메뉴가 준비된 뒤 사람의 호스트 루프백 리스너로 직접 접속한다(Eira에서 검증된 경로).
// 네이티브 -joinserverwithcharacter는 FejdStartup.Awake 안에서 플랫폼 초기화 전에 돌고
// 공용 prefs에 "profile"을 쓰기 때문에 쓰지 않는다.
internal static class Join
{
    public static void Start(BodyPlugin body)
    {
        if (!SteamManager.Initialize())
            throw new InvalidOperationException("Steam initialization refused");

        var file = body.CharacterFile.Value;
        var path = Path.Combine(Utils.GetSaveDataPath(FileHelpers.FileSource.Local), "characters_local", file + ".fch");
        var profile = new PlayerProfile(file, FileHelpers.FileSource.Local);
        if (File.Exists(path))
        {
            if (!profile.Load())
                throw new InvalidOperationException("character file exists but failed to load: " + path);
        }
        else
        {
            profile.SetName(body.CharacterName.Value);
            // 발키리 인트로 컷신은 조작이 막히는 구간이라 건너뛴다.
            profile.m_firstSpawn = false;
            if (!profile.Save())
                throw new InvalidOperationException("could not create character " + path);
        }
        Game.SetProfile(file, FileHelpers.FileSource.Local);

        // 비밀번호는 명령줄에 두지 않고 private setter로 넣는다. RPC_ClientHandshake가 자동으로 쓴다.
        var setter = AccessTools.PropertySetter(typeof(FejdStartup), "ServerPassword")
            ?? throw new MissingMethodException("FejdStartup", "set_ServerPassword");
        setter.Invoke(null, new object[] { body.JoinPassword.Value });

        ZNet.SetServer(false, false, false, "", "", null);
        ZNet.SetServerHost(body.JoinHost.Value, body.JoinPort.Value, OnlineBackendType.Steamworks);
        var load = AccessTools.Method(typeof(FejdStartup), "LoadMainScene")
            ?? throw new MissingMethodException("FejdStartup", "LoadMainScene");
        load.Invoke(FejdStartup.instance, null);
    }
}
