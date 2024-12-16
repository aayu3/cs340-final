import subprocess, signal, json, random, sys, time
import urllib.request
import pytest
import asyncio
import aiohttp
import re


    # foyer description
s1 = "You're in a hallway, unless it is a waiting room, or maybe a foyer? There are a couple of benches along the wall. To the east is an abandoned eatery of some kind blocked off by a grid of metal bars. To the north is a pair of double doors with a sign. To the east are double doors through which you can see indirect sunshine."

    # foyer read sign
s2 = 'The sign says <q>1404</q>'

    # classroom description
s3 = "You're in an auditorium with several tiers of seats and stairs leading down."

    # podium description
s4 = "This is a space for a speaker to use when addressing a class. There is a cabinet with several doors, a screen on a swinging arm, and an empty countertop. Stairs lead up into the student seating area."
    # podium description has this on a second line if the cabinet it open
s5 = "Inside the cabinet is a tangle of wires, a rack of computers and amplifiers, and a large switch."

    # podium look screen
s6 = "The screen is blank. You notice a cable leading down into the cabinet."
s7 = "The screen shows a password prompt. It's not the usual NetID prompt: it wants a special in-game password instead."
s8 = "The screen shows fireworks and confetti and flashed the words \"You won!\".\n\nIn smaller text you notice the phrase \"That's it. There's nothing more to the game in this MP.\""

    # podium open cabinet
s9 = "It seems to be locked."
s10 = "You open the cabinet doors." # then the same inside-cabinet line as podium description
s11 = "It's already open."

    # podium close cabinet
s12 = "You close the doors."
s13 = "It's already closed."

    # podium look cabinet
s14 = "The cabinet has a pair of doors with a small lock; the doors are closed."
s15 = "The cabinet has a pair of doors with a small lock; the doors are open." # then the same inside-cabinet line as podium description

    # podium use key cabinet
s16 = "You use the key to unlock the cabinet doors."
s17 = "You use the key to lock the cabinet doors."
s18 = "You don't have a key."

    # podium use switch if cabinet is open
s19 = "You move the switch to the up position."
s20 = "You move the switch to the down position."

    # podium look switch if cabinet is open
s21 = "The switch has a small label reading \"power\" and is in the up position."
s22 = "The switch has a small label reading \"power\" and is in the down position."

    # podium tell screen xyzzy in the password state
s23 = "You enter the password \"XYZZY\". After a few seconds of thinking, the screen fills with fireworks and confetti and flashes the words \"You won!\""

    # podium tell screen anything else in the password state
r1 = re.compile(r"You enter the password \"(.*?)\" but the computer doesn't accept it.")

    # podium depth-1 item you are hosting for other domains if cabinet is open
r2 = re.compile(r'There is a (.*?) <sub>(.*?)</sub> inside the cabinet.')
            

    # go <direction> where the direction is not supported
s24 = "You can't go that way from here."

    # Any command you can't handle
s25 = "I don't know how to do that."

    # After a room description for each item in that location
r3 = re.compile(r'There is a (.*?) <sub>(.*?)</sub> here.')

    # take something not here
r4 = re.compile(r"There's no (.*?) here to take")

    # any /command if the user has not yet been registered with /arrive
s26 = "You have to journey to this domain before you can send it commands."
    
    # when entering or looking in a location with a dropped or depth-0 hosted item
r5 = re.compile(r'There is a (.*?) <sub>(.*?)</sub> here.')


class sessionwrapper:
  def __init__(self):
    self.p = random.randrange(1<<14, 1<<16)
  def __enter__(self):
    self.hub = subprocess.Popen([sys.executable, "hub.py", '--port', str(self.p)])
    self.dom = subprocess.Popen([sys.executable, "domain.py", '--port', str(self.p+1)])
    time.sleep(0.5)
    return self.p, self.p+1
  def __exit__(self, extype, exval, extb):
    self.hub.send_signal(signal.Signals.SIGINT)
    self.dom.send_signal(signal.Signals.SIGINT)
    time.sleep(0.1)
    self.hub.terminate()
    self.dom.terminate()

