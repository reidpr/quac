#!/usr/bin/env python

"""
	All our code runs on a cluster. We break the jobs up by month, so each month of the Wiki access
	logs are dealt with independently.
"""

import datetime
from dateutil.relativedelta import relativedelta

current_date = datetime.date(year=2007, month=12, day=1) #day not used
end_date = datetime.date.today()
increment = relativedelta(months=1)

job_file_location = '/turquoise/usr/projects/infmodels/gfairchild/wikipedia/jobs/index_data/%s'

while current_date < end_date:
	year = current_date.strftime('%Y')
	month = current_date.strftime('%m')

	with open(job_file_location % ('%s-%s' % (year, month)), 'w') as job_file:
		job_file.write('#!/bin/bash\n\n')
		job_file.write('#MSUB -o %s\n' % (job_file_location % ('job_%s-%s.out' % (year, month))))
		job_file.write('#MSUB -e %s\n' % (job_file_location % ('job_%s-%s.err' % (year, month))))
		job_file.write('#MSUB -l nodes=32:ppn=8\n')
		job_file.write('#MSUB -l walltime=0:45:00\n')
		job_file.write('#MSUB -N index_%s-%s\n\n' % (year, month))
		job_file.write('date\n\n')
		job_file.write('cd /turquoise/usr/projects/infmodels/gfairchild/wikipedia/src\n')
		job_file.write('mpirun -n 256 python index_wiki_data.py %s %s\n\n' % (year, month))
		job_file.write('date')	

	current_date += increment
