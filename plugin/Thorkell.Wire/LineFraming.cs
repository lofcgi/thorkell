using System.IO;
using System.Text;

namespace Thorkell.Wire;

// 줄 단위 JSON(NDJSON). JSON 문자열 안의 개행은 이스케이프되므로 '\n'이 곧 메시지 경계다.
public sealed class LineReader
{
    readonly Stream stream;
    readonly byte[] chunk = new byte[8192];
    readonly MemoryStream pending = new MemoryStream();
    int chunkOffset;
    int chunkLength;

    public LineReader(Stream stream)
    {
        this.stream = stream;
    }

    // 스트림이 끝나면 null. 끝났는데 미완성 줄이 남아 있으면 예외.
    public string? ReadLine()
    {
        while (true)
        {
            if (chunkOffset == chunkLength)
            {
                chunkLength = stream.Read(chunk, 0, chunk.Length);
                chunkOffset = 0;
                if (chunkLength == 0)
                {
                    if (pending.Length > 0)
                        throw new ProtocolException("truncated_line", pending.Length + " bytes without newline at end of stream");
                    return null;
                }
            }

            int newline = System.Array.IndexOf(chunk, (byte)'\n', chunkOffset, chunkLength - chunkOffset);
            int take = (newline < 0 ? chunkLength : newline) - chunkOffset;
            if (pending.Length + take > Protocol.MaxLineBytes)
                throw new ProtocolException("line_too_long", "line exceeds " + Protocol.MaxLineBytes + " bytes");
            pending.Write(chunk, chunkOffset, take);

            if (newline < 0)
            {
                chunkOffset = chunkLength;
                continue;
            }

            chunkOffset = newline + 1;
            var line = Encoding.UTF8.GetString(pending.GetBuffer(), 0, (int)pending.Length);
            pending.SetLength(0);
            if (line.Length > 0 && line[line.Length - 1] == '\r')
                line = line.Substring(0, line.Length - 1);
            if (line.Length == 0)
                continue;
            return line;
        }
    }
}

public sealed class LineWriter
{
    static readonly UTF8Encoding Utf8 = new UTF8Encoding(false);
    readonly Stream stream;

    public LineWriter(Stream stream)
    {
        this.stream = stream;
    }

    public void Write(Message message)
    {
        var bytes = Utf8.GetBytes(Codec.Encode(message) + "\n");
        stream.Write(bytes, 0, bytes.Length);
        stream.Flush();
    }
}
