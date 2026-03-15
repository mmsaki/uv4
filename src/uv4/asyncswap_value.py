from dataclasses import dataclass


WAD = 10**18


@dataclass(frozen=True)
class TokenMeta:
    symbol: str
    decimals: int


@dataclass(frozen=True)
class TokenQuote:
    price_usd_x18: int
    updated_at: int


@dataclass(frozen=True)
class SurplusSplit:
    user_bps: int
    filler_bps: int
    protocol_bps: int

    def __post_init__(self) -> None:
        if self.user_bps + self.filler_bps + self.protocol_bps != 10_000:
            raise ValueError("split must sum to 10000 bps")


@dataclass(frozen=True)
class ValueCapturePreview:
    active: bool
    claim_share: int
    fair_claim_share: int
    surplus_input: int
    user_share_input: int
    filler_share_input: int
    protocol_share_input: int
    input_value_usd_x18: int
    output_value_usd_x18: int
    loss_bps: int
    disadvantaged: str = "none"  # "user", "filler", or "none"


class AsyncSwapUsdOracleModel:
    def __init__(
        self, max_age_seconds: int = 300, split: SurplusSplit | None = None
    ) -> None:
        self.max_age_seconds = max_age_seconds
        self.split = split or SurplusSplit(5000, 2500, 2500)
        self.tokens: dict[str, TokenMeta] = {}
        self.quotes: dict[str, TokenQuote] = {}
        self.current_time = 0

    def warp(self, timestamp: int) -> None:
        self.current_time = timestamp

    def register_token(self, symbol: str, decimals: int) -> None:
        self.tokens[symbol] = TokenMeta(symbol=symbol, decimals=decimals)

    def set_quote(
        self, symbol: str, price_usd_x18: int, updated_at: int | None = None
    ) -> None:
        self.quotes[symbol] = TokenQuote(
            price_usd_x18=price_usd_x18,
            updated_at=self.current_time if updated_at is None else updated_at,
        )

    def value_usd_x18(self, token: str, amount: int) -> int:
        meta = self.tokens[token]
        quote = self.quotes[token]
        return amount * quote.price_usd_x18 // (10**meta.decimals)

    def amount_from_usd_x18(self, token: str, usd_value_x18: int) -> int:
        meta = self.tokens[token]
        quote = self.quotes[token]
        return usd_value_x18 * (10**meta.decimals) // quote.price_usd_x18

    def preview_fill(
        self,
        input_token: str,
        output_token: str,
        claim_share: int,
        output_amount: int,
    ) -> ValueCapturePreview:
        if input_token not in self.tokens or output_token not in self.tokens:
            raise ValueError("unknown token")

        input_quote = self.quotes.get(input_token)
        output_quote = self.quotes.get(output_token)
        if input_quote is None or output_quote is None:
            return ValueCapturePreview(
                active=False,
                claim_share=claim_share,
                fair_claim_share=claim_share,
                surplus_input=0,
                user_share_input=0,
                filler_share_input=claim_share,
                protocol_share_input=0,
                input_value_usd_x18=0,
                output_value_usd_x18=0,
                loss_bps=0,
            )

        if self.current_time - input_quote.updated_at > self.max_age_seconds:
            return ValueCapturePreview(
                active=False,
                claim_share=claim_share,
                fair_claim_share=claim_share,
                surplus_input=0,
                user_share_input=0,
                filler_share_input=claim_share,
                protocol_share_input=0,
                input_value_usd_x18=0,
                output_value_usd_x18=0,
                loss_bps=0,
            )
        if self.current_time - output_quote.updated_at > self.max_age_seconds:
            return ValueCapturePreview(
                active=False,
                claim_share=claim_share,
                fair_claim_share=claim_share,
                surplus_input=0,
                user_share_input=0,
                filler_share_input=claim_share,
                protocol_share_input=0,
                input_value_usd_x18=0,
                output_value_usd_x18=0,
                loss_bps=0,
            )

        input_value = self.value_usd_x18(input_token, claim_share)
        output_value = self.value_usd_x18(output_token, output_amount)
        fair_claim = self.amount_from_usd_x18(input_token, output_value)

        if claim_share == fair_claim:
            # Perfectly fair execution
            return ValueCapturePreview(
                active=False,
                claim_share=claim_share,
                fair_claim_share=fair_claim,
                surplus_input=0,
                user_share_input=0,
                filler_share_input=claim_share,
                protocol_share_input=0,
                input_value_usd_x18=input_value,
                output_value_usd_x18=output_value,
                loss_bps=0,
                disadvantaged="none",
            )

        if claim_share > fair_claim:
            # User is disadvantaged (overpaying)
            surplus = claim_share - fair_claim
            user_rebate = surplus * self.split.user_bps // 10_000
            filler_bonus = surplus * self.split.filler_bps // 10_000
            protocol_share = surplus - user_rebate - filler_bonus
            filler_share = fair_claim + filler_bonus
            loss_bps = (
                0
                if input_value == 0
                else (input_value - output_value) * 10_000 // input_value
            )

            return ValueCapturePreview(
                active=True,
                claim_share=claim_share,
                fair_claim_share=fair_claim,
                surplus_input=surplus,
                user_share_input=user_rebate,
                filler_share_input=filler_share,
                protocol_share_input=protocol_share,
                input_value_usd_x18=input_value,
                output_value_usd_x18=output_value,
                loss_bps=loss_bps,
                disadvantaged="user",
            )

        # Filler is disadvantaged (overpaying — user quote is too favorable)
        surplus = fair_claim - claim_share
        filler_rebate = surplus * self.split.filler_bps // 10_000
        user_reduction = surplus * self.split.user_bps // 10_000
        protocol_share = surplus - filler_rebate - user_reduction
        filler_share = claim_share + filler_rebate
        loss_bps = (
            0
            if output_value == 0
            else (output_value - input_value) * 10_000 // output_value
        )

        return ValueCapturePreview(
            active=True,
            claim_share=claim_share,
            fair_claim_share=fair_claim,
            surplus_input=surplus,
            user_share_input=-user_reduction,
            filler_share_input=filler_share,
            protocol_share_input=protocol_share,
            input_value_usd_x18=input_value,
            output_value_usd_x18=output_value,
            loss_bps=loss_bps,
            disadvantaged="filler",
        )
