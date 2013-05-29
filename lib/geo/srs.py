'''This module contains various geographic utilities related to spatial
   reference systems.'''

# Copyright (c) 2012-2013 Los Alamos National Security, LLC, and others.


from __future__ import division

import io
import json
import re
import sys

from django.contrib.gis import geos
from django.contrib.gis import gdal
import numpy as np
import pyproj

import testable
import u


### Custom spatial reference systems ###

class Magic_SRS_Dict(dict):
   '''This class is a hack to make custom spatial reference systems available
      to Python code. The basic idea is: we look like a dict, and lookups are
      by SRID; values are gdal.SpatialReference objects. The reason we return
      such objects is to avoid repeatedly parsing PROJ4 strings for our custom
      SRSes. Example:

        >>> srs = Magic_SRS_Dict()
        >>> srs[4326].srid
        4326
        >>> srs[540036].srid
        540036
        >>> srs[540036].name
        u'Miller_Mm'
        >>> srs[540036].proj
        u'+proj=mill +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R_A +ellps=WGS84 +towgs84=0,0,0,0,0,0,0 +to_meter=1000000 +no_defs '
   '''

   def __init__(self):
      for (srid, (name, proj4)) in CUSTOM_SRS.iteritems():
         # An explanation of the extreme fail here. SpatialReference objects
         # created from proj4 text get a name of "unnamed" and an SRID of
         # 4326, and there's nothing you can do about it (the relevant
         # attributes are read-only). Our solution is to create an object,
         # dump its WKT, munge that, and create a new object (can't switch to
         # WKT because SpatiaLite doesn't grok it). Excuse me while I vomit.
         wkt = gdal.SpatialReference(proj4).wkt
         wkt = re.sub(r'unnamed', name, wkt)
         wkt = re.sub(r'AUTHORITY\["EPSG","4326"\]',
                      'AUTHORITY["LOCAL","%d"]' % (srid), wkt)
         self[srid] = gdal.SpatialReference(wkt)

   def __getitem__(self, key):
      try:
         return dict.__getitem__(self, key)
      except KeyError:
         self[key] = gdal.SpatialReference(key)
         return self[key]

CUSTOM_SRS = {
   # FIXME: If you need a km- or Mm-based version of a meter-based SRS with
   # SRID=x, number the new one x*10+3 or x*10+6, respectively. There is code
   # that relies on this numbering scheme in base.py.

   # no proj4 on spatialreference.org for EPSG 32663; omitted
   54003:  ('Miller',       '+proj=mill +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R_A +ellps=WGS84 +datum=WGS84 +units=m +no_defs'),
   540033: ('Miller_Km',    '+proj=mill +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R_A +ellps=WGS84 +datum=WGS84 +to_meter=1000 +no_defs'),
   540036: ('Miller_Mm',    '+proj=mill +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R_A +ellps=WGS84 +datum=WGS84 +to_meter=1000000 +no_defs'),
   54009:  ('Mollweide',    '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'),
   540093: ('Mollweide_Km', '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +to_meter=1000 +no_defs'),
   540096: ('Mollweide_Mm', '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +to_meter=1000000 +no_defs'),
}

SRS = Magic_SRS_Dict()
SRID_WGS84 = u.WGS84_SRID  # FIXME: eliminate redundant definition
SRS_WGS84 = SRS[SRID_WGS84]
SRID_EQAREA = 54009  # Mollweide. Units must be meters.
SRS_EQAREA = SRS[SRID_EQAREA]


### Geodesic computations ###

GEOD = pyproj.Geod(ellps='WGS84')
EARTH_RADIUS_KM = 6371.009 # http://en.wikipedia.org/wiki/Earth_radius
DEG2RAD = 0.017453293

# We have a couple of options for computing geodesic distances. We can use an
# ellipsoidal computation, which is accurate but slow (with the libraries we
# are using), or a spherical one, which is faster and can operate on vectors
# but is less accurate (up to about 0.3% error). Set the aliases below to
# choose which you prefer.

def geodesic_distance_ell(a, b):
   '''Return the ellipsoidal geodesic distance in kilometers from geos.Point a
      to geos.Point b, which can be in any SRS. For example, to compute
      distance from BNA to LAX
      (http://en.wikipedia.org/wiki/Great-circle_distance):

      >>> geodesic_distance_ell(geos.Point(-86.67, 36.12, srid=4326),
      ...                       geos.Point(-118.40, 33.94, srid=4326))
      2892.77...'''
   return geodesic_distance_mp_ell(a, geos.MultiPoint([b], srid=b.srid))[0]

def geodesic_distance_sph(a, b):
   '''Return the spherical geodesic distance in kilometers from geos.Point a
      to geos.Point b. E.g. (this is in error by about 0.2%):

      >>> geodesic_distance_sph(geos.Point(-86.67, 36.12, srid=4326),
      ...                       geos.Point(-118.40, 33.94, srid=4326))
      2886.44...'''
   return geodesic_distance_mp_sph(a, geos.MultiPoint([b], srid=b.srid))[0]

