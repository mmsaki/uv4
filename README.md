# UV4

![test](https://github.com/mmsaki/uv4/actions/workflows/test.yml/badge.svg)
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

## Fixed Point

- Q64.96 convertion utils
  - [x] Convert decimal to Q64.96
  - [x] Convert Q64.96 to decimal

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
>>>
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
