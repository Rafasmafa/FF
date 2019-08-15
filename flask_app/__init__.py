import sys

from flask import Flask, render_template, request
from views.pages import pages
from mailchimp_campaign_creator import MailChimpCampaignCreator

app = Flask(__name__)
app.register_blueprint(pages, url_prefix='/pages')


@app.route('/', methods=['POST'])
def create_camapigns():
    if request.method == 'POST':
        try:
            MCCC = MailChimpCampaignCreator()
            cards = MCCC.get_cards_to_send()
            MCCC.create_campaigns(cards, in_flask=True)
            return 'Campaigns Created!'
        except Exception as e:
            print e.message
            return ('There was a error creating campaigns.'
                    'Please contact Nick \n Error: {}'.format(e))

@app.route('/')
def homepage():
    return render_template("home.html")

if __name__ == "__main__":
    app.run()
