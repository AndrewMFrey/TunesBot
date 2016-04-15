import asyncio
import discord
import sqlite3

email = 'andrewmarkfrey+bot@gmail.com'
password = 'QWE##rty64'
opusPath = 'D:\Andrew\Code\TunesBot\libopus-0.dll'
music_root = 'E:\Music\Music\Lossy'


conn = sqlite3.connect('Music.db')
c = conn.cursor()


if not discord.opus.is_loaded():
    # the 'opus' library here is opus.dll on windows
    # or libopus.so on linux in the current directory
    # you should replace this with the location the
    # opus library is located in and with the proper filename.
    discord.opus.load_opus(opusPath)


class VoiceEntry:
    def __init__(self, message, song):
        self.requester = message.author
        self.channel = message.channel
        self.song = song


class Bot(discord.Client):
    def __init__(self):
        super().__init__()
        self.songs = asyncio.Queue()
        self.play_next_song = asyncio.Event()
        self.starter = None
        self.player = None
        self.current = None

    def toggle_next_song(self):
        self.loop.call_soon_threadsafe(self.play_next_song.set)

    def can_control_song(self, author):
        return author == self.starter or (self.current is not None and author == self.current.requester)

    def is_playing(self):
        return self.player is not None and self.player.is_playing()

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.channel.is_private:
            await self.send_message(message.channel, 'You cannot use this bot in private messages.')

        if message.content.startswith('!join'):
            if self.is_voice_connected():
                await self.send_message(message.channel, 'Already connected to a voice channel')
            channel_name = message.content[5:].strip()
            check = lambda c: c.name == channel_name and c.type == discord.ChannelType.voice

            channel = discord.utils.find(check, message.server.channels)
            if channel is None:
                await self.send_message(message.channel, 'Cannot find a voice channel by that name.')

            await self.join_voice_channel(channel)
            self.starter = message.author

        elif message.content.startswith('!leave'):
            if not self.can_control_song(message.author):
                return
            self.starter = None
            await self.voice.disconnect()
        elif message.content.startswith('!pause'):
            if not self.can_control_song(message.author):
                fmt = 'Only the requester ({0.current.requester}) can control this song'
                await self.send_message(message.channel, fmt.format(self))

            if self.player.is_playing():
                self.player.pause()
        elif message.content.startswith('!resume'):
            if not self.can_control_song(message.author):
                fmt = 'Only the requester ({0.current.requester}) can control this song'
                await self.send_message(message.channel, fmt.format(self))

            if self.player is not None and not self.is_playing():
                self.player.resume()
# Queues album or track for play
        elif message.content.startswith('!queue'):
            search_type = message.content[6:].strip().split(" ")[0]
            search_data = message.content[(8 + len(search_type)):]
            if search_type == 'artist':
                await self.send_message(message.channel, "Artist queueing is not supported")
            elif search_type == 'album':
                album_id = str(c.execute('''SELECT id FROM album WHERE album = ?''', (search_data,)).fetchall())[2:-3]
                if len(album_id) == 0:
                    await self.send_message(message.channel,
                                            "No album of that name found. Use !search to see what's available")
                else:
                    album = c.execute('''SELECT path FROM music WHERE album_id = ?''', (album_id,)).fetchall()
                    for track in album:
                        track = str(track)[2:-3]
                        print(track)
                        if track[len(track) - 4:] == '.mp3':
                            await self.songs.put(VoiceEntry(message, (music_root + '\\' + track)))
                            await self.send_message(message.channel, 'Successfully registered {}'.format(track))
                        else:
                            await self.send_message(message.channel, 'Unsupported format for {}'.format(track))
                await self.send_message(message.channel, 'Successfully registered {}'.format(search_data))
            elif search_type == 'track':
                title_id = c.execute('''SELECT id FROM title WHERE title = ?''', (search_data,)).fetchall()[1:-2]
                if len(title_id) == 0:
                    await self.send_message(message.channel,
                                            "No track of that name found. Use !search to see what's available")
                else:
                    title = str(c.execute('''SELECT path FROM music WHERE title_id = ?''', (title_id,)).fetchall())[2:-3]
                    await self.songs.put(VoiceEntry(message, (music_root + '\\' + title)))
                    await self.send_message(message.channel, 'Successfully registered {}'.format(music_root + '\\' + title))
        elif message.content.startswith('!play'):
            if self.player is not None and self.player.is_playing():
                await self.send_message(message.channel, 'Already playing a song')
                return
            while True:
                if not self.is_voice_connected():
                    await self.send_message(message.channel, 'Not connected to a voice channel')
                    return

                self.play_next_song.clear()
                self.current = await self.songs.get()
                self.player = self.voice.create_ffmpeg_player(self.current.song, after=self.toggle_next_song)
                self.player.start()
#                fmt = 'Playing song "{0.song}" from {0.requester}'
#                await self.send_message(self.current.channel, fmt.format(self.current))
                await self.send_message(self.current.channel,
                                        "Playing song {} from {}".format(self.current.song[len(music_root):],
                                                                         self.current.requester))
                await self.play_next_song.wait()
# Searches for artist, album, or track
# Command formatted as '!search <type> query
# Search data should not be wrapped in quotes
        elif message.content.startswith('!search'):
            if str(message.content).find(';') != -1:
                await self.send_message(message.channel, "Fuck off, m8")
                return
            search_type = message.content[7:].strip().split(" ")[0]
            search_data = message.content[(9 + len(search_type)):]
            if search_type == 'artist':
                artist = search_data
                print(artist)
                results = c.execute('''SELECT artist FROM artist WHERE artist LIKE ?''',
                                    (("%" + artist + "%"),)).fetchall()
                if len(results) > 5:
                    await self.send_message(message.channel,
                                        "{} results returned. Be more specific for a full list.".format(len(results)))
                else:
                    for result in results:
                        print(result[0])
                        await self.send_message(message.channel, result[0])
            elif search_type == 'album':
                album = search_data
                print(album)
                results = c.execute('''SELECT album FROM album WHERE album LIKE ?''',
                                    (("%" + album + "%"),)).fetchall()
                if len(results) > 5:
                    await self.send_message(message.channel,
                                        "{} results returned. Be more specific for a full list.".format(len(results)))
                else:
                    for result in results:
                        print(result[0])
                        await self.send_message(message.channel, result[0])
            elif search_type == 'track':
                title = search_data
                print(title)
                results = c.execute('''SELECT title FROM title WHERE title LIKE ?''',
                                    (("%" + title + "%"),)).fetchall()
                if len(results) > 5:
                    await self.send_message(message.channel,
                                        "{} results returned. Be more specific for a full list.".format(len(results)))
                else:
                    for result in results:
                        print(result[0])
                        await self.send_message(message.channel, result[0])
            else:
                await self.send_message(message.channel, "Invalid parameters.")


    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')


bot = Bot()
bot.run(email, password)