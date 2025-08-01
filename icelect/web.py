# Icelect - The web application
# (c) 2025 Martin Mareš <mj@ucw.cz>

import csv
from flask import Flask, request, session, redirect, url_for, render_template, Response, g
from flask.helpers import flash
import flask.logging
from flask.views import View
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from io import StringIO
import os
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
import werkzeug.exceptions
import wtforms
import wtforms.validators as validators

import icelect.config as config
from icelect.crypto import cred_to_h1, cred_to_h2, h1_to_receipt, h1_to_verifier
import icelect.db as db
from icelect.election import ElectionData


static_dir = os.path.abspath('static')
app = Flask(__name__, static_folder=static_dir)
app.config.from_object(config)

jenv = app.jinja_env
jenv.lstrip_blocks = True
jenv.trim_blocks = True
jenv.globals.update(ElectionState=db.ElectionState)

db.flask_db = SQLAlchemy(app,
                         metadata=db.Base.metadata,
                         engine_options={
                             'isolation_level': 'SERIALIZABLE',
                         })


def init_request() -> None:
    g.role = session.get('role', 'user')
    g.is_admin = g.role == 'admin'
    g.is_reg = g.role == 'reg'


app.before_request(init_request)


class IcelectView(View):
    election: db.Election
    edata: ElectionData

    def init_election(self, ident: str, admin_only: bool = False) -> None:
        sess = db.get_session()
        election = sess.scalar(select(db.Election).filter_by(ident=ident))
        if election is None:
            raise werkzeug.exceptions.NotFound("Election not found")
        self.election = election

        if self.election.state == db.ElectionState.init and not g.is_admin:
            raise werkzeug.exceptions.Forbidden("Election not ready")

        if admin_only and not g.is_admin:
            raise werkzeug.exceptions.Forbidden("Available only to administrators")

        self.edata = ElectionData.from_db(election)

    def is_valid_credential(self, cred: str | None) -> bool:
        if cred is None:
            return False
        sess = db.get_session()
        h2 = cred_to_h2(cred)
        return sess.scalar(select(db.CredHash).filter_by(election=self.election, hash=h2)) is not None

    def election_url(self) -> str:
        return url_for('election', ident=self.election.ident)


class MainPage(IcelectView):
    def dispatch_request(self) -> str:
        sess = db.get_session()
        elections = sess.scalars(select(db.Election).order_by(db.Election.order, db.Election.ident))

        if not g.is_admin:
            elections = [e for e in elections if e.state != db.ElectionState.init]

        e_data_list = [(e, ElectionData.from_db(e)) for e in elections]

        return render_template('index.html', e_data_list=e_data_list)


class SetStateForm(FlaskForm):
    new_state = wtforms.SelectField("State:", choices=db.ElectionState.choices(), coerce=db.ElectionState.coerce)
    submit = wtforms.SubmitField("Change")


class CredentialForm(FlaskForm):
    credential = wtforms.StringField("Credential:", [validators.DataRequired()])
    vote = wtforms.SubmitField("Vote")


class CheckVoteForm(FlaskForm):
    receipt = wtforms.StringField("Receipt:", [validators.DataRequired()])
    check = wtforms.SubmitField("Check")


class ElectionPage(IcelectView):
    def dispatch_request(self, ident: str) -> str:
        self.init_election(ident)

        set_state_form = None
        cred_form = None
        check_form = None

        if g.is_admin:
            set_state_form = SetStateForm()
            set_state_form.new_state.data = self.election.state
        elif self.election.state == db.ElectionState.voting:
            cred_form = CredentialForm()
            check_form = CheckVoteForm()

        return render_template(
            'election.html',
            election=self.election, edata=self.edata,
            cred_form=cred_form,
            check_form=check_form,
            set_state_form=set_state_form,
        )


class VoteFormBase(FlaskForm):
    credential = wtforms.HiddenField()
    nonce = wtforms.StringField("Nonce (a random string to make your vote unique):", [validators.DataRequired(), validators.Length(max=16)])
    send = wtforms.SubmitField("Send your vote")


