from flask import Blueprint, render_template

pages = Blueprint('pages', __name__)

@pages.route('/page_<num>')
def get_page(num):
     return render_template('pages/page.html', num=num)