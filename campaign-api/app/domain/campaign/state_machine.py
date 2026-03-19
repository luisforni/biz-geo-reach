"""Contact state machine: valid states and allowed transitions.

Pattern: State Machine — encapsulates all valid transitions in one place
so no other module can create invalid state changes.
"""

from enum import StrEnum

class ContactState(StrEnum):
    """Lifecycle states for a campaign contact."""

    PENDING = "pending"
    VALIDATING_WHATSAPP = "validating_whatsapp"
    NO_WHATSAPP = "no_whatsapp"
    SENDING_FIRST_MESSAGE = "sending_first_message"
    WAITING_RESPONSE = "waiting_response"
    TIMED_OUT = "timed_out"
    IN_CONVERSATION = "in_conversation"
    SCHEDULED_CALL = "scheduled_call"
    REJECTED = "rejected"
    COMPLETED = "completed"
    ERROR = "error"

TERMINAL_STATES: frozenset[ContactState] = frozenset(
    {
        ContactState.NO_WHATSAPP,
        ContactState.TIMED_OUT,
        ContactState.SCHEDULED_CALL,
        ContactState.REJECTED,
        ContactState.COMPLETED,
        ContactState.ERROR,
    }
)

_TRANSITIONS: dict[ContactState, frozenset[ContactState]] = {
    ContactState.PENDING: frozenset(
        {ContactState.VALIDATING_WHATSAPP}
    ),
    ContactState.VALIDATING_WHATSAPP: frozenset(
        {
            ContactState.PENDING,
            ContactState.NO_WHATSAPP,
            ContactState.SENDING_FIRST_MESSAGE,
            ContactState.ERROR,
        }
    ),
    ContactState.SENDING_FIRST_MESSAGE: frozenset(
        {ContactState.WAITING_RESPONSE, ContactState.ERROR}
    ),
    ContactState.WAITING_RESPONSE: frozenset(
        {
            ContactState.TIMED_OUT,
            ContactState.IN_CONVERSATION,
            ContactState.COMPLETED,
        }
    ),
    ContactState.IN_CONVERSATION: frozenset(
        {
            ContactState.SCHEDULED_CALL,
            ContactState.REJECTED,
            ContactState.IN_CONVERSATION,
            ContactState.ERROR,
        }
    ),
}

class InvalidTransitionError(ValueError):
    """Raised when an attempted state transition is not allowed."""

    def __init__(self, from_state: ContactState, to_state: ContactState) -> None:
        super().__init__(f"Invalid transition: {from_state!r} → {to_state!r}")
        self.from_state = from_state
        self.to_state = to_state

class ContactStateMachine:
    """Validates and applies state transitions for contacts.

    Applying SOLID — Open/Closed Principle: new states can be added
    by extending _TRANSITIONS without modifying this class.
    """

    @staticmethod
    def can_transition(from_state: ContactState, to_state: ContactState) -> bool:
        """Return True if the transition from_state → to_state is valid."""
        if from_state in TERMINAL_STATES:
            return False
        return to_state in _TRANSITIONS.get(from_state, frozenset())

    @staticmethod
    def transition(
        current_state: ContactState, new_state: ContactState
    ) -> ContactState:
        """Return new_state; raise InvalidTransitionError if not allowed."""
        if not ContactStateMachine.can_transition(current_state, new_state):
            raise InvalidTransitionError(current_state, new_state)
        return new_state

    @staticmethod
    def is_terminal(state: ContactState) -> bool:
        """Return True if the state has no further transitions."""
        return state in TERMINAL_STATES
