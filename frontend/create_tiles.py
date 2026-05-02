from PIL import Image, ImageDraw

img = Image.new('RGB', (32, 32), color=(100, 100, 100))
draw = ImageDraw.Draw(img)
draw.rectangle([1, 1, 30, 30], outline=(255, 255, 255), width=2)

img.save('tiles.png')
print("tiles.png created successfully")
