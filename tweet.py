# Classes to represent objects found in tweet streams.

from datetime import datetime
import dateutil.parser
import HTMLParser
import json
import pytz
import re

from django.contrib.gis import geos

import testable
import time_
import tsv_glue
import u


HTML_PARSER = HTMLParser.HTMLParser()
LOCAL_TZ = None
NON_ALPHANUMERICS_RE = re.compile(r'[\W_]+')
WHITESPACES_RE = re.compile(r'\s+')

class Unknown_Object_Error(Exception): pass


def init_timezone(tz):
   '''Set the time zone for computing day boundaries. This is only needed if
      parsing tweets from JSON.'''
   global LOCAL_TZ
   LOCAL_TZ = pytz.timezone(tz)


def from_json(text):
   j = json.loads(text)  # raises ValueError on parse failure
   if ('text' in j):
      return Tweet.from_json(j)
   elif ('delete' in j):
      return Deletion_Notice.from_json(j)
   elif ('status_withheld' in j):
      return Status_Withheld.from_json(j)
   else:
      raise Unknown_Object_Error()

def text_clean(t):
   '''We do three things to clean up text from the Twitter API:

        * If the string is just "null", return None.
        * Unescape HTML entities ("&lt;", etc.).
        * Replace all sequences of whitespace with a single space.

      This is to ensure that all tweets play nicely with our TSV files and
      generally make parsing down the line easier.'''
   # FIXME: This method uses an undocumented method in HTMLParser, unescape().
   # See <http://stackoverflow.com/questions/2087370>.
   if (t is None or t == 'null'):
      return None
   else:
      try:
         t = HTML_PARSER.unescape(t)
      except Exception, x:
         # don't print the offending text because it could be arbitrary binary
         # goop, but that makes the problem hard to diagnose...
         u.l.warning('exception while HTML unescaping, will use None: %s' % (x))
         return None
      t = WHITESPACES_RE.sub(' ', t)
      return t


class Deletion_Notice(object):

   # FIXME: implement

   @classmethod
   def from_json(class_, json):
      o = class_()
      return o


class Status_Withheld(object):

   # FIXME: implement??? or just ignore...

   @classmethod
   def from_json(class_, json):
      o = class_()
      return o


class Reader(tsv_glue.Reader):
   'Like a tsv_glue.Reader, except it emits Tweet objects, not lists.'

   def next(self):
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
                'day',
                'hour')

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
      if (json['user'].has_key('lang')):
         o.user_lang = text_clean(json['user']['lang'])
      else:
         o.user_lang = None
      o.user_location = text_clean(json['user']['location'])
      o.user_time_zone = text_clean(json['user']['time_zone'])
      try:
         o.geom = o.coords_to_point(json['coordinates']['coordinates'][0],
                                    json['coordinates']['coordinates'][1])
         assert (json['coordinates']['type'] == 'Point')
      except (TypeError, KeyError):
         # json['coordinates']:
         # - isn't a dict if there's no geotag (TypeError)
         # - may not exist at all in older tweets (KeyError)
         o.geom = None
      # derived data
      localtime = o.created_at.astimezone(LOCAL_TZ)
      assert not localtime.dst()
      o.day = localtime.strftime('%Y-%m-%d')
      o.hour = int(localtime.strftime('%H'))
      return o

   @classmethod
   def from_dict(class_, dict_):
      'Given a dict representation, return the corresponding Tweet object.'
      # WARNING: Make sure this is consistent with to_dict().
      o = class_()
      o.id = dict_['tweet_id']
      o.created_at = dict_['created_at']
      o.day = dict_['day']
      o.hour = dict_['hour']
      o.text = dict_['text']
      o.user_screen_name = dict_['user_screen_name']
      o.user_description = dict_['user_description']
      o.user_lang = dict_['user_lang']
      o.user_location = dict_['user_location']
      o.user_time_zone = dict_['user_time_zone']
      o.geom = dict_['geom']
      return o

   @classmethod
   def from_list(class_, list_):
      'Given a list representation, return the corresponding Tweet object.'
      # WARNING: Make sure this is consistent with to_list() and README.
      o = class_()
      o.id = int(list_[0])
      o.created_at = time_.iso8601utc_parse(list_[1])  # FIXME: Slow
      o.day = list_[2]
      o.hour = int(list_[3])
      o.text = list_[4]
      o.user_screen_name = list_[5]
      o.user_description = list_[6]
      o.user_lang = list_[7]
      o.user_location = list_[8]
      o.user_time_zone = list_[9]
      o.geom = o.coords_to_point(list_[10], list_[11])
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
               'day':               self.day,
               'hour':              self.hour,
               'text':              self.text,
               'user_screen_name':  self.user_screen_name,
               'user_description':  self.user_description,
               'user_lang':         self.user_lang,
               'user_location':     self.user_location,
               'user_time_zone':    self.user_time_zone,
               'geom':              self.geom }

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
               self.day,
               self.hour,
               self.text,
               self.user_screen_name,
               self.user_description,
               self.user_lang,
               self.user_location,
               self.user_time_zone,
               lon,
               lat ]

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
                                'day':               '20130118',
                                'hour':              '15',
                                'text':              'a b',
                                'user_screen_name':  'c',
                                'user_description':  'd',
                                'user_lang':         'e',
                                'user_location':     'f',
                                'user_time_zone':    'g',
                                'geom':              None })
