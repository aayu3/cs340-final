from aiohttp import web
from aiohttp.web import Request, Response, json_response
import random
import copy

routes = web.RouteTableDef()

users = {}  # UserID : domainstate
base_domain_info = {
    "hub_url": "",
    "domain_id": None,
    "secret": None,
}

base_domain_state = {
    "item_ids": {},  # ItemID : Item Description, this is for all items hosted by this domain
    "item_names": {},  # Name: ItemID
    "user_state": {},  # User State
    "owned": [],  # ItemIDs for objects owned here, but in other domains, these could also end up in the users inventory etc
    "locations": {
        "nexus": {
            "items_id": [],  # ItemIDs for the items located here
            "items_name": [],
            "exits": {
                "left": "puzzle_chamber_0",
                "north": "$journey north",
                "south": "$journey south",
                "west": "$journey west",
                "east": "$journey east",
                "forward": "lore_room",
                "forwards": "lore_room",
            },
            "gate_1": False,
            "altar": [False, False, False, False, False, False],
        },
        "secret_chamber": {
            "items_id": [],  # ItemIDS for the items located here
            "items_name": [],
            "exits": {"left": "nexus", "back" : "nexus", "backwards": "nexus"},
        },
        "puzzle_chamber_0": {
            "items_id": [],  # ItemIDs for the items located here
            "items_name": [],
            "exits": {"right": "nexus"},
            "symbiotic_lock": False,
            "suspension_beams": False,
        },
        "lore_room": {
            "items_id": [],  # ItemIDs for the items located here
            "items_name": [],
            "exits": {
                "back" : "nexus",
                "backward": "nexus",
                "backwards": "nexus",
                "left": "trap_room",
                "right": "puzzle_chamber_1",
                "forward" : "puzzle_chamber",
                "forwards" : "puzzle_chamber"
            },
            "suspension_beams": False,
            "palm_scan": False,
            "gate_2": False,
        },
        "trap_room": {
            "items_id": [],  # ItemIDs for the items located here
            "items_name": [],
            "exits": {
                "right": "lore_room","back": "lore_room","backwards": "lore_room","backward": "lore_room"
            },
        },
        "puzzle_chamber_1": {
            "items_id": [],  # ItemIDs for the items located here
            "items_name": [],
            "exits": {"left": "lore_room", "back": "lore_room","backwards": "lore_room","backward": "lore_room"},
            "symbiotic_lock": False,
        },
        "puzzle_chamber_2": {
            "items_id": [],  # ItemIDs for the items located here
            "items_name": [],
            "exits": {"backwards": "lore_room", "back" : "lore_room"},
            "gate_3": False,
            "suspension_beams": False,
            "symbiotic_lock": False,
            "retinal_scan": False,
        },
        "treasure_room": {
            "items_id": [],  # ItemIDs for the items located here
            "items_name": [],
            "exits": {"backwards": "puzzle_chamber_3"},
            "vault": False,
            "sample_analyzer": False,
        },
    },
}

