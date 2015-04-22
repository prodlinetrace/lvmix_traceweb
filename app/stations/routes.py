from flask import render_template, flash, redirect, url_for, abort, request, current_app
from flask.ext.login import login_required, current_user
from flask.ext.babel import gettext
from .. import db
from ..models import Station
from . import stations
from .forms import StationForm


@stations.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Station.query.paginate(
        page, per_page=current_app.config['STATIONS_PER_PAGE'],
        error_out=False)
    station_list = pagination.items
    return render_template('stations/index.html', stations=station_list, pagination=pagination)


@stations.route('/<int:id>')
@login_required
def station(id):
    station = Station.query.filter_by(id=id).first_or_404()
    page = request.args.get('page', 1, type=int)
    return render_template('stations/station.html', station=station)


@stations.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    if not current_user.is_admin:
        abort(403)
    _last_station_id = Station.query.first()
    if _last_station_id is None:
        id = 0
    else:
        id = _last_station_id.id
    id = id + 1
    form = StationForm()
    if form.validate_on_submit():
        station = Station(id)
        form.to_model(station) # update station object with form data
        db.session.add(station)
        db.session.commit()
        flash(gettext(u'New station: {station} was added successfully.'.format(station=station.name)))
        return redirect(url_for('.index'))
    else:
        flash(gettext("Validation failed"))
    return render_template('stations/new.html', form=form)


@stations.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    station = Station.query.get_or_404(id)
    if not current_user.is_admin:
        abort(403)
    form = StationForm()
    if form.validate_on_submit():
        form.to_model(station)
        db.session.add(station)
        db.session.commit()
        flash(gettext(u'Station profile for: {station} has been updated.'.format(station=station.name)))
        return redirect(url_for('.index'))
    else:
        flash(gettext("Validation failed"))
    form.from_model(station)
    return render_template('stations/edit.html', station=station, form=form)


@stations.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete(id):
    station = Station.query.get_or_404(id)
    if current_user.is_admin: 
        db.session.delete(station)
        db.session.commit()
        flash(gettext(u'Station for: {station} has been deleted.'.format(station=station.name)))
        return redirect(url_for('.index'))
    else:
        flash(gettext(u'You have to be adminstrator to remove stations.'.format(station=station.name)))
        return redirect(url_for('.index'))

    # should never get here
    return render_template('stations/index.html')
