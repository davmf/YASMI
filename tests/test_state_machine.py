
import unittest
from asyncio import CancelledError, create_task, sleep

import state_machine_1 as sm
from yasmi import State, publish

DELAY = 0.1


class TestStateMachine(unittest.IsolatedAsyncioTestCase):

    async def test_state_machine_sequence_A(self):
        state_machine = sm.StateMachine()
        manage_task = create_task(state_machine.manage())

        await sleep(DELAY)
        self.assertEqual(State.active_states(), {sm.StateMachineA, sm.StateAA})

        publish(sm.Events.EV0)
        await sleep(DELAY)
        self.assertEqual(State.active_states(), {sm.StateMachineB, sm.StateBA})

        publish(sm.Events.EV1)
        await sleep(DELAY)
        self.assertEqual(State.active_states(), {sm.StateMachineA, sm.StateAB})

        publish(sm.Events.EV1)
        await sleep(DELAY)
        self.assertEqual(State.active_states(), {sm.StateMachineB, sm.StateBA})

        publish(sm.Events.EV3)
        await sleep(DELAY)
        self.assertEqual(State.active_states(), {sm.StateMachineB, sm.StateBB})

        publish(sm.Events.EV1)
        await sleep(DELAY)
        self.assertEqual(State.active_states(), {sm.StateMachineA, sm.StateAB})

        publish(sm.Events.EV0)
        await sleep(DELAY)
        self.assertEqual(State.active_states(), {sm.StateMachineB, sm.StateBB})

        publish(sm.Events.EV3)
        await sleep(DELAY)
        self.assertEqual(State.active_states(), {sm.StateMachineA, sm.StateAB})

        publish(sm.Events.EV0)
        await sleep(DELAY)
        self.assertEqual(State.active_states(), {sm.StateMachineB, sm.StateBA})

        publish(sm.Events.EV1)
        await sleep(DELAY)
        self.assertEqual(State.active_states(), {sm.StateMachineA, sm.StateAB})

        manage_task.cancel()

        try:
            await manage_task
        except CancelledError:
            pass


if __name__ == "__main__":
    unittest.main()
