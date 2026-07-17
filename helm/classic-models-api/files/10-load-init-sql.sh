already_loaded=$(mysql ${mysql_flags} --skip-column-names -e \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='classicmodels' AND table_name='productlines'")

if [ "${already_loaded}" = "1" ]; then
  log_info 'classicmodels sample data already loaded, skipping 01-init.sql'
else
  log_info 'Loading classicmodels sample data (01-init.sql) ...'
  mysql ${mysql_flags} < "${APP_DATA}/mysql-init/01-init.sql"
fi
