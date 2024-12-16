from aiohttp import web
from aiohttp.web import Request, Response, json_response
import random

routes = web.RouteTableDef()

domain_state = {
    'hub_url': '',
    'domain_id': None,
    'secret': None,
    'item_ids': {}, # ItemID : Item Description, this is for all items hosted by this domain
    'item_names' : {}, # Name: ItemID
    'users': {}, # UserID : User State
    'owned': [], # ItemIDs for objects owned here, but in other domains, these could also end up in the users inventory etc
    'locations': {
        'foyer': {
            'items_id': [], #ItemIDs for the items located here
            'items_name': [],
            'exits': {'north': 'classroom', 'east': None}
        },
        'classroom': {
            'items_id': [], #ItemIDS for the items located here
            'items_name': [],
            'exits': {'south': 'foyer', 'down': 'podium', 'west': 'podium'}
        },
        'podium': {
            'items_id': [], #ItemIDs for the items located here
            'items_name': [],
            'exits': {'up': 'classroom', 'east': 'classroom'},
            'cabinet_state': 'locked', # locked, closed, open
            'switch_state': 'down',
            'screen_state': 'blank' # blank, password, won
        }
    }
}

domain_items = [
    {
        "name": "paper",
        "description":"A piece of paper with writing on it.",
        "verb": {
          "read":'The paper reads <q>XYZZY</q>'
        },
    },
    {
        "name": "key",
        "description":"A small key, as if for a locker or cabinet.",
        "verb": {},
        "depth": 1
    },
]

@routes.post('/newhub')
async def register_with_hub_server(req: Request) -> Response:
    """Used by web UI to connect this domain to a hub server.
    
    1. web calls domain's /register, with hub server URL payload
    2. domain calls hub server's /register, with name, description, and items
    3. hub server replies with domain's id, secret, and item identifiers
    """
    # partially implemented for you:
    url = await req.text()
    async with req.app.client.post(url+'/register', json={
          'url': whoami,
          'name': "MP10",
          'description': "An example domain based in Siebel 1404 and its surroundings.",
          'items': domain_items,
      }) as resp:
          data = await resp.json()
          if 'error' in data:
              return json_response(status=resp.status, data=data)
    
    # TO DO: store the url and values in the returned data for later use
    # Store hub information
    domain_state['hub_url'] = url
    domain_state['domain_id'] = data['id']
    domain_state['secret'] = data['secret']
    
    # TO DO: clear any user/game state to its initial state
    domain_state['users'].clear()
    domain_state['owned'].clear()
    domain_state['item_ids'].clear()
    domain_state['item_names'].clear()

    for location in domain_state['locations'].values():
        location['items_id'].clear()
        location['items_name'].clear()

    domain_state['locations']['podium']['cabinet_state'] = 'locked'
    domain_state['locations']['podium']['switch_state'] = 'down'
    domain_state['locations']['podium']['screen_state'] = 'blank'

    for i, item_id in enumerate(data['items']):
        domain_items[i]['id'] = item_id
        item_desc = domain_items[i]
        domain_state['item_ids'][item_id] = item_desc
        domain_state['item_names'][item_desc['name']] = item_id
    
    # Place paper in foyer (first item)
    paper_id = data['items'][0]
    paper_name = domain_items[0]['name']
    domain_state['locations']['foyer']['items_id'].append(paper_id)
    domain_state['locations']['foyer']['items_name'].append(paper_name)

    # Add key to owned items (second item)
    key_id = data['items'][1]
    domain_state['owned'].append(key_id)

    return json_response(data={'ok': 'Domain registered successfully'})


