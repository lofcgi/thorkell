using System;
using System.Collections.Generic;

namespace Thorkell.Core;

public sealed class GameBuild
{
    public string Game { get; set; } = "";
    public int Network { get; set; }
    public string Unity { get; set; } = "";
    // 파일 이름(예: assembly_valheim.dll) -> 소문자 sha256 hex
    public Dictionary<string, string> Sha256 { get; set; } = new Dictionary<string, string>();
}

public sealed class GateResult
{
    public bool Ok { get; }
    public IReadOnlyList<string> Problems { get; }

    public GateResult(bool ok, IReadOnlyList<string> problems)
    {
        Ok = ok;
        Problems = problems;
    }
}

// 시험한 빌드와 정확히 같을 때만 통과한다. 조용한 핫픽스도 해시로 잡는다.
public static class VersionGate
{
    public static GateResult Evaluate(GameBuild found, IEnumerable<GameBuild> tested, Version bepinex, Version minBepInEx)
    {
        var problems = new List<string>();
        if (bepinex < minBepInEx)
            problems.Add("bepinex " + bepinex + " < " + minBepInEx);

        GameBuild? match = null;
        foreach (var build in tested)
            if (build.Game == found.Game)
                match = build;

        if (match == null)
        {
            problems.Add("untested game version " + found.Game);
            return new GateResult(false, problems);
        }

        if (match.Network != found.Network)
            problems.Add("network " + found.Network + " != tested " + match.Network);
        if (match.Unity != found.Unity)
            problems.Add("unity " + found.Unity + " != tested " + match.Unity);
        foreach (var pair in match.Sha256)
        {
            if (!found.Sha256.TryGetValue(pair.Key, out var hash))
                problems.Add("missing hash for " + pair.Key);
            else if (!string.Equals(hash, pair.Value, StringComparison.OrdinalIgnoreCase))
                problems.Add(pair.Key + " sha256 differs from tested build");
        }
        return new GateResult(problems.Count == 0, problems);
    }
}
