# Projections of note. See:
#   - http://www.spatialreference.org/
#   - http://www.radicalcartography.net/?projectionref
#   - http://en.wikipedia.org/wiki/List_of_map_projections
#
#  4326 - WGS84 geodetic system (not a projection)
# 32663 - Plate Carree <http://en.wikipedia.org/wiki/Equirectangular_projection>
#  3395 - Mercator <http://en.wikipedia.org/wiki/Mercator_projection>
# 54003 - Miller <http://en.wikipedia.org/wiki/Miller_projection>
# 54009 - Mollweide <http://en.wikipedia.org/wiki/Mollweide_projection>
#       - Goode <http://en.wikipedia.org/wiki/Goode_homolosine_projection> [1]
#
# [1]: tricky because it is interrupted

# install Django 1.4 with pip

from django.contrib.gis import geos

def transform(x, y):
   a = geos.Point((x, y), srid=4326)
   print 'WGS84:  (lon = %f, lat = %f)' % (a.coords[0], a.coords[1])
   b = a.transform(54003, clone=True)
   print 'Miller: (x = %f, y = %f)' % (b.coords[0], b.coords[1])

transform(0, 0)
transform(-106.297778, 35.891111)
