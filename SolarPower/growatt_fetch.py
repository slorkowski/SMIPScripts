# Purpose: Get data from Growatt API
#   Depends on the Growatt API Script
#   This script assumes it is configured with a "custom" parameter that defines API credentials in one of two ways
#   For a single user: {"username":"YOURGROWATTUSERNAME","password":"YOURGROWATTPASSWORD"}
#   For multiple users: {"growattCredentials":"WIFIADAPTERSERIALNUMBER1,GROWATTUSERNAME1,GROWATTPASSWORD1|WIFIADAPTERSERIALNUMBER2,GROWATTUSERNAME2,GROWATTPASSWORD2"}
#
import json
from datetime import datetime, timedelta
# reverse engineering
import pickle
from pprint import pprint
from inspect import getmembers, isfunction
# /reverse engineering
from thinkiq.model.equipment import Equipment
from thinkiq.model.attribute import Attribute
from thinkiq.history import value_stream, StatusCodes
from thinkiq.history.vst import Vst
from thinkiq_context import get_context
from growatt_api_73152 import GrowattApi

print (GrowattApi.testing(GrowattApi, "Updating data from Growatt API..."))

# Find out what we're updating
context = get_context()                                 # the context object holds runtime information such as the equipment id and data stored between runs
parent_id = context.std_inputs.node_id
parent_node = Equipment.get_from_id(parent_id)
#print(vars(parent_node))

# Find its attributes (hack around poor documentation, should be a better way!)
attribs = []
for var in vars(parent_node):
    try:
        #pprint(getattr(parent_node.attributes, var))
        attribs.append(getattr(parent_node.attributes, var))
    except:
        #couldn't get the current from the attributes collection, so its not really an attribute
        pass

# Find credentials
username = ""
password = ""
try:
    username = context.custom_inputs.username
    password = context.custom_inputs.password
except:
    try:
        credentials = context.custom_inputs.growattCredentials
        credentials = credentials.split("|")
        for credential in credentials:
            credParts = credential.split(",")
            serialnumber = credParts[0]
            if (serialnumber.lower() == parent_node.display_name.lower()):
                username = credParts[1]
                password = credParts[2]
    except:
        print ("No Growatt credentials set in custom inputs. Quitting")
        quit() 
print ("Found credentials for " + parent_node.display_name)

# Make times
time_start = datetime.now()-timedelta(seconds=10)
time_end = datetime.now()

# Find data for this user and this data collector
api = GrowattApi()
api.server_url = "https://server-us.growatt.com/"
login_response = api.login(username, password)
plant_list = api.plant_list(login_response['user']['id'])
for plant in plant_list['data']:
  plant_id = plant['plantId']
  plant_name = plant['plantName']
  plant_info=api.plant_info(plant_id)
  for device in plant_info['deviceList']:
    device_sn = device['deviceSn']
    if device_sn.lower() == parent_node.display_name.lower():
        print("Found " + parent_node.display_name + " in plant " + plant_name)
        try:
            for attrib in attribs:
                #pprint(attrib)
                strVal = device[attrib.description];
                numVal = ''
                for char in strVal:
                    if char in '1234567890.':
                        numVal += char
                print (" - Need to update " + attrib.relative_name + " from datasource: " + attrib.description + ", with value: " + str(numVal))
                
                # Create value as stream
                vs = value_stream.ValueStream(None, time_start, time_end)
                vst1 = Vst(numVal, StatusCodes.Good, time_start)
                print (vst1)
                vs.add_vst(vst1)

                attrib.save_value_stream(vs)
        except:
            print("Could not parse response attributes")
        print("Device data: " + json.dumps(device), end='\n')