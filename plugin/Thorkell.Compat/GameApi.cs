#nullable enable
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using BepInEx;
using Newtonsoft.Json.Linq;
using Thorkell.Core;

namespace Thorkell.Compat;

// 실행 중인 게임 빌드를 읽고 tested-versions.json과 비교한다. 게임 쪽 값은 모두 런타임에 읽는다:
// c_networkVersion 같은 const는 컴파일 시점 값으로 박히므로 리플렉션으로 꺼내야 한다.
internal static class GameApi
{
    public static GameBuild ReadBuild()
    {
        var version = global::Version.CurrentVersion;
        var network = typeof(global::Version).GetField("c_networkVersion", BindingFlags.Public | BindingFlags.Static)
            ?? throw new MissingFieldException("Version", "c_networkVersion");
        var build = new GameBuild
        {
            Game = version.m_major + "." + version.m_minor + "." + version.m_patch,
            Network = Convert.ToInt32(network.GetRawConstantValue()),
            Unity = UnityEngine.Application.unityVersion,
        };
        build.Sha256["assembly_valheim.dll"] = Sha256(typeof(Player).Assembly.Location);
        build.Sha256["assembly_utils.dll"] = Sha256(typeof(ZInput).Assembly.Location);
        return build;
    }

    public static GateResult CheckBuild(out GameBuild found)
    {
        found = ReadBuild();
        var root = JObject.Parse(ReadResource("Thorkell.tested-versions.json"));
        var tested = root["builds"]!.Select(b => new GameBuild
        {
            Game = (string)b["game"]!,
            Network = (int)b["network"]!,
            Unity = (string)b["unity"]!,
            Sha256 = ((JObject)b["sha256"]!).Properties().ToDictionary(p => p.Name, p => (string)p.Value!),
        }).ToList();
        var minBepInEx = System.Version.Parse((string)root["min_bepinex"]!);
        var bepinex = typeof(BaseUnityPlugin).Assembly.GetName().Version;
        return VersionGate.Evaluate(found, tested, bepinex, minBepInEx);
    }

    static string Sha256(string path)
    {
        using (var sha = SHA256.Create())
        using (var stream = File.OpenRead(path))
            return string.Concat(sha.ComputeHash(stream).Select(b => b.ToString("x2")));
    }

    static string ReadResource(string name)
    {
        using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(name)
            ?? throw new FileNotFoundException("embedded resource missing", name))
        using (var reader = new StreamReader(stream))
            return reader.ReadToEnd();
    }
}
