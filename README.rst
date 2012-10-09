EU Subsidies for Agriculture in Romania
=======================================

Demo: http://agripay.gerty.grep.ro/
Source code: https://github.com/mgax/agripay


Importing the data
------------------
1. Get CSV files from http://apdrp.ro/content.aspx?item=2030&lang=RO

2. Import a CSV file into the application's database and a geojson file::

    $ ./manage.py group_by_comuna < raw/plati_fega_feadr-2010.csv > maps/money_per_comuna.geojson

3. Convert the geojson file into a spatialite database::

    $ ogr2ogr -f sqlite -overwrite maps/money_per_comuna.db maps/money_per_comuna.geojson


Copyright (c) 2012, The Hackers
