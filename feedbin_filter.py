import requests
import argparse
import sys
import json
import os
import re
from difflib import SequenceMatcher

from html2text import HTML2Text
from datetime import datetime, timedelta
from trello import TrelloApi

class FeedbinFilter(object):

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.freelance_matches = []
        self.tech_matches = []
        self.budget_matches = []
        self.email_matches = []
        self.html_handler = HTML2Text()
        self.html_handler.ignore_images = True
        self.html_handler.ignore_tables = True
        self.html_handler.ignore_emphasis = True
        #self.html_handler.ignore_links = True
        self.authenticate()


    def authenticate(self):
        response = requests.get(
            'https://api.feedbin.com/v2/authentication.json',
            auth=(self.username, self.password))
        status_code = response.status_code

        if status_code == 200:
            print 'Authentication Successful'

        else:
            print 'username or password is incorrect'
            sys.exit(0)

    def get_entries(self):
        response = requests.get(
            'https://api.feedbin.com/v2/entries.json?per_page=250',
            auth=(self.username, self.password))

        return response.text

    def filter_entries(self, json_obj, days_ago):

        freelace_filters = ['freelance', 'remote', 'contract',
                            'short term', 'long term', 'free lance'
                            'contractor', 'gig', 'anywhere', 'project',
                            'free-lance', 'short-term', 'long-term']

        tech_filters = ['python', 'php', 'wordpress',
                        'web developer', 'ruby', 'django',
                        'django', 'flask', 'drupal', 'ios',
                        'android', 'node', 'meteor', 'bitcoin',
                        'solidity', 'web development', 'laravel',
                        'react','rails', 'crypo', 'smart contract',
                        'html', 'css', 'javascript', 'java script','js', 'angular',
                        'shopify' ]


        entries = json.loads(json_obj)
        entries = self.filter_based_on_date(entries, days_ago)

        print '{} new entries'.format(len(entries))
        entries = self.filter_negative_keywords(entries)
        self.freelance_matches = self._filter(freelace_filters, entries, to_markdown=True)
        self.tech_matches = self._filter(tech_filters, self.freelance_matches)
        self.freelance_matches = self.remove_duplicates(self.freelance_matches, self.tech_matches)


        email_regex = r'[\w\.-]+@[\w\.-]+'
        self.email_matches = self._filter_regex(email_regex, self.tech_matches)
        self.tech_matches = self.remove_duplicates(self.tech_matches, self.email_matches)

        print '{} leads satisfy freelance filters'.format(len(self.freelance_matches))
        print '{} leads match tech filters'.format(len(self.tech_matches))
        print '{} leads match email filters'.format(len(self.email_matches))


    def filter_based_on_date(self, entries, days_ago):
        filtered = []
        days_dt = (datetime.now() - timedelta(days=days_ago)).isoformat()
        print 'Getting entries from {} days ago until now'.format(days_ago)
        for entry in entries:
            if entry['published'] > days_dt:
                filtered.append(entry)
        return filtered

    def remove_duplicates(self, list1, list2):
        """Deletes all the entries in list1 that are
            in list2"""
        temp1 = []
        temp2 = []
        for l1_entry in list1:
            for l2_entry in list2:
                if cmp(l1_entry, l2_entry) == 0:
                    temp1.append(l1_entry)

            if l1_entry not in temp1:
                temp2.append(l1_entry)

        return temp2

    def _save_file(self, path, data):
        path = os.path.join(os.getcwd(), path)
        with open(path, 'w') as jf:
            json.dump(data, jf, indent=4)

    def _filter_budget(self, budget, data):
        filtered_data = []
        for entry in data:
            content =  clean_html(entry['content'])
            digits = [int(s.strip('$')) for s in content.split() if s.strip('$').isdigit()]

            for string in content.split():
                if 'k' in string.lower():
                    try:
                        int(s.strip('k'))
                        if int >= 5:
                             filtered_data.append(entry)
                    except ValueError:
                        pass

            for digit in digits:
                if digit >= budget:
                    filtered_data.append(entry)

        return filtered_data

    def _filter_regex(self, pattern, data):
        filtered_data = []

        for entry in data:
            content =  clean_html(entry['content'])
            if re.findall(pattern, content):
                entry['content'] = content
                filtered_data.append(entry)

        return filtered_data

    def filter_negative_keywords(self, data):
        negative_filters = ['full time', 'fulltime', 'full-time', '401k' ,'401(k)',
                            'internship', 'career', 'on site only', 'on-site only' ]
        filtered_data = []
        for entry in data:
            if entry['content']:
                content = clean_html(entry['content'].lower())
                dont_add = False
                for filter in negative_filters:
                    if filter in content or '[for hire]' in entry['title'].lower():
                        dont_add = True
                if not dont_add:
                    filtered_data.append(entry)
        return filtered_data

    def is_duplicate(self, entries, entry_to_compare):
        for entry in entries:
            m = SequenceMatcher(None, entry_to_compare['content'], entry['content'])
            ratio = m.ratio()

            if ratio < .75:
                continue
            else:
                return True
        return False

    def _filter(self, filters, data, to_markdown=False, include_neg=True):
        filtered_data = []
        for entry in data:
            content = clean_html(entry['content'].lower())
            for filter in filters:
                if filter in content or filter in entry['title'].lower():
                    if to_markdown:
                        entry['content'] = self.html_handler.handle(entry['content'])
                    if not self.is_duplicate(filtered_data, entry):
                        filtered_data.append(entry)
                    break
        return filtered_data

