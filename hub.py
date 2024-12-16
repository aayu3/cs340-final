from aiohttp import web
import random

routes = web.RouteTableDef()


###############################
###    Section: global state    ###


# How all the domains a situated relative to on another
grid = {} # {(x,y): domain_id}

# Information about each domain
domains = {} # {domain_id:{"url":url, "name":str, "description":str, "cell":[x,y], "loot":[item_id]}}

# All item templates
templates = {} # {item_id:{"name":str, "description":str, "home":domain_id, "hosts":[domain_id], "depth":int}}

# Centrally-tracked information about each user
users = {} # id : {"in":domain_id, "open":[domain_id], "inventory":{item_id:location,...}}

# Global tracking of the different operation modes
mode = "setup" # {"setup", "play", "locked"}



##########################################################
###    Section: dummy state to simulate multiple domains ###

other_domains = [
    { "loot": {
            'name':'i-card',
            'description':"A University ID card. The name is smudged, but you recognize the face; this is the person who came from IT to fix the classroom computer when it broke down.",
            'verb':{'read':"The text is smudged and you don't know how to read bar codes or magnetic stripes."},
            'depth':0,
            'home':-1,
        },
        "messages": [
            "You journey in other domains, but find nothing of interest except a locked door with a card swipe next to it. You then return from whence you came.",
            "You journey in other domains. After several adventures you use the ID card to open a locked door, behind which you find a {}. You then return from whence you came.",
            "You journey in other domains, but don't find anything of note so you return from whence you came.",
        ]
    },
    { "loot": {
            'name':'axe',
            'description':"An axe, colored like those used by firefighters to break through burning walls.",
            'verb':{'use':"An axe like this could do some serious damage. Best not to use it anywhere on campus."},
            'depth':0,
            'home':-1,
        },
        "messages": [
            "You journey in other domains, but find nothing of interest except an old half-burnt firefighter training building. You try to enter, but its door is not burnt enough to knock down with your bare hands.",
            "You journey in other domains. After several adventures you use the axe to break down a door in a half-burnt firefighter training building. Inside you you find a {}. You then return from whence you came.",
            "You journey in other domains, but don't find anything of note so you return from whence you came.",
        ]
    },
]
toy = {
    'name':'toy',
    'description':'A small rubber turtle with a hard plastic shell',
    'verb':{'use':'You play with the turtle.'},
    'depth':1,
    'home':-2,
}
live_domain = None


###################################
###  Section: helper functions  ###


