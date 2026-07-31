#!/bin/bash
set -e

# Create replication user for PostgreSQL Streaming Replication
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'replicator_secure_pass_123';
EOSQL

# Append host replication entry to pg_hba.conf
echo "host replication replicator 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
