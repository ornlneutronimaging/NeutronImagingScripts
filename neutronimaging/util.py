#!/usr/env/bash
# -*- coding: utf-8 -*-

"""
Provide various useful helper functions that
handles system level tasks.
"""
import os


def in_jupyter():
    """check if current kernel is running as notebook backend"""
    try:
        from IPython import get_ipython

        kernel_name = get_ipython().__class__.__name__
        state = True if "ZMQ" in kernel_name else False
    except NameError:
        state = False
    return state


def probe_folder(root: str = ".") -> dict:
    """return folder structure as a dictionary"""
    return {
        os.path.basename(root): [
            os.path.join(root, me)
            if os.path.isfile(os.path.join(root, me))
            else probe_folder(os.path.join(root, me))
            for me in os.listdir(root)
        ]
    }


if __name__ == "__main__":
    pass
