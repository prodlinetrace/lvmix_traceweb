import hashlib
import bleach
import logging
from datetime import datetime
from markdown import markdown
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import request, current_app
from flask_login import UserMixin
from . import db, login_manager
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

__version__ = '0.7.3'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(64), nullable=False, unique=True, index=True)
    name = db.Column(db.String(64))
    is_admin = db.Column(db.Boolean)
    is_operator = db.Column(db.Boolean)
    password_hash = db.Column(db.String(128))
    location = db.Column(db.String(64))
    locale = db.Column(db.String(16))
    bio = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.now)
    avatar_hash = db.Column(db.String(32))
    comments = db.relationship('Comment', lazy='dynamic', backref='author')
    status = db.relationship('Status', lazy='dynamic', backref='user', foreign_keys='Status.user_id')


    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.login is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(
                self.login.encode('utf-8')).hexdigest()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        _hash = self.avatar_hash or hashlib.md5(self.login.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=_hash, size=size, default=default, rating=rating)

    def get_api_token(self, expiration=300):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'user': self.id}).decode('utf-8')

    @staticmethod
    def validate_api_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        _id = data.get('user')
        if _id:
            return User.query.get(_id)
        return None

    def __repr__(self):
        return '<User {id} Login {login} Name {name}>'.format(id=self.id, login=self.login, name=self.name)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    product_id = db.Column(db.String(20), db.ForeignKey('product.id'), index=True)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def __repr__(self):
        return '<Comment {id} Product {product} Author {author}>'.format(id=self.id, product=self.product_id, author=self.author_id)


db.event.listen(Comment.body, 'set', Comment.on_changed_body)


class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.String(20), nullable=False, unique=True, index=True, primary_key=True)
    type = db.Column(db.String(10), nullable=False, index=True, unique=False)
    serial = db.Column(db.String(6), nullable=False, index=True, unique=False)
    week = db.Column(db.String(2), nullable=False, index=True, unique=False)
    year = db.Column(db.String(2), nullable=False, index=True, unique=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('variant.id'), nullable=False, index=True, unique=False)
    prodasync = db.Column(db.Integer, nullable=False, index=True, unique=False, default=0)
    date_added = db.Column(db.DateTime(), index=True, default=datetime.now)
    comments = db.relationship('Comment', lazy='dynamic', backref='product')
    statuses = db.relationship('Status', lazy='dynamic', backref='product')
    operations = db.relationship('Operation', lazy='dynamic', backref='product')

    def __init__(self, prodtype, serial, week, year, variant_id, prodasync):
        self.type = prodtype
        self.serial = serial
        self.week = week
        self.year = year
        self.variant_id = variant_id
        self.prodasync = prodasync
        self.id = self.get_product_id(self.type, self.serial, self.week, self.year)

    def __repr__(self):
        return '<Product {id}>'.format(id=self.id)

    def get_product_id(self, prodtype=None, serial=None , week=None, year=None):
        """
        returns product id based on product_type, serial_number week and year.
        It is used within Product table.
        """
        if prodtype is None:
            prodtype = self.type

        if serial is None:
            serial = self.serial

        if week is None:
            week = self.week

        if year is None:
            year = self.year

        return Product.calculate_product_id(prodtype, serial, week, year)

    @staticmethod
    def calculate_product_id(_type="", _serial="", _week="", _year=""):
        return "{type}{serial}{week}{year}".format(type=str(_type).zfill(10), serial=str(_serial).zfill(6), week=str(_week).zfill(2) , year=str(_year).zfill(2))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'type': self.type,
            'serial': self.serial,
            'week': self.week,
            'year': self.year,
            'variant_id': self.variant_id,
            'date_added': self.date_added,
            'datetime_added': self.datetime_added,
            'prodasync': self.prodasync,
            'proda_serial': self.proda_serial,
        }

    @property
    def proda_serial(self):
        """Return proda serial number in well defined format: YYYY_WW_V_SN (YYYY-rok, WW-tydzien, V-wariant, SN-numer seryjny)"""
        return "{year:04d}_{week:02d}_{variant}_{serial}".format(year=2000+int(self.year), week=int(self.week), variant=self.variant_id, serial=str(self.serial).zfill(6))

    @property
    def datetime(self):
        return datetime.strptime(self.date_time, "%Y-%m-%d %H:%M:%S.%f")

    @property
    def status_count(self):
        """ Return number statuses """
        return self.statuses.count()  

    @property
    def status_count_good(self):
        """ Return number of good statuses """
        return self.statuses.filter(Status.status==1).count()  

    @property
    def status_count_bad(self):
        """ Return number of bad statuses """
        return self.statuses.filter(Status.status==2).count()

    @property
    def operation_count(self):
        """ Return number operations """
        return self.operations.count()  

    @property
    def operation_count_good(self):
        """ Return number of good operations """
        return self.operations.filter(Operation.operation_status_id==1).count()  

    @property
    def operation_count_bad(self):
        """ Return number of bad operations """
        return self.operations.filter(Operation.operation_status_id==2).count()

    @property
    def electronic_stamp(self):
        """ Return Electronic Stamp"""
        st55 = self.statuses.filter(Status.station_id==55).order_by(Status.id.desc()).first()
        return st55 

