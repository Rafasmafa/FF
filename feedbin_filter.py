import requests
import argparse
import sys
import json
import os
import re
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
                            'contractor', 'gig', 'part time', 'anywhere']

        tech_filters = ['python', 'php', 'wordpress',
                        'web developer', 'ruby', 'django',
                        'django', 'flask', 'drupal', 'ios',
                        'android', 'node', 'meteor', 'bitcoin',
                        'solidity']


        entries = json.loads(json_obj)
        entries = self.filter_based_on_date(entries, days_ago)

        print '{} new entries'.format(len(entries))
        self.freelance_matches = self._filter(freelace_filters, entries, to_markdown=True)
        self._save_file('freelance_matches.json', self.freelance_matches)

        self.tech_matches = self._filter(tech_filters, self.freelance_matches)
        self._save_file('tech_matches.json', self.tech_matches)

        self.freelance_matches = self.remove_duplicates(self.freelance_matches, self.tech_matches)

        self.budget_matches = self._filter_budget(5000, self.tech_matches)
        self._save_file('budget_matches.json', self.budget_matches)

        email_regex = r'[\w\.-]+@[\w\.-]+'
        self.email_matches = self._filter_regex(email_regex, self.tech_matches)
        self._save_file('email_matches.json', self.email_matches)

        self.tech_matches = self.remove_duplicates(self.tech_matches, self.budget_matches)
        self.tech_matches = self.remove_duplicates(self.tech_matches, self.email_matches)

        print '{} leads satisfy freelance filters'.format(len(self.freelance_matches))
        print '{} leads match tech filters'.format(len(self.tech_matches))
        print '{} leads match budget filters'.format(len(self.budget_matches))
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

    def _filter(self, filters, data, to_markdown=False):
        filtered_data = []
        for entry in data:
            content = entry['content'].lower()
            for filter in filters:
                if filter in content and '[for hire]' not in entry['title'].lower():
                    if to_markdown:
                        entry['content'] = self.html_handler.handle(entry['content'])
                    filtered_data.append(entry)
                    break
        return filtered_data

def clean_html(raw_html):
    cleanr = re.compile(r'<[^>]+>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def get_card_names(trello_cards):
    names = []
    for card in trello_cards:
        names.append(card['name'])

    return names

def post_to_trello(freelance, tech, email, budget):
    freelance_id = '5bc91cfdcaee543fd465743d'
    tech_matches_id = '5bc91d0bf7d2b839faaf71b8'
    email_matches_id = '5bc91d160d6b977c2b22e90e'
    budget_matches_id = '5bc91d1b4dc1245f1403812f'
    board_id = '5af708fdeffb84570bfc177e'

    token = os.environ['TRELLO_TOKEN']
    key = os.environ['TRELLO_API_KEY']
    trello = TrelloApi(key, token)
    trello.set_token(token)

    existing_freelance_cards = get_card_names(trello.lists.get_card(freelance_id))
    existing_tech_cards = get_card_names(trello.lists.get_card(tech_matches_id))
    existing_email_cards = get_card_names(trello.lists.get_card(email_matches_id))
    existing_budget_cards = get_card_names(trello.lists.get_card(budget_matches_id))

    for entry in freelance:
        if entry['title'] not in existing_freelance_cards:
            trello.cards.new(entry['title'], freelance_id, entry['content'])

    for entry in tech:
        if entry['title'] not in existing_tech_cards:
            trello.cards.new(entry['title'], tech_matches_id, entry['content'])

    for entry in email:
        if entry['title'] not in existing_email_cards:
            trello.cards.new(entry['title'], email_matches_id, entry['content'])

    for entry in budget:
        if entry['title'] not in existing_budget_cards:
            trello.cards.new(entry['title'], budget_matches_id, entry['content'])


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
                   feedbin.email_matches,
                   feedbin.budget_matches)
