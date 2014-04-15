#!/usr/bin/env python

# Copyright (c) Los Alamos National Security, LLC and others.

import argparse
from urllib import unquote

argparser = argparse.ArgumentParser(description='Decode a percent-encoded string.')
argparser.add_argument('string', type=str, help='percent-encoded string to decode')
args = argparser.parse_args()

print(unquote(args.string))
