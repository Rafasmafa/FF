import requests
import argparse
import sys
import json
import os
import re
from datetime import datetime, timedelta


class FeedbinFilter(object):

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.freelance_matches = []
        self.tech_matches = []
        self.budget_matches = []
        self.email_matches = []

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
        entries = self.filter_base_on_date(entries, days_ago)

        print '{} new entries'.format(len(entries))
        self.freelance_matches = self._filter(freelace_filters, entries)
        self._save_file('freelance_matches.json', self.freelance_matches)

        self.tech_matches = self._filter(tech_filters, self.freelance_matches)
        self._save_file('tech_matches.json', self.tech_matches)

        self.freelance_matches = self.remove_duplicates(self.freelance_matches, self.tech_matches)

        self.budget_matches = self._filter_regex(r'\$\d+.+', self.tech_matches)
        self._save_file('budget_matches.json', self.budget_matches)
        self.tech_matches = self.remove_duplicates(self.tech_matches, self.budget_matches)

        email_regex = r'[\w\.-]+@[\w\.-]+'
        self.email_matches = self._filter_regex(email_regex, self.tech_matches)
        self._save_file('email_matches.json', self.email_matches)

        self.tech_matches = self.remove_duplicates(self.tech_matches, self.email_matches)

        print '{} leads satisfy freelance filters'.format(len(self.freelance_matches))
        print '{} leads match tech filters'.format(len(self.tech_matches))
        print '{} leads match budget filters'.format(len(self.budget_matches))
        print '{} leads match email filters'.format(len(self.email_matches))


    def filter_base_on_date(self, entries, days_ago):
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

    def clean_html(self, raw_html):
      cleanr = re.compile(r'<[^>]+>')
      cleantext = re.sub(cleanr, '', raw_html)
      return cleantext

    def _save_file(self, path, data):
        path = os.path.join(os.getcwd(), path)
        with open(path, 'w') as jf:
            json.dump(data, jf, indent=4)

    def _filter_regex(self, pattern, data):
        filtered_data = []

        for entry in data:
            content =  self.clean_html(entry['content'])
            if re.findall(pattern, content):
                entry['content'] = content
                filtered_data.append(entry)

        return filtered_data

    def _filter(self, filters, data):
        filtered_data = []
        for entry in data:
            content = entry['content'].lower()
            for filter in filters:
                if filter in content and '[for hire]' not in entry['title'].lower():
                    filtered_data.append(entry)
                    break
        return filtered_data

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
