from PIL import Image, ImageDraw, ImageFont, features

print("raqm:", features.check("raqm"))
font = ImageFont.truetype("assets/fonts/NotoSansKannada-Regular.ttf", 48)
img = Image.new("RGB", (1000, 200), "white")
ImageDraw.Draw(img).text((20, 50), "ರಾಸಾಯನಿಕ ಕ್ರಿಯೆಗಳು ಮತ್ತು ಸಮೀಕರಣಗಳು", font=font, fill="black")
img.save("kn_test.png")
print("saved kn_test.png")