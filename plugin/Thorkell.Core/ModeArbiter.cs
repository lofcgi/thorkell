using System;
using System.Collections.Generic;

namespace Thorkell.Core;

// 반사 모드 우선순위. 숫자가 작을수록 우선한다. 두뇌의 행동은 어떤 모드도 활성이 아닐 때만 모터를 잡는다.
public enum ReflexMode
{
    HardStop = 0,
    SelfPreservation = 1,
    SelfDefense = 2,
    Unstuck = 3,
}

public enum TransitionKind
{
    None,
    Engaged,
    Switched,
    Released,
}

public readonly struct Transition
{
    public TransitionKind Kind { get; }
    public ReflexMode? From { get; }
    public ReflexMode? To { get; }

    public Transition(TransitionKind kind, ReflexMode? from, ReflexMode? to)
    {
        Kind = kind;
        From = from;
        To = to;
    }

    public static Transition Nothing => new Transition(TransitionKind.None, null, null);
}

// 매 틱 활성 모드 집합을 받아 모터 소유자를 정한다.
// 모드가 모두 꺼진 뒤 quietSeconds 동안 조용해야 Released를 내보내고, 그때 두뇌 행동을 재개할 수 있다.
public sealed class ModeArbiter
{
    readonly double quietSeconds;
    double quietSince = double.NaN;

    public ReflexMode? Owner { get; private set; }

    public ModeArbiter(double quietSeconds)
    {
        if (quietSeconds < 0)
            throw new ArgumentException("quietSeconds must be >= 0");
        this.quietSeconds = quietSeconds;
    }

    // 두뇌가 같은 상황을 넘겨받았을 때(예: 반격 중인 적에게 두뇌가 공격 명령) 조용히 기다리지 않고 바로 놓는다.
    public Transition ReleaseNow()
    {
        if (Owner == null)
            return Transition.Nothing;
        var released = Owner;
        Owner = null;
        quietSince = double.NaN;
        return new Transition(TransitionKind.Released, released, null);
    }

    public Transition Update(IEnumerable<ReflexMode> active, double now)
    {
        ReflexMode? best = null;
        foreach (var mode in active)
            if (best == null || mode < best.Value)
                best = mode;

        if (best != null)
        {
            quietSince = double.NaN;
            if (Owner == null)
            {
                Owner = best;
                return new Transition(TransitionKind.Engaged, null, best);
            }
            if (Owner.Value != best.Value)
            {
                var from = Owner;
                Owner = best;
                return new Transition(TransitionKind.Switched, from, best);
            }
            return Transition.Nothing;
        }

        if (Owner == null)
            return Transition.Nothing;
        if (double.IsNaN(quietSince))
            quietSince = now;
        if (now - quietSince < quietSeconds)
            return Transition.Nothing;

        var released = Owner;
        Owner = null;
        quietSince = double.NaN;
        return new Transition(TransitionKind.Released, released, null);
    }
}