def clean_html(raw_html):
    #===========================================================================
    # cleanr = re.compile(r'<[^>]+>')
    # cleantext = re.sub(cleanr, '', raw_html)
    # return cleantext
    #===========================================================================
    return raw_html

def get_card_names(trello_cards):
    names = []
    for card in trello_cards:
        names.append(card['name'].lower())

    return names

def tag_cards(trello_obj, trello_list_id):
    label_dict = {
        'red': ['ruby', 'rails', 'shopify'],
        'green': ['python', 'django', 'flask'],
        'yellow': ['smart contract', 'crypo', 'bitcoin', 'solidity'],
        'orange': ['android', 'ios',],
        'purple': ['php', 'wordpress', 'web developer', 'web development',
                   'web designer', 'web design', 'website', 'php', 'drupal',
                   'laravel'],
        'blue':  ['js', 'node', 'meteor', 'react', 'javascript', 'angular', 'vue' 'java script']
        }

    existing_cards = trello_obj.lists.get_card(trello_list_id)
    for card in existing_cards:
        for label in label_dict:
            for i in label_dict[label]:
                desc = card['desc'].encode('utf-8')
                if i in desc.lower():
                    if label not in __get_current_labels(card):
                        trello_obj.cards.new_label(card['id'], label)
                        new_label = label
                        card = trello_obj.cards.get(card['id'])
                        while new_label not in __get_current_labels(card):
                            pass
                            # waiting for label to update

def __get_current_labels(trello_card):
    labels = []
    for label in trello_card['labels']:
        labels.append(str(label['color']))

    return labels

def post_to_trello(freelance, tech, email):
    freelance_id = '5bc91cfdcaee543fd465743d'
    tech_matches_id = '5bc91d0bf7d2b839faaf71b8'
    email_matches_id = '5bc91d160d6b977c2b22e90e'
    #budget_matches_id = '5bc91d1b4dc1245f1403812f'
    board_id = '5af708fdeffb84570bfc177e'

    token = os.environ['TRELLO_TOKEN']
    key = os.environ['TRELLO_API_KEY']
    trello = TrelloApi(key, token)
    trello.set_token(token)

    _post(freelance, freelance_id, trello)
    _post(tech, tech_matches_id, trello)
    _post(email, email_matches_id, trello)
    tag_cards(trello, tech_matches_id)
    tag_cards(trello, email_matches_id)


def _post(list_of_entries, trello_list_id, trello_obj):
    existing_cards = get_card_names(trello_obj.lists.get_card(trello_list_id))
    for entry in list_of_entries:
        if entry['title'].lower() not in existing_cards:
            entry['content'] += "\n Source: <" + entry["url"] + ">"
            trello_obj.cards.new(entry['title'], trello_list_id, entry['content'])

if __name__== "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--username', '-u', dest='username' , default=None,
                        type=str, action='store',
                        help="Email account username")
    parser.add_argument('--password', '-p', dest='password' , default=None,
                        type=str, action='store',
                        help="Email account password")
    parser.add_argument('--days', '-d', dest='days' , default=14,
                    type=int, action='store',
                    help="Number of days to look for entries")
    args = parser.parse_args()

    feedbin = FeedbinFilter(args.username, args.password)
    entries = feedbin.get_entries()
    feedbin.filter_entries(entries, args.days)
    post_to_trello(feedbin.freelance_matches,
                   feedbin.tech_matches,
                   feedbin.email_matches,)
