-- Keep the official Ministry feed on the same hourly cadence as the worker.
update data_sources
set schedule = 'ogni ora'
where id = 'src-ministero-rss';
