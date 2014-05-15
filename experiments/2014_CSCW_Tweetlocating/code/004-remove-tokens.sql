-- This script removes the token table and associated stuff. Tokenization now
-- all happens in model-test.

.echo on
.bail on
.headers on
.mode columns
.load libspatialite.so

begin;

update metadata set value = '4' where key = 'schema_version';

delete from metadata where key = 'ngram';
delete from metadata where key = 'tokenizer';

drop table token;

commit;
vacuum;