class VotePage(IcelectView):
    methods = ['POST']

    def dispatch_request(self, ident: str):
        self.init_election(ident)

        if self.election.state != db.ElectionState.voting:
            flash('Voting in this election is no longer allowed.', 'danger')
            return redirect(self.election_url())

        class VoteForm(VoteFormBase):
            pass

        choices = [(str(i), str(i)) for i in range(1, self.edata.num_options + 1)]
        for i in range(self.edata.num_options):
            setattr(VoteForm, f'rank_{i}', wtforms.RadioField(choices=choices, coerce=int))

        cred_form = CredentialForm()
        vote_form = VoteForm()

        if cred_form.validate_on_submit() and cred_form.vote.data:
            cred = cred_form.credential.data
            if not self.is_valid_credential(cred):
                flash('This credential is not valid for this election.', 'danger')
                return redirect(self.election_url())
            for i in range(self.edata.num_options):
                getattr(vote_form, f'rank_{i}').data = self.edata.num_options
        elif vote_form.validate_on_submit() and vote_form.send.data:
            cred = vote_form.credential.data or ""
            if not self.is_valid_credential(cred):
                flash('This credential is not valid for this election.', 'danger')
                return redirect(self.election_url())

            ranks = []
            for i in range(self.edata.num_options):
                val = getattr(vote_form, f'rank_{i}').data
                if val is None:
                    val = self.edata.num_options - 1
                ranks.append(val)

            nonce = vote_form.nonce.data or ""
            receipt = self.record_vote(cred, nonce, ranks)

            flash(f'Your vote has been recorded. Please keep your receipt {receipt} and nonce {nonce}, which can be used to verify your vote later.', 'success')
            return redirect(self.election_url())

        return render_template(
            'vote.html',
            election=self.election, edata=self.edata,
            vote_form=vote_form,
            vote_rows=[(self.edata.options[i], getattr(vote_form, f'rank_{i}')) for i in range(self.edata.num_options)],
        )

    def record_vote(self, cred: str, nonce: str, ranks: list[int]) -> str:
        h1 = cred_to_h1(cred)
        receipt = h1_to_receipt(h1, self.election.election_key)
        verifier = h1_to_verifier(h1, self.election.verify_key)

        sess = db.get_session()
        vins = (insert(db.Verifier)
                .values(election_id=self.election.election_id, verifier=verifier)
                .on_conflict_do_nothing())
        sess.execute(vins)

        bins = (insert(db.Ballot)
                .values(
                    election_id=self.election.election_id,
                    receipt=receipt,
                    nonce=nonce,
                    ranks=ranks,
                )
                .on_conflict_do_update(
                    constraint='ballots_election_id_receipt_key',
                    set_={
                        'nonce': nonce,
                        'ranks': ranks,
                    },
                ))
        sess.execute(bins)

        sess.commit()

        app.logger.info(f'Ballot: election={self.election.ident} receipt={receipt} verifier={verifier} ranks={ranks}')
        return receipt


class CheckVotePage(IcelectView):
    methods = ['POST']

    def dispatch_request(self, ident: str):
        self.init_election(ident)

        if self.election.state != db.ElectionState.voting:
            flash('Voting in this election is no longer allowed.', 'danger')
            return redirect(self.election_url())

        form = CheckVoteForm()
        if not form.validate_on_submit():
            return redirect(self.election_url())

        sess = db.get_session()
        ballot = sess.scalar(select(db.Ballot).filter_by(election=self.election, receipt=form.receipt.data))

        return render_template(
            'check-vote.html',
            election=self.election, edata=self.edata,
            receipt=form.receipt.data,
            ballot=ballot,
            option_ranks=zip(self.edata.options, ballot.ranks) if ballot else [],
        )


class SetElectionState(IcelectView):
    methods = ['POST']

    def dispatch_request(self, ident: str):
        self.init_election(ident, admin_only=True)

        form = SetStateForm()
        if form.validate_on_submit():
            app.logger.info('Setting state of election {ident} to {form.new_state.data}')
            self.election.state = form.new_state.data
            db.get_session().commit()
            flash(f'State set to {self.election.state.friendly_name()}.', 'success')

        return redirect(self.election_url())


class BallotsPage(IcelectView):
    def dispatch_request(self, ident: str):
        self.init_election(ident)

        if self.election.state != db.ElectionState.results and not g.is_admin:
            flash('Election results are not available yet.', 'danger')
            return redirect(self.election_url())

        sess = db.get_session()
        ballots = sess.scalars(
            select(db.Ballot)
            .filter_by(election=self.election)
            .order_by(db.Ballot.receipt)
        )

        if request.endpoint == 'ballots_csv':
            file = StringIO()
            csw = csv.writer(file)
            csw.writerow(['receipt', 'nonce'] + self.edata.options)
            for ballot in ballots:
                csw.writerow([ballot.receipt, ballot.nonce] + ballot.ranks)

            return Response(
                response=file.getvalue(),
                mimetype='text/csv; charset=utf-8',
            )
        else:
            return render_template(
                'ballots.html',
                election=self.election, edata=self.edata,
                ballots=ballots,
            )


