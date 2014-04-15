#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
	Scrape the MMWR morbidity tables at http://wonder.cdc.gov/mmwr/mmwrmorb.asp
"""

# Copyright (c) Los Alamos National Security, LLC and others.

from __future__ import print_function, division
import requests
import codecs
import os

mmwr_table_url = 'http://wonder.cdc.gov/mmwr/mmwr_reps.asp?mmwr_year=%d&mmwr_week=%02d&mmwr_table=%s&request=Submit'
mmwr_file = '../data/mmwr/%d-%02d-%s.html'

tables = {'1', '2A', '2B', '2C', '2D', '2E', '2F', '2G', '2H', '2I', '2J', '2K', '3A', '3B', '4'}

error_messages = {'Data are not available for the week requested.', 'No records found.', 'does not exist before the  week ending'}

for year in range(1996, 2015):
	for week in range(1, 54):
		for table in tables:
			if not os.path.exists(mmwr_file % (year, week, table)):
				response = requests.get(mmwr_table_url % (year, week, table))

				error = False
				for error_message in error_messages:
					if error_message in response.text:
						error = True
						break

				if not error:
					with codecs.open(mmwr_file % (year, week, table), 'w', 'utf-8') as output:
						output.write(response.text)

					print('saved %s' % (mmwr_file % (year, week, table)))