@routes.post('/arrive')
async def register_with_hub_server(req: Request) -> Response:
    """Called by hub server each time a user enters or re-enters this domain."""
    data = await req.json()

    # Verify secret matches
    if data['secret'] != domain_state['secret']:
        return json_response(status=403, data={'error': 'Invalid secret'})
    
    user_id = data['user']
    user_state = {}
    if user_id in domain_state['users']:
        # Update existing user - clear current item dictionaries
        user_state = domain_state['users'][user_id]
        for itemdic in user_state['items_id'].values():
            itemdic.clear()
        for itemdic in user_state['items_name'].values():
            itemdic.clear()
        # Update location to foyer and add to visited locations
        user_state['location'] = 'foyer'
        user_state['visited_locations'].add('foyer')
    else:
        # Create new user state object
        # Create new user state object with dual indexing
        user_state = {
            'items_id': {
                'owned': {},    # items from this domain in inventory
                'carried': {},  # items from other domains in inventory
                'dropped': {},  # items left in this domain
                'prize': {}     # items to find
            },
            'items_name': {
                'owned': {},
                'carried': {},
                'dropped': {},
                'prize': {}
            },
            'location': 'foyer',
            'visited_locations': {'foyer'}
        }
    
    unused_depth = []
    
    # Process owned items
    for item in data['owned']:
        user_state['items_id']['owned'][item['id']] = item
        user_state['items_name']['owned'][item['name']] = item['id']
        
    # Process carried items
    for item in data['carried']:
        user_state['items_id']['carried'][item['id']] = item
        user_state['items_name']['carried'][item['name']] = item['id']
        
    # Process dropped items
    for item in data['dropped']:
        user_state['items_id']['dropped'][item['id']] = item
        user_state['items_name']['dropped'][item['name']] = item['id']
        # Add to domain's item dictionaries
        domain_state['item_ids'][item['id']] = item
        domain_state['item_names'][item['name']] = item['id']
        # Place item in specified location
        location = item['location']
        if location in domain_state['locations']:
            if item['id'] not in domain_state['locations'][location]['items_id']:
                domain_state['locations'][location]['items_id'].append(item['id'])
            if item['name'] not in domain_state['locations'][location]['items_name']:
                domain_state['locations'][location]['items_name'].append(item['name'])
    
    # Process prize items
    for item in data['prize']:
        user_state['items_id']['prize'][item['id']] = item
        user_state['items_name']['prize'][item['name']] = item['id']
        # Add to domain's item dictionaries
        domain_state['item_ids'][item['id']] = item
        domain_state['item_names'][item['name']] = item['id']
        depth = item['depth']
        
        if depth == 0:
            # Place in classroom
            if item['id'] not in domain_state['locations']['classroom']['items_id']:
                domain_state['locations']['classroom']['items_id'].append(item['id'])
            if item['name'] not in domain_state['locations']['classroom']['items_name']:
                domain_state['locations']['classroom']['items_name'].append(item['name'])
        elif depth == 1:
            # Place in podium
            if item['id'] not in domain_state['locations']['podium']['items_id']:
                domain_state['locations']['podium']['items_id'].append(item['id'])
            if item['name'] not in domain_state['locations']['podium']['items_name']:
                domain_state['locations']['podium']['items_name'].append(item['name'])
        else:
            # Track items we couldn't place
            unused_depth.append(item)
            
    domain_state['users'][user_id] = user_state
    return json_response(status=200, data={'unused_items_depth': unused_depth})


@routes.post('/dropped')
async def register_with_hub_server(req: Request) -> Response:
    """Called by hub server each time a user drops an item in this domain.
    The return value must be JSON, and will be given as the location on subsequent /arrive calls
    """
    data = await req.json()
    
    # Verify secret matches
    if data['secret'] != domain_state['secret']:
        return json_response(status=403, data={'error': 'Invalid secret'})
    
    # Verify user exists
    user_id = data['user']
    if user_id not in domain_state['users']:
        return json_response(status=404, data={'error': 'User not found'})

    # Get user's current location and state
    user_state = domain_state['users'][user_id]
    location = user_state['location']
    
    item_id = data['item']["id"]
    item = None

    # Try to find item in owned items
    if item_id in user_state['items_id']['owned']:
        item = user_state['items_id']['owned'][item_id]
        del user_state['items_id']['owned'][item_id]
        del user_state['items_name']['owned'][item['name']]
        
    # If not in owned, try carried items
    elif item_id in user_state['items_id']['carried']:
        item = user_state['items_id']['carried'][item_id]
        del user_state['items_id']['carried'][item_id]
        del user_state['items_name']['carried'][item['name']]

    # If item wasn't found in either place, return error
    if item is None:
        return json_response(status=404, data={'error': 'Item not found'})
    
    # Add item to dropped items with current location
    item['location'] = location
    user_state['items_id']['dropped'][item_id] = item
    user_state['items_name']['dropped'][item['name']] = item_id

    # Add item to domain's item dictionaries
    domain_state['item_ids'][item_id] = item
    domain_state['item_names'][item['name']] = item_id
    
    # Add item to current location's items list
    domain_state['locations'][location]['items_id'].append(item_id)
    domain_state['locations'][location]['items_name'].append(item['name'])

    # Return the location where item was dropped
    return json_response(location)

