# SPDX-FileCopyrightText: 2026 Cooper Dalrymple (@relic-se)
#
# SPDX-License-Identifier: GPLv3
import gc

try:
    import ustack
except ImportError:
    ustack = None

def mem_info(verbose: int = 0):
    if ustack:
        print(f"stack: {ustack.stack_usage()} out of {ustack.stack_size()}")
    used, free = gc.mem_alloc(), gc.mem_free()
    print(f"GC: total: {used+free}, used: {used}, free: {free}")
