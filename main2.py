"""# mask 图片路径
mask_path = 'mask.jpg'
# 载入 mask 图片
def load_mask(mask_path, shape):
# 读取文件
mask = tf.io.read_file(mask_path)
# 变成图片格式
mask = tf.image.decode_image(mask, channels=1)
mask = tf.image.convert_image_dtype(mask, tf.float32)
# 获得生成图片的宽度和高度
_, width, height, _ = shape
# 把 mask 图片 shape 变得跟生成图片一样
mask = tf.image.resize(mask, (width, height))
return mask
# 把 mask 应用到生成的图片中
def mask_content(content, generated, mask):
# 生成图片的 shape
width, height, channels = generated.shape
# 把内容图片变成 numpy 格式
content = content.numpy()
# 把生成图片变成 numpy 格式
generated = generated.numpy()
# mask 图片黑色部分，把内容图片的像素值填充到生成图片中
for i in range(width):
for j in range(height):
if mask[i, j] == 0.:
generated[i, j, :] = content[i, j, :]
return generated
# 载入 mask 图片
mask = load_mask(mask_path, image.shape)
# 3 维降 2 维
s_mask = tf.squeeze(mask)
# 4 维降 3 维
s_image = tf.squeeze(image)
# 4 维降 3 维
s_content_image = tf.squeeze(content_image)
# 把 mask 应用到生成的图片中
img = mask_content(s_content_image,s_image,s_mask)
# 显示图片
imshow(img)"""