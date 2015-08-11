# Classes to represent objects found in tweet streams.
#
# Copyright (c) Los Alamos National Security, LLC, and others.



from datetime import date, datetime
import dateutil.parser
import html.parser
from pprint import pprint
import re

from django.contrib.gis import geos
import ujson as json

import testable
import time_
import tsv_glue
import u


HTML_PARSER = html.parser.HTMLParser()
NON_ALPHANUMERICS_RE = re.compile(r'[\W_]+')
WHITESPACES_RE = re.compile(r'[\s\0]+')


class Nothing_To_Parse_Error(Exception):
   pass

class Unknown_Object_Error(Exception):
   def __str__(self):
      return 'unknown object parsed'


def expected_count(date_, sample_rate):
   '''Return the expected number of tweets on date with sample_rate. This very
      gross number comes from piecewise linear fits in tweet-volume.xls. (You
      should be suspicious of it.) For example (these tests match the
      spreadsheet):

      >>> expected_count(date(2010,  1,  1), 0.01)
      1234982.878...
      >>> expected_count(date(2011,  1,  1), 0.01)
      896212.305...
      >>> expected_count(date(2012,  4,  1), 0.01)
      2686752.038...
      >>> expected_count(date(2013,  4,  1), 0.01)
      4303487.866...
      >>> expected_count(date(2009,  9, 23), 0.01)
      Traceback (most recent call last):
        ...
      ValueError: extrapolating to 2009-09-23 is too scary
      >>> expected_count(date(2009,  9, 24), 0.01)
      Traceback (most recent call last):
        ...
      ValueError: extrapolating to 2009-09-24 is too scary
      >>> expected_count(date(2014,  1,  1), 0.01)
      Traceback (most recent call last):
        ...
      ValueError: extrapolating to 2014-01-01 is too scary'''
   # inclusive until date, slope, intercept
   segments = [[date(2009,  9, 24), None,             None],
               [date(2010,  7, 15), 5958.04409994402, -238153271.013031],
               [date(2011,  9, 30), 3002.77308306347, -120848219.574606],
               [date(2012, 12, 31), 6193.68213841385, -251254215.636034],
               [date(2013, 12, 31), 1975.28122757559, -77404020.1121891]]
   for s in segments:
      if (date_ > s[0]):
         # date_ is later than this segment; proceed to next
         continue
      if (s[1] is None):
         # date_ is earlier than any segments we have; give up
         break
      # Note that we use an epoch one day earlier than the true epoch of the
      # spreadsheet, as early Excel erroneously assumed 1900 was a leap year,
      # and this bug has propagated to every later version and every Excel
      # clone. #fail
      return ((s[1] * (date_ - date(1899, 12, 30)).days + s[2])
              * 100 * sample_rate)
   # If you get this error, you could try updating tweet-volume.xls and the
   # table above. Alternately, it is worth trying an entirely different
   # approach, such as a rolling average (but keep in mind that simply running
   # the code must not depend on a large database of tweets, and no extensive
   # calculations should be done at import time).
   raise ValueError("extrapolating to %s is too scary" % (date_))

def from_json(text):
   # Skip lines containing nothing but whitespace and lines that contain just
   # a hexadecimal number. The latter arises when the tweet stream is using
   # "Transfer-Encoding: chunked" and the chunk delimeters made their way into
   # the output file (i.e., before issue #92 was fixed).
   if (re.search(r'^[0-9a-f\s]*$', text)):
      raise Nothing_To_Parse_Error()
   j = json.loads(text)  # raises ValueError on parse failure
   if ('delete' in j):
      return Deletion_Notice.from_json(j)
   elif ('limit' in j):
      return Limit_Notice.from_json(j)
   elif ('scrub_geo' in j):
      return Scrub_Geo_Notice.from_json(j)
   elif ('status_withheld' in j):
      return Status_Withheld.from_json(j)
   elif ('text' in j):
      return Tweet.from_json(j)
   elif ('warning' in j):
      return Warning.from_json(j)
   else:
      raise Unknown_Object_Error()

