import matplotlib.pyplot as plt
import tensorflow as tf
import numpy as np
from PIL import Image
# ???????????
max_dim = 800
# ??????
content_path = 'content.jpg'
# ??????
style_path = 'style.png'
# ????
style_weight=10
# ????
content_weight=1
# ???????
total_variation_weight=1e5
# ????
stpes = 301
# ??????????????
save_img = True
# ????
def load_img(path_to_img):
    # ??????
    img = tf.io.read_file(path_to_img)
    # ?? 3 ??????
    img = tf.image.decode_image(img, channels=3, dtype=tf.float32)
    # img = tf.image.convert_image_dtype(img, tf.float32)
    # ????????????? float ??
    shape = tf.cast(tf.shape(img)[:-1], tf.float32)
    # ???????
    long_dim = max(shape)
    # ?????????????? max_dim
    scale = max_dim / long_dim
    new_shape = tf.cast(shape * scale, tf.int32)
    # resize ????
    img = tf.image.resize(img, new_shape)
    # ?? 1 ?????? 4 ???
    img = img[tf.newaxis, :]
    return img
# ??????
def imshow(image, title=None):
    # ??? 4 ????
    if len(image.shape) > 3:
        # ?? size ? 1 ????(1,300,300,3)->(300,300,3)
        image = tf.squeeze(image)
    # ????
    plt.imshow(image)
    if title:
        # ???? title
        plt.title(title)
        plt.axis('off')
        plt.show()
# ??????
content_image = load_img(content_path)
# ??????
style_image = load_img(style_path)
# ??????
imshow(content_image, 'Content Image')
# ??????
imshow(style_image, 'Style Image')



# ???? content loss
# ??????????????????????????
content_layers = ['block5_conv2']
# ??????????
style_layers = ['block1_conv1',
'block2_conv1',
'block3_conv1',
'block4_conv1',
'block5_conv1']
# ????
num_content_layers = len(content_layers)
num_style_layers = len(style_layers)
# ??????????? vgg16 ????????????
def vgg_layers(layer_names):
    # ?? VGG16 ??????
    vgg = tf.keras.applications.VGG16(include_top=False, weights='imagenet')
    # VGG16 ??????????
    vgg.trainable = False
    # ?????????
    outputs = [vgg.get_layer(name).output for name in layer_names]
    # ???????????? vgg16 ????????????
    model = tf.keras.Model([vgg.input], outputs)
    # ????
    return model
# ????????????
style_extractor = vgg_layers(style_layers)
# ????????????????RGB ? BGR
preprocessed_input = tf.keras.applications.vgg16.preprocess_input(style_image*255)
# ?????? style_extractor?????????
style_outputs = style_extractor(preprocessed_input)
# Gram ?????
def gram_matrix(input_tensor):
    # ???????bijc ?? input_tensor ?? 4 ????bijd ?? input_tensor ?? 4 ???
    # ?? input_tensor ? shape ?(1,300,200,32)??? b=1,i=300,j=200,c=32,d=32
    # ->bcd ?????????????(1,32,32),????????????????????
    result = tf.linalg.einsum('bijc,bijd->bcd', input_tensor, input_tensor)
    # ???? shape
    input_shape = tf.shape(input_tensor)
    # ?????????????????
    num_locations = tf.cast(input_shape[1]*input_shape[2], tf.float32)
    # ????????
    return result/(num_locations)
# ??????????????????
class StyleContentModel(tf.keras.models.Model):
    def __init__(self, style_layers, content_layers):
        super(StyleContentModel, self).__init__()
        # ????????????????
        self.vgg = vgg_layers(style_layers + content_layers)
        # ??????????
        self.style_layers = style_layers
        # ???? content loss ????
        self.content_layers = content_layers
        # ??????
        self.num_style_layers = len(style_layers)
    def call(self, inputs):
        # ????????????????RGB ? BGR
        preprocessed_input = tf.keras.applications.vgg16.preprocess_input(inputs*255.0)
        # ???????????????????
        outputs = self.vgg(preprocessed_input)
        # ???????????????
        style_outputs, content_outputs = (outputs[:self.num_style_layers],
        outputs[self.num_style_layers:])
        # ??????? Gram ??
        style_outputs = [gram_matrix(style_output) for style_output in style_outputs]
        # ?????? Gram ????????
        style_dict = {style_name:value for style_name, value in zip(self.style_layers, style_outputs)}
        # ?????????
        content_dict = {content_name:value for content_name, value in zip(self.content_layers, content_outputs)}
        # ????
        return {'content':content_dict, 'style':style_dict}
# ??????????????????
extractor = StyleContentModel(style_layers, content_layers)
# ?????????????
style_targets = extractor(style_image)['style']
# ?????????????
content_targets = extractor(content_image)['content']
# ?????????
image = tf.Variable(content_image)
# ?????
opt = tf.optimizers.Adam(learning_rate=0.02, beta_1=0.99, epsilon=1e-1)
# ???????? 0-1 ??
def clip_0_1(image):
    return tf.clip_by_value(image, clip_value_min=0.0, clip_value_max=1.0)
# ??????? loss
def style_content_loss(outputs):
    # ?????????
    style_outputs = outputs['style']
    # ?????????
    content_outputs = outputs['content']
    # ???? loss
    style_loss = tf.add_n([tf.reduce_mean((style_outputs[name]-style_targets[name])**2)
                           for name in style_outputs.keys()])
    style_loss *= style_weight / num_style_layers
    # ???? loss
    content_loss = tf.add_n([tf.reduce_mean((content_outputs[name]- content_targets[name])**2)
                             for name in content_outputs.keys()])
    content_loss *= content_weight / num_content_layers
    # ????? loss
    loss = style_loss + content_loss
    return loss
# ????????????????????????????????????
def total_variation_loss(image):
    x_deltas = image[:,:,1:,:] - image[:,:,:-1,:]
    y_deltas = image[:,1:,:,:] - image[:,:-1,:,:]
    return tf.reduce_mean(x_deltas**2) + tf.reduce_mean(y_deltas**2)
# ?????@tf.function ????? python ???? tensorflow ?????????????????
@tf.function()
# ???????????
def train_step(image):
    # ??????? tf.GradientTape()?????
    with tf.GradientTape() as tape:
        # ???????????????
        outputs = extractor(image)
        # ??????? loss
        loss = style_content_loss(outputs)
        # ???????? loss
        loss += total_variation_weight*total_variation_loss(image)
    # ?? loss ????????????
    grad = tape.gradient(loss, image)
    # ????????????????? image ??????
    opt.apply_gradients([(grad, image)])
    # ???????? 0-1 ??
    image.assign(clip_0_1(image))


# ?? steps ?
for n in range(stpes):
    # ????
    train_step(image)
    # ??? 5 ???????
    if n%100==0:
        imshow(image.read_value(), "Train step: {}".format(n))
        # ????
        if save_img==True:
            # ??????
            s_image = tf.squeeze(image)
            # ? array ?? Image ??
            s_image = Image.fromarray(np.uint8(s_image.numpy()*255))
            # ??????????
            s_image.save('tmp/'+'steps_'+str(n)+'.jpg')


