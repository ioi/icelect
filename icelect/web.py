# Icelect - The web application
# (c) 2025 Martin Mareš <mj@ucw.cz>

from flask import Flask, request, session, redirect, url_for, render_template, Response, g
import flask.logging
from flask.views import View
from flask_sqlalchemy import SQLAlchemy
import os
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
import werkzeug.exceptions

import icelect.config as config
import icelect.db as db
from icelect.election import ElectionConfig


static_dir = os.path.abspath('static')
app = Flask(__name__, static_folder=static_dir)
app.config.from_object(config)

jenv = app.jinja_env
jenv.lstrip_blocks = True
jenv.trim_blocks = True

db.flask_db = SQLAlchemy(app,
                         metadata=db.Base.metadata,
                         engine_options={
                             'isolation_level': 'SERIALIZABLE',
                         })


def init_request() -> None:
    g.is_admin = 'admin' in session


app.before_request(init_request)


class IcelectView(View):

    def init_election(self, ident: str) -> tuple[db.Election, ElectionConfig]:
        sess = db.get_session()
        election = sess.scalar(select(db.Election).filter_by(ident=ident))
        if election is None:
            raise werkzeug.exceptions.NotFound("Election not found")
        if election.state == db.ElectionState.init and not g.is_admin:
            raise werkzeug.exceptions.Forbidden("Election not ready")
        return election, ElectionConfig(ident, election.config)


class MainPage(IcelectView):
    def dispatch_request(self) -> str:
        sess = db.get_session()
        elections = sess.scalars(select(db.Election).order_by(db.Election.order, db.Election.ident))

        if not g.is_admin:
            elections = [e for e in elections if e.state != db.ElectionState.init]

        e_conf_list = [(e, ElectionConfig(e.ident, e.config)) for e in elections]

        return render_template('index.html', e_conf_list=e_conf_list)


class ElectionPage(IcelectView):
    def dispatch_request(self, ident: str) -> str:
        election, econf = self.init_election(ident)

        return render_template('election.html', election=election, econf=econf)


app.add_url_rule('/', view_func=MainPage.as_view('index'))
app.add_url_rule('/e/<ident>/', view_func=ElectionPage.as_view('election'))


@app.route('/admin')
def make_admin():
    # FIXME
    session['admin'] = 1
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    # FIXME
    session.pop('admin', None)
    return redirect(url_for('index'))