@routes.post("/command")
async def handle_command(req: Request) -> Response:
    """Handle hub-server commands"""
    data = await req.json()

    # Get user state
    user_id = data['user']
    if user_id not in domain_state['users'].keys():
        return Response(text="You have to journey to this domain before you can send it commands.")
        
    user_state = domain_state['users'][user_id]
    command = data['command']
    
    # Handle look command
    if command == ['look']:
        location = user_state['location']
        response = []
        
        # Add location description
        if location == 'foyer':
            response.append("You're in a hallway, unless it is a waiting room, or maybe a foyer? There are a couple of benches along the wall. To the east is an abandoned eatery of some kind blocked off by a grid of metal bars. To the north is a pair of double doors with a sign. To the east are double doors through which you can see indirect sunshine.")
        elif location == 'classroom':
            response.append("You're in an auditorium with several tiers of seats and stairs leading down.")
        elif location == 'podium':
            response.append("This is a space for a speaker to use when addressing a class. There is a cabinet with several doors, a screen on a swinging arm, and an empty countertop. Stairs lead up into the student seating area.")
            # Add cabinet contents description if open
            if domain_state['locations']['podium']['cabinet_state'] == 'open':
                response.append("Inside the cabinet is a tangle of wires, a rack of computers and amplifiers, and a large switch.")
                for item_id in domain_state['locations']['podium']['items_id']:
                        item = domain_state['item_ids'][item_id]
                        if item.get('depth') == 1:
                            response.append(f'There is a {item["name"]} <sub>{item_id}</sub> inside the cabinet.')  
        
        # Add visible items in current location
        loc_items = domain_state['locations'][location]['items_id']
        for item_id in loc_items:
            item = domain_state['item_ids'][item_id]
            # Check if item is depth-0 or was dropped here
            if ('depth' not in item or item['depth'] == 0) or \
               ('location' in item and item['location'] == location):
                response.append(f'There is a {item["name"]} <sub>{item_id}</sub> here.')
        
        return Response(text='\n'.join(response))
    elif len(command) == 2 and command[0] == 'look':
       location = user_state['location']
       item = command[1]
       
       # Special cases for podium items
       if item in ['cabinet', 'screen', 'switch']:
           if location != 'podium':
               return Response(text="I don't know how to do that.")
               
           if item == 'cabinet':
               cabinet_state = domain_state['locations']['podium']['cabinet_state']
               if cabinet_state == 'locked' or cabinet_state == 'closed':
                   return Response(text="The cabinet has a pair of doors with a small lock; the doors are closed.")
               else:
                   response = ["The cabinet has a pair of doors with a small lock; the doors are open.",
                  "Inside the cabinet is a tangle of wires, a rack of computers and amplifiers, and a large switch."]
                    # Show depth-1 items in the cabinet
                   for item_id in domain_state['locations']['podium']['items_id']:
                        item = domain_state['item_ids'][item_id]
                        if item.get('depth') == 1:
                            response.append(f'There is a {item["name"]} <sub>{item_id}</sub> inside the cabinet.')                    
                   return Response(text='\n'.join(response))                   
           elif item == 'screen':
               screen_state = domain_state['locations']['podium']['screen_state']
               if screen_state == 'blank':
                   return Response(text="The screen is blank. You notice a cable leading down into the cabinet.")
               elif screen_state == 'password':
                   return Response(text='The screen shows a password prompt. It\'s not the usual NetID prompt: it wants a special in-game password instead.')
               else:  # won
                   return Response(text='The screen shows fireworks and confetti and flashed the words "You won!".\n\nIn smaller text you notice the phrase "That\'s it. There\'s nothing more to the game in this MP."')  
           elif item == 'switch':
               if domain_state['locations']['podium']['cabinet_state'] != 'open':
                   return Response(text="I don't know how to do that.")
               switch_state = domain_state['locations']['podium']['switch_state']
               if switch_state == 'up':
                   return Response(text='The switch has a small label reading "power" and is in the up position.')
               else:  # down
                   return Response(text='The switch has a small label reading "power" and is in the down position.')
       
       # Regular items
       found_item = None
       
       # Try to find item in inventory first
       if item.isdigit():  # Search by ID
           item_id = int(item)
           if item_id in user_state['items_id']['owned']:
               found_item = user_state['items_id']['owned'][item_id]
           elif item_id in user_state['items_id']['carried']:
               found_item = user_state['items_id']['carried'][item_id]
       else:  # Search by name
           if item in user_state['items_name']['owned']:
               found_item = user_state['items_id']['owned'][user_state['items_name']['owned'][item]]
           elif item in user_state['items_name']['carried']:
               found_item = user_state['items_id']['carried'][user_state['items_name']['carried'][item]]
               
       # If not in inventory, check current location
       if not found_item:
           current_loc = domain_state['locations'][location]
           if item.isdigit():  # Search by ID
               item_id = int(item)
               if item_id in domain_state['item_ids']:
                   potential_item = domain_state['item_ids'][item_id]
                   # Check if item is in current location and has depth 0
                   if (item_id in current_loc['items_id'] and
                       ('depth' not in potential_item or potential_item['depth'] == 0)):
                       found_item = potential_item
           else:  # Search by name
               if item in domain_state['item_names']:
                   potential_item = domain_state['item_ids'][domain_state['item_names'][item]]
                   # Check if item is in current location and has depth 0
                   if (item in current_loc['items_name'] and
                       ('depth' not in potential_item or potential_item['depth'] == 0)):
                       found_item = potential_item
       
       if found_item:
           return Response(text=found_item['description'])
           
       return Response(text="I don't know how to do that.")
    elif len(command) == 2 and command[0] == 'take':

       location = user_state['location']
       item_query = command[1]
       current_loc = domain_state['locations'][location]
       
       # Find the item
       found_item = None
       item_id = None
       
       if item_query.isdigit():
           # Search by ID
           item_id = int(item_query)
           if item_id in current_loc['items_id']:
               found_item = domain_state['item_ids'][item_id]
       else:
           # Search by name
           if item_query in current_loc['items_name']:
               found_item = domain_state['item_ids'][domain_state['item_names'][item_query]]
               # Get the item_id from the item
               item_id = found_item["id"]
       
       if found_item:
           # Check permissions based on depth and location
           depth = found_item.get('depth', 0)
           
           can_take = (
               (depth == 0) or 
               (depth == 1 and location == 'podium' and 
                domain_state['locations']['podium']['cabinet_state'] == 'open')
           )
           
           if can_take:
               # Prepare transfer request
               transfer_data = {
                   "domain": domain_state['domain_id'],
                   "secret": domain_state['secret'],
                   "user": user_id,
                   "item": item_id,
                   "to": "inventory"
               }
               
               # Call transfer endpoint
               async with req.app.client.post(
                   domain_state['hub_url'] + '/transfer', 
                   json=transfer_data
               ) as resp:
                   if resp.status == 200:
                       # Remove item from location lists
                       current_loc['items_id'].remove(item_id)
                       current_loc['items_name'].remove(found_item['name'])

                       # Add item to appropriate user inventory based on ownership
                       if item_id in domain_state['owned']:
                        user_state['items_id']['owned'][item_id] = found_item
                        user_state['items_name']['owned'][found_item['name']] = item_id
                       else:
                        user_state['items_id']['carried'][item_id] = found_item
                        user_state['items_name']['carried'][found_item['name']] = item_id
                       return Response(text=f"{found_item['name']} was taken.")
                       
           # If we get here, either transfer failed or permissions weren't sufficient
           
       return Response(text=f"There's no {item_query} here to take")
    elif len(command) == 2 and command[0] == 'go':
       
       current_location = user_state['location']
       direction = command[1]
       
       # Check if direction is valid from current location
       exits = domain_state['locations'][current_location]['exits']
       if direction not in exits:
           return Response(text="You can't go that way from here.")
           
       # Get destination
       destination = exits[direction]
       
       # Handle leaving domain
       if destination is None:
           return Response(text="$journey east")
           
       # Update user location
       user_state['location'] = destination
       
       # Build response
       response = []
       
       # Add location description or name based on visit history
       if destination in user_state['visited_locations']:
           response.append(destination.capitalize())
       else:
           user_state['visited_locations'].add(destination)
           if destination == 'foyer':
               response.append("You're in a hallway, unless it is a waiting room, or maybe a foyer? There are a couple of benches along the wall. To the east is an abandoned eatery of some kind blocked off by a grid of metal bars. To the north is a pair of double doors with a sign. To the east are double doors through which you can see indirect sunshine.")
           elif destination == 'classroom':
               response.append("You're in an auditorium with several tiers of seats and stairs leading down.")
           else:  # podium
               response.append("This is a space for a speaker to use when addressing a class. There is a cabinet with several doors, a screen on a swinging arm, and an empty countertop. Stairs lead up into the student seating area.")
               if domain_state['locations']['podium']['cabinet_state'] == 'open':
                   response.append("Inside the cabinet is a tangle of wires, a rack of computers and amplifiers, and a large switch.")
       
       # Add visible items in new location
       loc_items = domain_state['locations'][destination]['items_id']
       for item_id in loc_items:
           item = domain_state['item_ids'][item_id]
           # Check if item is depth-0 or was dropped here
           if ('depth' not in item or item['depth'] == 0) or \
              ('location' in item and item['location'] == destination):
               response.append(f'There is a {item["name"]} <sub>{item_id}</sub> here.')
       
       # If in podium with open cabinet, show depth-1 items
       if destination == 'podium' and domain_state['locations']['podium']['cabinet_state'] == 'open':
           for item_id in domain_state['locations']['podium']['items_id']:
                item = domain_state['item_ids'][item_id]
                if item.get('depth') == 1:
                    response.append(f'There is a {item["name"]} <sub>{item_id}</sub> inside the cabinet.')
       
       return Response(text='\n'.join(response))
    elif len(command) == 2 and " ".join(command) == "read sign":
        location = user_state['location']
        if (location == "foyer"):
            return Response(text="The sign says <q>1404</q>")
    elif user_state['location'] == 'podium':
        # Handle cabinet commands
        if len(command) == 2:
            if command == ['open', 'cabinet']:
                cabinet_state = domain_state['locations']['podium']['cabinet_state']
                if cabinet_state == 'locked':
                    return Response(text="It seems to be locked.")
                elif cabinet_state == 'closed':
                    domain_state['locations']['podium']['cabinet_state'] = 'open'
                    response = ["You open the cabinet doors.",
                            "Inside the cabinet is a tangle of wires, a rack of computers and amplifiers, and a large switch."]
                    
                    # Show depth-1 items in the cabinet
                    for item_id in domain_state['locations']['podium']['items_id']:
                        item = domain_state['item_ids'][item_id]
                        if item.get('depth') == 1:
                            response.append(f'There is a {item["name"]} <sub>{item_id}</sub> inside the cabinet.')
                    
                    return Response(text='\n'.join(response))
                else:  # open
                    return Response(text="It's already open.")
                    
            elif command == ['close', 'cabinet']:
                cabinet_state = domain_state['locations']['podium']['cabinet_state']
                if cabinet_state == 'open':
                    domain_state['locations']['podium']['cabinet_state'] = 'closed'
                    return Response(text="You close the doors.")
                else:  # locked or closed
                    return Response(text="It's already closed.")
            elif command == ['use', 'switch']:
                if domain_state['locations']['podium']['cabinet_state'] != 'open':
                    return Response(text="I don't know how to do that.")
                    
                switch_state = domain_state['locations']['podium']['switch_state']
                if switch_state == 'down':
                    domain_state['locations']['podium']['switch_state'] = 'up'
                    # When switch goes up, screen changes to password state
                    domain_state['locations']['podium']['screen_state'] = 'password'
                    return Response(text="You move the switch to the up position.")
                else:  # up
                    domain_state['locations']['podium']['switch_state'] = 'down'
                    # When switch goes down, screen goes blank
                    domain_state['locations']['podium']['screen_state'] = 'blank'
                    return Response(text="You move the switch to the down position.")
        elif command == ['use', 'key', 'cabinet']:
                # Check if user has key in inventory
                has_key = False
                for item_id, item in user_state['items_id']['owned'].items():
                    if item['name'] == 'key':
                        has_key = True
                        break
                for item_id, item in user_state['items_id']['carried'].items():
                    if item['name'] == 'key':
                        has_key = True
                        break
                        
                if not has_key:
                    return Response(text="You don't have a key.")
                    
                cabinet_state = domain_state['locations']['podium']['cabinet_state']
                if cabinet_state == 'locked':
                    domain_state['locations']['podium']['cabinet_state'] = 'closed'
                    return Response(text="You use the key to unlock the cabinet doors.")
                elif cabinet_state == 'closed':
                    domain_state['locations']['podium']['cabinet_state'] = 'locked'
                    return Response(text="You use the key to lock the cabinet doors.")
        elif len(command) == 3 and command[0:2] == ['tell', 'screen']:
                '''
                if domain_state['locations']['podium']['screen_state'] != 'password':
                    return Response(text="Screen is turned off try finding a switch.")
                '''
                password = command[2]
                if (domain_state['locations']['podium']['screen_state'] == 'password'):
                    if password == 'xyzzy':
                        domain_state['locations']['podium']['screen_state'] = 'won'
                        return Response(text='You enter the password "XYZZY". After a few seconds of thinking, the screen fills with fireworks and confetti and flashes the words "You won!"')
                    else:
                        return Response(text=f'You enter the password "{password}" but the computer doesn\'t accept it.')
    elif len(command) == 2:
       verb = command[0]
       item_query = command[1]
       
       found_item = None
       
       # Check if item is in inventory (owned or carried)
       if item_query.isdigit():
           # Search by ID
           item_id = int(item_query)
           if item_id in user_state['items_id']['owned']:
               found_item = user_state['items_id']['owned'][item_id]
           elif item_id in user_state['items_id']['carried']:
               found_item = user_state['items_id']['carried'][item_id]
       else:
           # Search by name
           if item_query in user_state['items_name']['owned']:
               found_item = user_state['items_id']['owned'][user_state['items_name']['owned'][item_query]]
           elif item_query in user_state['items_name']['carried']:
               found_item = user_state['items_id']['carried'][user_state['items_name']['carried'][item_query]]
               
       if found_item and 'verb' in found_item:
           # Check if verb exists for item
           if verb in found_item['verb']:
               return Response(text=found_item['verb'][verb])# For any other command
    return Response(text="I don't know how to do that.")

# Do not modify code below this line

@web.middleware
async def allow_cors(req, handler):
    """Bypass cross-origin resource sharing protections,
    allowing anyone to send messages from anywhere.
    Generally unsafe, but for this class project it should be OK."""
    resp = await handler(req)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

async def start_session(app):
    """To be run on startup of each event loop. Makes singleton ClientSession"""
    from aiohttp import ClientSession, ClientTimeout
    app.client = ClientSession(timeout=ClientTimeout(total=3))

async def end_session(app):
    """To be run on shutdown of each event loop. Closes the singleton ClientSession"""
    await app.client.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default="0.0.0.0")
    parser.add_argument('-p','--port', type=int, default=3400)
    args = parser.parse_args()

    import socket
    whoami = socket.getfqdn()
    if '.' not in whoami: whoami = 'localhost'
    whoami += ':'+str(args.port)
    whoami = 'http://' + whoami
    print("URL to type into web prompt:\n\t"+whoami)
    print()

    app = web.Application(middlewares=[allow_cors])
    app.on_startup.append(start_session)
    app.on_shutdown.append(end_session)
    app.add_routes(routes)
    web.run_app(app, host=args.host, port=args.port)
