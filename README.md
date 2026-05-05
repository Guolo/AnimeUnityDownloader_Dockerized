# Anime Unity Downloader (Dockerized Web UI)
A full-stack, containerized application to download your favorite series from Anime Unity with ease.This project takes the powerful core logic of the original downloader and wraps it into a simple web interface, making it accessible even to those who aren't comfortable with the command line.  
> [!IMPORTANT]
> This tool is for educational purposes only. Please respect the terms of service of the original platform and support the anime industry by using official streaming services whenever possible.
<img width="580" height="605" alt="Screenshot 2026-05-05 alle 16 49 57" src="https://github.com/user-attachments/assets/7c59663c-d827-4e89-bd8d-a5dfe8de4e62" />


# Credits & Attribution
The core backend logic of this application is heavily based on and inspired by the excellent work of Lysagxra/AnimeUnityDownloader.  

I have extended the original project by:  
- Developing a dedicated Frontend for a better user experience.
- Refactoring the backend engine to output real-time download progress to a progress.json file, enabling dynamic progress bars in the UI.
- Dockerizing the entire workflow (Backend + Frontend) for portability.
- Optimizing the integration between the web UI and the download engine.

# Installation & Usage
Prerequisites:  
[Docker](https://www.docker.com) and [Docker Compose](https://docs.docker.com/compose/) installed on your system.

Clone the repository:
```
git clone https://github.com/Guolo/AnimeUnityDownloader_Dockerized.git
cd AnimeUnityDownloader_Dockerized
```
modify the ```.env``` file to set your local download paths:
```
nano .env
```
example ```.env``` file:
```
MOVIES_PATH=/path/to/your/movies
SERIES_PATH=/path/to/your/tv_series
```

Start your docker compose:
```
docker-compose up -d
```
# Access the App

Once the container is running, you can access the interface at:
```
http://your_ip:5050
```
# Monitoring Progress

If you want to check the raw download data, the application exposes the progress file directly via HTTP. This is useful for debugging or verifying the real-time status:
```
http://localhost:5050/progress.json
```
