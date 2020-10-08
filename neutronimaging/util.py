#!/usr/env/bash
# -*- coding: utf-8 -*-

"""
Provide various useful helper functions that
handles system level tasks.
"""


def in_jupyter():
    try:
        from IPython import get_ipython

        kernel_name = get_ipython().__class__.__name__
        state = True if "ZMQ" in kernel_name else False
    except NameError:
        state = False
    return state


if __name__ == "__main__":
    pass
