import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    USERS_PER_PAGE = 20
    STATIONS_PER_PAGE = 1000
    OPERATION_TYPES_PER_PAGE = 1000
    OPERATION_STATUSES_PER_PAGE = 1000
    OPERATIONS_PER_PAGE = 1000
    STATUSES_PAGE = 1000
    PRODUCTS_PER_PAGE = 200
    COMMENTS_PER_PAGE = 100
    SQLALCHEMY_DATABASE_URI_PREFIX = 'sqlite:///'
    BOOTSTRAP_SERVE_LOCAL = True
    LANGUAGES = (('en', 'English'), ('pl', 'Polish'))
    VERSION = '0.3.7'
    DBMODEL_VERSION = "None"
    BABEL_DEFAULT_LOCALE = 'en'

    STATION_STATUS_CODES = {
        0: {"result": "UNDEFINED", "desc": "status undefined (not present in database)"},
        1: {"result": "OK", "desc": "Status ok"},
        2: {"result": "NOK", "desc": "Status not ok"},
        4: {"result": "NOTAVAILABLE", "desc": "Not present in given type"},
        5: {"result": "REPEATEDOK", "desc": "Repeated test was ok"},
        6: {"result": "REPEATEDNOK", "desc": "Repeated test was not ok"},
        9: {"result": "WAITING", "desc": "status reset - PLC set status to 'WAITING' and waiting for PC response"},
        10: {"result": "INTERRUPTED", "desc": "Test was interrupted"},
        11: {"result": "REPEATEDINTERRUPTED", "desc": "Repeated test was interrupted"},
        99: {"result": "VALUEERROR", "desc": "Faulty value was passed. Unable to process data."},
    }

class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 't0p s3cr3t'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = 'secret'
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')


class ProductionConfig(Config):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 't0p s3cr3t'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
