using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Newtonsoft.Json.Serialization;

namespace Thorkell.Wire;

public static class Codec
{
    public static readonly JsonSerializerSettings Settings = new JsonSerializerSettings
    {
        ContractResolver = new DefaultContractResolver { NamingStrategy = new SnakeCaseNamingStrategy() },
        NullValueHandling = NullValueHandling.Ignore,
        MissingMemberHandling = MissingMemberHandling.Ignore,
        // 채팅 원문 같은 문자열이 날짜처럼 생겨도 문자열로 남겨야 한다.
        DateParseHandling = DateParseHandling.None,
        FloatParseHandling = FloatParseHandling.Double,
        Formatting = Formatting.None,
    };

    static readonly JsonSerializer Serializer = JsonSerializer.Create(Settings);

    static readonly Dictionary<string, Type> Types = new Dictionary<string, Type>
    {
        ["challenge"] = typeof(Challenge),
        ["hello"] = typeof(Hello),
        ["welcome"] = typeof(Welcome),
        ["reject"] = typeof(Reject),
        ["status"] = typeof(Status),
        ["state"] = typeof(State),
        ["scene"] = typeof(Scene),
        ["event"] = typeof(Event),
        ["cmd"] = typeof(Command),
        ["cancel"] = typeof(Cancel),
        ["stop_all"] = typeof(StopAll),
        ["ack"] = typeof(Ack),
        ["progress"] = typeof(Progress),
        ["result"] = typeof(Result),
        ["query"] = typeof(Query),
        ["query_result"] = typeof(QueryResult),
        ["config"] = typeof(Config),
    };

    public static IEnumerable<string> KnownTypes => Types.Keys;

    public static string Encode(Message message)
    {
        var line = JsonConvert.SerializeObject(message, Settings);
        if (Encoding.UTF8.GetByteCount(line) > Protocol.MaxLineBytes)
            throw new ProtocolException("line_too_long", message.Type + " exceeds " + Protocol.MaxLineBytes + " bytes");
        return line;
    }

    public static Message Decode(string line)
    {
        if (Encoding.UTF8.GetByteCount(line) > Protocol.MaxLineBytes)
            throw new ProtocolException("line_too_long", "incoming line exceeds " + Protocol.MaxLineBytes + " bytes");

        JObject obj;
        using (var reader = new JsonTextReader(new StringReader(line)))
        {
            reader.DateParseHandling = DateParseHandling.None;
            reader.FloatParseHandling = FloatParseHandling.Double;
            try
            {
                obj = JObject.Load(reader);
            }
            catch (JsonReaderException e)
            {
                throw new ProtocolException("bad_json", e.Message);
            }
        }

        var version = obj["v"];
        if (version == null || version.Type != JTokenType.Integer)
            throw new ProtocolException("bad_envelope", "missing integer v");
        if ((int)version != Protocol.Major)
            throw new ProtocolException("major_mismatch", "got v=" + (int)version + ", expected " + Protocol.Major);

        var type = obj["t"];
        if (type == null || type.Type != JTokenType.String)
            throw new ProtocolException("bad_envelope", "missing string t");
        if (!Types.TryGetValue((string)type!, out var target))
            throw new ProtocolException("unknown_type", (string)type!);

        try
        {
            return (Message)obj.ToObject(target, Serializer)!;
        }
        catch (JsonException e)
        {
            throw new ProtocolException("bad_body", (string)type! + ": " + e.Message);
        }
    }

    // op/kind별 DTO를 JObject 본문으로 바꿀 때 같은 snake_case 규칙을 쓴다.
    public static JObject ToBody(object dto) => JObject.FromObject(dto, Serializer);

    public static T FromBody<T>(JObject body) => body.ToObject<T>(Serializer)!;
}