domain_items = [
    {
        "name": "tissuesample",
        "description": "A preserved organic sample, faintly pulsating. (<code>hint</code>)",
        "verb": {"hint": "Consider searching for a sample analyzer"},
    },
    {
        "name": "metalcranium",
        "description": "A cold, polished skull crafted from an unknown alloy. (<code>hint</code>)",
        "verb": {"hint": "Consider searching for a sample analyzer"},
        "depth": 2,
    },
    {
        "name": "biomecheyel",
        "description": "A left eye, fused with advanced biomechanical circuitry. (<code>hint</code>)",
        "verb": {"hint": "Consider searching for a retinal scanner"},
        "depth": 1,
    },
    {
        "name": "biomecheyer",
        "description": "A right eye, lifeless but unnervingly pristine, like a crystal. (<code>hint</code>)",
        "verb": {"hint": "Consider searching for a retinal scanner"},
    },
    {
        "name": "biomechpalml",
        "description": "A metal left palm, its surface engraved with glowing, organic veins. (<code>hint</code>)",
        "verb": {"hint": "Consider searching for a palm scanner"},
        "depth": 0,
    },
    {
        "name": "biomechpalmr",
        "description": "A right palm, smooth and cold to the touch. (<code>hint</code>)",
        "verb": {"hint": "Consider searching for a palm scanner"},
    },
    {
        "name": "biomechtablet0",
        "description": "A humming tablet alive with faint pulses of energy. <code>(read/hint1/hint2/hint3/solution)</code>",
        "verb": {
            "hint1": "Perhaps it contains a clue for unlocking somethingr",
            "hint2": "Perhaps the Z's and O's correspond to something",
            "hint3": "Zero/One",
            "solution": "89",
            "read": "In the age of fire, a young noble was born who would later be known as the Nameless Ki... the rest of the text is indecipherable, save for the string <code>OZOOZZO</code>",
        },
    },
    {
        "name": "biomechtablet1",
        "description": "An active tablet etched with glowing script. <code>(read/hint1/hint2/solution)</code>",
        "verb": {
            "hint1": "Perhaps it contains a clue for unlocking somethingr",
            "hint2": "Consider the capitilization Of this Sentence: 37",
            "solution": "21185",
            "read": "After his Ascension to the Throne the Nameless King ushered in an era of Peace",  # 21185
        },
    },
    {
        "name": "biomechtablet10",
        "description": "A pulsing tablet that feels warm, almost alive. <code>(read/hint1/hint2/hint3/solution)</code>",
        "verb": {
            "hint1": "Perhaps it contains a clue for unlocking somethingr",
            "hint2": "Consider what words may have multiple meanings",
            "hint3": "It sure is ODD that you EVEN need to come here for more clues 1285",
            "solution": "303625",
            "read": "Even though the Nameless King has passed, odd rumors remain of his treasure, sealed away behind an altar of iridescent light",
        },
    },
    {
        "name": "pendantofnk",
        "description": "A steel pendant, with a pulsing heart in its center, it allows the user to return to the Ossuary of the Nameless King <code>(use)</code>",
        "verb": {"use": "$journey 001"},
    },
]


@routes.post("/newhub")
async def register_with_hub_server(req: Request) -> Response:
    """Used by web UI to connect this domain to a hub server.

    1. web calls domain's /register, with hub server URL payload
    2. domain calls hub server's /register, with name, description, and items
    3. hub server replies with domain's id, secret, and item identifiers
    """
    # partially implemented for you:
    url = await req.text()
    async with req.app.client.post(
        url + "/register",
        json={
            "url": whoami,
            "name": "Ossuary of the Nameless King",
            "description": "A biomechanical church, dedicated to the revered Nameless King",
            "items": domain_items,
        },
    ) as resp:
        data = await resp.json()
        if "error" in data:
            return json_response(status=resp.status, data=data)

    # TO DO: store the url and values in the returned data for later use
    # Store hub information
    base_domain_info["hub_url"] = url
    base_domain_info["domain_id"] = data["id"]
    base_domain_info["secret"] = data["secret"]

    # TO DO: clear any user/game state to its initial state
    users.clear()

    # Assign ItemIDs to the base_domain_state
    for i, item_id in enumerate(data["items"]):
        domain_items[i]["id"] = item_id
        item_desc = domain_items[i]
        base_domain_state["item_ids"][item_id] = item_desc
        base_domain_state["item_names"][item_desc["name"]] = item_id

    # locations for items in order
    item_locations = {"tissuesample":"puzzle_chamber_2",
        "metalcranium":"other", #other
        "biomecheyel":"other",
        "biomecheyer":"puzzle_chamber_1",
        "biomechpalml":"other",
        "biomechpalmr":"puzzle_chamber_0",
        "biomechtablet0":"nexus",
        "biomechtablet1":"lore_room",
        "biomechtablet10":"puzzle_chamber_2",
        "pendantofnk":"treasure_room" #treasure_room
        }
        
    for i in range(len(domain_items)):
        cur_name = domain_items[i]["name"]
        if item_locations[cur_name] == "other":
            continue
        cur_id = data["items"][i]
        cur_location = item_locations[cur_name]
        base_domain_state["locations"][cur_location]["items_id"].append(cur_id)
        base_domain_state["locations"][cur_location]["items_name"].append(cur_name)

    return json_response(data={"ok": "Domain registered successfully"})


