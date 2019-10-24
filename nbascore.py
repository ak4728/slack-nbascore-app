import os, sys
import random
import time
import re
from slackclient import SlackClient
from nba_api.stats.endpoints import *
import urllib.request, json, datetime
from nba_api.stats.static import players
from nba_api.stats.static import teams
from prettytable import PrettyTable

# instantiate Slack client
slack_client = SlackClient(token=os.environ['SLACK_API_TOKEN'])

# starterbot's user ID in Slack: value is assigned after the bot starts up
starterbot_id = 'AFJ3THYF7'


# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
EXAMPLE_COMMAND = "do"
TUKUR_COMMAND = "tukur"
SPORTS_COMMAND = "nba"
TEAM_COMMAND = "team"
FAV_TEAM_COMMAND = "nets"
PLAYER_COMMAND = "player"
STANDINGS_COMMAND = "standings"
SELECT_COMMAND = "select"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"
       
def post_message(msg, recipient):
    return self.slack_client.api_call(
        "chat.postMessage",
        channel='goygoy',
        text=msg,
        as_user=True
    )

def post_message_to_channel(response):
    response=response
    default_response = "default aq."
    response = "All games today:"+"\n"
    response = gameFinder(response,0)
    slack_client.api_call(
        "chat.postMessage",
        channel='goygoy',
        text=response or default_response,
        as_user=True
    )


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

def getStandings(conference):
    """
        Retrieves player stats for the last game.
        Career results can be added in the future
    """
    conference = conference.lower()
    now = str(datetime.datetime.now()-datetime.timedelta(hours=0)).replace('-','')[0:8]
    url = "http://data.nba.net/data/10s/prod/v1/current/standings_conference.json".format(now)
    try:
        with urllib.request.urlopen(url) as url2:
            data = json.loads(url2.read().decode())
            teamList=data['league']['standard']['conference'][conference]
            response = "{} Conference Standings\n".format(conference.capitalize())
            blocks = [
                        {
                            "type": "section",
                            "text": {
                                "text": "Conference Standings:",
                                "type": "mrkdwn"
                            },
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": "*Team*"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": "*W-L*"
                                }
                            ]
                        }
                    ]
            # This is to get around the limit of 10 items in a block table
            # I converted the type to text added new lines :)
            t= ""
            scores = ""
            for team in teamList:
                tname = str(teams.find_team_name_by_id(team['teamId'])['full_name'])
                t = t + str(tname)
                t = t + "\n"
                sc = str(team['win'])+str(" - ")+str(team['loss']) 
                scores = scores+ sc
                scores = scores +'\n'

            x = {
                    "type": "plain_text",
                    "text": t
                }
            blocks[0]['fields'].append(x)
            x = {
                    "type": "plain_text",
                    "text": scores
                }
            blocks[0]['fields'].append(x)
    except:
        response = '\nEither nbascore cannot locate standings or the season has not started yet.'
    return response,blocks

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


def gameFinder(response, deltahours, teamid='missing', now = str(datetime.datetime.now()-datetime.timedelta(hours=0)).replace('-','')[0:8]):
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
    url = "http://data.nba.net/data/10s/prod/v1/{}/scoreboard.json".format(now)

    req = urllib.request.urlopen(url)
    # try:
    #     url = "http://data.nba.net/data/10s/prod/v1/{}/scoreboard.json".format(now)
    #     req = urllib.request.urlopen(url)
    # except:
    #     now = getClosestDate()
    #     url = "http://data.nba.net/data/10s/prod/v1/{}/scoreboard.json".format(now)
    #     req = urllib.request.urlopen(url)
    with req as url2:
        data = json.loads(url2.read().decode())

        for i in range(len(data['games'])):
            vteamid = data['games'][i]['vTeam']['teamId']
            hteamid = data['games'][i]['hTeam']['teamId']
            try:
                vteamname = teams.find_team_name_by_id(vteamid)['full_name']
            except:
                vteamname = data['games'][i]['vTeam']['triCode']
            try:
                hteamname = teams.find_team_name_by_id(hteamid)['full_name']
            except:
                hteamname = data['games'][i]['vTeam']['triCode']
            vscore = data['games'][i]['vTeam']['score']
            hscore = data['games'][i]['hTeam']['score']
            gsid = data['games'][i]['statusNum']
            if teamid is 'missing':
                response = response + '{} {} {} - {} {} \n'.format( status[gsid-1], str(vteamname), str(vscore), str(hscore), str(hteamname) )
            elif teamid == vteamid or teamid == hteamid :
                response = response + '{} {} {} - {} {} \n'.format( status[gsid-1], str(vteamname), str(vscore), str(hscore), str(hteamname) )
    return response

