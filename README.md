# Anime Unity Downloader (Dockerized Web UI)
A full-stack, containerized application to download your favorite series from Anime Unity with ease.  This project takes the powerful core logic of the original downloader and wraps it into a simple web interface, making it accessible even to those who aren't comfortable with the command line.  

<img width="580" height="605" alt="Screenshot 2026-05-05 alle 16 49 57" src="https://github.com/user-attachments/assets/7c59663c-d827-4e89-bd8d-a5dfe8de4e62" />

> [!IMPORTANT]
> This tool is for educational purposes only. Please respect the terms of service of the original platform and support the anime industry by using official streaming services whenever possible.


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

Create a ```docker-compose.yml``` file:
```
services:
  anime-downloader:
    image: alguolo/unity_downloader:stable
    container_name: anime_unity_app
    ports:
      - "5050:5050"
    volumes:
      - ${FILM_PATH}:/app/Film/Downloads
      - ${SERIES_PATH}:/app/SerieTV/Downloads
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```
Create a ```.env``` file to set your local download paths:
```
nano .env
```
- example ```.env``` file:
```
MOVIES_PATH=/path/to/your/movies 
SERIES_PATH=/path/to/your/tv_series
```

Start your docker compose:
```
docker compose up -d
```
# Access the App

Once the container is running, you can access the interface at:
```
http://your_ip:5050
```
# Monitoring Progress

If you want to check the raw download data, the application exposes the progress file directly via HTTP. This is useful for debugging or verifying the real-time status:
```
http://your_ip:5050/progress.json
```

# Glance Dashboard Integration

I have also created a custom Glance widget to monitor the overall download status and individual episode progress directly from your dashboard.

<img width="336" height="160" alt="Screenshot 2026-05-05 alle 17 27 07" src="https://github.com/user-attachments/assets/dc343d68-608d-4dff-b6e2-8406ab251839" />

<br>


Add your app's IP to your Glance ```.env``` file:
```
ANIME_DOWNLOADER_IP=your_container_ip:port
```
Include the widget in your Glance configuration file (e.g., ```glance.yml```):
```
widgets:
  - $include: anime_downloader.yml
```
Create a new file named ```anime_downloader.yml``` in your Glance configuration folder and paste the following:
```
- type: custom-api
  title: Anime Downloader
  cache: 2s
  subrequests:
    progress:
      url: http://${ANIME_DOWNLOADER_IP}/progress.json
  template: |
    {{ $progress := .Subrequest "progress" }}

    {{ if eq $progress.Response.StatusCode 200 }}

      {{ $animeName   := $progress.JSON.String "anime_name" }}
      {{ $overallPct  := $progress.JSON.Float "overall.percentage" }}
      {{ $completed   := $progress.JSON.Int "overall.completed" }}
      {{ $total       := $progress.JSON.Int "overall.total" }}
      {{ $episodes    := $progress.JSON.Array "episodes" }}

      <div class="list" style="--list-gap: 12px;">

        <!-- Anime name + overall percentage -->
        <div>
          <div class="color-highlight size-h4 text-truncate">{{ $animeName }}</div>
          <div class="flex items-center" style="gap: 10px; margin-top: 6px;">
            <div style="flex-grow: 1; background: rgba(128,128,128,0.2); border-radius: 5px; height: 6px; overflow: hidden;">
              <div style="width: {{ printf "%.1f" $overallPct }}%; background-color: var(--color-positive); height: 100%; border-radius: 5px;"></div>
            </div>
            <div class="size-sm color-highlight" style="flex-shrink: 0; min-width: 60px; text-align: right;">
              {{ printf "%.1f" $overallPct }}% ({{ $completed }}/{{ $total }})
            </div>
          </div>
        </div>

        <!-- Per-episode list (only episodes not yet done) -->
        {{ $pending := 0 }}
        {{ range $ep := $episodes }}
          {{ if not ($ep.Bool "done") }}
            {{ $pending = add $pending 1 }}
          {{ end }}
        {{ end }}

        {{ if gt $pending 0 }}
          <ul class="list collapsible-container" data-collapse-after="0" style="--list-gap: 10px;">
            {{ range $ep := $episodes }}
              {{ if not ($ep.Bool "done") }}
                {{ $epPct := $ep.Float "percentage" }}
                <li class="flex items-center" style="gap: 10px;">
                  <div class="size-sm color-subdue" style="flex-shrink: 0; min-width: 90px;">
                    {{ $ep.String "label" }}
                  </div>
                  <div style="flex-grow: 1; background: rgba(128,128,128,0.2); border-radius: 5px; height: 4px; overflow: hidden;">
                    <div style="width: {{ printf "%.1f" $epPct }}%; background-color: var(--color-positive); height: 100%; border-radius: 5px;"></div>
                  </div>
                  <div class="size-sm color-paragraph" style="flex-shrink: 0; min-width: 42px; text-align: right;">
                    {{ printf "%.1f" $epPct }}%
                  </div>
                </li>
              {{ end }}
            {{ end }}
          </ul>
        {{ else }}
          <div class="color-positive size-sm">All episodes downloaded ✓</div>
        {{ end }}

      </div>

    {{ else }}
      <div class="color-negative size-sm text-center">
        Could not reach progress.json — is the server running?
      </div>
    {{ end }}
```
