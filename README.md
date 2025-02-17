# UV4

![test](https://github.com/mmsaki/uv4/actions/workflows/test.yml/badge.svg)
[![codecov](https://codecov.io/github/mmsaki/uv4/graph/badge.svg?token=36PUOA0L5F)](https://codecov.io/github/mmsaki/uv4)
![GitHub repo size](https://img.shields.io/github/repo-size/mmsaki/uv4)
![GitHub last commit](https://img.shields.io/github/last-commit/mmsaki/uv4)
![PyPI - Version](https://img.shields.io/pypi/v/uv4)
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

## 🧪 Run Tests

Dependencies:

- pytest
- pytest-watcher

Run command

```sh
ptw .
```
