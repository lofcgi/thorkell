using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading;

namespace Thorkell.Wire;

// 플러그인 쪽 연결. 백그라운드 스레드가 접속·핸드셰이크·수신을 맡고, 별도 스레드가 송신함을 비운다.
// Unity 메인 스레드는 Incoming을 꺼내 쓰고 Send로 넣기만 하므로 소켓 때문에 프레임이 멈추지 않는다.
public sealed class BridgeClient : IDisposable
{
    public const int OutboxLimit = 10000;

    readonly string host;
    readonly int port;
    readonly string tokenHex;
    readonly Func<Hello> helloFactory;
    readonly int[] backoffMs;
    readonly Thread thread;
    readonly BlockingCollection<Message> outbox = new BlockingCollection<Message>(new ConcurrentQueue<Message>());
    volatile bool disposed;
    volatile bool connected;
    TcpClient? client;

    public ConcurrentQueue<Message> Incoming { get; } = new ConcurrentQueue<Message>();
    // 연결 상태 변화와 오류를 메인 스레드가 로그로 남길 수 있게 쌓아 둔다.
    public ConcurrentQueue<string> Notices { get; } = new ConcurrentQueue<string>();
    public bool Connected => connected;
    public Welcome? Welcome { get; private set; }
    public long OutboxOverflows;

    public BridgeClient(string host, int port, string tokenHex, Func<Hello> helloFactory, int[]? backoffMs = null)
    {
        this.host = host;
        this.port = port;
        this.tokenHex = tokenHex;
        this.helloFactory = helloFactory;
        this.backoffMs = backoffMs ?? new[] { 1000, 2000, 5000 };
        thread = new Thread(Run) { IsBackground = true, Name = "thorkell-bridge" };
    }

    public void Start() => thread.Start();

    // 연결이 없어도 쌓아 두었다가 재접속 후 보낸다. 한도를 넘으면 오래된 것을 버리지 않고 실패를 알린다.
    public bool Send(Message message)
    {
        if (outbox.Count >= OutboxLimit)
        {
            Interlocked.Increment(ref OutboxOverflows);
            return false;
        }
        outbox.Add(message);
        return true;
    }

    void Run()
    {
        int attempt = 0;
        while (!disposed)
        {
            try
            {
                using (var tcp = new TcpClient(AddressFamily.InterNetwork))
                {
                    tcp.NoDelay = true;
                    tcp.Connect(IPAddress.Parse(host), port);
                    client = tcp;
                    var stream = tcp.GetStream();
                    var reader = new LineReader(stream);
                    var writer = new LineWriter(stream);
                    Handshake(reader, writer);
                    attempt = 0;
                    connected = true;
                    Notices.Enqueue("connected to brain " + host + ":" + port);
                    var sender = new Thread(() => Drain(writer)) { IsBackground = true, Name = "thorkell-bridge-send" };
                    sender.Start();
                    try
                    {
                        string? line;
                        while (!disposed && (line = reader.ReadLine()) != null)
                            Incoming.Enqueue(Codec.Decode(line));
                    }
                    finally
                    {
                        connected = false;
                        tcp.Close();
                        sender.Join(1000);
                    }
                    Notices.Enqueue("brain closed the connection");
                }
            }
            catch (Exception e) when (e is SocketException || e is IOException || e is ProtocolException || e is ObjectDisposedException)
            {
                connected = false;
                if (!disposed)
                    Notices.Enqueue("bridge error: " + e.GetType().Name + ": " + e.Message);
            }
            if (disposed)
                return;
            Thread.Sleep(backoffMs[Math.Min(attempt, backoffMs.Length - 1)]);
            attempt++;
        }
    }

    void Handshake(LineReader reader, LineWriter writer)
    {
        var first = Codec.Decode(reader.ReadLine() ?? throw new IOException("closed before challenge"));
        if (!(first is Challenge challenge))
            throw new ProtocolException("bad_handshake", "expected challenge, got " + first.Type);
        var hello = helloFactory();
        hello.Seq = 1;
        hello.Ts = NowMs();
        hello.Session = Auth.NewHex(16);
        hello.Mac = Auth.Mac(tokenHex, challenge.Nonce, hello.Role, hello.Session);
        writer.Write(hello);
        sequence = 1;

        var reply = Codec.Decode(reader.ReadLine() ?? throw new IOException("closed before welcome"));
        if (reply is Reject reject)
            throw new ProtocolException("rejected", reject.Reason);
        if (!(reply is Welcome welcome))
            throw new ProtocolException("bad_handshake", "expected welcome, got " + reply.Type);
        Welcome = welcome;
    }

    long sequence;

    void Drain(LineWriter writer)
    {
        try
        {
            while (connected && !disposed)
            {
                if (!outbox.TryTake(out var message, 200))
                    continue;
                message.Seq = ++sequence;
                message.Ts = NowMs();
                writer.Write(message);
            }
        }
        catch (Exception e) when (e is IOException || e is ObjectDisposedException || e is ProtocolException)
        {
            Notices.Enqueue("bridge send failed: " + e.Message);
            client?.Close();
        }
    }

    static long NowMs() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

    public void Dispose()
    {
        disposed = true;
        client?.Close();
        outbox.CompleteAdding();
    }
}
