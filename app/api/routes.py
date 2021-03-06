from flask import Flask, jsonify, abort, request, make_response, url_for, render_template
import json
from flask import render_template, flash, redirect, url_for, abort, request, current_app
from flask_login import login_required, current_user
from .. import db, auto, cfg
from ..models import *
from . import api as rest
from flask_selfdoc import Autodoc
import logging
import six
from sqlalchemy.exc import IntegrityError
from datetime import datetime

logger = logging.getLogger(__name__)


@rest.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)


@rest.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@rest.route("/product", methods=['GET'])
@auto.doc()
def get_products():
    """
    Get list of all products from database in JSON list format.
    In order to get list of all products please run HTTP GET on: http://localhost:5000/api/product
    """
    return jsonify(json_list=[i.serialize for i in Product.query.all()])


@rest.route('/autocomplete/<product_type>', methods=['GET'])
@auto.doc()
def autocomplete(product_type):
    results = []
    search = request.args.get('term')
    if search is None:
        search = ""
    return json.dumps([str(p.serial) for p in Product.query.all() if str(p.serial).startswith(search)  if str(p.type) == str(product_type)])


@rest.route('/product/<id>', methods=['GET'])
@auto.doc()
def get_product(id):
    """
    Gets the specific product identified by id (serial number) from database.
    In order to get product with id 1234 please run HTTP GET on: http://localhost:5000/api/product/1234
    """
    product = Product.query.filter_by(id=str(id)).first_or_404()
    if product is None:
        abort(404)
    return jsonify(product.serialize)


@rest.route("/product", methods=['POST'])
@auto.doc()
def add_product():
    """
    Adds new product.
    In order to create new product please run HTTP POST with following data on: http://localhost:5000/api/product

    Product Id is created as by following formula:
    product_id = type + serial + week + year

    Content Type: application/json
    Content:
    {
        "type": "1234567890",
        "serial": "654321",
        "week": "42",
        "year": "15"
    }
    """
    if not request.json:
        logger.error("Incorrect data in request %s" % repr(request.json))
        abort(400)

    for key in ['type', 'serial', 'week', 'year']:
        if key not in request.json:
            logger.error("required key: %s missing in request %s" % (key, repr(request.json)))
            abort(400)

    for key in ['type', 'serial', 'week', 'year']:  # check if keys are type of Int
        if not isinstance(request.json[key], six.string_types):
            logger.error("key: %s is not type of Int in request %s" % (key, repr(request.json)))
            abort(400)

    product_id = str(Product.calculate_product_id(type, serial, week, year))
    p = Product.query.filter_by(id=product_id).first()
    if p is not None:
        logger.warning("product with id: {id} is already present in product database. skipping.".format(id=product_id))
        abort(400)

    new_prod = Product(
        request.json['type'],
        request.json['serial'],
        request.json['week'],
        request.json['year'],
    )
    db.session.add(new_prod)
    db.session.commit()
    logger.info("new product added to database %s" % repr(new_prod))
    return jsonify(new_prod.serialize), 201


# method not allowed see: http://flask-restless.readthedocs.org/en/latest/customizing.html
@rest.route('/product/<id>', methods=['DELETE'])
@auto.doc()
def delete_product(id):
    """
    Deletes product from database.
    To delete product with id 2666 please send http DELETE to: http://localhost:5000/api/product/2666
    """
    product = Product.query.filter_by(id=str(id)).first()
    if product is None:
        abort(404)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'result': True})


# method not allowed see: http://flask-restless.readthedocs.org/en/latest/customizing.html
@rest.route('/product/<id>', methods=['PUT'])
@auto.doc()
def update_product(id):
    """
    Updates product.
    To update product with id 2666 please run PUT on: http://localhost:5000/api/product/2666
    Content Type: application/json
    Content:
        {
        "type": "1",
        "serial": "2",
        "week": "3",
        "year": "4"
        }
    """
    product = Product.query.filter_by(id=int(id)).first()
    for key in ['type', 'serial', 'week', 'year']:
        if key not in request.json:
            logger.error("required key: %s missing in request %s" % (key, repr(request.json)))
            abort(400)

    for key in ['type', 'serial', 'week', 'year']:  # check if keys are type of Int
        if not isinstance(request.json[key], six.string_types):
            logger.error("key: %s is not type of Int in request %s" % (key, repr(request.json)))
            abort(400)

    product.type = request.json['type']
    product.type = request.json['serial']
    product.week = request.json['week']
    product.year = request.json['year']
    db.session.commit()
    return jsonify(product.serialize)


@rest.route("/station", methods=['GET'])
@auto.doc()
def get_stations():
    """
    Get list of all stations from database in JSON format.
    In order to get list of all stations please run HTTP GET on: http://localhost:5000/api/station
    """
    return jsonify(json_list=[s.serialize for s in Station.query.all()])


