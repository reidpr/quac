#!/usr/bin/env python

"""
	Use MR-MPI to generate a time series of visits to specified Wikipedia articles. Also, aggregate results over specified intervals.

	examples:
		mpirun -n 32 python time_series.py -a ../data/articles/ja_flu_articles.txt -ao ../data/agg_test.csv -ro ../data/raw_test.csv -at interval -is 2009-01-17 -il 7

		mpirun -n 32 python time_series.py -a ../data/articles/pl_flu_articles.txt -ao ../data/agg_test.csv -ro ../data/raw_test.csv -at dates -df ../data/dates/poland_flu_dates.txt
"""

# Copyright (c) Los Alamos National Security, LLC and others.

from __future__ import print_function, division
import sqlite3
from mrmpi import mrmpi
import pypar
import gzip
import datetime
import sys
import os
import glob
import argparse
from collections import deque

#generate a list of all files to process
months = sorted(glob.glob('/panfs/scratch3/vol3/gfairchild/wikipedia/index/*/*'))

def make_datetime(date):
	return datetime.datetime.strptime(date, '%Y-%m-%d')

#read in search terms
argparser = argparse.ArgumentParser(description='Output both a raw hourly time series as well as a normalized aggregated time series of visits to specified Wikipedia articles.')
argparser.add_argument('-a', '--articles', type=argparse.FileType('r'), help='file containing articles we care about', required=True)
argparser.add_argument('-ao', '--aggregate-output', type=argparse.FileType('w'), help='file in which aggregated time series will be output')
argparser.add_argument('-ro', '--raw-output', type=argparse.FileType('w'), help='file in which raw time series will be output', required=True)
argparser.add_argument('-at', '--aggregation-type', type=str, help='select whether to aggregate at regular intervals or according to arbitrary dates specified in a file', choices=['none', 'dates', 'interval'], required=True)
argparser.add_argument('-df', '--date-file', type=argparse.FileType('r'), help='file for date aggregation')
argparser.add_argument('-is', '--interval-start', type=make_datetime, help='start date if using interval aggregation')
argparser.add_argument('-il', '--interval-length', type=int, help='number of days between dates if using interval aggregation')
argparser.add_argument('-ap', '--aggregate-period', type=str, help='select whether the aggregate period is BEFORE or AFTER the specified date (e.g., does date 2012-09-14 mean we aggregate from [2012-09-07 to 2012-09-14] or [2012-09-14 to 2012-09-21]?)', choices=['before', 'after'], default='after')
args = argparser.parse_args()

#read in desired articles
desired_articles = set()
with args.articles as articles:
	for line in articles:
		language, article = line.split()
		desired_articles.add((language, article))

def process_file(itask, mr):
	"""
		Read a single file and emit:
			key = date
			value = (language, article, num_accesses, language_accesses) tuple

		Note that multiple dates will be emitted. collate() will aggregate multiple instances into one KMV.
	"""
	month_path = months[itask]
	files = glob.glob('%s/*/*.db' % month_path)

	#process each file in the month
	#there will be a max of 744
	for file in files:
		year = int(file[48:52])
		month = int(file[53:55])
		day = int(file[56:58])
		hour = int(file[59:61])
		timestamp = datetime.datetime(year=year, month=month, day=day, hour=hour)

		#note that the access log timestamps mark the *end* of an hour, not the beginning
		#for this reason, emit (hour - 1) to make things easier
		timestamp -= datetime.timedelta(hours=1)

		#print('%s - %s start' % (datetime.datetime.now(), file))

		#now read file and search for all articles we care about
		with sqlite3.connect(file) as connection:
			connection.execute('PRAGMA cache_size=2097152;') #2gb

			language_accesses = dict()

			for language, article in desired_articles:
				#first get num_accesses for the article
				result = connection.execute('SELECT num_accesses FROM page_view_stats WHERE project=? AND page=?;', (language, article)).fetchone()
				if result:
					num_accesses = result[0]
				else:
					num_accesses = 0

				#now get the total number of access across all articles in this language
				if language not in language_accesses:
					result = connection.execute('SELECT total FROM project_totals WHERE project=?;', (language,)).fetchone()
					if result:
						language_accesses[language] = result[0]
					else:
						language_accesses[language] = 0

				#emit the values for this timestamp
				mr.add(timestamp, (language, article, num_accesses, language_accesses[language]))
	
		#print('%s - %s finish' % (datetime.datetime.now(), file))

