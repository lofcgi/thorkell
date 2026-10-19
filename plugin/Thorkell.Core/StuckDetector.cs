using System;

namespace Thorkell.Core;

// 남은 거리가 window초 동안 minProgress 이상 줄지 않으면 끼인 것으로 본다.
// 진척은 위치가 아니라 목표까지 남은 거리로 잰다(제자리걸음·벽 비비기를 잡기 위해).
public sealed class StuckDetector
{
    readonly double window;
    readonly float minProgress;
    double bestAt = double.NaN;
    float best = float.MaxValue;

    public StuckDetector(double windowSeconds, float minProgress)
    {
        if (windowSeconds <= 0 || minProgress <= 0)
            throw new ArgumentException("window and progress must be positive");
        window = windowSeconds;
        this.minProgress = minProgress;
    }

    public bool Update(double now, float remaining)
    {
        if (double.IsNaN(bestAt) || remaining < best - minProgress)
        {
            best = remaining;
            bestAt = now;
            return false;
        }
        return now - bestAt >= window;
    }

    public void Reset()
    {
        bestAt = double.NaN;
        best = float.MaxValue;
    }
}
