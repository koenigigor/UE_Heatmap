import configparser
import json
import os
import shutil
from os import listdir
from os.path import isfile, join
import cv2
import numpy as np
import getopt
import sys


class CoordinateTransformer:
    """ Converts coordinates between world and canvas space """

    def __init__(self, world_bounds, canvas_size):
        self.world_bounds = world_bounds
        self.canvas_size = canvas_size
        self.min_x, self.min_y, self.max_x, self.max_y = world_bounds
        self.canvas_width, self.canvas_height = canvas_size

        self.world_width = self.max_x - self.min_x
        self.world_height = self.max_y - self.min_y

    def world_to_canvas(self, x, y):
        canvas_x = ((x - self.min_x) / self.world_width) * self.canvas_width
        #canvas_y = self.canvas_height - ((y - self.min_y) / self.world_height) * self.canvas_height
        canvas_y = ((y - self.min_y) / self.world_height) * self.canvas_height
        return int(canvas_x), int(canvas_y)


def main():
    # Get config (override via --config argument)
    config_path = 'Config.ini'
    options, args = getopt.getopt(sys.argv[1:], "", ['config='])
    for option in options:
        if option[0] == '--config':     # key
            config_path = option[1]     # value
    
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8-sig")
    
    # Get files in folder
    heatmap_path = str(config['DEFAULT']['heatmap_path'])
    out_folder = str(config['DEFAULT']['out_folder'] + "/")
    heatmap_file_names = [f for f in listdir(heatmap_path) if isfile(join(heatmap_path, f)) and f.endswith(".Json")]

    # Prepare canvas
    canvas_width = int(config.getint('DEFAULT', 'out_width', fallback=1920) * 1.2)
    canvas_height = int(config.getint('DEFAULT', 'out_height', fallback=1080) * 1.2)

    level_key = str(config['DEFAULT']['level_key'])
    levels = {}

    # Set background image (aka. dungeon map)
    #image_background = cv2.imread('BG.png')
    #image_background = cv2.resize(image, (canvas_width, canvas_height))
    image_background = np.zeros((canvas_height, canvas_width, 3), np.uint8)

    # Automatically gather level bounds
    b_gather_auto_bounds = config.getboolean('DEFAULT', 'auto_bounds', fallback=True)
    auto_bounds = {}
    if b_gather_auto_bounds:
        log_iteration = 0
        for heatmap_file in heatmap_file_names:
            log_iteration += 1
            print(f"Gather auto bounds: {log_iteration}/{len(heatmap_file_names)}")

            heatmap_file = open(join(heatmap_path, heatmap_file), "r", encoding="utf-8-sig")
            heat_data = json.load(heatmap_file)
            heatmap_file.close()

            min_x = min_y = 9999999999
            max_x = max_y = -9999999999
            for point in heat_data['points']:
                min_x = min(point["x"], min_x)
                max_x = max(point["x"], max_x)
                min_y = min(point["y"], min_y)
                max_y = max(point["y"], max_y)

            level = heat_data[level_key]
            if level not in auto_bounds:
                auto_bounds[level] = (min_x, min_y, max_x, max_y)
            else:
                _min_x, _min_y, _max_x, _max_y = auto_bounds[level]
                auto_bounds[level] = (
                    min(_min_x, min_x),
                    min(_min_y, min_y),
                    max(_max_x, max_x),
                    max(_max_y, max_y))

    # Load input data
    alpha = max(0.1, 1 / len(heatmap_file_names))
    log_iteration = 0
    for heatmap_file in heatmap_file_names:
        log_iteration += 1
        print(f"Processing: {log_iteration}/{len(heatmap_file_names)}")

        color = (150, 150, 150)

        heatmap_file = open(join(heatmap_path, heatmap_file), "r", encoding="utf-8-sig")
        heat_data = json.load(heatmap_file)
        heatmap_file.close()

        level = heat_data[level_key]

        # init default data
        if level not in levels:
            # todo why sometimes it flipped?
            world_bounds = (
                min(heat_data["levelBoundsMin"]["x"], heat_data["levelBoundsMax"]["x"]),
                min(heat_data["levelBoundsMin"]["y"], heat_data["levelBoundsMax"]["y"]),
                max(heat_data["levelBoundsMin"]["x"], heat_data["levelBoundsMax"]["x"]),
                max(heat_data["levelBoundsMin"]["y"], heat_data["levelBoundsMax"]["y"]))
            if b_gather_auto_bounds:
                world_bounds = auto_bounds[level]

            levels[level] = {}
            levels[level]["transformer"] = CoordinateTransformer(
                world_bounds=world_bounds,
                canvas_size=(canvas_width, canvas_height)
            )
            levels[level]["image_paths"] = image_background.copy()
            levels[level]["image_heatmap"] = image_background.copy()
            levels[level]["image_death"] = image_background.copy()
            levels[level]["event_images"] = {}
            pass

        transformer = levels[level]["transformer"]
        image_paths = levels[level]["image_paths"]
        image_death = levels[level]["image_death"]
        event_images = levels[level]["event_images"]

        # Convert world points to canvas points
        canvas_points = np.array([], dtype=np.int32)
        for point in heat_data['points']:
            x, y = transformer.world_to_canvas(point["x"], point["y"])
            canvas_points = np.append(canvas_points, np.array([x, y])).reshape(-1, 2)

        # Draw path with alpha
        overlay = np.zeros((canvas_height, canvas_width, 3), np.uint8)
        cv2.polylines(overlay, [canvas_points], isClosed=False, color=color, thickness=2)

        levels[level]["image_paths"] = cv2.addWeighted(image_paths, 1, overlay, alpha, 0)

        death_overlay = np.zeros((canvas_height, canvas_width, 3), np.uint8)
        cv2.circle(death_overlay, canvas_points[-1], 4, color=color, thickness=4)
        levels[level]["image_death"] = cv2.addWeighted(image_death, 1, death_overlay, 1, 0)

        # heatmap points
        for point in heat_data['points']:
            x, y = transformer.world_to_canvas(point["x"], point["y"])

            point_overlay = np.zeros((canvas_height, canvas_width, 3), np.uint8)
            cv2.circle(point_overlay, np.array([x, y]), 4, color=color, thickness=4)

            levels[level]["image_heatmap"] = cv2.addWeighted(levels[level]["image_heatmap"], 1, point_overlay, alpha, 0)
            pass

        # events
        if "events" in heat_data:
            for event, points_cont in heat_data["events"].items():
                if event not in event_images:
                    event_images[event] = image_background.copy()

                for point in points_cont["points"]:
                    x, y = transformer.world_to_canvas(point["x"], point["y"])

                    event_overlay = np.zeros((canvas_height, canvas_width, 3), np.uint8)
                    cv2.circle(event_overlay, np.array([x, y]), 4, color=color, thickness=4)

                    event_images[event] = cv2.addWeighted(event_images[event], 1, event_overlay, alpha, 0)

                pass

        pass

    # create out folder
    if not os.path.isdir(out_folder):
        os.makedirs(out_folder)
        
    # clear out folder from previous file
    for filename in os.listdir(out_folder):
        file_path = os.path.join(out_folder, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)

    # save result images
    write_iteration = 0
    for level in levels.keys():
        image_paths = levels[level]["image_paths"]
        image_heatmap = levels[level]["image_heatmap"]
        image_death = levels[level]["image_death"]
        event_images = levels[level]["event_images"]

        image_summarized = cv2.addWeighted(image_paths, 1, image_heatmap, 1, 0)
        image_death_and_path = cv2.addWeighted(image_paths, 1, image_death, 1, 0)

        if not os.path.exists(f"{out_folder}{level}/"):
            os.makedirs(f"{out_folder}{level}/")

        # write out images
        write_iteration += 1
        print(f"Write out images {write_iteration}/{len(levels)}")
        cv2.imwrite(f"{out_folder}{level}/paths.png", image_paths)
        cv2.imwrite(f"{out_folder}{level}/heatmap.png", image_heatmap)
        cv2.imwrite(f"{out_folder}{level}/summarized.png", image_summarized)
        cv2.imwrite(f"{out_folder}{level}/death.png", image_death_and_path)
        for event_name, event_image in event_images.items():
            cv2.imwrite(f"{out_folder}{level}/event_{event_name}.png", event_image)
            pass

    # preview result texture
    #cv2.imshow("Lanteya Paths", image_paths)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()

    pass


if __name__ == '__main__':
    main()
