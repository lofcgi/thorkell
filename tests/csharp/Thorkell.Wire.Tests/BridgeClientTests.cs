using System.Net;
using System.Net.Sockets;
using Newtonsoft.Json.Linq;
using Thorkell.Wire;

namespace Thorkell.Wire.Tests;

// 두뇌(brain/thorkell/body/link.py)와 같은 핸드셰이크를 하는 가짜 서버로 클라이언트를 검증한다.
public class BridgeClientTests
{
    const string Token = "5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a";

    static Hello NewHello() => new Hello
    {
        Role = Roles.Body,
        Plugin = "0.1.0",
        Game = new GameInfo { Version = "1.0.16", Network = 40, AssemblySha256 = "00" },
        Caps = new[] { "observe", "move" },
    };

    sealed class FakeBrain : IDisposable
    {
        readonly TcpListener listener = new TcpListener(IPAddress.Loopback, 0);
        public int Port { get; }

        public FakeBrain()
        {
            listener.Start();
            Port = ((IPEndPoint)listener.LocalEndpoint).Port;
        }

        public (LineReader reader, LineWriter writer, TcpClient tcp, Hello hello) Accept(string token, string? rejectReason = null)
        {
            var tcp = listener.AcceptTcpClient();
            var stream = tcp.GetStream();
            var reader = new LineReader(stream);
            var writer = new LineWriter(stream);
            var nonce = Auth.NewHex(16);
            writer.Write(new Challenge { Seq = 1, Nonce = nonce });
            var hello = (Hello)Codec.Decode(reader.ReadLine()!);
            var ok = Auth.Verify(token, nonce, hello.Role, hello.Session, hello.Mac);
            if (rejectReason != null || !ok)
                writer.Write(new Reject { Seq = 2, Reason = rejectReason ?? "bad_mac" });
            else
                writer.Write(new Welcome { Seq = 2, AcceptedCaps = hello.Caps, StateHz = 10, SceneHz = 2 });
            return (reader, writer, tcp, hello);
        }

        public void Dispose() => listener.Stop();
    }

    static T WaitFor<T>(Func<T?> probe, int ms = 3000) where T : class
    {
        var deadline = DateTime.UtcNow.AddMilliseconds(ms);
        while (DateTime.UtcNow < deadline)
        {
            var value = probe();
            if (value != null)
                return value;
            Thread.Sleep(10);
        }
        throw new TimeoutException();
    }

    [Fact]
    public void HandshakeThenMessagesFlowBothWays()
    {
        using var brain = new FakeBrain();
        using var client = new BridgeClient("127.0.0.1", brain.Port, Token, NewHello, new[] { 50 });
        client.Start();
        var (reader, writer, tcp, hello) = brain.Accept(Token);
        using var _ = tcp;
        Assert.Equal(32, hello.Session.Length);
        Assert.Equal(1, hello.Seq);

        WaitFor(() => client.Connected ? "yes" : null);
        Assert.Equal(10, client.Welcome!.StateHz);

        client.Send(new Event { Kind = "chat", Data = new JObject { ["text"] = "안녕" } });
        client.Send(new Event { Kind = "chat", Data = new JObject { ["text"] = "둘째" } });
        var first = (Event)Codec.Decode(reader.ReadLine()!);
        var second = (Event)Codec.Decode(reader.ReadLine()!);
        Assert.Equal("안녕", (string)first.Data["text"]!);
        Assert.Equal(2, first.Seq);
        Assert.Equal(3, second.Seq);

        writer.Write(new Command { Seq = 3, Id = "c1", Op = "navigate", BasedOnSeq = 3, TtlMs = 1000 });
        var command = WaitFor(() => client.Incoming.TryDequeue(out var m) ? m : null);
        Assert.Equal("c1", ((Command)command).Id);
    }

    [Fact]
    public void RejectionIsReportedAndRetriedWithBackoff()
    {
        using var brain = new FakeBrain();
        using var client = new BridgeClient("127.0.0.1", brain.Port, "00" + Token.Substring(2), NewHello, new[] { 50 });
        client.Start();
        var (_, _, tcp, _) = brain.Accept(Token);
        tcp.Dispose();
        var notice = WaitFor(() => client.Notices.TryDequeue(out var n) ? n : null);
        Assert.Contains("rejected", notice);
        Assert.False(client.Connected);

        var (_, _, retry, _) = brain.Accept(Token);
        retry.Dispose();
    }

    [Fact]
    public void QueuedMessagesAreSentAfterConnecting()
    {
        using var brain = new FakeBrain();
        using var client = new BridgeClient("127.0.0.1", brain.Port, Token, NewHello, new[] { 50 });
        client.Send(new Event { Kind = "chat", Data = new JObject { ["text"] = "접속 전" } });
        client.Start();
        var (reader, _, tcp, _) = brain.Accept(Token);
        using var _ = tcp;
        var queued = (Event)Codec.Decode(reader.ReadLine()!);
        Assert.Equal("접속 전", (string)queued.Data["text"]!);
    }

    [Fact]
    public void OutboxLimitRefusesInsteadOfDroppingOldMessages()
    {
        using var client = new BridgeClient("127.0.0.1", 1, Token, NewHello);
        for (int i = 0; i < BridgeClient.OutboxLimit; i++)
            Assert.True(client.Send(new StopAll { Reason = "fill" }));
        Assert.False(client.Send(new StopAll { Reason = "overflow" }));
        Assert.Equal(1, client.OutboxOverflows);
    }
}
