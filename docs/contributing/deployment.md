## Local running

The frontend uses next.js, and runs its own server.
The following helper is provided to start both front and backend servers:

```bash
(umbrella) $ just servedev
```

To run the frontend server by itself, you can use the helper:

```bash
(umbrella) $ just frontenddev
```

or run `yarn dev` in the frontend directory.

Similarly, to run the backend django dev server by itself, you can run:
To run the frontend server by itself, you can use the helper:

```bash
(umbrella) $ just backenddev
```

### Using local mysql server

The containerized dev stack (`just devup`) already runs a MariaDB `db` service matching the deployed version — reachable on the host at `127.0.0.1:3306` (user `root`, password `devaccount`). No separate database container is needed.
To mirror the production database into it, the helper `just mirrorproddbtolocal` is provided (or `just fetchprodsnapshot` + `just loaddevdb`).

If you run the backend outside the container (bare metal), update your development `.env` to have these additional lines:

```dotenv
USE_MYSQL=True
MYSQL_NAME=production
MYSQL_USER=root
MYSQL_PWD=devaccount
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```

Your throw-away mysql instance should be reachable by cli with `mysql -h 127.0.0.1 -u root -p`. (Pw: devaccount)

## Deploying/managing company-facing servers

To interact with the local cluster and to deploy to production or staging, you'll need access to the `svc.czii.umbrella` user. See [environments page](environments.md).

### Backing up MySQL database

The following helper runs `mysqldump` on the production server, and stores it onto `/srv/dbbackups` there.

```bash
(umbrella) $ just backupdb
```

To wipe the database on staging and replace it with the most recent production backup (as generated with `just backupdb`):

```bash
(umbrella) $ just mirrorproddbtostaging
```

### Deployment to Staging/Production

To deploy to either staging or production, you can use:

```bash
(umbrella) $ just deploy <stage> <envfile> <git branch>
```

This does the following:

1.  `git clone` a shallow 1-commit branch from the remote `github.com:czimaginginstitute/czii-umbrella-django` to the server
1.  `git clone` a shallow 1-commit branch from the remote `github.com:czimaginginstitute/czii-umbrella-django` to the server
1.  `scp` the <envfile> into the server deployment directory `/srv/czii-umbrella-django`
1.  `scp` the `helpers/nginx.conf` file to server `/etc/nginx`
1.  If deploying production: Runs `just backupdb` from production, and then runs django database migrations
1.  If deploying staging: Runs `just mirrorproddbtostaging` to sync state of database to the last production backup.
1.  Builds frontend (`just updatefrontenddeps`)
1.  Builds these docs (`just updatebackenddeps`)
1.  Restarts servers (`just stopprodserve; just startprodserve`)