def is_enough(date_, count, sample_rate=0.01):
   '''Return True if count is "enough" tweets for date_, False otherwise. We
      consider there to be enough tweets for useful calculation on a given day
      if there are at least half the expected number. E.g.:

      >>> is_enough(date(2010, 1, 1), 617491)
      False
      >>> is_enough(date(2010, 1, 1), 617492)
      True

      You can also specify a sampling rate:

      >>> is_enough(date(2010, 1, 1), 61749, sample_rate=0.001)
      False
      >>> is_enough(date(2010, 1, 1), 61750, sample_rate=0.001)
      True'''
   # If you change the factor, you may want to also update tweet-volume.xls.
   return (count >= expected_count(date_, sample_rate) * 0.5)

def text_clean(t):
   '''We do three things to clean up text from the Twitter API:

        1. If the string is just "null", return None.
        2. Unescape HTML entities ("&lt;", etc.).
        3. Replace each sequence of whitespace and null characters with a
           single space.

      For example:

      >>> text_clean(u'A \\r\\n\\tB\\0C&gt;D')
      'A B C>D'
      >>> text_clean(u'null') is None
      True

      This is to ensure that all tweets play nicely with our TSV files and
      generally make parsing down the line easier.'''
   # FIXME: This method uses an undocumented method in HTMLParser, unescape().
   # See <http://stackoverflow.com/questions/2087370>.
   if (t is None or t == 'null'):
      return None
   else:
      try:
         t = HTML_PARSER.unescape(t)
      except Exception as x:
         # don't print the offending text because it could be arbitrary binary
         # goop, but that makes the problem hard to diagnose...
         u.l.warning('exception while HTML unescaping, will use None: %s' % (x))
         return None
      t = WHITESPACES_RE.sub(' ', t)
      return t


class Ignored_Object(object):

   @classmethod
   def from_json(class_, json):
      o = class_()
      return o

class Deletion_Notice(Ignored_Object): pass
class Limit_Notice(Ignored_Object): pass
class Scrub_Geo_Notice(Ignored_Object): pass
class Status_Withheld(Ignored_Object): pass
class Warning(Ignored_Object): pass


class Reader(tsv_glue.Reader):
   'Like a tsv_glue.Reader, except it emits Tweet objects, not lists.'

   def __next__(self):
      return Tweet.from_list(tsv_glue.Reader.next(self))