@rest.route('/station/<int:id>', methods=['GET'])
@auto.doc()
def get_station(id):
    """
    Get station information for given id.
    In order to get details of station with id 21 please run HTTP GET on: http://localhost:5000/api/station/21
    """
    station = Station.query.filter_by(id=int(id)).first_or_404()
    return jsonify(station.serialize)


@rest.route("/station", methods=['POST'])
@auto.doc()
def create_station():
    """
    Creates new station.
    In order to create new station please run HTTP POST with following data on: http://localhost:5000/api/station

    Content Type: application/json with following example
    Content:
    {
      "id": 10,
      "ip": "192.168.0.10",
      "port": 102,
      "rack": 0,
      "slot": 2
    }
    """

    if not request.json:
        logger.error("Incorrect data in request %s" % repr(request.json))
        abort(400)

    for key in ['id', 'ip', 'port', 'rack', 'slot']:
        if key not in request.json:
            logger.error("required key: %s missing in request %s" % (key, repr(request.json)))
            abort(400)

    for key in ['id', 'port', 'rack', 'slot']:  # check if keys are type of Int
        if not isinstance(request.json[key], six.integer_types):
            logger.error("key: %s is not type of Int in request %s" % (key, repr(request.json)))
            abort(400)

    for key in ['ip']:  # check if keys are type of Text
        if not isinstance(request.json[key], six.text_type):
            logger.error("key: %s is not type of Text in request %s" % (key, repr(request.json)))
            abort(400)

    new_station = Station(
        int(request.json['id']),
        request.json['ip'],
        int(request.json['port']),
        int(request.json['rack']),
        int(request.json['slot']),
    )
    db.session.add(new_station)
    db.session.commit()
    logger.info("new station added to database %s" % repr(new_station))
    return jsonify(new_station.serialize), 201
    # TODO: make better request validation like in update_product


# TODO: add delete and update station

@rest.route("/status", methods=['GET'])
@auto.doc()
def get_statuses():
    """
    Get list of all statuses from database in JSON format.
    URL: http://localhost:5000/api/status
    """
    return jsonify(json_list=[i.serialize for i in Status.query.all()])


@rest.route('/status/<int:id>', methods=['GET'])
@auto.doc()
def get_status(id):
    """
    Get status information for given id.
    In order to get status with id 1 please run HTTP GET on: http://localhost:5000/api/status/1
    :param id: id of given status
    """
    status = Status.query.filter_by(id=int(id)).first_or_404()
    return jsonify(status.serialize)


@rest.route('/status/product/<product_id>', methods=['GET'])
@auto.doc()
def get_status_product(product_id):
    """
    Get list of status information for given product_id (serial number).
    In order to get assembly status for product with id 1234 please run HTTP GET on: http://localhost:5000/api/status/product/1234
    This will return status information from all stations.
    :param product_id: product_id (serial number) of given status
    """
    status = Status.query.filter_by(product_id=str(product_id)).all()
    if len(status) == 0:
        abort(404)
    return jsonify(json_list=[i.serialize for i in Status.query.filter_by(product_id=str(product_id)).all()])


@rest.route('/status/station/<int:station_id>', methods=['GET'])
@auto.doc()
def get_status_station(station_id):
    """
    Get list of status information for given station_id.
    In order to get assembly status for station with id 21 please run HTTP GET on: http://localhost:5000/api/status/station/21
    This will return status information for all products matching criteria.
    :param station_id: station_id of given status.
    """

    status = Status.query.filter_by(station_id=int(station_id)).all()
    if len(status) == 0:
        abort(404)
    return jsonify(json_list=[i.serialize for i in Status.query.filter_by(station_id=int(station_id)).all()])


@rest.route('/status/station/<int:station_id>/product/<product_id>', methods=['GET'])
@auto.doc()
def get_status_station_product(station_id, product_id):
    """
    Get status information for given station_id and product_id.
    In order to get assembly status for station with id 21 and product id 464006201000000001 please run HTTP GET on: http://localhost:5000/api/status/station/21/product/464006201000000001
    This will return all status information for given criteria.
    :param station_id: station_id of given status
    :param product_id: product_id (string) of given status
    """

    statuses = Status.query.filter_by(station_id=int(station_id)).filter_by(product_id=product_id).order_by('id').all()
    if len(statuses) == 0:
        logger.error("status not found for Station ID: {station_id} Product Id: {product_id}".format(station_id=station_id, product_id=product_id))
        abort(404)
        return
    if len(statuses) > 1:
        status = statuses[-1]
        if status.status == 1:
            # the status is ok after repetition
            status.status = 5
        if status.status == 2:
            # the status is nok after repetition
            status.status = 6
    if len(statuses) == 1:
        status = statuses[0]

    return jsonify(status.serialize)


