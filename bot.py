import html
import re
import json
import time
import os.path
import requests
import sys
from datetime import datetime




from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class AccessDenied(Exception):
    pass
    
def authenticate(address, client_secret):
  
    host = address + ':3334/connect/token'
    auth_info = {'client_id':'mpx', 'client_secret': client_secret, 'grant_type':'client_credentials', 'response_type':'code id_token', 'scope':'authorization mpx.api ptkb.api'}
    head = {'Content-Type' : 'application/x-www-form-urlencoded'}
    
    
    r = requests.post(host, auth_info,  verify=False)
    response = r.text
    
    if r.status_code != 200:
        raise AccessDenied(response.text)
    
    print(r.json())
    access_token=r.json()["access_token"]
    expires=r.json()["expires_in"]
    print(access_token,expires)
    return access_token, expires

def print_response(response, check_status=True):
    #if check_status:
     #   assert response.status_code == 200
    return response
    
def parse_form(data):
    return re.search('action=[\'"]([^\'"]*)[\'"]', data).groups()[0], {
        item.groups()[0]: html.unescape(item.groups()[1])
        for item in re.finditer(
            'name=[\'"]([^\'"]*)[\'"] value=[\'"]([^\'"]*)[\'"]',
            data
        )
    }

def read_incident_file(file_name):
    incident_list = []
    if not os.path.exists(file_name):
        return []
    with open(file_name, "r") as fh:
        for line in fh:
            incident_list.append(line.rstrip())
            print(line.rstrip())
    return incident_list

def write_incident_file(file_name, incident):
    with open(file_name, "w") as fh:
        fh.write(incident + "\n")


def send_telegram_message(inc,asa, settings):
    url = settings['core_url'] + """/#/incident/incidents/view/""" + inc["id"]
    msg = ""
    msg += "[" + inc["key"] +"](" + url + ")  [" + inc['name'] + "]"
    msg += " Подробности: " + asa["description"]
    #https:// text part didn't work for me when passing in HTML parse_mode
    for chat_id in settings['chat_id']:
        requests.post("https://api.telegram.org/bot" + settings['token'] + "/sendMessage", data = {'chat_id': chat_id, 'text':msg, 'parse_mode': 'Markdown'})


if __name__ == "__main__":
    settings = {}
    settings['logfile'] = 'filename' #'/root/processed_incident_list.log'
    settings['core_url'] = 'url'   #https://maxpatrolsiemaddress
    settings['time_from'] = 6000 #in the last 10 minutes
    
    settings['client_secret'] = 'secret' # from corecfg get
   
   #tg bot
    settings['token'] = 'token'
    settings['chat_id'] = ['chat id']

    access_token, expires = authenticate(settings['core_url'],settings['client_secret'])
    sent_list = read_incident_file(settings['logfile'])
    #hi ver23
    time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    unix_time_old = int(time.time()) - settings['time_from']
    unix_time = str(datetime.utcfromtimestamp(unix_time_old).strftime(time_format))
    print(unix_time)
    #unix_time = datetime.fromtimestamp(unix_time_bly, tz=pytz.timezone("UTC")).strftime(self.__time_format)
    post_params = r'{"offset":0,"limit":50,"groups":{"filterType":"no_filter"},"timeFrom":"' + str(unix_time) + \
                  r'","timeTo":null,"filterTimeType":"creation","filter":{"select":["key","name","category",' + \
                  r'"type","status","created","assigned"], "where":"","orderby":[{"field":"created",' + \
                  r'"sortOrder":"descending"}, {"field":"status","sortOrder":"ascending"},' + \
                  r'{"field":"severity","sortOrder":"descending"}]},"queryIds":["all_incidents"]}'
    print(post_params)
    headers = {"Authorization": "Bearer "+ access_token}
    res = requests.post(settings['core_url'] + '/api/v2/incidents/', json=json.loads(post_params),headers=headers,verify=False).text

    recv_list = []
    print(res)
    for inc in (reversed(json.loads(res)["incidents"])):
        print(inc["key"])
        if not sent_list or (int(sent_list[-1]) < int(inc["key"].split('-')[-1])):
            rec = requests.get(settings['core_url'] + '/api/incidentsReadModel/incidents/' + inc["id"],headers=headers,verify=False).text
            print(rec)
            asa = json.loads(rec)
            #print(asa["description"])
            send_telegram_message(inc,asa, settings)
            #send_to_thehive(inc,asa,settings)
            recv_list.append(inc["key"].split('-')[-1])

    if recv_list:
        write_incident_file(settings['logfile'], recv_list[-1])