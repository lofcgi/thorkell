using Thorkell.Core;

namespace Thorkell.Core.Tests;

public class HysteresisTests
{
    [Fact]
    public void DoesNotOscillateBetweenThresholds()
    {
        var retreat = new BelowHysteresis(0.35f, 0.60f);
        Assert.False(retreat.Update(0.50f));
        Assert.True(retreat.Update(0.34f));
        Assert.True(retreat.Update(0.40f));
        Assert.True(retreat.Update(0.59f));
        Assert.True(retreat.Update(0.60f));
        Assert.False(retreat.Update(0.61f));
        Assert.False(retreat.Update(0.36f));
    }

    [Fact]
    public void RejectsInvertedThresholds()
    {
        Assert.Throws<ArgumentException>(() => new BelowHysteresis(0.6f, 0.35f));
    }
}

public class ModeArbiterTests
{
    [Fact]
    public void HighestPriorityModeOwnsTheMotor()
    {
        var arbiter = new ModeArbiter(quietSeconds: 1.0);
        var engaged = arbiter.Update(new[] { ReflexMode.SelfDefense }, 0.0);
        Assert.Equal(TransitionKind.Engaged, engaged.Kind);
        Assert.Equal(ReflexMode.SelfDefense, arbiter.Owner);

        var switched = arbiter.Update(new[] { ReflexMode.SelfDefense, ReflexMode.SelfPreservation }, 0.1);
        Assert.Equal(TransitionKind.Switched, switched.Kind);
        Assert.Equal(ReflexMode.SelfDefense, switched.From);
        Assert.Equal(ReflexMode.SelfPreservation, switched.To);

        Assert.Equal(TransitionKind.None, arbiter.Update(new[] { ReflexMode.SelfPreservation }, 0.2).Kind);
    }

    [Fact]
    public void ReleasesOnlyAfterQuietPeriod()
    {
        var arbiter = new ModeArbiter(quietSeconds: 1.0);
        arbiter.Update(new[] { ReflexMode.SelfDefense }, 0.0);
        Assert.Equal(TransitionKind.None, arbiter.Update(Array.Empty<ReflexMode>(), 5.0).Kind);
        Assert.Equal(TransitionKind.None, arbiter.Update(Array.Empty<ReflexMode>(), 5.9).Kind);
        Assert.Equal(ReflexMode.SelfDefense, arbiter.Owner);

        var released = arbiter.Update(Array.Empty<ReflexMode>(), 6.0);
        Assert.Equal(TransitionKind.Released, released.Kind);
        Assert.Equal(ReflexMode.SelfDefense, released.From);
        Assert.Null(arbiter.Owner);
    }

    [Fact]
    public void ReactivationDuringQuietKeepsOwnershipWithoutNewEngage()
    {
        var arbiter = new ModeArbiter(quietSeconds: 1.0);
        arbiter.Update(new[] { ReflexMode.SelfDefense }, 0.0);
        arbiter.Update(Array.Empty<ReflexMode>(), 1.0);
        Assert.Equal(TransitionKind.None, arbiter.Update(new[] { ReflexMode.SelfDefense }, 1.5).Kind);
        Assert.Equal(TransitionKind.None, arbiter.Update(Array.Empty<ReflexMode>(), 2.0).Kind);
        Assert.Equal(TransitionKind.Released, arbiter.Update(Array.Empty<ReflexMode>(), 3.0).Kind);
    }
}

public class VersionGateTests
{
    static GameBuild Tested() => new GameBuild
    {
        Game = "1.0.16",
        Network = 40,
        Unity = "6000.0.75f1",
        Sha256 = new Dictionary<string, string> { ["assembly_valheim.dll"] = "aa", ["assembly_utils.dll"] = "bb" },
    };

    [Fact]
    public void PassesOnExactMatch()
    {
        var found = Tested();
        found.Sha256["assembly_valheim.dll"] = "AA";
        var result = VersionGate.Evaluate(found, new[] { Tested() }, new Version(5, 4, 23, 5), new Version(5, 4, 23));
        Assert.True(result.Ok, string.Join("; ", result.Problems));
    }

    [Fact]
    public void ReportsEveryMismatch()
    {
        var found = Tested();
        found.Network = 41;
        found.Sha256["assembly_utils.dll"] = "cc";
        found.Sha256.Remove("assembly_valheim.dll");
        var result = VersionGate.Evaluate(found, new[] { Tested() }, new Version(5, 4, 22), new Version(5, 4, 23));
        Assert.False(result.Ok);
        Assert.Equal(4, result.Problems.Count);
    }

