from dataclasses import dataclass


@dataclass
class AsyncSwapStateMachine:
    """State machine model for AsyncSwap V1.

    Models the lifecycle of an async order: open, fill (partial/full), cancel.
    Tracks value conservation, user rebate recoverability, and expiry semantics.
    """

    original_input: int
    original_output: int
    remaining_input: int
    remaining_output: int
    protocol_fee_total: int = 0
    protocol_surplus_total: int = 0
    filler_payout_total: int = 0
    refunded_input_total: int = 0
    delivered_output_total: int = 0
    cancelled_output_total: int = 0
    user_rebate_total: int = 0
    user_rebate_returned: int = 0
    cancelled: bool = False
    deadline: int = 0
    current_time: int = 0

    @classmethod
    def open_order(
        cls,
        original_input: int,
        original_output: int,
        *,
        initial_protocol_fee: int = 0,
        remaining_input: int | None = None,
        deadline: int = 0,
        current_time: int = 0,
    ) -> "AsyncSwapStateMachine":
        if original_input <= 0:
            raise ValueError("original_input must be positive")
        if original_output < 0:
            raise ValueError("original_output must be non-negative")
        if initial_protocol_fee < 0:
            raise ValueError("initial_protocol_fee must be non-negative")
        if deadline != 0 and deadline <= current_time:
            raise ValueError("deadline must be in the future or zero")

        if remaining_input is None:
            remaining_input = original_input - initial_protocol_fee
        if remaining_input < 0:
            raise ValueError("remaining_input cannot be negative")

        return cls(
            original_input=original_input,
            original_output=original_output,
            remaining_input=remaining_input,
            remaining_output=original_output,
            protocol_fee_total=initial_protocol_fee,
            deadline=deadline,
            current_time=current_time,
        )

    def warp(self, timestamp: int) -> None:
        self.current_time = timestamp

    def is_expired(self) -> bool:
        return self.deadline != 0 and self.current_time > self.deadline

    def fill(
        self,
        *,
        output_amount: int,
        gross_input_slice: int,
        filler_payout: int,
        protocol_fee: int = 0,
        protocol_surplus: int = 0,
        user_rebate: int = 0,
    ) -> None:
        if self.cancelled:
            raise ValueError("order already cancelled")
        if self.is_expired():
            raise ValueError("order expired")
        if output_amount <= 0:
            raise ValueError("output_amount must be positive")
        if output_amount > self.remaining_output:
            raise ValueError("output_amount exceeds remaining_output")
        if gross_input_slice <= 0:
            raise ValueError("gross_input_slice must be positive")

        # Minimum fill: at least 50% of remaining
        min_fill = (self.remaining_output + 1) // 2
        if output_amount < min_fill:
            raise ValueError("output_amount below minimum fill threshold")

        charged_input = filler_payout + protocol_fee + protocol_surplus
        if gross_input_slice != charged_input + user_rebate:
            raise ValueError(
                "gross_input_slice must equal filler + fee + surplus + user_rebate"
            )
        if charged_input > self.remaining_input:
            raise ValueError("charged_input exceeds remaining_input")

        is_full_fill = output_amount == self.remaining_output

        self.remaining_input -= charged_input
        self.remaining_output -= output_amount
        self.filler_payout_total += filler_payout
        self.protocol_fee_total += protocol_fee
        self.protocol_surplus_total += protocol_surplus
        self.delivered_output_total += output_amount
        self.user_rebate_total += user_rebate

        # On full fill, user rebate is returned directly instead of staying in remaining_input
        if is_full_fill and user_rebate > 0:
            self.user_rebate_returned += user_rebate

    def cancel(self, caller: str = "swapper", swapper: str = "swapper") -> int:
        if caller != swapper and not self.is_expired():
            raise ValueError("only swapper can cancel before expiry")

        refund = self.remaining_input
        self.refunded_input_total += refund
        self.cancelled_output_total += self.remaining_output
        self.remaining_input = 0
        self.remaining_output = 0
        self.cancelled = True
        return refund

    def assert_conservation(self) -> None:
        assert (
            self.original_input
            == self.remaining_input
            + self.refunded_input_total
            + self.filler_payout_total
            + self.protocol_fee_total
            + self.protocol_surplus_total
        )
        assert (
            self.original_output
            == self.remaining_output
            + self.delivered_output_total
            + self.cancelled_output_total
        )

    def assert_user_protection(self) -> None:
        # User rebate must remain recoverable:
        # either still in remaining_input, already refunded, or already returned on full fill.
        assert (
            self.user_rebate_total
            <= self.remaining_input
            + self.refunded_input_total
            + self.user_rebate_returned
        )

    def assert_state(self) -> None:
        assert self.remaining_input >= 0
        assert self.remaining_output >= 0
        self.assert_conservation()
        self.assert_user_protection()
