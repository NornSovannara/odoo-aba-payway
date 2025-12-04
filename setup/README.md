## Run

```
docker compose up -d
```

## If you encounter db errors, initlize the database

```
docker compose run --rm odoo \
 odoo -i base -d odoo \
 --db_host=pg \
 --db_port=5432 \
 --db_user=odoo \
 --db_password=odoo123
```

## If you ecounter permission issues

```
sudo chmod -R 777 addons
sudo chmod -R 777 etc

sudo chmod -R 777 .
```
