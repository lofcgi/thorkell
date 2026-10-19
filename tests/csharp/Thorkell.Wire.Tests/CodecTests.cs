using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Thorkell.Wire;

namespace Thorkell.Wire.Tests;

public class CodecTests
{
    static readonly string FixtureDir = Path.GetFullPath(
        Path.Combine(AppContext.BaseDirectory, "../../../../../../protocol/v1/fixtures"));

    public static IEnumerable<object[]> Fixtures() =>
        Directory.GetFiles(FixtureDir, "*.json").OrderBy(p => p).Select(p => new object[] { Path.GetFileName(p) });

    static JObject Load(string name)
    {
        using var reader = new JsonTextReader(new StringReader(File.ReadAllText(Path.Combine(FixtureDir, name))))
        {
            DateParseHandling = DateParseHandling.None,
        };
        return JObject.Load(reader);
    }

    [Theory]
    [MemberData(nameof(Fixtures))]
    public void FixtureRoundTripsExactly(string name)
    {
        var fixture = Load(name);
        var message = Codec.Decode(fixture.ToString(Formatting.None));
        Assert.Equal((string)fixture["t"]!, message.Type);

        using var reader = new JsonTextReader(new StringReader(Codec.Encode(message))) { DateParseHandling = DateParseHandling.None };
        var encoded = JObject.Load(reader);
        Assert.True(JToken.DeepEquals(fixture, encoded), name + "\nexpected " + fixture.ToString(Formatting.None) + "\nactual   " + encoded.ToString(Formatting.None));
    }

    [Fact]
    public void EveryKnownTypeHasAFixture()
    {
        var covered = Fixtures().Select(f => (string)Load((string)f[0])["t"]!).ToHashSet();
        foreach (var type in Codec.KnownTypes)
            Assert.Contains(type, covered);
    }

    [Fact]
    public void KoreanTextAndDateLikeStringsStayStrings()
    {
        var message = (Event)Codec.Decode(Load("event_chat_ko.json").ToString(Formatting.None));
        Assert.Equal(JTokenType.String, message.Data["text"]!.Type);
        Assert.Equal("토르켈, 나무 좀 해줘. 2026-10-02 까지!", (string)message.Data["text"]!);
    }

    [Fact]
    public void SequenceBeyondDoublePrecisionSurvives()
    {
        var ack = (Ack)Codec.Decode(Load("ack.json").ToString(Formatting.None));
        Assert.Equal(9007199254740993L, ack.Seq);
        Assert.Contains("9007199254740993", Codec.Encode(ack));
    }

    [Fact]
    public void UnknownFieldsAreIgnored()
    {
        var message = Codec.Decode("{\"v\":1,\"t\":\"stop_all\",\"seq\":1,\"ts\":2,\"reason\":\"x\",\"added_in_1_1\":true}");
        Assert.Equal("x", ((StopAll)message).Reason);
    }

    [Theory]
    [InlineData("{\"v\":2,\"t\":\"stop_all\",\"seq\":1,\"ts\":2}", "major_mismatch")]
    [InlineData("{\"t\":\"stop_all\",\"seq\":1,\"ts\":2}", "bad_envelope")]
    [InlineData("{\"v\":1,\"seq\":1,\"ts\":2}", "bad_envelope")]
    [InlineData("{\"v\":1,\"t\":\"teleport\",\"seq\":1,\"ts\":2}", "unknown_type")]
    [InlineData("{\"v\":1,\"t\":\"ack\",\"seq\":\"many\",\"ts\":2}", "bad_body")]
    [InlineData("not json", "bad_json")]
    public void RejectsBadEnvelopes(string line, string code)
    {
        var error = Assert.Throws<ProtocolException>(() => Codec.Decode(line));
        Assert.Equal(code, error.Code);
    }

