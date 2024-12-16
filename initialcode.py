from aiohttp import web
from aiohttp.web import Request, Response, json_response
import random

routes = web.RouteTableDef()

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
    # TO DO: clear any user/game state to its initial state

    raise Warning("Code not finished")

@routes.post('/arrive')
async def register_with_hub_server(req: Request) -> Response:
    """Called by hub server each time a user enters or re-enters this domain."""
    data = await req.json()

    raise Warning("Code not finished")


@routes.post('/dropped')
async def register_with_hub_server(req: Request) -> Response:
    """Called by hub server each time a user drops an item in this domain.
    The return value must be JSON, and will be given as the location on subsequent /arrive calls
    """
    data = await req.json()

    raise Warning("Code not finished")


@routes.post("/command")
async def handle_command(req : Request) -> Response:
    """Handle hub-server commands"""
    data = await req.json()

    raise Warning("Code not finished")


def placeholder_for_strings():
    """This function is just a way to give you all the strings we'll test for"""
    # foyer description
    "You're in a hallway, unless it is a waiting room, or maybe a foyer? There are a couple of benches along the wall. To the east is an abandoned eatery of some kind blocked off by a grid of metal bars. To the north is a pair of double doors with a sign. To the east are double doors through which you can see indirect sunshine."

    # foyer read sign
    'The sign says <q>1404</q>'

    # classroom description
    "You're in an auditorium with several tiers of seats and stairs leading down."

    # podium description
    "This is a space for a speaker to use when addressing a class. There is a cabinet with several doors, a screen on a swinging arm, and an empty countertop. Stairs lead up into the student seating area."
    # podium description has this on a second line if the cabinet it open
    "Inside the cabinet is a tangle of wires, a rack of computers and amplifiers, and a large switch."

    # podium look screen
    "The screen is blank. You notice a cable leading down into the cabinet."
    "The screen shows a password prompt. It's not the usual NetID prompt: it wants a special in-game password instead."
    "The screen shows fireworks and confetti and flashed the words \"You won!\".\n\nIn smaller text you notice the phrase \"That's it. There's nothing more to the game in this MP.\""

    # podium open cabinet
    "It seems to be locked."
    "You open the cabinet doors." # then the same inside-cabinet line as podium description
    "It's already open."

    # podium close cabinet
    "You close the doors."
    "It's already closed."

    # podium look cabinet
    "The cabinet has a pair of doors with a small lock; the doors are closed."
    "The cabinet has a pair of doors with a small lock; the doors are open." # then the same inside-cabinet line as podium description

    # podium use key cabinet
    "You use the key to unlock the cabinet doors."
    "You use the key to lock the cabinet doors."
    "You don't have a key."

    # podium use switch if cabinet is open
    "You move the switch to the up position."
    "You move the switch to the down position."

    # podium look switch if cabinet is open
    "The switch has a small label reading \"power\" and is in the up position."
    "The switch has a small label reading \"power\" and is in the down position."

    # podium tell screen xyzzy in the password state
    "You enter the password \"XYZZY\". After a few seconds of thinking, the screen fills with fireworks and confetti and flashes the words \"You won!\""

    # podium tell screen anything else in the password state
    f"You enter the password \"{what_they_said}\" but the computer doesn't accept it."

    # podium depth-1 item you are hosting for other domains if cabinet is open
    f'There is a {item["name"]} <sub>{item["id"]}</sub> inside the cabinet.'
            

    # go <direction> where the direction is not supported
    "You can't go that way from here."

    # Any command you can't handle
    "I don't know how to do that."

    # After a room description for each item in that location
    f'There is a {item["name"]} <sub>{item["id"]}</sub> here.'

    # take something not here
    f"There's no {something} here to take"

    # any /command if the user has not yet been registered with /arrive
    "You have to journey to this domain before you can send it commands."
    
    # when entering or looking in a location with a dropped or depth-0 hosted item
    f'There is a {item["name"]} <sub>{item["id"]}</sub> here.'




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
