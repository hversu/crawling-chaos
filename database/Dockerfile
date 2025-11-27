FROM postgres:15-alpine

# Copy initialization script
COPY init.sql /docker-entrypoint-initdb.d/

# Set default database name
ENV POSTGRES_DB=crawling_chaos
