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


def _flatten_str_list(inlist: list) -> Generator:
    """Flatten a n-dimension nested list"""
    for item in inlist:
        if isinstance(item, str):
            yield item
        else:
            yield from _flatten_str_list(item)


def dir_tree_to_list(dir_tree: dict, flatten=True, sort=True) -> list:
    """Convert a dir tree (dict) to nested list"""
    _imglist = []
    for k, v in dir_tree.items():
        _imglist += [me if not isinstance(me, dict) else dir_tree_to_list(me) for me in v ]
    _imglist = list(_flatten_str_list(_imglist)) if flatten else _imglist
    return sorted(_imglist) if sort else _imglist

if __name__ == "__main__":
    pass