def geodesic_distance_mp_ell(a, b):
   a = transform(a, SRID_WGS84)
   b = transform(b, SRID_WGS84)
   dist_m = np.array([GEOD.inv(a.x, a.y, bx, by)[2] for (bx, by) in b.coords])
   return dist_m / 1000

def geodesic_distance_mp_sph(a, b):
   # Formula from <http://williams.best.vwh.net/avform.htm#Dist>.
   def c2as(seq):
      xys = DEG2RAD * np.array(seq)
      return (xys[:,0], xys[:,1])
   assert (a.geom_type == 'Point' and b.geom_type == 'MultiPoint')
   a = transform(a, SRID_WGS84)
   b = transform(b, SRID_WGS84)
   (alon, alat) = c2as([a.coords] * len(b))
   (blon, blat) = c2as(b.coords)
   return (EARTH_RADIUS_KM
           * 2 * np.arcsin(np.sqrt((np.sin((alat - blat) / 2))**2
                                   + (np.cos(alat) * np.cos(blat)
                                      * (np.sin((alon - blon) / 2))**2))))

geodesic_distance = geodesic_distance_sph
geodesic_distance_mp = geodesic_distance_mp_sph

def geodesic_area(p):
   '''Return the geodesic area of Polygon or MultiPolygon p in km^2. This
      simply projects to an equal-area projection and then computes the
      geometric area; a notable alternative is the Chamberlain & Duquette
      formula. For example, to compute the approximate area of Colorado:

        >>> co = geos.Polygon([(-109.05, 41), (-102.05, 41), (-102.05, 37),
        ...                    (-109.05, 37), (-109.05, 41)], srid=4326)
        >>> geodesic_area(co)
        269492.44...

      Wikipedia says the area is 269,837 km^2, so we're off by about 0.1%.'''
   if (p.geom_type == 'Polygon'):
      mp = geos.MultiPolygon([p])
   elif (p.geom_type == 'MultiPolygon'):
      mp = p
   else:
      raise TypeError('need Polygon or MultiPolygon, not %s' % (p.geom_type))
   return (transform(p, SRID_EQAREA).area / 1e6)


### Transforming from one SRS to another ###

TRANSFORMERS = {}

def transform(geom, srid, always_copy=False):
   '''Return geom transformed to SRID srid. The returned object may be geom
      itself, if no transformation is needed, unless always_copy==True, in
      which case a copy is always made.'''
   # NOTE: This function works around a Django bug that prevents transforming
   # from a custom SRID (https://code.djangoproject.com/ticket/19171). The
   # workaround is to set a fake SRID on the source object, do the
   # transformation, and the put the real SRID back.
   if (geom.srid == srid and not always_copy):
      return geom
   try:
      ct = TRANSFORMERS[(geom.srid, srid)]
   except KeyError:
      ct = gdal.CoordTransform(SRS[geom.srid], SRS[srid])
      TRANSFORMERS[(geom.srid, srid)] = ct
   source_srid_real = geom.srid
   geom.srid = SRID_WGS84
   result = geom.transform(ct, clone=True)
   geom.srid = source_srid_real
   return result


### Trimming geometries that slop off the globe ###

LATMAX = 89.99
LATMIN = -LATMAX
LONMAX = 180
LONMIN = -LONMAX
LON_BUFFER = 12

@u.memoize
def bounding_box_srid(srid):
   '''Return a bounding box for given SRID as a polygon in that SRID. E.g.:

      >>> bounding_box_srid(54003).coords
      (((240181312.2..., -14671436.0...), (240181312.2..., 14671436.0...), (-240181312.2..., 14671436.03...), (-240181312.2..., -14671436.0...), (240181312.2..., -14671436.0...)),)'''
   (xmin, xmax) = lon_bounds_srid(srid)
   (ymin, ymax) = lat_bounds_srid(srid)
   return geos.Polygon([(xmin, ymin), (xmin, ymax), (xmax, ymax),
                        (xmax, ymin), (xmin, ymin)], srid=srid)

def inbounds_p(geom):
   '''Return True if geom is entirely in-bounds (i.e., geom == trim(geom)),
      False otherwise. For example:

      >>> inbounds_p(geos.Point(0, 90.1, srid=SRID_WGS84))
      False'''
   assert (geom.geom_type == 'Point'), 'untested for non-Points'
   (s, n) = lat_bounds_srid(geom.srid)
   return (geom.extent[1] > s and geom.extent[3] < n)

@u.memoize
def lat_bounds_srid(srid):
   '''Return a tuple containing the Y coordinates of the (south, north) poles.
      For example:

      >>> lat_bounds_srid(4326)
      (-89.99, 89.99)
      >>> lat_bounds_srid(54003)
      (-14671436.0..., 14671436.0...)'''
   return (transform(geos.Point(0, LATMIN, srid=SRID_WGS84), srid).y,
           transform(geos.Point(0, LATMAX, srid=SRID_WGS84), srid).y)

