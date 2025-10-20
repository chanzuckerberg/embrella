
## MkDocs
Manual documentation for the project is in `/docs` and uses MkDocs. 

The following helper is provided to run a local live-reload server:

```bash
(umbrella) $ just servedocs
```

These are hosted upon deployment to production or staging at:

 * [http://umbrella.czbiohub.org/docs/](http://umbrella.czbiohub.org/docs/)
 * [http://umbrella-dev.czbiohub.org/docs/](http://umbrella-dev.czbiohub.org/docs/)

## API Documentation
API documentation is based on swagger annotation within the API view code, and are served at:

 * [http://umbrella.czbiohub.org/api/docs/](http://umbrella.czbiohub.org/api/docs/)
 * [http://umbrella-dev.czbiohub.org/api/docs/](http://umbrella-dev.czbiohub.org/api/docs/)

Alternatively:

 * [http://umbrella.czbiohub.org/api/redocs/](http://umbrella.czbiohub.org/api/redocs/)
 * [http://umbrella-dev.czbiohub.org/api/redocs/](http://umbrella-dev.czbiohub.org/api/redocs/)