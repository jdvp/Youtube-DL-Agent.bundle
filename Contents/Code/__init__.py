#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, hashlib, re, inspect, json
from io import open
import json

def Start():
    Log("Starting up ...")

def getMetadataExpectedPath(media):
    Log("Youtube-DL Agent: Running getMetadataExpectedPath")
    file = ""
    for s in media.seasons:
        for e in media.seasons[s].episodes:
            file = media.seasons[s].episodes[e].items[0].parts[0].file

            # If there is no file we can't get any metadata
            if file == "":
                continue

            # Split the filepath and file extension
            filepath, file_extension = os.path.splitext(file)
            filepath = filepath.strip()

            return filepath + ".info.json"
    return ""

def loadTvShowMetadata(metadata, metadataFile):
    Log("Youtube-DL Agent: Running loadTvShowMetadata")

    Log("Opening metadata file: {}".format(metadataFile))
    if metadataFile != "" and os.path.isfile(metadataFile):
        try:
            with open(metadataFile, encoding="utf-8") as json_file:
                data = json.load(json_file)

                metadata.title = data['uploader']
                metadata.studio = data['uploader']
                if 'playlist_title' in data:
                    metadata.summary = data['playlist_title']

                Log("Finished reading metadata file: {}".format(metadataFile))
        except IOError:
            Log("Could not access metadata file '{}'".format(metadataFile))
    else:
        Log("loadTvShowMetadata: metadata file does not seem to exist")

def loadTvShowArt(metadataFile, mediaType, collection):
    Log("Youtube-DL Agent: Running loadTvShowArt for {}".format(mediaType))

    filedir = os.path.split(metadataFile)[0]

    # Check if there is a thumbnail for this Show (/Youtuber)
    for extension in [".jpg", ".jpeg", ".webp", ".png", ".tiff", ".gif", ".jp2"]:
        maybeFile = os.path.join(filedir, mediaType + extension)
        if os.path.isfile(maybeFile):
            # we found an image, attempt to create an Proxy Media object to store it
            try:
                Log("loadTvShowArt: found valid {} file : {}".format(mediaType, maybeFile))
                picture = Core.storage.load(maybeFile)
                picture_hash = hashlib.md5(picture).hexdigest()
                collection[picture_hash] = Proxy.Media(picture, sort_order=1)
                break
            except Exception as e:
                Log("loadTvShowArt: Could not access file '{}' due to error {}".format(maybeFile, e))

class YoutubeDLAgent(Agent.TV_Shows):
    name, primary_provider, fallback_agent, contributes_to, languages, accepts_from = (
    'Youtube-DL', True, False, None, [Locale.Language.English, ], None)

    def search(self, results, media, lang, manual=False):
        results.Append(MetadataSearchResult(
            id='youtube-dl|{}|{}'.format(media.filename, media.openSubtitlesHash),
            name=media.title,
            year=None,
            lang=lang,
            score=100
        ))

        results.Sort('score', descending=True)

    def update(self, metadata, media, lang):
        Log("".ljust(157, '='))

        metadataFile = getMetadataExpectedPath(media)
        loadTvShowMetadata(metadata, metadataFile)
        loadTvShowArt(metadataFile, "poster", metadata.posters)
        loadTvShowArt(metadataFile, "banner", metadata.banners)
        loadTvShowArt(metadataFile, "background", metadata.art)

        @parallelize
        def UpdateEpisodes():
            for year in media.seasons:
                for shootID in media.seasons[year].episodes:
                    episode = metadata.seasons[year].episodes[shootID]
                    episode_media = media.seasons[year].episodes[shootID]
                    filepath, file_extension = os.path.splitext(episode_media.items[0].parts[0].file)
                    filepath = filepath.strip()

                    Log("Processing: '{}' in {}".format(filepath, metadata.title))

                    # Check if there is a thumbnail for this episode
                    for extension in [".jpg", ".jpeg", ".webp", ".png", ".tiff", ".gif", ".jp2"]:
                        maybeFile = filepath + extension
                        if os.path.isfile(maybeFile):
                            Log("Found thumbnail {}".format(maybeFile))
                            # we found an image, attempt to create an Proxy Media object to store it
                            try:
                                picture = Core.storage.load(maybeFile)
                                picture_hash = hashlib.md5(picture).hexdigest()
                                episode.thumbs[picture_hash] = Proxy.Media(picture, sort_order=1)
                                break
                            except:
                                Log("Could not access file '{}'".format(maybeFile))

                    # Attempt to open the .info.json file Youtube-DL stores.
                    try:
                        with open(filepath + ".info.json", encoding="utf-8") as json_file:
                            data = json.load(json_file)

                            episode.title = data['fulltitle']
                            episode.summary = data["description"]

                            if 'playlist_index' in data:
                                episode.absolute_index = data['playlist_index']

                            if 'upload_date' in data:
                                episode.originally_available_at = Datetime.ParseDate(data['upload_date']).date()

                            if 'average_rating' in data:
                                episode.rating = (data['average_rating'] * 2)

                            Log("Processed successfully! This episode was named '{}'".format(data['fulltitle']))
                    except IOError:
                        # Attempt to make a title out of the filename
                        episode.title = re.sub('\[.{11}\]', '', os.path.basename(filepath)).strip()
                        Log("Could not access file '{}', named the episode '{}'".format(filepath + ".info.json", episode.title))
