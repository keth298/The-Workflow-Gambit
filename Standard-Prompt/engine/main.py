#!/usr/bin/env python3
# main.py — Entry point

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from uci import uci_loop

if __name__ == '__main__':
    uci_loop()
