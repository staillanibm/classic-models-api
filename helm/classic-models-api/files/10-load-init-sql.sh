log_info 'Loading classicmodels sample data (01-init.sql) ...'
mysql ${mysql_flags} < "${APP_DATA}/mysql-init/01-init.sql"
