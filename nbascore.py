import os
import random
import time
import re
from slackclient import SlackClient
from nba_api.stats.endpoints import *
import urllib.request, json, datetime
from nba_api.stats.static import players
from nba_api.stats.static import teams


# instantiate Slack client
slack_client = SlackClient('s')
# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = None


# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "do"
TUKUR_COMMAND = "tukur"
SPORTS_COMMAND = "nba"
TEAM_COMMAND = "team"
PLAYER_COMMAND = "player"
SELECT_COMMAND = "select"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"
       
        
def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None

def getPlayer(playerId,fullname):
    """
        Retrieves player stats for the last game.
        Career results can be added in the future
    """
    url = "http://data.nba.net/prod/v1/2018/players/{}_gamelog.json".format(playerId)
    with urllib.request.urlopen(url) as url2:
        data = json.loads(url2.read().decode())
        pI=data['league']['standard'][0]['stats']
        gamedate = data['league']['standard'][0]['gameDateUTC']
        text = "Game stats for {} ({}) \n Pts {} \n Ass {}\n OfR {}\n DefR {}\n TotR {}\n".format(fullname 
,gamedate,pI['points'],pI['assists'],pI['offReb'],pI['defReb'],pI['totReb'])
    return text


def gameFinder(response, deltahours, teamid='missing'):
    """
        Retrieves games and scores for today.
        Delta hours can be used to retrieve historical results in the future.
        E.g.
            @nbascore nba yesterday
            if yesterday:
                deltahours = 24
            else:
                deltahours = 0
    """
    status = [':no_entry:',':basketball:',':checkered_flag:']
    points = 0
    now = str(datetime.datetime.now()-datetime.timedelta(hours=deltahours)).replace('-','')[0:8]
    url = "http://data.nba.net/prod/v1/{}/scoreboard.json".format(now)
    with urllib.request.urlopen(url) as url2:
        data = json.loads(url2.read().decode())
        for i in range(len(data['games'])):
            vteamid = data['games'][i]['vTeam']['teamId']
            hteamid = data['games'][i]['hTeam']['teamId']
            vteamname = teams.find_team_name_by_id(vteamid)['full_name']
            hteamname = teams.find_team_name_by_id(hteamid)['full_name']
            vscore = data['games'][i]['vTeam']['score']
            hscore = data['games'][i]['hTeam']['score']
            gsid = data['games'][i]['statusNum']
            if teamid is 'missing':
                response = response + '{} {} {} - {} {} \n'.format( status[gsid-1], str(vteamname), str(vscore), str(hscore), str(hteamname) )
            elif teamid == vteamid or teamid == hteamid :
                response = response + '{} {} {} - {} {} \n'.format( status[gsid-1], str(vteamname), str(vscore), str(hscore), str(hteamname) )
    return response


def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    default_response = "La bi dur gotunden kod uydurma ya. *{}* ne amk?".format(command)
    global pname
    # Finds and executes the given command, filling in response
    response = None
    # This is where you start to implement more commands!
    if command.startswith(TUKUR_COMMAND):
        response = "puh amk..."
    # Selection command after finding multiple players
    elif command.startswith(SELECT_COMMAND):
        ij = int(command.rsplit(" ")[1])-1
        try:
            pid = players.find_players_by_full_name(pname)[ij]['id']
            print(pname)
            fullname = players.find_players_by_full_name(pname)[ij]['full_name']
            print(pid,fullname)
            response = getPlayer(pid,fullname)
        except:
            reponse = "Something is wrong here..."
    # Player stat calls
    elif command.startswith(PLAYER_COMMAND):
        ninput = command.rsplit(" ")
        response = ""
        if  len(ninput)>2:
            pname = command.rsplit(" ")[1].capitalize()+' '+command.rsplit(" ")[-1].capitalize()
        else:
            pname = command.rsplit(" ")[1]
        try:
            resp = players.find_players_by_full_name(pname)
            if len(resp)>1:
                response = response + "I found more than one {}".format(pname.capitalize()) + '\n'
                response = response + "Here is the list, please make a selection (e.g.= @nbascore select 1)" + '\n'
                for i in range(len(resp)):
                    response = response+str(i+1)+" "+ str(players.find_players_by_full_name(pname)[i]['full_name'])+"\n"
            else:
                pid = players.find_players_by_full_name(pname)[0]['id']
                fullname = players.find_players_by_full_name(pname)[0]['full_name']
                response = getPlayer(pid,fullname)
        except:
            response = "No player with that name."
    # Just some answers to random questions
    elif command.startswith("nasilsin"):
        response = "Iyiyiz abi, sukur..."
    elif command.endswith("?"):
        response = "Nebilim abicim ben ya..."
    elif command.startswith(EXAMPLE_COMMAND):
        response = "Sure...write some more code then I can do that!"
    # Team score calls
    elif command.startswith(TEAM_COMMAND):
    	print("Request for 1 Team.")
    	try:
	    	tname = command.rsplit(" ")
	    	response = "Team result:"+"\n"
	    	nbateam = teams.find_teams_by_full_name(tname[1])
	    	teamid =  str(nbateam[0]['id'])
	    	response = gameFinder(response,0,teamid)
    	except:
    		response = "Please provide a team name."

    elif command.startswith(SPORTS_COMMAND):
    	print("Request for all teams")
    	response = "All games today:"+"\n"
    	response = gameFinder(response,0)

	
    		

    # Sends the response back to the channel
    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )




if __name__ == "__main__":
    try:
        if slack_client.rtm_connect(with_team_state=False):
            print("Starter Bot connected and running!")
            # Read bot's user ID by calling Web API method `auth.test`

            starterbot_id = slack_client.api_call("auth.test")["user_id"]
            print(starterbot_id )
            while True:
                command, channel = parse_bot_commands(slack_client.rtm_read())
                if command:
                    handle_command(command, channel)
                time.sleep(RTM_READ_DELAY)
        else:
            print("Connection failed. Exception traceback printed above.")
    except:
        time.sleep(60)
