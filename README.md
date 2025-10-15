# TEMPLATE

Project template description comes here. 

## DEVELOPMENT PROCESS

### Pre-Commit
Pre-Commit has been installed into this repository as a dependency. In order for the developer to install it as local webhook in the local git repository the developer should execute the following command inside the project's virtual environment:

```
  pre-commit install
```

### Database model (DDL)
For th API to be fully operational is best to create a minimal databae with a single table so evevery endpoint will work as expected.

The database DDL can be obtained from file [ [database_ddl.sql](resources/database_ddl.sql) ] or you can simply use the in-line version that follows:

```
create table templates
(
    tidx        serial
        constraint templates_pk
            primary key,
    templateid  uuid      default gen_random_uuid() not null,
    name        varchar   default ''::character varying,
    description varchar   default ''::character varying,
    content     varchar   default ''::character varying,
    created     timestamp default now(),
    modified    timestamp default now()
);

alter table templates
    owner to root;
```


### Environment variables and database migrations
Create a `.env` file in the project root directory with the configuration variables for databse, among other variables that might also exist there:

```
# -- Use: Flask configuration
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_HOST=localhost
FLASK_PORT=9000

# -- Secret key
FLASK_SECRET_KEY="Sup3rC0mpl3xS3cr3tK3y"

# -- Log level
FLASK_LOG_LEVEL=DEBUG

# -- Postgres configuration
DB_ENGINE=pg
DB_USER=root
DB_PASS=password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mypkg

# -- Redis configuration
REDIS_HOST=localhost
REDIS_PORT=5432
REDIS_PASS=password
REDIS_DB=0
REDIS_MAX_CONN=50

# -- Rate limit settings (connections per minute)
DEFAULT_RATE_LIMIT=10

# -- Enable or disable Prometheus metrics
PROMETHEUS_ENABLED=False

# -- Use: Gunicorn configuration
GUNIPORT=9000
```

## DEVELOPMENT PROCESS

In  order adecquately test the API there is a resource in the `resources` folder to import into `Insomnia` (by Kong&#8482; ) or `Postman`&#8482;. It's a JSON file with all the endpoints preconfigured according to the OpenAPI 3 specification. 

The file is [ [insomnia_project.json](resources/insomnia_project.json) ]. 