class Station(db.Model):
    __tablename__ = 'station'
    id = db.Column(db.Integer, primary_key=True)  # this is real station id
    ip = db.Column(db.String(16), unique=False)
    name = db.Column(db.String(64), unique=False)
    port = db.Column(db.Integer, unique=False)
    rack = db.Column(db.Integer, unique=False)
    slot = db.Column(db.Integer, unique=False)
    statuses = db.relationship('Status', lazy='dynamic', backref='station')
    operations = db.relationship('Operation', lazy='dynamic', backref='station')

    def __init__(self, id, ip='localhost', name="name", port=102, rack=0, slot=2):
        self.id = id
        self.ip = ip
        self.name = name
        self.port = port
        self.rack = rack
        self.slot = slot

    def __repr__(self):
        return '<Station {id}>'.format(id=self.id)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'ip': self.ip,
            'name': self.name,
            'port': self.port,
            'rack': self.rack,
            'slot': self.slot,
        }


class Status(db.Model):
    __tablename__ = 'status'
    id = db.Column(db.BigInteger, nullable=False, unique=True, index=True, primary_key=True, autoincrement=True)
    status = db.Column(db.Integer, db.ForeignKey('operation_status.id'), index=True)
    date_time = db.Column(db.String(40))
    product_id = db.Column(db.String(20), db.ForeignKey('product.id'), index=True)
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    fail_step = db.Column(db.String(255))
    prodasync = db.Column(db.Integer, index=True, default=0)

    def __init__(self, status, product, station, user=None, date_time=None, fail_step=''):
        self.status = status
        self.product_id = product
        self.station_id = station
        self.user_id = user
        if date_time is None:
            date_time = datetime.now()
        self.date_time = str(date_time)
        self.fail_step = fail_step

    def __repr__(self):
        return '<Status Id: {id} for Product: {product} Station: {station} Status: {status}>'.format(id=self.id, product=self.product_id, station=self.station_id, status=self.status)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'status': self.status,
            'product_id': self.product_id,
            'station_id': self.station_id,
            'user_id': self.user_id,
            'date_time': self.date_time,
            'datetime': self.datetime,
            'fail_step': self.fail_step,
            'operations': self.operations,
        }

    @property
    def datetime(self):
        return datetime.strptime(self.date_time, "%Y-%m-%d %H:%M:%S.%f")

    @property
    def operations(self):
        """
            get list of operations matching given status (360 seconds diff from operation and status is the limit). 
        """
        time_diff_limit = 360  # time diff limit in seconds
        
        # filter operations with matching station_id
        operations = filter(lambda x: x.station_id == self.station_id, self.product.operations.all())  
        # filter out operations with with time difference bigger than 360 seconds.
        operations = filter(lambda x: (self.datetime - datetime.strptime(x.date_time, "%Y-%m-%d %H:%M:%S.%f")).seconds < time_diff_limit, operations)
        
        # find operations with duplicate operation_type_id and group them
        import itertools
        lists = [list(v) for k,v in itertools.groupby(sorted(operations, key=lambda y: y.operation_type_id), lambda x: x.operation_type_id)]
        operations = []  # reset operations to fill it again with code below
        for items_groupped_by_operation_type_id in lists:
            if len(items_groupped_by_operation_type_id) > 1:  # this means that there is more tham one item with same operation_type_id
                # find item with closest operation date 
                item_with_closest_operation_date = min(items_groupped_by_operation_type_id, key=lambda x: (self.datetime - datetime.strptime(x.date_time, "%Y-%m-%d %H:%M:%S.%f")).seconds)
            else:
                item_with_closest_operation_date = items_groupped_by_operation_type_id[0] 
            operations.append(item_with_closest_operation_date)

        return operations


