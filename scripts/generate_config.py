#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Thin wrapper kept for callers that invoke the script by path; the
implementation lives in neutronimaging.cli, which is also installed as the
`generate_config` console command."""

from neutronimaging.cli.generate_config import main

if __name__ == "__main__":
    main()