class Tweet(object):

   # NOTE: Tweet geotags with coordinates (0, 0) cannot be stored, because
   # these coordinates are almost certainly bogus. So, if you encounter a
   # tweet which really does have these coordinates, you are out of luck.

   __slots__ = ('tokens',
                'id',
                'created_at',
                'text',
                'user_screen_name',
                'user_description',
                'user_lang',
                'user_location',
                'user_time_zone',
                'geom',
                'geom_src')

   def __init__(self):
      self.tokens = None

   def __eq__(self, other):
      try:
         if (self.__slots__ != other.__slots__): return False
      except AttributeError:
         return False
      for attr in self.__slots__:
         if (getattr(self, attr) != getattr(other, attr)): return False
      return True

   # Short aliases for attributes. These are use in e.g. geographic inference,
   # which builds a large database of tokens. Using a short alias saves
   # significant space because they are repeated so many times.
   @property
   def tx(self): return self.text
   @property
   def ds(self): return self.user_description
   @property
   def ln(self): return self.user_lang
   @property
   def lo(self): return self.user_location
   @property
   def tz(self):
      if (self.user_time_zone is None):
         return None
      else:
         # This hack guarantees that the returned time zone is a single token.
         return NON_ALPHANUMERICS_RE.sub('', self.user_time_zone)

   @property
   def day(self):
      'String representation of the created_at day.'
      return self.created_at.strftime('%Y-%m-%d')

   @classmethod
   def from_json(class_, json):
      o = class_()
      # raw data
      o.id = json['id']
        # FIXME: This time parse routine is fairly slow (about half of the
        # total time is spent parsing dates).
      o.created_at = time_.twitter_timestamp_parse(json['created_at'])
      o.text = text_clean(json['text'])
      o.user_screen_name = text_clean(json['user']['screen_name'])
      o.user_description = text_clean(json['user']['description'])
      if ('lang' in json['user']):
         o.user_lang = text_clean(json['user']['lang'])
      else:
         o.user_lang = None
      o.user_location = text_clean(json['user']['location'])
      o.user_time_zone = text_clean(json['user']['time_zone'])
      try:
         o.geom = o.coords_to_point(json['coordinates']['coordinates'][0],
                                    json['coordinates']['coordinates'][1])
         o.geom_src = 'co'
         assert (json['coordinates']['type'] == 'Point')
      except (TypeError, KeyError):
         # json['coordinates']:
         # - isn't a dict if there's no geotag (TypeError)
         # - may not exist at all in older tweets (KeyError)
         o.geom = None
         o.geom_src = None
      return o

   @classmethod
   def from_dict(class_, dict_):
      'Given a dict representation, return the corresponding Tweet object.'
      # WARNING: Make sure this is consistent with to_dict().
      o = class_()
      o.id = dict_['tweet_id']
      o.created_at = dict_['created_at']
      o.text = dict_['text']
      o.user_screen_name = dict_['user_screen_name']
      o.user_description = dict_['user_description']
      o.user_lang = dict_['user_lang']
      o.user_location = dict_['user_location']
      o.user_time_zone = dict_['user_time_zone']
      o.geom = dict_['geom']
      o.geom_src = dict_['geom_src']
      return o

   @classmethod
   def from_list(class_, list_):
      'Given a list representation, return the corresponding Tweet object.'
      # WARNING: Make sure this is consistent with to_list() and README.
      o = class_()
      o.id = int(list_[0])
      o.created_at = time_.iso8601utc_parse(list_[1])  # FIXME: Slow? Issue #46
      o.text = list_[2]
      o.user_screen_name = list_[3]
      o.user_description = list_[4]
      o.user_lang = list_[5]
      o.user_location = list_[6]
      o.user_time_zone = list_[7]
      o.geom = o.coords_to_point(list_[8], list_[9])
      o.geom_src = list_[10]
      return o

   def coords_to_point(self, lon, lat):
      '''Given longitude and latitude, return a geos.Point object, or None if
         the coordinates are None or zero. lon and lat can be strings or
         unicodes, in which case they must be convertible to floats.'''
      if (lon is None or lat is None or (float(lon) == float(lat) == 0)):
         return None
      else:
         return geos.Point((float(lon), float(lat)), srid=u.WGS84_SRID)

   def geotagged_p(self):
      'Return true if this tweet is geotagged, false otherwise.'
      return (self.geom is not None)

   def to_dict(self):
      'Return a dictionary representation of this object.'
      # WARNING: Make sure this is consistent with README and from_dict()
      # FIXME: can we do this w/o repeating every field twice?
      return { 'tweet_id':          self.id,
               'created_at':        self.created_at,
               'text':              self.text,
               'user_screen_name':  self.user_screen_name,
               'user_description':  self.user_description,
               'user_lang':         self.user_lang,
               'user_location':     self.user_location,
               'user_time_zone':    self.user_time_zone,
               'geom':              self.geom,
               'geom_src':          self.geom_src }

   def to_list(self):
      'Return a list representation of this object.'
      # WARNING: Make sure this is consistent with README and from_list()
      # FIXME: should this be a special method of some kind?
      if (self.geom is None):
         (lon, lat) = (None, None)
      else:
         (lon, lat) = self.geom.coords
      return [ self.id,
               self.created_at.isoformat(),
               self.text,
               self.user_screen_name,
               self.user_description,
               self.user_lang,
               self.user_location,
               self.user_time_zone,
               lon,
               lat,
               self.geom_src ]

   def tokenize(self, tker, fields, unify):
      '''Tokenize given fields and set self.tokens to the resulting sequence.
         If not unify, then add a prefix to each token distinguishing which
         field it came from. E.g.:

         >>> import tok.base
         >>> tzer = tok.base.Whitespace(1)
         >>> sorted(T_TW_SIMPLE.tokenize(tzer, ['tx', 'tz'], False))
         ['tx a', 'tx b', 'tz g']
         >>> sorted(T_TW_SIMPLE.tokenize(tzer, ['tx', 'tz'], True))
         ['a', 'b', 'g']'''
      raw = tker.tokenize_all({ f: getattr(self, f) for f in fields })
      self.tokens = []
      for (field, token) in raw:
         if (unify):
            self.tokens.append(token)
         else:
            self.tokens.append(field + ' ' + token)
      return self.tokens

   def usa_p(self):
      assert False, "unimplemented"


