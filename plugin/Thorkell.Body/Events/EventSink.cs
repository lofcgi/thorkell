using System.Collections.Generic;
using Newtonsoft.Json.Linq;
using Thorkell.Wire;
using UnityEngine;

namespace Thorkell.Body.Events;

// 게임 훅(메인 스레드)이 쌓고 BodyLink가 매 프레임 비운다. 이벤트는 버리지 않는다.
internal static class EventSink
{
    static readonly Queue<Event> pending = new Queue<Event>();

    public static void Emit(string kind, JObject data)
    {
        pending.Enqueue(new Event { Kind = kind, Tick = Time.frameCount, Data = data });
    }

    public static bool TryTake(out Event message)
    {
        if (pending.Count == 0)
        {
            message = null;
            return false;
        }
        message = pending.Dequeue();
        return true;
    }
}
