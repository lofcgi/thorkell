using System;
using System.Reflection;
using HarmonyLib;
using Newtonsoft.Json.Linq;
using UnityEngine;

namespace Thorkell.Body.Perception;

// 토르켈 자신의 화면. 사람이 모니터로 보듯 게임 카메라가 그리는 장면을 찍어 두뇌가 이해하게 한다
// (2026-10-18 사용자 결정: 장면 이해는 픽셀 비전으로. 포탈·집 입구·리더의 소환수를 물체 목록으로는 몰랐다).
// 머리 위 이름표·체력바 같은 화면 UI는 따로 그리는 층이라 담기지 않는다. 그 정보는 장면(scene)에 이미 있다.
// 사람은 카메라를 돌려 둘러보고, 궁금한 쪽으로 화면을 돌린다. turn(지금 화면에서 좌우로 몇 도)이나
// toward(그 지점 쪽)로 그만큼 돌린 화면을 찍는다. 찍는 동안만 돌리고 바로 되돌린다(몸은 그대로다).
internal static class Sight
{
    static readonly MethodInfo SetMotionBlur = AccessTools.Method(typeof(CameraEffects), "SetMotionBlur")
        ?? throw new MissingMethodException("CameraEffects", "SetMotionBlur");

    public static JObject Look(JObject args)
    {
        var width = Int(args, "width", 640);
        var height = Int(args, "height", 360);
        var quality = Int(args, "quality", 70);
        var camera = GameCamera.instance != null ? GameCamera.instance.GetComponent<Camera>() : Camera.main;
        if (camera == null)
            throw new InvalidOperationException("no_camera");
        // 봇 화면은 사람이 보지 않는다. 모션 블러는 돌려 찍은 화면을 다 번지게 해서 끈다(메모리에서만, 설정 파일은 안 건드림).
        if (CameraEffects.instance != null)
            SetMotionBlur.Invoke(CameraEffects.instance, new object[] { false });
        var started = Time.realtimeSinceStartup;
        var frames = new JArray();
        var original = camera.transform.rotation;
        try
        {
            if (args?["toward"] is JArray toward && toward.Count == 3)
            {
                var point = new Vector3((float)toward[0], (float)toward[1], (float)toward[2]);
                var direction = point - camera.transform.position;
                if (direction.sqrMagnitude > .01f)
                    camera.transform.rotation = Quaternion.LookRotation(direction);
                frames.Add(Frame(camera, width, height, quality));
            }
            else if (args?["turn"] is JArray turns && turns.Count > 0)
            {
                foreach (var turn in turns)
                {
                    camera.transform.rotation = Quaternion.Euler(0, (float)turn, 0) * original;
                    frames.Add(Frame(camera, width, height, quality));
                }
            }
            else
                frames.Add(Frame(camera, width, height, quality));
        }
        finally
        {
            camera.transform.rotation = original;
        }
        return new JObject
        {
            ["frames"] = frames,
            ["width"] = width,
            ["height"] = height,
            ["fov"] = Math.Round(camera.fieldOfView, 1),
            ["ms"] = Math.Round((Time.realtimeSinceStartup - started) * 1000f),
        };
    }

    static JObject Frame(Camera camera, int width, int height, int quality)
    {
        var target = RenderTexture.GetTemporary(width, height, 24);
        var previous = camera.targetTexture;
        var active = RenderTexture.active;
        Texture2D texture = null;
        try
        {
            camera.targetTexture = target;
            camera.Render();
            RenderTexture.active = target;
            texture = new Texture2D(width, height, TextureFormat.RGB24, false);
            texture.ReadPixels(new Rect(0, 0, width, height), 0, 0);
            texture.Apply();
            var forward = camera.transform.forward;
            return new JObject
            {
                ["jpeg"] = Convert.ToBase64String(texture.EncodeToJPG(quality)),
                // 화면이 향한 방위(북 0°, 동 90°)와 위아래(+면 아래를 봄).
                ["yaw"] = Math.Round(Mathf.Atan2(forward.x, forward.z) * Mathf.Rad2Deg, 1),
                ["pitch"] = Math.Round(-Mathf.Asin(forward.y) * Mathf.Rad2Deg, 1),
            };
        }
        finally
        {
            camera.targetTexture = previous;
            RenderTexture.active = active;
            RenderTexture.ReleaseTemporary(target);
            if (texture != null)
                UnityEngine.Object.Destroy(texture);
        }
    }

    static int Int(JObject args, string key, int fallback) =>
        args?[key]?.Type == JTokenType.Integer ? (int)args[key] : fallback;
}
