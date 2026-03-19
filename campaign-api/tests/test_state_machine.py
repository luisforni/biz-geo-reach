"""Unit tests for the contact state machine."""

import pytest

from app.domain.campaign.state_machine import (
    TERMINAL_STATES,
    ContactState,
    ContactStateMachine,
    InvalidTransitionError,
)

def test_valid_transition_pending_to_validating():
    result = ContactStateMachine.transition(
        ContactState.PENDING, ContactState.VALIDATING_WHATSAPP
    )
    assert result == ContactState.VALIDATING_WHATSAPP

def test_valid_transition_validating_to_no_whatsapp():
    result = ContactStateMachine.transition(
        ContactState.VALIDATING_WHATSAPP, ContactState.NO_WHATSAPP
    )
    assert result == ContactState.NO_WHATSAPP

def test_valid_transition_sending_to_waiting():
    result = ContactStateMachine.transition(
        ContactState.SENDING_FIRST_MESSAGE, ContactState.WAITING_RESPONSE
    )
    assert result == ContactState.WAITING_RESPONSE

def test_invalid_transition_raises():
    with pytest.raises(InvalidTransitionError):
        ContactStateMachine.transition(ContactState.PENDING, ContactState.COMPLETED)

def test_invalid_transition_skip_states():
    with pytest.raises(InvalidTransitionError):
        ContactStateMachine.transition(
            ContactState.PENDING, ContactState.WAITING_RESPONSE
        )

def test_terminal_states_block_all_transitions():
    for terminal in TERMINAL_STATES:
        for target in ContactState:
            assert not ContactStateMachine.can_transition(terminal, target), (
                f"Terminal state {terminal!r} should not transition to {target!r}"
            )

def test_is_terminal_for_terminal_states():
    for state in TERMINAL_STATES:
        assert ContactStateMachine.is_terminal(state)

def test_is_not_terminal_for_active_states():
    active = {
        ContactState.PENDING,
        ContactState.VALIDATING_WHATSAPP,
        ContactState.SENDING_FIRST_MESSAGE,
        ContactState.WAITING_RESPONSE,
        ContactState.IN_CONVERSATION,
    }
    for state in active:
        assert not ContactStateMachine.is_terminal(state)

def test_invalid_transition_error_attributes():
    exc = InvalidTransitionError(ContactState.PENDING, ContactState.COMPLETED)
    assert exc.from_state == ContactState.PENDING
    assert exc.to_state == ContactState.COMPLETED