class Writer(tsv_glue.Writer):
   'Like tsv_glue.Writer, except it takes Tweet objects instead of rows.'

   def writerow(self, tw):
      tsv_glue.Writer.writerow(self, tw.to_list())


# some test data
T_TW_SIMPLE = Tweet.from_dict({ 'tweet_id':          -1,
                                'created_at':        datetime.now(),
                                'text':              'a b',
                                'user_screen_name':  'c',
                                'user_description':  'd',
                                'user_lang':         'e',
                                'user_location':     'f',
                                'user_time_zone':    'g',
                                'geom':              None,
                                'geom_src':          None })
T_TW_JSON_CO = r'''{"text":"Guantes, bufanda, tenis y chamarra :) #Viena","id_str":"186339941163339776","contributors":null,"in_reply_to_status_id_str":null,"geo":{"type":"Point","coordinates":[48.24424304,16.37778864]},"retweet_count":0,"in_reply_to_status_id":null,"favorited":false,"in_reply_to_user_id":null,"source":"\u003Ca href=\"http:\/\/twitter.com\/#!\/download\/iphone\" rel=\"nofollow\"\u003ETwitter for iPhone\u003C\/a\u003E","created_at":"Sun Apr 01 06:31:18 +0000 2012","in_reply_to_user_id_str":null,"truncated":false,"entities":{"urls":[],"hashtags":[{"text":"Viena","indices":[38,44]}],"user_mentions":[]},"coordinates":{"type":"Point","coordinates":[16.37778864,48.24424304]},"place":{"country":"Austria","place_type":"city","url":"http:\/\/api.twitter.com\/1\/geo\/id\/9f659d51e5c5deae.json","country_code":"AT","bounding_box":{"type":"Polygon","coordinates":[[[16.182302,48.117666],[16.577511,48.117666],[16.577511,48.322574],[16.182302,48.322574]]]},"attributes":{},"full_name":"Vienna, Vienna","name":"Vienna","id":"9f659d51e5c5deae"},"in_reply_to_screen_name":null,"user":{"profile_background_color":"8B542B","id_str":"249409866","profile_background_tile":true,"screen_name":"montse_moso","listed_count":3,"time_zone":"Mexico City","profile_sidebar_fill_color":"ffffff","description":"you  It's exhausting being this Juicy \u2764","default_profile":false,"profile_background_image_url_https":"https:\/\/si0.twimg.com\/profile_background_images\/442998413\/ipod_tamborin.jpg","created_at":"Wed Feb 09 00:21:15 +0000 2011","profile_sidebar_border_color":"f03368","is_translator":false,"contributors_enabled":false,"geo_enabled":true,"url":null,"profile_image_url_https":"https:\/\/si0.twimg.com\/profile_images\/2003516916\/image_normal.jpg","follow_request_sent":null,"profile_use_background_image":true,"lang":"es","verified":false,"profile_text_color":"333333","protected":false,"default_profile_image":false,"show_all_inline_media":false,"notifications":null,"profile_background_image_url":"http:\/\/a0.twimg.com\/profile_background_images\/442998413\/ipod_tamborin.jpg","location":"","name":"Montse Alcaraz ","favourites_count":415,"profile_link_color":"9D582E","id":249409866,"statuses_count":5252,"following":null,"utc_offset":-21600,"friends_count":368,"followers_count":191,"profile_image_url":"http:\/\/a0.twimg.com\/profile_images\/2003516916\/image_normal.jpg"},"retweeted":false,"id":186339941163339776}'''
# FIXME: add test tweets for the other geotag sources


# Test-Depends: geo
testable.register('''

# Make sure we don't drop anything through all the parsing and unparsing.
>>> a = from_json(T_TW_JSON_CO)
>>> a.geom_src
'co'
>>> a.created_at
datetime.datetime(2012, 4, 1, 6, 31, 18, tzinfo=<UTC>)
>>> a.day
'2012-04-01'
>>> a == Tweet.from_list(a.to_list())
True
>>> a == Tweet.from_dict(a.to_dict())
True

''')
