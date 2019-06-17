from flask import Blueprint, redirect

home = Blueprint('home', __name__)

@home.route('/')
def index():

    return redirect(url_for('home'))
