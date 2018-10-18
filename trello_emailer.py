import smtplib
import argparse
from trello import TrelloApi
from email.mime.text import MIMEText

# Trello key and token will need to be regenerated after 15 days
# As of right now they only have read access
key = 'c1a5b8cdfdbce640845601eef881e701'
token = '72f2d406d56f96680142f11a1b9ca9161a5fa0462787294d18279c273282a238'
email_list_id = '5bb28890b2537c3ca92ef6ed'
board_id = '5af708fdeffb84570bfc177e'


server = smtplib.SMTP('smtp.gmail.com:587')
server.ehlo()
server.starttls()

def send_email(fromaddr, toaddrs, msg, username, password, subject=''):
    subject = 'New Lead From Feast Flow: {}'.format(subject)

    for address in toaddrs:
        message = """From: {}\nTo: {}\nSubject: {}\n\n{}
        """.format(fromaddr, address, subject, msg)

        server.login(username,password)
        server.sendmail(fromaddr, toaddrs, message)



def get_trello_cards():
    trello = TrelloApi(key, token)
    return trello.lists.get_card(email_list_id)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--email', '-e', default=None, dest='fromaddrs',
                        type=str, action='store',
                        help='Email to send from (Note: this only works with '
                        'gmail as of now, also you will need to change some '
                        'security settings on google)')
    parser.add_argument('--sendto', '-st', default=None, dest='toaddrs',
                        action='append',
                        help='A list of email address you want to send to')
    parser.add_argument('--username', '-u', dest='username' , default=None,
                        type=str, action='store',
                        help="Email account username")
    parser.add_argument('--password', '-p', dest='password' , default=None,
                        type=str, action='store',
                        help="Email account password")
    parser.add_argument('--cards', '-c', dest='card_names', default=[],
                        action='append',
                        help='List of card names you want to send')
    args = parser.parse_args()

    cards_to_email = get_trello_cards()
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    for card in cards_to_email:
        try:
            if args.card_names:
                # only send the card names given
                if card['name'] in args.card_names:
                    send_email(
                        args.fromaddrs, args.toaddrs, card['desc'],
                        args.username, args.password, card['name'])
            else:
                send_email(
                    args.fromaddrs, args.toaddrs, card['desc'],
                    args.username, args.password, card['name'])
        except Exception as e:
            raise Exception('Email failed to send: {}'.format(e.message))
    print 'email sent!'

    server.quit()


if __name__== "__main__":
    main()
