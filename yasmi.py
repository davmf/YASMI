# -*- coding: utf-8 -*-

import logging
from typing import Dict, Set, Optional, Callable, Any, Type
from asyncio import Queue, create_task, CancelledError, sleep, Task


"""Events could be any type but ints are simple.
"""
Event = str

"""For each event subscribed to, stores a set of the event queues to which the event is to be added
when it is published.
"""
_event_subscribers: Dict[Event, Set[Queue[Event]]] = {}


def subscribe_to(events: Set[Event], event_queue: Queue[Event]) -> None:
    """Allows subscription to a set of events.

    Allows subscription to a set of events and supply of the event queue to add events when they
    occur.

    Args:
        events:
            set of events to subscribe to
        event_queue:
            event queue for incoming events to be added to
    """
    for event in events:
        if event not in _event_subscribers:
            _event_subscribers[event] = set()
        _event_subscribers[event].add(event_queue)


def publish(event: Event) -> None:
    """Adds an event to the queue of each subscriber.

    Args:
        event:
            the event to add
    """
    print(f"Publish {event}")

    for event_queue in _event_subscribers[event]:
        event_queue.put_nowait(event)


class State:

    """Base class for creating a state.  Intended to be derived from.

    Class Attributes:
        active_states:
            - for tracking the currently active states
            - for diagnostic purposes only - no other useful function

    Attributes:
        has_history:
            - applicable for composite states only
            - whether this has a history entry point rather than just a straight initial state
            - a history entry point applies when the previous transition _from_ the composite state
              occurred from a sub-state other than the final state - the next transition _to_ the
              composite state will resume in the last sub-state that was previously active, rather
              than the _initial_ state
            - this attributes is set on initialisation and does not change thereafter
        initial:
            - applicable for composite states only
            - the initial state to become active when transitioning normally _to_ this composite
              state
            - this attributes is set on initialisation and does not change thereafter
        final:
            - applicable for composite states only
            - the final state to become active when transitioning normally _from_ this composite
              state
            - this attributes is set on initialisation and does not change thereafter
        is_final:
            - whether this state is a final state
            - final states don't execute a `do` method and cannot be history states
            - this attributes is set on initialisation and does not change thereafter
        state:
            - tracks the active substate if this is a composite state
            - otherwise `None` for a simple state
        do_task:
            - stores the task created from the `do` coroutine if one exists
        manage_task:
            - stores the task created from the `manage` coroutine if one exists (composite state
              only)
        history_state:
            - stores the entry state for a composite state with history enabled
        event_queue:
            - the queue for this state to store incoming events
        name:
            - the name of the derived class - for diagnostic use
    """
    # for tracking active states
    _active_states: Set[Type["State"]] = set()

    def __init__(
        self,
        is_final: bool = False
    ) -> None:
        """Creates the basis of a new state.  Intended to be called from the derived class init.

        Args:
            history:
                initialises the `history` attribute - default = None (simple state)
            initial:
                initialises the `initial` attribute - default = None (simple state)
            final:
                initialises the `final` attribute - default = None (simple state)
            is_final:
                initialises the `is final` attribute - default = False
        """
        self.is_final = is_final
        self.task: Optional[Task[Any]] = None
        self.name = type(self).__name__

    async def transition_to(
        self,
        new_state: "State",
        action: Optional[Callable[..., Any]] = None
    ) -> "State":
        """Manages a transition from this state to another, with an optional action.

        Args:
            new_state:
                state to transition to
            action:
                optional function to provide an action to be executed after exiting this state
                before entering the next state

        Returns:
            the state being transition to as a convenience to the caller
        """
        if self.task:
            self.task.cancel()

            try:
                await self.task
            except CancelledError:
                pass

        if action:
            action()

        new_state.run()

        return new_state

    def run(self) -> None:
        self.task = create_task(self._run())

    async def _run(self) -> None:
        State._active_states.add(type(self))
        print(f"\tEnter {self.name}")
        self.enter()

        # do
        try:
            while True:
                await self.do()
                await sleep(0)
        except CancelledError:
            print(f"\tExit {self.name}")
            self.exit()
            State._active_states.remove(type(self))
            raise

    def enter(self) -> None:
        pass

    async def do(self) -> None:
        pass

    def exit(self) -> None:
        pass

    @staticmethod
    def active_states() -> Set[Type["State"]]:
        return {state for state in State._active_states}


class Machine(State):

    def __init__(
        self,
        initial: State,
        final: Optional[State] = None,
        has_history: bool = False,
    ) -> None:
        """Creates the basis of a new state.  Intended to be called from the derived class init.

        Args:
            history:
                initialises the `history` attribute - default = None (simple state)
            initial:
                initialises the `initial` attribute - default = None (simple state)
            final:
                initialises the `final` attribute - default = None (simple state)
        """
        super().__init__()
        self._has_history = has_history
        self._initial: State = initial
        self.final = final
        self.state: State = initial
        self.history_state: Optional[State] = None
        self.event_queue: Queue[Event] = Queue()

    async def transition_to(
        self,
        new_state: State,
        action: Optional[Callable[..., Any]] = None
    ) -> State:
        """Manages a transition from this state to another, with an optional action.

        Args:
            new_state:
                state to transition to
            action:
                optional function to provide an action to be executed after exiting this state
                before entering the next state

        Returns:
            the state being transition to as a convenience to the caller
        """

        if self._has_history:            
            self.history_state = self.state if not self.state.is_final else None

        if self.state.task:
            self.state.task.cancel()

            try:
                await self.state.task
            except CancelledError:
                pass

        new_state = await super().transition_to(new_state, action)
        return new_state

    async def _run(self) -> None:
        self._clear_event_queue()
        print(f"Enter {type(self).__name__}")
        self.enter()
        self.manage_task = create_task(self.manage())

        # do
        try:
            while True:
                await self.do()
                await sleep(0)
        except CancelledError:
            self.manage_task.cancel()

            try:
                await self.manage_task
            except CancelledError:
                self.exit()
                print(f"Exit {type(self).__name__}")
                self.state = self._initial
                raise

    async def manage(self) -> None:
        try:
            while True:
                await sleep(0)

        except CancelledError:
            raise

    def _clear_event_queue(self) -> None:
        while not self.event_queue.empty():
            _ = self.event_queue.get_nowait()


