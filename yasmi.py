# -*- coding: utf-8 -*-

import logging
from typing import Dict, Set, Optional, Callable, Any, Type
from asyncio import Queue, create_task, CancelledError, sleep


"""Events could be any type but ints are simple.
"""
Event = int

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
    logging.debug("Publish event %s", event)

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
        self.do_task = None
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
        await self.exit()

        if action:
            action()

        new_state.enter()

        if not new_state.is_final:
            new_state.do()

        return new_state

    def enter(self) -> None:
        """Called when the state is entered.

        Called when the state is entered and performs:
          - adding to the list of active states
          - clearing of the event queue so only new events get processed

        Intended to be called by and supplemented with subclass entry behaviour if relevant - for
        actions to be performed by the subclassed state on entry.
        """
        State._active_states.add(type(self))

    def exit_(self) -> None:
        """Called when the state is exited, by the `exit` task.

        Called when the state is exited and performs:
          - resetting to the initial state

        Intended to be called by and supplemented with subclass exit behaviour if relevant - for
        actions to be performed by the subclassed state on exit.
        """
        pass

    async def exit(self) -> None:
        """Coroutine to create a task to manage state exit.

        Manages state exit as follows:
          - cancels the `do` task (which in turn cancels the `manage` task)
          - call the exit method
        """
        if self.do_task:
            self.do_task.cancel()

            try:
                await self.do_task
            except CancelledError:
                pass

        self.exit_()

        if self in State._active_states:
            State._active_states.remove(type(self))

    # default guard
    def guard(self) -> bool:
        return True

    # default action
    def action(self) -> None:
        pass

    async def _do(self) -> None:
        while True:
            await sleep(0)

    def do(self) -> None:
        self.do_task = create_task(self._do())

    @staticmethod
    def active_states() -> Set[Type["State"]]:
        return {state for state in State._active_states}



class Machine(State):

    def __init__(
        self,
        initial: State,
        final: Optional[State] = None,
        history: Optional[bool] = None,
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
        super().__init__()
        self.has_history = history
        self.initial: State = initial
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

        self.history_state = (
            self.state if self.has_history and not self.state.is_final else None
        )

        await self.state.exit()
        await super().transition_to(new_state, action)
        return new_state

    async def _do(self) -> None:
        self.manage_task = create_task(self.manage())

        try:
            await self.manage_task
        except CancelledError:
            self.manage_task.cancel()

            try:
                await self.manage_task
            except CancelledError:
                raise

    def exit_(self) -> None:
        """Called when the state is exited, by the `exit` task.

        Called when the state is exited and performs:
          - resetting to the initial state

        Intended to be called by and supplemented with subclass exit behaviour if relevant - for
        actions to be performed by the subclassed state on exit.
        """
        super().exit_()

        if self.initial:
            self.state = self.initial

    def do(self) -> None:
        self.do_task = create_task(self._do())

    async def manage(self) -> None:
        try:
            while True:
                await sleep(0)

        except CancelledError:
            raise

    async def exit(self) -> None:
        await super().exit()
        self.exit_()

    def _clear_event_queue(self) -> None:
        while not self.event_queue.empty():
            _ = self.event_queue.get_nowait()


