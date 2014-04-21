#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
	This is a really quick script to decide percent-encoded strings.

	example:
		./decode_url.py http://th.wikipedia.org/wiki/%E0%B9%84%E0%B8%82%E0%B9%89%E0%B9%80%E0%B8%94%E0%B9%87%E0%B8%87%E0%B8%81%E0%B8%B5
		http://th.wikipedia.org/wiki/ไข้เด็งกี
"""

# Copyright (c) Los Alamos National Security, LLC and others.

from __future__ import print_function
import argparse
from urllib import unquote

argparser = argparse.ArgumentParser(description='Decode a percent-encoded string.')
argparser.add_argument('string', type=str, help='percent-encoded string to decode')
args = argparser.parse_args()

print(unquote(args.string))
