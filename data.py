import sys
import csv
import flask
from peewee import Model, CharField, DecimalField, SqliteDatabase
import flatkit.datatables
from utils import html_unescape


db = SqliteDatabase(None, autocommit=False)


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


def register_commands(manager):

    @manager.command
    def create_all():
        Record.create_table(fail_silently=True)

    @manager.command
    def drop_all():
        Record.drop_table(fail_silently=True)

    @manager.command
    def load_apdrp_csv(csv_path):
        def split_line(line):
            clean = html_unescape(line).strip()
            spl = clean.split(';')
            if len(spl) == 8:
                return spl
            else:
                try:
                    first, other = clean.split(';RO', 1)
                except:
                    import pdb; pdb.set_trace()
                return [first] + ('RO' + other).split(';')

        with db.transaction():
            with open(csv_path, 'rb') as f:
                head = next(f).strip().split(';')
                for i, line in enumerate(f):
                    row = split_line(line)
                    assert len(head) == len(row), 'line %d: %r' % (i, row)
                    rowdict = dict(zip(head, row))
                    data = {
                        'name': rowdict['Denumire beneficiar'].decode('utf-8'),
                        'code': rowdict['Cod unic'],
                        'town': rowdict['Localitate'].decode('utf-8'),
                        'total': rowdict['Total plati'],
                    }
                    record = Record.create(**data)
            db.commit()

    @manager.command
    def dump_csv():
        out = csv.writer(sys.stdout)
        out.writerow(['name', 'code', 'town', 'total'])
        for record in Record.select():
            out.writerow([record.name.encode('utf-8'),
                          record.code, record.town, record.total])


def initialize(app):
    app.register_blueprint(queries)
    DatabasePlugin().initialize(app)
