"""Generate native Huff tick-key checks from the Python oracle. Usage: ... /path/to/v2-raff"""
import sys
from pathlib import Path
import random
from uv4.priority_protocol.arithmetic import price_key
r=random.Random(20261024)
v=[(b,z,a,o) for b in (False,True) for z in (False,True) for a,o in [(1,1),(10**18,10**9),(10**9,10**18),(1,10**70),(10**38,1),(10**36,10**12)]]
v += [(bool(r.getrandbits(1)),bool(r.getrandbits(1)),r.randrange(1,2**r.randrange(1,127)),r.randrange(1,2**r.randrange(1,256))) for _ in range(150)]
s='''// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.26;
import {Test} from "forge-std/Test.sol";
import {HuffNeoDeployer} from "foundry-huff-neo/HuffNeoDeployer.sol";
contract TickParityTest is Test {
 function test_pythonTickVectors() public {
 address h=HuffNeoDeployer.config().deploy("test/harness/TickHarness.huff");
'''
for b,z,a,o in v:
 expected=price_key(b,z,a,o)
 s+=f' _check(h,{str(b).lower()},{str(z).lower()},{a},{o},{expected});\n'
s+=''' }
 function _check(address h,bool b,bool z,uint256 a,uint256 o,uint256 e) internal view {
 (bool ok,bytes memory ret)=h.staticcall(abi.encode(b,z,a,o));
 require(ok,"Huff tick failed"); assertEq(abi.decode(ret,(uint256)),e,"Python tick oracle");
 }
}
'''
(Path(sys.argv[1]) / 'test/huff/TickParity.t.sol').write_text(s)