class Operation(db.Model):
    __tablename__ = 'operation'
    id = db.Column(db.BigInteger, nullable=False, unique=True, index=True, primary_key=True, autoincrement=True)
    product_id = db.Column(db.String(20), db.ForeignKey('product.id'), index=True)
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'), index=True)
    operation_status_id = db.Column(db.Integer, db.ForeignKey('operation_status.id'), index=True)
    operation_type_id = db.Column(db.Integer, db.ForeignKey('operation_type.id'), index=True)
    date_time = db.Column(db.String(40))
    prodasync = db.Column(db.Integer, index=True, default=0)
    result_1 = db.Column(db.Float)
    result_1_max = db.Column(db.Float)
    result_1_min = db.Column(db.Float)
    result_1_status_id = db.Column(db.Integer, db.ForeignKey('operation_status.id'), index=True)
    result_2 = db.Column(db.Float)
    result_2_max = db.Column(db.Float)
    result_2_min = db.Column(db.Float)
    result_2_status_id = db.Column(db.Integer, db.ForeignKey('operation_status.id'), index=True)
    result_3 = db.Column(db.Float)
    result_3_max = db.Column(db.Float)
    result_3_min = db.Column(db.Float)
    result_3_status_id = db.Column(db.Integer, db.ForeignKey('operation_status.id'), index=True)

    def __init__(self, product, station, operation_status_id, operation_type_id, date_time, r1=None, r1_max=None, r1_min=None, r1_stat=None, r2=None, r2_max=None, r2_min=None, r2_stat=None, r3=None, r3_max=None, r3_min=None, r3_stat=None):
        self.product_id = product
        self.station_id = station
        self.operation_status_id = operation_status_id
        self.operation_type_id = operation_type_id
        if date_time is None:
            date_time = datetime.now()
        self.date_time = str(date_time)

        self.result_1 = r1
        self.result_1_max = r1_max
        self.result_1_min = r1_min
        self.result_1_status_id = r1_stat

        self.result_2 = r2
        self.result_2_max = r2_max
        self.result_2_min = r2_min
        self.result_2_status_id = r2_stat

        self.result_3 = r3
        self.result_3_max = r3_max
        self.result_3_min = r3_min
        self.result_3_status_id = r3_stat

    def __repr__(self):
        return '<Assembly Operation Id: {id} for: Product: {product} Station: {station} Operation_type: {operation_type}>'.format(id=self.id, product=self.product_id, station=self.station_id, operation_type=self.operation_type_id)

    @property
    def datetime(self):
        return datetime.strptime(self.date_time, "%Y-%m-%d %H:%M:%S.%f")

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""

        return {
            'id': self.id,
            'product_id': self.product_id,
            'station_id': self.station_id,
            'operation_type_id': self.operation_type_id,
            'operation_status_id': self.operation_status_id,
            'date_time': self.date_time,
            'datetime': self.datetime,

            'result_1': self.result_1,
            'result_1_max': self.result_1_max,
            'result_1_min': self.result_1_min,
            'result_1_status_id': self.result_1_status_id,

            'result_2': self.result_2,
            'result_2_max': self.result_2_max,
            'result_2_min': self.result_2_min,
            'result_2_status_id': self.result_2_status_id,

            'result_3': self.result_3,
            'result_3_max': self.result_3_max,
            'result_3_min': self.result_3_min,
            'result_3_status_id': self.result_3_status_id,
        }


class Operation_Status(db.Model):
    __tablename__ = 'operation_status'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    description = db.Column(db.String(255))
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), index=True)
    operations = db.relationship('Operation', lazy='dynamic', backref='operation_status',  foreign_keys='Operation.operation_status_id')

    result_1_status = db.relationship('Operation', lazy='dynamic', backref='result_1_status', foreign_keys='Operation.result_1_status_id')
    result_2_status = db.relationship('Operation', lazy='dynamic', backref='result_2_status', foreign_keys='Operation.result_2_status_id')
    result_3_status = db.relationship('Operation', lazy='dynamic', backref='result_3_status', foreign_keys='Operation.result_3_status_id')

    status = db.relationship('Status', lazy='dynamic', backref='status_name', foreign_keys='Status.status')

    def __init__(self, id, name="Default Operation Status", description="Default Operation Status Description", unit_id=0):
        self.id = id
        self.name = name
        self.description = description
        self.unit_id = unit_id

    def __repr__(self):
        return '<Operation_Status Id: {id} Name: {name} Description: {desc}>'.format(id=self.id, name=self.name, desc=self.description)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'unit_id': self.unit_id,
        }


class Operation_Type(db.Model):
    __tablename__ = 'operation_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    description = db.Column(db.String(255))
    operations = db.relationship('Operation', lazy='dynamic', backref='operation_type')

    def __init__(self, id, name="Default Operation Name", description="Default Operation Description"):
        self.id = id
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Operation_Type Id: {id} Name: {name} Description: {desc}>'.format(id=self.id, name=self.name, desc=self.description)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
        }


class Unit(db.Model):
    __tablename__ = 'unit'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    symbol = db.Column(db.String(16))
    description = db.Column(db.String(255))
    unit = db.relationship('Operation_Status', lazy='dynamic', backref='unit', foreign_keys='Operation_Status.unit_id')

    def __init__(self, id, name="Default Unit Name", symbol="Default Unit Symbol", description="Default Unit Description"):
        self.id = id
        self.name = name
        self.symbol = symbol
        self.description = description

    def __repr__(self):
        return '<Unit Id: {id} Name: {name} Symbol: {symbol} Description: {desc}>'.format(id=self.id, name=self.name, symbol=self.symbol, desc=self.description)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'name': self.name,
            'symbol': self.symbol,
            'description': self.description,
        }


class Variant(db.Model):
    __tablename__ = 'variant'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    description = db.Column(db.String(255))
    variant = db.relationship('Product', lazy='dynamic', backref='variant', foreign_keys='Product.variant_id')

    def __init__(self, id, name="Default Variant Name", description="Default Variant Description"):
        self.id = id
        self.name = name
        self.description = description

    def __repr__(self):
        return '<Variant Id: {id} Name: {name} Description: {desc}>'.format(id=self.id, name=self.name, desc=self.description)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
        }
