import sys

from flask import Flask, render_template, request
from views.pages import pages
from mailchimp_campaign_creator import MailChimpCampaignCreator

app = Flask(__name__)
app.register_blueprint(pages, url_prefix='/pages')


@app.route('/', methods=['POST'])
def create_camapigns():
    if request.method == 'POST':
        MCCC = MailChimpCampaignCreator()
        cards = MCCC.get_cards_to_send()
        MCCC.create_campaigns(cards, in_flask=True)
        return sys.stdout

    return 'Error Creating Campaigns'

@app.route('/')
def homepage():
    return render_template("home.html")

#@app.route('/page_<num>')
#def pages(num):
#     return render_template('pages/page.html', num=num)
#     return render_template('pages/page.html', num=num)


if __name__ == "__main__":
    app.run()