    [Fact]
    public void UnknownGameVersionFails()
    {
        var found = Tested();
        found.Game = "1.0.17";
        var result = VersionGate.Evaluate(found, new[] { Tested() }, new Version(5, 4, 23), new Version(5, 4, 23));
        Assert.False(result.Ok);
        Assert.Contains("untested game version 1.0.17", result.Problems);
    }
}

public class ParityTests
{
    [Theory]
    [InlineData(30f, true, 40f, true)]
    [InlineData(30f, false, 40f, false)]
    [InlineData(3.5f, false, 40f, true)]
    [InlineData(45f, true, 40f, false)]
    public void PerceivesOnlyWhatIsVisibleOrRightNextToYou(float distance, bool lineOfSight, float range, bool expected)
    {
        Assert.Equal(expected, Parity.Perceived(distance, lineOfSight, range));
    }

    // EnemyHud(1.0.20 에셋): 보통 생물은 30m 안이면서 최근 60초 안에 조준한 적이 있어야 이름·체력이 보인다.
    // 바로 곁이어도 쳐다보지 않았으면 안 보인다. 보스는 깨어 있을 때 100m 안이면 보인다.
    [Theory]
    [InlineData(3f, false, false, 1e9, false)]
    [InlineData(9f, false, false, 5, true)]
    [InlineData(29f, false, false, 59, true)]
    [InlineData(31f, false, false, 5, false)]
    [InlineData(20f, false, false, 61, false)]
    [InlineData(80f, true, true, 1e9, true)]
    [InlineData(80f, true, false, 1e9, false)]
    [InlineData(80f, true, false, 5, false)]
    public void StatsFollowEnemyHudRules(float distance, bool boss, bool alerted, double sinceHover, bool expected)
    {
        Assert.Equal(expected, Parity.ShowsStats(distance, boss, alerted, sinceHover));
    }
}

public class DamageAttributionTests
{
    [Fact]
    public void OnlyTextsNearOwnRecentHitCount()
    {
        var attribution = new DamageAttribution(windowSeconds: 0.6, radius: 6f);
        Assert.False(attribution.IsOwn(1.0, new System.Numerics.Vector3(0, 0, 1)));

        attribution.RecordOwnHit(10.0, System.Numerics.Vector3.Zero);
        Assert.True(attribution.IsOwn(10.3, new System.Numerics.Vector3(1, 1, 2)));
        Assert.False(attribution.IsOwn(10.7, new System.Numerics.Vector3(1, 1, 2)));
        Assert.False(attribution.IsOwn(10.3, new System.Numerics.Vector3(9, 0, 0)));
        Assert.False(attribution.IsOwn(9.9, new System.Numerics.Vector3(1, 0, 0)));
    }
}

public class StuckDetectorTests
{
    [Fact]
    public void ProgressKeepsItAlive()
    {
        var stuck = new StuckDetector(windowSeconds: 3, minProgress: 0.3f);
        Assert.False(stuck.Update(0, 20f));
        Assert.False(stuck.Update(1, 19f));
        Assert.False(stuck.Update(3.5, 18f));
        Assert.False(stuck.Update(6, 17.5f));
    }

    [Fact]
    public void NoProgressForWindowIsStuck()
    {
        var stuck = new StuckDetector(windowSeconds: 3, minProgress: 0.3f);
        stuck.Update(0, 10f);
        Assert.False(stuck.Update(2.9, 9.9f));
        Assert.True(stuck.Update(3.0, 9.8f));
        stuck.Reset();
        Assert.False(stuck.Update(3.1, 9.8f));
    }
}

public class BallisticsTests
{
    // 게임과 같은 식(고정 스텝, 중력, 속도 제곱 저항)으로 쏴서 대상 지점 근처를 지나는지 본다.
    static float Miss(System.Numerics.Vector3 from, System.Numerics.Vector3 to, System.Numerics.Vector3 targetVelocity, System.Numerics.Vector3 direction, float speed, float gravity, float drag)
    {
        var position = from;
        var velocity = direction * speed;
        var best = float.MaxValue;
        for (var time = 0f; time < 6f; time += 0.02f)
        {
            velocity += -System.Numerics.Vector3.UnitY * (gravity * 0.02f);
            var magnitude = velocity.Length();
            velocity -= velocity / magnitude * (magnitude * magnitude * drag * 0.02f);
            var next = position + velocity * 0.02f;
            // 한 스텝에 1m 가까이 날아가므로 점이 아니라 선분과 대상 사이 거리를 잰다.
            var target = to + targetVelocity * (time + 0.02f);
            var segment = next - position;
            var along = Math.Clamp(System.Numerics.Vector3.Dot(target - position, segment) / segment.LengthSquared(), 0f, 1f);
            best = Math.Min(best, (position + segment * along - target).Length());
            position = next;
        }
        return best;
    }