class playwrapper:
  def __init__(self):
    self.sw = sessionwrapper()
  def __enter__(self):
    self.h, self.d = self.sw.__enter__()
    status, data = send_recv(self.h, '/domain', f"http://localhost:{self.d}")
    assert status == 200, "hub's /domain to domain's /register"
    status, data = send_recv(self.h, '/mode', 'play')
    assert status == 200, "hub's /mode"
    status, data = send_recv(self.h, '/login', '', method='GET')
    assert status == 200, "hub's /login to domain's first /arrive"
    assert isinstance(data, dict), "/arrive response type"
    for key in 'domain','id','secret':
      assert key in data, f"/arrive set of keys ({key})"
    self.id = data['id']
    self.secret = data['secret']
    self.domain = data['domain']
    return self
  def command(self, *words):
    if words[0] in ['drop','inventory','journey']:
      status, data = send_recv(self.h, '/command', {'user':self.id, 'secret':self.secret, 'command':words})
    else:
      status, data = send_recv(self.d, '/command', {'user':self.id, 'command':words})
    return data
  def __exit__(self, extype, exval, extb):
    self.sw.__exit__(extype, exval, extb)
    


def send_recv(port, path, data, method='POST'):
  if isinstance(data, bytes): pass
  elif isinstance(data, str): data = data.encode('utf-8')
  else: data = json.dumps(data).encode('utf-8')
  req = urllib.request.Request(url=f'http://localhost:{port}{path}', data=data, method=method)
  with urllib.request.urlopen(req) as f:
    status = f.status
    data = f.read().decode('utf-8')
  try: return status, json.loads(data)
  except: return status, data

def test_register(aiohttp_client):
  with sessionwrapper() as (h,d):
    status, data = send_recv(h, '/domain', f"http://localhost:{d}")
    assert status == 200
    status, data = send_recv(h, '/mode', 'play')
    assert status == 200
    assert data == 'Now in play mode'

def test_login(aiohttp_client):
  with playwrapper() as c:
    assert c.domain['name'] == 'MP10'
    assert c.domain['description'] == 'An example domain based in Siebel 1404 and its surroundings.'

def test_map(aiohttp_client):
  with playwrapper() as c:
    f1 = c.command('look')
    assert s1 in f1
    assert len(f1) < len(s1) + 100

    c1 = c.command('go','north')
    assert s3 in c1
    assert len(c1) < len(s3) + 100

    p1 = c.command('go','down')
    assert s4 in p1
    assert len(p1) < len(s4) + 100
    
    c.command('go','up')
    c2 = c.command('look')
    assert s3 in c2
    assert len(c2) < len(s3) + 100

    c.command('go','west')
    p2 = c.command('look')
    assert s4 in p2
    assert len(p2) < len(s4) + 100

    assert s24 == c.command('go','south')
    assert p2 == c.command('look')

    c.command('go','east')
    c3 = c.command('look')
    assert c2 == c3

    c.command('go','south')
    f2 = c.command('look')
    assert f1 == f2

def test_foyer_sign(aiohttp_client):
  with playwrapper() as c:
    assert s2 == c.command('read','sign')

def test_see_paper(aiohttp_client):
  with playwrapper() as c:
    f1 = c.command('look')
    m = r5.search(f1)
    assert m is not None, "Paper visible in starting location"
    
    assert m.group(1) == 'paper'
    pid = int(m.group(2))
    
def test_use_paper(aiohttp_client):
  with playwrapper() as c:
    f1 = c.command('look')
    m = r5.search(f1)
    assert m is not None, "Paper visible in starting location"
    
    assert m.group(1) == 'paper'
    pid = int(m.group(2))
    
    c.command('take','paper')
    msg = c.command('read','paper')
    assert msg == 'The paper reads <q>XYZZY</q>'
    
    f1 = c.command('look')
    m = r5.search(f1)
    assert m is None, "Paper gone after being taken"
    
    c.command('go', 'north')
    c.command('drop','paper')
    c.command('go', 'south')
    msg = c.command('read','paper')
    assert msg == s25, "can't read after dropping"

    f1 = c.command('look')
    m = r5.search(f1)
    assert m is None, "Paper gone after being dropped elsewhere"

    c.command('go', 'north')
    c1 = c.command('look')
    assert 'There is a paper' in c1, 'Paper found where dropped'