@routes.post("/arrive")
async def register_with_hub_server(req: Request) -> Response:
    """Called by hub server each time a user enters or re-enters this domain."""
    data = await req.json()

    # Verify secret matches
    if data["secret"] != base_domain_info["secret"]:
        return json_response(status=403, data={"error": "Invalid secret"})

    user_id = data["user"]
    user_state = None
    user_domain_state = None
    if user_id in users:
        user_domain_state = users[user_id]
        # Update existing user - clear current item dictionaries
        user_state = user_domain_state["user_state"]
        for itemdic in user_state["items_id"].values():
            itemdic.clear()
        for itemdic in user_state["items_name"].values():
            itemdic.clear()
        # Update location to foyer and add to visited locations
        user_state["location"] = "nexus"
        user_state["visited_locations"].add("nexus")
        user_state["arrived"] = True
    else:
        # Create new user state object
        # Create new user state object with dual indexing
        user_domain_state = copy.deepcopy(base_domain_state)
        users[user_id] = user_domain_state
        user_state = {
            "items_id": {
                "owned": {},  # items from this domain in inventory
                "carried": {},  # items from other domains in inventory
                "dropped": {},  # items left in this domain
                "prize": {},  # items to find
            },
            "items_name": {"owned": {}, "carried": {}, "dropped": {}, "prize": {}},
            "arrived": True,
            "location": "nexus",
            "visited_locations": {"nexus"},
        }

    unused_depth = []

    # Process owned items
    for item in data["owned"]:
        user_state["items_id"]["owned"][item["id"]] = item
        user_state["items_name"]["owned"][item["name"]] = item["id"]

    # Process carried items
    for item in data["carried"]:
        user_state["items_id"]["carried"][item["id"]] = item
        user_state["items_name"]["carried"][item["name"]] = item["id"]

    # Process dropped items
    for item in data["dropped"]:
        user_state["items_id"]["dropped"][item["id"]] = item
        user_state["items_name"]["dropped"][item["name"]] = item["id"]
        # Add to domain's item dictionaries
        user_domain_state["item_ids"][item["id"]] = item
        user_domain_state["item_names"][item["name"]] = item["id"]
        # Place item in specified location
        location = item["location"]
        if location in user_domain_state["locations"]:
            if item["id"] not in user_domain_state["locations"][location]["items_id"]:
                user_domain_state["locations"][location]["items_id"].append(item["id"])
            if (
                item["name"]
                not in user_domain_state["locations"][location]["items_name"]
            ):
                user_domain_state["locations"][location]["items_name"].append(
                    item["name"]
                )

    # Process prize items
    for item in data["prize"]:
        user_state["items_id"]["prize"][item["id"]] = item
        user_state["items_name"]["prize"][item["name"]] = item["id"]
        # Add to domain's item dictionaries
        user_domain_state["item_ids"][item["id"]] = item
        user_domain_state["item_names"][item["name"]] = item["id"]
        depth = item["depth"]

        if depth == 0:
            # Place in puzzle room 0
            if (
                item["id"]
                not in user_domain_state["locations"]["puzzle_chamber_0"]["items_id"]
            ):
                user_domain_state["locations"]["puzzle_chamber_0"]["items_id"].append(
                    item["id"]
                )
            if (
                item["name"]
                not in user_domain_state["locations"]["puzzle_chamber_0"]["items_name"]
            ):
                user_domain_state["locations"]["puzzle_chamber_0"]["items_name"].append(
                    item["name"]
                )
        elif depth == 1:
            # Place in lore room
            if (
                item["id"]
                not in user_domain_state["locations"]["lore_room"]["items_id"]
            ):
                user_domain_state["locations"]["lore_room"]["items_id"].append(
                    item["id"]
                )
            if (
                item["name"]
                not in user_domain_state["locations"]["lore_room"]["items_name"]
            ):
                user_domain_state["locations"]["lore_room"]["items_name"].append(
                    item["name"]
            )
        elif depth == 2:
            # Place in puzzle room 2
            if (
                item["id"]
                not in user_domain_state["locations"]["puzzle_chamber_2"]["items_id"]
            ):
                user_domain_state["locations"]["puzzle_chamber_2"]["items_id"].append(
                    item["id"]
                )
            if (
                item["name"]
                not in user_domain_state["locations"]["puzzle_chamber_2"]["items_name"]
            ):
                user_domain_state["locations"]["puzzle_chamber_2"]["items_name"].append(
                    item["name"]
                )
        else:

            # Track items we couldn't place
            unused_depth.append(item)

    user_domain_state["user_state"] = user_state
    return json_response(status=200, data={"unused_items_depth": unused_depth})


