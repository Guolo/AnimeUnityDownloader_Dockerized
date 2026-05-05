# Anime Unity Downloader (Dockerized Web UI)
A full-stack, containerized application to download your favorite series from Anime Unity with ease.This project takes the powerful core logic of the original downloader and wraps it into a simple web interface, making it accessible even to those who aren't comfortable with the command line.  
This tool is for educational purposes only. Please respect the terms of service of the original platform and support the anime industry by using official streaming services whenever possible.

# Credits & Attribution
The core backend logic of this application is heavily based on and inspired by the excellent work of Lysagxra/AnimeUnityDownloader.  

I have extended the original project by:  
- Developing a dedicated Frontend for a better user experience.
- Refactoring the backend engine to output real-time download progress to a progress.json file, enabling dynamic progress bars in the UI.
- Dockerizing the entire workflow (Backend + Frontend) for portability.
- Optimizing the integration between the web UI and the download engine.

# Installation & Usage
Prerequisites:  
Docker and Docker Compose installed on your system.

Clone the repository:
```
git clone https://github.com/
cd AnimeUnityDownloader
```
Modify .env file with your films and tv_series path:
```
nano .env
```

Start your docker compose:
```
docker-compose up -d
```
