#!/usr/bin/env bash

set -u   # crash on missing environment variables
set -e   # stop on any error
set -x   # log every command.

source /deploy/wait-for-it.sh

# load data in database
python manage.py migrate
# Do full import. Delete all data

if [ "$BOUWDOSSIERS_OBJECTSTORE_CONTAINER" = "dossiers_acceptance" ]
then
   python manage.py run_import --delete --skip_validate_import
else
   python manage.py run_import --delete --min_bouwdossiers_count ${MIN_BOUWDOSSIERS_COUNT}
fi