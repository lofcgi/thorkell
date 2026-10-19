using System;
using System.Numerics;

namespace Thorkell.Core;

// 정보 동등성: 토르켈 자신의 화면에서 사람이 알 수 있는 것만 두뇌에 넘긴다.
// 수치는 1.0.20 에셋의 EnemyHud 값(m_maxShowDistance 30, 보스 100, 조준 후 60초 유지)을 따른다.
public static class Parity
{
    public const float NearSenseRadius = 4f;
    public const float HudRadius = 30f;
    public const float BossHudRadius = 100f;
    public const double HoverPersistSeconds = 60.0;

    // 시야에 있거나 바로 곁(4m)이면 존재를 안다. 범위 밖이면 모른다.
    public static bool Perceived(float distance, bool lineOfSight, float maxRange) =>
        distance <= maxRange && (lineOfSight || distance <= NearSenseRadius);

    // 이름·체력바·별 등급은 게임이 머리 위 HUD를 띄울 때만 안다(EnemyHud.UpdateHuds).
    // 보통 생물은 30m 안에서 최근 60초 안에 조준한 적이 있을 때만, 보스는 깨어 있고 100m 안일 때만 띄운다.
    public static bool ShowsStats(float distance, bool isBoss, bool alerted, double secondsSinceHover) =>
        isBoss ? alerted && distance <= BossHudRadius : distance <= HudRadius && secondsSinceHover <= HoverPersistSeconds;
}

// DamageText에는 공격자 정보가 없다. 자기 근접 공격이 실제로 판정된 시각·위치와 가까운 텍스트만 자기 것으로 본다.
public sealed class DamageAttribution
{
    readonly double window;
    readonly float radius;
    double lastHitAt = double.NegativeInfinity;
    Vector3 lastHitFrom;

    public DamageAttribution(double windowSeconds, float radius)
    {
        if (windowSeconds <= 0 || radius <= 0)
            throw new ArgumentException("window and radius must be positive");
        window = windowSeconds;
        this.radius = radius;
    }

    public void RecordOwnHit(double now, Vector3 attackerPosition)
    {
        lastHitAt = now;
        lastHitFrom = attackerPosition;
    }

    public bool IsOwn(double now, Vector3 textPosition) =>
        now >= lastHitAt && now - lastHitAt <= window && Vector3.Distance(textPosition, lastHitFrom) <= radius;
}
