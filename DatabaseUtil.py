import sqlite3
import sys
import os
import time

# Put the root of the library here
music_root = 'E:\Music\Music\Lossy'


# Prints message containing valid arguments
def missing_arg():
    print('Please supply only one command line argument of the following when calling this file.')
    print('scan || -s: Creates tables, then does full scan of library')
    print('rebuild || -r: Drops tables, creates new tables, then does a complete scan of the library')


# Connects to the music database, and returns the connection object
def connect_music():
    conn = sqlite3.connect('Music.db')
    return conn


# Build the music database
# Primary table called music is used to track the ids from the other tables, and contains the path to the track
# Secondary table called artist tracks the artist name, and points back to the artist id used to construct music(id)
# Secondary table called album tracks the album name, and points back to the album id used to construct music(id)
# Secondary table called title tracks the track title, and points back to the title id used to construct music(id)
def build_music(conn):
    c = conn.cursor()
    print('Building music table')
    c.execute('''CREATE TABLE music (
                     id INTEGER PRIMARY KEY,
                     artist_id INTEGER,
                     album_id INTEGER,
                     title_id INTEGER,
                     path TEXT)''')
    print('Building artist table')
    c.execute('''CREATE TABLE artist (
                     id INTEGER PRIMARY KEY,
                     artist TEXT,
                     FOREIGN KEY (id) REFERENCES music(artist_id))''')
    print('Building album table')
    c.execute('''CREATE TABLE album (
                     id INTEGER PRIMARY KEY,
                     album TEXT,
                     FOREIGN KEY (id) REFERENCES music(album_id))''')
    print('Building title table')
    c.execute('''CREATE TABLE title (
                     id INTEGER PRIMARY KEY,
                     title TEXT,
                     FOREIGN KEY (id) REFERENCES music(title_id))''')
    conn.commit()


def drop_music(conn):
    c = conn.cursor()
    print('Dropping music table')
    c.execute("DROP TABLE music")
    print('Dropping artist table')
    c.execute("DROP TABLE artist")
    print('Dropping album table')
    c.execute("DROP TABLE album")
    print('Dropping title table')
    c.execute("DROP TABLE title")
    conn.commit()


# Scans through the root at the top of the file
# Artist is assigned path_split[0]
# Album is assigned path_split[(len(path_string) - 1)]
# Numerically increases in each level to build keys
# Writes records to database
# Commits at point chosen at the top of the file
def scan_music(conn):
    # Marks start time
    time.perf_counter()
    c = conn.cursor()
    # Used to pad keys
    album_key = 10000
    artist_key = 10000
    title_key = 10000
    current_artist = ""
    current_album = ""
    for root, dirs, files in os.walk(music_root):
        for file in files:
            # Removes library root from path that is put into database, then splits into folders on '\'
            path_split = root[len(music_root):].split('\\')
            # Splits track number from track title
            file_split = file.split(' - ')
            # Artist is the first folder name in the path
            artist = path_split[1]
            # Album will be the last in the case of nested discs (used to get around Chopin collection)
            album = path_split[(len(path_split) - 1)]
            if current_artist != artist:
                artist_key += 1
                current_artist = artist
                c.execute('''INSERT INTO artist VALUES (
                      ?, ?)''', (artist_key, artist))
                print("{} added.".format(artist))
            if current_album != album:
                album_key += 1
                current_album = album
                c.execute('''INSERT INTO album VALUES (
                      ?, ?)''', (album_key, album))
            if len(file_split) == 2:
                title_key += 1
                c.execute('''INSERT INTO title VALUES (
                             ?, ?)''', (title_key, file_split[1]))
                c.execute('''INSERT INTO music VALUES (
                             ?, ?, ?, ?, ?)''',
                             (int(str(artist_key) + str(album_key) + str(title_key)),
                             artist_key, album_key, title_key, "\\".join((root[len(music_root):], file))))
    conn.commit()
    print('----------------')
    print("Artists added: {}".format(artist_key - 10000))
    print("Albums added: {}".format(album_key - 10000))
    print("Tracks added: {}".format(title_key - 10000))
    print("Total time to scan: {:.2f} seconds".format(time.perf_counter()))


# Completes one final commit, then closes connection to the database
def close_music(conn):
    conn.commit()
    conn.close()
    print("Connection to Music.db closed.")


# Using args passed, processes command, or spits error message for unknown, or insufficient arguments
if len(sys.argv) == 1 or len(sys.argv) > 2:
    missing_arg()
else:
    if sys.argv[1] == 'scan' or sys.argv[1] == '-s':
        conn = connect_music()
        build_music(conn)
        print('----------------')
        scan_music(conn)
        print('----------------')
        close_music(conn)
    elif sys.argv[1] == 'rescan' or sys.argv[1] == '-r':
        conn = connect_music()
        drop_music(conn)
        print('----------------')
        build_music(conn)
        print('----------------')
        scan_music(conn)
        print('----------------')
        close_music(conn)
    else:
        missing_arg()
