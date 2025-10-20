# UV4

[![Publish](https://github.com/mmsaki/uv4/actions/workflows/release.yml/badge.svg)](https://github.com/mmsaki/uv4/actions/workflows/release.yml)
![PyPI - Version](https://img.shields.io/pypi/v/uv4)
![test](https://github.com/mmsaki/uv4/actions/workflows/test.yml/badge.svg)
[![codecov](https://codecov.io/github/mmsaki/uv4/graph/badge.svg?token=36PUOA0L5F)](https://codecov.io/github/mmsaki/uv4)
![GitHub repo size](https://img.shields.io/github/repo-size/mmsaki/uv4)
![GitHub last commit](https://img.shields.io/github/last-commit/mmsaki/uv4)
![PyPI - Downloads](https://img.shields.io/pypi/dm/uv4)
![GitHub top language](https://img.shields.io/github/languages/top/mmsaki/uv4)
![X (formerly Twitter) Follow](https://img.shields.io/twitter/follow/msakiart)

Math utils for Uniswap v4.

## Install

```sh
pip install uv4
```

## Q64.96

- Q64.96 Fixed Point convertions
  - [x] Convert decimal to Q64.96
  - [x] Convert Q64.96 to decimal
  - [x] Get 64 bit string
  - [x] Get 96 bit string

Usage

```py
>>> from uv4 import Q6496
>>> value = 1.0001
>>> q = Q6496(value)
>>> q.from_decimal()
79236085330515764027303304731
>>> q.to_decimal()
Decimal('1.00009999999999999999999999999957590837735318405341065472330397412292768422048538923263549804688')
>>> q.get_64_bits_string()
'0000000000000000000000000000000000000000000000000000000000000001'
>>> q.get_96_bits_precision_string()
'000000000000011010001101101110001011101011000111000100001100101100101001010111101001111000011011'
>>> q.to_Q6496_binary_string()
'0b0000000000000000000000000000000000000000000000000000000000000001000000000000011010001101101110001011101011000111000100001100101100101001010111101001111000011011'
>>> q.value
Decimal('1.0001')
>>> q.q_number
79236085330515764027303304731
```

## TickMath & Sqrt Prices

```py
>>> from uv4 import TickMath
>>> tick = 10
>>> tick_spacing = 1
>>> t = TickMath(tick, tick_spacing)
>>> t.to_price()
Decimal('1.0010004501200210025202100120004500100001')
>>> t.to_sqrt_price()
Decimal('1.00050010001000050001')
>>> t.to_sqrt_price_x96()
79267784519130042428790663799
```

- [x] get price at tick
- [x] get tick at price
- [x] get Q64.96 price at tick
- [x] get tick at Q64.96 price
- [x] get Q64.96 price from price
- [x] get price from Q64.96 price

## Hooks

```py
>>> from uv4 import Hook
>>> address = 0x00000000000000000000000000000000000000b5
>>> h = Hook(address)
>>> h.has_after_swap_flag()
False
>>> h.has_before_swap_flag()
True
```

## Liquidity amounts within and outside range

- [x] Amount of token0 within range
- [x] Amount of token1 within range
- [x] Amount of token0 outside range
- [x] Amount of token1 outside range

Usage:

```py
from uv4 import Liquidity, TickMath

liq = Liquidity()
tm = TickMath()

# https://app.uniswap.org/positions/v4/ethereum/1
position_liquidity = 555103547015
tick_lower = -887270
tick_upper = 887270
sqrt_price = 1260437594239115943190250841240651

tick = tm.from_sqrt_pricex96(sqrt_price)
price = tm.to_price(tick)
price_upper = tm.to_price(tick_upper)
price_lower = tm.to_price(tick_lower)

token0, token1 = liq.calculate_position_holdings(
    position_liquidity,
    price,
    price_upper,
    price_lower,
)
print("token0 amount == ", round(token0 / 10**6, 4), "USDC")
print("token1 amount == ", round(token1 / 10**18, 4), "ETH")
```

Result:

```txt
token0 amount ==  34.8933 USDC
token1 amount ==  0.0088 ETH
```

- `token0` = $34.89 USDC
- `token1` = 0.0088 ETH

## LP Fees earned

- [x] Amount of token0 in uncollected fees
- [x] Amount of token1 in uncollected fees

Usage:

```py
from uv4 import Liquidity

liq = Liquidity()

# example position https://app.uniswap.org/positions/v3/ethereum/37
position_liquidity = 10860507277202
feeGrowthGlobal0 = 5247194057753078598628514306485795
feeGrowthGlobal1 = 2233111119924828986464996298702686253189413
feeGrowthOutside0_lower = 96197287712989292312469866057737
feeGrowthOutside0_upper = 437757860306982806877467479294063
feeGrowthInside0 = 0
feeGrowthOutside1_lower = 20741530393032227016498669306435785133483
feeGrowthOutside1_upper = 101747371833570761666428696605043869042568
feeGrowthInside1 = 0
tick_lower = 192180
tick_upper = 193380
tick = 193397

fees0, fees1 = liq.calculate_uncollected_fees(
    position_liquidity,
    feeGrowthGlobal0,
    feeGrowthGlobal1,
    feeGrowthOutside0_lower,
    feeGrowthOutside0_upper,
    feeGrowthInside0,
    feeGrowthOutside1_lower,
    feeGrowthOutside1_upper,
    feeGrowthInside1,
    tick_lower,
    tick_upper,
    tick,
)
print("fees0 == ", round(fees0 / 10**6, 4), "USDC")
print("fees1 == ", round(fees1 / 10**18, 4), "ETH")
```

Result:

```txt
fees0 ==  10.9013 USDC
fees1 ==  0.0026 ETH
```

- `fees0` = $10.90 USDC
- `fees1` = 0.0026 ETH

## 🧪 Run Tests

Dependencies:

- pytest
- pytest-watcher

Run command

```sh
ptw .
```
