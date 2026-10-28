"""EOA EIP-712 signatures for the hook, Router and Permit2 witness paths.

Types mirror contracts/src/libraries/OrderSignatures.sol. Permit2 domain and witness encoding
follow Uniswap/permit2 src/EIP712.sol and src/libraries/PermitHash.sol. ERC-1271 execution is
an explicit verifier callback rather than an EVM implementation.
"""
from eth_utils import keccak
from .identity import address, digest
from .ledger import HOOK, ROUTER

POOL = "PoolKey(address currency0,address currency1,uint24 fee,int24 tickSpacing,address hooks)"
ORDER = "AsyncOrder(address maker,address tokenIn,address tokenOut,uint256 amountIn,uint256 amountOutMin,uint256 priorityFee,PoolKey pool)"
SET = "SetExecutor(address maker,address executor,bool allow,PoolKey pool,uint256 nonce,uint256 deadline)"
UPDATE = "UpdatePrice(address maker,address tokenIn,address tokenOut,uint256 amountIn,uint256 newAmountOutMin,bytes32 orderId,uint64 sequence,uint256 nonce,uint256 deadline)"
CANCEL = "CancelOrder(address maker,address tokenIn,address tokenOut,uint256 amountIn,bytes32 orderId,uint64 createdSequence,uint256 nonce,uint256 deadline)"
PERMIT2 = "0x000000000022D473030F116dDEE9F6B43aC78BA3"

def struct_hash(type_text, types, values):
    return digest(["bytes32"] + types, [keccak(text=type_text)] + values)

def pool_hash(pool):
    return struct_hash(POOL, ["address", "address", "uint24", "int24", "address"],
                       [address(pool.currency0), address(pool.currency1), pool.fee, pool.tick_spacing, address(HOOK)])

def domain(chain_id, target):
    if target == PERMIT2:
        return struct_hash("EIP712Domain(string name,uint256 chainId,address verifyingContract)",
                           ["bytes32", "uint256", "address"], [keccak(text="Permit2"), chain_id, PERMIT2])
    name = "AsyncSwap" if target == HOOK else "AsyncSwap Router"
    return struct_hash("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)",
                       ["bytes32", "bytes32", "uint256", "address"],
                       [keccak(text=name), keccak(text="1"), chain_id, address(target)])

def typed(chain_id, target, value):
    return keccak(b"\x19\x01" + domain(chain_id, target) + value)

def executor_digest(chain_id, pool, maker, executor, allow, nonce, deadline):
    h = struct_hash(SET + POOL, ["address", "address", "bool", "bytes32", "uint256", "uint256"],
                    [address(maker), address(executor), allow, pool_hash(pool), nonce, deadline])
    return typed(chain_id, HOOK, h)

def action_digest(chain_id, pool, order, nonce, deadline, new_minimum=None):
    tin, tout = pool.tokens(order.is_buy)
    types = ["address", "address", "address", "uint256"]
    values = [address(order.owner), address(tin), address(tout), order.amount_in]
    if new_minimum is not None:
        types += ["uint256"]
        values += [new_minimum]
    types += ["bytes32"]
    values += [bytes.fromhex(order.id)]
    # A reprice binds the queue sequence, which every reprice moves on; a cancel binds the incarnation.
    types += ["uint64"]
    values += [order.sequence if new_minimum is not None else order.created_sequence]
    types += ["uint256", "uint256"]
    values += [nonce, deadline]
    return typed(chain_id, HOOK if new_minimum is not None else ROUTER,
                 struct_hash(UPDATE if new_minimum is not None else CANCEL, types, values))

def permit_digest(chain_id, pool, maker, is_buy, amount, minimum, bid, nonce, deadline):
    tin, tout = pool.tokens(is_buy)
    witness = struct_hash(ORDER + POOL,
        ["address", "address", "address", "uint256", "uint256", "uint256", "bytes32"],
        [address(maker), address(tin), address(tout), amount, minimum, bid, pool_hash(pool)])
    token_type = "TokenPermissions(address token,uint256 amount)"
    permission = struct_hash(token_type, ["address", "uint256"], [address(tin), amount])
    permit_type = ("PermitWitnessTransferFrom(TokenPermissions permitted,address spender,uint256 nonce,uint256 deadline,"
                   "AsyncOrder witness)" + ORDER + POOL + token_type)
    return typed(chain_id, PERMIT2, struct_hash(permit_type,
        ["bytes32", "address", "uint256", "uint256", "bytes32"],
        [permission, address(ROUTER), nonce, deadline, witness]))

def verify(maker, value, signature, permit2=False):
    from eth_keys import keys
    from eth_keys.constants import SECPK1_N
    try:
        if len(signature) == 65:
            r, s, v = int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:64], "big"), signature[64]
        elif permit2 and len(signature) == 64:
            r, vs = int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big")
            s, v = vs & (2**255 - 1), 27 + (vs >> 255)
        else:
            return False
        if v not in (27, 28) or not 0 < s < SECPK1_N:
            return False
        if not permit2 and s > SECPK1_N // 2:
            return False
        recovered = keys.Signature(vrs=(v - 27, r, s)).recover_public_key_from_msg_hash(value)
        return recovered.to_checksum_address().lower() == address(maker).lower()
    except Exception:
        # eth_keys uses multiple validation and recovery exception classes.
        return False
