# encoding: utf-8
import sys
import os
import csv
from collections import defaultdict
from pprint import pprint as pp
import math
import flask
from peewee import Model, CharField, DecimalField, SqliteDatabase
from path import path
import geojson
import flatkit.datatables
from utils import html_unescape


db = SqliteDatabase(None, autocommit=False, threadlocals=True)

refdata = path(__file__).parent / 'refdata'

EPSG_31700_CRS = {
    "type": "name",
    "properties": {
        "name": "urn:ogc:def:crs:EPSG::31700",
    },
}


class Record(Model):
    name = CharField()
    code = CharField()
    town = CharField()
    total = DecimalField()
    norm_localitate = CharField()

    class Meta:
        database = db


class DatabasePlugin(object):

    def initialize(self, app):
        db_path = os.environ.get('DATABASE_PATH')
        if db_path is None:
            db_path = path(app.instance_path) / 'db.sqlite'
        Record.Meta.database.init(db_path)
        app.extensions['agripay_database'] = self


queries = flask.Blueprint('queries', __name__)


@queries.route('/')
def index():
    return flask.render_template('index.html')


@queries.route('/table')
def table():
    query = Record.select('sum(total) as s')
    localitate = flask.request.args.get('localitate')
    if localitate is not None:
        query = query.where(Record.norm_localitate==localitate)
    stats = {
        'sum(total)': query.get().s,
    }
    towns = [r.town for r in Record.select('distinct(town) as town')]
    return flask.render_template('table.html', **{
        'stats': stats,
        'towns': sorted(towns),
        'localitate': localitate,
    })


class RecordFilter(flatkit.datatables.FilterView):

    def query(self, options):
        select = Record.select()
        localitate = flask.request.args.get('localitate')
        if localitate is not None:
            select = select.where(Record.norm_localitate==localitate)

        order_by = options.get('order_by')
        if order_by:
            select = select.order_by(order_by)

        if options['limit']:
            select = select.limit(options['limit'])
        if options['offset']:
            select = select.offset(options['offset'])

        if options['count']:
            return select.count()

        else:
            return [{
                'name': r.name,
                'code': r.code,
                'town': r.town,
                'total': float(r.total),
            } for r in select]


queries.add_url_rule('/dt_query', view_func=RecordFilter.as_view('dt_query'))


def ascify(text):
    return text.decode('utf-8') \
               .replace(u'Ș', 'S') \
               .replace(u'Â', 'A') \
               .replace(u'Ă', 'A') \
               .replace(u'Ț', 'T')


def read_localities():
    columns = ['code', '1', 'judet', 'judet_code',
               'name', 'name_ascii', 'x', 'y']
    with (refdata / 'comune.txt').open('rb') as f:
        for row in csv.DictReader(f, columns):
            row['judet_ascii'] = ascify(row['judet'])
            yield row



def read_and_clean_csv(f):
    head = next(f).strip().split(';')
    for i, line in enumerate(f):
        row = line.strip().rsplit(';', 7)
        assert len(head) == len(row), 'line %d: %r' % (i, row)
        rowdict = dict(zip(head, row))
        data = {
            'name': rowdict['Denumire beneficiar'].decode('utf-8'),
            'code': rowdict['Cod unic'],
            'town': rowdict['Localitate'].decode('utf-8'),
            'total': rowdict['Total plati'],
        }
        yield data