    [Fact]
    public void WithoutGravityAimsStraightAtTheTarget()
    {
        var from = new System.Numerics.Vector3(0, 1.6f, 0);
        var to = new System.Numerics.Vector3(10, 1.6f, 0);
        var aim = Ballistics.Aim(from, to, System.Numerics.Vector3.Zero, 50f, 0f, 0f, out var flight);
        Assert.InRange(aim.X, 0.999f, 1.001f);
        Assert.InRange(flight, 0.18f, 0.22f);
    }

    [Theory]
    [InlineData(20f, 0f)]
    [InlineData(40f, 3f)]
    [InlineData(35f, -4f)]
    public void ArcsUpToHitAFarTargetUnderGravityAndDrag(float distance, float rise)
    {
        var from = new System.Numerics.Vector3(0, 1.6f, 0);
        var to = new System.Numerics.Vector3(distance * 0.6f, 1.6f + rise, distance * 0.8f);
        var aim = Ballistics.Aim(from, to, System.Numerics.Vector3.Zero, 40f, 9.81f, 0.002f, out _);
        Assert.True(aim.Y > (rise / distance) - 0.05f);
        Assert.True(Miss(from, to, System.Numerics.Vector3.Zero, aim, 40f, 9.81f, 0.002f) < 0.3f);
    }

    [Fact]
    public void LeadsARunningTarget()
    {
        var from = new System.Numerics.Vector3(0, 1.6f, 0);
        var to = new System.Numerics.Vector3(0, 1.0f, 25f);
        var running = new System.Numerics.Vector3(5f, 0, 0);
        var aim = Ballistics.Aim(from, to, running, 40f, 9.81f, 0.002f, out _);
        Assert.True(aim.X > 0.05f);
        Assert.True(Miss(from, to, running, aim, 40f, 9.81f, 0.002f) < 0.4f);
    }
}

public class PathFollowTests
{
    [Fact]
    public void SkipsACornerLeftBehindInsteadOfTurningBack()
    {
        // 몸은 (0,5). 경로 첫 점이 몸 뒤 (0,3)에 있고 다음 점은 앞 (0,20).
        var corners = new[] { new System.Numerics.Vector2(0, 3), new System.Numerics.Vector2(0, 20), new System.Numerics.Vector2(5, 30) };
        Assert.Equal(new System.Numerics.Vector2(0, 20), PathFollow.NextCorner(corners, new System.Numerics.Vector2(0, 5), 1.1f));
    }

    [Fact]
    public void KeepsACornerStillAhead()
    {
        var corners = new[] { new System.Numerics.Vector2(0, 0), new System.Numerics.Vector2(4, 4), new System.Numerics.Vector2(4, 20) };
        Assert.Equal(new System.Numerics.Vector2(4, 4), PathFollow.NextCorner(corners, new System.Numerics.Vector2(0, 1), 1.1f));
        Assert.Null(PathFollow.NextCorner(new[] { new System.Numerics.Vector2(0, 0) }, new System.Numerics.Vector2(0, 0.5f), 1.1f));
    }
}

public class FallsTests
{
    [Fact]
    public void TheNearestCreatureFell()
    {
        var around = new[] { (IsPlayer: false, Distance: 2.5f), (IsPlayer: false, Distance: 0.4f) };
        Assert.Equal(1, Falls.Fallen(false, around, 3f));
    }

    [Fact]
    public void APlayersBodyIsNotACreatureFalling()
    {
        // 리더가 죽은 자리 곁에 보스가 서 있었다.
        var boss = new[] { (IsPlayer: false, Distance: 1.2f) };
        Assert.Equal(-1, Falls.Fallen(true, boss, 3f));
        var leaderAndBoss = new[] { (IsPlayer: true, Distance: 0.1f), (IsPlayer: false, Distance: 1.2f) };
        Assert.Equal(-1, Falls.Fallen(false, leaderAndBoss, 3f));
    }

    [Fact]
    public void NobodyCloseEnoughMeansUnknown()
    {
        Assert.Equal(-1, Falls.Fallen(false, new[] { (IsPlayer: false, Distance: 5f) }, 3f));
    }
}
