using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace Thorkell.Wire;

// 모든 메시지는 한 줄짜리 평평한 JSON 객체다: {"v":1,"t":"...","seq":n,"ts":unix_ms, ...본문}.
// op/kind마다 달라지는 내용(args, data, evidence, metrics)은 JObject로 싣고,
// 그 스키마는 protocol/v1의 Python 모델과 fixture가 정한다.
public abstract class Message
{
    public int V { get; set; } = Protocol.Major;

    [JsonProperty("t")]
    public abstract string Type { get; }

    public long Seq { get; set; }
    public long Ts { get; set; }
}

public sealed class GameInfo
{
    public string Version { get; set; } = "";
    public int Network { get; set; }
    public string AssemblySha256 { get; set; } = "";
}

public sealed class VersionGateInfo
{
    public bool Ok { get; set; }
    public string Found { get; set; } = "";
    public string Tested { get; set; } = "";
}

// brain -> plugin
public sealed class Challenge : Message
{
    public override string Type => "challenge";
    public string Nonce { get; set; } = "";
    public int[] Proto { get; set; } = { Protocol.Major, Protocol.Minor };
}

// plugin -> brain
public sealed class Hello : Message
{
    public override string Type => "hello";
    public string Role { get; set; } = "";
    public int[] Proto { get; set; } = { Protocol.Major, Protocol.Minor };
    public string Plugin { get; set; } = "";
    public GameInfo Game { get; set; } = new GameInfo();
    public string Session { get; set; } = "";
    public string[] Caps { get; set; } = new string[0];
    public string Mac { get; set; } = "";
}

// brain -> plugin
public sealed class Welcome : Message
{
    public override string Type => "welcome";
    public string[] AcceptedCaps { get; set; } = new string[0];
    public int StateHz { get; set; }
    public int SceneHz { get; set; }
}

// brain -> plugin
public sealed class Reject : Message
{
    public override string Type => "reject";
    public string Reason { get; set; } = "";
}

// plugin -> brain, 1 Hz 하트비트를 겸한다.
public sealed class Status : Message
{
    public override string Type => "status";
    public bool Armed { get; set; }
    public bool Ready { get; set; }
    public string[] Reasons { get; set; } = new string[0];
    public VersionGateInfo VersionGate { get; set; } = new VersionGateInfo();
    public JObject? Perf { get; set; }
}

// body -> brain
public sealed class State : Message
{
    public override string Type => "state";
    public long Tick { get; set; }
    public JObject Data { get; set; } = new JObject();
}

// body -> brain
public sealed class Scene : Message
{
    public override string Type => "scene";
    public long Tick { get; set; }
    public JObject Data { get; set; } = new JObject();
}

// plugin -> brain, 절대 버리지 않는다.
public sealed class Event : Message
{
    public override string Type => "event";
    public string Kind { get; set; } = "";
    public long Tick { get; set; }
    public JObject Data { get; set; } = new JObject();
}

// brain -> body
public sealed class Command : Message
{
    public override string Type => "cmd";
    public string Id { get; set; } = "";
    public string Op { get; set; } = "";
    public JObject Args { get; set; } = new JObject();
    public string Mode { get; set; } = CommandModes.Replace;
    public int Priority { get; set; }
    public long BasedOnSeq { get; set; }
    public int TtlMs { get; set; }
    public bool Resume { get; set; }
}

// brain -> body
public sealed class Cancel : Message
{
    public override string Type => "cancel";
    public string CmdId { get; set; } = "";
    public string Reason { get; set; } = "";
}

// brain -> body
public sealed class StopAll : Message
{
    public override string Type => "stop_all";
    public string Reason { get; set; } = "";
}

// body -> brain
public sealed class Ack : Message
{
    public override string Type => "ack";
    public string CmdId { get; set; } = "";
    public bool Accepted { get; set; }
    public string Code { get; set; } = "";
}

// body -> brain, 최대 2 Hz
public sealed class Progress : Message
{
    public override string Type => "progress";
    public string CmdId { get; set; } = "";
    public JObject Metrics { get; set; } = new JObject();
}

// body -> brain
public sealed class Result : Message
{
    public override string Type => "result";
    public string CmdId { get; set; } = "";
    public string Status { get; set; } = "";
    public string Code { get; set; } = "";
    public JObject Evidence { get; set; } = new JObject();
}

// brain -> plugin
public sealed class Query : Message
{
    public override string Type => "query";
    public string Id { get; set; } = "";
    public string What { get; set; } = "";
    public JObject Args { get; set; } = new JObject();
}

// plugin -> brain
public sealed class QueryResult : Message
{
    public override string Type => "query_result";
    public string Id { get; set; } = "";
    public bool Ok { get; set; }
    public JToken? Data { get; set; }
    public string? Error { get; set; }
}

// brain -> plugin
public sealed class Config : Message
{
    public override string Type => "config";
    public JObject Values { get; set; } = new JObject();
}
