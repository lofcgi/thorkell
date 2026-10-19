using System;
using System.Numerics;

namespace Thorkell.Core;

// 화살 조준. 게임의 투사체는 고정 스텝마다 중력만큼 아래로, 속도 제곱에 비례한 공기저항만큼 느려진다(Projectile.FixedUpdate).
// 같은 식으로 궤적을 따라가며 대상 높이에 닿는 낮은 쏘아 올림 각을 이분법으로 찾고, 움직이는 대상은 날아가는 동안 갈 자리를 겨눈다.
public static class Ballistics
{
    const float MinPitch = -1.0f;   // 약 -57도
    const float MaxPitch = 0.785f;  // 45도: 그보다 높으면 같은 거리를 더 높은 궤적으로 맞히는 쪽이라 쓰지 않는다
    const float MaxFlight = 6f;

    public static Vector3 Aim(Vector3 from, Vector3 target, Vector3 targetVelocity, float speed, float gravity, float drag, out float flightSeconds, float step = 0.02f)
    {
        if (speed <= 0 || step <= 0)
            throw new ArgumentException("speed and step must be positive");
        var aimPoint = target;
        var direction = Vector3.Normalize(target - from);
        flightSeconds = 0f;
        for (var i = 0; i < 4; i++)
        {
            direction = Launch(from, aimPoint, speed, gravity, drag, step, out flightSeconds);
            aimPoint = target + targetVelocity * flightSeconds;
        }
        return direction;
    }

    static Vector3 Launch(Vector3 from, Vector3 to, float speed, float gravity, float drag, float step, out float flight)
    {
        var flat = new Vector3(to.X - from.X, 0, to.Z - from.Z);
        var distance = flat.Length();
        var heading = distance > 1e-4f ? flat / distance : Vector3.UnitZ;
        var rise = to.Y - from.Y;
        if (distance < 1e-3f)
        {
            flight = 0f;
            return rise >= 0 ? Vector3.UnitY : -Vector3.UnitY;
        }
        float low = MinPitch, high = MaxPitch, pitch = (low + high) / 2;
        flight = 0f;
        for (var i = 0; i < 24; i++)
        {
            pitch = (low + high) / 2;
            var height = HeightAt(heading, pitch, distance, speed, gravity, drag, step, out flight);
            if (float.IsNaN(height) || height < rise)
                low = pitch;
            else
                high = pitch;
        }
        return heading * (float)Math.Cos(pitch) + Vector3.UnitY * (float)Math.Sin(pitch);
    }

    // 수평 거리 distance에 닿았을 때의 높이. 닿기 전에 떨어지면 NaN.
    static float HeightAt(Vector3 heading, float pitch, float distance, float speed, float gravity, float drag, float step, out float time)
    {
        var velocity = (heading * (float)Math.Cos(pitch) + Vector3.UnitY * (float)Math.Sin(pitch)) * speed;
        var position = Vector3.Zero;
        time = 0f;
        while (time < MaxFlight)
        {
            velocity += -Vector3.UnitY * (gravity * step);
            var magnitude = velocity.Length();
            if (magnitude > 1e-4f)
                velocity -= velocity / magnitude * (magnitude * magnitude * drag * step);
            var next = position + velocity * step;
            time += step;
            var travelled = new Vector2(next.X, next.Z).Length();
            if (travelled >= distance)
            {
                var before = new Vector2(position.X, position.Z).Length();
                var t = (distance - before) / Math.Max(1e-5f, travelled - before);
                return position.Y + (next.Y - position.Y) * t;
            }
            position = next;
        }
        return float.NaN;
    }
}
