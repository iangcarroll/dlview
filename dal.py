import requests
import pprint
import os

URL = 'https://api.delta.com/api2/mobile/getPnr'

def _getbody(fname, lname, pnr):
    return f"<retrievePnrRequest><confirmationNumber>{pnr}</confirmationNumber><disableMerchandiseSearch>false</disableMerchandiseSearch><firstName>{fname}</firstName><isCheckForUpsell>Y</isCheckForUpsell><lastName>{lname}</lastName><requestInfo><appId>mobile</appId><applicationVersion>5.5</applicationVersion><buildNumber>19658</buildNumber><channel></channel><channelId>mobile</channelId><deviceName>IPHONE</deviceName><deviceType>3x</deviceType><osName>iOS</osName><osVersion>14.0</osVersion><responseType>json</responseType><transactionId></transactionId></requestInfo><retrieveBy>confirmationNumber</retrieveBy><vacationsSearch>true</vacationsSearch></retrievePnrRequest>"

def _getheaders():
    return {
        'content-type': 'application/xml; charset=utf-8',
        'x-device-resolution-class': '3x',
        'tlioscnx': 'Wi-Fi',
        'accept': 'applicastion/json',
        'tliosloc': 'gn=my_trips:list&ch=my_trips',
        'accept-encoding': 'gzip;q=1.0, compress;q=0.5',
        'accept-language': 'en-us',
        'response-json': 'true',
        'user-agent': 'Fly Delta iPhone, iOS 14.0, 5.5, Phone',
        'x-dynatrace': 'MT_3_1_63164922190840_218_b00d7922-1fe8-4353-af19-6c4db642b0a6_0_1_332'
    }

def _getdo(obj):
    obj = obj.get('domainObjectList')
    if not obj:
        return []
    obj = obj.get('domainObject')
    if isinstance(obj, dict):
        return [obj]
    
    return obj

def makereq(fname, lname, pnr):
    body = _getbody(fname, lname, pnr) # done with those vars now
    headers = _getheaders()

    return requests.post(URL, data=body, headers=headers, proxies={
        "http": os.environ.get('IPB_HTTP'),
        "https": os.environ.get('IPB_HTTP')
    })

def decode(resp):
    resp = resp.get('retrievePnrResponse')
    if resp.get('status') != 'SUCCESS':
        return False
    
    state = {
        'tags': [],
        'remarks': [],
        'flags': [],
        'flights': [],
        'pax': [],
    }

    state['trip'] = resp.get('tripsResponse')[0].get('pnr')
    
    state['remarks'] = []
    for remark in _getdo(state['trip'].get('remarks')):
        state['remarks'].append({
            'text': remark.get('freeFormText'), 
            'type': remark.get('remarkType'),
            'ruc': remark.get('remarkType') == 'SPCL' and remark.get('freeFormText') == '***PASSENGER DECLINED ELITE COMP UPGRADE***'
        })
    
    for flag in _getdo(state['trip'].get('pnrFlags')):
        if not flag.get('name'):
            continue
        
        state['flags'].append({'name': flag.get('name'), 'value': flag.get('value')})

    for itin in _getdo(state['trip'].get('itineraries')):
        flights = _getdo(itin.get('flights'))

        for flight in flights:
            if isinstance(flight, str):
                continue

            state['flights'].append({
                'Origin': flight.get('origin').get('code'),
                'Destination': flight.get('destination').get('code'),
                'Distance': flight.get('distance'),
                'Status': flight.get('status'),
                'Marketing Carrier': flight.get('marketingAirlineCode'),
                'Operating Carrier': flight.get('operatingAirlineCode'),
                'J Upgrade Status': flight.get('upgradeStatus'),
                'W Upgrade Status': flight.get('upgradeStatusWCabin'),
                'Cabin': flight.get('brandAssociatedCabinId'),
                'Plane': flight.get('equipment').get('description'),
                'Equipment Change': flight.get('equipmentChange'),
                'Action Code': flight.get('currentActionCode'),
                'Prev Action Code': flight.get('previousActionCode'),
                'Ground Handled': flight.get('groundHandled'),
                'Cleaned': flight.get('cleanedFlag'),
                'Misconnect': flight.get('misconnectFlag'),
            })
    
    pax = _getdo(state['trip'].get('passengers'))

    for passenger in pax:
        pnr_name = passenger.get('pnrName')
        status = False

        if passenger.get('loyaltyAccounts') and passenger.get('loyaltyAccounts').get('domainObjectList').get('domainObject'):
            status = passenger.get('loyaltyAccounts').get('domainObjectList').get('domainObject').get('membershipStatusDesc')

        ssrs = []
        for ssr in _getdo(passenger.get('ssrs')):
            if ssr.get('code') == 'FQTU':
                continue
            ssrs.append({
                'code': ssr.get('code'),
                'remark': ssr.get('remarks').get('remark')
            })
        
        seats = []

        for seat in _getdo(passenger.get('flightSeats')):
            seats.append({
                'segment': seat.get('segmentId'),
                'seat': seat.get('seatNumber'),
                'ruc': seat.get('status') == None and seat.get('seatNumber') == None
            })
        
        phantom_segs = 0

        for seat in seats:
            if seat.get('ruc'):
                phantom_segs += 1

        state['pax'].append({
            'PNR Name': pnr_name.get('firstName') + ' ' + pnr_name.get('lastName'),
            'Customer ID': passenger.get('customerId'),
            'Checked In': passenger.get('checkedIn'),
            'Selectee': passenger.get('selectee'),
            'Do Not Board': passenger.get('doNotBoard'),
            'SSRs': ssrs,
            'Phantom Segments': phantom_segs
        })
    return state