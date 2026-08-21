import pytest
from app.models.transaction import Transaction

def test_initial_state():
    """Verify default transaction state is CREATED."""
    txn = Transaction(
        id="txn_test001",
        checkout_id="chk_test001",
        customer_id="cust_test001",
        amount=100.0
    )
    assert txn.status == "CREATED"

def test_valid_state_transitions():
    """Verify series of valid state transitions."""
    txn = Transaction(
        id="txn_test001",
        checkout_id="chk_test001",
        customer_id="cust_test001",
        amount=100.0
    )

    # CREATED -> CHECKOUT_INITIATED
    txn.transition_to("CHECKOUT_INITIATED")
    assert txn.status == "CHECKOUT_INITIATED"

    # CHECKOUT_INITIATED -> PAYMENT_ATTEMPTED
    txn.transition_to("PAYMENT_ATTEMPTED")
    assert txn.status == "PAYMENT_ATTEMPTED"

    # PAYMENT_ATTEMPTED -> DIAGNOSING
    txn.transition_to("DIAGNOSING")
    assert txn.status == "DIAGNOSING"

    # DIAGNOSING -> DIAGNOSED
    txn.transition_to("DIAGNOSED")
    assert txn.status == "DIAGNOSED"

    # DIAGNOSED -> ACTION_PROPOSED
    txn.transition_to("ACTION_PROPOSED")
    assert txn.status == "ACTION_PROPOSED"

    # ACTION_PROPOSED -> GUARDRAIL_CHECK
    txn.transition_to("GUARDRAIL_CHECK")
    assert txn.status == "GUARDRAIL_CHECK"

    # GUARDRAIL_CHECK -> APPROVED
    txn.transition_to("APPROVED")
    assert txn.status == "APPROVED"

    # APPROVED -> EXECUTING
    txn.transition_to("EXECUTING")
    assert txn.status == "EXECUTING"

    # EXECUTING -> PAYMENT_ATTEMPTED
    txn.transition_to("PAYMENT_ATTEMPTED")
    assert txn.status == "PAYMENT_ATTEMPTED"

    # PAYMENT_ATTEMPTED -> RETRY_ESCALATE
    txn.transition_to("RETRY_ESCALATE")
    assert txn.status == "RETRY_ESCALATE"

    # RETRY_ESCALATE -> UNRECOVERABLE
    txn.transition_to("UNRECOVERABLE")
    assert txn.status == "UNRECOVERABLE"

def test_invalid_state_transitions():
    """Verify illegal state transitions raise ValueError."""
    txn = Transaction(
        id="txn_test001",
        checkout_id="chk_test001",
        customer_id="cust_test001",
        amount=100.0
    )

    # Direct CREATED -> RECOVERED is invalid
    with pytest.raises(ValueError) as excinfo:
        txn.transition_to("RECOVERED")
    assert "Illegal state transition" in str(excinfo.value)

    # Transition from terminal state is invalid
    txn_terminal = Transaction(
        id="txn_test002",
        checkout_id="chk_test002",
        customer_id="cust_test002",
        amount=100.0,
        status="UNRECOVERABLE"
    )
    with pytest.raises(ValueError) as excinfo:
        txn_terminal.transition_to("CHECKOUT_INITIATED")
    assert "Illegal state transition" in str(excinfo.value)

def test_self_transitions_allowed():
    """Verify transitioning to the same state is permitted."""
    txn = Transaction(
        id="txn_test001",
        checkout_id="chk_test001",
        customer_id="cust_test001",
        amount=100.0
    )
    # CREATED -> CREATED should work fine (updates timestamp)
    old_updated_at = txn.updated_at
    txn.transition_to("CREATED")
    assert txn.status == "CREATED"
    assert txn.updated_at >= old_updated_at
