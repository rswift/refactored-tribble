#
# Simple script to retrieve AWS account details and provide a query mechanism...
#
# Retrieves all accounts in an AWS Organisation, stores them then provides a simple
# means of looking up by account number or account name, offline.
#
# One time (and occasionally if there are new accounts being added) use with the
# --refresh option to pull back, note this'll need valid AWS credentials for boto3
# to sweep up and use...
#
import boto3
import logging
import os
import sys
import json
import readline

log_file = "{}/.aws/.account_info.log".format(os.path.expanduser('~'))
data_file = "{}/.aws/.account_info.dat".format(os.path.expanduser('~'))

logging.basicConfig(filename=log_file, encoding='utf-8', level=logging.DEBUG)
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)


def retrieve_accounts():
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        logging.debug(f"{identity=}")

    except Exception as e:
        logging.error(f"Exception validating AWS access: {e}")
        print(f"Failed to connect, check the AWS credentials?")
        return

    accounts = {}
    try:
        org = boto3.client('organizations')
        # retrieve all accounts
        params = {}
        processed_all = False
        i = 0
        while not processed_all:
            response = org.list_accounts(**params)
            if 'NextToken' in response:
                params['NextToken'] = response['NextToken']
            else:
                processed_all = True
            for account in response['Accounts']:
                i = i + 1
                # double up for ease, if you are looking at this thinking "we've got 1000+ accounts in our org" then
                # this script probably isn't for you - it'll work, but there may be better approaches... store the
                # salient details against the key 'id'
                accounts[account['Id']] = {"arn": account['Arn'], "email": account['Email'], "id": account['Name']}
                accounts[account['Name']] = {"arn": account['Arn'], "email": account['Email'], "id": account['Id']}
        with open(data_file, 'w') as accounts_info:
            accounts_info.write(json.dumps(accounts))
        print(f"Read {i} account{'s'[:i^1]} into {data_file}")

    except Exception as e:
        logging.error(f"Exception retrieving AWS accounts: {e}")
        print(f"Failed to retrieve AWS accounts")
        return

class MyCompleter(object):  # Custom completer
  """ shamelessly lifted: https://stackoverflow.com/a/7821956 """
  def __init__(self, options):
    self.options = sorted(options)

  def complete(self, text, state):
    if state == 0:  # on first trigger, build possible matches
        if text:  # cache matches (entries that start with entered text)
            self.matches = [s for s in self.options 
                                if s and s.startswith(text)]
        else:  # no text entered, all matches possible
            self.matches = self.options[:]

    # return match indexed by state
    try: 
        return self.matches[state]
    except IndexError:
        return None

class style:
   NORMAL = '\033[0m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'

def parse_input():
    accounts = {}
    try:
        with open(data_file, 'r') as accounts_info:
            accounts = json.loads(accounts_info.read())
    except Exception as e:
        logging.error(f"Exception reading account info: {e}")
        print(f"Failed to read account information! Try running again with --refresh")
        return

    completer = MyCompleter(list(accounts.keys()))
    readline.set_completer(completer.complete)
    readline.parse_and_bind('tab: complete')

    print("Use tab to complete, empty search to exit")
    lookup = "None" # hahaha...
    while lookup is not None:
        lookup = input("Lookup: ") or None
        if lookup:
            print(f"\n{lookup}is {style.BOLD}{accounts[lookup]['id']}{style.NORMAL} - {accounts[lookup]['email']}\n")

if __name__ == "__main__":
    refresh = False
    if len(sys.argv) == 2 and sys.argv[1] == "--refresh":
        refresh = True
    logging.debug(f"{refresh=}")

    if refresh:
        retrieve_accounts()
    else:
        parse_input()