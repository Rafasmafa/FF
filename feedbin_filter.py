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
#from page_parser import get_lws_leads

class FeedbinFilter(object):

    def __init__(self):
        self.username = os.environ['FEEDBIN_USER']
        self.password = os.environ['FEEDBIN_PASSWORD']
        self.freelance_matches = []
        self.tech_matches_not_confirmed = []
        self.tech_matches = []
        self.budget_matches = []
        self.email_matches = []
        self.html_handler = HTML2Text()
        self.html_handler.ignore_images = True
        self.html_handler.ignore_tables = True
        self.html_handler.ignore_emphasis = True
        #self.html_handler.ignore_links = True
        self.authenticate()
        self.reddit_json = os.path.join('reddit/freelancer_list.json')
        self.tech_filters = ['python', 'php', 'wordpress',
                            'web developer', 'ruby', 'django',
                            'django', 'flask', 'drupal', 'ios',
                            'android', 'node', 'meteor', 'vue.js'
                            'web development', 'laravel',
                            'react','rails','html', 'css',
                            'javascript', 'java script','js', 'angular',
                            'shopify', 'product design', 'packaging design',
                            'package design', 'UX/UI', 'User Interface',
                            'UX Designer', 'UI Designer', 'Product Design',
                            'Branding', 'Animation', 'Logo Design', 'Illustration',
                            'Mobile Design', 'web design', 'website design',
                            'visual design', 'Graphic Design']


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
            'https://api.feedbin.com/v2/entries.json?per_page=1500',
            auth=(self.username, self.password))

        return response.text

    def get_reddit_username(self, entry):
        return re.findall(r'/u/.+', entry['author'])[0].strip('/u/')

    def get_known_reddit_usernames(self):
        with open(self.reddit_json, 'r') as fn:
            data = json.load(fn)

        with open('reddit/reddit_leads.json') as fn2:
            data.extend(json.load(fn2))

        return data

    def update_reddit_username(self, usernames):
        with open(self.reddit_json, 'r') as fn:
            data = json.load(fn)

        for name in usernames:
            data.append(name)

        with open(self.reddit_json, 'w') as fn:
            json.dump(data, fn)

    def get_reddit_leads(self, json_obj):
        entries = json.loads(json_obj)
        known_usernames = self.get_known_reddit_usernames()
        print len(known_usernames)
        new_names = []
        count = 0
        known_count = 0
        for entry in entries:
            if '[for hire]' in entry['title'].lower():
                for keyword in self.tech_filters:
                    if keyword.lower() in entry['content'].lower().encode('utf-8'):
                        username = self.get_reddit_username(entry)
                        if username not in known_usernames and username not in new_names:
                            new_names.append(username)
                            count += 1
                            break
                        else:
                            known_count += 1

        self.update_reddit_username(new_names)
        print 'Added {} usernames to lead file'.format(count)

    def filter_entries(self, json_obj, days_ago, extra=None):

        # Case doesnt matter for filters, they all get
        # moved to lower case when time to compare

        freelace_filters = ['freelance', 'remote', 'contract',
                            'short term', 'long term', 'free lance'
                            'contractor', 'gig', 'anywhere', 'project',
                            'free-lance', 'short-term', 'long-term', 'rfp']



        entries = json.loads(json_obj)
        entries = self.filter_based_on_date(entries, days_ago)

        print '{} new entries'.format(len(entries))
        entries = self.filter_negative_keywords(entries)
        #if extra:
            #entries.extend(extra)
        self.freelance_matches = self._filter(freelace_filters, entries, to_markdown=True)
        self.tech_matches_not_confirmed = self._filter(self.tech_filters, entries, to_markdown=True)
        self.tech_matches = self._filter(self.tech_filters, self.freelance_matches)
        self.freelance_matches = self.remove_duplicates(self.freelance_matches, self.tech_matches)


        email_regex = r'[\w\.-]+@[\w\.-]+'
        self.email_matches = self._filter_regex(email_regex, self.tech_matches)
        self.tech_matches = self.remove_duplicates(self.tech_matches, self.email_matches)

        self.tech_matches_not_confirmed = self.remove_duplicates(
            self.tech_matches_not_confirmed, self.freelance_matches)
        self.tech_matches_not_confirmed = self.remove_duplicates(
            self.tech_matches_not_confirmed, self.tech_matches)
        self.tech_matches_not_confirmed = self.remove_duplicates(
            self.tech_matches_not_confirmed, self.email_matches)

        print '{} leads satisfy freelance filters'.format(len(self.freelance_matches))
        print '{} leads match tech filters'.format(len(self.tech_matches))
        print '{} leads match tech filters but might not be remote or freelance'.format(
            len(self.tech_matches_not_confirmed))
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
        'yellow': ['angular', 'vue', 'react', 'front-end', 'front end'],
        'orange': ['android', 'ios', 'react native'],
        'purple': ['php', 'wordpress', 'web developer', 'web development',
                   'web design', 'website', 'php', 'drupal', 'laravel'],
        'blue':  ['js', 'node', 'meteor', 'javascript', 'java script'],
        'lime': ['web design', 'mobile design', 'UX/UI', 'User Interface',
                 'UX Designer', 'UI Designer', 'UX expert','UI expert'],
        'pink': ['graphic design', 'logo', 'illustration', 'animation',
                 'branding', 'Product Design', 'product design',
                 'packaging design', 'illustrate']
        }

    existing_cards = trello_obj.lists.get_card(trello_list_id)
    for card in existing_cards:
        for label in label_dict:
            for i in label_dict[label]:
                desc = card['desc'].encode('utf-8').lower()
                name = card['name'].encode('utf-8').lower()
                if i in desc or i in name :
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

