from uv4.asyncswap_value import AsyncSwapUsdOracleModel, SurplusSplit


WAD = 10**18


def test_aave_usdt_bad_quote_shows_user_loss_in_common_usd_unit():
    model = AsyncSwapUsdOracleModel()
    model.register_token("AAVE", 18)
    model.register_token("USDT", 6)
    model.warp(1_000)
    model.set_quote("AAVE", 110 * WAD)
    model.set_quote("USDT", 1 * WAD)

    preview = model.preview_fill(
        input_token="AAVE",
        output_token="USDT",
        claim_share=1 * 10**18,
        output_amount=100 * 10**6,
    )

    assert preview.active is True
    assert preview.input_value_usd_x18 == 110 * WAD
    assert preview.output_value_usd_x18 == 100 * WAD
    assert preview.loss_bps == 909


def test_default_50_25_25_split_for_aave_usdt_example():
    model = AsyncSwapUsdOracleModel(split=SurplusSplit(5000, 2500, 2500))
    model.register_token("AAVE", 18)
    model.register_token("USDT", 6)
    model.warp(1_000)
    model.set_quote("AAVE", 110 * WAD)
    model.set_quote("USDT", 1 * WAD)

    preview = model.preview_fill(
        input_token="AAVE",
        output_token="USDT",
        claim_share=1 * 10**18,
        output_amount=100 * 10**6,
    )

    assert preview.active is True
    assert preview.surplus_input > 0
    # fair claim ~= 100 / 110 AAVE
    assert preview.fair_claim_share == 909090909090909090
    # 50% user, 25% filler, 25% protocol on surplus
    assert preview.user_share_input == 45454545454545455
    assert preview.protocol_share_input == 22727272727272728
    assert preview.filler_share_input == 931818181818181817


def test_missing_quote_skips_capture_instead_of_reverting():
    model = AsyncSwapUsdOracleModel()
    model.register_token("AAVE", 18)
    model.register_token("USDT", 6)
    model.warp(1_000)
    model.set_quote("AAVE", 110 * WAD)

    preview = model.preview_fill(
        input_token="AAVE",
        output_token="USDT",
        claim_share=1 * 10**18,
        output_amount=100 * 10**6,
    )

    assert preview.active is False
    assert preview.filler_share_input == 1 * 10**18


def test_stale_quote_skips_capture_instead_of_reverting():
    model = AsyncSwapUsdOracleModel(max_age_seconds=60)
    model.register_token("AAVE", 18)
    model.register_token("USDT", 6)
    model.warp(1_000)
    model.set_quote("AAVE", 110 * WAD, updated_at=900)
    model.set_quote("USDT", 1 * WAD, updated_at=900)

    preview = model.preview_fill(
        input_token="AAVE",
        output_token="USDT",
        claim_share=1 * 10**18,
        output_amount=100 * 10**6,
    )

    assert preview.active is False
    assert preview.filler_share_input == 1 * 10**18


def test_good_quote_has_no_capture():
    model = AsyncSwapUsdOracleModel()
    model.register_token("ETH", 18)
    model.register_token("USDC", 6)
    model.warp(1_000)
    model.set_quote("ETH", 3000 * WAD)
    model.set_quote("USDC", 1 * WAD)

    preview = model.preview_fill(
        input_token="ETH",
        output_token="USDC",
        claim_share=1 * 10**18,
        output_amount=3000 * 10**6,
    )

    assert preview.active is False
    assert preview.filler_share_input == 1 * 10**18
