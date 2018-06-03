import configparser
import json
import sched
import time
import requests
from datetime import datetime
from telegram.ext import Updater, CommandHandler

interval = 0
updater = None
chats = []
artists = []
s = sched.scheduler(time.time, time.sleep)


class Song:
    def __init__(self, data):
        self.status = data['Status']
        self.id = data['Id']
        self.song_name = data['SongName']
        self.artist = data['Artist']
        self.time = datetime.strptime(data['Time'], '%Y-%m-%dT%H:%M:%S%z')
        self.length = int(data['Length'])
        self.cover = data['Cover']

    def __str__(self):
        return "Song(status=%s, id=%s, song_name=%s, artist=%s, time=%s, length=%s, cover=%s)" % \
               (self.status, self.id, self.song_name, self.artist, self.time, self.length, self.cover)

    def __repr__(self):
        return self.__str__()


def get_songs():
    response = requests.get('http://oe3meta.orf.at/oe3mdata/WebPlayerFiles/PlayList200.json')
    data = json.loads(response.content)
    songs = [Song(e) for e in data]
    return songs


def from_artist(artist, songs):
    return [s for s in songs if s.artist.lower() == artist.lower()]


def from_artists(artists, songs):
    res = []
    for artist in artists:
        res += from_artist(artist, songs)
    return res


def check_oe3():
    songs = get_songs()
    upcoming = from_artists(artists, songs)
    print("Found: " + str(upcoming) + "; " + str(songs))
    if upcoming:
        msg = "Upcoming songs:"
        for s in upcoming:
            msg += "\n" + s.song_name + " by " + s.artist + ": " + s.time.strftime("%H:%M:%S %d.%m.%Y")
        for chat in chats:
            updater.bot.send_message(chat, msg)


def bot_start(bot, update):
    if update.message.chat.id in chats:
        update.message.reply_text(
            'You are already subscribed. You will be notified if a song is played by the following artists: %s!' % ', '.join(
                artists))
    else:
        chats.append(update.message.chat.id)
        update_config()
        print("User " + update.message.from_user.first_name + " " + update.message.from_user.last_name + " subscribed!")
        update.message.reply_text(
            'You will be notified if a song is played by the following artists: %s!' % ', '.join(artists))


def read_config():
    global updater, artists, interval, chats
    config = configparser.ConfigParser()
    config.read('config.ini')
    section = config['config']
    interval = section.getint('interval')
    artists = section.get('artists').split(',')
    updater = Updater(section.get('token'))
    chats = [int(id) for id in section.get('chats').split(',') if id]


def update_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    section = config['config']
    section['chats'] = ','.join(str(id) for id in chats)
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def schedule_handler(sc):
    check_oe3()
    s.enter(interval, 1, schedule_handler, (sc,))


if __name__ == "__main__":
    read_config()
    updater.dispatcher.add_handler(CommandHandler('start', bot_start))
    updater.start_polling()
    check_oe3()
    s.enter(interval, 1, schedule_handler, (s,))
    s.run()
