# -*- coding: utf-8 -*-
"""
Created on Fri May 01 15:24:42 2015

@author: Neo
"""


import xml.etree.ElementTree as ET
import pprint
import re
import codecs
import json
"""
Change over-abbreviated street types to full-name

"""


lower = re.compile(r'^([a-z]|_)*$')
lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problemchars = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
direction_type_re = re.compile(r'\b[NSWE]\.?\s', re.IGNORECASE)
digit_re = re.compile(r'\d')
IH35_re = re.compile(r'I[hH]*(\s|-)35')
text_re = re.compile(r'[a-zA-Z]*\s*')
state_re = re.compile(r',\s*T[xX]')


CREATED = [ "version", "changeset", "timestamp", "user", "uid"]
EXPECTED_ST = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place",
               "Square", "Lane", "Road", "Trail", "Parkway", "Commons",
               "Cove", "Expressway"]
MAPPING_ST = { "Rd": "Road",
            "Rd.": "Road",
            "St": "Street",
            "St.": "Street",
            "Ave": "Avenue",
            "Ave.": "Avenue",
            "Ct": "Court",
            "Ct.": "Court",
            "Blvd": "Boulevard",
            "Blvd.": "Boulevard",
            "Cv": "Cove",
            "Cv.": "Cove",
            "Dr": "Drive",
            "Dr.": "Drive",
            "Expwy": "Expressway",
            "Expwy.": "Expressway",
            "Ln": "Lane",
            "Ln.": "Lane",
            "Hwy": "Highway",
            "Hwy.": "Highway"
            }
            
EXPECTED_DI = ["North","South","East","West"]
MAPPING_DI = {"N ": "North ",
              "N. ": "North ",
              "S ": "South ",
              "S. ": "South ",
              "W ": "West ",
              "W. ": "West ",
              "E ": "East ",
              "E. ": "East "}

def update_city(ct):
    mct = state_re.search(ct)
    if mct:
        ct = re.sub(mct.group(), "", ct)
    return ct
            
def update_state(st):
    return "TX"

def update_postcode(zp):
    mzp = text_re.search(zp)
    if mzp:
        zp = re.sub(mzp.group(), "", zp)
    zp = zp[0:5]
    return zp


def update_phone(phone):
    phone = phone.replace("+","")
    phone = phone.replace("(", "")
    phone = phone.replace(")","")
    phone = phone.replace("-","")
    phone = phone.replace(" ","")
    if phone.startswith("1"):
        phone = phone.replace("1","",1)
    phone = "+1(" + phone[0:3] + ")" + phone[3:6] + "-" + phone[6:]
    
    return phone



def update_name(name, MAPPING_ST):
    m = street_type_re.search(name)
    if m:
        street_type = m.group()
        if len(street_type) == 1 and not(digit_re.search(street_type)):
            # if the direction is at the end of the street
            # e.g. "Capital of TX Hwy N"
            # first put direction at the front
            # then do street_type search again
            name = name[-1] + " " + name[0:-2]
            m = street_type_re.search(name)
            street_type = m.group()
            
        if street_type in MAPPING_ST:
            #and (not bool(digit_re.search(street_type))): no need to make sure it is not numbers
            # e.g. "US 290", just keep it as it is        
            name = re.sub(street_type_re, MAPPING_ST[street_type], name)

    mm = direction_type_re.search(name)
    if mm:
        direction_type = mm.group()
        if direction_type not in EXPECTED_DI:
            name = re.sub(direction_type, MAPPING_DI[direction_type], name)
    
    mm_ih35 = IH35_re.search(name)    
    if mm_ih35:
        name = re.sub(mm_ih35.group(), "Interstate Highway 35", name)
        
    
    return name
    
    


def shape_element(element):
    node = {}
    if element.tag == "node" or element.tag == "way" or element.tag == "relation":
        print element.attrib['id']
        
        node['type'] = element.tag
        # Parse the attributes
        for atr in element.attrib:
            if atr in CREATED:
                if 'created' not in node:
                    node['created'] = {}
                node['created'][atr] = element.attrib[atr]
            elif atr in ['lat','lon']:
                if 'pos' not in node:
                    node['pos'] = [None, None]
                if atr == 'lat':
                    node['pos'][0] = float(element.attrib[atr])
                else:
                    node['pos'][1] = float(element.attrib[atr])            
            else:
                node[atr] = element.attrib[atr]
        # iterating over the tag children
        for tag in element.iter("tag"):
            if not problemchars.search(tag.attrib['k']):
                if lower_colon.search(tag.attrib['k']): # single colon tags
                    if tag.attrib['k'].find('addr') == 0: # single colon starts with addr
                        if 'address' not in node: # check if key 'address' exists
                            node['address'] = {}
                        sub_attr = tag.attrib['k'].split(':',1)
                        if sub_attr[1] == "street": # update street name
                            node['address'][sub_attr[1]] = update_name(tag.attrib['v'], MAPPING_ST) # update its name
                        elif sub_attr[1] == "postcode": # update the postcode
                            node['address'][sub_attr[1]] = update_postcode(tag.attrib['v'])
                        elif sub_attr[1] == "city": # update the city name
                            node['address'][sub_attr[1]] = update_city(tag.attrib['v'])
                        elif sub_attr[1] == "state": # update the state name
                            node['address'][sub_attr[1]] = update_state(tag.attrib['v'])
                        else:
                            node['address'][sub_attr[1]] = tag.attrib['v']
                    else: # other single colon tags just process normally
                        node[tag.attrib['k']] = tag.attrib['v']
                elif tag.attrib['k'].find(':') == -1: # tags without colon
                    if tag.attrib['k'].find('phone') == 0:
                        node['phone'] = update_phone(tag.attrib['v'])
                    else:
                        node[tag.attrib['k']] = tag.attrib['v']
                    
        # iterating over the nd children to get node_refs
        for nd in element.iter("nd"):
            if 'node_refs' not in node:
                node['node_refs'] = []
            node['node_refs'].append(nd.attrib['ref'])
            
        return node
    else:
        return None


def process_map(file_in, pretty = False):
    # You do not need to change this file
    file_out = "{0}.json".format(file_in)
    data = []
    with codecs.open(file_out, "w") as fo:
        for _, element in ET.iterparse(file_in):
            el = shape_element(element)
            if el:
                data.append(el)
                if pretty:
                    fo.write(json.dumps(el, indent=2)+"\n")
                else:
                    fo.write(json.dumps(el) + "\n")
    return data


if __name__ == "__main__":
#    data = process_map('austin_test.osm', True)
    data = process_map('austin_texas.osm', True)
#    for dd in data:
#        pprint.pprint(dd)