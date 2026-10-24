"""Solidity-compatible ABI/Keccak order identities; symbolic fixture addresses are deterministic."""
from eth_abi import encode
from eth_utils import keccak
from .ledger import NATIVE

def address(value):
    if value == NATIVE:
        return "0x" + "00" * 20
    if value.startswith("0x") and len(value) == 42:
        return value
    return "0x" + keccak(text=value)[-20:].hex()

def digest(types, values):
    return keccak(encode(types, values))

def pool_id(currency0, currency1, fee, spacing, hook):
    return digest(["address", "address", "uint24", "int24", "address"],
                  [address(currency0), address(currency1), fee, spacing, address(hook)])

def order_id(chain_id, pool, owner, zfo, salt):
    return digest(["uint256", "bytes32", "address", "bool", "bytes32"],
                  [chain_id, pool, address(owner), zfo, salt]).hex()

def creation_salt(timestamp, block, manager, owner, amount, minimum, bid):
    return digest(["uint256", "uint256", "address", "address", "uint256", "uint256", "uint256"],
                  [timestamp, block, address(manager), address(owner), amount, minimum, bid])