@u.memoize
def lon_bounds_srid(srid):
   '''Return a tuple containing the X coordinates of the (west, east)
      "boundaries" of the given SRID. This is a little arbitrary, because
      there's no boundary (all the trigonometry works fine even if you go
      around and around the world), but it's useful to be able to make a
      boundary rectangle. Thus, we add a generous buffer.'''
   xmin = transform(geos.Point(LONMIN, 0, srid=SRID_WGS84), srid).x
   xmax = transform(geos.Point(LONMAX, 0, srid=SRID_WGS84), srid).x
   return (xmin * LON_BUFFER, xmax * LON_BUFFER)

def trim(geom):
   '''Given geometry geom in any SRS, remove any portions that extend off the
      globe (i.e., latitude further north than the North Pole or south than
      the South Pole) and return what's left. E.g.:

      # 90 degrees latitude is roughly 14,675,057 meters in this SRS
      >>> y = 15e6  # latitude
      >>> x = 10e6  # longitude
      >>> pl = geos.Polygon([(0,y), (x,0), (0,-y), (-x,0), (0,y)], srid=54003)
      >>> trim(pl).coords
      (((-219042.6..., 14671436.0...), (219042.6..., 14671436.0...), (10000000.0, 0.0), (219042.6..., -14671436.0...), (-219042.6..., -14671436.0...), (-10000000.0, 0.0), (-219042.6..., 14671436.0...)),)

      WARNING: This function only works correctly on projections with straight
      lines of latitude. E.g., azimuthal and conic projections will silently
      return incorrect results. (FIXME: add an assertion for this.)

      (FIXME: This doesn't test that the returned geometry makes any sense, is
      not null, or is valid.)'''
   # This actually requires a little finesse. If one defines a "trim polygon"
   # in WGS84, it can only extend to +/- 180 degrees longitude if we are to
   # transform it correctly to geom's SRS. On the other hand, geom can't be
   # transformed to WGS84 because (by definition) it may contain vertices
   # invalid in WGS84. So, we do more focused transformation of components.
   return bounding_box_srid(geom.srid).intersection(geom)


### Input and output ###

def dump_geojson(basename, geoms):
   '''Write a GeoJSON representation of geoms (transformed to WGS84, and
      cannot be a GeometryCollection because mixed types in a layer are
      unsupported in QGIS) to the file basename.geojson.'''
   assert (geoms.geom_type != 'GeometryCollection')
   d = { 'type': 'FeatureCollection',
         'crs': { 'type': 'name',
                  'properties': { 'name': 'EPSG:%d' % (SRID_WGS84) } },
         'features': [] }
   geoms = transform(geoms, SRID_WGS84)
   if (geoms.num_geom == 1):
      geoms = geos.GeometryCollection([geoms])
   for geom in geoms:
      # FIXME: It is super lame that we can't get a datastructure instead of a
      # JSON string from geometries.
      d['features'].append({ 'type': 'Feature',
                             'properties': {},
                             'geometry': json.loads(geom.json) })
      # can't dump directly to file b/c "TypeError: must be unicode, not str"
      json_ = json.dumps(d, ensure_ascii=False, indent=2)
      assert (isinstance(json_, unicode))
      fp = io.open(basename + '.geojson', mode='wt', encoding='utf8')
      fp.write(json_)


### Tests ###

testable.register('''

# Make sure the SRIDs we're interested in are available.
>>> for srid in (4326, 54003, 540033, 540036, 54009, 540093, 540096):
...   if not isinstance(SRS[srid], gdal.SpatialReference): srid

# Test that we can transform to and from the custom SRSes.
>>> a = geos.Point(1, 2, srid=SRID_WGS84)
>>> b = transform(a, 540036)
>>> a.srid
4326
>>> b.coords
(0.111..., 0.220...)
>>> b.srid
540036
>>> c = transform(b, 4326)
>>> c.srid
4326
>>> [round(x, 4) for x in c.coords]
[1.0, 2.0]

# geodesic_area() should except if we give it a bogus geometry type.
>>> geodesic_area(geos.Point(0,0))
Traceback (most recent call last):
  ...
TypeError: need Polygon or MultiPolygon, not Point

# inbounds_p() should work north/sound and on SRS that requires transform
>>> inbounds_p(geos.Point(0, 89.98, srid=SRID_WGS84))
True
>>> inbounds_p(geos.Point(0, 90.01, srid=SRID_WGS84))
False
>>> inbounds_p(geos.Point(0, -89.98, srid=SRID_WGS84))
True
>>> inbounds_p(geos.Point(0, -90.01, srid=SRID_WGS84))
False
>>> inbounds_p(geos.Point(0, 14671436.0, srid=54003))
True
>>> inbounds_p(geos.Point(0, 14671436.1, srid=54003))
False
>>> inbounds_p(geos.Point(0, -14671436.0, srid=54003))
True
>>> inbounds_p(geos.Point(0, -14671436.1, srid=54003))
False

# Ensure that trim() works on multipolygons.
>>> yo = 15e6
>>> yi = 14e6
>>> mp = geos.MultiPoint([geos.Point(0, yi), geos.Point(0, yo)], srid=54003)
>>> trim(mp).coords
(0.0, 14000000.0)

''')
