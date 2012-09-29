# encoding: utf-8
import sys
import csv
from collections import defaultdict
from pprint import pprint as pp
import flask
from peewee import Model, CharField, DecimalField, SqliteDatabase
from path import path
import flatkit.datatables
from utils import html_unescape


db = SqliteDatabase(None, autocommit=False)

refdata = path(__file__).parent / 'refdata'


class Record(Model):
    name = CharField()
    code = CharField()
    town = CharField()
    total = DecimalField()

    class Meta:
        database = db


class DatabasePlugin(object):

    def initialize(self, app):
        Record.Meta.database.init(app.config['DATABASE_PATH'])
        app.extensions['agripay_database'] = self


queries = flask.Blueprint('queries', __name__)


@queries.route('/')
def index():
    return flask.render_template('index.html')


@queries.route('/table')
def table():
    stats = {
        'sum(total)': Record.select('sum(total) as s').get().s,
    }
    towns = [r.town for r in Record.select('distinct(town) as town')]
    return flask.render_template('table.html', **{
        'stats': stats,
        'towns': sorted(towns),
    })


class RecordFilter(flatkit.datatables.FilterView):

    def query(self, options):
        select = Record.select()

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
    columns = ['code', '1', 'judet', '3', 'name', 'name_ascii', 'x', 'y']
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


def initialize(app):
    app.register_blueprint(queries)
    DatabasePlugin().initialize(app)
