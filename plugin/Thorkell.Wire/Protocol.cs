using System;

namespace Thorkell.Wire;

public static class Protocol
{
    public const int Major = 1;
    public const int Minor = 0;
    public const int MaxLineBytes = 256 * 1024;
}

public sealed class ProtocolException : Exception
{
    public string Code { get; }

    public ProtocolException(string code, string message) : base(code + ": " + message)
    {
        Code = code;
    }
}

public static class Roles
{
    public const string Body = "body";
    public const string Host = "host";
}

public static class CommandModes
{
    public const string Replace = "replace";
    public const string Queue = "queue";
    public const string Interrupt = "interrupt";
}

public static class ResultStatuses
{
    public const string Succeeded = "succeeded";
    public const string Failed = "failed";
    public const string Cancelled = "cancelled";
    public const string Preempted = "preempted";
}
