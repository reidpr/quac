"""
	Index the wikipedia data by creating a SQLite DB for each file.
"""

# Copyright (c) Los Alamos National Security, LLC and others.

from __future__ import print_function
import sqlite3
from mrmpi import mrmpi
import pypar
import gzip
import datetime
import sys
import os
import glob
from collections import deque
import argparse

argparser = argparse.ArgumentParser(description='Index Wikipedia data.')
argparser.add_argument('year', type=str, help='year to index', default=None)
argparser.add_argument('month', type=str, help='month to index', default=None)
args = argparser.parse_args()

def process_file(itask, mr):
	"""
		Read a single file and emit:
			key = date
			value = number of accesses

		Note that multiple dates will be emitted. collate() will aggregate multiple instances into one KMV.
	"""
	#first pull date/time from file name as ints to construct datetime
	file = input_files[itask]
	year = int(file[66:70])
	month = int(file[70:72])
	day = int(file[72:74])
	hour = int(file[75:77])
	timestamp = datetime.datetime(year=year, month=month, day=day, hour=hour)

	#get padded string versions of the datetime components
	y = timestamp.strftime('%Y')
	m = timestamp.strftime('%m')
	d = timestamp.strftime('%d')
	h = timestamp.strftime('%H')
	
	db_file = os.path.join(output_directory_string % (y, m, d), '%s.db' % h)

	print('%s - %s start' % (datetime.datetime.now(), db_file))

	#this is used to delete the database on error
	delete_me = False

	if not os.path.exists(db_file):
		#make directories if necessary
		try:
			os.makedirs(os.path.abspath(os.path.join(db_file, os.pardir)))
		except OSError:
			pass
	
		#now create DB
		with sqlite3.connect(db_file) as connection:
			connection.execute('PRAGMA cache_size=2097152;') #2gb
			connection.text_factory = str

			#initialize DB from schema
			with open(index_schema) as schema:
				schema_sql = schema.read()
			connection.executescript(schema_sql)

			try:
				#remember last 1000 pages to hopefully prevent duplicates from being added
				#I probably only really need to remember the last 3 or 5, but I just want to make sure....
				last_encountered_pages = deque(maxlen=1000)
				inserts = list()

				with gzip.open(file, 'rb') as pagecounts:
					for line in pagecounts:
						line_fields = line.split()
						
						project = line_fields[0]
						page = ' '.join(line_fields[1:-2]) #pages can contain spaces
						try:
							num_accesses = int(line_fields[-2])
							content_size = int(line_fields[-1])
						except:
							print('error parsing line [%s] in %s' % (line, file), file=sys.stderr)
							continue

						if (project, page) not in last_encountered_pages:
							#connection.execute('INSERT INTO page_view_stats VALUES (?, ?, ?, ?);', \
							#	(project, page, num_accesses, content_size))
							inserts.append((project, page, num_accesses, content_size))
							last_encountered_pages.append((project, page))

						#bulk insert for speed
						if len(inserts) == 100000:
							connection.executemany('INSERT INTO page_view_stats VALUES (?, ?, ?, ?);', inserts)
							inserts = list()

					connection.executemany('INSERT INTO page_view_stats VALUES (?, ?, ?, ?);', inserts)
				
				#make sure all entries are written before continuing on
				connection.commit()

				projects = connection.execute('SELECT DISTINCT project FROM page_view_stats;')
				for project in projects:
					total = connection.execute('SELECT sum(num_accesses) FROM page_view_stats WHERE project=?;', project).fetchone()[0]
					connection.execute('INSERT INTO project_totals VALUES (?, ?);', (project[0], total))
			except IOError as e:
				#with automatically handles errors, but in this case, I want to know which files are problematic
				print('error reading %s : %s' % (file, e), file=sys.stderr)
				delete_me = True
			except sqlite3.IntegrityError as e:
				print('error creating DB %s from %s : %s' % (db_file, file, e), file=sys.stderr)
				delete_me = True
			except Exception as e:
				print('some other error occurred creating DB %s from %s : %s' % (db_file, file, e), file=sys.stderr)
				delete_me = True
	
	if delete_me:
		os.remove(db_file)
	
	print('%s - %s finish' % (datetime.datetime.now(), db_file))
		
#we can either index ALL wiki data or only data for the month/year specified
if args.year:
	input_files = sorted(glob.glob('/panfs/scratch3/vol7/reidpr/wp-access/raw/%s/%s-%s/pagecounts*gz' % (args.year, args.year, args.month)))
else:
	input_files = sorted(glob.glob('/panfs/scratch3/vol7/reidpr/wp-access/raw/*/*/pagecounts*gz'))

output_directory_string = '/panfs/scratch3/vol3/gfairchild/wikipedia/index/%s/%s/%s' #YYYY, MM, DD
index_schema = '../data/index_schema.sql'

mr = mrmpi()
mr.verbosity(1)
mr.timer(1)

#get start time
pypar.barrier()
time_start = pypar.time()

#do actual work
mr.map(len(input_files), process_file)

#get stop time
pypar.barrier()
time_stop = pypar.time()

#clean up
mr.destroy()

#output stats
if pypar.rank() == 0:
	print('time to process %d files on %d procs: %g (secs)' % (len(input_files), pypar.size(), time_stop - time_start))
  
pypar.finalize()
