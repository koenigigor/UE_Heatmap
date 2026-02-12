# Heatmap generator
Generate heatmap images from Json's gathered by [**TavaHeatmap**](https://github.com/koenigigor) plugin.
<br>
Quickly analyze hot spots, player routes, and behavioral patterns in your game.

![example_paths](https://raw.githubusercontent.com/koenigigor/UE_Heatmap/main/example/example_paths.png)


---

## Usage
1. Download latest release or clone repository.
2. Setup **Config.ini**
   <br>&nbsp;&nbsp;2.1. Set paths for heatmap json's and output textures
   <br>&nbsp;&nbsp;2.2. Set *level_key* for group heatmap by .umap or custom grouping (like zone or specified player in multiple dungeon runs).
3. Run Heatmap tool

> You can override **Config.ini** by _config=_ argument (Heatmap.exe -config=OtherConfig.ini)

---

## Output
In output folder will be textures in their level folders.

![out_structure](https://raw.githubusercontent.com/koenigigor/UE_Heatmap/main/example/out_structure.png)


---

## Future plans
1. SSH copy files from remote server.
2. Config filter by date.
3. Config filter by player name.
4. Web interface for inspect heatmaps in browser.
