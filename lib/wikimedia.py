'Handy stuff for Wikimedia and Wikipedia data.'

# Copyright (c) Los Alamos National Security, LLC, and others.

# https://en.wikipedia.org/wiki/Special:ApiSandbox is helpful.

import datetime
import os
import re

import requests

import testable
import time_
import u

l = u.l


API_PAGELEN_DEFAULT = 500
LANG_SEPARATOR = '+'
# Wikipedia API requests contact info in the user agent. We try to guess the
# user's e-mail address rather than configuring it.
HEADERS = { 'User-Agent': ('QUAC http://reidpr.github.io/quac/ %s@%s'
                           % (os.environ['USER'], u.domain())) }

class Article_Not_Found(ValueError): pass


def api_query(lang, args):
   args.update({ 'action': 'query',
                 'format': 'json' })
   # Decode all arguments. Requests will encode them, and the Wikimedia API
   # will deal with canonicalizing article URLs.
   args = { k: (u.url_decode(v) if isinstance(v, str) else v)
            for k, v in args.items() }
   result = dict()
   #l.debug('Wikipedia API User-Agent: %s' % HEADERS['User-Agent'])
   while True:
      r = requests.get('https://%s.wikipedia.org/w/api.php' % lang, args,
                       headers=HEADERS)
      l.debug('%d: %s' % (r.status_code, r.url))
      r.raise_for_status()
      j = r.json()
      # Remove articles with negative IDs, which are assigned sequentially
      # starting from -1 on each result page. This makes the pages
      # un-mergeable.
      if ('pages' in j['query']):
         for pageid in list(j['query']['pages'].keys()):
            if (int(pageid) < 0):
               del j['query']['pages'][pageid]
      result = u.dicts_merge(result, j['query'])
      if ('continue' not in j):
         break
      # Set continue. There is also a generic continue parameter, but it fails
      # with "Invalid continue param". FIXME: Deriving the parameter name is a
      # total kludge.
      del j['continue']['continue']
      (ckey, cval) = j['continue'].popitem()
      assert (len(j['continue']) == 0)
      args[ckey] = cval
   return result

def api_get_categories(url, with_hidden=False, pagelen=API_PAGELEN_DEFAULT):
   try:
      (lang, url) = lang_split(url)
   except ValueError:
      raise Article_Not_Found('no language specified')
   args = { 'prop': 'categories',
            'titles': url,
            'cllimit': pagelen,
            'clprop': 'hidden' }
   data = api_query(lang, args)['pages']
   if (len(data) == 0):
      raise Article_Not_Found('article not found')
   data = data.popitem()[1]
   if ('categories' in data):
      for c in data['categories']:
         if ('hidden' not in c or with_hidden):
            yield (lang + LANG_SEPARATOR + c['title'])

def api_get_links(url, namespace=0, pagelen=API_PAGELEN_DEFAULT):
   (lang, url) = lang_split(url)
   args = { 'generator': 'links',
            'gpllimit': pagelen,
            'gplnamespace': namespace,
            'prop': 'info',
            'redirects': 1,
            'titles': url }
   data = api_query(lang, args)
   if ('missing' in data):
      raise Article_Not_Found('article not found')
   if ('pages' in data):
      for p in data['pages'].values():
         if ('missing' not in p):
            yield (lang + LANG_SEPARATOR + p['title'])

def hour_bizarro(x):
   '''Convert x into an hour number; it can be a filename or a metadata date
      thingy. In the latter case, both the minimum and maximum available hours
      are returned in a tuple. For example:

      >>> hour_bizarro('2013/2013-10/pagecounts-20131016-090001.gz')
      17643776
      >>> a = (datetime.date(2009, 9, 10),
      ...      {'hours': {2: 9058752, 3: 8307681, 4: 7311189, 5: 6341115},
      ...       'total': 49270827})
      >>> hour_bizarro(a)
      (17607842, 17607845)

      (Yes, this is a strange, very specific function with a weird interface.
      It's what I need, though. It really belongs in wp-hashfiles, but that
      has no tests.)'''
   if (isinstance(x, str)):
      dt = timestamp_parse(x)
      return dt.toordinal() * 24 + dt.hour
   else:
      do = x[0].toordinal() * 24
      return (do + min(x[1]['hours'].keys()),
              do + max(x[1]['hours'].keys()))

def lang_split(url):
   try:
      return url.split(LANG_SEPARATOR, 1)
   except ValueError:
      raise Article_Not_Found('no language specified')

def timestamp_parse(text):
   '''Parse the timestamp embedded in pagecount and projectcount files. A
      quirk is that the stamp marks the *end* of the data collection period;
      as we want the beginning, we subtract an hour to compensate (e-mail from
      ariel@wikimedia.org, 2013-09-11). Also, these files are nominally
      created on the hour, but often they are a few seconds later; we ignore
      this to keep consistent intervals. Finally, extra cruft before and after
      the timestamp is permitted. For example:

      >>> timestamp_parse('2013/2013-10/pagecounts-20131016-090001.gz')
      datetime.datetime(2013, 10, 16, 8, 0, tzinfo=<UTC>)
      >>> timestamp_parse('pagecounts-20120101-000000.gz')
      datetime.datetime(2011, 12, 31, 23, 0, tzinfo=<UTC>)
      >>> timestamp_parse('2013/2013-10/projectcounts-20131016-09000')
      Traceback (most recent call last):
        ...
      ValueError: no timestamp found
      >>> timestamp_parse('2013/2013-10/projectcounts-99999999-999999')
      Traceback (most recent call last):
        ...
      ValueError: time data '99999999-999999' does not match format '%Y%m%d-%H%M%S'
'''
   m = re.search(r'(\d{8}-\d{6})(\.gz)?', text)
   if (m is None):
      raise ValueError('no timestamp found')
   t = datetime.datetime.strptime(m.group(1), '%Y%m%d-%H%M%S')
   t = datetime.datetime(t.year, t.month, t.day, t.hour)
   t = time_.utcify(t)
   return (t - datetime.timedelta(hours=1))


testable.register('')
