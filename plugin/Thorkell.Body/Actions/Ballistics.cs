using UnityEngine;

namespace Thorkell.Body.Actions;

internal static class Ballistics
{
    public static Vector3 Aim(Vector3 from, Vector3 target, Vector3 targetVelocity, float speed, float gravity, float drag, out float flight)
    {
        var aim = Thorkell.Core.Ballistics.Aim(N(from), N(target), N(targetVelocity), speed, gravity, drag, out flight, Time.fixedDeltaTime);
        return new Vector3(aim.X, aim.Y, aim.Z);
    }

    static System.Numerics.Vector3 N(Vector3 v) => new System.Numerics.Vector3(v.x, v.y, v.z);
}