def total(key, mvalue, mr):
	"""
		Compile all accesses for a particular timestamp.
			key = timestamp
			value = dict containing total number of accesses for each article
	"""
	#transform from list to dict
	values = dict()

	all_language_accesses = dict()
	total_num_accesses = 0
	for value in mvalue:
		language = value[0]
		article = value[1]
		num_accesses = value[2]
		language_accesses = value[3]

		values[(language, article)] = num_accesses

		if language not in all_language_accesses:
			all_language_accesses[language] = language_accesses
	values['language_accesses'] = all_language_accesses

	#make sure there is an entry for every single article
	for (language, article) in desired_articles:
		if (language, article) not in values:
			values[(language, article)] = 0

	mr.add(key, values)

def compare(v1, v2):
	"""
		Order smallest to largest.
	"""
	if v1 < v2:
		return -1
	elif v1 > v2:
		return 1
	return 0

def convert_to_dict(itask, key, value, mr):
	"""
		Add each date/number of access to a Python dict for simpler operation.
	"""
	timestamp_counts[key] = value

mr = mrmpi()
mr.verbosity(1)
mr.timer(1)

#get start time
pypar.barrier()
time_start = pypar.time()

#do actual work
mr.map(len(months), process_file)
mr.collate()
mr.reduce(total)

#get stop time
pypar.barrier()
time_stop = pypar.time()

#gather all results on a single processor, sort, and output
mr.gather(1)
#mr.sort_keys(compare)
timestamp_counts = dict()
mr.map_mr(mr, convert_to_dict)

#clean up
mr.destroy()

