import logging
from typing import cast
from asyncio import CancelledError

from yasmi import Event, subscribe_to, publish, State, Machine



class Events:
    EV0: Event = cast(Event, 0)
    EV1: Event = cast(Event, 1)
    EV2: Event = cast(Event, 2)
    EV3: Event = cast(Event, 3)
    EV4: Event = cast(Event, 4)
    EVAF: Event = cast(Event, 5)
    EVBF: Event = cast(Event, 6)
    LAST: Event = EVBF


class StateMachine(Machine):

    """Top-level state machine as shown in `state_machine.puml`.
    """

    def __init__(self) -> None:
        super().__init__(initial=StateMachine_i())
        self.state_machine_A: State = StateMachineA()
        self.state_machine_B: State = StateMachineB()

        subscribe_to(
            {Events.EV0, Events.EV1, Events.EVAF, Events.EVBF},
            self.event_queue
        )

    async def manage(self):
        self.state = await self.state.transition_to(self.state_machine_A)

        try:
            while True:
                event: Event = await self.event_queue.get()

                if self.state == self.state_machine_A:
                    if (event == Events.EV0 and self.guard()) or event == Events.EVAF:
                        self.state = await self.state.transition_to(
                            self.state_machine_B, self.action
                        )
                elif self.state == self.state_machine_B:
                    if (event == Events.EV1 and self.guard()) or event == Events.EVBF:
                        self.state = await self.state.transition_to(
                            self.state_machine_A, self.action
                        )

        except CancelledError:
            raise


class StateMachineA(Machine):

    x = 0

    def __init__(self):
        super().__init__(initial=StateMachineA_i(), final=StateMachineA_f())
        self.state_AA: State = StateAA()
        self.state_AB: State = StateAB()
        subscribe_to({Events.EV1, Events.EV2}, self.event_queue)

    async def manage(self):
        destination: State = (
            self.history_state if self.history_state
            else self.state_AA if StateMachineA.x == 0 else self.state_AB
        )
        self.state = await self.state.transition_to(destination)

        try:
            while True:
                event: Event = await self.event_queue.get()

                if self.state == self.state_AA:
                    if event == Events.EV1:
                        self.state = await self.state.transition_to(self.state_AB, self.action)
                elif self.state == self.state_AB:
                    if event == Events.EV1:
                        self.state = await self.state.transition_to(self.final, self.action)
                    elif event == Events.EV2:
                        self.state = await self.state.transition_to(self.state_AA, self.action)

        except CancelledError:
            pass


class StateMachineB(Machine):

    def __init__(self):
        super().__init__(initial=StateMachineB_i(), final=StateMachineB_f(), history=True)
        self.state_A: State = StateBA()
        self.state_B: State = StateBB()
        subscribe_to({Events.EV3, Events.EV4}, self.event_queue)

    async def manage(self):
        log.debug("manage %s", self.name)

        if self.state and self.final:
            destination: State = self.history_state if self.history_state else self.state_A
            self.state = await self.state.transition_to(destination)

            try:
                while True:
                    event: Event = await self.event_queue.get()

                    if self.state == self.state_A:
                        if event == Events.EV3:
                            self.state = await self.state.transition_to(self.state_B, self.action)
                        elif event == Events.EV4:
                            self.state = await self.state.transition_to(self.final, self.action)
                    elif self.state == self.state_B:
                        if event == Events.EV3:
                            self.state = await self.state.transition_to(self.final, self.action)

            except CancelledError:
                pass


class StateMachine_i(State):

    def __init__(self):
        super().__init__()


class StateMachineA_i(State):

    def __init__(self):
        super().__init__()


class StateMachineB_i(State):

    def __init__(self):
        super().__init__()


class StateMachineA_f(State):

    def __init__(self):
        super().__init__(is_final=True)

    def enter(self) -> None:
        super().enter()
        publish(Events.EVAF)


class StateMachineB_f(State):

    def __init__(self):
        super().__init__(is_final=True)

    def enter(self) -> None:
        super().enter()
        publish(Events.EVBF)


class StateAA(State):

    def enter(self) -> None:
        super().enter()
        StateMachineA.x += 1


class StateAB(State):
    pass


class StateBA(State):
    pass


class StateBB(State):
    pass
