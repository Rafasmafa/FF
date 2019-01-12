#!/usr/bin/env python
# -*- coding: utf-8 -*- 

from mailchimp3 import MailChimp
from trello import TrelloApi
from templates.premium_no_screenshot import premium_no_screenshot
from templates.premium_w_screenshot import premium_w_screenshot
import requests
import argparse
import pprint
import os


class MailChimpCampaignCreator(object):


        def __init__(self):
            self.list_id = 'f875825c0f'
            self.segement_field_id = 'interests-ddaa47f9ce'
            self.trello_token = os.environ['TRELLO_TOKEN']
            self.trello_key = os.environ['TRELLO_API_KEY']
            self.mailchimp_key = os.environ['MAILCHIMP_API_KEY']
            self.client = MailChimp(mc_api=self.mailchimp_key)
            self.trello = TrelloApi(self.trello_key, self.trello_token)
            self.trello.set_token(self.trello_token)
            
            self.segments = {'ruby': 'd125b54ea5',
                             'python': '36af6f769b',
                             'javascript': 'c63ef1fad6',
                             'php':'dd47521189',
                             'mobile': 'ccae9429e5',
                             'crypto': '547568b68e'
                          
                          }

        def get_cards_to_send(self):
            trello_cards = []
            complete_cards = self.trello.lists.get_card('5c1674c0424cfa4164bc868b')
            for card in complete_cards:
                trello_cards.append(card)
            
            return trello_cards
        
        def create_campaigns(self, trello_cards):
            list_id = '3097db167f'
            for card in trello_cards:
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
                    "subject_line": card['name'],
                    "from_name": "FeastFlow",
                    "reply_to": 'hello@feastflow.com'}
                screenshot_url = self.get_screenshot(card)
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
                campaign.content.update(campaign.campaign_id, {'html':html})
        
        def get_list_segments(self, trello_card):
            
            segments = [] 
            for label in trello_card['labels']:
                segments.append(self.segments[label['name'].lower()])
                
            return segments
        
        def get_screenshot(self, trello_card):
            attachment = self.trello.cards.get_attachment(trello_card['id'])

            try:
                return attachment[0]["url"]
            except KeyError:
                return ''

        def get_card_content(self, trello_card):
            return trello_card['desc']

if __name__== "__main__":
    MCCC = MailChimpCampaignCreator()
    cards = MCCC.get_cards_to_send()
    MCCC.create_campaigns(cards)