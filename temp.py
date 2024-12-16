domain_state = {
    'hub_url': '',
    'domain_id': None,
    'secret': None,
    'item_ids': {}, # ItemID : Item Description, this is for all items owned by this domain
    'users': {}, # UserID : User State
    'owned': [], # ItemIDs for objects owned here, but in other domains, these could also end up in the users inventory etc
    'locations': {
        'foyer': {
            'items': [], #ItemIDs for the items located here
            'exits': {'north': 'classroom', 'east': None}
        },
        'classroom': {
            'items': [], #ItemIDS for the items located here
            'exits': {'south': 'foyer', 'down': 'podium', 'west': 'podium'}
        },
        'podium': {
            'items': [], #ItemIDs for the items located here
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



