from time import perf_counter
import urllib
import os
from PIL import Image, ImageQt, ImageOps, ImageEnhance

data = None
images = {}

def init(data):
    # TODO: handle zoom levels properly perhaps
    # TODO: make this caching stuff less of a clusterfuck
    # TODO: not downloading orbits on first run?
    data = data
    begin_init = perf_counter()
    
    # sprites
    for sheet in data['skillSprites'].items():
        sprite_category = {}
        sheet_type = sheet[0]
        sprite_sheet = sheet[1][-1]

        parsed_url = urllib.parse.urlparse(sprite_sheet['filename'])
        filename = os.path.basename(parsed_url.path)
        ver = parsed_url.query
        full_filename = f"{filename}_{ver}.png"
        
        os.makedirs("sprites/", exist_ok=True)

        if not os.path.exists(f"sprites/{full_filename}"):
            urllib.request.urlretrieve(sprite_sheet['filename'], f"sprites/{full_filename}")
        
        img = Image.open(f"sprites/{full_filename}")
        
        for skill in sprite_sheet['coords'].items():
            skill_path = skill[0]
            coords = skill[1]

            sprite = img.crop((coords['x'], coords['y'], 
                                coords['x'] + coords['w'], coords['y'] + coords['h']))

            sprite_category[skill_path] = ImageQt.ImageQt(sprite) 

        images[sheet_type] = sprite_category                   

    images['connectors'] = {}
    # generate connector images
    for state in ['Active', 'Intermediate', 'Normal']:        
        for i in range(1, 7):
            img = Image.open(f"sprites/Orbit{i}{state}.png")
            combined = Image.new('RGBA', (img.width * 2, img.height * 2))
            combined.paste(img, (0, 0))
            combined.paste(ImageOps.mirror(img), (img.width, 0))
            combined.paste(ImageOps.flip(img), (0, img.height))
            combined.paste(ImageOps.mirror(ImageOps.flip(img)), (img.width, img.height))
            images['connectors'][f"Orbit{i}{state}"] = ImageQt.ImageQt(combined)
            
            if state == 'Normal':
                img = ImageEnhance.Brightness(img).enhance(3)
                combined = Image.new('RGBA', (img.width * 2, img.height * 2))
                combined.paste(img, (0, 0))
                combined.paste(ImageOps.mirror(img), (img.width, 0))
                combined.paste(ImageOps.flip(img), (0, img.height))
                combined.paste(ImageOps.mirror(ImageOps.flip(img)), (img.width, img.height))
                images['connectors'][f"Orbit{i}HoverPath"] = ImageQt.ImageQt(combined)
        
        img = Image.open(f"sprites/LineConnector{state}.png")
        images['connectors'][f"LineConnector{state}"] = ImageQt.ImageQt(img)
        if state == 'Normal':
            img = ImageEnhance.Brightness(img).enhance(3)
            images['connectors'][f"LineConnectorHoverPath"] = ImageQt.ImageQt(img)


    #assets
    images['assets'] = {}
    for asset in data['assets'].items():
        asset_name = asset[0]
        asset_image = list(asset[1].values())[-1]
        filename = asset_image.split('/')[-1]

        if not os.path.exists(f"sprites/{filename}"):
            urllib.request.urlretrieve(asset_image, f"sprites/{filename}")
        
        img = Image.open(f"sprites/{filename}")
        img = img.convert('RGBA')
        images['assets'][asset_name] = ImageQt.ImageQt(img)


    print(f"Initialized {len(images)} images in {perf_counter() - begin_init} seconds")

def get_images():
    return images