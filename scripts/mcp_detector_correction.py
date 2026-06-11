#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Thin wrapper kept for callers that invoke the script by path (SNS/HFIR
autoreduction); the implementation lives in neutronimaging.cli, which is
also installed as the `mcp_detector_correction` console command."""

from neutronimaging.cli.mcp_detector_correction import main

if __name__ == "__main__":
    main()
