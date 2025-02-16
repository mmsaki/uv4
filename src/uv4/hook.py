class Hook:
    BEFORE_INITIALIZE_FLAG = 1 << 13
    AFTER_INITIALIZE_FLAG = 1 << 12
    BEFORE_ADD_LIQUIDITY_FLAG = 1 << 11
    AFTER_ADD_LIQUIDITY_FLAG = 1 << 10
    BEFORE_REMOVE_LIQUIDITY_FLAG = 1 << 9
    AFTER_REMOVE_LIQUIDITY_FLAG = 1 << 8
    BEFORE_SWAP_FLAG = 1 << 7
    AFTER_SWAP_FLAG = 1 << 6
    BEFORE_DONATE_FLAG = 1 << 5
    AFTER_DONATE_FLAG = 1 << 4
    BEFORE_SWAP_RETURNS_DELTA_FLAG = 1 << 3
    AFTER_SWAP_RETURNS_DELTA_FLAG = 1 << 2
    AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG = 1 << 1
    AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG = 1 << 0

    def __init__(self, address: int):
        assert address < 2**160
        self.address = address

    def get_hook_flags(self) -> str:
        return format(self.address & 0x3FFF, "b").zfill(14)

    def has_all_flags(self) -> bool:
        flags = self.get_hook_flags()
        return flags == "11111111111111"

    def has_before_initialize(self) -> bool:
        # flags = get_hook_flags(address)
        # before_intilize = flags[0]
        # print(flags)
        # return before_intilize == "1"
        mask = self.address & self.BEFORE_INITIALIZE_FLAG
        return mask == self.BEFORE_INITIALIZE_FLAG

    def has_after_initialize_flag(self) -> bool:
        mask = self.address & self.AFTER_INITIALIZE_FLAG
        return mask == self.AFTER_INITIALIZE_FLAG

    def has_before_add_liquidity_flag(self) -> bool:
        mask = self.address & self.BEFORE_ADD_LIQUIDITY_FLAG
        return mask == self.BEFORE_ADD_LIQUIDITY_FLAG

    def has_after_add_liquidity_flag(self) -> bool:
        mask = self.address & self.AFTER_ADD_LIQUIDITY_FLAG
        return mask == self.AFTER_ADD_LIQUIDITY_FLAG

    def has_before_remove_liquidity_flag(self) -> bool:
        mask = self.address & self.BEFORE_REMOVE_LIQUIDITY_FLAG
        return mask == self.BEFORE_REMOVE_LIQUIDITY_FLAG

    def has_after_remove_liquidity_flag(self) -> bool:
        mask = self.address & self.AFTER_REMOVE_LIQUIDITY_FLAG
        return mask == self.AFTER_REMOVE_LIQUIDITY_FLAG

    def has_before_swap_flag(self) -> bool:
        mask = self.address & self.BEFORE_SWAP_FLAG
        return mask == self.BEFORE_SWAP_FLAG

    def has_after_swap_flag(self) -> bool:
        mask = self.address & self.AFTER_SWAP_FLAG
        return mask == self.AFTER_SWAP_FLAG

    def has_before_donate_flag(self) -> bool:
        mask = self.address & self.BEFORE_DONATE_FLAG
        return mask == self.BEFORE_DONATE_FLAG

    def has_after_donate_flag(self) -> bool:
        mask = self.address & self.AFTER_DONATE_FLAG
        return mask == self.AFTER_DONATE_FLAG

    def has_before_swap_returns_delta_flag(self) -> bool:
        mask = self.address & self.BEFORE_SWAP_RETURNS_DELTA_FLAG
        return mask == self.BEFORE_SWAP_RETURNS_DELTA_FLAG

    def has_after_swap_returns_delta_flag(self) -> bool:
        mask = self.address & self.AFTER_SWAP_RETURNS_DELTA_FLAG
        return mask == self.AFTER_SWAP_RETURNS_DELTA_FLAG

    def has_after_add_liquidity_returns_delta_flag(self) -> bool:
        mask = self.address & self.AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG
        return mask == self.AFTER_ADD_LIQUIDITY_RETURNS_DELTA_FLAG

    def has_after_remove_liquidity_returns_delta_flag(self) -> bool:
        mask = self.address & self.AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG
        return mask == self.AFTER_REMOVE_LIQUIDITY_RETURNS_DELTA_FLAG