def test_hosted_item(aiohttp_client):
  with playwrapper() as c:
    c1 = c.command('go','north')
    m = r5.search(c1)
    print("m :" + str(m))
    assert m is not None, "depth=0 item in classroom"
    assert m.group(1) in ('i-card','axe'), "depth=0 item name from hub"
    print("Item was found")

    other = 'axe' if 'i-card' == m.group(1) else 'i-card'
    print("value of other: " + other)

    print("value of r4: " + str(r4))
    print(c.command('take', other))
    m2 = r4.fullmatch(c.command('take', other))
    print("value of m2: " + str(m2))
    assert m2 is not None, "recognize the other item is not there"
    assert m2.group(1) == other, "recognize the other item is not there"

    assert m.group(1) not in c.command('inventory')
    c1 = c.command('take',m.group(1))
    assert m.group(1) in c.command('inventory')
    
    if 'axe' == m.group(1):
      assert c.command('look','axe') == "An axe, colored like those used by firefighters to break through burning walls."
      assert c.command('use','axe') == "An axe like this could do some serious damage. Best not to use it anywhere on campus."
    else:
      assert c.command('look','i-card') == "A University ID card. The name is smudged, but you recognize the face; this is the person who came from IT to fix the classroom computer when it broke down."
      assert c.command('read','i-card') == "The text is smudged and you don't know how to read bar codes or magnetic stripes."
    
    assert 'key' not in c.command('inventory')
    c.command('go','south')
    assert '$journey east' == c.command('go','east')
    c.command('journey','east')
    assert 'key' in c.command('inventory')
    
def test_missing_key(aiohttp_client):
  with playwrapper() as c:
    c.command('take','paper')
    c.command('go','north')
    c.command('take','axe')
    c.command('take','i-card')
    c.command('go', 'down')
    assert c.command('look', 'cabinet') == s14
    assert c.command('look', 'screen') == s6
    assert c.command('tell', 'screen', 'xyzzy') == s25
    #error
    assert c.command('look', 'switch') == s25
    assert c.command('use', 'switch') == s25
    assert c.command('open', 'cabinet') == s9
    assert c.command('close', 'cabinet') == s13
    assert c.command('use', 'key', 'cabinet') == s18
    
def test_with_key_1(aiohttp_client):
  with playwrapper() as c:
    c.command('go','north')
    c.command('take','axe')
    c.command('take','i-card')
    c.command('go','south')
    c.command('go','east')
    c.command('journey','east')
    c.command('go','north')
    c.command('go', 'west')
    assert c.command('use', 'key', 'cabinet') == s16
    assert c.command('use', 'key', 'cabinet') == s17
    assert c.command('open', 'cabinet') == s9
    assert c.command('use', 'key', 'cabinet') == s16
    oc = c.command('open', 'cabinet')
    assert oc.startswith(s10 + '\n' + s5), "open shows success and inside of cabinet"
    print(oc)
    m = r2.search(oc)
    assert m is not None, "hosted depth=1 item"
    assert m.group(1) == 'toy', 'expected item name'
    lp = c.command('look')
    assert s5 in lp, "look sees inside of cabinet"
    m = r2.search(lp)
    if not m: m = r5.search(lp)
    assert m is not None, "look shows items inside cabinet"
    print(lp)
    temp = c.command('take', 'toy')
    print(temp)
    lp = c.command('look')
    print(lp)
    assert r2.search(lp) is None and r5.search(lp) is None, "can take items from inside open cabinet"
    
    
def test_with_key_2(aiohttp_client):
  with playwrapper() as c:
    c.command('go','north')
    c.command('take','axe')
    c.command('take','i-card')
    c.command('go','south')
    c.command('go','east')
    c.command('journey','east')
    c.command('go','north')
    c.command('go', 'west')
    c.command('use', 'key', 'cabinet')
    c.command('open', 'cabinet')
    assert c.command('look', 'switch') == s22, "look switch down"
    assert c.command('use', 'switch') == s19, "use switch down -> up"
    assert c.command('look', 'switch') == s21, "look switch up"
    assert c.command('use', 'switch') == s20, "use switch up -> down"
    assert c.command('look', 'switch') == s22, "look switch down again"
    assert c.command('use', 'switch') == s19, "use switch down -> up again"
    assert c.command('look', 'screen') == s7, "password screen"
    pw = c.command('tell', 'screen', 'swordfish')
    assert r1.fullmatch(pw) is not None, "bad password attempt"
    assert r1.fullmatch(pw).group(1) == 'swordfish', "bad password attempt"
    assert c.command('look', 'screen') == s7, "password screen after bad password"
    assert c.command('tell', 'screen', 'xyzzy') == s23, "good password attempt"
    assert c.command('look', 'screen') == s8, "look win screen"
