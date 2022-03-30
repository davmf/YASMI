import state_machine_1 as sm
from asyncio import create_task, sleep, run, CancelledError
from yasmi import State, publish


DELAY = 0.1

async def main():
    state_machine = sm.StateMachine()
    manage_task = create_task(state_machine.manage())

    await sleep(DELAY)
    print(State.active_states())
    assert State.active_states() == {sm.StateMachineA, sm.StateAA}

    publish(sm.Events.EV0)
    await sleep(DELAY)
    assert State.active_states() == {sm.StateMachineB, sm.StateBA}

    publish(sm.Events.EV1)
    await sleep(DELAY)
    assert State.active_states() == {sm.StateMachineA, sm.StateAB}

    publish(sm.Events.EV1)
    await sleep(DELAY)
    assert State.active_states() == {sm.StateMachineB, sm.StateBA}

    publish(sm.Events.EV3)
    await sleep(DELAY)
    assert State.active_states() == {sm.StateMachineB, sm.StateBB}

    publish(sm.Events.EV1)
    await sleep(DELAY)
    assert State.active_states() == {sm.StateMachineA, sm.StateAB}

    publish(sm.Events.EV0)
    await sleep(DELAY)
    assert State.active_states() == {sm.StateMachineB, sm.StateBB}

    publish(sm.Events.EV3)
    await sleep(DELAY)
    assert State.active_states() == {sm.StateMachineA, sm.StateAB}

    publish(sm.Events.EV0)
    await sleep(DELAY)
    assert State.active_states() == {sm.StateMachineB, sm.StateBA}

    publish(sm.Events.EV1)
    await sleep(DELAY)
    assert State.active_states() == {sm.StateMachineA, sm.StateAB}

    manage_task.cancel()

    try:
        await manage_task
    except CancelledError:
        pass


run(main())