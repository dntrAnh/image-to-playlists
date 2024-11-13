from django.db import models

class Search(models.Model):
    image_path = models.CharField(max_length=255)
    emotions = models.TextField()
    playlists = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.image_path