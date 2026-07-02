During local development, local web servers on ports 8000 and 3000 are run, and a sqlite file database is used for prototyping.

For release and testing in a production setting, there are two company-facing servers for Umbrella:

- https://umbrella-dev.czbiohub.org - Referred to as "Staging", run pre-release deployments for testing.
- https://umbrella.czbiohub.org - Referred to as "Production", runs production releases for company use.

MySQL servers are used for the backend database on staging and production.

Each of these contexts (development, staging, production) have secrets/settings specific to them, and those are stored in a local `key=val` file called `.env`.
The `key=val` pairs become environment variables accessible by the backend servers.

As there's sensitive information in the `.env` file, it's not version controlled.

The following `just` helpers are provided to help instantiate/synchronize your `.env` file.

## .env files

### Creating from empty template

To create a new `.env` file, you can use:

```bash
(umbrella) $ just initenv
```

This copies `helpers/.env_template` to `.env` if `.env` is not present. Open up `.env`, and fill in the values for each key.

### Securely shared .env files

For the following, you need to have the github CLI (`gh`) installed, and you should be authenticated to it.

Github provides named environment level variables for the repo, and they're used here as a rudimentary secrets-manager to store the encrypted `.env` file contents.

The encryption used is AES-256-CBC with PBKDF2, and you'll need to be given the password(s) to decrypt these.

Additionally, you'll need to be granted read access to the repo's github variables. (And write access, if you're going to update them.)

#### Retrieving an env:

```bash
(umbrella) $ just restoreencryptedenv development
You are about to overwrite the local file ./.env with contents from remote environment for staging...
Are you sure? ([y]es or [N]o): y
Are you *really* sure? ([y]es or [N]o): y
Password for decrypt:
```

#### Storing an env to a gh variable:

```bash
just backupencryptedenv staging
You are about to overwrite the remote environment for staging with the contents of ./.env...
Are you sure? ([y]es or [N]o): y
Are you *really* sure? ([y]es or [N]o): y
Password for encrypt:
✓ Updated variable ENV for chanzuckerberg/embrella environment staging
```

## svc.czii.umbrella service user

To deploy to either staging or production, you'll need to be given credentials for user `svc.czii.umbrella`.

This helper will retrieve that. (Password protected.)

```bash
(umbrella) $ just getserviceuserkey
```

Test that it works:

```bash
(umbrella) $ ssh svc.czii.umbrella@umbrella-dev
[svc.czii.umbrella@umbrella-dev ~]$ exit
```

For reference, these endpoints need to have the public key added should you replace that key:

```bash
(umbrella) $ ssh-copy-id -i ~/.ssh/svc_czii_umbrella svc.czii.umbrella@umbrella.czbiohub.org
(umbrella) $ ssh-copy-id -i ~/.ssh/svc_czii_umbrella svc.czii.umbrella@umbrella-dev.czbiohub.org
(umbrella) $ ssh-copy-id -i ~/.ssh/svc_czii_umbrella svc.czii.umbrella@czii-login-1.czbiohub.org
(umbrella) $ ssh-copy-id -i ~/.ssh/svc_czii_umbrella svc.czii.umbrella@login01.czbiohub.org
```