def getClosestDate(url = "http://data.nba.net/data/10s/prod/v1/calendar.json", now = str(datetime.datetime.now()-datetime.timedelta(hours=0)).replace('-','')[0:8]):
    now = str(datetime.datetime.now()-datetime.timedelta(hours=0)).replace('-','')[0:8]
    with urllib.request.urlopen(url) as url2:
        data = json.loads(url2.read().decode())
        beforeGames = {}
        nextGames = {}
        for dates,games in data.items():
            try:
                # if the number of games are bigger than 0
                if games>0:
                    # To make sure that now is bigger than the date
                    if int(dates) < int(now): 
                        beforeGames[dates] = abs(int(dates)-int(now))
                    else:
                        nextGames[dates] = abs(int(dates)-int(now))
            except:
                beforeGames[dates] = 9999
                nextGames[dates] = 9999
        if data[now] == 0:
            foundDates = min(beforeGames.items(), key=lambda x: x[1])[0],min(nextGames.items(), key=lambda x: x[1])[0]
        else:
            foundDates = now, now
        return foundDates

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
    now = str(datetime.datetime.now()-datetime.timedelta(hours=0)).replace('-','')[0:8]
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
    elif command.startswith(STANDINGS_COMMAND):
        print("Standings request.")
        try:
            conference = command.rsplit(" ")[1]
            response = "{} Conference Standings".format(conference.upper())
            r, b = getStandings(conference)
            response = response + r
            blocks = b
        except:
            response= "Please provide a conference name."
        
    elif command.startswith("nasilsin"):
        response = "Iyiyiz abi, sukur..."
    elif command.endswith("?"):
        response = "Nebilim abicim ben ya..."
    elif command.startswith(EXAMPLE_COMMAND):
        response = "Sure...write some more code then I can do that!"
    # Team score calls
    elif command.lower().startswith((TEAM_COMMAND,FAV_TEAM_COMMAND)):
        print("Request for 1 Team.")
        try:
            if command.lower().startswith(TEAM_COMMAND):
                tname = command.rsplit(" ")
                response = "Team result:"+"\n"
                nbateam = teams.find_teams_by_full_name(tname[1])
            else:
                tname = command
                response = "Team result:"+"\n"
                nbateam = teams.find_teams_by_full_name(tname)
            teamid =  str(nbateam[0]['id'])
            response = gameFinder(response,0,teamid)
        except:
            response = "Please provide a team name."

    elif command.startswith(SPORTS_COMMAND):
        print("Request for all teams")
        try:
            if now == getClosestDate()[0]:
                response = "All games today:"+"\n"
                response = gameFinder(response,0)
            else:
                print(getClosestDate())
                response = "No games are scheduled today or nbascore cannot locate them.\n\n The latest game I can find was on {}:\n".format(str(datetime.datetime.strptime(getClosestDate()[0], "%Y%m%d"))[0:10])
                response = gameFinder(response,0,now=getClosestDate()[0])
                response += "\n\nAlso, the next game will be on {}:\n".format(str(datetime.datetime.strptime(getClosestDate()[1], "%Y%m%d"))[0:10])
                response = gameFinder(response,0,now=getClosestDate()[1])
        except:
            response='Error:'

   
    try:
        # Sends the response back to the channel
        slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            text=response or default_response,
            blocks=blocks
        )
    except:
        # Sends the response back to the channel
        slack_client.api_call(
            "chat.postMessage",
            channel=channel,
            text=response or default_response
        )




if __name__ == "__main__":
    try:
        if slack_client.rtm_connect(auto_reconnect=True,with_team_state=False):
            if str(sys.argv[1]) == 'test':
                print('Test phase')
                #x = gameFinder('test\n',0,now=getClosestDate()[1])
                x = getStandings('east')
            print("nbascore bot is connected and running!")
            # Read bot's user ID by calling Web API method `auth.test`

            starterbot_id = slack_client.api_call("auth.test")["user_id"]
            print(starterbot_id )
            while True:
                curent_time = datetime.datetime.now()
                current_hour = curent_time.hour
                current_minute = curent_time.minute
                if current_hour == 21:
                    if current_minute ==0:
                        post_message_to_channel('test')
                        time.sleep(60.01)
                command, channel = parse_bot_commands(slack_client.rtm_read())
                if command:
                    handle_command(command, channel)
                time.sleep(RTM_READ_DELAY)
        else:
            print("Connection failed. Exception traceback printed above.")
    except Exception as exc:
        print(exc)
        time.sleep(60)
