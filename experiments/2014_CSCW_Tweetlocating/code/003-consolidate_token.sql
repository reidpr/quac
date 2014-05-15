-- This script consolidates the field and token fields of table token into the
-- token column. In principle, it should then drop the field column, but
-- SQLite doesn't support that, so we just leave it alone.

.echo on
.load libspatialite.so
.bail on
.headers on
.mode columns
.load libspatialite.so

begin;

insert into metadata (key, value) values ('schema_version', '3');
insert into metadata (key, value) values ('ngram', '1');

create unique index metadata_pk on metadata (key);

select tweet_id, token, field from token limit 3;

-- I am pretty sure that we don't need this index, and I think it makes the
-- subsequent update slow, so drop it.
drop index token_token_idx;

update token set token = field || ' ' || token;

select tweet_id, token, field from token limit 3;

commit;
vacuum;
