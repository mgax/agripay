import csv
import flask
from peewee import Model, CharField, DecimalField, SqliteDatabase


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


CSV_CONFIG = {
    'a': {
        'csv_kwargs': {'delimiter': ';'},
    },
}


def register_commands(manager):

    @manager.command
    def create_all():
        Record.create_table(fail_silently=True)

    @manager.command
    def drop_all():
        Record.drop_table(fail_silently=True)

    @manager.command
    def load_csv(config_name, csv_path):
        config = CSV_CONFIG[config_name]

        with db.transaction():
            with open(csv_path, 'rb') as f:
                csv_kwargs = config.get('csv_kwargs', {})
                for csvrow in csv.DictReader(f, **csv_kwargs):
                    data = {
                        'name': csvrow['Denumire beneficiar'].decode('utf-8'),
                        'code': csvrow['Cod unic'],
                        'town': csvrow['Localitate'].decode('utf-8'),
                        'total': csvrow['Total plati'],
                    }
                    record = Record.create(**data)
            db.commit()
