using System;
using System.Security.Cryptography;
using System.Text;

namespace Thorkell.Wire;

// 핸드셰이크: brain이 nonce를 보내면 plugin이 HMAC-SHA256(token, "nonce|role|session")을 hex로 돌려준다.
// token은 실행마다 brain이 만든 32바이트 난수의 hex 문자열이고, HMAC 키는 그 hex를 디코드한 바이트다.
public static class Auth
{
    public static string NewHex(int bytes)
    {
        var buffer = new byte[bytes];
        using (var rng = RandomNumberGenerator.Create())
            rng.GetBytes(buffer);
        return ToHex(buffer);
    }

    public static string Mac(string tokenHex, string nonce, string role, string session)
    {
        using (var hmac = new HMACSHA256(FromHex(tokenHex)))
            return ToHex(hmac.ComputeHash(Encoding.UTF8.GetBytes(nonce + "|" + role + "|" + session)));
    }

    public static bool Verify(string tokenHex, string nonce, string role, string session, string mac)
    {
        var expected = Encoding.ASCII.GetBytes(Mac(tokenHex, nonce, role, session));
        var actual = Encoding.ASCII.GetBytes(mac.ToLowerInvariant());
        if (expected.Length != actual.Length)
            return false;
        int diff = 0;
        for (int i = 0; i < expected.Length; i++)
            diff |= expected[i] ^ actual[i];
        return diff == 0;
    }

    public static string ToHex(byte[] bytes)
    {
        var builder = new StringBuilder(bytes.Length * 2);
        foreach (var b in bytes)
            builder.Append(b.ToString("x2"));
        return builder.ToString();
    }

    public static byte[] FromHex(string hex)
    {
        if (hex.Length % 2 != 0)
            throw new ProtocolException("bad_token", "hex length must be even");
        var bytes = new byte[hex.Length / 2];
        for (int i = 0; i < bytes.Length; i++)
            bytes[i] = Convert.ToByte(hex.Substring(i * 2, 2), 16);
        return bytes;
    }
}