class ResultsPage(IcelectView):
    def dispatch_request(self, ident: str):
        self.init_election(ident)

        if self.election.state != db.ElectionState.results and not g.is_admin:
            flash('Election results are not available yet.', 'danger')
            return redirect(self.election_url())

        sess = db.get_session()
        result = sess.get(db.Result, self.election.election_id)
        if result is None:
            raise werkzeug.exceptions.NotFound("Election results not found")
        json = result.result

        num_votes = sess.scalar(select(func.count()).select_from(db.Ballot).filter_by(election=self.election))
        num_voters = sess.scalar(select(func.count()).select_from(db.CredHash).filter_by(election=self.election))
        schulze_order = json['schulze_order']

        return render_template(
            'results.html',
            election=self.election, edata=self.edata,
            num_votes=num_votes,
            num_voters=num_voters,
            condorcet_winner=self.edata.options[json['condorcet_winner']] if json['condorcet_winner'] is not None else None,    # type: ignore
            weak_condorcet_winners=[self.edata.options[w] for w in json['weak_condorcet_winners']],
            schulze_winners=[self.edata.options[w] for w in schulze_order[0]],
            schulze_layers=[[self.edata.options[w] for w in layer] for layer in schulze_order],
            beats=json['beats'],
            weights=json['weights'],
            strengths=json['strengths'],
        )



class VerifierDownload(IcelectView):
    def dispatch_request(self, ident: str):
        self.init_election(ident)

        if self.election.state not in (db.ElectionState.counting, db.ElectionState.results) or not (g.is_admin or g.is_reg):
            raise werkzeug.exceptions.Forbidden("Not available to you")

        sess = db.get_session()
        verifiers = list(sess.scalars(
            select(db.Verifier.verifier)
            .filter_by(election=self.election)
            .order_by(db.Verifier.verifier)
        ))

        out = [
            f'# Election: {ident}',
            f'# Verification key: {self.election.verify_key}',
        ] + verifiers + []

        return Response(
            response="\n".join(out),
            mimetype='text/plain; charset=utf-8',
        )


class LoginForm(FlaskForm):
    password = wtforms.PasswordField()
    login = wtforms.SubmitField("Log in")


class LoginPage(IcelectView):
    methods = ['GET', 'POST']

    def dispatch_request(self):
        form = LoginForm()
        if form.validate_on_submit():
            if form.password.data == config.ADMIN_PASSWORD:
                flash('You are logged in as the administrator.', 'success')
                session['role'] = 'admin'
                return redirect(url_for('index'))
            elif form.password.data == config.REGISTRAR_PASSWORD:
                flash('You are logged in as the registrar.', 'success')
                session['role'] = 'reg'
                return redirect(url_for('index'))
            else:
                flash('Invalid password.', 'danger')

        return render_template(
            'login.html',
            form=form,
        )


class LogoutPage(IcelectView):
    methods = ['POST']

    def dispatch_request(self):
        session.pop('role', None)
        return redirect(url_for('index'))


app.add_url_rule('/', view_func=MainPage.as_view('index'))
app.add_url_rule('/login', view_func=LoginPage.as_view('login'))
app.add_url_rule('/logout', view_func=LogoutPage.as_view('logout'))
app.add_url_rule('/e/<ident>/', view_func=ElectionPage.as_view('election'))
app.add_url_rule('/e/<ident>/vote', view_func=VotePage.as_view('vote'))
app.add_url_rule('/e/<ident>/check', view_func=CheckVotePage.as_view('check_vote'))
app.add_url_rule('/e/<ident>/ballots', view_func=BallotsPage.as_view('ballots'))
app.add_url_rule('/e/<ident>/ballots.csv', view_func=BallotsPage.as_view('ballots_csv'))
app.add_url_rule('/e/<ident>/verifiers.txt', view_func=VerifierDownload.as_view('verifiers'))
app.add_url_rule('/e/<ident>/results', view_func=ResultsPage.as_view('results'))
app.add_url_rule('/e/<ident>/admin/set-state', view_func=SetElectionState.as_view('set_state'))
