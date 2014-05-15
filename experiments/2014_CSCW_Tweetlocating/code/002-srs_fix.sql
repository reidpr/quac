.headers on
.mode columns

begin;

select count(*) from spatial_ref_sys;

insert into spatial_ref_sys (srid, auth_name, auth_srid, ref_sys_name, proj4text) values (540033, 'LOCAL', 540033, 'Miller_Km', '+proj=mill +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R_A +ellps=WGS84 +datum=WGS84 +to_meter=1000 +no_defs');
insert into spatial_ref_sys (srid, auth_name, auth_srid, ref_sys_name, proj4text) values (540036, 'LOCAL', 540036, 'Miller_Mm', '+proj=mill +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R_A +ellps=WGS84 +datum=WGS84 +to_meter=1000000 +no_defs');

insert into spatial_ref_sys (srid, auth_name, auth_srid, ref_sys_name, proj4text) values (540093, 'LOCAL', 540093, 'Mollweide_Km', '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +to_meter=1000 +no_defs');
insert into spatial_ref_sys (srid, auth_name, auth_srid, ref_sys_name, proj4text) values (540096, 'LOCAL', 540096, 'Mollweide_Mm', '+proj=moll +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +to_meter=1000000 +no_defs');

select count(*) from spatial_ref_sys;

select * from spatial_ref_sys where auth_name = 'LOCAL';

select tweet_id, AsEWKT(geom) from tweet limit 3;

select tweet_id, AsEWKT(ST_Transform(geom, 54003)) from tweet limit 3;
select tweet_id, AsEWKT(ST_Transform(geom, 540033)) from tweet limit 3;
select tweet_id, AsEWKT(ST_Transform(geom, 540036)) from tweet limit 3;

select tweet_id, AsEWKT(ST_Transform(geom, 54009)) from tweet limit 3;
select tweet_id, AsEWKT(ST_Transform(geom, 540093)) from tweet limit 3;
select tweet_id, AsEWKT(ST_Transform(geom, 540096)) from tweet limit 3;

rollback;