def make_secret(secure=False, nbytes=12):
    """Creates a random string"""
    if secure:
        import secrets
        return secrets.token_urlsafe(nbytes)
    else:
        import string
        alphabet = string.ascii_letters + string.digits + '-_'
        return ''.join(random.choice(alphabet) for _ in range(nbytes*8//6))


def make_map():
    """Puts each domain in a random location on a grid"""
    # For this MP, only a single domain is supported
    return

def assign_loot():
    """Distributes items with depth to other domains"""
    # For this MP, only a single domain is supported, so this picks a random "outside world" scenario instead
    global live_domain
    
    live_domain = random.choice(other_domains).copy()
    live_domain['state'] = 0
    live_domain['hiding'] = set(tid for tid in templates if 'depth' in templates[tid])
    lootid = random.randrange(1000)
    while lootid in templates: lootid += 1
    hostid = next(iter(domains))
    templates[lootid] = live_domain['loot']
    templates[lootid]['hosts'] = [hostid]
    domains[hostid]['loot'] = [lootid]
    live_domain['key'] = lootid

    while lootid in templates: lootid += 1
    templates[lootid] = toy
    toy['hosts'] = [hostid]
    domains[hostid]['loot'].append(lootid)
    


def checkuid(data : dict) -> web.Response | int:
    if mode != 'play':
        return web.json_response(status=409, data={'error':'Only available during play'})
    for need in 'user','secret':
        if need not in data:
            return web.json_response(status=400, data={'error':'Request must contain '+need})
    uid = data['user']
    if uid not in users:
        return web.json_response(status=403, data={'error':f'User {uid} not known'})
    if users[uid]['secret'] != data['secret']:
        return web.json_response(status=403, data={'error':f'Invalid secret'})
    return uid

def checkdid(data : dict) -> web.Response | int:
    if mode != 'play':
        return web.json_response(status=409, data={'error':'Only available during play'})
    for need in 'domain','secret':
        if need not in data:
            return web.json_response(status=400, data={'error':'Request must contain '+need})
    did = data['domain']
    if did not in domains:
        return web.json_response(status=403, data={'error':f'Domain {did} not known'})
    if domains[did]['secret'] != data['secret']:
        return web.json_response(status=403, data={'error':f'Invalid secret'})
    return did
    


####################################
###  Section: web UI interfaces  ###

@routes.get("/")
async def web_interface(req : web.Request) -> web.StreamResponse:
    """Display web front-end"""
    return web.FileResponse(path="tba.html")

@routes.get("/mode")
async def get_mode(req : web.Request) -> web.Response:
    """Get the mode of the server (play or setup)"""
    return web.Response(text=mode)

@routes.post("/mode")
async def set_mode(req : web.Request) -> web.Response:
    """Change the mode of the server"""
    global mode
    newmode = await req.text()
    if newmode == mode: return web.Response(text="Already in "+newmode+" mode")
    elif mode == 'locked': return web.Response(status=409, text="Error: request sent midway through handling another request.")
    elif newmode == 'setup':
        mode = 'setup'
        users.clear()
        grid.clear()
        domains.clear()
        templates.clear()
    elif newmode == 'play':
        if len(domains) == 0:
            return web.Response(status=409, text="Must register at least one domain before entering play mode.")
        mode = 'locked'
        make_map()
        assign_loot()
        mode = 'play'
    else:
        return web.Response(status=400, text="Unknown mode "+repr(newmode))
    
    return web.Response(text="Now in "+mode+" mode")

@routes.post("/domain")
async def notify_domain(req : web.Request) -> web.Response:
    """Web front-end to tell hub server to ask domain server for details"""
    if mode != 'setup':
        return web.Response(status=409, text="Central server is not in setup mode.")
    try:
        data = await req.text()
        if any(d['url'] == data for d in domains.values()):
            return web.Response(text="That domain server has already been registered.")
        async with req.app.client.post(data+'/newhub', data=whoami) as resp:
            spot = await resp.json()
            if 'error' in spot:
                return web.Response(text="Domain server returned an error message:<pre>"+spot['error']+"</pre>")
            else:
                return web.Response(text=spot.get('ok','Domain registered.'))
    except BaseException as ex:
        return web.Response(status=500, text="Domain registration failed with error:<pre>"+repr(ex)+"</pre>")
    
@routes.post("/newhub")
async def notify_domain(req : web.Request) -> web.Response:
    """Placeholder to give more useful error messages for on common error"""
    return web.json_response(status=400, data={
        'error': whoami+' is the URL of the hub server, not a domain server.'
    })

@routes.get("/login")
async def login(req : web.Request) -> web.Response:
    """User log-in"""
    if mode != 'play':
        return web.json_response(status=409, data={'error':'Players cannot log in during setup'})
    if len(users) > 0:
        print("WARNING: MP10 only requires support for 1 user, but more than 1 registered")
    data = {}
    data['secret'] = make_secret()
    data['in'] = random.choice(tuple(domains))
    data['open'] = [data['in']]
    data['inventory'] = {}
    uid = len(users)
    users[uid] = data
    await arrive(uid, data['in'], req.app)
    return web.json_response(data={'id':uid,'secret':data['secret'],
        'domain':{k:v for k,v in domains[data['in']].items() if k in ('url','name','description')}})


@routes.post("/command")
async def handle_command(req : web.Request) -> web.Response:
    """Handle hub-server commands"""
    try: data = await req.json()
    except: return web.json_response(status=400, text="JSON data required")
    uid = checkuid(data)
    if isinstance(uid, web.Response): return uid
    if 'command' not in data: return web.json_response(status=400, text="Command expected")
    cmd = data['command']
    if not isinstance(cmd, list): return web.json_response(status=400, text="Command should be a list")
    if not all(isinstance(word, str) for word in cmd): return web.json_response(status=400, text="Command should be a list of strings")
    
    if cmd[0] == 'region': return await region(uid, cmd[1:])
    if cmd[0] == 'journey': return await journey(uid, cmd[1:], req.app)
    if cmd[0] == 'inventory': return await inventory(uid, cmd[1:])
    if cmd[0] == 'score': return await score(uid, cmd[1:])
    if cmd[0] == 'drop': return await drop(uid, cmd[1:], req.app)
    
    return web.Response(text="I don't know how to do that")






##################################
###  Section: command helpers  ###

async def region(uid:int, rest:list[str]) -> web.Response:
    """Information about the current domain for the user"""
    me = users[uid]
    here = domains[me['in']]
    return web.Response(text='You are in domain <strong>'+here['name']+'</strong>\n'+here['description']+'\n\nFor this MP, there is no detail available about other domains in the region.')

async def journey(uid:int, rest:list[str], app:web.Application) -> web.Response:
    """User-initiated move between domains"""
    if len(rest) != 1 or rest[0] not in ('north','south','east','west'):
        return web.Response(text='I only know how to journey in cardinal directions', status=403)

    me = users[uid]
    here = domains[me['in']]
    message = live_domain['messages'][2]

    if live_domain['state'] == 0:
        if me['inventory'].get(live_domain['key']) == 'inventory': 
            live_domain['state'] = 1
            for item in live_domain['hiding']:
                me['inventory'][item] = 'inventory'
            message = live_domain['messages'][1].format(' and '.join(templates[tid]['name'] for tid in live_domain['hiding']))
        else:
            message = live_domain['messages'][0]
    await arrive(uid, me['in'], app)
    return web.Response(text=message)

async def inventory(uid:int, rest:list[str]) -> web.Response:
    """Display what the user is carrying"""
    me = users[uid]
    if not any(v == 'inventory' for v in me['inventory'].values()):
        return web.Response(text='You are not carrying anything.')
    return web.Response(text='You are carrying:<ul>'+''.join(f'<li>{templates[tid]["name"]} <sub>{tid}</sub></li>' for tid in me['inventory'] if me['inventory'][tid] == 'inventory'))

async def score(uid:int, rest:list[str]) -> web.Response:
    """Display the scoreboard"""
    return web.Response(text="There's no scoreboard because you are the only user.")


async def arrive(uid: int, dest: int, app:web.Application) -> None:
    """Alert a domain that a user has arrived"""
    owned, carried, dropped, prize = [],[],[],[]
    for tid, loc in users[uid]['inventory'].items():
        t = templates[tid]
        brief = {k:v for k,v in t.items() if k in ('name','description','verb')}
        brief['id'] = tid
        if loc == 'inventory':
            if t['home'] == dest:
                owned.append(brief)
            else: carried.append(brief)
        elif loc[0] == dest:
            brief['location'] = loc[1]
            dropped.append(brief)
    for tid in domains[dest]['loot']:
        if tid not in users[uid]['inventory']:
            t = templates[tid]
            brief = {k:v for k,v in t.items() if k in ('name','description','verb','depth')}
            brief['id'] = tid
            prize.append(brief)
    
    try:
        async with app.client.post(domains[dest]['url']+'/arrive', json={
            'secret':domains[dest]['secret'],
            'user':uid,
            'owned':owned,
            'carried':carried,
            'dropped':dropped,
            'prize':prize,
        }) as resp:
            assert resp.status == 200, (resp.status, await resp.read())
    except BaseException as ex:
        print('ERROR:',domains[dest]['url']+'/arrive','did not work',repr(ex))

async def drop(uid:int, rest:list[str], app:web.Application) -> web.Response:
    """Called by users to drop items where they are"""
    if len(rest) == 0:
        return web.Response(text='What do you want to drop?\n><code>inventory</code> will show your options')
    
    me = users[uid]
    gear = [tid for tid,where in me['inventory'].items() if where == 'inventory']
    
    todrop = ' '.join(rest)
    
    if todrop in [str(tid) for tid in gear]:
        item = int(todrop)
    else:
        todrop = [tid for tid in gear if templates[tid]['name'] == todrop]
        if len(todrop) == 0:
            return web.Response(text='You have no '+' '.join(rest)+' to drop')
        if len(todrop) > 1:
            return web.Response(text='You have more than one '+' '.join(rest)+': please disambiguate which one you mead by using one of the following:<ul>'+
                ''.join(f'<li><code>drop {tid}</code> to drop {templates[tid]["name"]} <sub>{tid}</sub></li>' for tid in todrop)
            +'</ul')
        item = todrop[0]
    
    did = users[uid]['in']
    spot = None
    try:
        async with app.client.post(domains[did]['url']+'/dropped', json={
            'secret':domains[did]['secret'],
            'user':uid,
            'item':{'id':item} | {k:v for k,v in templates[item].items() if k in ('name','description','verb')},
        }) as resp:
            spot = await resp.json()
    except:
        return web.Response(text="You try to drop it, but the domain won't let you")
    
    me['inventory'][item] = (did, spot)
    
    return web.Response(text=templates[item]['name']+f" <sub>{item}</sub> dropped.")



###########################################
###  Section: domain server interfaces  ###


@routes.post("/register")
async def register_domain(req : web.Request) -> web.Response:
    """Registers a domain, if the server is in the domain-registering mode"""
    if mode != 'setup':
        return web.Response(status=409, text="Central server is not in setup mode")
    try: data = await req.json()
    except: return web.json_response(status=400, data={"error":"JSON data required"})
    if 'name' not in data or not isinstance(data['name'], str):
        return web.json_response(status=400, data={"error":"Name string required"})
    if 'description' not in data or not isinstance(data['description'], str):
        return web.json_response(status=400, data={"error":"Description string required"})
    if 'url' not in data or not isinstance(data['url'], str):
        return web.json_response(status=400, data={"error":"Sever url required"})
    if 'items' not in data or not isinstance(data['items'], list) or any(not isinstance(item, dict) for item in data['items']):
        return web.json_response(status=400, data={"error":"List of item templates required"})
    for i,d in domains.items():
        if d['url'] == data['url']:
            return web.json_response(status=409, data={"error":"Cannot register same domain more than once"})
    if len(domains) > 1:
        return web.Response(status=409, text="MP10's hub server only supports a single domain at a time.")
    did = random.randrange(1000) # only one domain, but fake a different ID for each
    secret = make_secret()
    domains[did] = {
    'url':data['url'],
    'name':data['name'],
    'description':data['description'],
    'secret':secret,
    }
    ids = []
    t0 = random.randrange(1000)
    for item in data['items']:
        tid = len(templates)+t0
        templates[tid] = {'name':item.get('name','thing'), 'description':item.get('description','error: owner did not describe this item'), 'verb':item.get('verb',{}), 'home':did}
        ids.append(tid)
        if 'depth' in item and isinstance(item['depth'], int):
            templates[tid]['depth'] = max(0,item['depth'])
        

    return web.json_response({'id':did,"items":ids,'secret':secret})


@routes.post("/transfer")
async def transfer(req: web.Request) -> web.Response:
    """Called by domain servers to move items into our out of gear
    
    { "domain": sending domain's id
    , "secret": sending domain's secret id
    , "user": user id
    , "item": item type id
    , "to": destination
    }
    
    Destination "inventory" means the item should be carried.
    Any other destination names some location within the sending domain (as if dropped).
    
    """
    try: data = await req.json()
    except: return web.json_response(status=400, data={"error":"JSON data required"})
    did = checkdid(data)
    if isinstance(did, web.Response): return did
    uid = data.get('user')
    if uid not in users:
        return web.json_response(status=400, data={"error":"Valid user ID required"})
    tid = data.get('item')
    if tid not in templates:
        return web.json_response(status=400, data={"error":"Valid item ID required"})
    if 'to' not in data:
        return web.json_response(status=400, data={"error":"Missing \"to\" field"})
    
    old = users[uid]['inventory'].get(tid)
    new = data['to']
    owned = templates[tid]['home'] == did or did in templates[tid].get('hosts',[])
    
    
    if old == new:
        return web.json_response(status=409, data={"error":"Cannot move item to where it already is"})
    
    if old is None and not owned:
        return web.json_response(status=403, data={"error":"Cannot generate items that don't belong to you"})
    if old is not None and new != 'inventory' and templates[tid]['home'] != did:
        return web.json_response(status=403, data={"error":"Cannot move or remove items that don't belong to you"})

    if old is not None and old[0] != did:
        return web.json_response(status=403, data={"error":"That item has been dropped in a different domain"})

    users[uid]['inventory'][tid] = new if new == 'inventory' else (did, new)


    return web.json_response(status=200, data={"ok":"Item transferred"})


@routes.post("/query")
async def transfer(req: web.Request) -> web.Response:
    """Called by domain servers to find out what items are where
    
    { "domain": sending domain's id
    , "secret": sending domain's secret id
    , "user": user id
    , "location": either "inventory" or a domain-selected location value
    , "depth": asks for any prizes of that depth
    }
    
    One (not both) of "location" and "depth" must be provided.
    
    Return is a list of item ID.
    """
    try: data = await req.json()
    except: return web.json_response(status=400, data={"error":"JSON data required"})
    did = checkdid(data)
    if isinstance(did, web.Response): return did
    uid = data.get('user')
    if uid not in users:
        return web.json_response(status=400, data={"error":"Valid user ID required"})
    if ('location' in data) == ('depth' in data):
        return web.json_response(status=400, data={"error":"Must provide location xor depth"})

    if 'location' in data:
        where = data['location']
        if where is None:
            return web.json_response(status=400, data={"error":"Location required"})
        if where != 'inventory':
            where = (did, where)
        resp = [iid for iid,loc in users[uid]['inventory'].items() if loc == where]
    else:
        resp = [iid for iid in domains[did]['loot'] if iid not in users[uid]['inventory'] and templates[iid].get('depth') == data['depth']]
    
    return web.json_response(status=200, data=resp)



async def start_session(app):
    """To be run on startup of each event loop"""
    from aiohttp import ClientSession, ClientTimeout
    app.client = ClientSession(timeout=ClientTimeout(total=3))

async def end_session(app):
    """To be run on shutdown of each event loop"""
    await app.client.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default="0.0.0.0")
    parser.add_argument('-p','--port', type=int, default=10340)
    args = parser.parse_args()

    import socket
    whoami = socket.getfqdn()
    if '.' not in whoami: whoami = 'localhost'
    whoami += ':'+str(args.port)
    whoami = 'http://' + whoami
    print("URL to visit in browser:\n\t"+whoami)
    print()
    
    app = web.Application()
    app.on_startup.append(start_session)
    app.on_shutdown.append(end_session)
    app.add_routes(routes)
    web.run_app(app, host=args.host, port=args.port)
