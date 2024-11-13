import os
import numpy as np
import json
from django.shortcuts import render
from google.cloud import vision
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from django.core.files.storage import default_storage
from django.conf import settings
from .models import Search
from dotenv import load_dotenv

load_dotenv()

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
VISION_ANALYSIS_PATH = os.getenv("VISION_ANALYSIS_PATH")

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = VISION_ANALYSIS_PATH

auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

color_emotion_map = {
    (0, 0, 0): "Sadness",       
    (84, 83, 85): "Neutral",    
    (121, 116, 110): "Neutral",  
    (55, 55, 56): "Sadness",     
    (156, 148, 141): "Neutral",  
    (195, 187, 180): "Comfort",  
    (26, 26, 26): "Sadness",     
    (41, 55, 69): "Calmness",    
    (66, 76, 90): "Seriousness",  
    (243, 235, 227): "Comfort",   
    (63, 53, 41): "Sadness",      
    (117, 77, 93): "Romantic",    
    (115, 122, 208): "Calmness",  
    (180, 99, 98): "Anger",       
    (121, 163, 226): "Joy",       
    (176, 189, 228): "Joy",       
    (147, 102, 114): "Romantic",  
    (125, 105, 193): "Joyful",    
    (167, 97, 114): "Anger",      
    (209, 129, 123): "Sadness",   
    (103, 70, 101): "Sadness",    
    (199, 140, 126): "Warmth",    
    (82, 84, 89): "Neutral",      
    (227, 134, 99): "Warmth",     
    (242, 182, 131): "Happiness",   
    (254, 230, 172): "Happiness",   
    (162, 107, 95): "Warmth",     
    (116, 115, 119): "Neutral",    
    (51, 55, 60): "Seriousness",   
    (180, 89, 61): "Anger",        
}

def get_all_emotions():
    return list(set(color_emotion_map.values()))

def get_emotion_from_rgba(r, g, b):
    closest_emotion = "Neutral"
    min_distance = float('inf')
    for color, emotion in color_emotion_map.items():
        distance = np.sqrt((r - color[0])**2 + (g - color[1])**2 + (b - color[2])**2)
        if distance < min_distance:
            min_distance = distance
            closest_emotion = emotion
    return closest_emotion

def detect_properties(path):
    client = vision.ImageAnnotatorClient()
    with open(path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.image_properties(image=image)
    emotions_in_image = []

    if response.image_properties_annotation:
        for color in response.image_properties_annotation.dominant_colors.colors:
            r, g, b = color.color.red, color.color.green, color.color.blue
            emotion = get_emotion_from_rgba(r, g, b)
            emotions_in_image.append(emotion)
    
    return emotions_in_image

def search_playlist(emotions):
    flattened_emotions = [emotion for emotion in emotions]
    unique_emotions = set(flattened_emotions)
    search_query = " ".join(unique_emotions)

    playlists = []
    offset = 0
    limit = 5
    total_playlists_needed = 5

    while len(playlists) < total_playlists_needed:
        results = sp.search(q=search_query, type="playlist", limit=limit, offset=offset)

        if results['playlists']['items']:
            for item in results['playlists']['items']:
                owner_name = item['owner']['display_name'].lower()
                if owner_name != "spotify" and "official" not in owner_name:
                    playlist_info = {
                        'name': item['name'],
                        'url': item['external_urls']['spotify'],
                        'description': item['description'],
                        'owner': item['owner']['display_name'],
                        'id': item['id']
                    }
                    playlists.append(playlist_info)

            offset += limit
        else:
            break

    return playlists[:total_playlists_needed]

def home(request):
    if request.method == "POST":
        if 'image' in request.FILES:
            image = request.FILES['image']
            
            image_path = default_storage.save(f"uploads/{image.name}", image)
            full_image_path = os.path.join(settings.MEDIA_ROOT, image_path)
            
            emotions = detect_properties(full_image_path)
            playlists = search_playlist(emotions)
            
            Search.objects.create(
                image_path=image_path,
                emotions=json.dumps(emotions), 
                playlists=json.dumps(playlists)
            )
            
            past_playlists = get_last_unique_playlists()
            
            all_emotions = get_all_emotions()

            return render(request, "result.html", {
                'playlists': playlists,
                'past_playlists': past_playlists,
                'all_emotions': all_emotions
            })
    
    return render(request, "index.html")

def get_last_unique_playlists(limit=42):
    searches = Search.objects.order_by('-timestamp').values('playlists', 'emotions')
    
    unique_playlists = []
    seen_playlist_ids = set()

    for search in searches:
        playlists = json.loads(search['playlists'])
        emotions = json.loads(search['emotions'])

        for playlist in playlists:
            if playlist['id'] not in seen_playlist_ids:
                unique_playlists.append({
                    'playlist': playlist,
                    'emotions': emotions
                })
                seen_playlist_ids.add(playlist['id'])

            if len(unique_playlists) >= limit:
                break
        if len(unique_playlists) >= limit:
            break

    return unique_playlists

def past_searches_view(request):
    past_playlists = get_last_unique_playlists()

    context = {
        'past_playlists': past_playlists,
    }
    return render(request, 'recommendation/past_searches.html', context)