from dataclasses import dataclass


@dataclass
class AsyncSwapStateMachine:
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
    cancelled: bool = False

    @classmethod
    def open_order(
        cls,
        original_input: int,
        original_output: int,
        *,
        initial_protocol_fee: int = 0,
        remaining_input: int | None = None,
    ) -> "AsyncSwapStateMachine":
        if original_input <= 0:
            raise ValueError("original_input must be positive")
        if original_output < 0:
            raise ValueError("original_output must be non-negative")
        if initial_protocol_fee < 0:
            raise ValueError("initial_protocol_fee must be non-negative")

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
        )

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
        if output_amount <= 0:
            raise ValueError("output_amount must be positive")
        if output_amount > self.remaining_output:
            raise ValueError("output_amount exceeds remaining_output")
        if gross_input_slice <= 0:
            raise ValueError("gross_input_slice must be positive")

        charged_input = filler_payout + protocol_fee + protocol_surplus
        if gross_input_slice != charged_input + user_rebate:
            raise ValueError(
                "gross_input_slice must equal filler + fee + surplus + user_rebate"
            )
        if charged_input > self.remaining_input:
            raise ValueError("charged_input exceeds remaining_input")

        self.remaining_input -= charged_input
        self.remaining_output -= output_amount
        self.filler_payout_total += filler_payout
        self.protocol_fee_total += protocol_fee
        self.protocol_surplus_total += protocol_surplus
        self.delivered_output_total += output_amount
        self.user_rebate_total += user_rebate

    def cancel(self) -> int:
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
        # User rebate must remain recoverable inside the remaining input or already refunded.
        assert (
            self.user_rebate_total <= self.remaining_input + self.refunded_input_total
        )

    def assert_state(self) -> None:
        assert self.remaining_input >= 0
        assert self.remaining_output >= 0
        self.assert_conservation()
        self.assert_user_protection()