def register_commands(manager):

    @manager.command
    def create_all():
        Record.create_table(fail_silently=True)

    @manager.command
    def drop_all():
        Record.drop_table(fail_silently=True)

    @manager.command
    def clean_csv():
        header = ['name', 'code', 'town', 'total']
        out = csv.writer(sys.stdout)
        out.writerow(header)
        for data in read_and_clean_csv(sys.stdin):
            out.writerow([data['name'].encode('utf-8'),
                          data['code'], data['town'], data['total']])

    @manager.command
    def load_apdrp_csv():
        with db.transaction():
            for data in read_and_clean_csv(sys.stdin):
                record = Record.create(**data)
            db.commit()

    @manager.command
    def dump_csv():
        out = csv.writer(sys.stdout)
        out.writerow(['name', 'code', 'town', 'total'])
        for record in Record.select():
            out.writerow([record.name.encode('utf-8'),
                          record.code, record.town, record.total])

    @manager.command
    def georeference():
        #columns = ['code', '1', 'judet', '3', 'name', 'name_ascii', 'x', 'y']
        locmap = {(l['judet_ascii'], l['name_ascii']): l for l in read_localities()}
        count = defaultdict(int)
        not_matched = []
        by_coord = defaultdict(float)
        for row in csv.DictReader(sys.stdin):
            if not row['county']:
                count['nojudet'] += 1
                continue
            if row['county'] == row['town'] == 'BUCURESTI':
                count['bucuresti'] += 1
                continue
            if 'BUCURESTI SECTOR ' in row['town']:
                row['town'] = row['town'].replace('BUCURESTI SECTOR ',
                                                  'BUCURESTI SECTORUL ')
                row['county'] = 'BUCURESTI'
            elif row['county'] == 'SATU-MARE':
                row['county'] = 'SATU MARE'
            if row['town'] == 'BICAZ CHEI':
                row['town'] = 'BICAZ-CHEI'
            for v in ['ORAS ', 'MUNICIPIUL ', '']:
                key = (row['county'], v + row['town'])
                locality = locmap.get(key)
                if locality is not None:
                    break
            else:
                count['?'] += 1
                #not_matched.append(key)
                if len(not_matched) > 10:
                    break
                continue
            count['ok'] += 1
            by_coord[(locality['x'], locality['y'])] += float(row['total'])

        out = csv.DictWriter(sys.stdout, ['value', 'x', 'y'])
        out.writerow({'x': 'x', 'y': 'y', 'value': 'value'})
        for (x, y), value in by_coord.items():
            out.writerow({
                'x': x,
                'y': y,
                'value': value,
            })
        #pp(dict(count))
        #pp(not_matched)

    @manager.command
    def group_by_comuna():
        localities = list(read_localities())
        n_localities = defaultdict(int)
        loc_by_name = defaultdict(list)
        for l in localities:
            n_localities[l['name_ascii']] += 1
            loc_by_name[l['name_ascii']].append(l)
        locmap = {l['name_ascii']: l for l in localities}

        grand_total = 0
        by_town = defaultdict(float)
        geotype = defaultdict(float)
        bug = defaultdict(float)
        fuzzy = defaultdict(float)
        fuzzy_n = defaultdict(int)

        Record.drop_table(fail_silently=True)
        Record.create_table()

        for row in read_and_clean_csv(sys.stdin):
            total = float(row['total'])
            localitate = row['town']
            if localitate not in n_localities:
                for fix_pattern in ['MUNICIPIUL %s', 'ORAS %s']:
                    fix = fix_pattern % localitate
                    if fix in n_localities:
                        localitate = fix
                        break
                else:
                    if 'BUCURESTI' in localitate:
                        localitate = 'BUCURESTI SECTORUL 1'
            row['norm_localitate'] = localitate
            n_loc = n_localities.get(localitate, 0)
            if n_loc < 1:
                geotype['bug'] += total
                bug[localitate] += total
            elif n_loc == 1:
                geotype['ok'] += total
            else:
                geotype['fuzzy'] += total
                fuzzy[localitate] += total
                fuzzy_n[localitate] += 1
            grand_total += total
            by_town[localitate] += total

            Record.create(**row)

        db.commit()

        #print 'grand total: %11d' % grand_total
        #print '   ok total: %11d (%.4f)' % (geotype['ok'],
        #                                    geotype['ok'] / grand_total)
        #print 'fuzzy total: %11d (%.4f)' % (geotype['fuzzy'],
        #                                    geotype['fuzzy'] / grand_total)
        #print '  bug total: %11d (%.4f)' % (geotype['bug'],
        #                                    geotype['bug'] / grand_total)

        #top_bug = sorted(bug.items(), key=lambda kv: kv[1], reverse=True)
        #top_fuzzy = sorted(fuzzy.items(), key=lambda kv: kv[1], reverse=True)
        ##pp(top_bug[:10])
        #n = 30
        #fuzzy_top_n = top_fuzzy[:n]
        #sum_top_n = sum(f[1] for f in fuzzy_top_n)
        #print 'fuztop %4d: %11d (%.4f)' % (n, sum_top_n, sum_top_n / grand_total)
        #print '=== fuzzy ==='
        #for name, value in top_fuzzy:
        #    print '%10d %3d %s' % (value, fuzzy_n[name], name)

        layer = geojson.FeatureCollection([], crs=EPSG_31700_CRS)
        for name in by_town:
            if name not in loc_by_name:
                continue
            locs_with_name = loc_by_name[name]
            value_for_each = by_town[name] / len(locs_with_name)
            for l in locs_with_name:
                the_point = geojson.Point([float(l['x']), float(l['y'])])
                the_feature = geojson.Feature(geometry=the_point, id=l['code'])
                the_feature.properties.update({
                    'name': name,
                    'judet': l['judet_ascii'],
                    'judet_code': l['judet_code'],
                    'total': value_for_each,
                    'circle_size': math.sqrt(value_for_each) * .01,
                    'ambiguity': len(locs_with_name),
                })
                layer.features.append(the_feature)

        print geojson.dumps(layer, indent=2)

        # ogr2ogr -f sqlite -overwrite money.db money.geojson


def initialize(app):
    app.register_blueprint(queries)
    DatabasePlugin().initialize(app)
