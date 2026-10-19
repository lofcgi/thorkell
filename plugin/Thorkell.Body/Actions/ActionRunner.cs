using System;
using Newtonsoft.Json.Linq;
using Thorkell.Wire;
using UnityEngine;

namespace Thorkell.Body.Actions;

internal sealed class Outcome
{
    public string Status;
    public string Code;
    public JObject Evidence;

    public static Outcome Succeeded(string code, JObject evidence = null) => new Outcome { Status = ResultStatuses.Succeeded, Code = code, Evidence = evidence ?? new JObject() };
    public static Outcome Failed(string code, JObject evidence = null) => new Outcome { Status = ResultStatuses.Failed, Code = code, Evidence = evidence ?? new JObject() };
}

internal interface IAction
{
    string Phase { get; }
    // null이면 계속 진행 중이다.
    Outcome Tick(Player self, float now);
    JObject Progress(Player self);
    void Stop(Player self);
}

// 진행 중 행동 1개, 대기 1개. 명령마다 ack → (progress) → result가 반드시 나간다.
internal sealed class ActionRunner
{
    const float ProgressInterval = 0.5f;

    readonly Action<Message> send;
    Command activeCommand;
    IAction active;
    float activeSince, nextProgress;
    Command queuedCommand;
    IAction queued;

    public ActionRunner(Action<Message> send)
    {
        this.send = send;
    }

    public string ActiveOp => activeCommand?.Op;

    // 반사가 모터를 잡으면 진행 중인 행동은 preempted로 닫는다. 이어서 할지는 두뇌가 정한다.
    public void Preempt(string mode, Player self)
    {
        if (active != null)
            Finish(new Outcome { Status = ResultStatuses.Preempted, Code = mode, Evidence = new JObject() }, self);
    }

    public JObject Describe() =>
        activeCommand == null ? null : new JObject { ["cmd_id"] = activeCommand.Id, ["op"] = activeCommand.Op, ["phase"] = active.Phase };

    public void Submit(Command command, Player self, bool armed, string reflex)
    {
        if (!armed)
        {
            Ack(command, false, "not_armed");
            return;
        }
        IAction action;
        try
        {
            action = Primitives.Create(command.Op, command.Args, self);
        }
        catch (ArgumentException e)
        {
            Ack(command, false, e.Message);
            return;
        }

        // 말하기는 행동 슬롯을 차지하지 않는다: 걸으면서, 나무를 베면서 말할 수 있어야 한다.
        if (Primitives.IsInstant(command.Op))
        {
            Ack(command, true, "ok");
            Result(command, action.Tick(self, Time.time) ?? Outcome.Failed("instant_op_did_not_finish"));
            return;
        }

        // 반사가 몸을 잡고 있으면(맞으며 방어 중, 불 속에서 탈출 중) 움직이는 명령은 진행되지 않는다.
        // 기다리게 두면 두뇌는 응답 없이 시간 초과로 멈췄다. 바로 반사에 밀렸다고 알린다.
        if (reflex != null)
        {
            Ack(command, true, "ok");
            Result(command, new Outcome { Status = ResultStatuses.Preempted, Code = reflex, Evidence = new JObject() });
            return;
        }

        switch (command.Mode)
        {
            case CommandModes.Replace:
                Ack(command, true, "ok");
                if (active != null)
                    Finish(new Outcome { Status = ResultStatuses.Cancelled, Code = "replaced", Evidence = new JObject() }, self);
                Begin(command, action);
                break;
            case CommandModes.Queue:
                Ack(command, true, active == null ? "ok" : "queued");
                if (active == null)
                {
                    Begin(command, action);
                    break;
                }
                if (queued != null)
                    Result(queuedCommand, new Outcome { Status = ResultStatuses.Cancelled, Code = "superseded", Evidence = new JObject() });
                queuedCommand = command;
                queued = action;
                break;
            default:
                Ack(command, false, "unsupported_mode");
                break;
        }
    }

    public void Cancel(string commandId, string reason, Player self)
    {
        if (activeCommand != null && activeCommand.Id == commandId)
            Finish(new Outcome { Status = ResultStatuses.Cancelled, Code = reason, Evidence = new JObject() }, self);
        else if (queuedCommand != null && queuedCommand.Id == commandId)
        {
            Result(queuedCommand, new Outcome { Status = ResultStatuses.Cancelled, Code = reason, Evidence = new JObject() });
            queuedCommand = null;
            queued = null;
        }
    }

    public void StopAll(string reason, Player self)
    {
        if (queuedCommand != null)
            Result(queuedCommand, new Outcome { Status = ResultStatuses.Cancelled, Code = reason, Evidence = new JObject() });
        queuedCommand = null;
        queued = null;
        if (active != null)
            Finish(new Outcome { Status = ResultStatuses.Cancelled, Code = reason, Evidence = new JObject() }, self);
        Motor.Intent.Clear();
    }

    public void Tick(Player self)
    {
        if (active == null)
            return;
        var now = Time.time;
        Outcome outcome;
        try
        {
            outcome = active.Tick(self, now);
        }
        catch (Exception e)
        {
            outcome = Outcome.Failed("exception", new JObject { ["error"] = e.GetType().Name + ": " + e.Message });
        }
        if (outcome != null)
        {
            outcome.Evidence["duration_ms"] = Mathf.RoundToInt((now - activeSince) * 1000);
            Finish(outcome, self);
            return;
        }
        if (now >= nextProgress)
        {
            nextProgress = now + ProgressInterval;
            send(new Progress { CmdId = activeCommand.Id, Metrics = active.Progress(self) });
        }
    }

    void Begin(Command command, IAction action)
    {
        activeCommand = command;
        active = action;
        activeSince = Time.time;
        nextProgress = Time.time + ProgressInterval;
    }

    void Finish(Outcome outcome, Player self)
    {
        active.Stop(self);
        Motor.Intent.Clear();
        Result(activeCommand, outcome);
        activeCommand = null;
        active = null;
        if (queued != null)
        {
            var command = queuedCommand;
            var action = queued;
            queuedCommand = null;
            queued = null;
            Begin(command, action);
        }
    }

    void Ack(Command command, bool accepted, string code) =>
        send(new Ack { CmdId = command.Id, Accepted = accepted, Code = code });

    void Result(Command command, Outcome outcome) =>
        send(new Result { CmdId = command.Id, Status = outcome.Status, Code = outcome.Code, Evidence = outcome.Evidence });
}
