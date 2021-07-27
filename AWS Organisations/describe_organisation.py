#
# Simple script to retrieve and display AWS Organisation details, not pretty, but functional...
#
import boto3
import json

org = boto3.client('organizations')

organisation = {}
accounts = {}
organisation_units = {}
delegated_administrators = {}

try:
    # get the core organisation information
    response = org.describe_organization()['Organization']
    organisation['id'] = response['Id']
    organisation['arn'] = response['Arn']
    organisation['management_account'] = response['MasterAccountId']

    # the organisation root ID is needed
    response = org.list_roots()['Roots']
    organisation['root'] = response[0]['Id']

    # retrieve any delegated administration accounts
    params = {}
    processed_all = False
    while not processed_all:
        response = org.list_delegated_administrators(**params)
        if 'NextToken' in response:
            params['NextToken'] = response['NextToken']
        else:
            processed_all = True
        for account in response['DelegatedAdministrators']:
            delegated_services = []
            for delegation in org.list_delegated_services_for_account(AccountId=account['Id'])['DelegatedServices']:
                delegated_services.append(delegation['ServicePrincipal'])
            delegated_administrators[account['Id']] = delegated_services

    # retrieve all accounts
    params = {}
    processed_all = False
    while not processed_all:
        response = org.list_accounts(**params)
        if 'NextToken' in response:
            params['NextToken'] = response['NextToken']
        else:
            processed_all = True
        for account in response['Accounts']:
            accounts[account['Id']] = {"arn": account['Arn'], "status": account['Status'], "email": account['Email'], "name": account['Name']}

    # retrieve OUs (only goes below root as this is AWS Control Tower behaviour)
    for child in org.list_children(ParentId=organisation['root'], ChildType='ORGANIZATIONAL_UNIT')['Children']:
        ou_id = child['Id']
        ou = org.describe_organizational_unit(OrganizationalUnitId=ou_id)
        accounts_in_ou =[]
        max_length = 0
        for account in org.list_accounts_for_parent(ParentId=ou_id)['Accounts']:
            accounts_in_ou.append(account['Id'])
            if len(accounts[account['Id']]['name']) > max_length:
                max_length = len(accounts[account['Id']]['name'])
        organisation_units[child['Id']] = {'name': ou['OrganizationalUnit']['Name'], 'accounts': accounts_in_ou, 'max_length': max_length}

    print(f"\nRoot: {organisation['id']} / {organisation['root']}\n      {organisation['management_account']} | {accounts[organisation['management_account']]['email']}\n")
    last = False
    for ou in organisation_units:
        name = organisation_units[ou]['name']
        print(f"  {name}: {ou}")
        for ou_account in organisation_units[ou]['accounts']:
            width = 4 + organisation_units[ou]['max_length']
            print(f"{accounts[ou_account]['name']:>{width}}: {ou_account} | {accounts[ou_account]['email']}")
            if ou_account in delegated_administrators:
                for delegation in delegated_administrators[ou_account]:
                    print(f"{' ':>{width + 2}}Delegated: {delegation}")
        print()

except Exception as e:
    import traceback
    traceback.print_exc()