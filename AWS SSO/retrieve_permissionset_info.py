#
# retrieve and render AWS SSO PermissionSet information, would be nice to
# find a way to indent the policy rendering, i know this is a hack, please don't judge me... 🖖
#
import boto3
import json
import os

sso = boto3.client('sso-admin')

instances = sso.list_instances() # using [0] is daft, but not sure it is possible to have two instances in a region?
instance_arn = instances['Instances'][0]['InstanceArn']
identity_store = instances['Instances'][0]['IdentityStoreId']
print(f"Retrieving PermissionSets for AWS SSO Instance {instance_arn.split('/')[1]}, Identity Store {identity_store}...")

store_policies = True
policy_directory = f"{os.path.dirname(os.path.realpath(__file__))}/Policies"
processed_all = False
permission_sets = []
params = {"InstanceArn": instance_arn, "MaxResults": 100}
while not processed_all:
    response = sso.list_permission_sets(**params)
    if 'NextToken' in response:
        params['NextToken'] = response['NextToken']
    else:
        processed_all = True
    permission_sets = permission_sets.copy() + response['PermissionSets'].copy()

for arn in permission_sets:
    print()
    detail = sso.describe_permission_set(InstanceArn=instance_arn, PermissionSetArn=arn) # https://boto3.amazonaws.com/v1/documentation/api/1.18.10/reference/services/sso-admin.html#SSOAdmin.Client.describe_permission_set
    relay_state = detail['PermissionSet']['RelayState'] if 'RelayState' in detail['PermissionSet'] else f"not set"
    print(f"{detail['PermissionSet']['Name']}:\n  Description: {detail['PermissionSet']['Description']}\n  ARN: {detail['PermissionSet']['PermissionSetArn']}\n  Session duration: {detail['PermissionSet']['SessionDuration']}\n  Relay URL: {relay_state}")

    params = {"InstanceArn": instance_arn, "PermissionSetArn": arn, "MaxResults": 100}
    processed_all = False
    accounts = []
    while not processed_all:
        response = sso.list_accounts_for_provisioned_permission_set(**params) # https://boto3.amazonaws.com/v1/documentation/api/1.18.10/reference/services/sso-admin.html#SSOAdmin.Client.list_accounts_for_provisioned_permission_set
        if 'NextToken' in response:
            params['NextToken'] = response['NextToken']
        else:
            processed_all = True
        for account in response['AccountIds']:
            accounts.append(account)
        account_list = f"none"
        if len(accounts) > 0:
            account_list = ", ".join(accounts)
        print(f"  Assigned to AWS Account{'s'[:len(accounts)^1]}: {account_list}")

    response = sso.list_managed_policies_in_permission_set(InstanceArn=instance_arn, PermissionSetArn=arn, MaxResults=100) # only max 10 possible, so no need to do the NextToken thing!? https://boto3.amazonaws.com/v1/documentation/api/1.18.10/reference/services/sso-admin.html#SSOAdmin.Client.list_managed_policies_in_permission_set
    if response['AttachedManagedPolicies']:
        max_length = 0
        for policy in response['AttachedManagedPolicies']:
            if len(policy['Name']) > max_length:
                max_length = len(policy['Name'])
        print("  AWS Managed Policies:")
        for policy in response['AttachedManagedPolicies']:
            print(f"    {policy['Name']:>{max_length}}: {policy['Arn']}")    
    else:
        print(f"  AWS Managed Policies: none")

    response = sso.get_inline_policy_for_permission_set(InstanceArn=instance_arn, PermissionSetArn=arn) # https://boto3.amazonaws.com/v1/documentation/api/1.18.10/reference/services/sso-admin.html#SSOAdmin.Client.get_inline_policy_for_permission_set
    if response['InlinePolicy']:
        print("  Custom policy", end='')
        if store_policies:
            if not os.path.exists(policy_directory):
                os.makedirs(policy_directory)
            with open(f"{policy_directory}/{policy['Name']}.json", 'w') as w:
                w.write(json.dumps(json.loads(response['InlinePolicy']), indent=4))
            print(f" (saved to ./Policies/{policy['Name']}.json)", end='')
        print(":")
        print(json.dumps(json.loads(response['InlinePolicy']), indent=4))
    else:
        print("  No additional policy attached")

print(f"\nRead {len(permission_sets)} PermissionSet{'s'[:len(permission_sets)^1]}")