T_TW_JSON = u'{"text":"@01mlkqstronda_ @v70_M34M4R pode cr\u00e9 se ela qser envia ne","id_str":"186339928593018880","contributors":null,"in_reply_to_status_id_str":"186339780995452929","geo":null,"retweet_count":0,"in_reply_to_status_id":186339780995452929,"favorited":false,"in_reply_to_user_id":397382377,"source":"web","created_at":"Sun Apr 01 06:31:15 +0000 2012","in_reply_to_user_id_str":"397382377","truncated":false,"entities":{"urls":[],"hashtags":[],"user_mentions":[{"indices":[0,15],"screen_name":"01mlkqstronda_","id_str":"397382377","name":"Emo Do Ax\u00e9 e Funk  \u2665","id":397382377},{"indices":[16,27],"screen_name":"v70_M34M4R","id_str":"415136346","name":"M\u0197\u0197N\u0394F\u0394K3D\u00d8\u0197 :3 \u221e","id":415136346}]},"coordinates":null,"place":null,"in_reply_to_screen_name":"01mlkqstronda_","user":{"profile_background_color":"BADFCD","id_str":"510589263","profile_background_tile":false,"screen_name":"1AlexFernando","listed_count":0,"time_zone":null,"profile_sidebar_fill_color":"C0DFEC","description":"La pa lapa Com meus parc\u00e9iros .\u266b TATUQUARACITY ","default_profile":false,"profile_background_image_url_https":"https:\/\/si0.twimg.com\/profile_background_images\/476593884\/this-is-my-element-212288.jpeg","created_at":"Thu Mar 01 17:46:35 +0000 2012","profile_sidebar_border_color":"a8c7f7","is_translator":false,"contributors_enabled":false,"geo_enabled":true,"url":null,"profile_image_url_https":"https:\/\/si0.twimg.com\/profile_images\/1987399794\/SDC13097_normal.JPG","follow_request_sent":null,"profile_use_background_image":true,"lang":"pt","verified":false,"profile_text_color":"333333","protected":false,"default_profile_image":false,"show_all_inline_media":false,"notifications":null,"profile_background_image_url":"http:\/\/a0.twimg.com\/profile_background_images\/476593884\/this-is-my-element-212288.jpeg","location":"CWBROOKLIN,1995 ","name":"V\u00c7 V\u00c7 V\u00c7 V\u00c7 V\u00c7 QUER?","favourites_count":0,"profile_link_color":"FF0000","id":510589263,"statuses_count":2947,"following":null,"utc_offset":null,"friends_count":64,"followers_count":101,"profile_image_url":"http:\/\/a0.twimg.com\/profile_images\/1987399794\/SDC13097_normal.JPG"},"retweeted":false,"id":186339928593018880}'


testable.register(u'''

# Make sure we don't drop anything through all the parsing and unparsing.
>>> init_timezone('UTC')
>>> a = from_json(T_TW_JSON)
>>> a == Tweet.from_list(a.to_list())
True
>>> a == Tweet.from_dict(a.to_dict())
True

''')