def post_to_trello(freelance, tech, tech_not_confirmed, email):
    freelance_id = '5bc91cfdcaee543fd465743d'
    tech_matches_id = '5bc91d0bf7d2b839faaf71b8'
    email_matches_id = '5bc91d160d6b977c2b22e90e'
    tech_matches_not_confirmed_id = '5cb1ec921fa7ff624beebc4b'
    #budget_matches_id = '5bc91d1b4dc1245f1403812f'
    board_id = '5af708fdeffb84570bfc177e'

    token = os.environ['TRELLO_TOKEN']
    key = os.environ['TRELLO_API_KEY']
    trello = TrelloApi(key, token)
    trello.set_token(token)

    _post(freelance, freelance_id, trello)
    _post(tech, tech_matches_id, trello)
    _post(tech_not_confirmed, tech_matches_not_confirmed_id, trello)
    _post(email, email_matches_id, trello)
    tag_cards(trello, tech_matches_id)
    tag_cards(trello, tech_matches_not_confirmed_id)
    tag_cards(trello, email_matches_id)


def _post(list_of_entries, trello_list_id, trello_obj):
    existing_cards = get_card_names(trello_obj.lists.get_card(trello_list_id))
    for entry in list_of_entries:
        if entry['title'].lower() not in existing_cards:
            entry['content'] += "\n Source: <" + entry["url"] + ">"
            trello_obj.cards.new(entry['title'], trello_list_id, entry['content'])

if __name__== "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--days', '-d', dest='days' , default=1,
                    type=int, action='store',
                    help="Number of days to look for entries")
    parser.add_argument('--get_lws', action='store_true', default=False)
    parser.add_argument('--generate_reddit_leads', '-grl', action='store_true', default=False)
    args = parser.parse_args()

    feedbin = FeedbinFilter()
    entries = feedbin.get_entries()
    if args.generate_reddit_leads:
        feedbin.get_reddit_leads(entries)
        sys.exit()

    #if args.get_lws:
        #extra = get_lws_leads()

    feedbin.filter_entries(entries, args.days)
    post_to_trello(feedbin.freelance_matches,
                   feedbin.tech_matches,
                   feedbin.tech_matches_not_confirmed,
                   feedbin.email_matches)