@routes.post("/depart")
async def register_with_hub_server(req: Request) -> Response:
    data = await req.json()

    user_id = data["user"]
    if user_id not in users:
        return json_response(status=404, data={"error": "User not found"})

    user_domain_state = users[user_id]
    user_state = user_domain_state["user_state"]

    user_state["arrived"] = False

    return json_response(
        status=200,
        data={
            "ok": f'User succesfully departed from domain {base_domain_info["domain_id"]}'
        },
    )


@routes.post("/dropped")
async def register_with_hub_server(req: Request) -> Response:
    """Called by hub server each time a user drops an item in this domain.
    The return value must be JSON, and will be given as the location on subsequent /arrive calls
    """
    data = await req.json()

    # Verify secret matches
    if data["secret"] != base_domain_info["secret"]:
        return json_response(status=403, data={"error": "Invalid secret"})

    # Verify user exists
    user_id = data["user"]
    if user_id not in users:
        return json_response(status=404, data={"error": "User not found"})

    # Get user's current location and state and domainstate
    user_domain_state = users[user_id]
    user_state = user_domain_state["user_state"]

    if not user_state["arrived"]:
        return json_response(
            status=409,
            data={"error": "User has departed more recently than they have arrived"},
        )

    location = user_state["location"]

    item_id = data["item"]["id"]
    item = None

    # Try to find item in owned items
    if item_id in user_state["items_id"]["owned"]:
        item = user_state["items_id"]["owned"][item_id]
        del user_state["items_id"]["owned"][item_id]
        del user_state["items_name"]["owned"][item["name"]]

    # If not in owned, try carried items
    elif item_id in user_state["items_id"]["carried"]:
        item = user_state["items_id"]["carried"][item_id]
        del user_state["items_id"]["carried"][item_id]
        del user_state["items_name"]["carried"][item["name"]]

    # If item wasn't found in either place, return error
    if item is None:
        return json_response(status=404, data={"error": "Item not found"})

    # Add item to dropped items with current location
    item["location"] = location
    user_state["items_id"]["dropped"][item_id] = item
    user_state["items_name"]["dropped"][item["name"]] = item_id

    # Add item to domain's item dictionaries
    user_domain_state["item_ids"][item_id] = item
    user_domain_state["item_names"][item["name"]] = item_id

    # Add item to current location's items list
    user_domain_state["locations"][location]["items_id"].append(item_id)
    user_domain_state["locations"][location]["items_name"].append(item["name"])

    # Return the location where item was dropped
    return json_response(location)

def find_item_location(user_id, item_query):
    user_domain_state = users[user_id]
    user_state = user_domain_state["user_state"]
    
    location = user_state["location"]
    current_loc = user_domain_state["locations"][location]

    # Find the item
    found_item = None
    item_id = None
    returnList = [] #duplicate, found_item, item_id
    if item_query.isdigit():
        # Search by ID
        item_id = int(item_query)
        if item_id in current_loc["items_id"]:
            found_item = user_domain_state["item_ids"][item_id]
        returnList.append(False)
    else:
        # Search by name
        if current_loc["items_name"].count(item_query) > 1:
            returnList.append(True)
        else:
            returnList.append(False)
        if item_query in current_loc["items_name"]:
            item_id = user_domain_state["item_names"][item_query]
            found_item = user_domain_state["item_ids"][item_id]
    returnList.append(found_item)
    returnList.append(item_id)
    return returnList


