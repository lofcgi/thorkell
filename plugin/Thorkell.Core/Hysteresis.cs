using System;

namespace Thorkell.Core;

// 값이 enterBelow 아래로 내려가면 켜지고, exitAbove 위로 올라가야 꺼진다.
// Eira에서 단일 임계값 후퇴가 경계에서 진동했던 문제를 막는다.
public sealed class BelowHysteresis
{
    public float EnterBelow { get; }
    public float ExitAbove { get; }
    public bool Active { get; private set; }

    public BelowHysteresis(float enterBelow, float exitAbove)
    {
        if (!(exitAbove > enterBelow))
            throw new ArgumentException("exitAbove must be greater than enterBelow");
        EnterBelow = enterBelow;
        ExitAbove = exitAbove;
    }

    public bool Update(float value)
    {
        if (Active)
        {
            if (value > ExitAbove)
                Active = false;
        }
        else if (value < EnterBelow)
        {
            Active = true;
        }
        return Active;
    }
}
