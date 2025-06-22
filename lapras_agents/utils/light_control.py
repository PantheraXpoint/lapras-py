from phue import Bridge
import argparse
import json
import urllib.request

# bridge IP from OpenWrt
BRIDGE_IP = '192.168.0.182' 

USERNAME = "P2laHGvjzthn7Ip5-fAAIbVB9ulu9OlHWk8L7Yex"
b = Bridge(BRIDGE_IP, USERNAME)
b.connect()


###################################################################################
###################################################################################
### urllib.request version ###
BASE_URL = f"http://{BRIDGE_IP}/api/{USERNAME}"


### create new group ###
def create_group_with_urllib(new_name, new_lights):
    
    new_data = {'name': new_name, 'lights': new_lights}
    req = urllib.request.Request(
        BASE_URL+'/groups/',
        data=json.dumps(new_data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    with urllib.request.urlopen(req) as response:
        result = json.load(response)
        print("Response:", result)


### set name/lights of group ###
def set_group_with_urllib(group_id, name=None, lights=None):
    GROUP_URL = f'{BASE_URL}/groups/{group_id}'
    group_data = {}
    if name!=None:
        group_data['name']=name
    if lights!=None:
        group_data['lights']=lights
        
    req = urllib.request.Request(
        GROUP_URL,
        data=json.dumps(group_data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    with urllib.request.urlopen(req) as response:
        result = json.load(response)
        print("Response:", result)

def set_group_act_with_urllib(group_id, data):
    ### set actions of group ###
    ACT_URL = f'{BASE_URL}/groups/{group_id}/action'
    req = urllib.request.Request(
        ACT_URL,
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    with urllib.request.urlopen(req) as response:
        result = json.load(response)
        print("Response:", result)

###################################################################################
###################################################################################




def main():
    parser = argparse.ArgumentParser(description="Control all Hue lights ON/OFF")
    parser.add_argument('-g', '--group', choices=['left', 'right', 'all'], required=True,
                        help='Specify which group to control')
    parser.add_argument('-o', '--on', choices=['on', 'off'],
                        help='Switch lights ON or OFF')
    parser.add_argument('-b', '--bri', type=int, help='Brightnes(0-254)')
    parser.add_argument('-H', '--hue', type=int, help='Hue(0-360)')
    parser.add_argument('-s', '--sat', type=int, help='Saturation(0-254)')
    parser.add_argument('-e', '--effect', choices=['none', 'colorloop'], type=str, help='Effect')
    parser.add_argument('-a', '--alert', choices=['none', 'select', 'lselect'], type=str, help='Alert')
    
    
    # process input values
    args = parser.parse_args()
    
    raw = vars(args)
    data = {}
    
    group_id = b.get_group_id_by_name(args.group)
    
    # input data --> dictionary
    for key in raw:
        if key=='group': continue
        if raw[key] is not None:
            data[key] = raw[key]
            if key=='on':
                data[key] = raw[key]=='on'
            
            # Hue bridge use scale [0, 65535], so need to convert
            if key=='hue':
                data[key] = int(raw[key] / 360 * 65535)
    
    
    ### set group action with phue ###
    b.set_group(group_id, data)
    
    group = b.get_group(group_id)
    print(group)
    
    
    
    ### set group action with urllib ###
    # set_group_act_with_urllib(group_id, data)
    
    
    
    ###################################################################################
    ###################################################################################
    ### create/set new group ###
    # b.create_group('new_group', [<list of light id's>]]) 

    # b.set_group(1, 'lights', [2, 3, 7, 8])
    # b.set_group(1, 'name', 'right')

    # b.set_group(2, 'lights', [1, 5, 6, 10])
    # b.set_group(2, 'name', 'left')
    
    # b.set_group(3, 'lights', [1, 2, 3, 5, 6, 7, 8, 10])
    # b.set_group(3, 'name', 'all')
    
    
    
    ### urllib ver.###
    
    # create_group_with_urllib('new_switch', [])
    # set_group_with_urllib(5, name='Switch2')
    # set_group_with_urllib(5, lights=['1', '5', '6', '9'])
    # set_group_with_urllib(5, name='Switch2', lights=['1', '5', '6', '9'])
    ###################################################################################
    ###################################################################################
    
    
    
    ###################################################################################
    ###################################################################################
    ### Set each parameter one by one ###
    
    # b.set_group(group_id, 'on', True/False)
    # b.set_group(group_id, 'bri', bright)
    # b.set_group(group_id, 'hue', hue)
    # b.set_group(group_id, 'sat', sat)
    # b.set_group(group_id, 'effect', effect)
    # b.set_group(group_id, 'alert', alert)
    
    ###################################################################################
    ###################################################################################
      
    

        
if __name__ == '__main__':
    main()