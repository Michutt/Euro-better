from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort
import sqlite3
from EuroBetter.auth import login_required
from EuroBetter.db import get_db

bp = Blueprint('blog', __name__)


@bp.route('/')
def index():
    db = get_db()
    matches = db.execute(
        ' SELECT country1, country2, id'
        ' FROM matches'
        ' ORDER BY id DESC'
    ).fetchall()
    return render_template('blog/index.html', matches=matches)


@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if g.user['username'] == 'admin':

        if request.method == 'POST':
            country1 = request.form['country1']
            country2 = request.form['country2']

            error = None

            if not country1 and not country2:
                error = 'Countries are required.'

            if error is not None:
                flash(error)
            else:
                db = get_db()
                db.execute(
                    'INSERT INTO matches (country1, country2)'
                    ' VALUES (?, ?)',
                    (country1, country2)
                )
                db.commit()
                return redirect(url_for('blog.index'))

        return render_template('blog/create.html')
    else:
        flash("You do not have permisions to do that!")
        return redirect(url_for('blog.index'))


def get_post(id):
    db = get_db()
    match = db.execute(
        'SELECT * FROM matches WHERE id = ?', (id,)
    ).fetchone()

    if match is None:
        abort(404, "Post id {0} doesn't exist.".format(id))

    return match


@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    match = get_post(id)

    if request.method == 'POST':
        country1 = request.form['country1']
        country2 = request.form['country2']
        result1 = request.form['result1']
        result2 = request.form['result2']
        error = None

        if not country1 and not country2:
            error = 'Countries are required.'

        db = get_db()
        bet = db.execute(
            ' SELECT result1, result2'
            ' FROM matches'
            ' WHERE id = ?',
            (id,)
        ).fetchone()
        print("LALALALA", bet[0])

        if bet[0] != None and bet[1] != None:
            error = 'Match is over'

        if error is not None:
            flash(error)
        elif result2 is not None and result1 is not None:
            db = get_db()
            db.execute(
                'UPDATE matches SET result1 = ?, result2 = ?'
                ' WHERE id = ?',
                (result1, result2, id)
            )
            db.commit()

            score_update(db, id)

            return redirect(url_for('blog.index'))
        else:
            db = get_db()
            db.execute(
                'UPDATE matches SET country1 = ?, country2 = ?'
                ' WHERE id = ?',
                (country1, country2, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', match=match)


@bp.route('/<int:id>/bet', methods=('GET', 'POST'))
@login_required
def bet(id):
    match = get_post(id)

    if request.method == 'POST':
        result1 = request.form['result1']
        result2 = request.form['result2']
        error = None

        if not result1 and not result2:
            error = 'Predictions are required!'

        # if type(result1) != int or type(result2) != int:
        #     error = 'You should type integers ;)'

        db = get_db()
        bet = db.execute(
            ' SELECT result1, result2'
            ' FROM matches'
            ' WHERE id = ?',
            (id,)
        ).fetchone()

        if bet[0] != None and bet[1] != None:
            error = 'Match is over'

        if error is not None:
            flash(error)
        else:
            db = get_db()

            db.row_factory = sqlite3.Row
            cur = db.cursor()
            cur.execute('SELECT * FROM bets')
            check = cur.fetchall()

            match_ids = []
            for x in check:
                if x[0] == g.user['id']:
                    match_ids.append(x[1])

            if not check or match['id'] not in match_ids:
                db.execute(
                    'INSERT INTO bets (user_id, match_id, result1, result2)'
                    ' VALUES (?, ?, ?, ?)', (g.user['id'], match['id'], result1, result2)
                )
                db.commit()
            else:
                flash("You have already betted")

            return redirect(url_for('blog.index'))

    return render_template('blog/bet.html', match=match)


@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM matches WHERE id = ?', (id,))
    db.execute('DELETE FROM bets WHERE match_id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))


def score_update(db, id):
    db.row_factory = sqlite3.Row
    cur = db.cursor()
    result = cur.execute(
        'SELECT result1, result2 FROM matches'
        ' WHERE id = ?',
        (id,)
    ).fetchone()

    bets = db.execute(
        'SELECT result1, result2, user_id'
        ' FROM bets'
        ' WHERE match_id = ?',
        (id,)
    ).fetchall()

    res = result[0] - result[1]

    for bet in bets:
        bet_res = bet[0] - bet[1]
        user_id = bet[2]

        score = cur.execute(
            'SELECT score FROM user'
            ' WHERE id = ?',
            (user_id,)
        ).fetchone()
        score = score[0]

        if bet[0] == result[0] and bet[1] == result[1]:
            score += 3
        elif res > 0 and bet_res > 0:
            score += 1
        elif res == bet_res:
            score += 1
        elif res < 0 and bet_res < 0:
            score += 1
        else:
            score += 0

        db.execute(
            'UPDATE user SET score = ?'
            ' WHERE id = ?',
            (score, user_id)
        )

        db.commit()