@rest.route("/status", methods=['POST'])
@auto.doc()
def add_status():
    """
    Writes status information for given station_id.
    Please either specify product_id or product_type together with serial_numnber.
    The date_time field is optional. Tool will take current datetime if not specified.
    In order to get assembly status please run HTTP POST on: http://localhost:5000/api/status
    Content Type: application/json
    Content:
    {
        "status": 1,
        "station_id": 10,
        "product_id": "16666",
        "date_time": "2015-02-11 22:49:37.496000",
        "fail_step": "fail step description"
    }

    """
    if not request.json:
        logger.error("Incorrect data in request %s" % repr(request.json))
        abort(400)

    for key in ['status', 'station_id']:
        if key not in request.json:
            logger.error("required key: %s missing in request %s" % (key, repr(request.json)))
            abort(400)

    for key in ['status', 'station_id']:  # check if keys are type of Int
        if not isinstance(request.json[key], six.integer_types):
            logger.error("key: %s is not type of Int in request %s" % (key, repr(request.json)))
            abort(400)

    if "product_id" in request.json:
        if isinstance(request.json["product_id"], six.string_types):
            product_id = request.json["product_id"]
        else:
            logger.error("key: %s is not type of String in request %s" % ("product_id", repr(request.json)))
            abort(400)

    p = Product.query.filter_by(id=str(product_id)).first()
    if p is None:
        logger.warning("product with id: {product_id} is not present in product database".format(product_id=product_id))

    date_time = get_current_datetime()
    if "date_time" in request.json:
        if isinstance(request.json["date_time"], six.text_type):
            date_time = request.json['date_time']

    fail_step = ""
    if "fail_step" in request.json:
        if isinstance(request.json["fail_step"], six.text_type):
            fail_step = request.json["fail_step"]

    new_status = Status(
        status=request.json['status'],
        product=product_id,
        station=request.json['station_id'],
        date_time=date_time,
        fail_step=fail_step
    )
    db.session.add(new_status)
    try:
        db.session.commit()
    except IntegrityError, e:
        error = "%s : %s " % (repr(e), e)
        logger.error(error)
        return error, 400

    logger.info("new status added to database %s" % repr(new_status))
    return jsonify(new_status.serialize), 201


@rest.route("/datetime", methods=['GET'])
@auto.doc()
def get_current_datetime():
    """
    Get the current date and time from PC
    URL: http://localhost:5000/api/datetime
    """

    return str(datetime.now())


@rest.route("/current_reference", methods=['GET'])
@auto.doc()
def get_current_reference():
    """
    Get the currently processed product_type
    URL: http://localhost:5000/api/current_reference
    """

    sql_query = "select type from Product where id = (select product_id from Status where station_id=11 order by id DESC limit 1);"
    results = db.engine.execute(sql_query)
    # return first element
    for row in results:
        return str(row[0])

    return str(0)
    
    #last_status = db.session.query(Status).filter(station_id=11).order_by('id').get()
	#cur_product = db.session.query(Product).
    last_status = Status.query.filter_by(station_id=11).order_by('-id').first()
    if last_status is None:
        return str(0)
    product = Product.query.filter_by(id=str(last_status.product_id)).first()
    if product is not None:
        cur_ref = str(product.type)
    else:
        cur_ref = 0

    return str(cur_ref)


@rest.route("/serverstatus", methods=['GET'])
@auto.doc()
def get_serverstatus():
    """
    Get the current server status in JSON format.
    Status contains:
    - current date_time from PC
    - currently processed product_type
    URL: http://localhost:5000/api/serverstatus
    """

    serverstatus = {
        'date_time': get_current_datetime(),
        'current_reference': get_current_reference(),
    }

    return jsonify(serverstatus)

	
@rest.route("/serverstatus2", methods=['GET'])
@auto.doc()
def get_serverstatus2():
    """
    Get the current server status in JSON format.
    Status contains:
    - current date_time from PC
    - currently processed product_type
    URL: http://localhost:5000/api/serverstatus
    """
    begin = datetime.now()
    ref = get_current_reference()
    end = datetime.now()
    elapsed = end - begin
    serverstatus = {
        'date_time': get_current_datetime(),
        'current_reference': str(ref),
        'elapsed': str(elapsed),
    }

    return jsonify(serverstatus)	

@rest.route('/')
def index(name=None):
    """
    Rest API of ProdLineTrace.
    Please refer to http://localhost:5000/api/doc for documentation.

    Author: Piotr.Wilkosz@gmail.com
    """
    return render_template('restapi/index.html', name=name, status_codes=cfg['default'].STATION_STATUS_CODES)

@rest.route('/status_codes')
def status_codes():
    """
    Status codes list
    Author: Piotr.Wilkosz@gmail.com
    """
    return render_template('restapi/status_codes.html', status_codes=cfg['default'].STATION_STATUS_CODES)


@rest.route('/doc')
def documentation():
    return auto.html(template="restapi/autodoc_default.html", title="ProdLineTrace RestAPI documentation", author='Piotr Wilkosz')

