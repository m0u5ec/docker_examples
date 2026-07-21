#!/bin/bash
set -e

# Создаем вторую БД, используя переменную POSTGRES_DB2
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE $POSTGRES_DB2;
EOSQL
