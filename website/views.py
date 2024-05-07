from flask import Flask, render_template, send_file, request, Blueprint, make_response
import requests
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
import os
import json
views = Blueprint('views', __name__)
credential = DefaultAzureCredential()

subscription_id = ""
resource_group_name = ""
workspace_name = ""

@views.route('/')
def home():
    # Retrieve subscription ID, resource group name, workspace name from request or configuration   
    # Initialize Resource Management client
    resource_client = ResourceManagementClient(credential, subscription_id)

    # Get analytic rules using Azure Management API
    url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}/providers/Microsoft.SecurityInsights/alertRules?api-version=2024-03-01"
    
    # Make authenticated request using requests library
    response = requests.get(url, headers={'Authorization': 'Bearer ' + credential.get_token('https://management.azure.com/').token})
    
    if response.status_code == 200:
        rules_json = response.json()
        rule_names = [rule['properties']['displayName'] for rule in rules_json['value']]
        return render_template('home.html', rule_names=rule_names)
    else:
        return render_template('home.html', error=f"Failed to retrieve analytic rules: {response.text}")
    
@views.route('/download-template', methods=['GET'])
def download_template():
    # Retrieve rule name from query parameters
    rule_name = request.args.get('rule_name')
    if not rule_name:
        return "Error: Rule name not provided."
    
    try:
        # Get analytic rules using Azure Management API
        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}/providers/Microsoft.SecurityInsights/alertRules?api-version=2024-03-01"
        
        # Make authenticated request using requests library
        response = requests.get(url, headers={'Authorization': 'Bearer ' + credential.get_token('https://management.azure.com/').token})
        
        if response.status_code == 200:
            rules_json = response.json()
            for rule in rules_json.get('value', []):
                if rule.get('properties', {}).get('displayName') == rule_name:
                    # Remove unnecessary properties from the rule
                    rule = remove_unnecessary_properties(rule)
                    rule = generate_arm_template(rule)

                    # Create ARM template JSON string
                    arm_template_json = json.dumps(rule, indent=4)
                    
                    # Create response with ARM template content
                    response = make_response(arm_template_json)
                    
                    # Set content type and headers
                    response.headers['Content-Type'] = 'application/json'
                    response.headers['Content-Disposition'] = f'attachment; filename={rule_name}.json'
                    
                    return response
            return "Error: Rule not found."
        else:
            return "Failed to retrieve analytic rules."
    except Exception as e:
        return f"An error occurred: {e}"

# Remove unnecessary properties from the rule before saving it as JSON
def remove_unnecessary_properties(rule):
    # Remove 'id' and 'etag' properties from the rule
    if 'id' in rule:
        del rule['id']
    if 'etag' in rule:
        del rule['etag']
    
    # Remove 'lastModifiedUtc' property from 'properties' dictionary
    if 'properties' in rule and 'lastModifiedUtc' in rule['properties']:
        del rule['properties']['lastModifiedUtc']

    return rule


def generate_arm_template(rule):
    # Define ARM template structure
    arm_template = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "workspace": {
                "type": "string"
            }
        },
        "resources": [
            {
                "id": f"[concat(resourceId('Microsoft.OperationalInsights/workspaces/providers', parameters('workspace'), 'Microsoft.SecurityInsights'),'/alertRules/{rule['name']}')]",
                "name": f"[concat(parameters('workspace'),'/Microsoft.SecurityInsights/{rule['name']}')]",
                "type": "Microsoft.OperationalInsights/workspaces/providers/alertRules",
                "kind": "Scheduled",
                "apiVersion": "2022-11-01-preview",
                "properties": rule['properties']
            }
        ]
    }
    return arm_template
