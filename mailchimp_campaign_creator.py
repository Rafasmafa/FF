#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import os
import re
import time
import neverbounce_sdk
import sys


from mailchimp3 import MailChimp
from trello import TrelloApi
from templates.premium_no_screenshot import premium_no_screenshot
from templates.premium_w_screenshot import premium_w_screenshot
from markdown2 import Markdown
from selenium import webdriver
from PIL import Image
from resizeimage import resizeimage
from selenium.webdriver.chrome.options import Options
from requests.exceptions import ConnectionError


class MailChimpCampaignCreator(object):

        def __init__(self):
            self.list_id = 'f875825c0f'
            self.segement_field_id = 'interests-ddaa47f9ce'
            self.trello_token = os.environ['TRELLO_TOKEN']
            self.trello_key = os.environ['TRELLO_API_KEY']
            self.mailchimp_key = os.environ['MAILCHIMP_API_KEY']
            self.never_bouce_apy_key = os.environ['NB_APY_KEY']
            self.client = MailChimp(mc_api=self.mailchimp_key)
            self.trello = TrelloApi(self.trello_key, self.trello_token)
            self.trello.set_token(self.trello_token)
            self.markdown2html = Markdown()

            self.segments = {'ruby': 'd125b54ea5',
                             'python': '36af6f769b',
                             'javascript (backend/node/meteor)': 'c63ef1fad6',
                             'php':'dd47521189',
                             'mobile': 'ccae9429e5',
                             'javascript (frontend/angular/react/vue)': 'e46d8964c6',
                             'interaction design (web design/mobile design/ui/ux)': '6958995281',
                             'graphic design (branding/logos/animations/illustrations)': '6f583d899e'

                             }

        def get_cards_to_send(self):
            trello_cards = []
            complete_cards = self.trello.lists.get_card('5bb1e965e5336c5390e7e505')
            for card in complete_cards:
                trello_cards.append(card)

            return trello_cards

        def create_campaigns(self, trello_cards, in_flask=False):
            for card in trello_cards:
                print "Creating campaign for {}".format(card['name'].encode('utf-8'))
                sys.stdout.flush()
                if self.validate_links(card) and self.validate_email(card):
                    segments = self.get_list_segments(card)
                    data_dict = {}
                    data_dict['type'] = 'regular'
                    data_dict['content_type'] = 'html'
                    data_dict["recipients"] = {'list_id': self.list_id,
                                               'segment_opts': {'match': 'any'}}
                    data_dict["recipients"]['segment_opts']['conditions'] = [{"condition_type": "Interests",
                                                                             'op': 'interestcontains',
                                                                            'field': self.segement_field_id,
                                                                            'value': segments}]
                    data_dict['settings'] = {
                        "title": card['name'],
                        "subject_line": card['name'],
                        "from_name": "FeastFlow",
                        "reply_to": 'hello@feastflow.com'}
                    screenshot_url = self.get_screenshot(card, in_flask)

                    if screenshot_url:
                        html = premium_w_screenshot
                    else:
                        html = premium_no_screenshot

                    html.encode('utf-8')
                    html = html.replace("%IMAGE%", screenshot_url)
                    html = html.replace("%TITLE%", card['name'])
                    html = html.replace("%CONTENT%", self.get_card_content(card))

                    campaign = self.client.campaigns
                    campaign.create(data_dict)
                    campaign.content.get(campaign.campaign_id)
                    campaign.content.update(
                        campaign.campaign_id, {'html': html})
                print 'done!'

        def get_list_segments(self, trello_card):

            segments = []
            for label in trello_card['labels']:
                segments.append(self.segments[label['name'].lower()])

            return segments

        def get_screenshot(self, trello_card, in_flask=False):
            attachment = self.trello.cards.get_attachment(trello_card['id'])

            try:
                # if an attachment exists and its an image
                # do not get a screenshot
                if attachment[0]["url"][-3] == 'png':
                    return attachment[0]["url"]
                else:
                    # if its not an image then raise a key error so
                    # we can hit the exception below and get a screenshot
                    raise KeyError
            except (KeyError, IndexError):
                try:
                    url_regex = r'URL: <https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)>'
                    url = re.search(url_regex, str(
                        trello_card['desc'].encode('utf-8'))).group()
                    url = url.strip('URL: <')
                    url = url.strip('>')
                    if in_flask:
                        print "setting up chromedriver"
                        sys.stdout.flush()
                        chrome_options = Options()
                        chrome_options.binary_location = \
                            os.environ['GOOGLE_CHROME_BIN']
                        chrome_options.add_argument('--disable-gpu')
                        chrome_options.add_argument('--no-sandbox')
                        chrome_options.add_argument('--headless')
                        chrome_options.add_argument('--disable-dev-shm-usage')
                        driver = webdriver.Chrome(
                            executable_path=str(os.environ.get('CHROMEDRIVER_PATH')),
                            chrome_options=chrome_options)
                    else:
                        DRIVER = os.path.join(os.getcwd(), 'drivers', 'chromedriver')
                        driver = webdriver.Chrome(DRIVER)
                    driver.get(url)
                    time.sleep(3)  # wait for page to load
                    screenshot = driver.save_screenshot('lead_screenshot.png')
                    print "got screenshot"
                    sys.stdout.flush()
                    driver.quit()

                    # resize image
                    with open('lead_screenshot.png', 'r+b') as f:
                        with Image.open(f) as image:
                            img = resizeimage.resize_width(image, 600)
                            img.save('lead_screenshot.png', image.format)

                    ss_path = os.path.abspath('lead_screenshot.png')
                    self.upload_file_to_trello_card(trello_card['id'], ss_path)
                    os.remove(ss_path)

                    return self.trello.cards.get_attachment(
                        trello_card['id'])[0]["url"]

                except AttributeError:
                    print 'Failed to get screenshot for {}'.format(
                        trello_card['name'].encode('utf-8'))
                    return ''

        def get_card_content(self, trello_card):
            return self.markdown2html.convert(trello_card['desc'])

        def upload_file_to_trello_card(self, card_id, file_path):
            """
            Upload a local file to a Trello card as an attachment.
            File must be less than 10MB (Trello API limit).
            :param card_id: The relevant card id
            :param file_path: path to the file to upload
            Returns a request Response object. It's up to you to check the
                status code.
            """
            ATTACHMENTS_URL = 'https://api.trello.com/1/cards/%s/attachments'

            params = {'key': self.trello_key, 'token': self.trello_token}
            files = {'file': open(file_path, 'rb')}
            url = ATTACHMENTS_URL % card_id
            requests.post(url, params=params, files=files)
            print 'successfully uploaded screenshot to trello card'
            sys.stdout.flush()

        def validate_links(self, trello_card):
            print "Validating all links in trello card"
            sys.stdout.flush()
            url_regex = r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)'
            links = re.finditer(url_regex, str(trello_card['desc'].encode('utf-8')))
            for link in links:
                try:
                    request = requests.get(link.group(0))
                except ConnectionError:
                    self.__move_card_to_broken_link_column(trello_card)
                    return False

                if request.status_code in [200, 403, 999, 406]:
                    continue
                else:
                    self.__move_card_to_broken_link_column(trello_card)
                    print "Broken Link in {} with status code {}: {}".format(
                        trello_card['name'].encode('utf-8'),
                        request.status_code,
                        link.group(0))

                    return False
            print "All links valid"
            sys.stdout.flush()
            return True

        def validate_email(self, trello_card):
            print "Print validating all emails in trello card"
            sys.stdout.flush()
            client = neverbounce_sdk.client(api_key=self.never_bouce_apy_key)
            email_regex = r'[\w\.-]+@[\w\.-]+'
            emails = re.findall(email_regex, str(trello_card['desc'].encode('utf-8')))
            for address in emails:
                if not address[-1].isalpha():
                    del address[-1]
                resp = client.single_check(address)

                if resp['result'] in ['valid', 'catchall', 'unknown']:
                    continue
                else:
                    self.__move_card_to_broken_link_column(trello_card)
                    print "Email Bounced in {}: {} with return code '{}'".format(
                        trello_card['name'].encode("utf-8"), address, resp['result'])
                    return False
            print "All emails valid"
            sys.stdout.flush()
            return True

        def __move_card_to_broken_link_column(self, trello_card):
            # move card to broken link column
            self.trello.cards.update_idList(
                trello_card['id'], "5c55ae09f1d4eb1efb039019")


if __name__ == "__main__":
    MCCC = MailChimpCampaignCreator()
    cards = MCCC.get_cards_to_send()
    MCCC.create_campaigns(cards)