#output - only processor 0 has the data because of gather()
if pypar.rank() == 0:
	sorted_timestamps = sorted(timestamp_counts)
	first_date = sorted_timestamps[0]
	last_date = sorted_timestamps[-1]

	sorted_desired_articles = sorted(desired_articles) #sort to ensure order
	increment = datetime.timedelta(hours=1) #always move to next hour in dataset when incrementing

	#remember that all wiki data are given for the previous hour - this is why 1 is subtracted from the hour
	#e.g., hour 6 refers to the accesses between 5 and 6
	first_date -= increment
	last_date -= increment

	#first, output all raw data
	with args.raw_output as output:
		#write header
		output.write('timestamp',)
		#first output articles
		for language, article in sorted_desired_articles:
			output.write(',%s-%s' % (language, article))
		#next output languages
		encountered_languages = set()
		for language, _ in sorted_desired_articles:
			if language not in encountered_languages:
				output.write(',%s' % language)
				encountered_languages.add(language)
		output.write('\n')

		#always output all raw data
		current_timestamp = first_date
		while current_timestamp <= last_date:
			output.write('%s' % (current_timestamp + increment)) #add increment so that the raw data dates correspond directly with a wiki file

			#print out article counts
			for language, article in sorted_desired_articles:
				#account for missing data
				if current_timestamp in timestamp_counts:
					output.write(',%d' % timestamp_counts[current_timestamp][(language, article)])
				else:
					output.write(',0')
			
			#now print out language counts
			encountered_languages = set()
			for language, _ in sorted_desired_articles:
				if language not in encountered_languages:
					#account for missing data
					if current_timestamp in timestamp_counts:
						output.write(',%d' % timestamp_counts[current_timestamp]['language_accesses'][language])
					else:
						output.write(',0')
					encountered_languages.add(language)

			output.write('\n')

			current_timestamp += increment

	#now, output all aggregate data
	if args.aggregation_type != 'none':
		with args.aggregate_output as output:
			#write header
			output.write('date',)
			for language, article in sorted_desired_articles:
				output.write(',%s-%s' % (language, article))
			output.write('\n')
	
			#either output at regular intervals or according to dates in a file
			if args.aggregation_type == 'interval':
				interval = datetime.timedelta(days=args.interval_length) #to know when the next aggregation date is
				start_date = args.interval_start #used solely for output

				#handle aggregation period parameter
				if args.aggregate_period == 'before':
					next_date = start_date
					current_timestamp = start_date - interval
				else:
					next_date = start_date + interval
					current_timestamp = start_date

				cumulative_counts = dict() #map (language, article) to cumulative count (total_num_accesses, total_language_accesses)

				while current_timestamp <= last_date:
					#output aggregated data if we hit the next interval
					if current_timestamp >= next_date:
						output.write('%s' % start_date.date())
						for language, article in sorted_desired_articles:
							#lots of missing data can lead to a divide by zero error
							if cumulative_counts[(language, article)][1] != 0:
								output.write(',%g' % (cumulative_counts[(language, article)][0] / cumulative_counts[(language, article)][1]))
							else:
								output.write(',0')
						output.write('\n')

						cumulative_counts = dict()
						start_date += interval
						next_date += interval

					#increment aggregate counts
					for language, article in sorted_desired_articles:
						if (language, article) not in cumulative_counts:
							cumulative_counts[(language, article)] = (0, 0)
						#there may be missing data
						if current_timestamp in timestamp_counts:
							cumulative_counts[(language, article)] = (cumulative_counts[(language, article)][0] + \
																	  timestamp_counts[current_timestamp][(language, article)], \
																	  cumulative_counts[(language, article)][1] + \
																	  timestamp_counts[current_timestamp]['language_accesses'][language])

					#go to next hour
					current_timestamp += increment
			else:
				#read in dates from file
				dates = deque()
				with args.date_file as aggregation_dates:
					for date in aggregation_dates:
						dates.append(datetime.datetime.strptime(date.strip(), '%Y-%m-%d'))

				#right now, I'm deliberately not handling args.aggregate_period here
				#I'll just assume for now that it's 'after'
					
				start_date = dates.popleft()
				next_date = dates.popleft()
				current_timestamp = start_date

				cumulative_counts = dict() #map (language, article) to cumulative count (total_num_accesses, total_language_accesses)
	
				while current_timestamp <= last_date:
					if current_timestamp >= next_date:
						#output because we hit the next date
						output.write('%s' % start_date.date())
						for language, article in sorted_desired_articles:
							#lots of missing data can lead to a divide by zero error
							if cumulative_counts[(language, article)][1] != 0:
								output.write(',%g' % (cumulative_counts[(language, article)][0] / cumulative_counts[(language, article)][1]))
							else:
								output.write(',0')
						output.write('\n')

						#we can only output cumulative counts for a date range
						#when we hit the last date in dates, there is no end date, so we should quit
						if not dates:
							break

						cumulative_counts = dict()
						start_date = next_date
						next_date = dates.popleft()

					#increment aggregate counts
					for language, article in sorted_desired_articles:
						if (language, article) not in cumulative_counts:
							cumulative_counts[(language, article)] = (0, 0)
						#there may be missing data
						if current_timestamp in timestamp_counts:
							cumulative_counts[(language, article)] = (cumulative_counts[(language, article)][0] + \
																	  timestamp_counts[current_timestamp][(language, article)], \
																	  cumulative_counts[(language, article)][1] + \
																	  timestamp_counts[current_timestamp]['language_accesses'][language])

					current_timestamp += increment

	print('time to process %d files on %d procs: %g (secs)' % (len(timestamp_counts), pypar.size(), time_stop - time_start))

pypar.finalize()