    [Fact]
    public void RejectsOversizeEncode()
    {
        var huge = new Event { Kind = "chat", Data = new JObject { ["text"] = new string('가', Protocol.MaxLineBytes / 3 + 1) } };
        var error = Assert.Throws<ProtocolException>(() => Codec.Encode(huge));
        Assert.Equal("line_too_long", error.Code);
    }

    [Fact]
    public void BodyHelpersUseSnakeCase()
    {
        var body = Codec.ToBody(new { ArriveRadius = 2.5, TargetId = "1:2" });
        Assert.Equal(2.5, (double)body["arrive_radius"]!);
        Assert.Equal("1:2", (string)body["target_id"]!);
    }
}

public class LineFramingTests
{
    [Fact]
    public void SplitsLinesAcrossChunksAndHandlesCrLf()
    {
        var a = Codec.Encode(new StopAll { Seq = 1, Reason = "첫 번째" });
        var b = Codec.Encode(new Cancel { Seq = 2, CmdId = "c1", Reason = "두 번째" });
        var payload = Encoding.UTF8.GetBytes(a + "\r\n\n" + b + "\n");
        var reader = new LineReader(new MemoryStream(payload));
        Assert.Equal("첫 번째", ((StopAll)Codec.Decode(reader.ReadLine()!)).Reason);
        Assert.Equal("두 번째", ((Cancel)Codec.Decode(reader.ReadLine()!)).Reason);
        Assert.Null(reader.ReadLine());
    }

    [Fact]
    public void TruncatedTailIsAnError()
    {
        var reader = new LineReader(new MemoryStream(Encoding.UTF8.GetBytes("{\"v\":1")));
        var error = Assert.Throws<ProtocolException>(() => reader.ReadLine());
        Assert.Equal("truncated_line", error.Code);
    }

    [Fact]
    public void OversizeLineIsAnError()
    {
        var reader = new LineReader(new MemoryStream(new byte[Protocol.MaxLineBytes + 10]));
        var error = Assert.Throws<ProtocolException>(() => reader.ReadLine());
        Assert.Equal("line_too_long", error.Code);
    }

    [Fact]
    public void WriterTerminatesEachMessageWithNewline()
    {
        var stream = new MemoryStream();
        var writer = new LineWriter(stream);
        writer.Write(new StopAll { Seq = 1, Reason = "a" });
        writer.Write(new StopAll { Seq = 2, Reason = "b" });
        var text = Encoding.UTF8.GetString(stream.ToArray());
        Assert.Equal(2, text.Count(c => c == '\n'));
        Assert.EndsWith("\n", text);
    }
}

public class AuthTests
{
    static readonly string VectorFile = Path.GetFullPath(
        Path.Combine(AppContext.BaseDirectory, "../../../../../../protocol/v1/hmac_vectors.json"));

    [Fact]
    public void MatchesSharedVectors()
    {
        foreach (var vector in JArray.Parse(File.ReadAllText(VectorFile)))
        {
            var mac = Auth.Mac((string)vector["token"]!, (string)vector["nonce"]!, (string)vector["role"]!, (string)vector["session"]!);
            Assert.Equal((string)vector["mac"]!, mac);
            Assert.True(Auth.Verify((string)vector["token"]!, (string)vector["nonce"]!, (string)vector["role"]!, (string)vector["session"]!, mac.ToUpperInvariant()));
        }
    }

    [Fact]
    public void RejectsWrongRoleOrTamperedMac()
    {
        var token = Auth.NewHex(32);
        var mac = Auth.Mac(token, "n", "body", "s");
        Assert.False(Auth.Verify(token, "n", "host", "s", mac));
        Assert.False(Auth.Verify(token, "n", "body", "s", mac.Substring(1) + "0"));
        Assert.False(Auth.Verify(token, "n", "body", "s", ""));
    }

    [Fact]
    public void NewHexHasRequestedLength()
    {
        Assert.Equal(64, Auth.NewHex(32).Length);
        Assert.NotEqual(Auth.NewHex(16), Auth.NewHex(16));
    }
}
