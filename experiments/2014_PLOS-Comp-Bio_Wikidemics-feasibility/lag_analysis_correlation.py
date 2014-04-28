#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
	Run ±28 lagged correlations between wiki data and CSV ground truth data. This script tries all
	possible combinations of articles. This is more of an exploratory script to explore the data.

	example:
		./lag_analysis_correlation.py ../data/time_series/ja_flu_raw.csv ../data/ground_truth/csv/ja_flu.csv
"""

# Copyright (c) Los Alamos National Security, LLC and others.

from __future__ import print_function, division
import argparse
import csv
import sys
import datetime
from collections import OrderedDict
from scipy import stats
from itertools import combinations
from dateutil.parser import parse

argparser = argparse.ArgumentParser(description='Perform ±28 day lagged correlations to determine how Wikipedia and ground truth data are related.')
argparser.add_argument('raw_wikipedia_counts_csv', type=argparse.FileType('r'), help='CSV file containing raw Wikipedia counts')
argparser.add_argument('ground_truth_csv', type=argparse.FileType('r'), help='CSV file containing date,value ground truth data')
argparser.add_argument('-ap', '--aggregate-period', type=str, help='select whether the aggregate period is BEFORE or AFTER the specified date (e.g., does date 2012-09-14 mean we aggregate from [2012-09-07 to 2012-09-14] or [2012-09-14 to 2012-09-21]?)', choices=['before', 'after'], default='after')
args = argparser.parse_args()

#first, read the raw wiki data and aggregate each article's counts by day since that's the resolution we want
project_article_date_count = dict() #en -> flu -> 10/12/09 -> 14
project_date_count = dict() #en -> 10/12/09 -> 9000000
project_articles = set()
with args.raw_wikipedia_counts_csv as wiki_csv:
	reader = csv.reader(wiki_csv)

	#first deal with the headers
	index_project_article = dict() #map header index to (project, article) tuple (e.g., 1 -> (en, Flu), 2 -> (en, Human_flu))
	headers = reader.next()
	for index, header in enumerate(headers):
		if header != 'timestamp':
			header_split = header.split('-')
			if len(header_split) >= 2:
				project = header_split[0]
				article = ''.join(header_split[1:])

				project_articles.add((project, article))

				#initialize dicts that store the wiki data
				if project not in project_article_date_count:
					project_article_date_count[project] = dict()
					project_date_count[project] = OrderedDict() #ordered by date
				if article not in project_article_date_count[project]:
					project_article_date_count[project][article] = OrderedDict() #ordered by date

				index_project_article[index] = (project, article)
			elif len(header_split) == 1:
				index_project_article[index] = (project, None)
	
	#now read the data
	for row in reader:
		#don't forget to account for off-by-one hour issue since hourly timestamps mark the END of the hour
		#date = (datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S') - datetime.timedelta(hours=1)).date()
		date = (parse(row[0]) - datetime.timedelta(hours=1)).date()

		for index, value in enumerate(row):
			#skip timestamp since we've already read it
			if index == 0:
				continue

			project, article = index_project_article[index]

			#article will be None if it's the project total count
			if article:
				if date not in project_article_date_count[project][article]:
					project_article_date_count[project][article][date] = 0
				project_article_date_count[project][article][date] += int(value)
			else:
				if date not in project_date_count[project]:
					project_date_count[project][date] = 0
				project_date_count[project][date] += int(value)

#now read the ground truth data
ground_truth_date_count = OrderedDict() #ordered by date
with args.ground_truth_csv as ground_truth_csv:
	reader = csv.reader(ground_truth_csv)

	for row in reader:
		#date = datetime.datetime.strptime(row[0], '%Y-%m-%d').date()
		date = parse(row[0]).date()

		if date in ground_truth_date_count:
			raise ValueError('date [%s] present multiple times in ground truth CSV' % date)
		ground_truth_date_count[date] = float(row[1])

#now we can do the lag analysis
for size in range(1, 6):
	for combination in combinations(project_articles, size):
		print(combination)
		
		#look at ±28 day lagged correlations and find the best
		best_offset = None
		best_correlation = float('-inf')
		
		offset = -28
		while offset <= 28:
			#generate list of offset dates
			offset_ground_truth_dates = [(x + datetime.timedelta(days=offset)) for x in ground_truth_date_count.keys() if (x + datetime.timedelta(days=offset)) in project_article_date_count[combination[0][0]][combination[0][1]]] #using the first combination is arbitrary - all will have the same dates
			offset_ground_truth_dates_iterator = iter(offset_ground_truth_dates)

			#construct new normalized shifted time series
			start_date = next(offset_ground_truth_dates_iterator)
			current_date = start_date
			next_date = next(offset_ground_truth_dates_iterator)
			last_date = offset_ground_truth_dates[-1]
			date_normalized_wiki_count = OrderedDict()
			current_total_project_accesses = 0
			while start_date <= last_date:
				#we've hit the next date so finalize the normalization, shift dates, and reset counters
				if current_date == next_date:
					#don't forget to deal with the aggregate period here
					if args.aggregate_period == 'after':
						if current_total_project_accesses != 0:
							date_normalized_wiki_count[start_date] /= current_total_project_accesses
						else:
							date_normalized_wiki_count[start_date] = 0
					else:
						if current_total_project_accesses != 0:
							date_normalized_wiki_count[next_date] /= current_total_project_accesses
						else:
							date_normalized_wiki_count[next_date] = 0

					start_date = next_date
					next_date = next(offset_ground_truth_dates_iterator, None)
					current_total_project_accesses = 0

					if not next_date:
						break

				#add counts for this time frame
				#the aggregate period is handled here: we still count the same values, but the values get associated with next_date instead of start_date
				if args.aggregate_period == 'after':
					if start_date not in date_normalized_wiki_count:
						date_normalized_wiki_count[start_date] = 0
					
					#aggregate all article counts
					for project, article in combination:
						date_normalized_wiki_count[start_date] += project_article_date_count[project][article][current_date]

					#do project totals
					encountered_projects = set()
					for project, _ in combination:
						if project not in encountered_projects:
							current_total_project_accesses += project_date_count[project][current_date]
							encountered_projects.add(project)
				else:
					if next_date not in date_normalized_wiki_count:
						date_normalized_wiki_count[next_date] = 0

					for project, article in combination:
						date_normalized_wiki_count[next_date] += project_article_date_count[project][article][current_date]

					encountered_projects = set()
					for project, _ in combination:
						if project not in encountered_projects:
							current_total_project_accesses += project_date_count[project][current_date]
							encountered_projects.add(project)

				current_date += datetime.timedelta(days=1)

			#pull ground truth values only for the dates that are in agreement with the wiki values
			#these are the values we use to correlate with the wiki values
			corresponding_ground_truth_values = [ground_truth_date_count[x - datetime.timedelta(days=offset)] for x in date_normalized_wiki_count]

			#compute correlation
			correlation = stats.pearsonr(date_normalized_wiki_count.values(), corresponding_ground_truth_values)[0]

			if correlation > best_correlation:
				best_correlation = correlation
				best_offset = offset

			print('correlation: %g (offset: %d days)' % (correlation, offset))

			offset += 1

		print('----------------------------')
		print('best correlation: %g (offset: %d days)' % (best_correlation, best_offset if best_offset else 0))
		print()