@routes.post("/command")
async def handle_command(req: Request) -> Response:
    """Handle hub-server commands"""
    data = await req.json()

    # Get user state
    user_id = data["user"]
    if user_id not in users:
        return Response(
            text="You have to journey to this domain before you can send it commands."
        )

    user_domain_state = users[user_id]
    user_state = user_domain_state["user_state"]

    if not user_state["arrived"]:
        return json_response(
            status=409,
            data={"error": "User has departed more recently than they have arrived"},
        )

    command = data["command"]

    # Handle look command
    if command == ["look"]:
        location = user_state["location"]
        response = []

        # Add location description
        if location == "nexus":
            response.append(
                "You stand in the Nexus, the central chamber of the labyrinth. A massive metallic spire rises from the ground, its surface smooth and flawless, casting a brilliant rainbow reflection as light passes over it. " +
                "Faint pulses of energy ripple outward, like the heartbeat of a labyrinth.\nPortals appear in all cardinal directions, leading to unknown destinations. To the left is a chamber with a towering mechanical tree. Going forwards you come to a large bronze gate."
            )
        elif location == "secret_chamber":
            response.append(
                "You've discovered the sarcophagus of the Nameless King. The air here is cold, and the walls are lined with skeletal remains fused with twisted metal.\n" +
                "At the center lies a broken, bone-carved throne, shrouded in faint bioluminescent vines. Perhaps it is waiting for the return of its master. The only way back leads to the central nexus."
            )
        elif location == "puzzle_chamber_0":
            response.append(
                "This chamber hums with latent energy. Biomechanical surfaces glisten, and faint veins of light pulse through the floor like living circuitry.\n" +
                "A symbiotic lock rests at the far end, its tendrils twitching faintly in anticipation."
            )
        elif location == "lore_room":
            response.append(
                "The chamber feels sacred, as though it remembers a forgotten past. Rib-like metallic structures arch across the ceiling, forming an eerie dome. Relics from various civilizations are suspended in the center of the room, perhaps scientests once studied them here. In the center lies a pedestal with two indentations, perhaps a pair of hands might fit?\n"+
                "To the left lies a room adorned with gold and to the right another puzzle chamber, this time with the crumbling ruins of a futuristic laboratory. Going forwards you encounter a large silver gate."
            )
        elif location == "puzzle_chamber_1":
            response.append(
                "You enter a room of strange geometries. Metallic spires rise at odd angles, emitting melodic tones that vibrate softly, shattered glass lines the floor.\n"
                "A palm scanner rests near the far wall, glowing faintly with energy."
            )
        elif location == "puzzle_chamber_2":
            response.append(
                "This chamber feels alive. Tendrils of biomechanical material stretch across the walls and ceiling, pulsing in rhythmic waves. You feel you near the end of your journey. You see a warning, powerful items are once again sealed away in beams of light, perhaps this time for the safety of all who come. Next to the items are two retinal scanners.\n" +
                "A symbiotic lock rests at the far end, its tendrils twitching faintly in anticipation. Finally this time you find a large gold gate in froont of you."
            )
        elif location == "treasure_room":
            response.append(
                "You step into the treasure room—a vast, cathedral-like chamber shimmering with energy. Crystal formations jut from the ground, and at the center stands a massive vault. "+
                "The air hums with a faint, melodic resonance, as if something monumental lies just beyond reach.\n" + "On the wall a sample analyzer opens, waiting for something."
            )

        # Add visible items in current location
        location = user_domain_state["locations"][location]
        loc_items = location["items_id"]
        for item_id in loc_items:
            item = user_domain_state["item_ids"][item_id]
            # Check if item is depth-0 or was dropped here
            if ("depth" not in item or item["depth"] == 0) or (
                "location" in item and item["location"] == location
            ):
                response.append(f'There is a {item["name"]} <sub>{item_id}</sub> here.')
            elif ("suspension_beams" in location and location["suspension_beams"]):
                response.append(
                f'There is a {item["name"]} <sub>{item_id}</sub> gently suspended in a beam of light.'
            )
            else:
                 response.append(
                f'There is a {item["name"]} <sub>{item_id}</sub> locked in place by a beam of light.'
            )

        
        return Response(text="\n".join(response))
    elif len(command) == 2 and command[0] == "look":
        location = user_state["location"]
        locstate = user_domain_state["locations"][location]
        item = command[1]

        #special cases
        if location == "nexus" and (item == "altar" or item == "spire") and not all(locstate["altar"]):
            return Response(text="The altar does not respond, perhaps it awaits more offerings.") 
        elif location == "nexus" and (item == "altar" or item == "spire") and all(locstate["altar"]):
            return Response(text="The altar hums with a gentle glow try <code>touch</code>ing it.")
        
            
        # Regular items
        found_item = None

        # Try to find item in inventory first
        if item.isdigit():  # Search by ID
            item_id = int(item)
            if item_id in user_state["items_id"]["owned"]:
                found_item = user_state["items_id"]["owned"][item_id]
            elif item_id in user_state["items_id"]["carried"]:
                found_item = user_state["items_id"]["carried"][item_id]
        else:  # Search by name
            if item in user_state["items_name"]["owned"]:
                found_item = user_state["items_id"]["owned"][
                    user_state["items_name"]["owned"][item]
                ]
            elif item in user_state["items_name"]["carried"]:
                found_item = user_state["items_id"]["carried"][
                    user_state["items_name"]["carried"][item]
                ]

        # If not in inventory, check current location
        if not found_item:
            duplicate, found_item, item_id = find_item_location(user_id, item_query)
        location = user_state["location"]
        current_loc = user_domain_state["locations"][location]
        
        if (duplicate):
            return Response(
            text=f"Please specify the item ID, multiple instances of {item_query} where found."
        )
            
        if found_item:
            return Response(text=found_item["description"])

        return Response(text="I don't know how to do that.")
    elif len(command) == 2 and command[0] == "take":

        item_query = command[1]

        # Find the item
        duplicate, found_item, item_id = find_item_location(user_id, item_query)
        location = user_state["location"]
        current_loc = user_domain_state["locations"][location]
        
        if (duplicate):
            return Response(
            text=f"Please specify the item ID, multiple instances of {item_query} where found."
        )

        if found_item:
            # Check permissions based on depth and location or if dropped
            depth = found_item.get('depth', 0)
            
            can_take = ("suspension_beams" in current_loc and current_loc["suspension_beams"]) or (
                "location" in found_item and found_item["location"] == location
            )  or (depth == 0)

            if can_take:
                # Prepare transfer request
                transfer_data = {
                    "domain": base_domain_info["domain_id"],
                    "secret": base_domain_info["secret"],
                    "user": user_id,
                    "item": item_id,
                    "to": "inventory",
                }

                # Call transfer endpoint
                async with req.app.client.post(
                    base_domain_info["hub_url"] + "/transfer", json=transfer_data
                ) as resp:
                    if resp.status == 200:
                        # Remove item from location lists
                        current_loc["items_id"].remove(item_id)
                        current_loc["items_name"].remove(found_item["name"])

                        # Add item to appropriate user inventory based on ownership
                        if item_id in user_domain_state["owned"]:
                            user_state["items_id"]["owned"][item_id] = found_item
                            user_state["items_name"]["owned"][
                                found_item["name"]
                            ] = item_id
                        else:
                            user_state["items_id"]["carried"][item_id] = found_item
                            user_state["items_name"]["carried"][
                                found_item["name"]
                            ] = item_id
                        return Response(text=f"{found_item['name']} was taken.")

            # If we get here, either transfer failed or permissions weren't sufficient

        return Response(text=f"There's no {item_query} here to take")
    elif len(command) == 2 and command[0] == "go":

        current_location = user_state["location"]
        direction = command[1]

        # Check if direction is valid from current location
        exits = user_domain_state["locations"][current_location]["exits"]
        if direction not in exits:
            return Response(text="You can't go that way from here.")

        # Get destination
        destination = exits[direction]

        # Update user location
        user_state["location"] = destination

        # Build response
        response = []

        # Add location description or name based on visit history
        if destination in user_state["visited_locations"]:
            response.append(destination.capitalize())
        else:
            user_state["visited_locations"].add(destination)
            if destination == "foyer":
                response.append(
                    "You're in a hallway, unless it is a waiting room, or maybe a foyer? There are a couple of benches along the wall. To the east is an abandoned eatery of some kind blocked off by a grid of metal bars. To the north is a pair of double doors with a sign. To the east are double doors through which you can see indirect sunshine."
                )
            elif destination == "classroom":
                response.append(
                    "You're in an auditorium with several tiers of seats and stairs leading down."
                )
            else:  # podium
                response.append(
                    "This is a space for a speaker to use when addressing a class. There is a cabinet with several doors, a screen on a swinging arm, and an empty countertop. Stairs lead up into the student seating area."
                )
                if user_domain_state["locations"]["podium"]["cabinet_state"] == "open":
                    response.append(
                        "Inside the cabinet is a tangle of wires, a rack of computers and amplifiers, and a large switch."
                    )

        # Add visible items in new location
        loc_items = user_domain_state["locations"][destination]["items_id"]
        for item_id in loc_items:
            item = user_domain_state["item_ids"][item_id]
            # Check if item is depth-0 or was dropped here
            if ("depth" not in item or item["depth"] == 0) or (
                "location" in item and item["location"] == destination
            ):
                response.append(f'There is a {item["name"]} <sub>{item_id}</sub> here.')

        # If in podium with open cabinet, show depth-1 items
        if (
            destination == "podium"
            and user_domain_state["locations"]["podium"]["cabinet_state"] == "open"
        ):
            for item_id in user_domain_state["locations"]["podium"]["items_id"]:
                item = user_domain_state["item_ids"][item_id]
                if item.get("depth") == 1:
                    response.append(
                        f'There is a {item["name"]} <sub>{item_id}</sub> inside the cabinet.'
                    )

        return Response(text="\n".join(response))
    elif len(command) == 2:
        verb = command[0]
        print(command)
        item_query = command[1]

        found_item = None

        # Check if item is in inventory (owned or carried)
        if item_query.isdigit():
            # Search by ID
            item_id = int(item_query)
            if item_id in user_state["items_id"]["owned"]:
                found_item = user_state["items_id"]["owned"][item_id]
            elif item_id in user_state["items_id"]["carried"]:
                found_item = user_state["items_id"]["carried"][item_id]
        else:
            # Search by name
            if item_query in user_state["items_name"]["owned"]:
                found_item = user_state["items_id"]["owned"][
                    user_state["items_name"]["owned"][item_query]
                ]
            elif item_query in user_state["items_name"]["carried"]:
                found_item = user_state["items_id"]["carried"][
                    user_state["items_name"]["carried"][item_query]
                ]
        print(found_item)
        if found_item and "verb" in found_item:
            # Check if verb exists for item
            if verb in found_item["verb"]:
                return Response(text=found_item["verb"][verb])  # For any other command
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("-p", "--port", type=int, default=3400)
    args = parser.parse_args()

    import socket

    whoami = socket.getfqdn()
    if "." not in whoami:
        whoami = "localhost"
    whoami += ":" + str(args.port)
    whoami = "http://" + whoami
    print("URL to type into web prompt:\n\t" + whoami)
    print()

    app = web.Application(middlewares=[allow_cors])
    app.on_startup.append(start_session)
    app.on_shutdown.append(end_session)
    app.add_routes(routes)
    web.run_app(app, host=args.host, port=args.port)
